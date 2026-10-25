"""
clustering_engine.py
Unsupervised DBSCAN (Density-Based Spatial Clustering of Applications with Noise)
engine with PCA 2D projection and Silhouette score evaluation.
"""
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


def run_dbscan_clustering(
    df: pd.DataFrame,
    features: Optional[List[str]] = None,
    eps: float = 0.5,
    min_samples: int = 5,
    max_display_points: int = 500,
) -> Dict[str, Any]:
    """
    Executes DBSCAN clustering on numerical features.
    Projects results to 2D using PCA for visualization.
    """
    if features is None:
        features = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if len(features) < 2:
        return {
            "error": "At least two numeric features are required for DBSCAN clustering.",
            "features_available": features,
        }

    sub_df = df[features].apply(pd.to_numeric, errors="coerce").dropna()
    if len(sub_df) < 15:
        return {"error": "Insufficient numeric observations for clustering (minimum 15 rows)."}

    # Standardize data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(sub_df)

    # Run DBSCAN
    db = DBSCAN(eps=eps, min_samples=min_samples)
    labels = db.fit_predict(X_scaled)

    unique_labels = set(labels)
    n_clusters = len([l for l in unique_labels if l != -1])
    n_noise = int(np.sum(labels == -1))

    # Calculate Silhouette score if we have at least 2 non-noise clusters
    valid_mask = (labels != -1)
    if n_clusters >= 2 and np.sum(valid_mask) > n_clusters:
        try:
            sil_score = round(float(silhouette_score(X_scaled[valid_mask], labels[valid_mask])), 3)
        except Exception:
            sil_score = 0.0
    else:
        sil_score = 0.0

    # 2D PCA projection for scatter visualization
    pca = PCA(n_components=2, random_state=42)
    coords_2d = pca.fit_transform(X_scaled)
    var_explained = [round(float(v) * 100, 1) for v in pca.explained_variance_ratio_]

    # Subsample if large dataset for snappy frontend rendering
    n_total = len(sub_df)
    indices = np.arange(n_total)
    if n_total > max_display_points:
        np.random.seed(42)
        indices = np.random.choice(indices, size=max_display_points, replace=False)

    points = []
    for idx in indices:
        lbl = int(labels[idx])
        points.append({
            "x": round(float(coords_2d[idx, 0]), 3),
            "y": round(float(coords_2d[idx, 1]), 3),
            "cluster": lbl,
            "is_noise": bool(lbl == -1),
            "original_index": int(sub_df.index[idx]),
        })

    # Cluster profiles (mean values per cluster)
    profiles = {}
    for lbl in sorted(unique_labels):
        mask = (labels == lbl)
        cluster_data = sub_df[mask]
        c_name = f"Cluster {lbl}" if lbl != -1 else "Noise (Outliers)"
        profiles[c_name] = {
            "cluster_id": int(lbl),
            "size": int(len(cluster_data)),
            "pct": round(len(cluster_data) / n_total * 100, 1),
            "means": {col: round(float(cluster_data[col].mean()), 2) for col in features},
        }

    return {
        "status": "success",
        "algorithm": "DBSCAN",
        "n_clusters": n_clusters,
        "n_noise_points": n_noise,
        "noise_rate_pct": round(n_noise / n_total * 100, 2),
        "silhouette_score": sil_score,
        "parameters": {"eps": eps, "min_samples": min_samples},
        "features_used": features,
        "pca_variance_explained": var_explained,
        "cluster_profiles": profiles,
        "points": points,
    }
