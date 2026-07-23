# Local LuxTTS Runtime

VoiceVault uses the LuxTTS/ZipVoice code under `backend/tts` for local, reference-audio voice cloning. The active API does not call a hosted text-to-speech provider or download models at request time.

## Required local models

Before starting the backend, provision these two directories on the machine or mounted runtime volume:

```text
VOICEVAULT_TTS_MODEL_PATH/
  config.json
  model.pt                 # GPU runtime, or text_encoder.onnx and fm_decoder.onnx for CPU
  tokens.txt
  vocoder/
    config.yaml
    vocos.bin

VOICEVAULT_TTS_ASR_MODEL_PATH/
  config.json
  ...                      # a compatible local Transformers ASR model
```

The ASR model transcribes the short voice-reference sample before LuxTTS synthesizes speech. Keep both model directories out of source control and attach them to the deployed host or persistent volume.

## Configuration

```env
VOICEVAULT_TTS_MODEL_PATH=/var/lib/voicevault/models/lux-tts
VOICEVAULT_TTS_ASR_MODEL_PATH=/var/lib/voicevault/models/whisper
VOICEVAULT_TTS_DEVICE=cuda
VOICEVAULT_TTS_THREADS=4
VOICEVAULT_TTS_REFERENCE_SECONDS=5
VOICEVAULT_TTS_NUM_STEPS=4
VOICEVAULT_TTS_GUIDANCE_SCALE=3.0
VOICEVAULT_TTS_T_SHIFT=0.5
VOICEVAULT_TTS_SPEED=1.0
```

Use `VOICEVAULT_TTS_DEVICE=cpu` where no GPU is available. The local runtime is loaded lazily on the first clone request, so `/healthz` remains available even if the model paths are misconfigured. TTS requests receive HTTP 503 with the configuration error until both directories are valid.

## API flows

- `POST /api/tts/clone` accepts multipart `audio` and `text`, then returns a cloned 48 kHz WAV.
- `POST /api/tts/generate` accepts an authorized `walrus://` voice bundle, uses its `preview.wav` as the clone reference, and returns a cloned 48 kHz WAV.

The second route preserves the existing Sui license and x402 access checks before model inference.
