import asyncio
import json
import logging
from urllib.parse import urlencode

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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

    if not settings.VOICE_LIVE_KEY:
        await websocket.send_json({
            "type": "voice.error",
            "message": "VOICE_LIVE_KEY is not configured on the backend.",
        })
        await websocket.close(code=1011)
        return

    azure_ws = None
    try:
        azure_ws = await websockets.connect(
            _voice_live_url(),
            additional_headers={"api-key": settings.VOICE_LIVE_KEY},
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
            async for message in azure_ws:
                await websocket.send_text(message)

        await asyncio.gather(browser_to_azure(), azure_to_browser())

    except WebSocketDisconnect:
        logger.info("Voice Live browser websocket disconnected")
    except Exception as exc:
        logger.error(f"Voice Live proxy error: {exc}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "voice.error",
                "message": "Voice Live session failed. Check endpoint, key, model deployment, and region support.",
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
