import asyncio
import inspect
import json
import logging
from urllib.parse import urlencode

import websockets
from websockets.exceptions import ConnectionClosedError, InvalidHandshake
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.azure_auth import get_voice_live_auth_headers
from app.config import settings

router = APIRouter(prefix="/api", tags=["voice"])
logger = logging.getLogger(__name__)


def _voice_live_url() -> str:
    endpoint = (settings.VOICE_LIVE_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT).rstrip("/")
    if endpoint.startswith("https://"):
        endpoint = "wss://" + endpoint.removeprefix("https://")
    elif endpoint.startswith("http://"):
        endpoint = "ws://" + endpoint.removeprefix("http://")

    query = urlencode({
        "api-version": settings.VOICE_LIVE_API_VERSION,
        "model": settings.VOICE_LIVE_MODEL,
    })
    return f"{endpoint}/voice-live/realtime?{query}"


def _websocket_header_kwargs(headers: dict[str, str]) -> dict:
    connect_parameters = inspect.signature(websockets.connect).parameters
    if "additional_headers" in connect_parameters:
        return {"additional_headers": headers}
    return {"extra_headers": headers}


def _session_update_event() -> dict:
    return {
        "type": "session.update",
        "event_id": "mstech-demo-session-update",
        "session": {
            "modalities": ["text", "audio"],
            "instructions": (
                "You are the voice mode for the MS Tech Summit demo. "
                "Answer clearly, briefly, and naturally. "
                "When users ask about the architecture, explain the model-routing demo in practical Azure terms."
            ),
            "voice": {
                "name": settings.VOICE_LIVE_VOICE,
                "type": "azure-standard",
                "temperature": 0.8,
            },
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "input_audio_sampling_rate": 24000,
            "input_audio_transcription": {
                "model": "azure-speech",
                "language": "en",
            },
            "turn_detection": {
                "type": "azure_semantic_vad",
                "threshold": 0.7,
                "prefix_padding_ms": 500,
                "silence_duration_ms": 1600,
                "create_response": True,
            },
            "temperature": 0.8,
            "max_response_output_tokens": 600,
        },
    }


@router.websocket("/voice/live")
async def voice_live(websocket: WebSocket):
    await websocket.accept()

    azure_ws = None
    azure_error_forwarded = False
    try:
        logger.info("Opening Voice Live session to %s with model %s", _voice_live_url(), settings.VOICE_LIVE_MODEL)
        azure_ws = await websockets.connect(
            _voice_live_url(),
            **_websocket_header_kwargs(get_voice_live_auth_headers()),
            ping_interval=20,
            ping_timeout=20,
            max_size=8 * 1024 * 1024,
        )
        await azure_ws.send(json.dumps(_session_update_event()))
        await websocket.send_json({
            "type": "voice.connected",
            "model": settings.VOICE_LIVE_MODEL,
            "voice": settings.VOICE_LIVE_VOICE,
        })

        async def browser_to_azure():
            while True:
                message = await websocket.receive_text()
                payload = json.loads(message)
                if payload.get("type") == "voice.stop":
                    await azure_ws.close()
                    break
                await azure_ws.send(message)

        async def azure_to_browser():
            nonlocal azure_error_forwarded
            async for message in azure_ws:
                try:
                    azure_error_forwarded = json.loads(message).get("type") == "error"
                except (json.JSONDecodeError, AttributeError):
                    pass
                await websocket.send_text(message)

        await asyncio.gather(browser_to_azure(), azure_to_browser())

    except WebSocketDisconnect:
        logger.info("Voice Live browser websocket disconnected")
    except InvalidHandshake as exc:
        status = getattr(exc, "status_code", None)
        if status is None and hasattr(exc, "response"):
            status = getattr(exc.response, "status_code", None)
        logger.error("Voice Live connection rejected with status %s: %s", status or "unknown", exc, exc_info=True)
        try:
            await websocket.send_json({
                "type": "voice.error",
                "message": (
                    "Voice Live connection was rejected"
                    + (f" with status {status}" if status else "")
                    + ". Check endpoint, managed identity roles, API key, model deployment, and region support."
                ),
            })
        except Exception:
            pass
    except ConnectionClosedError as exc:
        logger.error("Voice Live connection closed: code=%s reason=%s", exc.code, exc.reason, exc_info=True)
        if not azure_error_forwarded:
            try:
                await websocket.send_json({
                    "type": "voice.error",
                    "message": f"Voice Live connection closed ({exc.code}): {exc.reason or 'no reason provided'}",
                })
            except Exception:
                pass
    except Exception as exc:
        logger.error(f"Voice Live proxy error: {exc}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "voice.error",
                "message": f"Voice Live session failed: {exc}",
            })
        except Exception:
            pass
    finally:
        if azure_ws:
            await azure_ws.close()
        try:
            await websocket.close()
        except Exception:
            pass
