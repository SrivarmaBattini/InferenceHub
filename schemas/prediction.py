# schemas/prediction.py
from pydantic import BaseModel, Field
from datetime import datetime

class PredictRequest(BaseModel):
    # a flat list of numeric features fed to the model
    features: list[float] = Field(
        min_length=1,
        max_length=100,
        examples=[[1.2, 0.5, 3.8]],
    )
    model_version: str = Field(default="v1", examples=["v1"])

class PredictResponse(BaseModel):
    prediction:    float
    confidence:    float = Field(ge=0.0, le=1.0)
    model_version: str
    latency_ms:    float
    predicted_at:  datetime

    model_config = {"from_attributes": True}

class PredictionSummary(BaseModel):
    id:            int
    prediction:    float
    confidence:    float
    model_version: str
    latency_ms:    float
    created_at:    datetime

    model_config = {"from_attributes": True}