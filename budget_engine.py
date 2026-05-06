#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Budget Engine for Agent Budget Guard
Handles budget monitoring, anomaly detection, and spending analysis
"""

import os
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlparse

from database import budget_db


class BudgetEngine:
    def __init__(self):
        self.default_daily_limit = float(os.getenv("DEFAULT_DAILY_LIMIT", "5.00"))
        self.default_monthly_limit = float(os.getenv("DEFAULT_MONTHLY_LIMIT", "150.00"))

        # Anomaly detection thresholds
        self.repeated_payment_threshold = 5  # per hour
        self.high_value_threshold = 1.0  # USDC
        self.suspicious_hour_start = 23  # 11 PM
        self.suspicious_hour_end = 6   # 6 AM

        # Risk levels
        self.risk_thresholds = {
            "low": 0.5,      # 50% of daily budget
            "medium": 0.8,   # 80% of daily budget
            "high": 1.0      # 100% of daily budget
        }

        # Known safe APIs (you can expand this list)
        self.known_safe_apis = [
            "api.openai.com",
            "api.anthropic.com",
            "agentic.market",
            "api.together.ai",
            "api.replicate.com"
        ]

    async def check_budget(self, agent_id: str, api_url: str, amount_usdc: float,
                          category: str = "infrastructure", daily_limit: float = None) -> Dict[str, Any]:
        """
        Check if spending is approved and detect anomalies

        Args:
            agent_id: Agent identifier
            api_url: API being paid
            amount_usdc: Payment amount
            category: Spending category
            daily_limit: Override daily limit

        Returns:
            Budget check result
        """
        try:
            # Get or create budget rules
            budget_rules = await budget_db.get_budget_rules(agent_id)
            if not budget_rules:
                # Create default budget rules
                budget_rules = await budget_db.create_budget_rules(
                    agent_id=agent_id,
                    daily_limit=daily_limit or self.default_daily_limit,
                    monthly_limit=self.default_monthly_limit
                )

            # Get current spending
            daily_spend = await budget_db.get_daily_spending(agent_id)
            monthly_spend = await budget_db.get_monthly_spending(agent_id)

            # Calculate remaining budget
            effective_daily_limit = daily_limit or budget_rules.get("daily_limit", self.default_daily_limit)
            remaining_daily = effective_daily_limit - daily_spend
            remaining_monthly = budget_rules.get("monthly_limit", self.default_monthly_limit) - monthly_spend

            # Check basic budget constraints
            approved = True
            reason = "Budget check passed"
            warnings = []

            # Daily limit check
            if daily_spend + amount_usdc > effective_daily_limit:
                approved = False
                reason = f"Daily limit exceeded: {daily_spend + amount_usdc:.2f} > {effective_daily_limit:.2f} USDC"

            # Monthly limit check
            elif monthly_spend + amount_usdc > budget_rules.get("monthly_limit", self.default_monthly_limit):
                approved = False
                reason = f"Monthly limit exceeded: {monthly_spend + amount_usdc:.2f} > {budget_rules.get('monthly_limit', self.default_monthly_limit):.2f} USDC"

            # Anomaly detection
            anomalies = await self._detect_anomalies(agent_id, api_url, amount_usdc, category)
            if anomalies:
                warnings.extend(anomalies)

                # High-risk anomalies can block transactions
                high_risk_anomalies = [a for a in anomalies if "CRITICAL" in a or "SUSPICIOUS" in a]
                if high_risk_anomalies and approved:
                    approved = False
                    reason = f"Transaction blocked due to anomalies: {'; '.join(high_risk_anomalies[:2])}"

            # Calculate risk level
            risk_level = self._calculate_risk_level(daily_spend + amount_usdc, effective_daily_limit)

            # Log anomalies if any detected
            if anomalies:
                await budget_db.log_anomaly_alert(
                    agent_id=agent_id,
                    alert_type="budget_anomaly",
                    severity="medium" if approved else "high",
                    description=f"Anomalies detected: {'; '.join(anomalies)}",
                    metadata={
                        "api_url": api_url,
                        "amount_usdc": amount_usdc,
                        "daily_spend": daily_spend,
                        "anomalies": anomalies
                    }
                )

            result = {
                "approved": approved,
                "reason": reason,
                "current_daily_spend": round(daily_spend, 2),
                "remaining_budget": round(max(0, remaining_daily), 2),
                "risk_level": risk_level,
                "warnings": warnings
            }

            print(f"[OK] Budget check for {agent_id}: approved={approved}, risk={risk_level}")
            return result

        except Exception as e:
            print(f"[ERROR] Budget check failed: {e}")
            raise

    async def record_transaction(self, agent_id: str, api_url: str, amount_usdc: float,
                               transaction_id: str, category: str = "infrastructure") -> Dict[str, Any]:
        """
        Record a completed transaction

        Args:
            agent_id: Agent identifier
            api_url: API that was paid
            amount_usdc: Payment amount
            transaction_id: Transaction hash/ID
            category: Spending category

        Returns:
            Recording result with totals
        """
        try:
            # Record transaction
            await budget_db.record_transaction(
                agent_id=agent_id,
                api_url=api_url,
                amount_usdc=amount_usdc,
                transaction_id=transaction_id,
                category=category
            )

            # Get updated totals
            daily_total = await budget_db.get_daily_spending(agent_id)
            monthly_total = await budget_db.get_monthly_spending(agent_id)

            # Post-transaction anomaly check
            await self._post_transaction_analysis(agent_id, api_url, amount_usdc)

            result = {
                "recorded": True,
                "total_today": round(daily_total, 2),
                "total_this_month": round(monthly_total, 2)
            }

            print(f"[OK] Transaction recorded for {agent_id}: {amount_usdc} USDC to {api_url}")
            return result

        except Exception as e:
            print(f"[ERROR] Transaction recording failed: {e}")
            raise

    async def get_agent_report(self, agent_id: str) -> Dict[str, Any]:
        """
        Generate detailed spending report for agent

        Args:
            agent_id: Agent identifier

        Returns:
            Detailed spending report
        """
        try:
            # Get spending totals
            daily_spend = await budget_db.get_daily_spending(agent_id)
            monthly_spend = await budget_db.get_monthly_spending(agent_id)

            # Get budget rules
            budget_rules = await budget_db.get_budget_rules(agent_id)
            daily_limit = budget_rules.get("daily_limit", self.default_daily_limit) if budget_rules else self.default_daily_limit

            # Get recent transactions
            transactions = await budget_db.get_agent_transactions(agent_id, limit=50)

            # Calculate budget utilization
            budget_utilization = (daily_spend / daily_limit) * 100 if daily_limit > 0 else 0

            # Risk assessment
            risk_assessment = self._assess_agent_risk(daily_spend, daily_limit, transactions)

            # Get recent alerts
            alerts = await budget_db.get_agent_alerts(agent_id, days=7)

            # Spending patterns analysis
            spending_patterns = await self._analyze_spending_patterns(agent_id, transactions)

            report = {
                "agent_id": agent_id,
                "daily_spend": round(daily_spend, 2),
                "monthly_spend": round(monthly_spend, 2),
                "daily_limit": daily_limit,
                "monthly_limit": budget_rules.get("monthly_limit", self.default_monthly_limit) if budget_rules else self.default_monthly_limit,
                "transactions": [
                    {
                        "api_url": tx["api_url"],
                        "amount_usdc": tx["amount_usdc"],
                        "category": tx["category"],
                        "timestamp": tx["timestamp"],
                        "transaction_id": tx["transaction_id"][:16] + "..." if len(tx["transaction_id"]) > 16 else tx["transaction_id"]
                    }
                    for tx in transactions[:20]  # Last 20 transactions
                ],
                "budget_utilization": round(budget_utilization, 1),
                "risk_assessment": risk_assessment,
                "recent_alerts": len(alerts),
                "spending_patterns": spending_patterns,
                "report_generated_at": datetime.now().isoformat()
            }

            print(f"[OK] Generated report for {agent_id}: {daily_spend:.2f} USDC spent today")
            return report

        except Exception as e:
            print(f"[ERROR] Agent report generation failed: {e}")
            raise

    async def _detect_anomalies(self, agent_id: str, api_url: str, amount_usdc: float, category: str) -> List[str]:
        """Detect spending anomalies"""
        anomalies = []

        try:
            # 1. Repeated payments to same API (5+ times per hour)
            recent_payments = await budget_db.get_recent_api_payments(agent_id, api_url, hours=1)
            if len(recent_payments) >= self.repeated_payment_threshold:
                anomalies.append(f"CRITICAL: {len(recent_payments)} payments to same API in last hour")

            # 2. Sudden high-value payment
            if amount_usdc >= self.high_value_threshold:
                avg_payment = await budget_db.get_average_payment(agent_id, days=7)
                if avg_payment > 0 and amount_usdc > avg_payment * 3:
                    anomalies.append(f"HIGH: Payment {amount_usdc:.2f} USDC is 3x higher than usual ({avg_payment:.2f} USDC)")

            # 3. Unknown API
            domain = self._extract_domain(api_url)
            if domain not in self.known_safe_apis:
                known_domains = await budget_db.get_agent_known_apis(agent_id)
                if domain not in known_domains:
                    anomalies.append(f"MEDIUM: First payment to unknown API domain: {domain}")

            # 4. Late night spending pattern
            current_hour = datetime.now().hour
            if self.suspicious_hour_start <= current_hour or current_hour <= self.suspicious_hour_end:
                night_spending = await budget_db.get_night_spending_pattern(agent_id)
                if night_spending < 0.1:  # Less than 10% of usual spending is at night
                    anomalies.append(f"SUSPICIOUS: Late night payment at {current_hour}:00")

            # 5. Rapid spending spike
            last_hour_spend = await budget_db.get_hourly_spending(agent_id, hours=1)
            if last_hour_spend + amount_usdc > 2.0:  # More than $2 in an hour
                anomalies.append(f"MEDIUM: High hourly spending: ${last_hour_spend + amount_usdc:.2f}")

            return anomalies

        except Exception as e:
            print(f"[WARN] Anomaly detection failed: {e}")
            return []

    def _extract_domain(self, api_url: str) -> str:
        """Extract domain from API URL"""
        try:
            parsed = urlparse(api_url)
            return parsed.netloc.lower()
        except:
            return api_url.lower()

    def _calculate_risk_level(self, current_spend: float, daily_limit: float) -> str:
        """Calculate risk level based on spending"""
        if daily_limit <= 0:
            return "medium"

        ratio = current_spend / daily_limit

        if ratio >= self.risk_thresholds["high"]:
            return "high"
        elif ratio >= self.risk_thresholds["medium"]:
            return "medium"
        else:
            return "low"

    def _assess_agent_risk(self, daily_spend: float, daily_limit: float, transactions: List[Dict]) -> str:
        """Assess overall agent risk"""
        # Budget utilization risk
        utilization = (daily_spend / daily_limit) if daily_limit > 0 else 0

        # Transaction frequency risk
        recent_tx_count = len([tx for tx in transactions if
                              (datetime.now() - datetime.fromisoformat(tx["timestamp"])).hours <= 24])

        # Variety risk (many different APIs)
        unique_apis = len(set(tx["api_url"] for tx in transactions[:10]))

        risk_score = 0

        if utilization > 0.9:
            risk_score += 3
        elif utilization > 0.7:
            risk_score += 2
        elif utilization > 0.5:
            risk_score += 1

        if recent_tx_count > 20:
            risk_score += 2
        elif recent_tx_count > 10:
            risk_score += 1

        if unique_apis > 5:
            risk_score += 1

        if risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"

    async def _analyze_spending_patterns(self, agent_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """Analyze agent spending patterns"""
        if not transactions:
            return {"no_data": True}

        # Category distribution
        categories = {}
        for tx in transactions:
            cat = tx.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + tx["amount_usdc"]

        # Top APIs
        apis = {}
        for tx in transactions:
            api = self._extract_domain(tx["api_url"])
            apis[api] = apis.get(api, 0) + tx["amount_usdc"]

        # Time patterns
        hours = {}
        for tx in transactions:
            try:
                hour = datetime.fromisoformat(tx["timestamp"]).hour
                hours[hour] = hours.get(hour, 0) + 1
            except:
                continue

        return {
            "top_categories": dict(sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]),
            "top_apis": dict(sorted(apis.items(), key=lambda x: x[1], reverse=True)[:3]),
            "peak_hours": dict(sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]),
            "transaction_count": len(transactions)
        }

    async def _post_transaction_analysis(self, agent_id: str, api_url: str, amount_usdc: float):
        """Analyze patterns after transaction is recorded"""
        try:
            # Check for rapid successive payments
            recent_same_api = await budget_db.get_recent_api_payments(agent_id, api_url, hours=1)
            if len(recent_same_api) > 3:
                await budget_db.log_anomaly_alert(
                    agent_id=agent_id,
                    alert_type="rapid_payments",
                    severity="medium",
                    description=f"Multiple payments to {api_url} in short timeframe",
                    metadata={"payment_count": len(recent_same_api), "api_url": api_url}
                )

        except Exception as e:
            print(f"[WARN] Post-transaction analysis failed: {e}")

    async def test_system(self) -> bool:
        """Test budget engine functionality"""
        try:
            # Test basic calculations
            test_risk = self._calculate_risk_level(3.0, 5.0)
            test_domain = self._extract_domain("https://api.openai.com/v1/chat")

            return test_risk == "medium" and test_domain == "api.openai.com"
        except Exception as e:
            print(f"[ERROR] Budget engine test failed: {e}")
            return False