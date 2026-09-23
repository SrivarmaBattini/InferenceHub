import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
import joblib
import numpy as np

class ModelRegistry:
    def __init__(self, max_workers: int = 4):
        self._models:   dict[str, Any] = {}
        self._executor  = ThreadPoolExecutor(
            max_workers = max_workers,
            thread_name_prefix = "ml-worker",
        )

    def load(self, name: str, path: str | Path):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        self._models[name] = joblib.load(path)
        print(f"[model] Loaded '{name}' from {path}")

    def get(self, name: str):
        model = self._models.get(name)
        if model is None:
            raise KeyError(f"Model '{name}' not loaded")
        return model

    async def predict_async(
        self,
        name:     str,
        features: list[float],
    ):
        model = self.get(name)
        array = np.array(features, dtype=np.float64).reshape(1, -1)

        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self._executor,
            model.predict,
            array,
        )
        return result

    def shutdown(self):
        self._executor.shutdown(wait=True)
        print("[model] Thread pool shut down")

registry: ModelRegistry | None = None

def get_registry():
    if registry is None:
        raise RuntimeError("ModelRegistry not initialised")
    return registry
