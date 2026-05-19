# Agent Budget Guard Skill

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
POST /api/budget/check

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
