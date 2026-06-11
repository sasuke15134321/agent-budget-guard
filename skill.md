# Agent Budget Guard Skill

Pre-payment control API for AI agents and machine wallets.
Use before autonomous payments via x402, USDC, or JPYC.

## Purpose
Use Agent Budget Guard before an AI agent calls a paid API or triggers an x402 / USDC / JPYC payment.

## When to use
- An AI agent is about to call a paid API
- An AI agent is about to trigger an x402 payment
- The user has a daily or monthly spending limit
- The agent needs approval before spending
- The system needs an audit record before payment

## When not to use
- Transfer tokens
- Hold funds
- Sign transactions
- Replace a wallet
- Process the actual payment

## Main endpoint
POST /api/budget/check (0.03 USDC)

## Example request
{
  "agent_id": "agent-demo-001",
  "amount": 0.05,
  "currency": "USDC",
  "purpose": "calling a paid x402 API",
  "daily_limit": 1.00
}

## Decision logic
- allowed: true -> Proceed to payment
- allowed: false -> Stop the payment flow
- requires_approval: true -> Ask for human approval

## Recommended flow
AI Agent -> Budget Guard -> Security Gateway -> x402 Payment -> Paid API -> Audit Log

Quick test: POST /api/budget/check with amount and daily_limit to verify pre-payment control.

## Skill: Agent Action Atom

### Use this when
- budget check before payment
- paid API call recording
- spending policy match or violation
- payment evidence attachment
- fuse allow / block / escalate decision
- human approval for high-value payment

### Do not use this as
- a payment protocol
- a wallet or settlement layer
- a legal liability engine
- a compliance guarantee
- an implemented API unless explicitly provided

### Minimal record fields
atom_id / actor / action / target / source / policy / meaning / state / proof / time / relation

### Purpose
Make one AI-agent action externally explainable and auditable, especially for budget control and payment safety flows.

### Important rule
Do not claim payment settlement from an Atom alone. Payment settlement requires attached evidence: facilitator verify log, facilitator settle log, transaction hash, onchain confirmation, wallet confirmation.
