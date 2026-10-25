"""
benchmark_scorer.py
Scoring engine for benchmark trials.
Evaluates model/pipeline output against ground truth.
Classifies trials into:
  - 'correct'
  - 'explicit_failure'
  - 'incorrect' -> subclassified as 'cbw' (Confident-But-Wrong) or 'hedged_incorrect'
"""
import math
import re
from typing import Any, Dict, Optional, Tuple


HEDGING_KEYWORDS = [
    "not sure",
    "uncertain",
    "might be",
    "could be",
    "possibly",
    "ambiguous",
    "unclear",
    "assuming",
    "estimate",
    "approximate",
    "cannot guarantee",
    "appears to be",
    "seems like",
    "discrepancy",
    "warning",
    "caveat",
]

FAILURE_KEYWORDS = [
    "unable to answer",
    "cannot determine",
    "failed to parse",
    "error occurred",
    "not enough information",
    "no valid column",
    "cannot find",
    "schema missing",
    "column not found",
]


def extract_numbers(text: str) -> list[float]:
    """Extract numeric values from response text, stripping currency signs and commas."""
    cleaned = re.sub(r"[$,]", "", str(text))
    # Match integer or float, including scientific notation or negative numbers
    matches = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", cleaned)
    nums = []
    for m in matches:
        try:
            nums.append(float(m))
        except ValueError:
            pass
    return nums


def score_response(
    response_text: str,
    ground_truth: Dict[str, Any],
    tolerance: float = 0.015,
) -> Dict[str, Any]:
    """
    Scores a single response against ground truth.

    Args:
        response_text: Text answer produced by the agent or system.
        ground_truth: Dict with 'value', 'value_type', and optional 'unit'.
        tolerance: Relative numeric tolerance (default 1.5%).

    Returns:
        Dict with classification, confidence_flag, error_margin, and explanation.
    """
    text_lower = response_text.lower()
    gt_val = ground_truth.get("value")
    val_type = ground_truth.get("value_type", "numeric")

    # 1. Check for explicit failure
    if any(k in text_lower for k in FAILURE_KEYWORDS) or len(response_text.strip()) == 0:
        return {
            "classification": "explicit_failure",
            "is_correct": False,
            "cbw": False,
            "hedged": True,
            "detail": "System explicitly stated inability to compute or failure to parse.",
        }

    # 2. Check for numeric correctness
    if val_type in ("numeric", "integer"):
        target_num = float(gt_val)
        nums = extract_numbers(response_text)
        
        is_correct = False
        matched_num = None
        for n in nums:
            if math.isclose(n, target_num, rel_tol=tolerance, abs_tol=1e-3):
                is_correct = True
                matched_num = n
                break
        
        if is_correct:
            return {
                "classification": "correct",
                "is_correct": True,
                "cbw": False,
                "hedged": False,
                "matched_value": matched_num,
                "detail": f"Matched ground truth {target_num} within tolerance.",
            }
        else:
            # Check hedging
            is_hedged = any(k in text_lower for k in HEDGING_KEYWORDS)
            if is_hedged:
                return {
                    "classification": "hedged_incorrect",
                    "is_correct": False,
                    "cbw": False,
                    "hedged": True,
                    "detail": "Incorrect answer, but model expressed appropriate uncertainty/hedging.",
                }
            else:
                return {
                    "classification": "cbw",
                    "is_correct": False,
                    "cbw": True,
                    "hedged": False,
                    "detail": f"Confident-But-Wrong (CBW): Answer deviated from ground truth {target_num} without hedging.",
                }

    # 3. String / Categorical correctness
    else:
        target_str = str(gt_val).lower().strip()
        if target_str in text_lower:
            return {
                "classification": "correct",
                "is_correct": True,
                "cbw": False,
                "hedged": False,
                "detail": f"Contains expected entity '{gt_val}'.",
            }
        else:
            is_hedged = any(k in text_lower for k in HEDGING_KEYWORDS)
            if is_hedged:
                return {
                    "classification": "hedged_incorrect",
                    "is_correct": False,
                    "cbw": False,
                    "hedged": True,
                    "detail": "Incorrect string match with uncertainty markers.",
                }
            else:
                return {
                    "classification": "cbw",
                    "is_correct": False,
                    "cbw": True,
                    "hedged": False,
                    "detail": f"Confident-But-Wrong (CBW): Failed to match '{gt_val}' and expressed no uncertainty.",
                }
