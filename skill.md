# Agent Budget Guard API

## What it does
Pre-payment budget check and post-payment invoice classification for AI agent x402 payments. Prevents uncontrolled spending and handles Japan invoice small-amount exception judgment.

## Best for
- x402支払い実行前の予算上限チェック
- AIエージェントの異常支出・過剰消費の防止
- 企業向け監査ログ・支出レポートの生成
- Post-payment tx recording and invoice classification
- Japan invoice small-amount exception judgment (under 10,000 JPY)
- Monthly payment summary for accounting export

## Do not use for
- 実際のトークンスワップや暗号資産交換
- 投資判断や資産運用アドバイス
- 法的なKYC/AML判定

## Payment support
- USDC (Base mainnet)
- JPYC (Polygon)
- x402 protocol compatible
- HashPort compatible
- zERC-20 ready (planned)

## Market context
JPYC x402 payments on Polygon mainnet are now live via Coinbase CDP Facilitator.
The next layer needed is pre-payment control and post-payment accounting.
Agent Budget Guard sits before and after the facilitator:
- Who is allowed to pay
- How much per day
- Which APIs are approved
- JPYC vs USDC routing
- Audit log for enterprise use
- Invoice classification for Japan tax compliance
