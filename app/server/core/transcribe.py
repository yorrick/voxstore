import logging
import os

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
ELEVENLABS_TOKEN_URL = "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe"
ELEVENLABS_WS_BASE = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"


class TranscriptionError(Exception):
    """Raised when transcription fails."""


async def transcribe_audio(audio_data: bytes, content_type: str) -> str:
    """Transcribe audio using ElevenLabs Scribe v2.

    Args:
        audio_data: Raw audio bytes.
        content_type: MIME type (e.g. 'audio/webm').

    Returns:
        Transcribed text.

    Raises:
        TranscriptionError: If transcription fails for any reason.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise TranscriptionError("ELEVENLABS_API_KEY not configured")

    ext_map = {
        "audio/webm": "webm",
        "audio/wav": "wav",
        "audio/mp3": "mp3",
        "audio/mpeg": "mp3",
        "audio/ogg": "ogg",
    }
    ext = ext_map.get(content_type, "webm")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ELEVENLABS_STT_URL,
                headers={"xi-api-key": api_key},
                files={"file": (f"audio.{ext}", audio_data, content_type)},
                data={"model_id": "scribe_v2"},
            )

        if response.status_code == 401:
            body = response.text
            if "quota_exceeded" in body:
                logger.warning("[ELEVENLABS] Quota exceeded: %s", body)
                raise TranscriptionError("ElevenLabs API quota exceeded")
            raise TranscriptionError("Invalid ElevenLabs API key")
        if response.status_code != 200:
            logger.error(
                "[ELEVENLABS] API error %d: %s",
                response.status_code,
                response.text,
            )
            raise TranscriptionError(f"ElevenLabs API error: {response.status_code}")

        result = response.json()
        text = result.get("text", "").strip()
        if not text:
            raise TranscriptionError("No speech detected")
        return text

    except httpx.TimeoutException as e:
        raise TranscriptionError("Transcription request timed out") from e
    except httpx.RequestError as e:
        raise TranscriptionError(f"Network error: {e}") from e
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"Unexpected error: {e}") from e


async def get_websocket_token() -> dict[str, str]:
    """Get a single-use WebSocket token for realtime transcription.

    Returns:
        Dict with 'token' and 'ws_url' keys.

    Raises:
        TranscriptionError: If token generation fails.
    """
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise TranscriptionError("ELEVENLABS_API_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                ELEVENLABS_TOKEN_URL,
                headers={"xi-api-key": api_key},
            )

        if response.status_code == 401:
            raise TranscriptionError("Invalid ElevenLabs API key")
        if response.status_code != 200:
            logger.error(
                "[ELEVENLABS] Token error %d: %s",
                response.status_code,
                response.text,
            )
            raise TranscriptionError(f"ElevenLabs token error: {response.status_code}")

        data = response.json()
        token = data.get("token", "")
        if not token:
            raise TranscriptionError("Empty token returned")

        ws_url = (
            f"{ELEVENLABS_WS_BASE}"
            f"?token={token}"
            f"&model_id=scribe_v2_realtime"
            f"&commit_strategy=manual"
            f"&audio_format=pcm_16000"
        )
        return {"token": token, "ws_url": ws_url}

    except httpx.TimeoutException as e:
        raise TranscriptionError("Token request timed out") from e
    except httpx.RequestError as e:
        raise TranscriptionError(f"Network error: {e}") from e
    except TranscriptionError:
        raise
    except Exception as e:
        raise TranscriptionError(f"Unexpected error: {e}") from e
