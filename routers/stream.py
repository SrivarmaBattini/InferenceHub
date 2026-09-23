import asyncio
import json
import time
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from jose import JWTError

from dependencies.auth import require_user
from ml.registry import ModelRegistry, get_registry
from ml.utils import prediction_to_confidence
from streaming import sse_event, sse_error, sse_done
from security import decode_access_token
import numpy as np

router = APIRouter(prefix="/stream", tags=["streaming"])

async def _stream_prediction_tokens(
    features:      list[float],
    model_version: str,
    registry:      ModelRegistry,
):
    try:
        yield sse_event(
            data       = {"status": "started", "features": len(features)},
            event_type = "status",
        )
        await asyncio.sleep(0.05)

        reasoning_tokens = [
            f"Analysing {len(features)} input features...",
            "Running gradient boosting inference...",
            "Aggregating 100 decision trees...",
            "Applying feature scaling...",
            "Computing final prediction...",
        ]

        for i, token in enumerate(reasoning_tokens):
            yield sse_event(
                data       = {"token": token, "index": i},
                event_type = "token",
                event_id   = i,
            )
            await asyncio.sleep(0.15)

        start_ms   = time.perf_counter() * 1000
        raw_output = await registry.predict_async("regressor_v1", features)
        latency_ms = round(time.perf_counter() * 1000 - start_ms, 3)

        prediction = round(float(raw_output[0]), 6)
        confidence = prediction_to_confidence(prediction, scale=3.0)

        yield sse_event(
            data = {
                "prediction":    prediction,
                "confidence":    confidence,
                "model_version": model_version,
                "latency_ms":    latency_ms,
                "predicted_at":  datetime.now(timezone.utc).isoformat(),
            },
            event_type = "result",
        )

        yield sse_done()

    except Exception as exc:
        yield sse_error(f"Inference failed: {exc!r}")

@router.get(
    "/predict",
    summary="Stream prediction with token-by-token output",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "SSE stream of prediction tokens",
            "content":     {"text/event-stream": {}},
        }
    },
)
async def stream_predict(
    features:      str,
    model_version: str            = "v1",
    current_user:  dict[str, Any] = Depends(require_user),
    registry:      ModelRegistry  = Depends(get_registry),
):
    try:
        parsed = [float(f.strip()) for f in features.split(",")]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":   "INVALID_FEATURES",
                "message": "features must be comma-separated floats: '0.5,-1.2,0.8'",
            },
        )

    if len(parsed) != 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":    "WRONG_FEATURE_COUNT",
                "message":  f"Expected 5 features, got {len(parsed)}",
            },
        )

    return StreamingResponse(
        _stream_prediction_tokens(parsed, model_version, registry),
        media_type = "text/event-stream",
        headers    = {
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":      "keep-alive",
        },
    )

@router.websocket("/ws/predict")
async def websocket_predict(
    websocket: WebSocket,
    token:     str,
    registry:  ModelRegistry = Depends(get_registry),
):
    try:
        payload = decode_access_token(token)
    except JWTError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await websocket.accept()
    user_id = int(payload["sub"])
    print(f"[ws] Connected user_id={user_id}")

    try:
        while True:
            try:
                raw = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            try:
                message  = json.loads(raw)
                features = message.get("features", [])
                if not features or len(features) != 5:
                    await websocket.send_json({
                        "type":    "error",
                        "message": "Send exactly 5 features",
                    })
                    continue
            except (json.JSONDecodeError, TypeError):
                await websocket.send_json({
                    "type":    "error",
                    "message": "Invalid JSON — send {\"features\": [...]}",
                })
                continue

            start_ms   = time.perf_counter() * 1000
            raw_output = await registry.predict_async("regressor_v1", features)
            latency_ms = round(time.perf_counter() * 1000 - start_ms, 3)

            prediction = round(float(raw_output[0]), 6)
            confidence = prediction_to_confidence(prediction, scale=3.0)

            await websocket.send_json({
                "type":          "result",
                "prediction":    prediction,
                "confidence":    confidence,
                "latency_ms":    latency_ms,
                "predicted_at":  datetime.now(timezone.utc).isoformat(),
            })

    except WebSocketDisconnect:
        print(f"[ws] Disconnected user_id={user_id}")
    except Exception as exc:
        print(f"[ws] Unexpected error user_id={user_id}: {exc!r}")
        await websocket.close(code=1011, reason="Internal error")

@router.get("/events", summary="Live server event feed")
async def event_stream(
    current_user: dict[str, Any] = Depends(require_user),
):
    async def generator():
        counter = 0
        while True:
            counter += 1
            yield sse_event(
                data = {
                    "counter":   counter,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message":   f"Server tick {counter}",
                },
                event_type = "tick",
                event_id   = counter,
            )
            await asyncio.sleep(2.0)

    return StreamingResponse(
        generator(),
        media_type = "text/event-stream",
        headers    = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
