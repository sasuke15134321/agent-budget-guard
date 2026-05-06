# Agent Budget Guard API

AI agent spending monitoring and anomaly detection service with x402 payment protocol integration.

## Features

- **Budget Monitoring**: Real-time spending tracking and budget enforcement
- **Anomaly Detection**: Advanced pattern recognition for suspicious spending behavior
- **Transaction Recording**: Comprehensive transaction logging and analysis
- **Agent Reports**: Detailed spending analytics and risk assessment
- **x402 Payment Protocol**: Cryptocurrency payment integration (USDC on Base network)
- **PostgreSQL Database**: Persistent storage for budget rules, transactions, and alerts

## API Endpoints

### Paid Endpoints (x402 Payment Required)

- **POST /api/budget/check** (0.03 USDC) - Check spending approval and detect anomalies
- **POST /api/budget/record** (0.01 USDC) - Record completed transactions
- **GET /api/budget/report/{agent_id}** (0.05 USDC) - Detailed agent spending report

### Free Endpoints

- **GET /api/budget/stats** - Budget statistics and anomaly overview
- **GET /health** - Health check
- **GET /.well-known/x402.json** - x402 protocol discovery

## Anomaly Detection Patterns

The API automatically detects the following suspicious spending patterns:

- **Repeated API Payments** - Same API called 5+ times within an hour
- **Daily Limit Exceeded** - Spending above configured daily limits
- **Sudden High Payments** - Payments significantly higher than historical average
- **Unknown API Payments** - First-time payments to unrecognized APIs
- **Late Night Patterns** - Unusual spending during 11 PM - 6 AM hours

## Installation

1. Clone repository:
```bash
git clone <repository-url>
cd agent_budget_api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize database:
```bash
# Ensure PostgreSQL is running
python -c "from database import budget_db; import asyncio; asyncio.run(budget_db.initialize())"
```

5. Run server:
```bash
python main.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Anthropic API key (optional) | - |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `WALLET_ADDRESS` | x402 payment recipient wallet | Required |
| `NETWORK` | Blockchain network | base-mainnet |
| `PRICE_USDC` | Price per budget check in USDC | 0.03 |
| `DEFAULT_DAILY_LIMIT` | Default daily spending limit | 5.00 |
| `DEFAULT_MONTHLY_LIMIT` | Default monthly spending limit | 150.00 |
| `TEST_MODE` | Skip payment verification | true |
| `PORT` | Server port | 8000 |

## Database Schema

### budget_rules
- Agent-specific budget configuration
- Daily and monthly spending limits
- Category-specific limits

### transactions
- Complete transaction history
- API URLs, amounts, categories
- Transaction IDs and timestamps

### alerts
- Anomaly detection alerts
- Alert types, severity levels
- Metadata for analysis

### budget_checks
- Budget check request logs
- Approval/denial decisions
- Reason tracking

## Usage Examples

### Budget Check
```bash
curl -X POST "http://localhost:8000/api/budget/check" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "agent_id": "agent-001",
    "api_url": "https://api.openai.com/v1/chat/completions",
    "amount_usdc": 0.20,
    "category": "infrastructure",
    "daily_limit": 5.00
  }'
```

Response:
```json
{
  "approved": true,
  "reason": "Budget check passed",
  "current_daily_spend": 1.20,
  "remaining_budget": 3.80,
  "risk_level": "low",
  "warnings": []
}
```

### Record Transaction
```bash
curl -X POST "http://localhost:8000/api/budget/record" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "agent_id": "agent-001",
    "api_url": "https://api.openai.com/v1/chat/completions",
    "amount_usdc": 0.20,
    "transaction_id": "0xabc123...",
    "category": "infrastructure"
  }'
```

Response:
```json
{
  "recorded": true,
  "total_today": 1.40,
  "total_this_month": 12.50
}
```

### Agent Report
```bash
curl -X GET "http://localhost:8000/api/budget/report/agent-001" \
  -H "X-PAYMENT: {payment_data}"
```

Response:
```json
{
  "agent_id": "agent-001",
  "daily_spend": 1.40,
  "monthly_spend": 12.50,
  "daily_limit": 5.00,
  "monthly_limit": 150.00,
  "transactions": [
    {
      "api_url": "https://api.openai.com/v1/chat/completions",
      "amount_usdc": 0.20,
      "category": "infrastructure",
      "timestamp": "2024-01-15T14:30:00",
      "transaction_id": "0xabc123..."
    }
  ],
  "budget_utilization": 28.0,
  "risk_assessment": "low",
  "recent_alerts": 0,
  "spending_patterns": {
    "top_categories": {"infrastructure": 1.20, "consulting": 0.20},
    "top_apis": {"api.openai.com": 1.20},
    "peak_hours": {14: 3, 10: 2, 16: 1}
  }
}
```

### Budget Statistics
```bash
curl -X GET "http://localhost:8000/api/budget/stats"
```

## Anomaly Detection Examples

### Repeated Payments Alert
```json
{
  "warnings": [
    "CRITICAL: 5 payments to same API in last hour"
  ]
}
```

### High Value Payment Alert
```json
{
  "warnings": [
    "HIGH: Payment 2.50 USDC is 3x higher than usual (0.80 USDC)"
  ]
}
```

### Unknown API Alert
```json
{
  "warnings": [
    "MEDIUM: First payment to unknown API domain: new-api.com"
  ]
}
```

## Risk Assessment

### Risk Levels
- **Low (0-50% of budget)**: Normal spending patterns
- **Medium (50-80% of budget)**: Elevated spending, monitoring recommended
- **High (80%+ of budget)**: High spending, immediate attention required

### Anomaly Severity
- **LOW**: Informational alerts, no action required
- **MEDIUM**: Warning alerts, monitoring recommended
- **HIGH**: Critical alerts, may block transactions
- **CRITICAL**: Severe anomalies, transactions blocked

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  PostgreSQL     │
│   Main Server   │◄──►│   Database      │
└─────────┬───────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│ Payment         │    │  Budget         │
│ Verifier        │    │  Engine         │
└─────────────────┘    └─────────┬───────┘
                                 │
          ┌─────────────────┐    │
          │  Anomaly        │    │
          │  Detection      │◄───┤
          └─────────────────┘    │
                                 │
          ┌─────────────────┐    │
          │  Risk           │    │
          │  Assessment     │◄───┘
          └─────────────────┘
```

## Monitoring Features

- **Real-time Spending Tracking**: Live budget utilization monitoring
- **Pattern Analysis**: Historical spending pattern recognition
- **Alert System**: Automated anomaly notifications
- **Risk Scoring**: Dynamic risk level assessment
- **Reporting**: Comprehensive agent spending analytics

## Integration Examples

### Budget-Aware Agent
```python
import httpx

class BudgetAwareAgent:
    def __init__(self, agent_id, budget_api_url):
        self.agent_id = agent_id
        self.budget_api_url = budget_api_url
    
    async def make_api_call(self, api_url, amount):
        # Check budget first
        check_response = await self.check_budget(api_url, amount)
        
        if not check_response["approved"]:
            raise Exception(f"Budget check failed: {check_response['reason']}")
        
        # Make the actual API call
        result = await self.call_external_api(api_url)
        
        # Record the transaction
        await self.record_transaction(api_url, amount, result["tx_id"])
        
        return result
```

## Development

### Testing
```bash
# Set TEST_MODE=true in .env to skip payment verification
export TEST_MODE=true
python main.py
```

### Database Management
```bash
# Initialize database
python -c "from database import budget_db; import asyncio; asyncio.run(budget_db.initialize())"

# Test connection
python -c "from database import budget_db; import asyncio; print(asyncio.run(budget_db.test_connection()))"
```

## Deployment

### Render Deployment
1. Connect GitHub repository to Render
2. Create new Web Service
3. Configure environment variables
4. Deploy automatically on push

### Environment Configuration
- Set `DATABASE_URL` to your PostgreSQL instance
- Set `WALLET_ADDRESS` to your payment wallet
- Set `TEST_MODE=false` for production
- Configure budget limits as needed

## Security

- Input validation and sanitization
- Payment verification and replay protection
- Database connection security
- Anomaly detection and blocking
- Comprehensive audit logging

## Use Cases

- **AI Agent Budget Management**: Monitor and control AI agent spending
- **Cost Optimization**: Identify spending inefficiencies and patterns
- **Fraud Detection**: Detect suspicious payment behaviors
- **Compliance Monitoring**: Ensure spending within approved limits
- **Risk Management**: Assess and mitigate financial risks

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please create an issue in the GitHub repository.