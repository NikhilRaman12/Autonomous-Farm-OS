from __future__ import annotations
import os
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from .models import FarmState

def predict_yield(s: FarmState) -> float:
    rows = [{"growth": t.growth, "moisture": t.moisture,
             "yield": max(0.0, t.growth * .08 + t.moisture * .02)}
            for t in s.tiles if t.crop]
    if len(rows) < 2:
        return round(sum(r["yield"] for r in rows), 2)
    df = pd.DataFrame(rows)
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(df[["growth", "moisture"]], df["yield"])
    return round(float(model.predict([[75, 60]])[0]), 2)

def tensorflow_ready() -> bool:
    if os.getenv("FIELDNODE_ENABLE_TENSORFLOW", "0") != "1":
        return False
    try:
        import tensorflow as tf
        return True
    except ImportError:
        return False
