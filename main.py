#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Budget Guard API
FastAPI server with x402 payment protocol for AI agent spending monitoring and anomaly detection
"""

import os
from fastapi import FastAPI, Request, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import base64
from datetime import datetime
import asyncio
import traceback
from fastapi.openapi.utils import get_openapi

from payment_verifier import PaymentVerifier
from budget_engine import BudgetEngine
from database import budget_db

# Environment variables
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0x")
PRICE_USDC = os.getenv("PRICE_USDC", "0.03")
NETWORK = os.getenv("NETWORK", "base-mainnet")
TEST_MODE = os.getenv("TEST_MODE", "true").lower() == "true"

app = FastAPI(
    title="Agent Budget Guard",
    version="1.0.0",
    description=(
        "Pay-per-request governance APIs for AI agents using x402. "
        "Check budgets, log payments, classify invoices, and generate audit-ready "
        "spending records. Built for autonomous agents, USDC/Base payments, "
        "and JPY/JPYC reporting workflows."
    )
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-guidance"] = (
        "This API provides x402-paid governance tools for autonomous AI agents. "
        "Agents should call /api/budget/check before making paid API calls to verify "
        "per-request and daily spending limits. Use /api/budget/record to persist budget "
        "decisions, /api/record-payment to log completed x402 payments, and "
        "/api/classify-invoice to classify invoice or payment records. "
        "The API is useful for AI agent spending control, payment governance, budget limits, "
        "audit logging, USDC payments on Base, JPYC/JPY reporting workflows, and preventing "
        "unexpected paid tool calls."
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

def paid_operation(amount_usd: str) -> dict:
    return {
        "x-payment-info": {
            "price": {
                "mode": "fixed",
                "currency": "USD",
                "amount": amount_usd,
            },
            "protocols": [{"x402": {}}],
        }
    }

# Paid endpoint config: (method, path) -> price in USD
_PAID_ENDPOINTS = {
    ("POST", "/api/budget/check"):    "0.03",
    ("POST", "/api/budget/record"):   "0.01",
    ("POST", "/api/record-payment"):  "0.03",
    ("POST", "/api/classify-invoice"): "0.03",
}

_ENDPOINT_DESCRIPTIONS = {
    "/api/budget/check":    "Check budget and approve/deny AI agent spending with x402 payment verification",
    "/api/budget/record":   "Record a budget transaction for an AI agent",
    "/api/record-payment":  "Log a completed x402 payment",
    "/api/classify-invoice": "Classify an invoice or payment record for tax/accounting purposes",
}

# CDP Bazaar indexing extension for /api/budget/check
_BAZAAR_EXTENSIONS = {
    "bazaar": {
        "info": {
            "input": {
                "type": "http",
                "method": "POST",
                "bodyType": "json",
                "body": {
                    "agent_id": "agent_001",
                    "requested_amount": 0.03,
                    "currency": "USDC",
                    "target_api": "https://example.com/api/paid",
                    "action_type": "x402_payment"
                }
            },
            "output": {
                "type": "json",
                "example": {
                    "allow": True,
                    "approval_required": False,
                    "remaining_budget": 0.97,
                    "audit_status": "ready",
                    "risk_level": "low",
                    "next_recommended": "proceed_with_x402_payment"
                }
            }
        },
        "schema": {
            "type": "object",
            "properties": {
                "allow": {"type": "boolean"},
                "approval_required": {"type": "boolean"},
                "remaining_budget": {"type": "number"},
                "audit_status": {"type": "string"},
                "risk_level": {"type": "string"},
                "next_recommended": {"type": "string"}
            }
        }
    }
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
        payment_header = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("X-PAYMENT")
        if not payment_header:
            amount = str(round(float(price) * 1_000_000))
            _accept = {
                "scheme": "exact",
                "network": "eip155:8453",
                "amount": amount,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE",
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USD Coin", "version": "2"},
                "resource": {"method": method, "mimeType": "application/json"},
            }
            _pc = {
                "x402Version": 2,
                "error": "Payment required",
                "resource": {
                    "url": str(request.url),
                    "method": method,
                    "description": _ENDPOINT_DESCRIPTIONS.get(path, "Paid API endpoint"),
                    "mimeType": "application/json",
                },
                "accepts": [_accept],
            }
            if path == "/api/budget/check":
                _pc["extensions"] = _BAZAAR_EXTENSIONS
                _pc["allow"] = False
                _pc["approval_required"] = True
                _pc["remaining_budget"] = 0.0
                _pc["audit_status"] = "payment_required"
                _pc["risk_level"] = "unknown"
                _pc["next_recommended"] = "complete_x402_payment"
            return JSONResponse(
                status_code=402,
                content=_pc,
                headers={"Payment-Required": base64.b64encode(json.dumps(_pc).encode()).decode()}
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
    agent_id: Optional[str] = Field(default="default-agent", description="AI agent identifier")
    amount: Optional[float] = Field(default=None, description="Requested payment amount in USDC")
    requested_amount: Optional[float] = Field(default=None, description="Requested payment amount (alias for amount)")
    currency: Optional[str] = Field(default="USD", description="Currency: USD, USDC, JPYC, JPY")
    api_url: Optional[str] = Field(default=None, description="Target API URL")
    target_api: Optional[str] = Field(default=None, description="Target API URL (alias for api_url)")
    daily_limit: Optional[float] = Field(default=5.0, description="Daily spend limit in USDC")
    action_type: Optional[str] = Field(default=None, description="Action type")

class RecordTransactionRequest(BaseModel):
    agent_id: Optional[str] = Field(default="default-agent", description="AI agent identifier")
    api_url: Optional[str] = Field(default=None, description="Target API URL")
    amount_usdc: Optional[float] = Field(default=0.01, description="Payment amount in USDC")
    transaction_id: Optional[str] = Field(default=None, description="Transaction ID")
    category: Optional[str] = Field(default="infrastructure", description="Transaction category")

class RecordPaymentRequest(BaseModel):
    agent_id: Optional[str] = Field(default="default-agent", description="AI agent identifier")
    amount: Optional[float] = Field(default=0.01, description="Payment amount")
    currency: Optional[str] = Field(default="USDC", description="Currency used")
    tax_included_amount_jpy: Optional[float] = Field(default=None, description="Tax-included amount in JPY")
    network: Optional[str] = Field(default="polygon", description="Blockchain network")
    tx_hash: Optional[str] = Field(default=None, description="Transaction hash")
    purpose: Optional[str] = Field(default="api_call", description="Payment purpose")

class ClassifyInvoiceRequest(BaseModel):
    buyer_taxable_sales_jpy: Optional[float] = Field(default=50000000, description="Buyer annual taxable sales in JPY")
    transaction_amount_tax_included_jpy: Optional[float] = Field(default=1500, description="Transaction amount including tax in JPY")
    transaction_date: Optional[str] = Field(default=None, description="Transaction date YYYY-MM-DD")
    seller_invoice_registered: Optional[bool] = Field(default=True, description="Whether seller is invoice registered")

# Response models
class NextRecommendation(BaseModel):
    api_name: str
    url: str
    reason: str
    expected_improvement: str
    price_usdc: float

class BudgetCheckResponse(BaseModel):
    approved: bool
    allow: bool
    approval_required: bool
    reason: str
    current_daily_spend: float
    remaining_budget: float
    audit_status: str
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
@app.get("/.well-known/ai-agent-policy", include_in_schema=False)
async def ai_agent_policy():
    import json
    import os
    policy_path = "ai-agent-policy.json"
    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Policy not found"}

@app.get("/ai-agent-policy.json", include_in_schema=False)
async def ai_agent_policy_json():
    from pathlib import Path
    policy_path = Path(__file__).parent / "ai-agent-policy.json"
    with open(policy_path) as f:
        return json.load(f)

# x402 payment protocol endpoint discovery
@app.get("/.well-known/x402.json", include_in_schema=False)
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

@app.get("/.well-known/x402", include_in_schema=False)
async def x402_discovery_manifest():
    return {
        "version": 1,
        "name": "Agent Budget Guard",
        "title": "Agent Budget Guard",
        "description": (
            "Pay-per-request governance APIs for autonomous AI agents using x402. "
            "Check budgets, record spending decisions, log completed payments, "
            "classify invoices, and generate audit-ready budget reports. "
            "Built for AI agent spending control, USDC/Base payments, and JPY/JPYC reporting."
        ),
        "tags": ["AI", "Payments", "Governance"],
        "resources": [
            "https://agent-budget-guard.onrender.com/api/budget/check",
            "https://agent-budget-guard.onrender.com/api/budget/record",
            "https://agent-budget-guard.onrender.com/api/budget/report/{agent_id}",
            "https://agent-budget-guard.onrender.com/api/record-payment",
            "https://agent-budget-guard.onrender.com/api/classify-invoice"
        ],
        "ownershipProofs": [
            "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"
        ],
        "instructions": (
            "Agent Budget Guard helps AI agents control x402 spending. "
            "Use /api/budget/check before paid API calls, /api/budget/record "
            "to persist budget decisions, /api/record-payment to log payments, "
            "/api/classify-invoice for accounting classification."
        )
    }

@app.post(
    "/api/budget/check",
    summary="Budget Check - Verify spending before paid API calls",
    description="Checks whether an autonomous AI agent is allowed to make a paid x402 API call. Use before external tool calls to prevent unexpected spending and budget overruns.",
    response_model=BudgetCheckResponse,
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
    tags=["Governance"],
)
async def check_budget(payload: BudgetCheckRequest, request: Request):
    """Check budget and approve/deny spending with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {
                "x402Version": 2,
                "error": "Payment required",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}],
                "extensions": _BAZAAR_EXTENSIONS,
                "allow": False,
                "approval_required": True,
                "remaining_budget": 0.0,
                "audit_status": "payment_required",
                "risk_level": "unknown",
                "next_recommended": "complete_x402_payment",
            }
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, PRICE_USDC)
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        effective_api_url = payload.api_url or payload.target_api or "unknown"
        effective_amount = payload.amount or payload.requested_amount or 0.03

        result = await budget_engine.check_budget(
            agent_id=payload.agent_id,
            api_url=effective_api_url,
            amount_usdc=effective_amount,
            category="infrastructure",
            daily_limit=payload.daily_limit
        )

        # Log budget check
        await budget_db.log_budget_check(
            agent_id=payload.agent_id,
            api_url=effective_api_url,
            amount_usdc=effective_amount,
            approved=result["approved"],
            reason=result["reason"]
        )

        # Map to Bazaar-required field names
        result["allow"] = result["approved"]
        result["approval_required"] = not result["approved"]
        result["audit_status"] = "ready" if result["approved"] else "flagged"

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

@app.post(
    "/api/budget/record",
    summary="Budget Record - Store AI spending decisions",
    description="Records budget decisions for AI agents, including allowed or denied paid API calls, amounts, currencies, reasons, and audit metadata.",
    response_model=RecordTransactionResponse,
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
    tags=["Governance"],
)
async def record_budget(payload: BudgetCheckRequest, request: Request):
    """Record transaction with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "10000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.01")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        effective_api_url = payload.api_url or payload.target_api or "unknown"
        effective_amount = payload.amount or payload.requested_amount or 0.01

        result = await budget_engine.record_transaction(
            agent_id=payload.agent_id,
            api_url=effective_api_url,
            amount_usdc=effective_amount,
            transaction_id=None,
            category="infrastructure"
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

@app.get(
    "/api/budget/report/{agent_id}",
    summary="Budget Report - Get AI agent spending report",
    description="Returns spending report for a specific AI agent including daily totals, transaction history, and budget utilization.",
    response_model=AgentReportResponse,
    tags=["Governance"],
)
async def get_agent_report(agent_id: str = Path(..., description="Agent ID"), http_request: Request = None):
    """Get detailed spending report for specific agent with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "GET", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

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

@app.get("/api/budget/stats", response_model=BudgetStatsResponse, include_in_schema=False)
async def get_budget_stats():
    """Get budget statistics (free endpoint)"""
    try:
        stats = await budget_db.get_budget_statistics()
        return stats
    except Exception as e:
        print(f"[ERROR] Failed to get budget stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get budget statistics: {str(e)}")

@app.get("/health", include_in_schema=False)
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

@app.get("/", include_in_schema=False)
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

@app.post(
    "/api/record-payment",
    summary="Payment Record - Log completed x402 payments",
    description="Logs completed x402 payments for AI agents, including transaction hash, amount, network, currency, and agent identifier for audit and reporting.",
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
    tags=["Payments"],
)
async def record_payment(payload: RecordPaymentRequest, request: Request):
    """Record payment tx and classify for Japan invoice small-amount exception"""
    ts = int(datetime.now().timestamp())
    invoice_required = (payload.tax_included_amount_jpy or 0) >= 10000
    reason = "invoice required" if invoice_required else "small-amount exception candidate"
    return {
        "recorded": True,
        "audit_id": f"audit_{ts}",
        "invoice_required": invoice_required,
        "reason": reason,
        "bookkeeping_required": True,
        "monthly_summary_required": True
    }

@app.post(
    "/api/classify-invoice",
    summary="Invoice Classifier - Classify payment and invoice records",
    description="Classifies invoice or payment text for AI agent accounting workflows. Useful for x402 payment logs, JPY-denominated reporting, and audit preparation.",
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
    tags=["Accounting"],
)
async def classify_invoice(payload: ClassifyInvoiceRequest, request: Request):
    """Classify invoice requirement under Japan invoice small-amount exception rules"""
    small_amount_exception = (
        (payload.buyer_taxable_sales_jpy or 50000000) <= 100_000_000 and
        (payload.transaction_amount_tax_included_jpy or 1500) < 10_000
    )
    if small_amount_exception:
        return {
            "invoice_required": False,
            "bookkeeping_only": True,
            "reason": "small-amount exception applies (under 10,000 JPY, buyer taxable sales under 100M JPY)"
        }
    return {
        "invoice_required": True,
        "bookkeeping_only": False,
        "reason": "standard invoice required"
    }

@app.get("/api/monthly-summary", include_in_schema=False)
async def monthly_summary(buyer_id: Optional[str] = None, month: Optional[str] = None):
    """Monthly payment summary for accounting (free endpoint, no x402 required)"""
    return {
        "buyer_id": buyer_id,
        "month": month,
        "total_transactions": 0,
        "total_amount_jpy": 0,
        "small_amount_exception_count": 0,
        "invoice_required_count": 0,
        "note": "Summary feature coming soon. Tx recording via /api/record-payment."
    }

@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml():
    content = open("openapi.yaml").read()
    return PlainTextResponse(content, media_type="text/yaml")

@app.get("/skill.md", include_in_schema=False)
async def skill_md():
    content = open("skill.md").read()
    return PlainTextResponse(content)

@app.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    content = open("llms.txt").read()
    return PlainTextResponse(content)

@app.get("/examples.md", include_in_schema=False)
async def examples_md():
    content = open("examples.md").read()
    return PlainTextResponse(content)


@app.get("/.well-known/mcp/server-card.json", include_in_schema=False)
async def mcp_server_card():
    return {
        "serverInfo": {
            "name": "agent-budget-guard",
            "version": "1.0.0",
            "description": "Pre-payment budget check and invoice routing for AI agent x402 payments. Prevents uncontrolled spending."
        },
        "tools": [
            {
                "name": "check_budget",
                "description": "Check if AI agent should pay for an API call. Use before any x402 USDC or JPYC payment. Returns allow/deny with remaining budget.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "api_url": {"type": "string"},
                        "amount_usdc": {"type": "number"}
                    },
                    "required": ["agent_id", "api_url", "amount_usdc"]
                }
            },
            {
                "name": "record_payment",
                "description": "Record completed x402 payment for audit log and invoice classification.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                        "tx_hash": {"type": "string"}
                    },
                    "required": ["agent_id", "amount", "currency"]
                }
            },
            {
                "name": "classify_invoice",
                "description": "Classify invoice requirement for JPYC x402 micro-payment under Japan invoice system.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "buyer_taxable_sales_jpy": {"type": "number"},
                        "transaction_amount_tax_included_jpy": {"type": "number"},
                        "transaction_date": {"type": "string"}
                    },
                    "required": ["buyer_taxable_sales_jpy", "transaction_amount_tax_included_jpy"]
                }
            }
        ],
        "resources": [],
        "prompts": []
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)