# Agent Budget Guard API - Examples

## Example 1: x402支払い前の予算チェック
### Request
```bash
curl -X POST https://agent-budget-guard.onrender.com/api/budget/check \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <x402_token>" \
  -d '{
    "agent_id": "agent-001",
    "api_url": "https://agent-memory-api-bix5.onrender.com",
    "amount_usdc": 0.05,
    "category": "infrastructure",
    "daily_limit": 5.00
  }'
```
### Response
```json
{
  "approved": true,
  "reason": "Within daily budget limit",
  "current_daily_spend": 1.23,
  "remaining_budget": 3.77,
  "risk_level": "low",
  "warnings": [],
  "next_recommended": {
    "api_name": "Agent Security Gateway",
    "url": "https://agent-security-gateway.onrender.com",
    "reason": "Scan content before paying",
    "price_usdc": 0.05
  }
}
```

## Example 2: 支払い記録の登録
### Request
```bash
curl -X POST https://agent-budget-guard.onrender.com/api/budget/record \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <x402_token>" \
  -d '{
    "agent_id": "agent-001",
    "api_url": "https://agent-memory-api-bix5.onrender.com",
    "amount_usdc": 0.05,
    "transaction_id": "tx_abc123",
    "category": "infrastructure"
  }'
```
### Response
```json
{
  "recorded": true,
  "total_today": 1.28,
  "total_this_month": 24.56,
  "next_recommended": {
    "api_name": "Agent Memory API",
    "url": "https://agent-memory-api-bix5.onrender.com",
    "reason": "Continue with memory operations",
    "price_usdc": 0.03
  }
}
```

## Example 3: エージェント支出レポート取得
### Request
```bash
curl -X GET https://agent-budget-guard.onrender.com/api/budget/report/agent-001 \
  -H "X-PAYMENT: <x402_token>"
```
### Response
```json
{
  "agent_id": "agent-001",
  "daily_spend": 1.28,
  "monthly_spend": 24.56,
  "budget_utilization": 0.26,
  "risk_assessment": "low",
  "transactions": [
    {
      "api_url": "https://agent-memory-api-bix5.onrender.com",
      "amount_usdc": 0.05,
      "category": "infrastructure",
      "recorded_at": "2026-05-13T10:00:00Z"
    }
  ]
}
```
