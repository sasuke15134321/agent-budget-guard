#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Budget Guard API
FastAPI server with x402 payment protocol for AI agent spending monitoring and anomaly detection
"""

import os
from fastapi import FastAPI, Request, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import asyncio
import traceback

from payment_verifier import PaymentVerifier
from budget_engine import BudgetEngine
from database import budget_db

# Environment variables
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0x")
PRICE_USDC = os.getenv("PRICE_USDC", "0.03")
NETWORK = os.getenv("NETWORK", "base-mainnet")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

app = FastAPI(
    title="Agent Budget Guard API",
    description="AI agent spending monitoring and anomaly detection service with x402 payment protocol",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paid endpoint config: path -> (price, method)
_PAID_ENDPOINTS = {
    ("POST", "/api/budget/check"):  "0.03",
    ("POST", "/api/budget/record"): "0.01",
}

@app.middleware("http")
async def x402_payment_middleware(request: Request, call_next):
    """Pydantic バリデーションより先に支払いヘッダーをチェックする"""
    method = request.method
    path = request.url.path

    # GET /api/budget/report/{agent_id} も有料
    is_report = method == "GET" and path.startswith("/api/budget/report/")
    price_for_report = "0.05"

    key = (method, path)
    price = _PAID_ENDPOINTS.get(key) or (price_for_report if is_report else None)

    if not TEST_MODE and price is not None:
        payment_header = request.headers.get("X-PAYMENT")
        if not payment_header:
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment Required",
                    "price": price,
                    "currency": "USDC",
                    "network": "base-mainnet",
                    "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE",
                    "endpoint": path
                }
            )

    return await call_next(request)

# Initialize components
payment_verifier = PaymentVerifier()
budget_engine = BudgetEngine()

# Startup event
@app.on_event("startup")
async def startup_event():
    try:
        await budget_db.initialize()
        print("[OK] Agent Budget Guard API startup complete")
    except Exception as e:
        print(f"[WARN] Database initialization failed (continuing without DB): {e}")
        print("[OK] Agent Budget Guard API started in DB-less mode")

# Request models
class BudgetCheckRequest(BaseModel):
    agent_id: str
    api_url: str
    amount_usdc: float
    category: str = "infrastructure"  # consulting, infrastructure, security
    daily_limit: Optional[float] = 5.00

class RecordTransactionRequest(BaseModel):
    agent_id: str
    api_url: str
    amount_usdc: float
    transaction_id: str
    category: Optional[str] = "infrastructure"

# Response models
class NextRecommendation(BaseModel):
    api_name: str
    url: str
    reason: str
    expected_improvement: str
    price_usdc: float

class BudgetCheckResponse(BaseModel):
    approved: bool
    reason: str
    current_daily_spend: float
    remaining_budget: float
    risk_level: str
    warnings: List[str]
    next_recommended: NextRecommendation

class RecordTransactionResponse(BaseModel):
    recorded: bool
    total_today: float
    total_this_month: float
    next_recommended: NextRecommendation

class BudgetStatsResponse(BaseModel):
    total_agents: int
    daily_spending: Dict[str, float]
    top_apis: List[Dict[str, Any]]
    anomalies_detected: List[Dict[str, Any]]

class AgentReportResponse(BaseModel):
    agent_id: str
    daily_spend: float
    monthly_spend: float
    transactions: List[Dict[str, Any]]
    budget_utilization: float
    risk_assessment: str
    next_recommended: NextRecommendation

# AI agent policy endpoint
@app.get("/.well-known/ai-agent-policy")
async def ai_agent_policy():
    import json
    import os
    policy_path = "ai-agent-policy.json"
    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Policy not found"}

# x402 payment protocol endpoint discovery
@app.get("/.well-known/x402.json")
async def x402_discovery():
    """x402 protocol endpoint discovery for Agentic.Market"""
    return {
        "version": 1,
        "endpoints": [
            {
                "path": "/api/budget/check",
                "method": "POST",
                "price": PRICE_USDC,
                "currency": "USDC",
                "network": "base",
                "description": "エージェント支出承認チェック・異常検出",
                "category": "finance",
                "tags": ["ai", "budget", "spending", "monitoring", "anomaly-detection"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "budget-monitoring"
                    }
                }
            },
            {
                "path": "/api/budget/record",
                "method": "POST",
                "price": "0.01",
                "currency": "USDC",
                "network": "base",
                "description": "エージェント支出記録・トラッキング",
                "category": "finance",
                "tags": ["ai", "budget", "transaction", "recording"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "transaction-recording"
                    }
                }
            },
            {
                "path": "/api/budget/report/{agent_id}",
                "method": "GET",
                "price": "0.05",
                "currency": "USDC",
                "network": "base",
                "description": "エージェント別詳細支出レポート",
                "category": "finance",
                "tags": ["ai", "budget", "report", "analytics"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "spending-analytics"
                    }
                }
            }
        ]
    }

@app.post("/api/budget/check", response_model=BudgetCheckResponse)
async def check_budget(request: BudgetCheckRequest, http_request: Request):
    """Check budget and approve/deny spending with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            raise HTTPException(
                status_code=402,
                detail={
                    "x402Version": 1,
                    "accepts": [{
                        "scheme": "exact",
                        "network": "base",
                        "maxAmountRequired": "30000",  # 0.03 USDC
                        "resource": f"{http_request.url}",
                        "description": "Budget Check - エージェント支出承認チェック",
                        "mimeType": "application/json",
                        "payTo": WALLET_ADDRESS,
                        "maxTimeoutSeconds": 300,
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "extra": {"name": "USDC", "version": "2"}
                    }]
                }
            )

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, PRICE_USDC)
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await budget_engine.check_budget(
            agent_id=request.agent_id,
            api_url=request.api_url,
            amount_usdc=request.amount_usdc,
            category=request.category,
            daily_limit=request.daily_limit
        )

        # Log budget check
        await budget_db.log_budget_check(
            agent_id=request.agent_id,
            api_url=request.api_url,
            amount_usdc=request.amount_usdc,
            approved=result["approved"],
            reason=result["reason"]
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security Gateway",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "予算管理データのセキュリティ強化と不正取引検出",
            "expected_improvement": "90%予算保護強化",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        print(f"[ERROR] Budget check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Budget check failed: {str(e)}")

@app.post("/api/budget/record", response_model=RecordTransactionResponse)
async def record_transaction(request: RecordTransactionRequest, http_request: Request):
    """Record transaction with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            raise HTTPException(
                status_code=402,
                detail={
                    "x402Version": 1,
                    "accepts": [{
                        "scheme": "exact",
                        "network": "base",
                        "maxAmountRequired": "10000",  # 0.01 USDC
                        "resource": f"{http_request.url}",
                        "description": "Transaction Recording - 支出記録",
                        "mimeType": "application/json",
                        "payTo": WALLET_ADDRESS,
                        "maxTimeoutSeconds": 300,
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "extra": {"name": "USDC", "version": "2"}
                    }]
                }
            )

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.01")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await budget_engine.record_transaction(
            agent_id=request.agent_id,
            api_url=request.api_url,
            amount_usdc=request.amount_usdc,
            transaction_id=request.transaction_id,
            category=request.category
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security Gateway",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "取引記録の改ざん防止とセキュリティ監査ログ強化",
            "expected_improvement": "95%取引データ保護",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        print(f"[ERROR] Transaction recording failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transaction recording failed: {str(e)}")

@app.get("/api/budget/report/{agent_id}", response_model=AgentReportResponse)
async def get_agent_report(agent_id: str = Path(..., description="Agent ID"), http_request: Request = None):
    """Get detailed spending report for specific agent with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            raise HTTPException(
                status_code=402,
                detail={
                    "x402Version": 1,
                    "accepts": [{
                        "scheme": "exact",
                        "network": "base",
                        "maxAmountRequired": "50000",  # 0.05 USDC
                        "resource": f"{http_request.url}",
                        "description": "Agent Report - エージェント詳細レポート",
                        "mimeType": "application/json",
                        "payTo": WALLET_ADDRESS,
                        "maxTimeoutSeconds": 300,
                        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                        "extra": {"name": "USDC", "version": "2"}
                    }]
                }
            )

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.05")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        report = await budget_engine.get_agent_report(agent_id)

        # Add cross-sell recommendation
        report["next_recommended"] = {
            "api_name": "Agent Security Gateway",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "予算レポートの機密性保護とアクセス権限管理",
            "expected_improvement": "85%レポートセキュリティ向上",
            "price_usdc": 0.05
        }

        return report
    except Exception as e:
        print(f"[ERROR] Agent report generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Agent report generation failed: {str(e)}")

@app.get("/api/budget/stats", response_model=BudgetStatsResponse)
async def get_budget_stats():
    """Get budget statistics (free endpoint)"""
    try:
        stats = await budget_db.get_budget_statistics()
        return stats
    except Exception as e:
        print(f"[ERROR] Failed to get budget stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get budget statistics: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Test database connectivity
    database_status = "operational"
    try:
        await budget_db.test_connection()
    except Exception:
        database_status = "error"

    # Test budget engine
    engine_status = "operational"
    try:
        await budget_engine.test_system()
    except Exception:
        engine_status = "error"

    return {
        "status": "healthy",
        "test_mode": TEST_MODE,
        "network": NETWORK,
        "services": {
            "budget_engine": engine_status,
            "database": database_status,
            "payment_verifier": "operational"
        },
        "anomaly_detection": {
            "repeated_payments": True,
            "daily_limit_exceeded": True,
            "sudden_high_payments": True,
            "unknown_api_payments": True,
            "late_night_patterns": True
        }
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Agent Budget Guard API",
        "description": "AI agent spending monitoring and anomaly detection service",
        "endpoints": {
            "budget_check": "/api/budget/check",
            "record_transaction": "/api/budget/record",
            "agent_report": "/api/budget/report/{agent_id}",
            "budget_stats": "/api/budget/stats",
            "health": "/health",
            "discovery": "/.well-known/x402.json"
        },
        "pricing": {
            "budget_check": f"{PRICE_USDC} USDC",
            "record_transaction": "0.01 USDC",
            "agent_report": "0.05 USDC"
        },
        "network": NETWORK,
        "currency": "USDC",
        "anomaly_patterns": [
            "repeated_api_payments",
            "daily_limit_exceeded",
            "sudden_high_payments",
            "unknown_api_payments",
            "late_night_patterns"
        ],
        "features": [
            "Real-time Budget Monitoring",
            "Anomaly Detection",
            "Spending Analytics",
            "Transaction Recording",
            "Risk Assessment",
            "x402 Payment Integration"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)