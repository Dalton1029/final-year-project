"""Train a baseline engagement model; swap LogisticRegression for XGBoost when deployed at scale."""
from pathlib import Path
import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier


def train(output_path="ml/nudge_model.pkl", use_xgboost=False):
    # In production this matrix comes from observed nudge delivery and redemption events.
    X = np.array([[25, 95, 7], [130, 75, 30], [0, 40, 90], [15, 50, 120], [80, 90, 5], [10, 45, 60]])
    y = np.array([1, 1, 0, 0, 1, 0])
    model = (XGBClassifier(n_estimators=20, max_depth=2, eval_metric="logloss") if use_xgboost else LogisticRegression()).fit(X, y)
    Path(output_path).parent.mkdir(exist_ok=True)
    with open(output_path, "wb") as file:
        pickle.dump(model, file)
    print(f"Saved baseline nudge model to {output_path}")


if __name__ == "__main__":
    train(use_xgboost="--xgboost" in __import__("sys").argv)
