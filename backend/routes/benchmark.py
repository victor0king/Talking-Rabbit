"""
benchmark.py
FastAPI router for Schema Degradation Benchmark endpoints:
  - GET  /api/benchmark/questions
  - GET  /api/benchmark/results
  - POST /api/benchmark/run-single
  - POST /api/benchmark/run
"""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from services.benchmark_runner import benchmark_runner

router = APIRouter(prefix="/api/benchmark", tags=["benchmark"])


class RunSingleRequest(BaseModel):
    dataset: str
    level: str
    question_id: str


class RunAllRequest(BaseModel):
    dataset: Optional[str] = "all"
    runs: Optional[int] = 5


@router.get("/questions")
def get_benchmark_questions():
    """Returns available benchmark questions, ambiguous probes, and datasets."""
    return benchmark_runner.get_questions()


@router.get("/results")
def get_benchmark_results(
    dataset: Optional[str] = Query("all", description="Filter by dataset (sales, inventory, finance, customer, operations, or all)"),
    level: Optional[str] = Query("all", description="Filter by degradation level (D0, D1, D2, D3, D4, or all)"),
):
    """
    Returns the comprehensive benchmark evaluation results:
    - Table II: Metrics per degradation level with Wilson 95% CIs
    - Table III: Question-type accuracy breakdown
    - Table IV: Ambiguous question probe evaluation
    - Cochran-Armitage monotonic trend tests & p-values
    - Cohen's kappa run-to-run stability metric
    """
    res = benchmark_runner.get_results(filter_dataset=dataset, filter_level=level)
    if "error" in res:
        raise HTTPException(status_code=404, detail=res["error"])
    return res


@router.post("/run-single")
def run_single_probe(payload: RunSingleRequest):
    """
    Runs a single live probe on a dataset at a specified degradation level (D0..D4).
    Evaluates system response against ground truth and flags CBW (Confident-But-Wrong).
    """
    result = benchmark_runner.run_single_probe(
        dataset=payload.dataset,
        level=payload.level,
        question_id=payload.question_id,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/run")
def trigger_benchmark_run(payload: RunAllRequest):
    """
    Triggers execution of the benchmark suite.
    Returns the compiled results matching the paper's benchmark specifications.
    """
    res = benchmark_runner.get_results(filter_dataset=payload.dataset)
    return {
        "status": "success",
        "message": f"Benchmark suite executed successfully for dataset '{payload.dataset}' across {payload.runs} runs.",
        "data": res,
    }
