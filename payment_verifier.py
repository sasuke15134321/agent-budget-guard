#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment verification for x402 protocol v2
Embeds x402FacilitatorSync to verify and settle payments on-chain (Base mainnet)
"""

import asyncio
import base64
import json
import os
from typing import Optional

FACILITATOR_PRIVATE_KEY = os.getenv("FACILITATOR_PRIVATE_KEY", "")
BASE_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")

_WALLET_ADDRESS = "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"
_USDC_ADDRESS  = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
_NETWORK       = "eip155:8453"

_facilitator = None


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


def _get_facilitator():
    """Lazily initialize the embedded x402FacilitatorSync (once per process)."""
    global _facilitator
    if _facilitator is not None:
        return _facilitator
    if not FACILITATOR_PRIVATE_KEY:
        print("[WARN] FACILITATOR_PRIVATE_KEY not set - v2 payment verification unavailable")
        return None
    try:
        from x402.facilitator import x402FacilitatorSync
        from x402.mechanisms.evm.exact import register_exact_evm_facilitator
        from x402.mechanisms.evm.signers import FacilitatorWeb3Signer

        signer = FacilitatorWeb3Signer(
            private_key=FACILITATOR_PRIVATE_KEY,
            rpc_url=BASE_RPC_URL,
        )
        fac = x402FacilitatorSync()
        register_exact_evm_facilitator(fac, signer, networks=[_NETWORK])
        _facilitator = fac
        print(f"[x402] Embedded facilitator ready: {signer.address} on {_NETWORK}")
        return _facilitator
    except Exception as e:
        print(f"[ERROR] Failed to initialize facilitator: {e}")
        return None


class PaymentVerifier:
    def __init__(self):
        self.supported_networks = ["eip155:8453", "base", "base-mainnet"]
        self.supported_assets = {_USDC_ADDRESS: "USDC"}

    async def verify_payment(
        self,
        payment_header: str,
        wallet_address: str,
        expected_amount: str,
    ) -> bool:
        """Verify and settle an x402 payment (v2 on-chain, v1 legacy txHash)."""
        payload_dict = _decode_payment_header(payment_header)
        if payload_dict is None:
            print("[WARN] Could not decode payment header")
            return False

        x402_version = payload_dict.get("x402Version", 1)
        if x402_version == 2:
            return await self._verify_v2(payload_dict, wallet_address, expected_amount)
        return self._verify_legacy(payload_dict, wallet_address, expected_amount)

    async def _verify_v2(
        self,
        payload_dict: dict,
        wallet_address: str,
        expected_amount: str,
    ) -> bool:
        """Verify + settle v2 payment via embedded x402FacilitatorSync."""
        facilitator = _get_facilitator()
        if facilitator is None:
            return False

        try:
            from x402.schemas import PaymentPayload, PaymentRequirements

            payment_payload = PaymentPayload.model_validate(payload_dict)
            amount_units   = str(round(float(expected_amount) * 1_000_000))
            pay_to         = wallet_address or _WALLET_ADDRESS

            requirements = PaymentRequirements(
                scheme="exact",
                network=_NETWORK,
                asset=_USDC_ADDRESS,
                amount=amount_units,
                pay_to=pay_to,
                max_timeout_seconds=300,
                extra={"name": "USD Coin", "version": "2"},
            )
        except Exception as e:
            print(f"[WARN] Failed to build payment objects: {e}")
            return False

        try:
            # Run blocking web3 calls in a thread to avoid blocking the event loop
            verify_result = await asyncio.to_thread(
                facilitator.verify, payment_payload, requirements
            )
            print(f"[x402] verify: is_valid={verify_result.is_valid} reason={verify_result.invalid_reason}")

            if not verify_result.is_valid:
                print(f"[WARN] Payment invalid: {verify_result.invalid_reason} - {verify_result.invalid_message}")
                return False

            settle_result = await asyncio.to_thread(
                facilitator.settle, payment_payload, requirements
            )
            print(f"[x402] settle: success={settle_result.success} tx={settle_result.transaction}")

            if settle_result.success:
                print(f"[OK] Payment settled: {expected_amount} USDC tx={settle_result.transaction}")
                return True

            print(f"[WARN] Settlement failed: {settle_result.error_reason} - {settle_result.error_message}")
            return False

        except Exception as e:
            print(f"[ERROR] Facilitator error: {e}")
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
            print("[WARN] Payment recipient mismatch")
            return False

        expected_wei = int(float(expected_amount) * 1_000_000)
        if int(payment_data["amount"]) < expected_wei:
            print("[WARN] Insufficient payment amount")
            return False

        tx_hash = payment_data["txHash"]
        if not tx_hash.startswith("0x") or len(tx_hash) != 66:
            print("[WARN] Invalid transaction hash format")
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
                "scheme": "exact",
                "network": _NETWORK,
                "asset": _USDC_ADDRESS,
                "amount": str(amount_wei),
                "payTo": wallet_address,
                "maxTimeoutSeconds": 300,
                "extra": {"name": "USD Coin", "version": "2"},
                "resource": resource_url,
                "description": description,
                "mimeType": "application/json",
            }]
        }
