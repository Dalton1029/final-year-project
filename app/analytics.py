"""Pandas/NumPy feature engineering used by the FastAPI service."""
import numpy as np
import pandas as pd


def transaction_features(transactions, member_id: str) -> dict:
    rows = [t.__dict__ for t in transactions if t.member_id == member_id]
    if not rows:
        return {"transaction_count": 0, "average_spend": 0.0, "category_diversity": 0}
    frame = pd.DataFrame(rows)
    amounts = frame["amount"].astype(float).to_numpy()
    return {"transaction_count": int(amounts.size), "average_spend": float(np.round(np.mean(amounts), 2)), "category_diversity": int(frame["category"].nunique())}
