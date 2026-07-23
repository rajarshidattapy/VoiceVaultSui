"""Local LuxTTS voice-cloning adapter for the VoiceVault API.

The adapter intentionally loads models from local filesystem paths. Model
loading is lazy so the FastAPI health check remains available while a GPU/CPU
model is not configured.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import threading
import wave
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent
TTS_DIR = BACKEND_DIR / "tts"


class TTSServiceError(RuntimeError):
    """Raised when the local TTS runtime cannot produce audio."""


_model_lock = threading.RLock()
_model = None


def _positive_float(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise TTSServiceError(f"{name} must be a number") from exc
    if value <= 0:
        raise TTSServiceError(f"{name} must be greater than zero")
    return value


def _positive_int(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise TTSServiceError(f"{name} must be an integer") from exc
    if value <= 0:
        raise TTSServiceError(f"{name} must be greater than zero")
    return value


def _required_directory(name: str) -> Path:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        raise TTSServiceError(
            f"{name} is not configured. Point it at a locally provisioned model directory."
        )

    path = Path(raw_value).expanduser()
    if not path.is_dir():
        raise TTSServiceError(f"{name} does not exist or is not a directory: {path}")
    return path


def _load_model():
    """Load LuxTTS once, only when the first synthesis request arrives."""
    global _model

    with _model_lock:
        if _model is not None:
            return _model

        model_path = _required_directory("VOICEVAULT_TTS_MODEL_PATH")
        asr_model_path = _required_directory("VOICEVAULT_TTS_ASR_MODEL_PATH")
        device = os.getenv("VOICEVAULT_TTS_DEVICE", "cuda").strip() or "cuda"
        threads = _positive_int("VOICEVAULT_TTS_THREADS", 4)

        if str(TTS_DIR) not in sys.path:
            sys.path.insert(0, str(TTS_DIR))

        try:
            from zipvoice.luxvoice import LuxTTS
        except Exception as exc:
            raise TTSServiceError(
                "LuxTTS dependencies are unavailable. Install backend/tts/requirements.txt."
            ) from exc

        try:
            _model = LuxTTS(
                model_path=str(model_path),
                asr_model_path=str(asr_model_path),
                device=device,
                threads=threads,
            )
        except Exception as exc:
            raise TTSServiceError(f"Unable to initialize the local LuxTTS model: {exc}") from exc

        return _model


def _repair_wav_header(audio: bytes) -> bytes:
    """Rewrite WAV metadata when a legacy preview was stored as a byte slice.

    Older bundles may declare more frames than their truncated data contains.
    Reading and rewriting the available frames produces a standard WAV for the
    local prompt loader. Non-WAV inputs are returned unchanged.
    """
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            frames = source.readframes(source.getnframes())
            repaired = io.BytesIO()
            with wave.open(repaired, "wb") as output:
                output.setparams(source.getparams())
                output.writeframes(frames)
            return repaired.getvalue()
    except (wave.Error, EOFError):
        return audio


def synthesize(text: str, reference_audio: bytes) -> bytes:
    """Clone ``reference_audio`` and return a 48 kHz WAV containing ``text``."""
    clean_text = text.strip()
    if not clean_text:
        raise TTSServiceError("text is required")
    if not reference_audio:
        raise TTSServiceError("A reference audio sample is required for LuxTTS cloning")

    reference_audio = _repair_wav_header(reference_audio)

    reference_seconds = _positive_float("VOICEVAULT_TTS_REFERENCE_SECONDS", 5.0)
    num_steps = _positive_int("VOICEVAULT_TTS_NUM_STEPS", 4)
    guidance_scale = _positive_float("VOICEVAULT_TTS_GUIDANCE_SCALE", 3.0)
    speed = _positive_float("VOICEVAULT_TTS_SPEED", 1.0)
    t_shift = _positive_float("VOICEVAULT_TTS_T_SHIFT", 0.5)

    reference_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="voicevault-reference-", suffix=".wav", delete=False) as handle:
            handle.write(reference_audio)
            reference_path = Path(handle.name)

        model = _load_model()
        with _model_lock:
            encoded_prompt = model.encode_prompt(
                str(reference_path),
                duration=reference_seconds,
                rms=0.01,
            )
            waveform = model.generate_speech(
                clean_text,
                encoded_prompt,
                num_steps=num_steps,
                guidance_scale=guidance_scale,
                t_shift=t_shift,
                speed=speed,
            )

        try:
            import torchaudio
        except Exception as exc:
            raise TTSServiceError("torchaudio is required to encode LuxTTS WAV output") from exc

        output = io.BytesIO()
        torchaudio.save(
            output,
            waveform.detach().cpu(),
            sample_rate=48_000,
            format="wav",
            encoding="PCM_S",
            bits_per_sample=16,
        )
        return output.getvalue()
    except TTSServiceError:
        raise
    except Exception as exc:
        raise TTSServiceError(f"LuxTTS synthesis failed: {exc}") from exc
    finally:
        if reference_path is not None:
            reference_path.unlink(missing_ok=True)
