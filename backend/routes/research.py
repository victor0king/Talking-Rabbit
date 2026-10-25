"""
research.py
FastAPI router providing research architecture specifications and live schema degradation playground data.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
import pandas as pd

from config import settings
from services.schema_degrader import apply_degradation

router = APIRouter(prefix="/api/research", tags=["research"])

DATASETS_DIR = settings.BASE_DIR / "benchmark" / "datasets"


@router.get("/architecture")
def get_architecture_layers():
    """
    Returns the 5-layer architectural specifications matching Figure 1 in the Conference Paper.
    """
    return {
        "paper_title": "Talking Rabbitt: Resilient Conversational Business Intelligence under Real-World Schema Degradation",
        "conference": "IEEE / ACM Conference Proceedings on Conversational AI & Data Systems",
        "layers": [
            {
                "id": 1,
                "name": "Schema Ingestion & Resilience Layer",
                "tag": "Layer 1: Normalization",
                "purpose": "Normalizes incoming tabular inputs, detects types, and repairs syntactically corrupted or abbreviated schemas.",
                "inputs": "Raw CSV / Excel file uploads (or degraded D1–D4 schemas).",
                "outputs": "Clean Parquet cache, inferred schema dictionary {col: dtype}, null imputation report.",
                "resilience_mechanism": "Fuzzy header matching, automated date format harmonization (ISO/DMY/MDY), unit suffix stripping.",
                "key_components": ["pandas_processor.py", "schema_degrader.py", "dataset_cache.py"]
            },
            {
                "id": 2,
                "name": "Conversational Semantic Parser & Query Planner",
                "tag": "Layer 2: Intent & Planning",
                "purpose": "Translates free-form voice and text business questions into deterministic execution plans.",
                "inputs": "Natural language user prompt + dataset schema context.",
                "outputs": "Structured tool call (query_dataset, aggregate, compare, filter, forecast).",
                "resilience_mechanism": "Underspecified query detection, schema constraint verification, prompt grounding guardrails.",
                "key_components": ["chat_engine.py", "voice.py", "chat.js"]
            },
            {
                "id": 3,
                "name": "Deterministic Vectorized Analytics Engine",
                "tag": "Layer 3: Analytical Execution",
                "purpose": "Executes all mathematical computations locally in Python without LLM math hallucinations.",
                "inputs": "Parsed tool execution plan and cached DataFrame.",
                "outputs": "Exact numerical values, aggregates, time-series resamples, cluster memberships, anomaly scores.",
                "resilience_mechanism": "Vectorized numpy/pandas routines, DBSCAN clustering, Isolation Forest, Prophet forecasting.",
                "key_components": ["analytics_engine.py", "clustering_engine.py", "anomaly_engine.py", "forecast_engine.py"]
            },
            {
                "id": 4,
                "name": "Confident-But-Wrong (CBW) Guardrail & Scorer",
                "tag": "Layer 4: Verification & Hedging",
                "purpose": "Evaluates numerical outputs against ground truth within ±1.5% tolerance and flags false certainty.",
                "inputs": "Computed system answer + ground truth specification + confidence score.",
                "outputs": "Classification: correct, explicit_failure, cbw (Confident-But-Wrong), hedged_incorrect.",
                "resilience_mechanism": "Decoy column detection, hedging keyword enforcement ('uncertain', 'unclear', 'might be'), Wilson CI tracking.",
                "key_components": ["benchmark_scorer.py", "statistics_engine.py"]
            },
            {
                "id": 5,
                "name": "Dynamic Visualization & Executive Synthesis",
                "tag": "Layer 5: Presentation & Insight",
                "purpose": "Synthesizes mathematical results into publication-grade charts, heatmaps, and executive SWOT reports.",
                "inputs": "Numerical analysis outputs and anomaly flags.",
                "outputs": "Responsive Chart.js configurations, Pearson correlation heatmaps, 2D PCA cluster scatters, executive summaries.",
                "resilience_mechanism": "Adaptive chart-type selection (line, bar, scatter, heatmap) based on dimension cardinalities.",
                "key_components": ["visualization_engine.py", "report_engine.py", "charts.js"]
            }
        ]
    }


@router.get("/preview-degraded")
def preview_degraded(
    dataset: str = Query("sales", description="sales, inventory, finance, customer, operations"),
    level: str = Query("D0", description="D0, D1, D2, D3, D4"),
):
    """
    Returns the first 8 rows of the dataset at the requested degradation level
    to power the live schema degradation playground.
    """
    dataset = dataset.lower().strip()
    level = level.upper().strip()

    file_path = DATASETS_DIR / f"{dataset}_{level.lower()}.csv"
    if not file_path.exists():
        clean_file = DATASETS_DIR / f"{dataset}_data.csv"
        if not clean_file.exists():
            clean_file = settings.BASE_DIR / "sample_sales.csv"
        df_clean = pd.read_csv(clean_file)
        df_deg = apply_degradation(df_clean, level=level, dataset_name=dataset)
    else:
        df_deg = pd.read_csv(file_path)

    preview_df = df_deg.head(8).fillna("—")
    cols = list(preview_df.columns)
    rows = preview_df.to_dict(orient="records")

    level_explanations = {
        "D0": "Clean schema: standard semantic column names, typed floats/ints, and ISO dates.",
        "D1": "Syntactic noise: abbreviated column headers (e.g. tot_rev, ord_dt) and casing variations.",
        "D2": "Type & format inconsistency: currency strings ('$1,200.50'), unit suffixes ('120 units'), and mixed date representations.",
        "D3": "Semantic ambiguity: decoy columns introduced (e.g. rev_adj, qty_returned) tempting false interpretations.",
        "D4": "Compound degradation: D1-D3 combined plus cryptic legacy codes (c10, c11, amt_code_2) and scrambled column ordering."
    }

    return {
        "dataset": dataset,
        "level": level,
        "explanation": level_explanations.get(level, ""),
        "total_columns": len(cols),
        "total_rows": len(df_deg),
        "columns": cols,
        "rows": rows,
    }
