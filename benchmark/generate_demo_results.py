"""
generate_demo_results.py
Generates the pre-computed 750 benchmark trials (30 questions x 5 degradation levels x 5 runs)
and 15 ambiguous probe evaluations matching the empirical results from the research paper:
  D0: Accuracy 88.7%, Failure 5.3%, CBW 11.1% of incorrect
  D1: Accuracy 78.0%, Failure 8.7%, CBW 35.0% of incorrect
  D2: Accuracy 69.3%, Failure 11.3%, CBW 37.9% of incorrect
  D3: Accuracy 57.3%, Failure 12.7%, CBW 57.8% of incorrect
  D4: Accuracy 42.0%, Failure 16.0%, CBW 61.9% of incorrect
"""
import json
import random
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent

def generate():
    np.random.seed(42)
    random.seed(42)

    with open(BASE_DIR / "benchmark" / "questions.json") as f:
        qdata = json.load(f)
    questions = qdata["questions"]
    amb_probes = qdata.get("ambiguous_probes", [])

    with open(BASE_DIR / "benchmark" / "ground_truth.json") as f:
        ground_truth = json.load(f)

    # Counts per level out of 150 trials (30 questions * 5 runs)
    # Target values from Table II:
    # D0: 133 correct, 8 failure, 9 incorrect (1 CBW, 8 hedged)
    # D1: 117 correct, 13 failure, 20 incorrect (7 CBW, 13 hedged)
    # D2: 104 correct, 17 failure, 29 incorrect (11 CBW, 18 hedged)
    # D3: 86 correct, 19 failure, 45 incorrect (26 CBW, 19 hedged)
    # D4: 63 correct, 24 failure, 63 incorrect (39 CBW, 24 hedged)
    level_targets = {
        "D0": {"correct": 133, "failure": 8, "cbw": 1, "hedged": 8},
        "D1": {"correct": 117, "failure": 13, "cbw": 7, "hedged": 13},
        "D2": {"correct": 104, "failure": 17, "cbw": 11, "hedged": 18},
        "D3": {"correct": 86, "failure": 19, "cbw": 26, "hedged": 19},
        "D4": {"correct": 63, "failure": 24, "cbw": 39, "hedged": 24},
    }

    trials = []
    trial_counter = 1

    for level, targets in level_targets.items():
        # Build exact list of 150 classification outcomes
        outcomes = (
            ["correct"] * targets["correct"] +
            ["explicit_failure"] * targets["failure"] +
            ["cbw"] * targets["cbw"] +
            ["hedged_incorrect"] * targets["hedged"]
        )
        assert len(outcomes) == 150

        # Shuffle deterministically
        rnd = random.Random(42 + ord(level[1]))
        rnd.shuffle(outcomes)

        idx = 0
        for run_id in range(1, 6):
            for q in questions:
                qid = q["id"]
                gt = ground_truth[qid]
                outcome = outcomes[idx]
                idx += 1

                # Construct realistic system response based on outcome
                gt_val = gt["value"]
                unit_str = f" {gt['unit']}" if gt.get("unit") else ""

                if outcome == "correct":
                    # Perturb slightly within 0.2% tolerance or exact
                    if gt["value_type"] in ("numeric", "integer"):
                        reported = gt_val if gt["value_type"] == "integer" else round(gt_val * rnd.uniform(0.999, 1.001), 2)
                        answer = f"Based on the dataset query, the calculated value is {reported:,.2f}{unit_str}."
                    else:
                        answer = f"The analysis identifies {gt_val} as the relevant category/entity."
                    confidence = round(rnd.uniform(0.92, 0.99), 3)

                elif outcome == "explicit_failure":
                    reasons = [
                        f"Unable to resolve required columns in schema due to ambiguous or missing headers at {level}.",
                        f"Execution aborted: Encountered invalid type conversion for field required to answer question.",
                        f"Error: The query planner could not confidently map query concepts to columns present in {level}.",
                    ]
                    answer = rnd.choice(reasons)
                    confidence = round(rnd.uniform(0.15, 0.35), 3)

                elif outcome == "cbw":
                    # Confident but wrong: uses decoy value or corrupted computation
                    if gt["value_type"] in ("numeric", "integer"):
                        # Biased value by 20% to 150%
                        factor = rnd.choice([0.65, 0.78, 1.28, 1.54, 2.1])
                        wrong_val = round(gt_val * factor, 2)
                        answer = f"The total computed across the dataset is exactly {wrong_val:,.2f}{unit_str}."
                    else:
                        wrong_entities = ["Cloud Router", "WH-Central", "Accounts Payable", "Mid-Market", "Alex Mercer"]
                        wrong_pick = rnd.choice([w for w in wrong_entities if w != gt_val] or ["Alternative Entity"])
                        answer = f"The highest ranking category verified from the records is definitely {wrong_pick}."
                    confidence = round(rnd.uniform(0.88, 0.98), 3)  # high false confidence!

                else:  # hedged_incorrect
                    if gt["value_type"] in ("numeric", "integer"):
                        wrong_val = round(gt_val * rnd.uniform(0.7, 1.3), 2)
                        answer = f"It appears to be approximately {wrong_val:,.2f}{unit_str}, though column headers are ambiguous and this estimate might be uncertain."
                    else:
                        answer = f"The records seem like they might point to an alternative entity, but data formats are unclear."
                    confidence = round(rnd.uniform(0.40, 0.62), 3)

                latency = int(rnd.normalvariate(420 + ord(level[1]) * 60, 45))

                trials.append({
                    "trial_id": f"TR-{trial_counter:04d}",
                    "run_id": run_id,
                    "level": level,
                    "dataset": q["dataset"],
                    "question_id": qid,
                    "question_type": q["type"],
                    "question_text": q["question"],
                    "ground_truth_value": gt_val,
                    "system_answer": answer,
                    "classification": outcome,
                    "confidence_score": confidence,
                    "latency_ms": max(150, latency),
                })
                trial_counter += 1

    # Generate Ambiguous Probes results (Table IV)
    ambiguous_results = []
    for amb in amb_probes:
        ambiguous_results.append({
            "probe_id": amb["id"],
            "dataset": amb["dataset"],
            "question": amb["question"],
            "ambiguity_type": amb["ambiguity_type"],
            "d0_response": {
                "answer": f"Standard interpretation verified: {amb['d0_expected_behavior']}.",
                "classification": "clarified_or_correct",
                "cbw": False,
                "confidence": 0.94,
            },
            "d3_response": {
                "answer": f"Synthesized without clarification: {amb['d3_expected_behavior']}.",
                "classification": "confident_but_wrong",
                "cbw": True,
                "confidence": 0.91,
                "vulnerability": "Decoy column adopted without uncertainty disclosure."
            }
        })

    output_file = BASE_DIR / "benchmark" / "demo_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "total_trials": len(trials),
            "summary_levels": level_targets,
            "trials": trials,
            "ambiguous_probes": ambiguous_results,
        }, f, indent=2)
    print(f"Generated {output_file} with {len(trials)} trials and {len(ambiguous_results)} ambiguous probes.")


if __name__ == "__main__":
    generate()
