import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import joblib
import os

np.random.seed(42)
n_samples  = 1_000
n_features = 5

X = np.random.randn(n_samples, n_features)
y = 2.5 * X[:, 0] - 1.8 * X[:, 1] + 0.9 * X[:, 2] + np.random.randn(n_samples) * 0.3

pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("model",  GradientBoostingRegressor(
        n_estimators   = 100,
        max_depth      = 4,
        learning_rate  = 0.1,
        random_state   = 42,
    )),
])
pipeline.fit(X, y)
os.makedirs("ml_models", exist_ok=True)
model_path = "ml_models/regressor_v1.joblib"
joblib.dump(pipeline, model_path)
print(f"Model saved to {model_path}")
