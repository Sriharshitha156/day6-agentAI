import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.schemas import FinalDecision
from src.graph import build_graph, MAX_STEPS
from src.guardrails import fairness_check

load_dotenv()

st.set_page_config(
    page_title="TechVest Recruitment Agent",
    page_icon="",
    layout="wide",
)

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def load_defaults():
    with open(os.path.join(DEFAULT_DATA_DIR, "job_description.md"), "r", encoding="utf-8") as f:
        default_jd = f.read()
    with open(os.path.join(DEFAULT_DATA_DIR, "rubric.json"), "r", encoding="utf-8") as f:
        default_rubric = json.load(f)
    default_candidates = {}
    candidates_dir = os.path.join(DEFAULT_DATA_DIR, "candidates")
    for fname in os.listdir(candidates_dir):
        if fname.endswith(".md"):
            name = fname.replace(".md", "").title()
            with open(os.path.join(candidates_dir, fname), "r", encoding="utf-8") as f:
                default_candidates[name] = f.read()
    return default_jd, default_rubric, default_candidates


if "jd" not in st.session_state:
    djd, drub, dcand = load_defaults()
    st.session_state.jd = djd
    st.session_state.rubric = drub
    st.session_state.candidates = dcand
    st.session_state.candidate_names = list(dcand.keys())
    st.session_state.result = None
    st.session_state.ran = False

st.title("TechVest Recruitment Agent")
st.markdown("Edit the JD, rubric, and candidates below, then click **Run Agent**.")

with st.sidebar:
    st.header("Configuration")

    with st.expander("Job Description", expanded=True):
        jd_text = st.text_area("Edit JD", st.session_state.jd, height=250, key="jd_input")
        if jd_text != st.session_state.jd:
            st.session_state.jd = jd_text

    with st.expander("Scoring Rubric", expanded=True):
        rubric = st.session_state.rubric
        new_criteria = []
        for i, c in enumerate(rubric["criteria"]):
            st.markdown(f"**Criterion {i+1}**")
            name = st.text_input("Name", c["name"], key=f"c_name_{i}")
            weight = st.number_input("Weight", 0.0, 1.0, c["weight"], 0.05, key=f"c_weight_{i}")
            desc = st.text_area("Description", c["description"], height=60, key=f"c_desc_{i}")
            scale_str = st.text_area(
                "Scale (0-5, one per line as `level: description`)",
                "\n".join(f"{k}: {v}" for k, v in c["scale"].items()),
                height=100, key=f"c_scale_{i}"
            )
            new_scale = {}
            for line in scale_str.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_scale[k.strip()] = v.strip()
            new_criteria.append({"name": name, "weight": weight, "description": desc, "scale": new_scale})
            st.divider()
        rubric["criteria"] = new_criteria
        st.session_state.rubric = rubric

    with st.expander("Candidates", expanded=True):
        names = list(st.session_state.candidates.keys())
        for name in names:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                if st.button("Remove", key=f"rm_{name}"):
                    del st.session_state.candidates[name]
                    st.session_state.candidate_names = list(st.session_state.candidates.keys())
                    st.rerun()

        for name in names:
            resume_text = st.text_area(
                f"{name} resume",
                st.session_state.candidates[name],
                height=150, key=f"resume_{name}"
            )
            if resume_text != st.session_state.candidates[name]:
                st.session_state.candidates[name] = resume_text

        new_name = st.text_input("New candidate name", key="new_cand_name")
        new_resume = st.text_area("New candidate resume", height=100, key="new_cand_resume")
        if st.button("Add Candidate") and new_name and new_resume:
            st.session_state.candidates[new_name] = new_resume
            st.session_state.candidate_names = list(st.session_state.candidates.keys())
            st.rerun()

        with st.button("Reset to defaults"):
            djd, drub, dcand = load_defaults()
            st.session_state.jd = djd
            st.session_state.rubric = drub
            st.session_state.candidates = dcand
            st.session_state.candidate_names = list(dcand.keys())
            st.rerun()

    st.subheader("Guardrails")
    guardrail_status = {
        "Step Cap": f"Active (max {MAX_STEPS} steps)",
        "Human-in-the-Loop": "Active (schedule requires approval)",
        "Injection Defence": "Active",
        "Fairness Check": "Active",
    }
    for g, status in guardrail_status.items():
        st.markdown(f"- **{g}**: {status}")

    run_btn = st.button("Run Agent", type="primary")


tab1, tab2, tab3, tab4 = st.tabs(["Shortlist", "Trajectory", "Guardrails", "Fairness Check"])

if run_btn:
    candidates = st.session_state.candidates
    if not candidates:
        st.error("Add at least one candidate before running.")
    else:
        with st.spinner("Running recruitment agent..."):
            try:
                app = build_graph()

                initial_state = {
                    "job_description": st.session_state.jd,
                    "rubric": st.session_state.rubric,
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

                config = {"recursion_limit": MAX_STEPS, "configurable": {"thread_id": "recruitment-1"}}
                result = app.invoke(initial_state, config=config)

                st.session_state.result = result
                st.session_state.ran = True
                st.rerun()

            except Exception as e:
                st.error(f"Agent run failed: {e}")
                st.session_state.ran = False

if st.session_state.get("ran") and st.session_state.result:
    result = st.session_state.result

    with tab1:
        st.header("Ranked Shortlist")
        shortlist = result.get("shortlist", [])
        if not shortlist:
            st.warning("No shortlist produced.")
        else:
            for entry in shortlist:
                color = {"interview": "green", "hold": "orange", "reject": "red"}
                badge_color = color.get(entry.recommendation, "gray")

                with st.container(border=True):
                    cols = st.columns([1, 3, 2])
                    with cols[0]:
                        st.markdown(f"## #{entry.rank}")
                    with cols[1]:
                        st.markdown(f"### {entry.candidate_name}")
                        st.markdown(f":{badge_color}[**{entry.recommendation.upper()}**]")
                        st.metric("Weighted Score", f"{entry.scorecard.weighted_total:.2f}/5.0")
                    with cols[2]:
                        if entry.proposed_action:
                            slot = entry.proposed_action.slot
                            st.markdown(f"**Proposed Interview:**")
                            st.markdown(f"{slot.date} @ {slot.time} ({slot.duration_minutes}min)")
                            st.markdown(f"Status: `{entry.proposed_action.status}`")
                            if entry.proposed_action.status == "pending_approval":
                                approve_key = f"approve_{entry.candidate_name}"
                                if st.button(f"Approve Interview — {entry.candidate_name}", key=approve_key):
                                    entry.proposed_action.status = "approved"
                                    st.success(f"Interview approved for {entry.candidate_name}!")
                        else:
                            st.markdown("*No interview proposed*")

                    with st.expander("Scorecard & Justification"):
                        st.markdown("**Per-Criterion Scores:**")
                        for cs in entry.scorecard.criterion_scores:
                            st.markdown(f"- {cs.criterion}: **{cs.score}/5** (weight: {cs.weight}) — *{cs.evidence}*")
                        st.markdown("---")
                        st.markdown("**Justification:**")
                        st.markdown(entry.justification)

    with tab2:
        st.header("Trajectory — Reasoning Trace")
        trajectory = result.get("trajectory", [])
        if not trajectory:
            st.warning("No trajectory recorded.")
        else:
            for step in trajectory:
                with st.container(border=True):
                    st.markdown(f"**Step {step.step_number}** — `{step.action}`")
                    st.markdown(f"**Thought:** {step.thought}")
                    st.markdown(f"**Input:** `{json.dumps(step.action_input, indent=2)}`")
                    st.markdown(f"**Observation:**")
                    st.code(step.observation[:300], language="text")

            st.subheader("Full Audit Log")
            st.code(json.dumps([s.model_dump() for s in trajectory], indent=2), language="json")

    with tab3:
        st.header("Guardrail Status")

        inj_detected = result.get("injection_attempt_detected", False)
        if inj_detected:
            st.warning("**Injection Attempt Detected** — A resume contained a prompt injection instruction. It was blocked and did not affect scoring.")
        else:
            st.success("**Injection Defence** — No injection attempts detected.")

        step_count = result.get("step_count", 0)
        st.metric("Steps Used", f"{step_count}/{MAX_STEPS}")
        if step_count >= MAX_STEPS:
            st.error("Step cap reached!")
        else:
            st.success("Step cap respected.")

        shortlist = result.get("shortlist", [])
        pending = [e for e in shortlist if e.proposed_action and e.proposed_action.status == "pending_approval"]
        if pending:
            st.warning(f"**Human-in-the-Loop** — {len(pending)} interview(s) pending human approval. Switch to Shortlist tab to approve.")
        else:
            st.success("**Human-in-the-Loop** — All actions approved or none pending.")

    with tab4:
        st.header("Fairness Check")
        profiles = result.get("parsed_profiles", {})
        scorecards = result.get("scorecards", {})

        names = list(profiles.keys())
        if len(names) >= 2:
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    name_a = names[i]
                    name_b = names[j]
                    if name_a in profiles and name_b in profiles and name_a in scorecards and name_b in scorecards:
                        fcheck = fairness_check(profiles[name_a], profiles[name_b], scorecards[name_a], scorecards[name_b])
                        with st.container(border=True):
                            st.markdown(f"**{name_a} vs {name_b}**")
                            st.markdown(f"Relevant score (excluding non-JD criteria):")
                            st.markdown(f"- {name_a}: **{fcheck['relevant_score_a']:.2f}**")
                            st.markdown(f"- {name_b}: **{fcheck['relevant_score_b']:.2f}**")
                            if fcheck["passed"]:
                                st.success(" Fairness check passed — scores are consistent.")
                            else:
                                st.error(" Fairness check failed — investigate potential bias.")
        else:
            st.info("Need at least 2 candidates for fairness comparison.")
else:
    for tab in [tab1, tab2, tab3, tab4]:
        with tab:
            st.info("Click **Run Agent** in the sidebar to start the recruitment pipeline.")
