import atexit
import asyncio
import json
import math
import os
import platform
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn

# Load .env — try backend/ first, then project root as fallback
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")

import voice_model
import walrus as walrus_module
import agent_store
import agent_index
import livekit_service
import x402 as x402_module
import usage_store

# Ensure storage directories exist
walrus_module._ensure_storage_dirs()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _download_preview_from_walrus(model_uri: str):
    """Download voice files from Walrus bundle."""
    try:
        manifest_blob_id = walrus_module.parse_walrus_uri(model_uri)
        embedding_buffer = walrus_module.download_file(manifest_blob_id, "embedding.bin")
    except Exception:
        embedding_buffer = None
    try:
        config_buffer = walrus_module.download_file(manifest_blob_id, "config.json")
    except Exception:
        config_buffer = None
    try:
        preview_buffer = walrus_module.download_file(manifest_blob_id, "preview.wav")
    except Exception:
        preview_buffer = None

    return embedding_buffer, config_buffer, preview_buffer


def _content_type_for(filename: str) -> str:
    if filename.endswith(".json"):
        return "application/json"
    if filename.endswith(".wav"):
        return "audio/wav"
    return "application/octet-stream"


def _pick(data: dict, *keys: str, default=None):
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return default


_agent_worker_process: subprocess.Popen | None = None
_agent_worker_log_handle = None
_mcp_server_process: subprocess.Popen | None = None
_mcp_server_log_handle = None


def _agent_worker_log_path() -> Path:
    return BACKEND_DIR / "storage" / "agent_worker.log"


def _mcp_server_log_path() -> Path:
    return BACKEND_DIR / "storage" / "agent_network_mcp.log"


def _close_agent_worker_log() -> None:
    global _agent_worker_log_handle
    if _agent_worker_log_handle is not None:
        try:
            _agent_worker_log_handle.close()
        except Exception:
            pass
        _agent_worker_log_handle = None


def _close_mcp_server_log() -> None:
    global _mcp_server_log_handle
    if _mcp_server_log_handle is not None:
        try:
            _mcp_server_log_handle.close()
        except Exception:
            pass
        _mcp_server_log_handle = None


def _is_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _ensure_mcp_server() -> tuple[bool, bool, str | None]:
    """Start the central Agent Network MCP server if needed."""
    global _mcp_server_process, _mcp_server_log_handle

    if os.getenv("AGENT_NETWORK_MCP_ENABLED", "true").lower() in {"0", "false", "no"}:
        return False, False, "Agent Network MCP is disabled"

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))

    if _mcp_server_process is not None:
        exit_code = _mcp_server_process.poll()
        if exit_code is None:
            return True, False, None
        print(f"[mcp] previous MCP server exited with code {exit_code}; restarting")
        _mcp_server_process = None
        _close_mcp_server_log()

    if _is_port_open(host, port):
        return True, False, None

    mcp_script = BACKEND_DIR / "swaraos_mcp_server.py"
    if not mcp_script.exists():
        return False, False, f"Agent Network MCP server script not found: {mcp_script}"

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("BACKEND_URL", os.getenv("BACKEND_URL", f"http://localhost:{os.getenv('PORT', '8000')}"))
    env.setdefault("MCP_HOST", host)
    env.setdefault("MCP_PORT", str(port))

    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    log_path = _mcp_server_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _mcp_server_log_handle = open(log_path, "a", encoding="utf-8")
        _mcp_server_process = subprocess.Popen(
            [sys.executable, str(mcp_script)],
            cwd=str(BACKEND_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=_mcp_server_log_handle,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        print(f"[mcp] Agent Network MCP started pid={_mcp_server_process.pid}, log={log_path}")
        return True, True, None
    except Exception as err:
        _mcp_server_process = None
        _close_mcp_server_log()
        return False, False, f"Failed to start Agent Network MCP server: {err}"


def _ensure_agent_worker() -> tuple[bool, bool, str | None]:
    """Start the LiveKit agent worker if it is not already running."""
    global _agent_worker_process, _agent_worker_log_handle

    if not livekit_service.is_configured():
        return False, False, "LiveKit credentials are not configured"

    if not os.getenv("OPENAI_API_KEY"):
        return False, False, "OPENAI_API_KEY is not configured for the voice agent worker"

    mcp_running, mcp_started, mcp_error = _ensure_mcp_server()
    if mcp_started:
        import time

        time.sleep(float(os.getenv("MCP_STARTUP_GRACE_SECONDS", "1")))
    if not mcp_running and os.getenv("AGENT_NETWORK_MCP_REQUIRED", "false").lower() in {"1", "true", "yes"}:
        return False, False, mcp_error or "Agent Network MCP server is not running"

    if _agent_worker_process is not None:
        exit_code = _agent_worker_process.poll()
        if exit_code is None:
            return True, False, None
        print(f"[livekit] previous agent worker exited with code {exit_code}; restarting")
        _agent_worker_process = None
        _close_agent_worker_log()

    worker_script = BACKEND_DIR / "agent_worker.py"
    if not worker_script.exists():
        return False, False, f"Agent worker script not found: {worker_script}"

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("LIVEKIT_AGENT_NAME", livekit_service.LIVEKIT_AGENT_NAME)
    mode = os.getenv("LIVEKIT_AGENT_MODE", "start")

    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    log_path = _agent_worker_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _agent_worker_log_handle = open(log_path, "a", encoding="utf-8")
        _agent_worker_process = subprocess.Popen(
            [sys.executable, str(worker_script), mode],
            cwd=str(BACKEND_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=_agent_worker_log_handle,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
        print(f"[livekit] agent worker started pid={_agent_worker_process.pid}, log={log_path}")
        return True, True, None
    except Exception as err:
        _agent_worker_process = None
        _close_agent_worker_log()
        return False, False, f"Failed to start LiveKit agent worker: {err}"


def _stop_agent_worker() -> None:
    global _agent_worker_process
    if _agent_worker_process is not None and _agent_worker_process.poll() is None:
        try:
            _agent_worker_process.terminate()
            _agent_worker_process.wait(timeout=5)
        except Exception:
            _agent_worker_process.kill()
    _agent_worker_process = None
    _close_agent_worker_log()


def _stop_mcp_server() -> None:
    global _mcp_server_process
    if _mcp_server_process is not None and _mcp_server_process.poll() is None:
        try:
            _mcp_server_process.terminate()
            _mcp_server_process.wait(timeout=5)
        except Exception:
            _mcp_server_process.kill()
    _mcp_server_process = None
    _close_mcp_server_log()


atexit.register(_stop_agent_worker)
atexit.register(_stop_mcp_server)


async def _prepare_livekit_room(agent: dict, identity: str) -> dict:
    room_name = agent["room_name"]
    user_token = livekit_service.create_token(room_name, identity)
    join_url = livekit_service.get_join_url(room_name, user_token)
    start_cmd = livekit_service.agent_start_command(room_name)

    result = {
        "roomName": room_name,
        "joinUrl": join_url,
        "userToken": user_token,
        "token": user_token,
        "startCmd": start_cmd,
        "liveKitConfigured": livekit_service.is_configured(),
        "workerRunning": False,
        "agentDispatched": False,
        "workerError": None,
        "dispatchError": None,
    }

    if result["liveKitConfigured"] and not join_url:
        result["workerError"] = "LiveKit token generation failed; check livekit-api and credentials"
        return result

    if not result["liveKitConfigured"]:
        return result

    worker_running, worker_started, worker_error = _ensure_agent_worker()
    if worker_started:
        grace = float(os.getenv("LIVEKIT_WORKER_STARTUP_GRACE_SECONDS", "2"))
        await asyncio.sleep(max(0.0, grace))
        if _agent_worker_process is not None and _agent_worker_process.poll() is not None:
            worker_running = False
            worker_error = (
                f"Agent worker exited with code {_agent_worker_process.poll()}. "
                f"See {_agent_worker_log_path()}."
            )

    result["workerRunning"] = worker_running
    result["workerError"] = worker_error

    if not worker_running:
        return result

    metadata = json.dumps(
        {
            "agent_id": agent.get("id", ""),
            "target_agent_id": agent.get("id", ""),
            "agent_name": agent.get("agent_name", ""),
            "owner": agent.get("owner", ""),
            "voice_id": agent.get("voice_id", ""),
            "room_name": room_name,
            "user_identity": identity,
            "mode": "primary",
        }
    )
    dispatched, dispatch_error = await livekit_service.ensure_agent_dispatch(
        room_name,
        metadata,
        dispatch_key=f"primary:{agent.get('id', room_name)}",
    )
    result["agentDispatched"] = dispatched
    result["dispatchError"] = dispatch_error
    return result


def _livekit_room_error(room: dict) -> str | None:
    if not room.get("liveKitConfigured"):
        return None
    if not room.get("workerRunning"):
        return room.get("workerError") or "LiveKit agent worker is not running"
    if not room.get("agentDispatched"):
        return room.get("dispatchError") or "LiveKit agent was not dispatched to the room"
    return None


def _parse_recent_turns(value):
    if isinstance(value, list):
        return value[:12]
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed[:12] if isinstance(parsed, list) else []
    except Exception:
        return []


def _default_skills(template_id: str, agent_name: str, system_prompt: str) -> list[str]:
    text = f"{template_id} {agent_name} {system_prompt}".lower()
    skills = set()
    template_map = {
        "sales": ["sales", "pricing", "lead qualification", "course advising"],
        "support": ["support", "faq", "troubleshooting"],
        "tutor": ["tutoring", "teaching", "course content", "education"],
        "creator": ["creator", "brand", "community"],
        "custom": ["general"],
    }
    skills.update(template_map.get(template_id, []))
    keyword_map = {
        "course": "course content",
        "curriculum": "course content",
        "teach": "teaching",
        "tutor": "tutoring",
        "sales": "sales",
        "pricing": "pricing",
        "support": "support",
        "faq": "faq",
    }
    for keyword, skill in keyword_map.items():
        if keyword in text:
            skills.add(skill)
    return sorted(skills or {"general"})


def _public_agent(agent: dict) -> dict:
    return {
        "agent_id": agent.get("id", ""),
        "name": agent.get("agent_name", ""),
        "description": agent.get("agent_description", ""),
        "status": agent.get("status", "idle"),
        "skills": agent.get("skills", []),
        "language": agent.get("language", "en-IN"),
        "voice_name": agent.get("voice_name", ""),
        "calls_count": agent.get("calls_count", 0),
    }


async def _generate_delegate_answer(target_agent: dict, payload: dict) -> str:
    from openai import OpenAI

    question = str(payload.get("question") or payload.get("text") or "").strip()
    context_summary = str(payload.get("context_summary") or "").strip()
    user_intent = str(payload.get("user_intent") or "").strip()
    recent_turns = _parse_recent_turns(payload.get("recent_turns") or payload.get("recent_turns_json"))

    if not question:
        raise ValueError("question is required")

    agent_name = target_agent.get("agent_name", "VoiceVault Agent")
    system_prompt = target_agent.get("system_prompt", "You are a helpful specialist.")
    language = target_agent.get("language", "en-IN")

    messages = [
        {
            "role": "system",
            "content": (
                f"{system_prompt}\n\n"
                f"You are {agent_name}, acting as a specialist consulted by another live voice agent. "
                "Answer only the delegated question. Use the provided context, do not invent facts, "
                "and keep the response concise enough to be spoken in a live call. "
                f"Preferred language: {language}."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "delegated_question": question,
                    "user_intent": user_intent,
                    "conversation_summary": context_summary,
                    "recent_turns": recent_turns,
                },
                ensure_ascii=False,
            ),
        },
    ]

    model = os.getenv("AGENT_DELEGATION_MODEL", "gpt-4o-mini")
    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        max_tokens=500,
    )
    return (response.choices[0].message.content or "").strip()


# ==================== Unified TTS Endpoint ====================

@app.post("/api/tts/generate")
async def tts_generate(request: Request):
    try:
        data = await request.json()
        model_uri = data.get("modelUri")
        text = data.get("text")
        requester_account = data.get("requesterAccount")
        voice_object_id = data.get("voiceObjectId")  # VoiceIdentity object ID on Sui

        if not model_uri:
            return JSONResponse({"error": "modelUri parameter missing"}, status_code=400)
        if not text:
            return JSONResponse({"error": "text parameter missing"}, status_code=400)

        if model_uri.startswith("walrus://"):
            if not requester_account:
                return JSONResponse({"error": "requesterAccount required for Walrus URIs"}, status_code=400)

            # Check 1: voice owner always has access
            is_owner = walrus_module.verify_walrus_access(model_uri, requester_account)

            if not is_owner:
                # Check 2: full LicensePass (purchased voice)
                has_license = bool(voice_object_id and walrus_module.verify_license_pass(voice_object_id, requester_account))

                # Check 3: x402 UsagePass (pay-per-use)
                has_usage_pass = False
                active_pass_id = None
                if not has_license and voice_object_id:
                    ok, record = usage_store.has_access(requester_account, voice_object_id)
                    if ok and record:
                        has_usage_pass = True
                        active_pass_id = record["id"]

                # Check 4: fresh X-Payment-Proof header (new x402 payment)
                if not has_license and not has_usage_pass:
                    payment_proof = request.headers.get("X-Payment-Proof", "")
                    if payment_proof and voice_object_id:
                        price_mist = x402_module.DEFAULT_PRICE_MIST
                        creator = data.get("creatorAddress", "")
                        ok, err = x402_module.verify_sui_payment(
                            payment_proof, requester_account, creator, price_mist
                        )
                        if ok:
                            record = usage_store.create_pass(
                                requester_account, voice_object_id,
                                uses=x402_module.DEFAULT_USES,
                                tx_digest=payment_proof,
                            )
                            active_pass_id = record["id"]
                            has_usage_pass = True

                if not has_license and not has_usage_pass:
                    # Return 402 with payment requirements so clients can pay and retry
                    price_mist = x402_module.DEFAULT_PRICE_MIST
                    creator = data.get("creatorAddress", "")
                    payment_req = x402_module.make_402_response(
                        voice_object_id or "", price_mist, creator, "/api/tts/generate"
                    )
                    return JSONResponse(payment_req, status_code=402)

                # Consume one use from the UsagePass
                if has_usage_pass and active_pass_id and not has_license:
                    usage_store.consume_pass(active_pass_id)

            embedding_buffer, config_buffer, preview_buffer = _download_preview_from_walrus(model_uri)

            if not embedding_buffer or not config_buffer:
                return JSONResponse({"error": "Voice model files not found on Walrus"}, status_code=404)

            if preview_buffer and len(preview_buffer) > 0:
                return Response(content=preview_buffer, media_type="audio/wav")

            return JSONResponse({"error": "No preview audio available for this voice"}, status_code=404)

        return JSONResponse({
            "error": "Unsupported model URI format",
            "message": "Supported format: 'walrus://...'",
        }, status_code=400)
    except Exception as err:
        return JSONResponse({"error": "TTS generation failed", "message": str(err)}, status_code=500)


# ==================== Payment Breakdown Calculation ====================

@app.post("/api/payment/breakdown")
async def payment_breakdown(request: Request):
    try:
        data = await request.json()
        amount = data.get("amount")

        if not isinstance(amount, (int, float)) or amount <= 0:
            return JSONResponse({"error": "Invalid amount. Must be a positive number"}, status_code=400)

        amount_in_octas = math.floor(amount * 100_000_000)

        platform_fee_bps = 250
        platform_fee = math.floor((amount_in_octas * 250) / 10_000)
        remaining_after_platform = amount_in_octas - platform_fee

        royalty_bps = 1000
        royalty_amount = math.floor((remaining_after_platform * 1000) / 10_000)
        creator_amount = remaining_after_platform - royalty_amount

        return {
            "totalAmount": amount,
            "totalAmountOctas": amount_in_octas,
            "breakdown": {
                "platformFee": {
                    "amount": platform_fee / 100_000_000,
                    "amountOctas": platform_fee,
                    "percentage": 2.5,
                    "basisPoints": platform_fee_bps,
                },
                "royalty": {
                    "amount": royalty_amount / 100_000_000,
                    "amountOctas": royalty_amount,
                    "percentage": 10,
                    "basisPoints": royalty_bps,
                },
                "creator": {
                    "amount": creator_amount / 100_000_000,
                    "amountOctas": creator_amount,
                },
            },
        }
    except Exception as err:
        return JSONResponse({"error": "Failed to calculate payment breakdown", "message": str(err)}, status_code=500)


# ==================== Walrus Storage Integration ====================

@app.post("/api/voice/process")
async def voice_process(
    audio: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(None),
    owner: str = Form(...),
    voiceId: str = Form(...),
):
    try:
        audio_buffer = await audio.read()
        mime_type = audio.content_type

        print("[API] Processing voice model...")
        bundle = voice_model.process_voice_model(
            audio_buffer=audio_buffer,
            mime_type=mime_type,
            name=name,
            description=description,
            owner=owner,
            voice_id=voiceId,
        )

        print("[API] Uploading bundle to Walrus...")
        upload_result = walrus_module.upload_to_walrus(
            owner_address=owner,
            voice_id=voiceId,
            bundle_files=bundle["files"],
        )

        return {
            "success": True,
            "uri": upload_result["walrusUri"],
            "walrusUri": upload_result["walrusUri"],
            "manifestBlobId": upload_result["manifestBlobId"],
            "previewUrl": upload_result.get("previewUrl"),
            "blobs": upload_result["blobs"],
            "cid": upload_result["manifestBlobId"],
            "bundle": {
                "config": bundle["config"],
                "meta": bundle["meta"],
            },
        }
    except Exception as err:
        print(f"[API] Voice processing error: {err}")
        return JSONResponse({"error": "Voice processing failed", "message": str(err)}, status_code=500)


@app.post("/api/walrus/upload")
async def walrus_upload(request: Request):
    try:
        form = await request.form()
        account = request.headers.get("x-sui-account") or str(form.get("owner") or "")
        voice_id = request.headers.get("x-voice-id") or str(form.get("voiceId") or "")

        if not account or not voice_id:
            return JSONResponse({"error": "Sui account and voice ID are required"}, status_code=400)

        bundle_files = {}
        for field_name in ["embedding.bin", "config.json", "meta.json", "preview.wav"]:
            upload = form.get(field_name)
            if upload and hasattr(upload, "read"):
                bundle_files[field_name] = await upload.read()

        if not bundle_files:
            return JSONResponse({"error": "No files provided"}, status_code=400)

        result = walrus_module.upload_to_walrus(
            owner_address=account,
            voice_id=voice_id,
            bundle_files=bundle_files,
        )

        return {
            "success": True,
            "uri": result["walrusUri"],
            "walrusUri": result["walrusUri"],
            "manifestBlobId": result["manifestBlobId"],
            "previewUrl": result.get("previewUrl"),
            "blobs": result["blobs"],
            "size": result["size"],
        }
    except Exception as err:
        print(f"[API] Walrus upload error: {err}")
        return JSONResponse({"error": "Walrus upload failed", "message": str(err)}, status_code=500)


@app.get("/api/walrus/blobs/{blob_id:path}")
async def walrus_blob(blob_id: str):
    try:
        file_buffer = walrus_module.download_from_walrus(blob_id)
        return Response(content=file_buffer, media_type="application/octet-stream")
    except walrus_module.WalrusFileNotFoundError as err:
        return JSONResponse({"error": "Blob not found", "message": str(err)}, status_code=404)
    except Exception as err:
        print(f"[API] Walrus blob error: {err}")
        return JSONResponse({"error": "Walrus blob fetch failed", "message": str(err)}, status_code=500)


@app.post("/api/walrus/download")
async def walrus_download(request: Request):
    try:
        data = await request.json()
        uri = data.get("uri")
        filename = data.get("filename")
        requester_account = data.get("requesterAccount")

        if not uri or not filename:
            return JSONResponse({"error": "URI and filename are required"}, status_code=400)

        if requester_account:
            has_access = walrus_module.verify_walrus_access(uri, requester_account)
            if not has_access:
                return JSONResponse({"error": "Access denied"}, status_code=403)

        manifest_blob_id = walrus_module.parse_walrus_uri(uri)
        file_buffer = walrus_module.download_file(manifest_blob_id, filename)
        return Response(content=file_buffer, media_type=_content_type_for(filename))
    except walrus_module.WalrusFileNotFoundError as err:
        return JSONResponse({"error": "File not found", "message": str(err)}, status_code=404)
    except Exception as err:
        print(f"[API] Walrus download error: name={type(err).__name__}, message={err}")
        return JSONResponse({"error": "Walrus download failed", "message": str(err)}, status_code=500)


@app.post("/api/walrus/delete")
async def walrus_delete(request: Request):
    try:
        data = await request.json()
        uri = data.get("uri")
        account = data.get("account")

        if not uri or not account:
            return JSONResponse({"error": "URI and account are required"}, status_code=400)

        if not uri.startswith("walrus://"):
            return JSONResponse({"error": "Invalid URI format. Must be a Walrus URI (walrus://...)"}, status_code=400)

        result = walrus_module.delete_from_walrus(uri, account)
        return result
    except Exception as err:
        print(f"[API] Walrus delete error: {err}")
        return JSONResponse({"error": "Walrus delete failed", "message": str(err)}, status_code=500)


# ==================== Legacy Walrus Routes ====================

@app.post("/api/walrus/upload")
async def walrus_upload(request: Request):
    try:
        uri = request.headers.get("x-walrus-uri")
        account = request.headers.get("x-sui-account") or request.headers.get("x-aptos-account")

        if not uri or not account:
            return JSONResponse({"error": "Walrus URI and account are required"}, status_code=400)

        match = re.match(r"^walrus://([^/]+)/([^/]+)/(.+)$", uri)
        if not match:
            return JSONResponse({"error": "Invalid Walrus URI format"}, status_code=400)

        parsed_account, namespace, voice_id = match.group(1), match.group(2), match.group(3)

        if parsed_account.lower() != account.lower():
            return JSONResponse({"error": "Account mismatch"}, status_code=403)

        form = await request.form()
        bundle_files = {}
        for field_name in ["embedding.bin", "config.json", "meta.json", "preview.wav"]:
            upload = form.get(field_name)
            if upload and hasattr(upload, "read"):
                bundle_files[field_name] = await upload.read()

        if not bundle_files:
            return JSONResponse({"error": "No files provided"}, status_code=400)

        result = walrus_module.upload_to_walrus(account, namespace, voice_id, bundle_files)

        return {
            "success": True,
            "uri": result["uri"],
            "cid": result["cid"],
            "size": result["size"],
        }
    except Exception as err:
        print(f"[API] Walrus upload error: {err}")
        return JSONResponse({"error": "Walrus upload failed", "message": str(err)}, status_code=500)


@app.post("/api/walrus/download")
async def walrus_download(request: Request):
    try:
        data = await request.json()
        uri = data.get("uri")
        filename = data.get("filename")
        requester_account = data.get("requesterAccount")

        if not uri or not filename:
            return JSONResponse({"error": "URI and filename are required"}, status_code=400)

        if requester_account:
            has_access = walrus_module.verify_walrus_access(uri, requester_account)
            if not has_access:
                return JSONResponse({"error": "Access denied"}, status_code=403)

        manifest_blob_id = walrus_module.parse_walrus_uri(uri)
        file_buffer = walrus_module.download_file(manifest_blob_id, filename)
        return Response(content=file_buffer, media_type=_content_type_for(filename))
    except walrus_module.WalrusFileNotFoundError as err:
        return JSONResponse({"error": "File not found", "message": str(err)}, status_code=404)
    except Exception as err:
        print(f"[API] Walrus download error: name={type(err).__name__}, message={err}")
        return JSONResponse({"error": "Walrus download failed", "message": str(err)}, status_code=500)


@app.post("/api/walrus/delete")
async def walrus_delete(request: Request):
    try:
        data = await request.json()
        uri = data.get("uri")
        account = data.get("account")

        if not uri or not account:
            return JSONResponse({"error": "URI and account are required"}, status_code=400)

        if not uri.startswith("walrus://"):
            return JSONResponse({"error": "Invalid URI format. Must be a Walrus URI (walrus://...)"}, status_code=400)

        result = walrus_module.delete_from_walrus(uri, account)
        return result
    except Exception as err:
        print(f"[API] Walrus delete error: {err}")
        return JSONResponse({"error": "Walrus delete failed", "message": str(err)}, status_code=500)


# ==================== Agent Deploy API ====================

@app.post("/api/agent/create")
async def agent_create(request: Request):
    try:
        data = await request.json()
        owner = data.get("owner")
        if not owner:
            return JSONResponse({"error": "owner is required"}, status_code=400)

        template_id = _pick(data, "templateId", "template_id", default="custom")
        agent_name = _pick(data, "agentName", "agent_name", default="My Agent")
        system_prompt = _pick(
            data,
            "systemPrompt",
            "system_prompt",
            default="You are a helpful assistant.",
        )
        explicit_skills = _pick(data, "skills", default=None)
        skills = explicit_skills if isinstance(explicit_skills, list) else _default_skills(template_id, agent_name, system_prompt)

        config = {
            "agent_name": agent_name,
            "template_id": template_id,
            "system_prompt": system_prompt,
            "agent_description": _pick(data, "agentDescription", "agent_description", default=""),
            "skills": [str(skill).strip().lower() for skill in skills if str(skill).strip()],
            "llm_provider": _pick(data, "llmProvider", "llm_provider", default="gpt-4o"),
            "price_per_call": float(_pick(data, "pricePerCall", "price_per_call", default=0.1)),
            "voice_name": _pick(data, "voiceName", "voice_name", default=""),
            "voice_uri": _pick(data, "voiceUri", "voice_uri", default=""),
            "voice_id": _pick(data, "voiceId", "voice_id", default=""),
            "language": _pick(data, "language", "language_code", default="en-IN"),
            "x402_enabled": bool(_pick(data, "x402Enabled", "x402_enabled", default=True)),
            "x402_price_sui": float(_pick(data, "x402PriceSui", "x402_price_sui", default=0.1)),
            "x402_uses": int(_pick(data, "x402Uses", "x402_uses", default=2)),
        }

        agent = agent_store.create_agent(owner, config)
        return {"success": True, "agent": agent}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/agent/list")
async def agent_list(owner: str):
    try:
        agents = agent_store.list_agents(owner)
        return {"agents": agents}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/agent/worker-status")
async def agent_worker_status():
    running = _agent_worker_process is not None and _agent_worker_process.poll() is None
    mcp_running = (_mcp_server_process is not None and _mcp_server_process.poll() is None) or _is_port_open(
        os.getenv("MCP_HOST", "127.0.0.1"),
        int(os.getenv("MCP_PORT", "8001")),
    )
    return {
        "running": running,
        "pid": _agent_worker_process.pid if running else None,
        "logPath": str(_agent_worker_log_path()),
        "agentName": livekit_service.LIVEKIT_AGENT_NAME,
        "mcpRunning": mcp_running,
        "mcpLogPath": str(_mcp_server_log_path()),
    }


@app.get("/api/agent/discover")
async def agent_discover(skill: str = "", language: str = "", limit: int = 5, exclude_agent_id: str = ""):
    try:
        agents = agent_index.discover(
            skill=skill,
            language=language or None,
            limit=limit,
            exclude_agent_id=exclude_agent_id,
        )
        return {"agents": agents, "count": len(agents)}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/agent/register-skill")
async def agent_register_skill(request: Request):
    try:
        data = await request.json()
        agent_id = data.get("agent_id") or data.get("agentId") or ""
        if not agent_id:
            return JSONResponse({"error": "agent_id is required"}, status_code=400)

        updated = agent_index.register_skills(
            agent_id=agent_id,
            skills=data.get("skills", []),
            language=data.get("language", "en-IN"),
            description=data.get("description", ""),
        )
        if not updated:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        return {"success": True, "agent": updated}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/agent/delegate/{agent_id}")
async def agent_delegate(agent_id: str, request: Request):
    try:
        data = await request.json()
        current_depth = int(data.get("current_depth", 0))
        max_depth = int(data.get("max_delegation_depth", 2))
        if current_depth >= max_depth:
            return JSONResponse({"error": "Delegation depth limit reached"}, status_code=409)

        target = agent_store.get_agent(agent_id)
        if not target:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if target.get("status") != "live":
            return JSONResponse({"error": "Target agent is not live"}, status_code=503)

        source_agent_id = data.get("source_agent_id", "")
        if source_agent_id and source_agent_id == agent_id:
            return JSONResponse({"error": "An agent cannot delegate to itself"}, status_code=400)

        answer = await _generate_delegate_answer(target, data)
        agent_index.increment_calls(agent_id)

        return {
            "success": True,
            "agent": _public_agent(target),
            "answer": answer,
            "delegation_depth": current_depth + 1,
            "handoff_mode": "private_text",
        }
    except ValueError as err:
        return JSONResponse({"error": str(err)}, status_code=400)
    except Exception as err:
        print(f"[AgentDelegate] error: {err}")
        return JSONResponse({"error": "Agent delegation failed", "message": str(err)}, status_code=500)


@app.post("/api/agent/invite/{agent_id}")
async def agent_invite(agent_id: str, request: Request):
    try:
        data = await request.json()
        target = agent_store.get_agent(agent_id)
        if not target:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if target.get("status") != "live":
            return JSONResponse({"error": "Target agent is not live"}, status_code=503)

        room_name = data.get("roomName") or data.get("room_name") or ""
        if not room_name.startswith("vv-"):
            return JSONResponse({"error": "roomName must be a VoiceVault LiveKit room"}, status_code=400)

        source_agent_id = data.get("source_agent_id", "")
        if not source_agent_id and room_name.startswith("vv-"):
            source_agent_id = room_name[3:]
        if source_agent_id and source_agent_id == agent_id:
            return JSONResponse({"error": "An agent cannot invite itself"}, status_code=400)

        current_depth = int(data.get("current_depth", 0))
        if current_depth >= int(data.get("max_delegation_depth", 2)):
            return JSONResponse({"error": "Delegation depth limit reached"}, status_code=409)

        worker_running, worker_started, worker_error = _ensure_agent_worker()
        if worker_started:
            await asyncio.sleep(float(os.getenv("LIVEKIT_WORKER_STARTUP_GRACE_SECONDS", "2")))
        if not worker_running:
            return JSONResponse({"error": worker_error or "Agent worker is not running"}, status_code=503)

        is_transfer = bool(data.get("transfer"))
        is_handoff = bool(data.get("handoff"))
        metadata = json.dumps(
            {
                "agent_id": agent_id,
                "target_agent_id": agent_id,
                "source_agent_id": source_agent_id,
                "source_participant_identity": data.get("source_participant_identity", ""),
                "agent_name": target.get("agent_name", ""),
                "room_name": room_name,
                "user_identity": data.get("user_identity", ""),
                "mode": "room_invite",
                "question": data.get("question", ""),
                "context_summary": data.get("context_summary", ""),
                "recent_turns_json": data.get("recent_turns_json", "[]"),
                "current_depth": current_depth + 1,
                "handoff": is_handoff,
                "transfer": is_transfer,
            },
            ensure_ascii=False,
        )
        if is_transfer or is_handoff:
            handoff_id = data.get("handoff_id") or str(int(time.time() * 1000))
            dispatch_mode = "transfer" if is_transfer else "handoff"
            dispatch_key = f"{dispatch_mode}:{room_name}:{agent_id}:{source_agent_id or 'unknown'}:{handoff_id}"
        else:
            dispatch_key = f"invite:{room_name}:{agent_id}:{source_agent_id or 'unknown'}"
        dispatched, dispatch_error = await livekit_service.ensure_agent_dispatch(room_name, metadata, dispatch_key=dispatch_key)
        if not dispatched:
            return JSONResponse({"error": dispatch_error or "Failed to invite agent"}, status_code=503)

        removed_source = False
        remove_source_error = None
        if is_transfer and data.get("source_participant_identity"):
            removed_source, remove_source_error = await livekit_service.remove_participant(
                room_name,
                data.get("source_participant_identity"),
            )

        return {
            "success": True,
            "roomName": room_name,
            "agent": _public_agent(target),
            "agentDispatched": True,
            "sourceAgentRemoved": removed_source,
            "sourceAgentRemoveError": remove_source_error,
            "handoff_mode": "live_room_handoff" if is_handoff else "live_room_invite",
        }
    except Exception as err:
        print(f"[AgentInvite] error: {err}")
        return JSONResponse({"error": "Agent invite failed", "message": str(err)}, status_code=500)


@app.get("/api/agent/{agent_id}")
async def agent_get(agent_id: str):
    agent = agent_store.get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    agent = {**agent}
    base_url = os.getenv("BACKEND_URL", f"http://localhost:{os.getenv('PORT', '8000')}").rstrip("/")
    agent.setdefault("endpoint", f"{base_url}/api/agent/delegate/{agent_id}")
    agent.setdefault("skills", [])
    agent.setdefault("language", "en-IN")
    agent.setdefault("agent_description", "")
    return {"agent": agent}


@app.post("/api/agent/deploy/{agent_id}")
async def agent_deploy(agent_id: str):
    try:
        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        room = await _prepare_livekit_room(agent, "user")
        room_error = _livekit_room_error(room)
        if room_error:
            return JSONResponse({"error": room_error, **room}, status_code=503)

        agent_store.update_agent(agent_id, {"status": "live"})

        return {
            "success":   True,
            **room,
        }
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/agent/pause/{agent_id}")
async def agent_pause(agent_id: str):
    updated = agent_store.update_agent(agent_id, {"status": "paused"})
    if not updated:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return {"success": True, "agent": updated}


@app.post("/api/agent/resume/{agent_id}")
async def agent_resume(agent_id: str):
    updated = agent_store.update_agent(agent_id, {"status": "live"})
    if not updated:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return {"success": True, "agent": updated}


@app.delete("/api/agent/{agent_id}")
async def agent_delete(agent_id: str):
    deleted = agent_store.delete_agent(agent_id)
    if not deleted:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return {"success": True}


@app.post("/api/agent/join/{agent_id}")
async def agent_join(agent_id: str, request: Request):
    try:
        data = await request.json()
        participant = data.get("participantName", "user")
        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if agent.get("status") == "paused":
            return JSONResponse({"error": "Agent is paused"}, status_code=503)

        room = await _prepare_livekit_room(agent, participant)
        room_error = _livekit_room_error(room)
        if room_error:
            return JSONResponse({"error": room_error, **room}, status_code=503)

        return {
            **room,
        }
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/agent/talk/{agent_id}")
async def agent_talk(agent_id: str, request: Request):
    try:
        try:
            data = await request.json()
        except Exception:
            data = {}
        identity = _pick(data, "identity", "participantName", default="user")

        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if agent.get("status") != "live":
            return JSONResponse({"error": "Agent is not live. Deploy or resume it first."}, status_code=503)

        room = await _prepare_livekit_room(agent, identity)
        room_error = _livekit_room_error(room)
        if room_error:
            return JSONResponse({"error": room_error, **room}, status_code=503)

        return {"success": True, **room}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


# ==================== x402 Pay-Per-Use Routes ====================

@app.get("/api/x402/requirements")
async def x402_requirements(voice_id: str, creator: str = ""):
    """Return payment requirements for a voice (called before paying)."""
    price_mist = x402_module.DEFAULT_PRICE_MIST
    return x402_module.make_402_response(voice_id, price_mist, creator, "/api/tts/generate")


@app.post("/api/x402/verify")
async def x402_verify(request: Request):
    """Verify a payment proof without consuming it."""
    try:
        data = await request.json()
        tx_digest    = data.get("txDigest", "")
        payer        = data.get("payer", "")
        recipient    = data.get("recipient", "")
        amount_mist  = int(data.get("amountMist", x402_module.DEFAULT_PRICE_MIST))

        ok, reason = x402_module.verify_sui_payment(tx_digest, payer, recipient, amount_mist)
        return {"valid": ok, "reason": reason}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/x402/create-pass")
async def x402_create_pass(request: Request):
    """Verify payment and issue a UsagePass."""
    try:
        data         = await request.json()
        tx_digest    = data.get("txDigest", "")
        payer        = data.get("payer", "")
        voice_id     = data.get("voiceId", "")
        creator      = data.get("creator", "")
        amount_mist  = int(data.get("amountMist", x402_module.DEFAULT_PRICE_MIST))
        uses         = int(data.get("uses", x402_module.DEFAULT_USES))

        if not tx_digest or not payer or not voice_id:
            return JSONResponse({"error": "txDigest, payer, voiceId required"}, status_code=400)

        ok, reason = x402_module.verify_sui_payment(tx_digest, payer, creator, amount_mist)
        if not ok:
            return JSONResponse({"error": "Payment verification failed", "reason": reason}, status_code=402)

        record = usage_store.create_pass(payer, voice_id, uses=uses, tx_digest=tx_digest)
        return {"success": True, "pass": record}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/x402/consume")
async def x402_consume(request: Request):
    """Consume one use from a UsagePass."""
    try:
        data    = await request.json()
        pass_id = data.get("passId", "")
        if not pass_id:
            return JSONResponse({"error": "passId required"}, status_code=400)
        record = usage_store.consume_pass(pass_id)
        if not record:
            return JSONResponse({"error": "Pass not found or exhausted"}, status_code=404)
        return {"success": True, "pass": record}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/x402/status")
async def x402_status(user: str, voice_id: str):
    """Check if user has an active UsagePass for a voice."""
    ok, record = usage_store.has_access(user, voice_id)
    return {
        "hasAccess":       ok,
        "usesRemaining":   record["uses_remaining"] if record else 0,
        "expiresAt":       record["expires_at"] if record else 0,
        "passId":          record["id"] if record else None,
    }


@app.get("/api/x402/passes")
async def x402_passes(user: str):
    """List all UsagePasses for a user."""
    passes = usage_store.list_passes_for_user(user)
    return {"passes": passes}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Voice server running -> http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
