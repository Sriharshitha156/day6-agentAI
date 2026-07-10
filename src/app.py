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

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.8rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        color: white !important;
        font-weight: 700;
        font-size: 2rem;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .main-header p {
        color: rgba(255,255,255,0.7);
        margin: 4px 0 0 0;
        font-size: 0.9rem;
    }
    .pill-container {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 1.2rem;
    }
    .pill {
        background: #f0f2f6;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        color: #333;
        border: 1px solid #e0e0e0;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .pill.active {
        background: #e8f5e9;
        border-color: #4caf50;
        color: #2e7d32;
    }
    .pill .dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        display: inline-block;
    }
    .pill .dot.green { background: #4caf50; }
    .stButton button {
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.4rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    div[data-testid="stTabs"] button {
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.4rem 1.2rem;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom: 3px solid #0f3460;
    }
    div.stExpander {
        border-radius: 10px;
        border: 1px solid #eef0f4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .verdict-badge {
        display: inline-block;
        padding: 3px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .verdict-badge.interview { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
    .verdict-badge.hold { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
    .verdict-badge.reject { background: #fbe9e7; color: #c62828; border: 1px solid #ef9a9a; }
    .score-ring {
        width: 60px; height: 60px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: 1rem;
        border: 3px solid #e0e0e0;
    }
    .score-ring.high { border-color: #4caf50; color: #2e7d32; }
    .score-ring.mid { border-color: #ff9800; color: #e65100; }
    .score-ring.low { border-color: #ef5350; color: #c62828; }
    .candidate-card {
        background: white;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #eef0f4;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        transition: box-shadow 0.2s ease;
    }
    .candidate-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }

    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 18px;
    }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #eef0f4;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .metric-card .label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .metric-card .value { font-size: 1.5rem; font-weight: 700; margin-top: 4px; }
    hr { margin: 1.5rem 0; border-color: #eef0f4; }
    footer { display: none; }
    #MainMenu { visibility: hidden; }
    .stCodeBlock { border-radius: 10px; }
    div[role="alert"] { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

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


def suggest_criteria_from_jd(jd_text: str) -> dict:
    text_lower = jd_text.lower()
    keywords = {
        "Python": ["python"],
        "Machine Learning": ["machine learning", "ml", "deep learning", "neural", "model training", "supervised", "unsupervised", "classification", "regression"],
        "Data Engineering": ["data pipeline", "etl", "data processing", "sql", "database", "data warehouse", "big data", "spark"],
        "Cloud & DevOps": ["aws", "gcp", "azure", "cloud", "docker", "kubernetes", "ci/cd", "devops", "deployment"],
        "MLOps": ["mlops", "mlflow", "dvc", "experiment tracking", "model deployment", "model monitoring"],
        "Deep Learning": ["pytorch", "tensorflow", "keras", "transformer", "lstm", "cnn", "deep learning"],
        "NLP": ["nlp", "natural language", "text", "sentiment", "llm", "language model", "gpt"],
        "Communication": ["communication", "present", "stakeholder", "collaborate", "team", "mentor", "documentation"],
        "Frameworks & Tools": ["scikit-learn", "pandas", "numpy", "flask", "fastapi", "react", "node"],
        "Software Engineering": ["software", "microservice", "api", "rest", "testing", "code review", "agile", "git"],
        "Domain Knowledge": ["fintech", "finance", "healthcare", "e-commerce", "fraud", "recommendation"],
    }
    scale_templates = {
        "Python": {"0": "No Python", "1": "Basic syntax", "2": "Scripts with libraries", "3": "Built applications", "4": "Production code", "5": "Expert / OSS contributor"},
        "Machine Learning": {"0": "No ML knowledge", "1": "Theoretical familiarity", "2": "Coursework projects", "3": "Hands-on with real data", "4": "Production models", "5": "Published research"},
        "Data Engineering": {"0": "None", "1": "Basic SQL", "2": "Data scripts", "3": "Built pipelines", "4": "Production pipelines", "5": "Distributed systems"},
        "Cloud & DevOps": {"0": "None", "1": "Familiar", "2": "Used in projects", "3": "Deployed apps", "4": "Managed infrastructure", "5": "Expert"},
        "MLOps": {"0": "None", "1": "Aware", "2": "Used tools", "3": "Set up pipelines", "4": "Production MLOps", "5": "Designed systems"},
        "Deep Learning": {"0": "None", "1": "Familiar", "2": "Used frameworks", "3": "Built models", "4": "Deployed DL", "5": "Published"},
        "NLP": {"0": "None", "1": "Basic text processing", "2": "NLP projects", "3": "Production NLP", "4": "LLM experience", "5": "Published"},
        "Communication": {"0": "No evidence", "1": "Basic participation", "2": "Team contributor", "3": "Presented work", "4": "Mentors others", "5": "Leader / published"},
        "Frameworks & Tools": {"0": "None", "1": "1-2 tools", "2": "2-3 tools", "3": "Working proficiency", "4": "Deep stack", "5": "Contributor"},
        "Software Engineering": {"0": "None", "1": "Basic coding", "2": "Built features", "3": "Production apps", "4": "Microservices", "5": "Architect"},
        "Domain Knowledge": {"0": "None", "1": "Awareness", "2": "Some exposure", "3": "Working knowledge", "4": "Deep domain expertise", "5": "Industry authority"},
    }
    suggested = []
    matched = set()
    for criteria_name, kws in keywords.items():
        for kw in kws:
            if kw in text_lower and criteria_name not in matched:
                matched.add(criteria_name)
                scale = scale_templates.get(criteria_name, {"0": "None", "1": "Basic", "2": "Some", "3": "Good", "4": "Strong", "5": "Expert"})
                suggested.append({"name": criteria_name, "weight": 0.0, "description": "Assessed from JD requirements", "scale": scale})
                break
    if not suggested:
        suggested = [
            {"name": "Technical Skills", "weight": 0.0, "description": "Overall technical alignment with JD", "scale": {"0": "None", "1": "Basic", "2": "Some", "3": "Good", "4": "Strong", "5": "Expert"}},
            {"name": "Experience", "weight": 0.0, "description": "Relevant experience level", "scale": {"0": "None", "1": "<1yr", "2": "1-2yr", "3": "2-4yr", "4": "4-6yr", "5": "6+yr"}},
            {"name": "Culture Fit", "weight": 0.0, "description": "Communication and teamwork", "scale": {"0": "None", "1": "Minimal", "2": "Adequate", "3": "Good", "4": "Strong", "5": "Exceptional"}},
        ]
    total = len(suggested)
    for c in suggested:
        c["weight"] = round(1.0 / total, 2) if total > 0 else 0.2
    remainder = round(1.0 - sum(c["weight"] for c in suggested), 2)
    if suggested and remainder != 0:
        suggested[0]["weight"] = round(suggested[0]["weight"] + remainder, 2)
    return {"criteria": suggested, "evidence_rule": "Every score MUST cite a specific line from the candidate's resume.", "scoring_approach": "Weighted average of 0-5 criterion scores."}


if "jd" not in st.session_state:
    djd, drub, dcand = load_defaults()
    st.session_state.jd = djd
    st.session_state.rubric = drub
    st.session_state.candidates = dcand
    st.session_state.candidate_names = list(dcand.keys())
    st.session_state.result = None
    st.session_state.ran = False
    st.session_state.trajectory_step = 0
    st.session_state.llm_mode = False
    st.session_state.api_key = os.getenv("OPENAI_API_KEY", "")
    st.session_state.provider = "openai"
    st.session_state.bias_audit_result = None

st.markdown(
    '<div class="main-header">'
    '<div style="display:flex;justify-content:space-between;align-items:center">'
    '<div><h1>TechVest Recruitment Agent</h1>'
    '<p>Autonomous candidate scoring, ranking & schedule</p></div>'
    '<div style="display:flex;gap:10px">'
    '</div></div></div>',
    unsafe_allow_html=True
)

with st.sidebar:
    st.markdown("### Configuration")
    st.session_state.llm_mode = st.toggle("LLM Mode (ReAct Agent)", value=st.session_state.llm_mode)
    if st.session_state.llm_mode:
        st.session_state.api_key = st.text_input("API Key", type="password", value=st.session_state.api_key, help="OpenAI / OpenRouter / Google API key")
        st.session_state.provider = st.selectbox("Provider", ["openai", "openrouter", "google"], index=["openai", "openrouter", "google"].index(st.session_state.provider))
    st.markdown("---")
    st.markdown("### Actions")
    djd, drub, dcand = load_defaults()
    if st.button("Reset to Defaults", use_container_width=True):
        st.session_state.jd = djd
        st.session_state.rubric = drub
        st.session_state.candidates = dcand
        st.session_state.candidate_names = list(dcand.keys())
        st.session_state.result = None
        st.session_state.ran = False
        st.session_state.trajectory_step = 0
        st.session_state.bias_audit_result = None
        st.rerun()
    run_btn = st.button("Run Agent", type="primary", use_container_width=True)

    if st.session_state.get("ran") and st.session_state.result:
        st.markdown("---")
        st.markdown("### Trajectory Stepper")
        trajectory = st.session_state.result.get("trajectory", [])
        if trajectory:
            max_step = len(trajectory)
            current = st.session_state.trajectory_step
            col_p, col_n = st.columns(2)
            with col_p:
                if st.button("◀ Prev", use_container_width=True) and current > 0:
                    st.session_state.trajectory_step = current - 1
                    st.rerun()
            with col_n:
                if st.button("Next ▶", use_container_width=True) and current < max_step - 1:
                    st.session_state.trajectory_step = current + 1
                    st.rerun()
            if max_step > 0:
                idx = min(current, max_step - 1)
                step = trajectory[idx]
                st.markdown(f"**Step {step.step_number}/{max_step}**: {step.action}")
                st.code(step.observation[:300], language="text")

        st.markdown("---")
        st.markdown("### Bias Audit")
        if st.button("Run Name-Swap Bias Audit", use_container_width=True):
            profiles = st.session_state.result.get("parsed_profiles", {})
            scorecards = st.session_state.result.get("scorecards", {})
            names = list(profiles.keys())
            if len(names) >= 2:
                swapped = []
                for i in range(len(names)):
                    for j in range(i + 1, len(names)):
                        na, nb = names[i], names[j]
                        if na in scorecards and nb in scorecards:
                            fcheck = fairness_check(profiles[na], profiles[nb], scorecards[na], scorecards[nb])
                            swapped.append(fcheck)
                st.session_state.bias_audit_result = swapped
                st.rerun()

pills_html = '<div class="pill-container">'
guardrail_pills = [
    ("Step Cap", f"Max {MAX_STEPS} steps", True),
    ("Human-in-the-Loop", "Active", True),
    ("Injection Defence", "Active", True),
    ("Fairness Check", "Active", True),
    ("Mode", "LLM" if st.session_state.llm_mode else "Deterministic", True),
]
for label, desc, active in guardrail_pills:
    cls = "pill active" if active else "pill"
    pills_html += f'<span class="{cls}"><span class="dot green"></span>{label}: {desc}</span>'
pills_html += "</div>"
st.markdown(pills_html, unsafe_allow_html=True)

config_tab1, config_tab2, config_tab3 = st.tabs(["Job Description", "Scoring Rubric", "Candidates"])

with config_tab1:
    jd_col1, jd_col2 = st.columns([4, 1])
    with jd_col1:
        jd_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["txt", "pdf", "docx"], key="jd_upload", label_visibility="collapsed")
        if jd_file:
            st.session_state.jd = extract_text_from_file(jd_file)
            st.rerun()
    with jd_col2:
        st.metric("Characters", f"{len(st.session_state.jd):,}")
    jd_text = st.text_area("Job description", st.session_state.jd, height=260, label_visibility="collapsed")
    if jd_text != st.session_state.jd:
        st.session_state.jd = jd_text

with config_tab2:
    rubric = st.session_state.rubric
    col_suggest, col_info = st.columns([1, 2])
    with col_suggest:
        if st.button("Suggest criteria from JD", use_container_width=True):
            suggested = suggest_criteria_from_jd(st.session_state.jd)
            st.session_state.rubric = suggested
            st.rerun()
    with col_info:
        total_weight = sum(c["weight"] for c in rubric["criteria"])
        st.markdown(f"**{len(rubric['criteria'])} criteria** | Total weight: **{total_weight:.2f}**")
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"Weights sum to {total_weight:.2f}. Adjust sliders to reach 1.0.")
    new_criteria = []
    for i, c in enumerate(rubric["criteria"]):
        with st.expander(f"{c['name']}  (weight: {c['weight']})", expanded=False):
            col_a, col_b = st.columns([1, 1])
            with col_a:
                name = st.text_input("Criterion name", c["name"], key=f"c_name_{i}")
                weight = st.slider("Weight", 0.0, 1.0, c["weight"], 0.05, key=f"c_weight_{i}")
            with col_b:
                desc = st.text_input("Short description", c["description"], key=f"c_desc_{i}")
            st.markdown("**Scale (0–5)** — one line per level as `level: description`")
            scale_str = st.text_area(
                "Scale levels", "\n".join(f"{k}: {v}" for k, v in c["scale"].items()),
                height=130, key=f"c_scale_{i}", label_visibility="collapsed"
            )
            new_scale = {}
            for line in scale_str.strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    new_scale[k.strip()] = v.strip()
            new_criteria.append({"name": name, "weight": weight, "description": desc, "scale": new_scale})
    rubric["criteria"] = new_criteria
    st.session_state.rubric = rubric

with config_tab3:
    names = list(st.session_state.candidates.keys())
    cand_tabs = st.tabs([n.split()[0] for n in names] + ["+ Add"])
    for idx, name in enumerate(names):
        with cand_tabs[idx]:
            c1, c2 = st.columns([1, 5])
            with c1:
                cand_file = st.file_uploader("Upload", type=["txt", "pdf", "docx"], key=f"upd_{name}", label_visibility="collapsed")
                if cand_file:
                    st.session_state.candidates[name] = extract_text_from_file(cand_file)
                    st.rerun()
                if st.button(f"Remove", key=f"rm_{name}"):
                    del st.session_state.candidates[name]
                    st.session_state.candidate_names = list(st.session_state.candidates.keys())
                    st.rerun()
            with c2:
                resume_text = st.text_area("Resume text", st.session_state.candidates[name], height=260, key=f"resume_{name}", label_visibility="collapsed")
                if resume_text != st.session_state.candidates[name]:
                    st.session_state.candidates[name] = resume_text
    with cand_tabs[-1]:
        nc1, nc2 = st.columns(2)
        with nc1:
            new_file = st.file_uploader("Upload resume (PDF, DOCX, TXT)", type=["txt", "pdf", "docx"], key="new_cand_file")
            new_name = st.text_input("Candidate name", key="new_cand_name")
            if new_file and new_name:
                extracted = extract_text_from_file(new_file)
                st.session_state.candidates[new_name] = extracted
                st.session_state.candidate_names = list(st.session_state.candidates.keys())
                st.rerun()
        with nc2:
            new_resume = st.text_area("Or paste resume text", height=140, key="new_cand_resume")
            new_name2 = st.text_input("Candidate name", key="new_cand_name2")
            if st.button("Add Candidate") and new_name2 and new_resume:
                st.session_state.candidates[new_name2] = new_resume
                st.session_state.candidate_names = list(st.session_state.candidates.keys())
                st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

if run_btn:
    candidates = st.session_state.candidates
    if not candidates:
        st.error("Add at least one candidate before running.")
    else:
        if st.session_state.llm_mode and not st.session_state.api_key:
            st.error("API key required for LLM mode. Enter it in the sidebar or switch to deterministic mode.")
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
                        "messages": [],
                        "llm_mode": st.session_state.llm_mode,
                        "api_key": st.session_state.api_key if st.session_state.llm_mode else "",
                        "provider": st.session_state.provider if st.session_state.llm_mode else "",
                    }
                    config = {"recursion_limit": MAX_STEPS, "configurable": {"thread_id": "recruitment-1"}}
                    result = app.invoke(initial_state, config=config)
                    st.session_state.result = result
                    st.session_state.ran = True
                    st.session_state.trajectory_step = 0
                    st.session_state.bias_audit_result = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Agent run failed: {e}")
                    st.session_state.ran = False

if st.session_state.get("ran") and st.session_state.result:
    result = st.session_state.result
    res_tab1, res_tab2, res_tab3, res_tab4 = st.tabs(["Shortlist", "Trajectory", "Guardrails", "Fairness Check"])

    with res_tab1:
        st.markdown("### Ranked Shortlist")
        shortlist = result.get("shortlist", [])
        if not shortlist:
            st.warning("No shortlist produced.")
        else:
            for entry in shortlist:
                score = entry.scorecard.weighted_total
                score_class = "high" if score >= 3.5 else ("mid" if score >= 2.0 else "low")
                badge_class = entry.recommendation
                st.markdown(
                    f'<div class="candidate-card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div style="display:flex;align-items:center;gap:16px">'
                    f'<div style="font-size:1.6rem;font-weight:800;color:#ccc;">#{entry.rank}</div>'
                    f'<div><div style="font-size:1.1rem;font-weight:600">{entry.candidate_name}</div>'
                    f'<span class="verdict-badge {badge_class}">{entry.recommendation.upper()}</span></div>'
                    f'</div>'
                    f'<div style="text-align:center">'
                    f'<div class="score-ring {score_class}">{score:.1f}</div>'
                    f'<div style="font-size:0.7rem;color:#888;margin-top:4px">/ 5.0</div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )
                if entry.proposed_action:
                    slot = entry.proposed_action.slot
                    status = entry.proposed_action.status
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.markdown(f"**Proposed Interview:** {slot.date} @ {slot.time} ({slot.duration_minutes}min)")
                    with col_b:
                        if status == "pending_approval":
                            if st.button(f"Approve Interview", key=f"app_{entry.candidate_name}", use_container_width=True):
                                entry.proposed_action.status = "approved"
                                st.success("Interview approved!")
                        else:
                            st.markdown(f"Status: `{status}`")
                with st.expander("Scorecard & Evidence"):
                    for cs in entry.scorecard.criterion_scores:
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;padding:4px 0">'
                            f'<span>{cs.criterion} <span style="color:#999;font-size:0.85rem">(w: {cs.weight})</span></span>'
                            f'<span><strong>{cs.score}/5</strong> <span style="color:#999;font-size:0.85rem">{cs.evidence[:60]}</span></span>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

    with res_tab2:
        st.markdown("### Reasoning Trace")
        trajectory = result.get("trajectory", [])
        if not trajectory:
            st.warning("No trajectory recorded.")
        else:
            for step in trajectory:
                with st.expander(f"Step {step.step_number}: {step.action}", expanded=False):
                    st.markdown(f'<div style="background:#f8f9fa;padding:12px;border-radius:8px">', unsafe_allow_html=True)
                    st.markdown(f"**Thought:** {step.thought}")
                    st.markdown(f"**Input:** `{json.dumps(step.action_input)}`")
                    st.markdown(f"**Observation:**")
                    st.code(step.observation[:500], language="text")
                    st.markdown("</div>", unsafe_allow_html=True)
            with st.expander("Full Audit Log (JSON)"):
                st.code(json.dumps([s.model_dump() for s in trajectory], indent=2), language="json")

    with res_tab3:
        st.markdown("### Guardrail Status")
        inj = result.get("injection_attempt_detected", False)
        step_count = result.get("step_count", 0)
        shortlist = result.get("shortlist", [])
        pending = [e for e in shortlist if e.proposed_action and e.proposed_action.status == "pending_approval"]
        gcols = st.columns(4)
        with gcols[0]:
            st.markdown(
                f'<div class="metric-card"><div class="label">Steps Used</div>'
                f'<div class="value" style="color:{"#ef5350" if step_count>=MAX_STEPS else "#333"}">{step_count}/{MAX_STEPS}</div></div>',
                unsafe_allow_html=True
            )
        with gcols[1]:
            st.markdown(
                f'<div class="metric-card"><div class="label">Injection</div>'
                f'<div class="value" style="color:{"#ef5350" if inj else "#4caf50"}">{"Blocked" if inj else "Clear"}</div></div>',
                unsafe_allow_html=True
            )
        with gcols[2]:
            st.markdown(
                f'<div class="metric-card"><div class="label">HITL Pending</div>'
                f'<div class="value" style="color:{"#ff9800" if pending else "#4caf50"}">{len(pending)}</div></div>',
                unsafe_allow_html=True
            )
        with gcols[3]:
            st.markdown(
                f'<div class="metric-card"><div class="label">Mode</div>'
                f'<div class="value">{"LLM" if st.session_state.llm_mode else "Deterministic"}</div></div>',
                unsafe_allow_html=True
            )
        if inj:
            st.warning("Prompt injection attempt was detected in a resume and blocked.")
        if pending:
            st.info(f"{len(pending)} interview(s) pending human approval — go to Shortlist tab.")

    with res_tab4:
        st.markdown("### Fairness Check")
        profiles = result.get("parsed_profiles", {})
        scorecards = result.get("scorecards", {})
        names = list(profiles.keys())
        if len(names) >= 2:
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    na, nb = names[i], names[j]
                    if na in profiles and nb in profiles and na in scorecards and nb in scorecards:
                        fcheck = fairness_check(profiles[na], profiles[nb], scorecards[na], scorecards[nb])
                        st.markdown(
                            f'<div style="background:#fafbfc;border-radius:12px;padding:16px;border:1px solid #eef0f4;margin-bottom:12px">'
                            f'<div style="font-weight:600;margin-bottom:8px">{na} vs {nb}</div>'
                            f'<div style="display:flex;gap:20px">',
                            unsafe_allow_html=True
                        )
                        cc = st.columns(3)
                        cc[0].metric(na, f"{fcheck['relevant_score_a']:.2f}")
                        cc[1].metric(nb, f"{fcheck['relevant_score_b']:.2f}")
                        if fcheck["passed"]:
                            cc[2].success("Consistent")
                        else:
                            cc[2].error("Bias detected")

        if st.session_state.bias_audit_result:
            st.markdown("### Bias Audit Report")
            st.markdown("Name-swap test: candidate names were swapped to check for inconsistent scoring.")
            for check in st.session_state.bias_audit_result:
                st.markdown(
                    f'<div style="background:{"#e8f5e9" if check["passed"] else "#fbe9e7"};border-radius:10px;padding:12px;margin-bottom:8px">'
                    f'<strong>{check["candidate_a"]} vs {check["candidate_b"]}</strong> — '
                    f'{"Consistent" if check["passed"] else "Inconsistent scores detected"} '
                    f'({check["relevant_score_a"]:.2f} vs {check["relevant_score_b"]:.2f})'
                    f'<br><small>{check["note"]}</small>'
                    f'</div>',
                    unsafe_allow_html=True
                )
else:
    st.info("Configure the inputs above, then click **Run Agent**.")
