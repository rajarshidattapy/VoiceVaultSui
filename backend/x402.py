"""x402 payment verification and 402-response helpers."""
import os
import time
import requests

SUI_RPC_URL = os.getenv("SUI_RPC_URL", "https://fullnode.testnet.sui.io")
PLATFORM_ADDRESS = os.getenv("SUI_ADDRESS", "")
PACKAGE_ID = os.getenv("SUI_PACKAGE_ID", "")

# In-memory replay-protection set (reset on restart; fine for MVP)
_used_proofs: set[str] = set()


# ── 402 response builder ──────────────────────────────────────────────────────

def make_402_response(
    voice_id: str,
    price_mist: int,
    creator: str,
    resource: str,
    uses: int = 2,
) -> dict:
    """Return the JSON body for an HTTP 402 response."""
    return {
        "x402Version": 1,
        "error": "Payment Required",
        "accepts": [
            {
                "scheme": "exact",
                "network": "sui-testnet",
                "maxAmountRequired": str(price_mist),
                "resource": resource,
                "description": f"Pay {price_mist / 1_000_000_000:.3f} SUI for {uses} uses of this voice",
                "mimeType": "audio/wav",
                "payTo": creator,
                "maxTimeoutSeconds": 300,
                "asset": "0x2::sui::SUI",
                "extra": {
                    "voice_id": voice_id,
                    "uses": uses,
                    "expires_in_hours": 24,
                    "upsell_url": "/marketplace",
                },
            }
        ],
    }


# ── Payment verification ──────────────────────────────────────────────────────

def verify_sui_payment(
    tx_digest: str,
    expected_payer: str,
    expected_recipient: str,
    min_amount_mist: int,
) -> tuple[bool, str]:
    """
    Verify a Sui transfer tx. Returns (ok, error_reason).
    Adds digest to replay-protection set on success.
    """
    if not tx_digest:
        return False, "No transaction digest provided"

    if tx_digest in _used_proofs:
        return False, "Replay attack: transaction digest already consumed"

    try:
        resp = requests.post(
            SUI_RPC_URL,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "sui_getTransactionBlock",
                "params": [
                    tx_digest,
                    {
                        "showInput": True,
                        "showEffects": True,
                        "showBalanceChanges": True,
                    },
                ],
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            return False, f"RPC error: {data['error']}"

        result = data.get("result", {})
        effects = result.get("effects", {})
        status = effects.get("status", {}).get("status", "")
        if status != "success":
            return False, f"Transaction did not succeed (status={status})"

        balance_changes = result.get("balanceChanges", [])
        payer_paid = False
        recipient_received = False

        for change in balance_changes:
            owner = change.get("owner", {})
            owner_addr = (
                owner.get("AddressOwner", "") if isinstance(owner, dict) else ""
            )
            amount = int(change.get("amount", "0"))

            if (
                owner_addr.lower() == expected_payer.lower()
                and amount < 0
                and abs(amount) >= min_amount_mist
            ):
                payer_paid = True

            if (
                owner_addr.lower() == expected_recipient.lower()
                and amount > 0
            ):
                recipient_received = True

        if not payer_paid:
            return False, f"Payer did not send minimum {min_amount_mist} MIST"

        if not recipient_received:
            return False, f"Creator {expected_recipient} did not receive payment"

        _used_proofs.add(tx_digest)
        return True, ""

    except Exception as exc:
        return False, f"Verification failed: {exc}"


# ── Default pricing ───────────────────────────────────────────────────────────

DEFAULT_PRICE_MIST = int(os.getenv("X402_DEFAULT_PRICE_MIST", str(100_000_000)))  # 0.1 SUI
DEFAULT_USES = int(os.getenv("X402_DEFAULT_USES", "2"))
