import base64
import io
import os

from sarvamai import SarvamAI

_client: SarvamAI | None = None


def _get_client() -> SarvamAI:
    global _client
    if _client is None:
        api_key = os.getenv("SARVAM_API_KEY", "")
        if not api_key:
            raise RuntimeError("SARVAM_API_KEY is not set")
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def text_to_speech(text: str, language_code: str = "en-IN") -> bytes:
    """Call Sarvam TTS and return raw WAV bytes."""
    client = _get_client()
    response = client.text_to_speech.convert(
        text=text,
        target_language_code=language_code,
    )
    # Sarvam returns base64-encoded audio in response.audios list
    if hasattr(response, "audios") and response.audios:
        return base64.b64decode(response.audios[0])
    raise RuntimeError("No audio returned from Sarvam TTS")


def speech_to_text(audio_bytes: bytes, language_code: str = "en-IN") -> str:
    """Call Sarvam STT and return transcript string."""
    client = _get_client()
    # Wrap bytes in a file-like object named as WAV
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.wav"
    response = client.speech_to_text.transcribe(
        file=audio_file,
        language_code=language_code,
    )
    return getattr(response, "transcript", "") or ""
