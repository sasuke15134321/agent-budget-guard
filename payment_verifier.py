#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Payment verification for x402 protocol
Handles USDC payment validation on Base network
"""

import json
import hashlib
import hmac
from typing import Optional


class PaymentVerifier:
    def __init__(self):
        self.supported_networks = ["base", "base-mainnet"]
        self.supported_assets = {
            "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913": "USDC"  # USDC on Base
        }

    async def verify_payment(self, payment_header: str, wallet_address: str, expected_amount: str) -> bool:
        """
        Verify x402 payment header

        Args:
            payment_header: X-PAYMENT header value
            wallet_address: Expected recipient wallet address
            expected_amount: Expected payment amount in USDC

        Returns:
            bool: True if payment is valid
        """
        try:
            # Parse payment header
            payment_data = json.loads(payment_header)

            # Basic validation
            if not isinstance(payment_data, dict):
                print("[WARN] Invalid payment data format")
                return False

            # Check required fields
            required_fields = ["amount", "asset", "network", "to", "txHash"]
            for field in required_fields:
                if field not in payment_data:
                    print(f"[WARN] Missing required payment field: {field}")
                    return False

            # Validate network
            if payment_data["network"] not in self.supported_networks:
                print(f"[WARN] Unsupported network: {payment_data['network']}")
                return False

            # Validate asset
            if payment_data["asset"] not in self.supported_assets:
                print(f"[WARN] Unsupported asset: {payment_data['asset']}")
                return False

            # Validate recipient address
            if payment_data["to"].lower() != wallet_address.lower():
                print(f"[WARN] Payment recipient mismatch: {payment_data['to']} != {wallet_address}")
                return False

            # Validate amount (convert to wei for comparison)
            expected_amount_wei = int(float(expected_amount) * 1_000_000)  # USDC has 6 decimals
            payment_amount = int(payment_data["amount"])

            if payment_amount < expected_amount_wei:
                print(f"[WARN] Insufficient payment amount: {payment_amount} < {expected_amount_wei}")
                return False

            # In a production system, you would:
            # 1. Query the blockchain to verify the transaction exists
            # 2. Check that the transaction was confirmed
            # 3. Verify the transaction hasn't been used before (prevent replay attacks)
            # 4. Check timestamp to ensure payment is recent

            # For this implementation, we'll do basic validation
            tx_hash = payment_data["txHash"]

            # Simple tx hash format validation
            if not tx_hash.startswith("0x") or len(tx_hash) != 66:
                print(f"[WARN] Invalid transaction hash format: {tx_hash}")
                return False

            print(f"[OK] Payment verified: {payment_amount / 1_000_000} USDC to {wallet_address}")
            return True

        except json.JSONDecodeError:
            print("[WARN] Invalid JSON in payment header")
            return False
        except Exception as e:
            print(f"[ERROR] Payment verification failed: {e}")
            return False

    def generate_payment_request(self, wallet_address: str, amount: str, description: str, resource_url: str) -> dict:
        """
        Generate x402 payment request structure

        Args:
            wallet_address: Recipient wallet address
            amount: Payment amount in USDC
            description: Payment description
            resource_url: Resource being paid for

        Returns:
            dict: x402 payment request
        """
        amount_wei = int(float(amount) * 1_000_000)  # Convert to wei (6 decimals for USDC)

        return {
            "x402Version": 1,
            "accepts": [{
                "scheme": "exact",
                "network": "base",
                "maxAmountRequired": str(amount_wei),
                "resource": resource_url,
                "description": description,
                "mimeType": "application/json",
                "payTo": wallet_address,
                "maxTimeoutSeconds": 300,
                "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
                "extra": {
                    "name": "USDC",
                    "version": "2"
                }
            }]
        }