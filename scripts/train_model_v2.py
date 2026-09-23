from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
import numpy as np, joblib, os

np.random.seed(0)
X = np.random.randn(500, 5)
y = 1.5 * X[:, 0] - 0.7 * X[:, 2] + np.random.randn(500) * 0.5

pipeline = Pipeline([("scaler", StandardScaler()), ("model", Ridge(alpha=1.0))])
pipeline.fit(X, y)
os.makedirs("ml_models", exist_ok=True)
joblib.dump(pipeline, "ml_models/regressor_v2.joblib")
print("v2 saved")
