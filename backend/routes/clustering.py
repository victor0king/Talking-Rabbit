"""
clustering.py
FastAPI router for unsupervised DBSCAN clustering & PCA visualization endpoints:
  - POST /api/clustering/run
  - GET  /api/clustering/{dataset_id}
"""
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
import pandas as pd

from database import get_db
import crud
from config import settings
from services import dataset_cache as cache
from services.clustering_engine import run_dbscan_clustering

router = APIRouter(prefix="/api/clustering", tags=["clustering"])


class RunClusteringRequest(BaseModel):
    dataset_id: Optional[int] = None
    sample_dataset: Optional[str] = "sales"
    features: Optional[List[str]] = None
    eps: float = 0.5
    min_samples: int = 5


@router.get("/{dataset_id}")
def get_dataset_clustering(
    dataset_id: int,
    eps: float = Query(0.5),
    min_samples: int = Query(5),
    features: Optional[str] = Query(None, description="Comma-separated feature column names"),
    db: Session = Depends(get_db),
):
    """
    Executes DBSCAN clustering on the specified dataset with 2D PCA projection.
    """
    feat_list = [f.strip() for f in features.split(",")] if features else None

    # Check if dataset exists in database
    dataset = crud.get_dataset(db, dataset_id)
    if dataset:
        df = cache.load(dataset_id, dataset.cache_path)
    else:
        # Fallback to pre-saved SME benchmark dataset
        sme_file = settings.BASE_DIR / "benchmark" / "datasets" / "sales_data.csv"
        if not sme_file.exists():
            sme_file = settings.BASE_DIR / "sample_sales.csv"
        df = pd.read_csv(sme_file)

    result = run_dbscan_clustering(df, features=feat_list, eps=eps, min_samples=min_samples)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/run")
def run_custom_clustering(payload: RunClusteringRequest, db: Session = Depends(get_db)):
    """
    Runs DBSCAN clustering with custom hyper-parameters (eps, min_samples)
    and custom feature selection.
    """
    if payload.dataset_id:
        dataset = crud.get_dataset(db, payload.dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        df = cache.load(payload.dataset_id, dataset.cache_path)
    else:
        # Use SME benchmark dataset
        sme_name = (payload.sample_dataset or "sales").lower()
        sme_file = settings.BASE_DIR / "benchmark" / "datasets" / f"{sme_name}_data.csv"
        if not sme_file.exists():
            sme_file = settings.BASE_DIR / "sample_sales.csv"
        df = pd.read_csv(sme_file)

    result = run_dbscan_clustering(
        df,
        features=payload.features,
        eps=payload.eps,
        min_samples=payload.min_samples,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
