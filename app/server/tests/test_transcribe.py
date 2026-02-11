from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from core.transcribe import TranscriptionError, transcribe_audio


def _mock_response(status_code: int, json_data: dict | None = None, text: str = ""):
    """Create a MagicMock that behaves like an httpx.Response (sync .json())."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


# --- Unit tests for core/transcribe.py ---


@pytest.mark.asyncio
async def test_transcribe_audio_success():
    mock_response = _mock_response(200, {"text": "hello world"})

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            result = await transcribe_audio(b"fake-audio", "audio/webm")

    assert result == "hello world"


@pytest.mark.asyncio
async def test_transcribe_audio_no_api_key():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(TranscriptionError, match="not configured"):
            await transcribe_audio(b"fake-audio", "audio/webm")


@pytest.mark.asyncio
async def test_transcribe_audio_invalid_key():
    mock_response = _mock_response(401)

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "bad-key"}):
            with pytest.raises(TranscriptionError, match="Invalid.*API key"):
                await transcribe_audio(b"fake-audio", "audio/webm")


@pytest.mark.asyncio
async def test_transcribe_audio_quota_exceeded():
    mock_response = _mock_response(
        401,
        text='{"detail":{"status":"quota_exceeded","message":"quota exceeded"}}',
    )

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with pytest.raises(TranscriptionError, match="quota exceeded"):
                await transcribe_audio(b"fake-audio", "audio/webm")


@pytest.mark.asyncio
async def test_transcribe_audio_api_error():
    mock_response = _mock_response(500, text="Internal Server Error")

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with pytest.raises(TranscriptionError, match="API error: 500"):
                await transcribe_audio(b"fake-audio", "audio/webm")


@pytest.mark.asyncio
async def test_transcribe_audio_timeout():
    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with pytest.raises(TranscriptionError, match="timed out"):
                await transcribe_audio(b"fake-audio", "audio/webm")


@pytest.mark.asyncio
async def test_transcribe_audio_empty_response():
    mock_response = _mock_response(200, {"text": ""})

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with pytest.raises(TranscriptionError, match="No speech detected"):
                await transcribe_audio(b"fake-audio", "audio/webm")


# --- Integration tests for /api/transcribe endpoint ---


def test_endpoint_success(client):
    with patch("server.transcribe_audio", new_callable=AsyncMock) as mock:
        mock.return_value = "test transcription"
        files = {"file": ("test.webm", b"fake-audio", "audio/webm")}
        res = client.post("/api/transcribe", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["text"] == "test transcription"
    assert data["error"] is None


def test_endpoint_invalid_file_type(client):
    files = {"file": ("test.txt", b"text data", "text/plain")}
    res = client.post("/api/transcribe", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Invalid file type" in data["error"]


def test_endpoint_empty_file(client):
    files = {"file": ("test.webm", b"", "audio/webm")}
    res = client.post("/api/transcribe", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "Empty audio" in data["error"]


def test_endpoint_transcription_error(client):
    with patch("server.transcribe_audio", new_callable=AsyncMock) as mock:
        mock.side_effect = TranscriptionError("API key not configured")
        files = {"file": ("test.webm", b"fake-audio", "audio/webm")}
        res = client.post("/api/transcribe", files=files)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert "API key" in data["error"]


# --- Unit tests for get_websocket_token ---


@pytest.mark.asyncio
async def test_get_websocket_token_success():
    from core.transcribe import get_websocket_token

    mock_response = _mock_response(200, {"token": "test-token-123"})

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            result = await get_websocket_token()

    assert result["token"] == "test-token-123"
    assert "wss://api.elevenlabs.io" in result["ws_url"]
    assert "token=test-token-123" in result["ws_url"]
    assert "commit_strategy=manual" in result["ws_url"]


@pytest.mark.asyncio
async def test_get_websocket_token_no_api_key():
    from core.transcribe import get_websocket_token

    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(TranscriptionError, match="not configured"):
            await get_websocket_token()


@pytest.mark.asyncio
async def test_get_websocket_token_invalid_key():
    from core.transcribe import get_websocket_token

    mock_response = _mock_response(401)

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "bad-key"}):
            with pytest.raises(TranscriptionError, match="Invalid.*API key"):
                await get_websocket_token()


@pytest.mark.asyncio
async def test_get_websocket_token_timeout():
    from core.transcribe import get_websocket_token

    with patch("core.transcribe.httpx.AsyncClient") as mock_client_cls:
        instance = AsyncMock()
        instance.post.side_effect = httpx.TimeoutException("timeout")
        mock_client_cls.return_value.__aenter__.return_value = instance

        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test-key"}):
            with pytest.raises(TranscriptionError, match="timed out"):
                await get_websocket_token()


# --- Integration tests for /api/transcribe/token endpoint ---


def test_token_endpoint_success(client):
    with patch("server.get_websocket_token", new_callable=AsyncMock) as mock:
        mock.return_value = {"token": "abc", "ws_url": "wss://example.com"}
        res = client.post("/api/transcribe/token")

    assert res.status_code == 200
    data = res.json()
    assert data["token"] == "abc"
    assert data["ws_url"] == "wss://example.com"


def test_token_endpoint_error(client):
    with patch("server.get_websocket_token", new_callable=AsyncMock) as mock:
        mock.side_effect = TranscriptionError("ELEVENLABS_API_KEY not configured")
        res = client.post("/api/transcribe/token")

    assert res.status_code == 500
