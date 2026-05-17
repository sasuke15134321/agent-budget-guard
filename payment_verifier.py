#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment verification for x402 protocol v2
Verifies and settles payments via x402.org facilitator
"""

import base64
import json
import httpx
from typing import Optional

FACILITATOR_URL = "https://x402.org/facilitator"

# Payment requirements for /api/budget/check (0.03 USDC on Base mainnet)
_BASE_REQUIREMENTS = {
    "scheme": "exact",
    "network": "eip155:8453",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE",
    "maxTimeoutSeconds": 300,
    "extra": {"name": "USD Coin", "version": "2"},
}


def _decode_payment_header(payment_header: str) -> Optional[dict]:
    """Decode base64-encoded PAYMENT-SIGNATURE or X-PAYMENT header."""
    try:
        decoded = base64.b64decode(payment_header).decode("utf-8")
        return json.loads(decoded)
    except Exception:
        pass
    try:
        return json.loads(payment_header)
    except Exception:
        return None


class PaymentVerifier:
    def __init__(self):
        self.supported_networks = ["eip155:8453", "base", "base-mainnet"]
        self.supported_assets = {
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC"
        }

    async def verify_payment(
        self,
        payment_header: str,
        wallet_address: str,
        expected_amount: str,
    ) -> bool:
        """
        Verify and settle x402 v2 payment via x402.org facilitator.
        Falls back to legacy txHash-based verification for v1 payments.
        """
        payload = _decode_payment_header(payment_header)
        if payload is None:
            print("[WARN] Could not decode payment header")
            return False

        x402_version = payload.get("x402Version", 1)

        if x402_version == 2:
            return await self._verify_v2(payload, wallet_address, expected_amount)
        else:
            return self._verify_legacy(payload, wallet_address, expected_amount)

    async def _verify_v2(
        self,
        payload: dict,
        wallet_address: str,
        expected_amount: str,
    ) -> bool:
        """Verify x402 v2 payment via facilitator verify + settle."""
        amount_units = str(round(float(expected_amount) * 1_000_000))

        requirements = {
            **_BASE_REQUIREMENTS,
            "amount": amount_units,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: verify
                verify_resp = await client.post(
                    f"{FACILITATOR_URL}/verify",
                    json={"payload": payload, "paymentRequirements": requirements},
                )
                verify_data = verify_resp.json()
                print(f"[x402] verify status={verify_resp.status_code} valid={verify_data.get('isValid')}")

                if not verify_data.get("isValid"):
                    print(f"[WARN] Payment verification failed: {verify_data.get('invalidReason')}")
                    return False

                # Step 2: settle
                settle_resp = await client.post(
                    f"{FACILITATOR_URL}/settle",
                    json={"payload": payload, "paymentRequirements": requirements},
                )
                settle_data = settle_resp.json()
                print(f"[x402] settle status={settle_resp.status_code} success={settle_data.get('success')}")

                if settle_data.get("success"):
                    tx_hash = settle_data.get("txHash") or settle_data.get("transaction", {}).get("hash")
                    print(f"[OK] Payment settled: {expected_amount} USDC tx={tx_hash}")
                    return True
                else:
                    print(f"[WARN] Settlement failed: {settle_data.get('error')}")
                    return False

        except Exception as e:
            print(f"[ERROR] Facilitator call failed: {e}")
            return False

    def _verify_legacy(
        self,
        payment_data: dict,
        wallet_address: str,
        expected_amount: str,
    ) -> bool:
        """Legacy v1 verification (txHash-based)."""
        required_fields = ["amount", "asset", "network", "to", "txHash"]
        for field in required_fields:
            if field not in payment_data:
                print(f"[WARN] Missing required payment field: {field}")
                return False

        if payment_data["network"] not in self.supported_networks:
            print(f"[WARN] Unsupported network: {payment_data['network']}")
            return False

        if payment_data["asset"] not in self.supported_assets:
            print(f"[WARN] Unsupported asset: {payment_data['asset']}")
            return False

        if payment_data["to"].lower() != wallet_address.lower():
            print(f"[WARN] Payment recipient mismatch")
            return False

        expected_wei = int(float(expected_amount) * 1_000_000)
        if int(payment_data["amount"]) < expected_wei:
            print(f"[WARN] Insufficient payment amount")
            return False

        tx_hash = payment_data["txHash"]
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            print(f"[WARN] Invalid transaction hash format")
            return False

        print(f"[OK] Legacy payment verified: {int(payment_data['amount']) / 1_000_000} USDC")
        return True

    def generate_payment_request(
        self, wallet_address: str, amount: str, description: str, resource_url: str
    ) -> dict:
        amount_wei = int(float(amount) * 1_000_000)
        return {
            "x402Version": 2,
            "accepts": [{
                **_BASE_REQUIREMENTS,
                "amount": str(amount_wei),
                "resource": resource_url,
                "description": description,
                "mimeType": "application/json",
                "payTo": wallet_address,
            }]
        }
