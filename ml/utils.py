import math

def sigmoid(x: float):
    return 1.0 / (1.0 + math.exp(-x))

def prediction_to_confidence(raw_prediction: float, scale: float = 1.0):
    return round(min(0.99, sigmoid(abs(raw_prediction) / scale)), 4)
