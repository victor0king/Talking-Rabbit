"""
routes/analytics.py
Powers the dashboard: KPI cards, trend chart, top/worst performers, anomalies.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import pandas as pd

from database import get_db
import crud
from utils.validators import validate_dataset_exists
from services import dataset_cache as cache
from services import pandas_processor as pp
from services import analytics_engine as ae
from services import visualization_engine as ve

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _load(dataset_id: int, db: Session):
    dataset = crud.get_dataset(db, dataset_id)
    validate_dataset_exists(dataset)
    df = cache.load(dataset_id, dataset.cache_path)
    schema = dataset.column_schema
    return dataset, df, schema


@router.get("/{dataset_id}/dashboard")
def get_dashboard(dataset_id: int, db: Session = Depends(get_db)):
    dataset, df, schema = _load(dataset_id, db)

    kpis = pp.compute_kpis(df, schema)
    numeric_cols = [c for c, t in schema.items() if t == "numeric"]
    metric_col = numeric_cols[0] if numeric_cols else None

    trend_chart, ranking_top, ranking_bottom, anomalies = {}, [], [], []

    if metric_col:
        trend = ae.get_trend(df, schema, metric_col)
        trend_chart = ve.trend_to_chart(trend)

        anomaly_result = ae.detect_anomalies(df, schema, metric_col)
        anomalies = anomaly_result.get("anomalies", [])

        categorical_cols = [c for c, t in schema.items() if t == "categorical"]
        if categorical_cols:
            perf = ae.top_bottom_performers(df, schema, categorical_cols[0], metric_col, n=5)
            ranking_top = perf.get("top", [])
            ranking_bottom = perf.get("bottom", [])

    return {
        "kpis": pp.compute_kpis(df, schema),
        "kpi_cards": ve.kpi_cards(kpis),
        "trend_chart": trend_chart,
        "top_performers": ranking_top,
        "worst_performers": ranking_bottom,
        "anomalies": anomalies,
        "risks": ae.detect_risks(df, schema),
    }


@router.get("/{dataset_id}/compare")
def compare(dataset_id: int, dimension: str = Query(...), metric: str = Query(...), db: Session = Depends(get_db)):
    _, df, schema = _load(dataset_id, db)
    result = ae.compare_dimension(df, schema, dimension, metric)
    result["chart"] = ve.comparison_to_chart(result) if "ranking" in result else None
    return result


@router.get("/{dataset_id}/report")
def executive_report(dataset_id: int, db: Session = Depends(get_db)):
    from services import report_engine
    _, df, schema = _load(dataset_id, db)
    return report_engine.build_executive_report(df, schema)


@router.get("/{dataset_id}/recommendations")
def recommendations(dataset_id: int, db: Session = Depends(get_db)):
    from services import recommendation_engine
    dataset, df, schema = _load(dataset_id, db)
    recs = recommendation_engine.generate_recommendations(df, schema)
    crud.save_recommendations(db, dataset_id, recs)
    return recs


@router.get("/{dataset_id}/correlation")
def get_correlation(dataset_id: int, db: Session = Depends(get_db)):
    """Computes Pearson correlation matrix and identifies notable relationships."""
    from services import correlation_engine
    _, df, schema = _load(dataset_id, db)
    numeric_cols = [c for c, t in schema.items() if t == "numeric"]
    return correlation_engine.compute_correlation_matrix(df, numeric_cols)


@router.get("/{dataset_id}/anomalies-advanced")
def get_advanced_anomalies(
    dataset_id: int,
    method: str = Query("isolation_forest", description="isolation_forest or z_score"),
    metric: Optional[str] = Query(None),
    contamination: float = Query(0.05),
    db: Session = Depends(get_db),
):
    """Detects outliers using either Isolation Forest or parametric Z-score."""
    from services import anomaly_engine
    _, df, schema = _load(dataset_id, db)
    numeric_cols = [c for c, t in schema.items() if t == "numeric"]

    if method == "z_score":
        target_col = metric or (numeric_cols[0] if numeric_cols else None)
        if not target_col:
            return {"error": "No numeric column available for Z-score anomaly detection."}
        return anomaly_engine.detect_zscore_anomalies(df, target_col)
    else:
        return anomaly_engine.detect_isolation_forest_anomalies(
            df, numeric_cols=numeric_cols, contamination=contamination
        )


@router.get("/{dataset_id}/profiling")
def get_dataset_profiling(dataset_id: int, db: Session = Depends(get_db)):
    """Comprehensive dataset profiling: distributions, statistical moments, and missingness."""
    _, df, schema = _load(dataset_id, db)
    import numpy as np

    total_rows = len(df)
    total_cols = len(df.columns)
    missing_cells = int(df.isna().sum().sum())
    total_cells = total_rows * total_cols
    quality_score = round((1.0 - (missing_cells / total_cells if total_cells > 0 else 0)) * 100, 1)

    col_profiles = {}
    for col in df.columns:
        ctype = schema.get(col, "text")
        null_count = int(df[col].isna().sum())
        profile = {
            "type": ctype,
            "null_count": null_count,
            "null_pct": round(null_count / total_rows * 100, 1) if total_rows > 0 else 0,
            "unique_count": int(df[col].nunique()),
        }

        if ctype == "numeric":
            numeric_s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(numeric_s) > 0:
                profile.update({
                    "mean": round(float(numeric_s.mean()), 2),
                    "std": round(float(numeric_s.std()), 2),
                    "min": round(float(numeric_s.min()), 2),
                    "q25": round(float(numeric_s.quantile(0.25)), 2),
                    "median": round(float(numeric_s.median()), 2),
                    "q75": round(float(numeric_s.quantile(0.75)), 2),
                    "max": round(float(numeric_s.max()), 2),
                    "skewness": round(float(numeric_s.skew()), 2) if len(numeric_s) > 2 else 0.0,
                })
        elif ctype == "categorical":
            vc = df[col].value_counts().head(5).to_dict()
            profile["top_categories"] = {str(k): int(v) for k, v in vc.items()}

        col_profiles[col] = profile

    return {
        "dataset_id": dataset_id,
        "row_count": total_rows,
        "column_count": total_cols,
        "missing_cells": missing_cells,
        "data_quality_score": quality_score,
        "column_profiles": col_profiles,
    }

