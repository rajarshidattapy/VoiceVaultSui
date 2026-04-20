import math
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import uvicorn

# Load .env from project root (one level up from backend/)
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BACKEND_DIR.parent / ".env")

import voice_model
import walrus as walrus_module
import agent_store
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

        config = {
            "agent_name":    data.get("agentName", "My Agent"),
            "template_id":   data.get("templateId", "custom"),
            "system_prompt": data.get("systemPrompt", "You are a helpful assistant."),
            "llm_provider":  data.get("llmProvider", "gpt-4o"),
            "price_per_call":float(data.get("pricePerCall", 0.1)),
            "voice_name":    data.get("voiceName", ""),
            "voice_uri":     data.get("voiceUri", ""),
            "voice_id":      data.get("voiceId", ""),
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
        join_url   = livekit_service.get_join_url(room_name, user_token)
        start_cmd  = livekit_service.agent_start_command(room_name)

        agent_store.update_agent(agent_id, {"status": "live"})

        return {
            "success":   True,
            "roomName":  room_name,
            "joinUrl":   join_url,
            "userToken": user_token,
            "startCmd":  start_cmd,
            "liveKitConfigured": livekit_service.is_configured(),
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

        room_name  = agent["room_name"]
        user_token = livekit_service.create_token(room_name, participant)
        join_url   = livekit_service.get_join_url(room_name, user_token)

        return {
            "roomName":  room_name,
            "token":     user_token,
            "joinUrl":   join_url,
            "liveKitConfigured": livekit_service.is_configured(),
        }
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
