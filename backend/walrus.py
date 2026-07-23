"""
Walrus-oriented storage helpers for VoiceVault.

The production path can talk to a Walrus Publisher/Aggregator over HTTP.
For local development we keep a filesystem-backed implementation that
preserves Walrus-style content-addressed blob IDs and manifest bundles.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote

import httpx

BACKEND_DIR = Path(__file__).resolve().parent
STORAGE_BASE_DIR = Path(os.getenv("VOICEVAULT_STORAGE_DIR", str(BACKEND_DIR / "storage"))).expanduser()

PORT = os.getenv("PORT", "8000")
REMOTE_MODE = os.getenv("WALRUS_STORAGE_MODE", "local").lower() == "remote"
PUBLISHER_URL = os.getenv("WALRUS_PUBLISHER_URL", "https://publisher.walrus-testnet.walrus.space").rstrip("/")
AGGREGATOR_URL = os.getenv(
    "WALRUS_AGGREGATOR_URL",
    f"http://localhost:{PORT}/api/walrus",
).rstrip("/")
DEFAULT_EPOCHS = int(os.getenv("WALRUS_EPOCHS", "5"))
DELETABLE = os.getenv("WALRUS_DELETABLE", "true").lower() == "true"
MAX_BLOB_SIZE = int(os.getenv("WALRUS_MAX_BLOB_SIZE", str(10 * 1024 * 1024)))

STORAGE_ROOT = STORAGE_BASE_DIR / "walrus"
BLOB_DIR = STORAGE_ROOT / "blobs"
META_DIR = STORAGE_ROOT / "meta"
SHELBY_STORAGE_ROOT = STORAGE_BASE_DIR / "shelby"


class WalrusFileNotFoundError(Exception):
    """Raised when a requested Walrus blob or bundle file does not exist."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ENOENT"


class FileNotFoundError(Exception):
    """Legacy Shelby-compatible file-not-found error."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ENOENT"


def _ensure_storage_dirs() -> None:
    BLOB_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)


def _as_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    return bytes(value)


def _blob_id_for(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _object_id_for(blob_id: str) -> str:
    digest = hashlib.sha256(f"object:{blob_id}".encode("utf-8")).hexdigest()
    return f"0x{digest[:64]}"


def _blob_path(blob_id: str) -> Path:
    return BLOB_DIR / f"{blob_id}.bin"


def _meta_path(blob_id: str) -> Path:
    return META_DIR / f"{blob_id}.json"


def _write_local_blob(data: bytes, *, is_manifest: bool = False) -> Tuple[str, str]:
    _ensure_storage_dirs()
    blob_id = _blob_id_for(data)
    object_id = _object_id_for(blob_id)
    blob_path = _blob_path(blob_id)
    meta_path = _meta_path(blob_id)

    if not blob_path.exists():
        blob_path.write_bytes(data)

    if not meta_path.exists():
        meta_path.write_text(
            json.dumps(
                {
                    "blobId": blob_id,
                    "objectId": object_id,
                    "size": len(data),
                    "isManifest": is_manifest,
                    "storedAt": int(time.time() * 1000),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return blob_id, object_id


def _read_local_blob(blob_id: str) -> bytes:
    blob_path = _blob_path(blob_id)
    if not blob_path.exists():
        raise WalrusFileNotFoundError(f"Blob not found: {blob_id}")
    return blob_path.read_bytes()


def _delete_local_blob(blob_id: str) -> None:
    blob_path = _blob_path(blob_id)
    meta_path = _meta_path(blob_id)
    if blob_path.exists():
        blob_path.unlink()
    if meta_path.exists():
        meta_path.unlink()


def _upload_remote_blob(
    data: bytes,
    *,
    epochs: int,
    send_object_to: Optional[str] = None,
) -> Tuple[str, str]:
    params = {"epochs": str(epochs)}
    if DELETABLE:
        params["deletable"] = "true"
    if send_object_to:
        params["send_object_to"] = send_object_to

    response = httpx.put(
        f"{PUBLISHER_URL}/v1/blobs",
        params=params,
        content=data,
        headers={"Content-Type": "application/octet-stream"},
        timeout=120,
    )
    response.raise_for_status()

    payload = response.json()
    if "newlyCreated" in payload:
        blob_object = payload["newlyCreated"].get("blobObject", {})
        return blob_object["blobId"], blob_object.get("id", "")
    if "alreadyCertified" in payload:
        certified = payload["alreadyCertified"]
        event = certified.get("event", {})
        return certified["blobId"], event.get("txDigest", "")
    raise ValueError(f"Unexpected Walrus publisher response: {payload}")


def _store_blob(
    data: bytes,
    *,
    epochs: int,
    send_object_to: Optional[str] = None,
    is_manifest: bool = False,
) -> Tuple[str, str]:
    if REMOTE_MODE:
        return _upload_remote_blob(data, epochs=epochs, send_object_to=send_object_to)
    return _write_local_blob(data, is_manifest=is_manifest)


def _chunk_bytes(data: bytes, chunk_size: int = MAX_BLOB_SIZE) -> List[bytes]:
    return [data[index:index + chunk_size] for index in range(0, len(data), chunk_size)]


def _store_file_reference(
    data: bytes,
    *,
    epochs: int,
    send_object_to: Optional[str] = None,
) -> Dict[str, object]:
    if len(data) <= MAX_BLOB_SIZE:
        blob_id, object_id = _store_blob(
            data,
            epochs=epochs,
            send_object_to=send_object_to,
        )
        return {
            "blobId": blob_id,
            "objectId": object_id,
            "size": len(data),
        }

    blob_ids: List[str] = []
    object_ids: List[str] = []
    for chunk in _chunk_bytes(data):
        blob_id, object_id = _store_blob(
            chunk,
            epochs=epochs,
            send_object_to=send_object_to,
        )
        blob_ids.append(blob_id)
        object_ids.append(object_id)

    return {
        "chunked": True,
        "blobIds": blob_ids,
        "objectIds": object_ids,
        "size": len(data),
    }


def upload_to_walrus(
    owner_address: str,
    voice_id: str,
    bundle_files: Dict[str, bytes],
    *,
    epochs: int = DEFAULT_EPOCHS,
    send_object_to: Optional[str] = None,
) -> Dict[str, object]:
    """
    Upload a bundle to Walrus and return a manifest whose URI becomes the model URI.
    """
    if not bundle_files:
        raise ValueError("bundle_files is required")

    normalized_files = {
        filename: _as_bytes(buffer)
        for filename, buffer in bundle_files.items()
    }

    blobs = {
        filename: _store_file_reference(
            data,
            epochs=epochs,
            send_object_to=send_object_to or owner_address,
        )
        for filename, data in normalized_files.items()
    }

    manifest = {
        "voiceId": voice_id,
        "owner": owner_address,
        "blobs": blobs,
        "version": 1,
        "storageMode": "remote" if REMOTE_MODE else "local",
    }

    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
    manifest_blob_id, manifest_object_id = _store_blob(
        manifest_bytes,
        epochs=epochs,
        send_object_to=send_object_to or owner_address,
        is_manifest=True,
    )

    manifest["manifestBlobId"] = manifest_blob_id
    manifest["manifestObjectId"] = manifest_object_id
    manifest["walrusUri"] = build_walrus_uri(manifest_blob_id)
    manifest["size"] = sum(len(data) for data in normalized_files.values())
    manifest["previewUrl"] = get_manifest_preview_url(manifest)
    return manifest


def _download_remote_blob(blob_id: str) -> bytes:
    if AGGREGATOR_URL.endswith("/v1"):
        url = f"{AGGREGATOR_URL}/blobs/{quote(blob_id, safe='')}"
    else:
        url = f"{AGGREGATOR_URL}/v1/blobs/{quote(blob_id, safe='')}"

    response = httpx.get(
        url,
        timeout=120,
    )
    if response.status_code == 404:
        raise WalrusFileNotFoundError(f"Blob not found: {blob_id}")
    response.raise_for_status()
    return response.content


def download_from_walrus(blob_id: str) -> bytes:
    if REMOTE_MODE:
        return _download_remote_blob(blob_id)
    return _read_local_blob(blob_id)


def parse_walrus_uri(uri: str) -> str:
    if not uri.startswith("walrus://"):
        raise ValueError(f"Invalid Walrus URI: {uri}")
    return uri[len("walrus://"):]


def build_walrus_uri(blob_id: str) -> str:
    return f"walrus://{blob_id}"


def is_walrus_uri(uri: str) -> bool:
    return uri.startswith("walrus://")


def load_manifest(manifest_blob_id: str) -> Dict[str, object]:
    try:
        manifest_bytes = download_from_walrus(manifest_blob_id)
    except WalrusFileNotFoundError:
        raise
    except Exception as error:
        raise WalrusFileNotFoundError(f"Manifest not found: {manifest_blob_id}") from error

    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as error:
        raise ValueError(f"Manifest blob is not valid JSON: {manifest_blob_id}") from error

    if "walrusUri" not in manifest:
        manifest["walrusUri"] = build_walrus_uri(manifest_blob_id)
    return manifest


def _download_blob_reference(blob_ref: Dict[str, object]) -> bytes:
    if blob_ref.get("chunked"):
        blob_ids = blob_ref.get("blobIds") or []
        return b"".join(download_from_walrus(blob_id) for blob_id in blob_ids)

    blob_id = blob_ref.get("blobId")
    if not blob_id:
        raise WalrusFileNotFoundError("Blob reference does not contain a blobId")
    return download_from_walrus(blob_id)


def download_file(manifest_blob_id: str, filename: str) -> bytes:
    manifest = load_manifest(manifest_blob_id)
    blob_ref = (manifest.get("blobs") or {}).get(filename)
    if not blob_ref:
        raise WalrusFileNotFoundError(f"File not found: {filename} in walrus://{manifest_blob_id}")
    return _download_blob_reference(blob_ref)


def download_bundle(manifest_blob_id: str) -> Dict[str, bytes]:
    manifest = load_manifest(manifest_blob_id)
    blobs = manifest.get("blobs") or {}
    return {
        filename: _download_blob_reference(blob_ref)
        for filename, blob_ref in blobs.items()
    }


def get_aggregator_url(blob_id: str) -> str:
    if REMOTE_MODE:
        if AGGREGATOR_URL.endswith("/v1"):
            return f"{AGGREGATOR_URL}/blobs/{quote(blob_id, safe='')}"
        return f"{AGGREGATOR_URL}/v1/blobs/{quote(blob_id, safe='')}"
    return f"{AGGREGATOR_URL}/blobs/{quote(blob_id, safe='')}"


def get_manifest_preview_url(manifest: Dict[str, object]) -> Optional[str]:
    preview = (manifest.get("blobs") or {}).get("preview.wav")
    if not preview:
        return None
    if preview.get("chunked"):
        return None
    blob_id = preview.get("blobId")
    if not blob_id:
        return None
    return get_aggregator_url(blob_id)


def verify_walrus_access(uri: str, requester_account: str) -> bool:
    """Owner-only fast path — kept for legacy callers. Use verify_license_pass for buyers."""
    try:
        manifest = load_manifest(parse_walrus_uri(uri))
        owner = str(manifest.get("owner", ""))
        return bool(owner and requester_account and owner.lower() == requester_account.lower())
    except Exception:
        return False


def verify_license_pass(voice_object_id: str, requester_account: str) -> bool:
    """
    Query the Sui RPC to check whether `requester_account` owns a LicensePass
    for `voice_object_id`.  Returns True only when a matching pass is found.
    """
    rpc_url = os.getenv("SUI_RPC_URL", "https://fullnode.testnet.sui.io")
    package_id = os.getenv("SUI_PACKAGE_ID", "").strip()

    if not package_id or not voice_object_id or not requester_account:
        return False

    struct_type = f"{package_id}::payment::LicensePass"

    try:
        response = httpx.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "suix_getOwnedObjects",
                "params": [
                    requester_account,
                    {
                        "filter": {"StructType": struct_type},
                        "options": {"showContent": True},
                    },
                ],
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        objects = (data.get("result") or {}).get("data") or []
        for obj in objects:
            content = ((obj.get("data") or {}).get("content")) or {}
            if content.get("dataType") != "moveObject":
                continue
            fields = content.get("fields") or {}
            # Sui serialises ID as a plain hex string or {"id": "0x..."}
            raw_vid = fields.get("voice_id")
            if isinstance(raw_vid, dict):
                raw_vid = raw_vid.get("id") or raw_vid.get("bytes") or ""
            if raw_vid and str(raw_vid).lower() == voice_object_id.lower():
                return True
        return False
    except Exception as err:
        print(f"[verify_license_pass] Sui RPC error: {err}")
        return False


def _normalize_hex(value: object) -> str:
    return str(value or "").lower()


def _owner_address(owner: object) -> str:
    if isinstance(owner, dict):
        value = owner.get("AddressOwner") or owner.get("addressOwner") or owner.get("address")
        if value:
            return _normalize_hex(value)
    return _normalize_hex(owner)


def _argument_input_index(argument: object) -> Optional[int]:
    if isinstance(argument, dict):
        value = argument.get("Input")
        if value is None:
            value = argument.get("input")
        if isinstance(value, int):
            return value
    return None


def _input_address(inputs: list, argument: object) -> str:
    index = _argument_input_index(argument)
    if index is None or index >= len(inputs):
        return ""

    value = inputs[index]
    if isinstance(value, dict):
        pure_value = value.get("value") or value.get("Value")
        if pure_value:
            return _normalize_hex(pure_value)
        object_id = value.get("objectId") or value.get("object_id")
        if object_id:
            return _normalize_hex(object_id)
    return ""


def _programmable_transaction(tx_kind: dict) -> tuple[list, list]:
    if not isinstance(tx_kind, dict):
        return [], []

    if "ProgrammableTransaction" in tx_kind:
        programmable = tx_kind.get("ProgrammableTransaction") or {}
        return programmable.get("inputs") or [], programmable.get("transactions") or []

    if "programmableTransaction" in tx_kind:
        programmable = tx_kind.get("programmableTransaction") or {}
        return programmable.get("inputs") or [], programmable.get("transactions") or []

    return tx_kind.get("inputs") or [], tx_kind.get("transactions") or []


def _move_call(command: object) -> dict:
    if not isinstance(command, dict):
        return {}
    return command.get("MoveCall") or command.get("moveCall") or {}


def verify_purchase_transaction(
    tx_digest: str,
    requester_account: str,
    creator_address: str,
    voice_object_id: str = "",
) -> bool:
    """
    Verify a legacy marketplace purchase transaction.

    The current deployed payment contract does not mint LicensePass and does
    not carry voice_id, so the strongest legacy proof is: successful payment
    call from buyer to the voice creator in the configured package.
    """
    rpc_url = os.getenv("SUI_RPC_URL", "https://fullnode.testnet.sui.io")
    package_id = os.getenv("SUI_PACKAGE_ID", "").strip()

    if not package_id or not tx_digest or not requester_account or not creator_address:
        return False

    try:
        response = httpx.post(
            rpc_url,
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
        response.raise_for_status()
        result = (response.json().get("result") or {})

        effects = result.get("effects") or {}
        status = (effects.get("status") or {}).get("status")
        if status != "success":
            return False

        tx_data = ((result.get("transaction") or {}).get("data")) or {}
        if _normalize_hex(tx_data.get("sender")) != _normalize_hex(requester_account):
            return False

        inputs, commands = _programmable_transaction(tx_data.get("transaction") or {})
        expected_package = _normalize_hex(package_id)
        expected_creator = _normalize_hex(creator_address)
        expected_voice = _normalize_hex(voice_object_id)

        payment_call_found = False
        for command in commands:
            call = _move_call(command)
            if not call:
                continue
            if _normalize_hex(call.get("package")) != expected_package:
                continue
            if call.get("module") != "payment" or call.get("function") != "pay_with_royalty_split":
                continue

            args = call.get("arguments") or []
            if len(args) >= 5:
                call_voice = _input_address(inputs, args[1])
                call_creator = _input_address(inputs, args[2])
                if expected_voice and call_voice != expected_voice:
                    continue
            elif len(args) == 4:
                call_creator = _input_address(inputs, args[1])
            else:
                continue

            if call_creator == expected_creator:
                payment_call_found = True
                break

        if not payment_call_found:
            return False

        for change in result.get("balanceChanges") or []:
            if _owner_address(change.get("owner")) != expected_creator:
                continue
            if change.get("coinType") != "0x2::sui::SUI":
                continue
            if int(change.get("amount") or 0) > 0:
                return True

        return False
    except Exception as err:
        print(f"[verify_purchase_transaction] Sui RPC error: {err}")
        return False


def _manifest_blob_ids(manifest: Dict[str, object]) -> List[str]:
    referenced: List[str] = []
    for blob_ref in (manifest.get("blobs") or {}).values():
        if blob_ref.get("chunked"):
            referenced.extend(blob_ref.get("blobIds") or [])
        elif blob_ref.get("blobId"):
            referenced.append(blob_ref["blobId"])
    return referenced


def _iter_manifest_ids() -> Iterable[str]:
    if not META_DIR.exists():
        return []

    manifest_ids: List[str] = []
    for meta_file in META_DIR.glob("*.json"):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if meta.get("isManifest") and meta.get("blobId"):
            manifest_ids.append(meta["blobId"])
    return manifest_ids


def _collect_remaining_blob_references(excluding_manifest_id: Optional[str] = None) -> set[str]:
    remaining: set[str] = set()
    for manifest_id in _iter_manifest_ids():
        if excluding_manifest_id and manifest_id == excluding_manifest_id:
            continue
        try:
            manifest = load_manifest(manifest_id)
        except Exception:
            continue
        remaining.update(_manifest_blob_ids(manifest))
    return remaining


def delete_from_walrus(uri: str, account: str) -> Dict[str, object]:
    if REMOTE_MODE:
        raise NotImplementedError(
            "Remote Walrus deletion requires a wallet-signed Sui transaction and is not implemented by this backend helper."
        )

    manifest_blob_id = parse_walrus_uri(uri)
    manifest = load_manifest(manifest_blob_id)
    owner = str(manifest.get("owner", ""))

    if owner.lower() != account.lower():
        raise PermissionError("Unauthorized: Only the owner can delete their voice from Walrus")

    referenced_blob_ids = _manifest_blob_ids(manifest)
    remaining_references = _collect_remaining_blob_references(excluding_manifest_id=manifest_blob_id)

    _delete_local_blob(manifest_blob_id)

    deleted_blob_ids: List[str] = []
    for blob_id in referenced_blob_ids:
        if blob_id in remaining_references:
            continue
        _delete_local_blob(blob_id)
        deleted_blob_ids.append(blob_id)

    return {
        "success": True,
        "uri": uri,
        "deletedAt": int(time.time() * 1000),
        "deletedBlobIds": deleted_blob_ids,
    }


def _ensure_shelby_storage_dir(account: str, namespace: str, voice_id: str) -> Path:
    dir_path = SHELBY_STORAGE_ROOT / account / namespace / voice_id
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def upload_to_shelby(account: str, namespace: str, voice_id: str, bundle_files: Dict[str, bytes]) -> Dict[str, object]:
    """
    Legacy Shelby storage helper kept here so walrus.py is the canonical backend storage module.
    """
    uri = f"shelby://{account}/{namespace}/{voice_id}"
    storage_dir = _ensure_shelby_storage_dir(account, namespace, voice_id)

    total_size = 0
    hash_obj = hashlib.sha256()

    for filename, buffer in bundle_files.items():
        data = _as_bytes(buffer)
        (storage_dir / filename).write_bytes(data)
        total_size += len(data)
        hash_obj.update(data)

    cid = hash_obj.hexdigest()

    return {
        "uri": uri,
        "cid": f"0x{cid}",
        "size": total_size,
        "uploadedAt": int(time.time() * 1000),
    }


def download_from_shelby(uri: str, filename: str) -> bytes:
    match = re.match(r"^shelby://([^/]+)/([^/]+)/(.+)$", uri)
    if not match:
        raise ValueError(f"Invalid Shelby URI: {uri}")

    account, namespace, voice_id = match.group(1), match.group(2), match.group(3)
    file_path = SHELBY_STORAGE_ROOT / account / namespace / voice_id / filename

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename} in {uri}")

    return file_path.read_bytes()


def delete_from_shelby(uri: str, account: str) -> Dict[str, object]:
    match = re.match(r"^shelby://([^/]+)/([^/]+)/(.+)$", uri)
    if not match:
        raise ValueError(f"Invalid Shelby URI: {uri}")

    owner_account, namespace, voice_id = match.group(1), match.group(2), match.group(3)
    if owner_account.lower() != account.lower():
        raise PermissionError("Unauthorized: Only the owner can delete their voice from Shelby")

    voice_dir = SHELBY_STORAGE_ROOT / owner_account / namespace / voice_id
    if not voice_dir.exists():
        return {
            "success": True,
            "uri": uri,
            "message": "Voice bundle not found (may have been already deleted)",
        }

    for file_path in voice_dir.iterdir():
        if file_path.is_file():
            file_path.unlink()

    voice_dir.rmdir()

    return {
        "success": True,
        "uri": uri,
        "deletedAt": int(time.time() * 1000),
    }


def verify_shelby_access(uri: str, requester_account: str) -> bool:
    try:
        match = re.match(r"^shelby://([^/]+)/([^/]+)/(.+)$", uri)
        if not match:
            return False

        owner_account = match.group(1)
        if owner_account.lower() == requester_account.lower():
            return True

        return True
    except Exception:
        return False


def verify_access(uri: str, requester_account: str) -> bool:
    if uri.startswith("shelby://"):
        return verify_shelby_access(uri, requester_account)
    if uri.startswith("walrus://"):
        return verify_walrus_access(uri, requester_account)
    return False
