"""
Voice Model Generation Pipeline

Converts raw audio into embedding-based voice models:
1. Audio normalization (16kHz, mono, WAV)
2. Embedding generation (voice characteristics extraction)
3. Bundle creation (embedding.bin, config.json, meta.json, preview.wav)

NOTE: This is a simplified implementation. In production, you would:
- Use actual voice embedding models (e.g., Resemblyzer, GE2E, etc.)
- Handle longer audio files with chunking
- Support multiple embedding formats
"""

import hashlib
import json
import struct
import subprocess
import time


def normalize_audio(audio_buffer, mime_type="audio/wav"):
    """
    Normalize audio file: Convert to WAV, 16kHz, mono
    Uses ffmpeg if available, otherwise falls back to basic processing
    """
    try:
        if _check_ffmpeg():
            return _normalize_with_ffmpeg(audio_buffer, mime_type)
        else:
            # Fallback: return as-is (assume already normalized)
            # In production, you'd want a proper fallback or require ffmpeg
            print("[VoiceModel] FFmpeg not available, using audio as-is")
            return audio_buffer
    except Exception as error:
        print(f"[VoiceModel] Audio normalization error: {error}")
        raise RuntimeError(f"Audio normalization failed: {error}")


def _check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def _normalize_with_ffmpeg(audio_buffer, mime_type):
    """Normalize audio using ffmpeg."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", "pipe:0",          # Input from stdin
                "-ar", "16000",           # Sample rate: 16kHz
                "-ac", "1",               # Channels: mono
                "-f", "wav",              # Format: WAV
                "-acodec", "pcm_s16le",   # Codec: PCM 16-bit little-endian
                "pipe:1",                 # Output to stdout
            ],
            input=audio_buffer,
            capture_output=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {result.stderr.decode()}")

        return result.stdout
    except FileNotFoundError:
        raise RuntimeError("FFmpeg not found")


def generate_embedding(normalized_audio):
    """
    Generate voice embedding from normalized audio

    NOTE: This is a placeholder. In production, you would:
    - Use a trained embedding model (e.g., Resemblyzer, GE2E, etc.)
    - Extract voice characteristics as a fixed-size vector
    - Return binary embedding data

    For now, we generate a deterministic hash-based "embedding"
    (This is NOT secure/production-ready, just for demonstration)
    """
    try:
        # TODO: Replace with actual embedding model inference
        # Example: embedding = embedding_model.encode(normalized_audio)

        # Placeholder: Generate deterministic "embedding" from audio hash
        # In production, use actual voice embedding models
        hash_bytes = hashlib.sha256(normalized_audio).digest()

        # Create a 256-dimensional embedding (placeholder)
        # Real embeddings would be from a trained model
        embedding_size = 256
        embedding = bytearray(embedding_size * 4)  # float32 = 4 bytes

        # Fill with deterministic values based on hash
        for i in range(embedding_size):
            hash_index = i % len(hash_bytes)
            value = (hash_bytes[hash_index] / 255.0 - 0.5) * 2.0  # Normalize to [-1, 1]
            struct.pack_into("<f", embedding, i * 4, value)

        return {
            "data": bytes(embedding),
            "size": embedding_size,
            "format": "float32",
        }
    except Exception as error:
        print(f"[VoiceModel] Embedding generation error: {error}")
        raise RuntimeError(f"Embedding generation failed: {error}")


def create_voice_bundle(name, description, owner, voice_id, normalized_audio, embedding, preview_audio=None):
    """Create voice model bundle."""
    # Create config.json
    config = {
        "modelVersion": "1.0.0",
        "sampleRate": 16000,
        "channels": 1,
        "format": "wav",
        "embeddingSize": embedding["size"],
        "embeddingFormat": embedding["format"],
    }

    # Create meta.json
    meta = {
        "name": name,
        "description": description or "",
        "owner": owner,
        "voiceId": voice_id,
        "createdAt": int(time.time() * 1000),
        "modelVersion": config["modelVersion"],
    }

    # Build bundle files
    bundle_files = {
        "embedding.bin": embedding["data"],
        "config.json": json.dumps(config, indent=2).encode("utf-8"),
        "meta.json": json.dumps(meta, indent=2).encode("utf-8"),
    }

    # Add preview.wav - use normalized_audio if preview extraction failed
    if preview_audio:
        bundle_files["preview.wav"] = preview_audio
    else:
        # Fallback: use entire normalized audio or first portion as preview
        print("[VoiceModel] Using normalized audio as preview")
        bundle_files["preview.wav"] = normalized_audio[:min(len(normalized_audio), 160000)]  # ~5 seconds at 16kHz

    return {
        "files": bundle_files,
        "config": config,
        "meta": meta,
    }


def process_voice_model(audio_buffer, mime_type, name, description, owner, voice_id):
    """
    Process audio file and generate voice model bundle
    Main entry point for voice model generation
    """
    try:
        # Step 1: Normalize audio
        print("[VoiceModel] Normalizing audio...")
        normalized_audio = normalize_audio(audio_buffer, mime_type)

        # Step 2: Generate embedding
        print("[VoiceModel] Generating voice embedding...")
        embedding = generate_embedding(normalized_audio)

        # Step 3: Extract preview (first 5 seconds, optional)
        preview_audio = None
        try:
            # Extract first 5 seconds for preview (16kHz mono WAV = 16000 * 2 bytes/second * 5)
            preview_duration = 5  # seconds
            preview_size = 16000 * 2 * preview_duration  # 16-bit PCM = 2 bytes/sample
            if len(normalized_audio) > preview_size:
                preview_audio = normalized_audio[:preview_size]
        except Exception as error:
            print(f"[VoiceModel] Preview extraction failed, continuing without preview: {error}")

        # Step 4: Create bundle
        print("[VoiceModel] Creating voice bundle...")
        bundle = create_voice_bundle(
            name=name,
            description=description,
            owner=owner,
            voice_id=voice_id,
            normalized_audio=normalized_audio,
            embedding=embedding,
            preview_audio=preview_audio,
        )

        return bundle
    except Exception as error:
        print(f"[VoiceModel] Voice model processing failed: {error}")
        raise
