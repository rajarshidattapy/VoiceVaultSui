from pathlib import Path
from gradio_client import Client, handle_file

_client: Client | None = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client("ResembleAI/Chatterbox")
    return _client


def text_to_speech(text: str, audio_path: str) -> bytes:
    """Clone the voice at audio_path and synthesize text using Chatterbox."""
    client = _get_client()
    result = client.predict(
        text_input=text,
        audio_prompt_path_input=handle_file(audio_path),
        exaggeration_input=0.5,
        temperature_input=0.8,
        seed_num_input=0,
        cfgw_input=0.5,
        vad_trim_input=False,
        api_name="/generate_tts_audio",
    )
    # result is a local filepath to the generated audio
    return Path(result).read_bytes()
