"""
correlation_engine.py
Computes Pearson pairwise correlation matrices and identifies notable statistical relationships.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def compute_correlation_matrix(df: pd.DataFrame, numeric_cols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Computes Pearson correlation matrix and flags strong / moderate correlations.
    """
    if numeric_cols is None:
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if len(numeric_cols) < 2:
        return {
            "error": "At least two numeric columns are required to compute a correlation matrix.",
            "columns": numeric_cols,
            "matrix": [],
            "strong_correlations": [],
        }

    sub_df = df[numeric_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub_df) < 5:
        return {"error": "Insufficient valid numeric rows for correlation analysis."}

    corr_df = sub_df.corr(method="pearson")

    # Format matrix for heatmap visualizer
    cols = list(corr_df.columns)
    matrix = []
    strong_correlations = []

    for i, col1 in enumerate(cols):
        row = []
        for j, col2 in enumerate(cols):
            val = corr_df.loc[col1, col2]
            val_clean = 0.0 if np.isnan(val) else round(float(val), 3)
            row.append(val_clean)

            # Check for strong correlations (avoid duplicate pairs and self-correlation)
            if i < j and not np.isnan(val):
                abs_val = abs(val)
                if abs_val >= 0.65:
                    direction = "positive" if val > 0 else "inverse (negative)"
                    strength = "very strong" if abs_val >= 0.85 else "strong"
                    strong_correlations.append({
                        "col1": col1,
                        "col2": col2,
                        "r": val_clean,
                        "strength": strength,
                        "direction": direction,
                        "insight": f"{col1} and {col2} exhibit a {strength} {direction} correlation (r = {val_clean:+.2f})."
                    })

        matrix.append(row)

    # Sort strong correlations by absolute r descending
    strong_correlations.sort(key=lambda x: abs(x["r"]), reverse=True)

    return {
        "columns": cols,
        "matrix": matrix,
        "sample_size": len(sub_df),
        "strong_correlations": strong_correlations,
        "summary": f"Analyzed {len(cols)} numeric dimensions across {len(sub_df)} records. Found {len(strong_correlations)} strong correlations."
    }
