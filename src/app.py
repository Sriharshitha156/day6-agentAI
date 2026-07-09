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


def extract_text_from_file(uploaded_file):
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    if name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif name.endswith(".pdf"):
        from PyPDF2 import PdfReader
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        import docx
        doc = docx.Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    return uploaded_file.read().decode("utf-8")


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

header_col1, header_col2, header_col3 = st.columns([3, 1, 1])
with header_col1:
    st.title("TechVest Recruitment Agent")
with header_col2:
    if st.button("Reset to defaults", use_container_width=True):
        djd, drub, dcand = load_defaults()
        st.session_state.jd = djd
        st.session_state.rubric = drub
        st.session_state.candidates = dcand
        st.session_state.candidate_names = list(dcand.keys())
        st.session_state.result = None
        st.session_state.ran = False
        st.rerun()
with header_col3:
    run_btn = st.button("Run Agent", type="primary", use_container_width=True)

guardrail_pills = {
    "Step Cap": f"{MAX_STEPS} steps",
    "Human-in-the-Loop": "Active",
    "Injection Defence": "Active",
    "Fairness Check": "Active",
}
pills_html = " | ".join(
    f'<span style="background:#f0f2f6;padding:2px 10px;border-radius:12px;font-size:13px">&#x2705; {k}: {v}</span>'
    for k, v in guardrail_pills.items()
)
st.markdown(
    f'<div style="margin-bottom:20px">{pills_html}</div>',
    unsafe_allow_html=True,
)

config_tab1, config_tab2, config_tab3 = st.tabs(["Job Description", "Scoring Rubric", "Candidates"])

with config_tab1:
    jd_col1, jd_col2 = st.columns([1, 1])
    with jd_col1:
        jd_file = st.file_uploader("Upload JD (PDF, DOCX, TXT)", type=["txt", "pdf", "docx"], key="jd_upload")
        if jd_file:
            st.session_state.jd = extract_text_from_file(jd_file)
            st.rerun()
    with jd_col2:
        char_count = len(st.session_state.jd)
        st.metric("Characters", f"{char_count:,}")
    jd_text = st.text_area("Edit JD", st.session_state.jd, height=300)
    if jd_text != st.session_state.jd:
        st.session_state.jd = jd_text

with config_tab2:
    rubric = st.session_state.rubric
    rubric_cols = st.columns(len(rubric["criteria"]))
    new_criteria = []
    for i, c in enumerate(rubric["criteria"]):
        with rubric_cols[i]:
            st.markdown(f"**{c['name']}**")
            name = st.text_input("Name", c["name"], key=f"c_name_{i}", label_visibility="collapsed")
            weight = st.number_input("Weight", 0.0, 1.0, c["weight"], 0.05, key=f"c_weight_{i}")
            desc = st.text_area("Description", c["description"], height=80, key=f"c_desc_{i}")
            scale_str = st.text_area(
                "Scale (0-5)",
                "\n".join(f"{k}: {v}" for k, v in c["scale"].items()),
                height=150, key=f"c_scale_{i}"
            )
            new_scale = {}
            for line in scale_str.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_scale[k.strip()] = v.strip()
            new_criteria.append({"name": name, "weight": weight, "description": desc, "scale": new_scale})
    rubric["criteria"] = new_criteria
    st.session_state.rubric = rubric
    total_weight = sum(c["weight"] for c in rubric["criteria"])
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"Weights sum to {total_weight:.2f}. They should sum to 1.0.")

with config_tab3:
    names = list(st.session_state.candidates.keys())
    cand_tabs = st.tabs([f"{n}" for n in names] + ["+ Add"])

    for idx, name in enumerate(names):
        with cand_tabs[idx]:
            c1, c2 = st.columns([1, 5])
            with c1:
                cand_file = st.file_uploader(
                    f"Upload PDF/DOCX/TXT", type=["txt", "pdf", "docx"],
                    key=f"upd_{name}", label_visibility="collapsed"
                )
                if cand_file:
                    st.session_state.candidates[name] = extract_text_from_file(cand_file)
                    st.rerun()
                if st.button(f"Remove {name}", key=f"rm_{name}"):
                    del st.session_state.candidates[name]
                    st.session_state.candidate_names = list(st.session_state.candidates.keys())
                    st.rerun()
            with c2:
                resume_text = st.text_area(
                    f"Edit resume", st.session_state.candidates[name],
                    height=250, key=f"resume_{name}", label_visibility="collapsed"
                )
                if resume_text != st.session_state.candidates[name]:
                    st.session_state.candidates[name] = resume_text

    with cand_tabs[-1]:
        nc1, nc2 = st.columns([1, 1])
        with nc1:
            new_file = st.file_uploader("Upload resume (PDF, DOCX, TXT)", type=["txt", "pdf", "docx"], key="new_cand_file")
            new_name = st.text_input("Candidate name", key="new_cand_name")
            if new_file and new_name:
                extracted = extract_text_from_file(new_file)
                st.session_state.candidates[new_name] = extracted
                st.session_state.candidate_names = list(st.session_state.candidates.keys())
                st.rerun()
        with nc2:
            new_resume = st.text_area("Or paste resume text", height=150, key="new_cand_resume")
            new_name2 = st.text_input("Candidate name", key="new_cand_name2")
            if st.button("Add") and new_name2 and new_resume:
                st.session_state.candidates[new_name2] = new_resume
                st.session_state.candidate_names = list(st.session_state.candidates.keys())
                st.rerun()

st.divider()

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
    res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs(["Shortlist", "Trajectory", "Guardrails", "Fairness Check"])

    with res_tab1:
        st.subheader("Ranked Shortlist")
        shortlist = result.get("shortlist", [])
        if not shortlist:
            st.warning("No shortlist produced.")
        else:
            for entry in shortlist:
                color = {"interview": "green", "hold": "orange", "reject": "red"}
                badge = color.get(entry.recommendation, "gray")
                with st.container(border=True):
                    cols = st.columns([1, 4, 3])
                    with cols[0]:
                        st.markdown(f"## #{entry.rank}")
                    with cols[1]:
                        st.markdown(f"### {entry.candidate_name}")
                        st.markdown(f":{badge}[**{entry.recommendation.upper()}**]  |  Score: **{entry.scorecard.weighted_total:.2f}/5.0**")
                    with cols[2]:
                        if entry.proposed_action:
                            slot = entry.proposed_action.slot
                            st.markdown(f"**Proposed:** {slot.date} @ {slot.time}")
                            st.markdown(f"Status: `{entry.proposed_action.status}`")
                            if entry.proposed_action.status == "pending_approval":
                                if st.button(f"Approve Interview", key=f"app_{entry.candidate_name}"):
                                    entry.proposed_action.status = "approved"
                                    st.success("Approved!")
                        else:
                            st.markdown("*No interview proposed*")
                    with st.expander("Scorecard & Justification"):
                        for cs in entry.scorecard.criterion_scores:
                            st.markdown(f"- {cs.criterion}: **{cs.score}/5** (w: {cs.weight}) &mdash; *{cs.evidence}*")
                        st.markdown("---")
                        st.markdown(entry.justification)

    with res_tab2:
        st.subheader("Reasoning Trace")
        trajectory = result.get("trajectory", [])
        if not trajectory:
            st.warning("No trajectory recorded.")
        else:
            for step in trajectory:
                with st.expander(f"Step {step.step_number}: {step.action}", expanded=False):
                    st.markdown(f"**Thought:** {step.thought}")
                    st.markdown(f"**Input:** `{json.dumps(step.action_input)}`")
                    st.markdown(f"**Observation:**")
                    st.code(step.observation[:500], language="text")
            with st.expander("Full Audit Log (JSON)"):
                st.code(json.dumps([s.model_dump() for s in trajectory], indent=2), language="json")

    with res_tab3:
        st.subheader("Guardrail Status")
        gcols = st.columns(4)
        inj = result.get("injection_attempt_detected", False)
        step_count = result.get("step_count", 0)
        shortlist = result.get("shortlist", [])
        pending = [e for e in shortlist if e.proposed_action and e.proposed_action.status == "pending_approval"]
        with gcols[0]:
            st.metric("Steps Used", f"{step_count}/{MAX_STEPS}")
        with gcols[1]:
            st.metric("Injection Attempt", "Blocked" if inj else "None")
        with gcols[2]:
            st.metric("HITL Pending", len(pending))
        with gcols[3]:
            passed = result.get("fairness_checked", False)
            st.metric("Fairness", "Checked" if passed else "Pending")

    with res_tab4:
        st.subheader("Fairness Check")
        profiles = result.get("parsed_profiles", {})
        scorecards = result.get("scorecards", {})
        names = list(profiles.keys())
        if len(names) >= 2:
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    na, nb = names[i], names[j]
                    if na in profiles and nb in profiles and na in scorecards and nb in scorecards:
                        fcheck = fairness_check(profiles[na], profiles[nb], scorecards[na], scorecards[nb])
                        with st.container(border=True):
                            st.markdown(f"**{na} vs {nb}**")
                            cc = st.columns(2)
                            cc[0].metric(na, f"{fcheck['relevant_score_a']:.2f}")
                            cc[1].metric(nb, f"{fcheck['relevant_score_b']:.2f}")
                            if fcheck["passed"]:
                                st.success("Consistent — no bias detected.")
                            else:
                                st.error("Discrepancy found — review criteria.")
        else:
            st.info("Need at least 2 candidates.")
else:
    st.info("Configure the inputs above, then click **Run Agent**.")
