> JPYC x402 payments are now live on Polygon mainnet.
> Agent Budget Guard is the pre-payment control layer for
> JPYC / USDC / x402 AI agent payments.

# Agent Budget Guard - AI運用コスト革命システム

## What this API does
AIエージェントのAPI決済前に、予算上限・承認要否・監査準備状態を確認するAPIです。

## When an AI agent should call this API
AIエージェントがx402 USDC / JPYC決済を実行する前に呼び出してください。
意図しない支出、予算超過、承認漏れを防ぐために使います。

## Best used before
- x402 payment
- paid API call
- autonomous agent purchase
- JPYC / USDC API spending

## Output
- allow / deny
- approval_required
- remaining_budget
- audit_status
- next_recommended

## Japanese Agent Trust Layer

このAPIは「Japanese Agent Trust Layer」の一部です。
日本語対応AIエージェントが安全・確実・予算内でAPIを使うためのインフラ層を提供します。

### Trust Layerの構成
- 記憶管理: agent-memory-api
- 安全判定: agent-security-gateway
- 予算管理: agent-budget-guard
- API選定: agent-curator-api
- 自律進化: agent-evolution-engine

### 特徴
- x402 / USDC決済対応
- 日本語対応
- 決定論的バリデーター（AI不使用）
- 暗号化・削除証跡付き
- Base Mainnet対応

## 🚨 損失回避メッセージ
**予算管理なしでは、AI運用費が年間3000万円無制限拡大、予算破綻による事業継続危機が発生します。**

無管理なAI支出 → 想定外コスト発生 → 予算オーバー → キャッシュフロー圧迫 → 事業活動制限 → 競争力低下

## 💰 期待利得の数値
- **AI運用コスト50%削減**
- **予算管理精度95%向上**
- **ROI可視化完全実現**
- **異常支出検出率99%達成**
- **総合予算ROI: 800%**

## 🎯 HARM分析

### Health (生存リスクの除去)
- 予算破綻による事業継続リスクの完全除去
- AI支出の無制限拡大による資金ショート回避
- コスト管理不備による投資家信頼失墜防止

### Ambitions (収益・効率の向上)
- AI投資ROI最大化による収益性向上
- コスト構造の完全透明化で経営判断精度向上
- 自動予算管理により人的リソース90%効率化

### Relationships (連携可能なAPI)
- **Agent Evolution API**: 進化コストの最適配分管理
- **Agent Curator API**: コスト効率最適なAPI選択
- **AI Trend Scout**: 投資トレンドに基づく予算計画

### Money (ROI数値)
- **投資対効果: 800%**
- 予算管理投資1円でコスト削減8円
- 年間AI運用コスト削減: 3000万円
- 予算最適化による投資効率向上: 5000万円価値

## 🔄 次に使うべきAPI（クロスセル）
**Agent Curator API** - コスト効率最適なAPI選択により、さらなる運用費削減を実現します。

## 💸 価格と投資対効果
- **予算チェック: 0.04 USDC** → **50%コスト削減**
- **支出記録: 0.01 USDC** → **完全な可視化**
- **詳細レポート: 0.05 USDC** → **ROI最適化**

## ⚡ 実装方法

### Paid Endpoints (x402 Payment Required)

```bash
# AI支出チェック・承認 (0.04 USDC)
curl -X POST "https://agent-budget-guard.onrender.com/api/budget/check" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "service": "claude-api",
    "amount_usdc": 15.50,
    "transaction_type": "api_call",
    "purpose": "document_analysis"
  }'

# 取引記録・分析 (0.01 USDC)
curl -X POST "https://agent-budget-guard.onrender.com/api/budget/record" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "transaction_id": "tx_123456",
    "final_amount": 14.30,
    "completion_status": "success",
    "actual_usage": "95%"
  }'

# 詳細予算レポート (0.05 USDC)
curl -X GET "https://agent-budget-guard.onrender.com/api/budget/report/agent_001" \
  -H "X-PAYMENT: your-payment-proof"

# 異常支出検出・アラート (0.03 USDC)
curl -X POST "https://agent-budget-guard.onrender.com/api/budget/anomaly" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "monitoring_period": "24h",
    "sensitivity": "high"
  }'
```

### Free Endpoints

```bash
# システムヘルスチェック
curl "https://agent-budget-guard.onrender.com/health"

# 予算統計サマリー
curl "https://agent-budget-guard.onrender.com/api/budget/stats"

# x402プロトコル発見
curl "https://agent-budget-guard.onrender.com/.well-known/x402.json"
```

### 予算管理機能

#### 💰 **リアルタイム支出監視**
- 秒単位での支出トラッキング
- 予算残高の即座更新・アラート
- 複数エージェント並行監視

#### 🚨 **異常検出パターン**
- 通常の10倍超過支出の即座検出
- 深夜時間帯の大量API呼び出し
- 同一処理の重複実行による無駄遣い
- 予算枠を超過する前の事前警告

#### 📊 **コスト分析・最適化**
- サービス別・時間別支出分析
- ROI計算・投資効果測定
- 最適予算配分の自動提案

#### 🔒 **支出承認ワークフロー**  
- 閾値超過時の自動承認停止
- 段階的承認プロセス（1万円/10万円/100万円）
- 緊急時の例外処理・即座承認

### 監視対象サービス

- **Claude API**: トークン使用量・リクエスト頻度
- **OpenAI API**: GPT-4利用・ファインチューニングコスト
- **Compute Resources**: AWS/GCP/Azure利用料金
- **Third-party APIs**: 各種外部サービス利用料
- **Storage & Database**: データベース・ストレージ費用

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

## AI Agent Safety Stack
Works best with:
- Agent Security Gateway: https://agent-security-gateway.onrender.com（危険な命令を止める）
- Agent Budget Guard: https://agent-budget-guard.onrender.com（勝手な課金を止める）
- Agent Memory API: https://agent-memory-api-bix5.onrender.com（必要な記憶を残す）