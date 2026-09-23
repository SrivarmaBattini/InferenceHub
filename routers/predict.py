# routers/predict.py
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from cache import CacheKey, cache_get, cache_set
from config import get_settings
from dependencies.auth import require_user
from exceptions import ValidationError as AppValidationError
from ml.registry import ModelRegistry, get_registry
from ml.utils import prediction_to_confidence
from schemas.prediction import PredictRequest, PredictResponse
from schemas.errors import error_responses
from tasks.background import log_prediction_to_db, increment_prediction_counter
from logger import log

settings = get_settings()
router   = APIRouter(prefix="/predict", tags=["predictions"])

MODEL_VERSION_MAP = {
    "v1": "regressor_v1",
    "v2": "regressor_v2",
}
EXPECTED_FEATURES = 5

def _compute_input_hash(features: list[float], model_version: str):
    payload = json.dumps(
        {"features": features, "model": model_version},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]

@router.post(
    "/",
    response_model=PredictResponse,
    responses={**error_responses},
    summary="Run ML inference — cached by input hash",
)
async def predict(
    body:             PredictRequest,
    background_tasks: BackgroundTasks,
    current_user:     dict[str, Any] = Depends(require_user),
    registry:         ModelRegistry  = Depends(get_registry),
):
    user_id = int(current_user["sub"])

    log.info(
        "predict_called",
        user_id=user_id,
        model_version=body.model_version,
        feature_count=len(body.features),
    )

    if len(body.features) != EXPECTED_FEATURES:
        raise AppValidationError(
            f"Expected {EXPECTED_FEATURES} features, got {len(body.features)}",
            expected=EXPECTED_FEATURES,
            received=len(body.features),
        )

    model_name = MODEL_VERSION_MAP.get(body.model_version)
    if not model_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error":     "UNKNOWN_MODEL_VERSION",
                "message":   f"Unknown model version: {body.model_version!r}",
                "available": list(MODEL_VERSION_MAP.keys()),
            },
        )

    input_hash = _compute_input_hash(body.features, body.model_version)
    cache_key  = CacheKey.prediction(input_hash, body.model_version)

    cached = await cache_get(cache_key)
    if cached:
        log.info("predict_cache_hit", cache_key=cache_key, user_id=user_id)
        background_tasks.add_task(
            log_prediction_to_db,
            user_id       = user_id,
            features      = body.features,
            prediction    = cached["prediction"],
            confidence    = cached["confidence"],
            model_version = body.model_version,
            latency_ms    = 0.0,
        )
        return PredictResponse(**cached)

    log.info("predict_cache_miss", cache_key=cache_key)
    start_ms = time.perf_counter() * 1000

    try:
        raw_output = await registry.predict_async(model_name, body.features)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error":   "INFERENCE_FAILED",
                "message": "Model inference raised an unexpected error",
            },
        ) from exc

    latency_ms   = round(time.perf_counter() * 1000 - start_ms, 3)
    prediction   = round(float(raw_output[0]), 6)
    confidence   = prediction_to_confidence(prediction, scale=3.0)
    predicted_at = datetime.now(timezone.utc)

    log.info(
        "predict_complete",
        user_id=user_id,
        prediction=prediction,
        confidence=confidence,
        latency_ms=latency_ms,
        model_version=body.model_version,
        cached=False,
    )

    result = PredictResponse(
        prediction    = prediction,
        confidence    = confidence,
        model_version = body.model_version,
        latency_ms    = latency_ms,
        predicted_at  = predicted_at,
    )

    await cache_set(cache_key, result.model_dump(), ttl=3600)

    background_tasks.add_task(
        log_prediction_to_db,
        user_id       = user_id,
        features      = body.features,
        prediction    = prediction,
        confidence    = confidence,
        model_version = body.model_version,
        latency_ms    = latency_ms,
    )
    background_tasks.add_task(
        increment_prediction_counter, user_id, body.model_version,
    )

    return result

@router.get(
    "/models",
    summary="List available model versions",
)
async def list_models(
    _user:    dict[str, Any] = Depends(require_user),
    registry: ModelRegistry  = Depends(get_registry),
):
    return {
        "models": [
            {
                "version":    version,
                "name":       name,
                "features":   EXPECTED_FEATURES,
                "type":       "regression",
            }
            for version, name in MODEL_VERSION_MAP.items()
        ]
    }
