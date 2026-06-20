"""x402 Pay-Per-Use payment verification — Monad Testnet."""
import os
from typing import Tuple

DEFAULT_PRICE_WEI = int(os.getenv("DEFAULT_PRICE_WEI", "10000000000000000"))  # 0.01 MON
DEFAULT_USES = 2


def _get_web3():
    try:
        from web3 import Web3
        rpc_url = os.getenv("MONAD_RPC_URL", "https://testnet-rpc.monad.xyz")
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        return w3
    except Exception:
        return None


def verify_monad_transaction(
    tx_hash: str,
    expected_payer: str,
    expected_recipient: str,
    min_amount: int,
) -> Tuple[bool, str]:
    """Verify a Monad transaction: payer, recipient, amount."""
    if not tx_hash or not tx_hash.startswith("0x"):
        return False, "Invalid tx_hash format"

    try:
        import database
        if database.has_payment_proof(tx_hash):
            return False, "Transaction already used (replay attack)"
    except Exception:
        pass

    w3 = _get_web3()
    if not w3:
        # web3 not available — allow in dev mode
        return True, "web3 not configured, allowing in dev mode"

    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        tx = w3.eth.get_transaction(tx_hash)

        if receipt is None or tx is None:
            return False, "Transaction not found"

        if receipt.status != 1:
            return False, "Transaction failed on-chain"

        if expected_payer and tx["from"].lower() != expected_payer.lower():
            return False, f"Payer mismatch: expected {expected_payer}, got {tx['from']}"

        if expected_recipient:
            to_addr = tx.get("to") or ""
            if to_addr.lower() != expected_recipient.lower():
                return False, f"Recipient mismatch"

        if tx.get("value", 0) < min_amount:
            return False, f"Amount too low: got {tx.get('value', 0)}, expected {min_amount}"

        return True, "ok"
    except Exception as err:
        return False, f"Verification error: {err}"


def make_402_response(voice_id: str, price_wei: int, creator: str, endpoint: str) -> dict:
    chain_id = int(os.getenv("CHAIN_ID", "10143"))
    return {
        "error": "Payment Required",
        "x402": {
            "version": "1",
            "scheme": "exact",
            "network": f"eip155:{chain_id}",
            "maxAmountRequired": str(price_wei),
            "resource": endpoint,
            "description": f"Pay to access voice {voice_id}",
            "mimeType": "audio/wav",
            "payTo": creator,
            "maxTimeoutSeconds": 300,
            "asset": "0x0000000000000000000000000000000000000000",
            "extra": {"voiceId": voice_id, "priceWei": price_wei},
        },
    }
