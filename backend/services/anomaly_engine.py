"""
anomaly_engine.py
Anomaly detection engine supporting both:
  1. Parametric Z-score thresholding
  2. Non-parametric Isolation Forest (multivariate & univariate)
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def detect_zscore_anomalies(
    df: pd.DataFrame,
    numeric_col: str,
    threshold: float = 2.5,
) -> Dict[str, Any]:
    """Z-score based univariate anomaly detection."""
    series = pd.to_numeric(df[numeric_col], errors="coerce").dropna()
    if len(series) < 5:
        return {"error": "Insufficient numeric observations for Z-score anomaly detection."}

    mean = float(series.mean())
    std = float(series.std())
    if std == 0:
        return {"anomalies_count": 0, "anomalies": [], "threshold": threshold, "mean": mean, "std": std}

    z_scores = (series - mean) / std
    is_anomaly = np.abs(z_scores) > threshold

    anomalies = []
    for idx, is_anom in is_anomaly.items():
        if is_anom:
            anomalies.append({
                "index": int(idx),
                "value": round(float(series.loc[idx]), 2),
                "z_score": round(float(z_scores.loc[idx]), 2),
                "severity": "extreme" if abs(z_scores.loc[idx]) > 3.5 else "moderate",
            })

    return {
        "method": "z_score",
        "column": numeric_col,
        "total_records": len(series),
        "anomalies_count": len(anomalies),
        "anomaly_rate_pct": round(len(anomalies) / len(series) * 100, 2),
        "mean": round(mean, 2),
        "std": round(std, 2),
        "threshold": threshold,
        "anomalies": anomalies,
    }


def detect_isolation_forest_anomalies(
    df: pd.DataFrame,
    numeric_cols: Optional[List[str]] = None,
    contamination: float = 0.05,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Multivariate / univariate Isolation Forest anomaly detection using scikit-learn.
    Isolates observations by randomly selecting a feature and splitting value.
    """
    if numeric_cols is None:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if not numeric_cols:
        return {"error": "No numeric columns identified for Isolation Forest detection."}

    data = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(data) < 10:
        return {"error": "At least 10 valid numeric rows are required for Isolation Forest."}

    clf = IsolationForest(
        contamination=min(0.2, max(0.01, contamination)),
        random_state=random_state,
        n_estimators=100,
    )
    clf.fit(data)

    preds = clf.predict(data)  # 1: normal, -1: anomaly
    scores = clf.decision_function(data)  # Lower score = more anomalous

    anomaly_mask = (preds == -1)
    anomaly_indices = data.index[anomaly_mask].tolist()

    anomalies = []
    for idx in anomaly_indices:
        record_vals = {c: round(float(data.loc[idx, c]), 2) for c in numeric_cols}
        anomalies.append({
            "index": int(idx),
            "anomaly_score": round(float(-scores[data.index.get_loc(idx)]), 4),
            "values": record_vals,
        })

    # Sort by anomaly severity
    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

    return {
        "method": "isolation_forest",
        "columns_evaluated": numeric_cols,
        "total_records": len(data),
        "anomalies_count": len(anomalies),
        "anomaly_rate_pct": round(len(anomalies) / len(data) * 100, 2),
        "contamination": contamination,
        "anomalies": anomalies[:50],  # Return top 50
    }
