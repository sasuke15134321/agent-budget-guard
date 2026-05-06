#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database operations for Agent Budget Guard
Handles PostgreSQL database for budget rules, transactions, and anomaly alerts
"""

import os
import json
import asyncpg
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib


class BudgetDatabase:
    def __init__(self):
        # Use DATABASE_URL environment variable for PostgreSQL connection
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            # Fallback to individual components if DATABASE_URL not set
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            database = os.getenv("POSTGRES_DB", "budget_guard")
            user = os.getenv("POSTGRES_USER", "postgres")
            password = os.getenv("POSTGRES_PASSWORD", "")

            if password:
                self.database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                self.database_url = f"postgresql://{user}@{host}:{port}/{database}"

        print(f"[INFO] PostgreSQL database configured: {self.database_url.split('@')[1] if '@' in self.database_url else self.database_url}")

    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.database_url)

    async def initialize(self):
        """Initialize database and create tables if they don't exist"""
        conn = await self.get_connection()
        try:
            # Create budget_rules table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_rules (
                    id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(255) UNIQUE NOT NULL,
                    daily_limit DECIMAL(10, 4) DEFAULT 5.0000,
                    monthly_limit DECIMAL(10, 4) DEFAULT 150.0000,
                    category_limits JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create transactions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(255) NOT NULL,
                    api_url TEXT NOT NULL,
                    amount_usdc DECIMAL(10, 4) NOT NULL,
                    transaction_id VARCHAR(255) NOT NULL,
                    category VARCHAR(100) DEFAULT 'infrastructure',
                    timestamp TIMESTAMP DEFAULT NOW(),
                    metadata JSONB DEFAULT '{}',
                    approved BOOLEAN DEFAULT true
                )
            """)

            # Create alerts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(255) NOT NULL,
                    alert_type VARCHAR(100) NOT NULL,
                    severity VARCHAR(20) DEFAULT 'medium',
                    description TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW(),
                    resolved BOOLEAN DEFAULT false
                )
            """)

            # Create budget_checks table for logging check requests
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_checks (
                    id SERIAL PRIMARY KEY,
                    agent_id VARCHAR(255) NOT NULL,
                    api_url TEXT NOT NULL,
                    amount_usdc DECIMAL(10, 4) NOT NULL,
                    approved BOOLEAN NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_rules_agent_id ON budget_rules(agent_id)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_agent_id ON transactions(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_api_url ON transactions(api_url)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_agent_id ON alerts(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_alert_type ON alerts(alert_type)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_checks_agent_id ON budget_checks(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_budget_checks_timestamp ON budget_checks(timestamp)")

            print("[OK] PostgreSQL database initialized with all tables and indexes")

        finally:
            await conn.close()

    async def get_budget_rules(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get budget rules for an agent"""
        conn = await self.get_connection()
        try:
            row = await conn.fetchrow("""
                SELECT daily_limit, monthly_limit, category_limits, created_at, updated_at
                FROM budget_rules WHERE agent_id = $1
            """, agent_id)

            if row:
                return {
                    "daily_limit": float(row["daily_limit"]),
                    "monthly_limit": float(row["monthly_limit"]),
                    "category_limits": json.loads(row["category_limits"]) if row["category_limits"] else {},
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat()
                }
            return None

        finally:
            await conn.close()

    async def create_budget_rules(self, agent_id: str, daily_limit: float = 5.0,
                                monthly_limit: float = 150.0, category_limits: Dict[str, float] = None) -> Dict[str, Any]:
        """Create budget rules for an agent"""
        conn = await self.get_connection()
        try:
            category_limits = category_limits or {}

            await conn.execute("""
                INSERT INTO budget_rules (agent_id, daily_limit, monthly_limit, category_limits)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (agent_id) DO UPDATE SET
                    daily_limit = $2,
                    monthly_limit = $3,
                    category_limits = $4,
                    updated_at = NOW()
            """, agent_id, daily_limit, monthly_limit, json.dumps(category_limits))

            return {
                "daily_limit": daily_limit,
                "monthly_limit": monthly_limit,
                "category_limits": category_limits
            }

        finally:
            await conn.close()

    async def get_daily_spending(self, agent_id: str, date: datetime = None) -> float:
        """Get total daily spending for an agent"""
        conn = await self.get_connection()
        try:
            target_date = date or datetime.now().date()

            total = await conn.fetchval("""
                SELECT COALESCE(SUM(amount_usdc), 0)
                FROM transactions
                WHERE agent_id = $1 AND DATE(timestamp) = $2
            """, agent_id, target_date)

            return float(total or 0)

        finally:
            await conn.close()

    async def get_monthly_spending(self, agent_id: str, date: datetime = None) -> float:
        """Get total monthly spending for an agent"""
        conn = await self.get_connection()
        try:
            target_date = date or datetime.now()
            month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            total = await conn.fetchval("""
                SELECT COALESCE(SUM(amount_usdc), 0)
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
            """, agent_id, month_start)

            return float(total or 0)

        finally:
            await conn.close()

    async def record_transaction(self, agent_id: str, api_url: str, amount_usdc: float,
                               transaction_id: str, category: str = "infrastructure") -> int:
        """Record a transaction"""
        conn = await self.get_connection()
        try:
            tx_id = await conn.fetchval("""
                INSERT INTO transactions (agent_id, api_url, amount_usdc, transaction_id, category)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, agent_id, api_url, amount_usdc, transaction_id, category)

            return tx_id

        finally:
            await conn.close()

    async def log_budget_check(self, agent_id: str, api_url: str, amount_usdc: float,
                             approved: bool, reason: str = None) -> int:
        """Log a budget check request"""
        conn = await self.get_connection()
        try:
            check_id = await conn.fetchval("""
                INSERT INTO budget_checks (agent_id, api_url, amount_usdc, approved, reason)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, agent_id, api_url, amount_usdc, approved, reason)

            return check_id

        finally:
            await conn.close()

    async def log_anomaly_alert(self, agent_id: str, alert_type: str, severity: str,
                              description: str, metadata: Dict[str, Any] = None) -> int:
        """Log an anomaly alert"""
        conn = await self.get_connection()
        try:
            alert_id = await conn.fetchval("""
                INSERT INTO alerts (agent_id, alert_type, severity, description, metadata)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, agent_id, alert_type, severity, description, json.dumps(metadata or {}))

            return alert_id

        finally:
            await conn.close()

    async def get_recent_api_payments(self, agent_id: str, api_url: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get recent payments to a specific API"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(hours=hours)

            rows = await conn.fetch("""
                SELECT amount_usdc, timestamp, transaction_id
                FROM transactions
                WHERE agent_id = $1 AND api_url = $2 AND timestamp >= $3
                ORDER BY timestamp DESC
            """, agent_id, api_url, since)

            return [
                {
                    "amount_usdc": float(row["amount_usdc"]),
                    "timestamp": row["timestamp"].isoformat(),
                    "transaction_id": row["transaction_id"]
                }
                for row in rows
            ]

        finally:
            await conn.close()

    async def get_average_payment(self, agent_id: str, days: int = 7) -> float:
        """Get average payment amount for an agent"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(days=days)

            avg = await conn.fetchval("""
                SELECT AVG(amount_usdc)
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
            """, agent_id, since)

            return float(avg or 0)

        finally:
            await conn.close()

    async def get_agent_known_apis(self, agent_id: str, days: int = 30) -> List[str]:
        """Get list of APIs the agent has used before"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(days=days)

            rows = await conn.fetch("""
                SELECT DISTINCT api_url
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
            """, agent_id, since)

            # Extract domains
            domains = []
            for row in rows:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(row["api_url"]).netloc.lower()
                    if domain:
                        domains.append(domain)
                except:
                    continue

            return list(set(domains))

        finally:
            await conn.close()

    async def get_night_spending_pattern(self, agent_id: str, days: int = 30) -> float:
        """Get percentage of spending that occurs at night"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(days=days)

            # Total spending
            total = await conn.fetchval("""
                SELECT COALESCE(SUM(amount_usdc), 0)
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
            """, agent_id, since)

            # Night spending (11 PM to 6 AM)
            night = await conn.fetchval("""
                SELECT COALESCE(SUM(amount_usdc), 0)
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
                AND (EXTRACT(hour FROM timestamp) >= 23 OR EXTRACT(hour FROM timestamp) <= 6)
            """, agent_id, since)

            if total > 0:
                return float(night) / float(total)
            return 0.0

        finally:
            await conn.close()

    async def get_hourly_spending(self, agent_id: str, hours: int = 1) -> float:
        """Get spending in the last N hours"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(hours=hours)

            total = await conn.fetchval("""
                SELECT COALESCE(SUM(amount_usdc), 0)
                FROM transactions
                WHERE agent_id = $1 AND timestamp >= $2
            """, agent_id, since)

            return float(total or 0)

        finally:
            await conn.close()

    async def get_agent_transactions(self, agent_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent transactions for an agent"""
        conn = await self.get_connection()
        try:
            rows = await conn.fetch("""
                SELECT api_url, amount_usdc, transaction_id, category, timestamp
                FROM transactions
                WHERE agent_id = $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, agent_id, limit)

            return [
                {
                    "api_url": row["api_url"],
                    "amount_usdc": float(row["amount_usdc"]),
                    "transaction_id": row["transaction_id"],
                    "category": row["category"],
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in rows
            ]

        finally:
            await conn.close()

    async def get_agent_alerts(self, agent_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get recent alerts for an agent"""
        conn = await self.get_connection()
        try:
            since = datetime.now() - timedelta(days=days)

            rows = await conn.fetch("""
                SELECT alert_type, severity, description, created_at
                FROM alerts
                WHERE agent_id = $1 AND created_at >= $2
                ORDER BY created_at DESC
            """, agent_id, since)

            return [
                {
                    "alert_type": row["alert_type"],
                    "severity": row["severity"],
                    "description": row["description"],
                    "created_at": row["created_at"].isoformat()
                }
                for row in rows
            ]

        finally:
            await conn.close()

    async def get_budget_statistics(self) -> Dict[str, Any]:
        """Get overall budget statistics"""
        conn = await self.get_connection()
        try:
            stats = {}

            # Total agents
            total_agents = await conn.fetchval("SELECT COUNT(DISTINCT agent_id) FROM budget_rules")
            stats['total_agents'] = total_agents or 0

            # Daily spending by agent (today)
            today = datetime.now().date()
            daily_spending_rows = await conn.fetch("""
                SELECT agent_id, SUM(amount_usdc) as daily_total
                FROM transactions
                WHERE DATE(timestamp) = $1
                GROUP BY agent_id
                ORDER BY daily_total DESC
                LIMIT 10
            """, today)

            stats['daily_spending'] = {
                row['agent_id']: float(row['daily_total'])
                for row in daily_spending_rows
            }

            # Top APIs
            top_apis_rows = await conn.fetch("""
                SELECT api_url, COUNT(*) as usage_count, SUM(amount_usdc) as total_spent
                FROM transactions
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                GROUP BY api_url
                ORDER BY total_spent DESC
                LIMIT 10
            """)

            stats['top_apis'] = [
                {
                    "api_url": row['api_url'],
                    "usage_count": row['usage_count'],
                    "total_spent": float(row['total_spent'])
                }
                for row in top_apis_rows
            ]

            # Recent anomalies
            recent_anomalies = await conn.fetch("""
                SELECT agent_id, alert_type, severity, description, created_at
                FROM alerts
                WHERE created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 10
            """)

            stats['anomalies_detected'] = [
                {
                    "agent_id": row['agent_id'],
                    "alert_type": row['alert_type'],
                    "severity": row['severity'],
                    "description": row['description'],
                    "created_at": row['created_at'].isoformat()
                }
                for row in recent_anomalies
            ]

            return stats

        finally:
            await conn.close()

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = await self.get_connection()
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Database connection test failed: {e}")
            return False


# Global database instance
budget_db = BudgetDatabase()