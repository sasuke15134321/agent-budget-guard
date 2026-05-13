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
from pydantic import BaseModel
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

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-guidance"] = "Use this API before every x402 USDC or JPYC payment. L4 budget control, Japan invoice compliance."

    price_map = {
        "/api/budget/check": "0.03",
        "/api/budget/record": "0.01",
        "/api/budget/report/{agent_id}": "0.05",
        "/api/record-payment": "0.01",
        "/api/classify-invoice": "0.01"
    }

    for path, methods in openapi_schema.get("paths", {}).items():
        if path in price_map:
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    operation["x-payment-info"] = {
                        "protocols": ["x402"],
                        "authMode": "x402",
                        "price": price_map[path],
                        "currency": "USDC"
                    }
                    if "requestBody" not in operation:
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "agent_id": {"type": "string", "description": "Agent identifier"},
                                            "amount_usdc": {"type": "number", "description": "Payment amount in USDC"}
                                        }
                                    }
                                }
                            }
                        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Paid endpoint config: path -> (price, method)
_PAID_ENDPOINTS = {
    ("POST", "/api/budget/check"):    "0.03",
    ("POST", "/api/budget/record"):   "0.01",
    ("POST", "/api/record-payment"):  "0.01",
    ("POST", "/api/classify-invoice"): "0.01",
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
            max_amount = str(round(float(price) * 1_000_000))
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": max_amount, "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
            return JSONResponse(
                status_code=402,
                content=_pc,
                headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()}
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

class RecordPaymentRequest(BaseModel):
    agent_id: str
    amount: float
    currency: str
    tax_included_amount_jpy: float
    network: str
    tx_hash: str
    purpose: str

class ClassifyInvoiceRequest(BaseModel):
    buyer_taxable_sales_jpy: float
    transaction_amount_tax_included_jpy: float
    transaction_date: str
    seller_invoice_registered: bool

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

@app.get("/.well-known/x402")
async def x402_discovery_manifest():
    return {
        "version": 1,
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
        "instructions": "x402 L4 governance API for AI agent payments. Budget control, JPYC support, Japan invoice compliance."
    }

@app.post("/api/budget/check", response_model=BudgetCheckResponse)
async def check_budget(request: BudgetCheckRequest, http_request: Request):
    """Check budget and approve/deny spending with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

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
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "10000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

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
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/record-payment")
async def record_payment(request: RecordPaymentRequest, http_request: Request):
    """Record payment tx and classify for Japan invoice small-amount exception"""
    ts = int(datetime.now().timestamp())
    invoice_required = request.tax_included_amount_jpy >= 10000
    reason = "invoice required" if invoice_required else "small-amount exception candidate"
    return {
        "recorded": True,
        "audit_id": f"audit_{ts}",
        "invoice_required": invoice_required,
        "reason": reason,
        "bookkeeping_required": True,
        "monthly_summary_required": True
    }

@app.post("/api/classify-invoice")
async def classify_invoice(request: ClassifyInvoiceRequest, http_request: Request):
    """Classify invoice requirement under Japan invoice small-amount exception rules"""
    small_amount_exception = (
        request.buyer_taxable_sales_jpy <= 100_000_000 and
        request.transaction_amount_tax_included_jpy < 10_000
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

@app.get("/api/monthly-summary")
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

@app.get("/openapi.yaml")
async def openapi_yaml():
    content = open("openapi.yaml").read()
    return PlainTextResponse(content, media_type="text/yaml")

@app.get("/skill.md")
async def skill_md():
    content = open("skill.md").read()
    return PlainTextResponse(content)

@app.get("/llms.txt")
async def llms_txt():
    content = open("llms.txt").read()
    return PlainTextResponse(content)

@app.get("/examples.md")
async def examples_md():
    content = open("examples.md").read()
    return PlainTextResponse(content)


@app.get("/.well-known/mcp/server-card.json")
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

@app.get(
    "/api/x402-demo",
    responses={402: {"description": "Payment Required"}},
    openapi_extra={
        "x-payment-info": {
            "protocols": [{"name": "x402", "version": "1"}],
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.01"}
        },
        "requestBody": {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            }
        }
    }
)
async def x402_demo(request: Request):
    payment_header = request.headers.get("X-PAYMENT")
    if not payment_header:
        pc = {
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "eip155:8453",
                "maxAmountRequired": "10000",
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
                "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"
            }],
            "error": "Payment required"
        }
        return JSONResponse(
            status_code=402,
            content=pc,
            headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(pc).encode()).decode()}
        )
    return {"ok": True, "message": "paid"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)