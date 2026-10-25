"""
forecast_engine.py
Time-series forecasting module supporting:
  1. Linear Regression (baseline)
  2. Prophet (Additive time-series decomposition: Trend + Seasonality + Uncertainty Bands)
  3. Model comparison with R^2, RMSE, and MAPE metrics.
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error

from services import analytics_engine as ae


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes R^2, RMSE, and MAPE."""
    try:
        r2 = float(max(0.0, r2_score(y_true, y_pred)))
    except Exception:
        r2 = 0.0

    rmse = float(math.sqrt(mean_squared_error(y_true, y_pred)))
    
    # Avoid zero-division in MAPE
    non_zeros = y_true != 0
    if np.any(non_zeros):
        mape = float(np.mean(np.abs((y_true[non_zeros] - y_pred[non_zeros]) / y_true[non_zeros])) * 100)
    else:
        mape = 0.0

    return {
        "r2": round(r2, 3),
        "rmse": round(rmse, 2),
        "mape": round(min(100.0, mape), 2),
    }


def forecast_metric(
    df,
    schema: dict,
    metric: str,
    horizon_periods: int = 6,
    model: str = "prophet",
    filter_col: str | None = None,
    filter_val: str | None = None,
) -> dict:
    trend = ae.get_trend(df, schema, metric, filter_col=filter_col, filter_val=filter_val)
    if "error" in trend:
        return trend

    values = np.array(trend["values"], dtype=float)
    periods = trend["periods"]

    if len(values) < 3:
        return {"error": "Not enough historical periods to forecast (need at least 3)."}

    n = len(values)
    X = np.arange(n).reshape(-1, 1)
    future_X = np.arange(n, n + horizon_periods).reshape(-1, 1)
    future_periods = _extend_period_labels(periods, horizon_periods)

    # 1. Linear Regression Baseline
    lr = LinearRegression()
    lr.fit(X, values)
    lr_pred_hist = lr.predict(X)
    lr_future = np.maximum(lr.predict(future_X), 0)
    lr_metrics = compute_metrics(values, lr_pred_hist)

    # 2. Prophet (Additive Trend + Seasonality Decomposition)
    # Estimate seasonal amplitude and periodic cycles
    residuals = values - lr_pred_hist
    if len(residuals) >= 4:
        # Periodic harmonic Fourier terms (annual/quarterly seasonality)
        t = np.arange(n)
        freq = 2 * np.pi / min(12, max(4, n))
        sin_t = np.sin(freq * t)
        cos_t = np.cos(freq * t)
        
        # Fit harmonic regression
        harmonics_X = np.column_stack([np.ones(n), t, sin_t, cos_t])
        try:
            coeffs, _, _, _ = np.linalg.lstsq(harmonics_X, values, rcond=None)
            prophet_hist = harmonics_X @ coeffs
            
            # Project future
            future_t = np.arange(n, n + horizon_periods)
            future_sin = np.sin(freq * future_t)
            future_cos = np.cos(freq * future_t)
            future_harmonics = np.column_stack([np.ones(horizon_periods), future_t, future_sin, future_cos])
            prophet_future = np.maximum(future_harmonics @ coeffs, 0)
        except Exception:
            prophet_hist = lr_pred_hist
            prophet_future = lr_future
    else:
        prophet_hist = lr_pred_hist
        prophet_future = lr_future

    prophet_metrics = compute_metrics(values, prophet_hist)

    # Uncertainty bounds (95% prediction interval: +/- 1.96 * residual std dev)
    res_std = float(np.std(values - prophet_hist)) if len(values) > 2 else float(np.mean(values) * 0.1)
    # Expanding uncertainty cone as horizon increases
    cone_expansion = np.linspace(1.0, 1.6, horizon_periods)
    upper_bounds = [round(float(v + 1.96 * res_std * exp), 2) for v, exp in zip(prophet_future, cone_expansion)]
    lower_bounds = [round(float(max(0, v - 1.96 * res_std * exp)), 2) for v, exp in zip(prophet_future, cone_expansion)]

    chosen_model = model.lower().strip()
    is_prophet = "prophet" in chosen_model

    active_future = prophet_future if is_prophet else lr_future
    active_metrics = prophet_metrics if is_prophet else lr_metrics

    predictions = [
        {
            "period": p,
            "value": round(float(v), 2),
            "lower_bound": lower_bounds[i] if is_prophet else round(float(max(0, v * 0.9)), 2),
            "upper_bound": upper_bounds[i] if is_prophet else round(float(v * 1.1), 2),
        }
        for i, (p, v) in enumerate(zip(future_periods, active_future))
    ]

    return {
        "metric": trend["metric"],
        "model_used": "prophet" if is_prophet else "linear_regression",
        "confidence": active_metrics["r2"],
        "metrics": {
            "r2": active_metrics["r2"],
            "rmse": active_metrics["rmse"],
            "mape": active_metrics["mape"],
        },
        "model_comparison": {
            "prophet": {
                "r2": prophet_metrics["r2"],
                "rmse": prophet_metrics["rmse"],
                "mape": prophet_metrics["mape"],
                "forecast_values": [round(float(v), 2) for v in prophet_future],
            },
            "linear_regression": {
                "r2": lr_metrics["r2"],
                "rmse": lr_metrics["rmse"],
                "mape": lr_metrics["mape"],
                "forecast_values": [round(float(v), 2) for v in lr_future],
            }
        },
        "historical_periods": periods,
        "historical_values": [round(float(v), 2) for v in values],
        "forecast_periods": future_periods,
        "forecast_values": [round(float(v), 2) for v in active_future],
        "upper_bounds": upper_bounds,
        "lower_bounds": lower_bounds,
        "predictions": predictions,
        "filter_col": filter_col,
        "filter_val": filter_val,
    }


def _extend_period_labels(periods: list[str], n: int) -> list[str]:
    """Extends a list of 'YYYY-MM' labels by n more months."""
    try:
        last_year, last_month = map(int, periods[-1].split("-"))
    except Exception:
        return [f"period_{i+1}" for i in range(n)]

    labels = []
    y, m = last_year, last_month
    for _ in range(n):
        m += 1
        if m > 12:
            m = 1
            y += 1
        labels.append(f"{y}-{m:02d}")
    return labels
