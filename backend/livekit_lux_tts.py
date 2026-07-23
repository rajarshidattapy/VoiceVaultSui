"""LiveKit TTS adapter for VoiceVault's locally hosted LuxTTS cloner.

Each deployed agent has a ``walrus://`` bundle URI persisted in its config.
This adapter downloads that bundle's ``preview.wav`` once and uses it as the
reference prompt for every spoken response in the agent's LiveKit session.
"""
from __future__ import annotations

import asyncio
import io
import logging
import uuid
import wave

from livekit.agents import APIConnectOptions
from livekit.agents import tts as livekit_tts

import tts_service
import walrus as walrus_module


logger = logging.getLogger("voicevault-agent.tts")


def _decode_pcm_wav(audio: bytes) -> tuple[bytes, int, int]:
    """Return signed 16-bit PCM payload and its WAV format metadata."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as source:
            if source.getcomptype() != "NONE":
                raise ValueError("LuxTTS output must be uncompressed PCM WAV")
            if source.getsampwidth() != 2:
                raise ValueError("LuxTTS output must use 16-bit PCM samples")

            sample_rate = source.getframerate()
            num_channels = source.getnchannels()
            pcm = source.readframes(source.getnframes())
    except (wave.Error, EOFError) as exc:
        raise ValueError("LuxTTS returned an invalid WAV response") from exc

    if not pcm or sample_rate <= 0 or num_channels <= 0:
        raise ValueError("LuxTTS returned an empty WAV response")
    return pcm, sample_rate, num_channels


class WalrusLuxTTS(livekit_tts.TTS):
    """Non-streaming LiveKit TTS backed by a registered Walrus voice bundle."""

    def __init__(self, *, voice_uri: str, agent_id: str = "") -> None:
        super().__init__(
            capabilities=livekit_tts.TTSCapabilities(streaming=False),
            sample_rate=48_000,
            num_channels=1,
        )
        if not walrus_module.is_walrus_uri(voice_uri):
            raise ValueError("A deployed voice agent requires a walrus:// creator voice URI")

        self._voice_uri = voice_uri
        self._agent_id = agent_id
        self._reference_audio: bytes | None = None
        self._reference_lock = asyncio.Lock()

    @property
    def model(self) -> str:
        return "LuxTTS"

    @property
    def provider(self) -> str:
        return "voicevault-local"

    async def preload_reference(self) -> None:
        """Fetch and cache the creator's Walrus preview before joining a call."""
        if self._reference_audio is not None:
            return

        async with self._reference_lock:
            if self._reference_audio is not None:
                return

            manifest_blob_id = walrus_module.parse_walrus_uri(self._voice_uri)
            try:
                reference = await asyncio.to_thread(
                    walrus_module.download_file,
                    manifest_blob_id,
                    "preview.wav",
                )
            except Exception as exc:
                raise RuntimeError(
                    "Could not load preview.wav from the deployed agent's Walrus voice bundle"
                ) from exc

            if not reference:
                raise RuntimeError("The deployed agent's Walrus voice bundle has an empty preview.wav")

            self._reference_audio = reference
            logger.info(
                "Loaded creator voice reference for agent_id=%s from %s",
                self._agent_id or "unknown",
                self._voice_uri,
            )

    async def reference_audio(self) -> bytes:
        await self.preload_reference()
        if self._reference_audio is None:  # Defensive guard for type checkers and future changes.
            raise RuntimeError("Creator voice reference was not loaded")
        return self._reference_audio

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions | None = None,
    ) -> "WalrusLuxTTSChunkedStream":
        return WalrusLuxTTSChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options or APIConnectOptions(),
        )


class WalrusLuxTTSChunkedStream(livekit_tts.ChunkedStream):
    """Convert one LuxTTS WAV synthesis into LiveKit PCM audio frames."""

    def __init__(
        self,
        *,
        tts: WalrusLuxTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts: WalrusLuxTTS = tts

    async def _run(self, output_emitter: livekit_tts.AudioEmitter) -> None:
        reference_audio = await self._tts.reference_audio()
        rendered_wav = await asyncio.to_thread(
            tts_service.synthesize,
            self._input_text,
            reference_audio,
        )
        pcm, sample_rate, num_channels = _decode_pcm_wav(rendered_wav)

        output_emitter.initialize(
            request_id=f"lux-{uuid.uuid4().hex}",
            sample_rate=sample_rate,
            num_channels=num_channels,
            mime_type="audio/pcm",
            frame_size_ms=20,
        )
        output_emitter.push(pcm)
