from fastapi import Depends
from ml.registry import get_registry, ModelRegistry

def get_model_registry():
    return get_registry()
