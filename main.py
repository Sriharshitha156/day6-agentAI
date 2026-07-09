import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.stdout.reconfigure(encoding='utf-8')

import json
import argparse
from src.graph import build_graph
from src.schemas import TrajectoryStep


def load_data():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    with open(os.path.join(data_dir, "job_description.md"), "r", encoding="utf-8") as f:
        jd = f.read()
    with open(os.path.join(data_dir, "rubric.json"), "r", encoding="utf-8") as f:
        rubric = json.load(f)
    candidates = {}
    candidates_dir = os.path.join(data_dir, "candidates")
    for fname in sorted(os.listdir(candidates_dir)):
        if fname.endswith(".md"):
            name = fname.replace(".md", "").title()
            with open(os.path.join(candidates_dir, fname), "r", encoding="utf-8") as f:
                candidates[name] = f.read()
    return jd, rubric, candidates


def main():
    parser = argparse.ArgumentParser(description="TechVest Recruitment Agent")
    parser.add_argument("--stream", action="store_true", help="Stream output step by step")
    args = parser.parse_args()

    jd, rubric, candidates = load_data()
    app = build_graph()

    initial_state = {
        "job_description": jd,
        "rubric": rubric,
        "candidates": candidates,
        "parsed_profiles": {},
        "scorecards": {},
        "shortlist": [],
        "trajectory": [],
        "current_candidate": None,
        "candidates_remaining": list(candidates.keys()),
        "phase": "planning",
        "step_count": 0,
        "human_approval_pending": None,
        "injection_attempt_detected": False,
        "fairness_checked": False,
        "error": None,
    }

    config = {"recursion_limit": 30, "configurable": {"thread_id": "recruitment-1"}}

    if args.stream:
        print("=== Streaming Agent Trajectory ===\n")
        for event in app.stream(initial_state, config=config):
            for node_name, step_state in event.items():
                trajectory = step_state.get("trajectory", [])
                if trajectory:
                    last = trajectory[-1]
                    print(f"[Step {last.step_number}] {last.action}")
                    print(f"  Thought: {last.thought[:100]}...")
                    print(f"  Observation: {last.observation[:150]}...")
                    print()
    else:
        result = app.invoke(initial_state, config=config)

        print("=" * 60)
        print("FINAL SHORTLIST")
        print("=" * 60)
        for entry in sorted(result.get("shortlist", []), key=lambda e: e.scorecard.weighted_total, reverse=True):
            print(f"\n#{entry.rank} {entry.candidate_name} — {entry.recommendation.upper()}")
            print(f"  Score: {entry.scorecard.weighted_total:.2f}/5.0")
            if entry.proposed_action:
                slot = entry.proposed_action.slot
                print(f"  Interview: {slot.date} @ {slot.time} [{entry.proposed_action.status}]")
            print(f"  Justification: {entry.justification[:200]}...")

        if result.get("injection_attempt_detected"):
            print("\n[!] Prompt injection attempt was detected and blocked.")

        print(f"\nTotal steps: {result.get('step_count', 0)}")


if __name__ == "__main__":
    main()
