import atexit
import hashlib
import math
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, FileResponse
import uvicorn

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

import database
import voice_model
import x402 as x402_module
import usage_store
import agent_store
import agent_index
import livekit_service
import payment as payment_module
import sarvam
import chatterbox

AUDIO_DIR = BACKEND_DIR / "storage" / "audio"
PREVIEW_DIR = BACKEND_DIR / "storage" / "previews"

def _ensure_dirs():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

_ensure_dirs()
database.init_db()

app = FastAPI(title="SwaraOS API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Voice Upload ====================

@app.post("/api/voice/upload")
async def voice_upload(
    audio: UploadFile = File(...),
    name: str = Form(...),
    owner: str = Form(...),
    description: str = Form(""),
    price_per_use: int = Form(0),
):
    try:
        audio_buffer = await audio.read()
        if len(audio_buffer) > 50 * 1024 * 1024:
            return JSONResponse({"error": "File too large (max 50MB)"}, status_code=400)

        voice_id = f"voice_{uuid.uuid4().hex}"

        # Normalize audio with FFmpeg
        normalized = voice_model.normalize_audio(audio_buffer, audio.content_type or "audio/wav")

        # SHA256 hash for on-chain anchoring
        audio_hash = "0x" + hashlib.sha256(normalized).hexdigest()

        # Store MP3 (store normalized WAV as .mp3 filename for simplicity)
        audio_path = AUDIO_DIR / f"{voice_id}.mp3"
        audio_path.write_bytes(normalized)

        # Preview: first 5 seconds (16kHz mono = 16000 samples/s * 2 bytes)
        preview_bytes = normalized[:min(len(normalized), 160000)]
        preview_path = PREVIEW_DIR / f"{voice_id}.wav"
        preview_path.write_bytes(preview_bytes)

        # Persist to SQLite
        record = database.insert_voice(
            voice_id=voice_id,
            owner_address=owner,
            name=name,
            description=description,
            audio_hash=audio_hash,
            audio_path=str(audio_path),
            preview_path=str(preview_path),
            price_per_use=price_per_use,
        )

        return {
            "success": True,
            "voice_id": voice_id,
            "audio_hash": audio_hash,
            "preview_url": f"/api/preview/{voice_id}",
        }
    except Exception as err:
        print(f"[Upload] error: {err}")
        return JSONResponse({"error": "Upload failed", "message": str(err)}, status_code=500)


# ==================== Voice Query ====================

@app.get("/api/voice/list")
async def voice_list():
    try:
        voices = database.list_voices()
        for v in voices:
            v.pop("audio_path", None)
            v.pop("preview_path", None)
            v["preview_url"] = f"/api/preview/{v['voice_id']}"
        return {"voices": voices}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/voice/{voice_id}")
async def voice_get(voice_id: str):
    record = database.get_voice(voice_id)
    if not record:
        return JSONResponse({"error": "Voice not found"}, status_code=404)
    record.pop("audio_path", None)
    record.pop("preview_path", None)
    record["preview_url"] = f"/api/preview/{voice_id}"
    return record


# ==================== On-chain ID sync ====================

@app.patch("/api/voice/{voice_id}/on-chain-id")
async def voice_set_on_chain_id(voice_id: str, request: Request):
    """Called by the frontend after VoiceRegistry.registerVoice() is confirmed."""
    try:
        data = await request.json()
        on_chain_id = data.get("on_chain_id")
        tx_hash = data.get("tx_hash", "")
        if on_chain_id is None:
            return JSONResponse({"error": "on_chain_id required"}, status_code=400)
        record = database.get_voice(voice_id)
        if not record:
            return JSONResponse({"error": "Voice not found"}, status_code=404)
        updated = database.set_on_chain_id(voice_id, int(on_chain_id), tx_hash)
        updated.pop("audio_path", None)
        updated.pop("preview_path", None)
        return {"success": True, "voice": updated}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


# ==================== Audio Serving ====================

@app.get("/api/preview/{voice_id}")
async def serve_preview(voice_id: str):
    record = database.get_voice(voice_id)
    if not record:
        return JSONResponse({"error": "Voice not found"}, status_code=404)
    path = Path(record["preview_path"])
    if not path.exists():
        return JSONResponse({"error": "Preview not found"}, status_code=404)
    return FileResponse(str(path), media_type="audio/wav")


@app.get("/api/audio/{voice_id}")
async def serve_audio(voice_id: str, requester: str = ""):
    record = database.get_voice(voice_id)
    if not record:
        return JSONResponse({"error": "Voice not found"}, status_code=404)
    if requester.lower() != record["owner_address"].lower():
        return JSONResponse({"error": "Access denied"}, status_code=403)
    path = Path(record["audio_path"])
    if not path.exists():
        return JSONResponse({"error": "Audio not found"}, status_code=404)
    return FileResponse(str(path), media_type="audio/wav")


# ==================== TTS Generation ====================

@app.post("/api/tts/generate")
async def tts_generate(request: Request):
    try:
        data = await request.json()
        voice_id = data.get("voice_id") or data.get("voiceId")
        text = data.get("text", "")
        requester = (data.get("requester_account") or data.get("requesterAccount") or "").lower()

        if not voice_id:
            return JSONResponse({"error": "voice_id required"}, status_code=400)
        if not text:
            return JSONResponse({"error": "text required"}, status_code=400)

        record = database.get_voice(voice_id)
        if not record:
            return JSONResponse({"error": "Voice not found"}, status_code=404)

        # Access control hierarchy
        is_owner = requester and requester == record["owner_address"].lower()

        if not is_owner:
            has_lic = requester and database.has_license(requester, voice_id)

            has_pass = False
            active_pass_id = None
            if not has_lic and requester:
                ok, pass_record = usage_store.has_access(requester, voice_id)
                if ok and pass_record:
                    has_pass = True
                    active_pass_id = pass_record["id"]

            if not has_lic and not has_pass:
                payment_proof = request.headers.get("X-Payment-Proof", "")
                if payment_proof and requester:
                    creator = record["owner_address"]
                    min_amount = record["price_per_use"] or x402_module.DEFAULT_PRICE_WEI
                    ok, err = x402_module.verify_monad_transaction(payment_proof, requester, creator, min_amount)
                    if ok:
                        database.record_payment_proof(payment_proof, requester)
                        pass_record = usage_store.create_pass(requester, voice_id, tx_digest=payment_proof)
                        active_pass_id = pass_record["id"]
                        has_pass = True

            if not has_lic and not has_pass:
                price_wei = record["price_per_use"]
                if price_wei == 0:
                    # Free voice — grant access without payment
                    pass
                else:
                    creator = record["owner_address"]
                    return JSONResponse(
                        x402_module.make_402_response(voice_id, price_wei, creator, "/api/tts/generate"),
                        status_code=402,
                    )

            if has_pass and active_pass_id and not has_lic:
                usage_store.consume_pass(active_pass_id)

        try:
            audio_bytes = chatterbox.text_to_speech(text, record["audio_path"])
        except Exception as tts_err:
            print(f"[TTS] Chatterbox failed ({tts_err}), falling back to Sarvam")
            language_code = data.get("language_code", "en-IN")
            audio_bytes = sarvam.text_to_speech(text, language_code=language_code)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as err:
        print(f"[TTS] error: {err}")
        return JSONResponse({"error": "TTS failed", "message": str(err)}, status_code=500)


# ==================== STT Transcription ====================

@app.post("/api/stt/transcribe")
async def stt_transcribe(
    audio: UploadFile = File(...),
    language_code: str = Form("en-IN"),
):
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            return JSONResponse({"error": "Empty audio file"}, status_code=400)

        transcript = sarvam.speech_to_text(audio_bytes, language_code=language_code)
        return {"transcript": transcript, "language_code": language_code}
    except Exception as err:
        print(f"[STT] error: {err}")
        return JSONResponse({"error": "Transcription failed", "message": str(err)}, status_code=500)


# ==================== Payment ====================

@app.get("/api/licenses/{buyer_address}")
async def get_licenses(buyer_address: str):
    voices = database.get_licenses_for_buyer(buyer_address)
    return {"voices": voices}


@app.post("/api/license/grant")
async def license_grant(request: Request):
    """Grant backend-side access to a voice without requiring on-chain payment.
    Used for voices not yet registered on-chain."""
    try:
        data = await request.json()
        voice_id = data.get("voice_id", "")
        buyer_address = data.get("buyer_address", "")
        if not voice_id or not buyer_address:
            return JSONResponse({"error": "voice_id and buyer_address required"}, status_code=400)
        record = database.get_voice(voice_id)
        if not record:
            return JSONResponse({"error": "Voice not found"}, status_code=404)
        if record["owner_address"].lower() == buyer_address.lower():
            return JSONResponse({"error": "You already own this voice"}, status_code=400)
        if database.has_license(buyer_address, voice_id):
            return JSONResponse({"already": True, "voice_id": voice_id})
        result = database.insert_license(buyer_address, voice_id, tx_hash="offchain")
        return {"granted": True, **result}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/payment/verify")
async def payment_verify(request: Request):
    try:
        data = await request.json()
        tx_hash = data.get("tx_hash", "")
        buyer = data.get("buyer_address", "")
        voice_id = data.get("voice_id", "")

        if not tx_hash or not buyer or not voice_id:
            return JSONResponse({"error": "tx_hash, buyer_address, voice_id required"}, status_code=400)

        record = database.get_voice(voice_id)
        if not record:
            return JSONResponse({"error": "Voice not found"}, status_code=404)

        creator = record["owner_address"]
        min_amount = record["price_per_use"] or x402_module.DEFAULT_PRICE_WEI

        ok, reason = x402_module.verify_monad_transaction(tx_hash, buyer, creator, min_amount)
        if ok:
            database.record_payment_proof(tx_hash, buyer)
            database.insert_license(buyer, voice_id, tx_hash)

        return {"verified": ok, "reason": reason}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/payment/breakdown")
async def payment_breakdown(request: Request):
    try:
        data = await request.json()
        amount = data.get("amount") or data.get("totalAmount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return JSONResponse({"error": "Invalid amount"}, status_code=400)

        # Treat as MON units (wei)
        total_wei = int(amount)
        breakdown = payment_module.calculate_breakdown(total_wei)
        return breakdown
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


# ==================== x402 Routes ====================

@app.get("/api/x402/requirements")
async def x402_requirements(voice_id: str, creator: str = ""):
    record = database.get_voice(voice_id)
    price_wei = (record["price_per_use"] if record else 0) or x402_module.DEFAULT_PRICE_WEI
    return x402_module.make_402_response(voice_id, price_wei, creator, "/api/tts/generate")


@app.post("/api/x402/create-pass")
async def x402_create_pass(request: Request):
    try:
        data = await request.json()
        tx_hash = data.get("txHash") or data.get("tx_hash", "")
        payer = data.get("payer", "")
        voice_id = data.get("voiceId") or data.get("voice_id", "")
        creator = data.get("creator", "")
        uses = int(data.get("uses", x402_module.DEFAULT_USES))

        if not tx_hash or not payer or not voice_id:
            return JSONResponse({"error": "txHash, payer, voiceId required"}, status_code=400)

        record = database.get_voice(voice_id)
        min_amount = (record["price_per_use"] if record else 0) or x402_module.DEFAULT_PRICE_WEI

        ok, reason = x402_module.verify_monad_transaction(tx_hash, payer, creator, min_amount)
        if not ok:
            return JSONResponse({"error": "Payment verification failed", "reason": reason}, status_code=402)

        database.record_payment_proof(tx_hash, payer)
        pass_record = usage_store.create_pass(payer, voice_id, uses=uses, tx_digest=tx_hash)
        return {"success": True, "pass": pass_record}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/x402/status")
async def x402_status(user: str, voice_id: str):
    ok, record = usage_store.has_access(user, voice_id)
    return {
        "hasAccess": ok,
        "usesRemaining": record["uses_remaining"] if record else 0,
        "expiresAt": record["expires_at"] if record else 0,
        "passId": record["id"] if record else None,
    }


@app.get("/api/x402/passes")
async def x402_passes(user: str):
    return {"passes": usage_store.list_passes_for_user(user)}


# ==================== Agent Routes ====================

# ==================== Agent Discovery & Delegation ====================

@app.get("/api/agent/discover")
async def agent_discover(skill: str, language: str = "", limit: int = 5):
    results = agent_index.discover(
        skill=skill,
        language=language or None,
        limit=min(limit, 20),
    )
    return {"agents": results, "count": len(results)}


@app.post("/api/agent/register-skill")
async def agent_register_skill(request: Request):
    try:
        data = await request.json()
        agent_id = data.get("agent_id", "")
        skills = data.get("skills", [])
        language = data.get("language", "en-IN")

        if not agent_id:
            return JSONResponse({"error": "agent_id required"}, status_code=400)

        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        updated = agent_index.register_skills(agent_id, skills, language)
        return {"success": True, "agent": updated}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.post("/api/agent/call/{agent_id}")
async def agent_call(agent_id: str, request: Request):
    """
    Delegated TTS endpoint — callable by other agents or humans.
    Applies x402 access control and calls Sarvam TTS on behalf of the agent's voice.
    """
    try:
        data = await request.json()
        text = data.get("text", "").strip()
        requester = (data.get("requester_account") or "").lower()
        language_code = data.get("language_code", "en-IN")

        if not text:
            return JSONResponse({"error": "text required"}, status_code=400)

        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if agent.get("status") != "live":
            return JSONResponse({"error": "Agent is not live"}, status_code=503)

        voice_id = agent.get("voice_id", "")
        price_per_call_wei = int(agent.get("price_per_call", 0.1) * 1e18)

        # x402 access check — owner of the agent's voice gets free access
        record = database.get_voice(voice_id) if voice_id else None
        is_owner = record and requester and requester == record["owner_address"].lower()

        if not is_owner and price_per_call_wei > 0:
            payment_proof = request.headers.get("X-Payment-Proof", "")
            if not payment_proof:
                return JSONResponse(
                    x402_module.make_402_response(voice_id or agent_id, price_per_call_wei, agent["owner"], f"/api/agent/call/{agent_id}"),
                    status_code=402,
                )

            creator = agent["owner"]
            ok, err = x402_module.verify_monad_transaction(payment_proof, requester, creator, price_per_call_wei)
            if not ok:
                return JSONResponse({"error": "Payment verification failed", "reason": err}, status_code=402)

            database.record_payment_proof(payment_proof, requester)

        # Generate speech
        lang = language_code or agent.get("language", "en-IN")
        audio_bytes = sarvam.text_to_speech(text, language_code=lang)

        # Track call metrics
        agent_index.increment_calls(agent_id, earned_wei=price_per_call_wei)

        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as err:
        print(f"[AgentCall] error: {err}")
        return JSONResponse({"error": "Agent call failed", "message": str(err)}, status_code=500)


@app.post("/api/agent/create")
async def agent_create(request: Request):
    try:
        data = await request.json()
        owner = data.get("owner")
        if not owner:
            return JSONResponse({"error": "owner required"}, status_code=400)
        config = {
            "agent_name": data.get("agentName", "My Agent"),
            "template_id": data.get("templateId", "custom"),
            "system_prompt": data.get("systemPrompt", "You are a helpful assistant."),
            "llm_provider": data.get("llmProvider", "gpt-4o"),
            "price_per_call": float(data.get("pricePerCall", 0.1)),
            "voice_name": data.get("voiceName", ""),
            "voice_id": data.get("voiceId", ""),
        }
        agent = agent_store.create_agent(owner, config)
        return {"success": True, "agent": agent}
    except Exception as err:
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/agent/list")
async def agent_list(owner: str):
    return {"agents": agent_store.list_agents(owner)}


@app.get("/api/agent/{agent_id}")
async def agent_get(agent_id: str):
    agent = agent_store.get_agent(agent_id)
    if not agent:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return {"agent": agent}


@app.post("/api/agent/deploy/{agent_id}")
async def agent_deploy(agent_id: str):
    try:
        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        room_name = agent["room_name"]
        user_token = livekit_service.create_token(room_name, "user")
        join_url = livekit_service.get_join_url(room_name, user_token)
        agent_store.update_agent(agent_id, {"status": "live"})
        return {"success": True, "roomName": room_name, "joinUrl": join_url, "userToken": user_token}
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


# ==================== Agent Worker Process Management ====================

_agent_worker_process = None


def _ensure_agent_worker() -> bool:
    """Ensure the LiveKit agent worker subprocess is running.

    Returns True if the worker is (or just became) running.
    """
    global _agent_worker_process

    # Already running?
    if _agent_worker_process is not None and _agent_worker_process.poll() is None:
        return True

    # LiveKit credentials available?
    if not livekit_service.is_configured():
        print("[Server] LiveKit not configured — cannot start agent worker")
        return False

    # OpenAI key available?
    if not os.getenv("OPENAI_API_KEY"):
        print("[Server] OPENAI_API_KEY not set — cannot start agent worker")
        return False

    worker_script = BACKEND_DIR / "agent_worker.py"
    if not worker_script.exists():
        print("[Server] agent_worker.py not found")
        return False

    # Prepare environment (inherit current env so .env vars are available)
    env = os.environ.copy()

    # Platform-specific process flags
    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    # Log output to a file so it doesn't block the subprocess pipe
    log_file = BACKEND_DIR / "storage" / "agent_worker.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        _agent_worker_process = subprocess.Popen(
            [sys.executable, str(worker_script), "dev"],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=open(log_file, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            **kwargs,
        )
        print(f"[Server] OK Agent worker started (PID {_agent_worker_process.pid})")
        print(f"[Server]    Logs -> {log_file}")
        return True
    except Exception as err:
        print(f"[Server] Failed to start agent worker: {err}")
        return False


def _stop_agent_worker():
    """Terminate the agent worker subprocess if running."""
    global _agent_worker_process
    if _agent_worker_process is not None and _agent_worker_process.poll() is None:
        print(f"[Server] Stopping agent worker (PID {_agent_worker_process.pid})...")
        try:
            _agent_worker_process.terminate()
            _agent_worker_process.wait(timeout=5)
        except Exception:
            _agent_worker_process.kill()
        _agent_worker_process = None


# Clean up worker on server exit
atexit.register(_stop_agent_worker)


# ==================== Talk (Voice Conversation) ====================

@app.post("/api/agent/talk/{agent_id}")
async def agent_talk(agent_id: str, request: Request):
    """
    Start a voice conversation with a deployed agent.

    - Generates a fresh LiveKit room token for the caller.
    - Auto-launches the agent worker subprocess if not already running.
    - Returns a joinUrl the frontend can open in a new tab.
    """
    try:
        agent = agent_store.get_agent(agent_id)
        if not agent:
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        if agent.get("status") != "live":
            return JSONResponse(
                {"error": "Agent is not live. Deploy or resume it first."},
                status_code=503,
            )

        room_name = agent["room_name"]

        # Parse optional identity from request body
        identity = "user"
        try:
            data = await request.json()
            identity = data.get("identity", "user") or "user"
        except Exception:
            pass

        # Generate user token for the LiveKit room
        user_token = livekit_service.create_token(room_name, identity)
        join_url = livekit_service.get_join_url(room_name, user_token)

        # Make sure the agent worker is running
        worker_ok = _ensure_agent_worker()

        if not join_url:
            return JSONResponse(
                {
                    "error": "LiveKit not configured",
                    "message": "Add LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET to .env",
                },
                status_code=503,
            )

        return {
            "success": True,
            "joinUrl": join_url,
            "userToken": user_token,
            "roomName": room_name,
            "workerRunning": worker_ok,
        }
    except Exception as err:
        print(f"[Talk] error: {err}")
        return JSONResponse({"error": str(err)}, status_code=500)


@app.get("/api/agent/worker-status")
async def agent_worker_status():
    """Check if the agent worker subprocess is running."""
    running = _agent_worker_process is not None and _agent_worker_process.poll() is None
    return {
        "running": running,
        "pid": _agent_worker_process.pid if running else None,
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"SwaraOS API running -> http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
