# TechVest Recruitment Agent

Autonomous AI-powered recruitment agent built with **LangGraph**. Takes a job description and three candidate resumes, parses them, scores against a weighted rubric, ranks candidates, checks availability, and produces an auditable shortlist — all with guardrails for safe, fair operation.

Built for **Day 6 Afternoon Lab** of GenAI & Agentic AI Engineering programme.

---

## Quick Start

```bash
# 1. Create & activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # PowerShell
# .\.venv\Scripts\activate.bat         # CMD

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the agent
python main.py                         # CLI — full shortlist
python main.py --stream                # CLI — step-by-step trace

# 4. Launch Streamlit UI
streamlit run src/app.py

# 5. Run tests
python tests/test_tools.py
```

---

## Project Structure

```
.
├── data/
│   ├── job_description.md          # TechVest Junior AI Engineer JD
│   ├── rubric.json                 # Weighted scoring rubric (6 criteria, 0-5 scale)
│   └── candidates/
│       ├── priya.md                # Strong fit — ML internship, PyTorch, fraud detection
│       ├── rahul.md                # Borderline — SWE with some ML exposure
│       └── meera.md                # Weak fit — UI/UX designer + planted prompt injection
│
├── src/
│   ├── __init__.py
│   ├── schemas.py                  # Pydantic models (CandidateProfile, ScoreCard, etc.)
│   ├── state.py                    # LangGraph TypedDict state with custom reducers
│   ├── tools.py                    # 4 tools: parse_resume, score_candidate, check_availability, propose_interview
│   ├── graph.py                    # LangGraph wiring — 6 nodes, conditional edges, checkpointer
│   ├── guardrails.py               # Injection defence + fairness check
│   └── app.py                      # Streamlit UI (4 tabs: Shortlist, Trajectory, Guardrails, Fairness)
│
├── tests/
│   └── test_tools.py               # 10 unit tests
│
├── main.py                         # CLI entry point
├── requirements.txt                # Python dependencies
├── .gitignore
├── README.md
└── Day6_AfternoonLab_Recruitment_Agent.md   # Lab instructions reference
```

---

## What to Run for What

| Goal | Command | What happens |
|---|---|---|
| **Run agent (CLI)** | `python main.py` | Parses all 3 candidates, scores, ranks, prints shortlist |
| **Stream trajectory** | `python main.py --stream` | Prints each step (thought → action → observation) live |
| **Launch UI** | `streamlit run src/app.py` | Opens browser with Shortlist, Trajectory, Guardrails, Fairness tabs |
| **Run tests** | `python tests/test_tools.py` | Runs 10 tests covering all tools, guardrails, edge cases |
| **Install deps** | `pip install -r requirements.txt` | Installs langgraph, streamlit, pydantic, etc. |

---

## Architecture

```
                         ┌──────────────┐
                         │    PLAN      │
                         │  (workflow)  │
                         └──────┬───────┘
                                │
                                ▼
                     ┌───────────────────┐
          ┌──────────│      PARSE        │◄──── injection defence runs here
          │          │  (one candidate)  │
          │          └────────┬──────────┘
          │                   │ parsed?
          │              ┌────┴────┐
          │           yes│         │no
          │              ▼         │
          │          ┌──────────┐  │
          │          │  SCORE   │  │
          │          │ (rubric) │  │
          │          └────┬─────┘  │
          │               │ scored?│
          │           ┌───┴───┐    │
          │        yes│       │no  │
          │           ▼           │
          │       ┌────────┐      │
          │       │ DECIDE │      │
          │       │ (rank) │      │
          │       └───┬────┘      │
          │           │ more?     │
          │       ┌───┴───┐      │
          │     yes│       │no    │
          │◄────────┘       ▼    │
          │               ┌──────┴────────┐
          │               │   FINALIZE    │
          │               │ (shortlist)   │
          │               └───────┬───────┘
          │                       │ has interview?
          │                   ┌───┴───┐
          │                yes│       │no
          │                   ▼       │
          │            ┌──────────┐   │
          │            │ SCHEDULE │   │
          │            │ (slots)  │   │
          │            └────┬─────┘   │
          │                 │         │
          │                 ▼         ▼
          │              ┌────────────────┐
          └─────────────►│      END       │
                         │  (trajectory)  │
                         └────────────────┘
```

---

## How It Works

### Agent Loop (6 Nodes)

| Node | Function | What it does |
|---|---|---|
| **Plan** | `node_plan` | Logs the workflow plan: parse each candidate → score → decide → schedule |
| **Parse** | `node_parse_next` | Picks the next candidate from `candidates_remaining`, runs `parse_resume` tool, runs injection defence |
| **Score** | `node_score_next` | Runs `score_candidate` tool against the rubric for current candidate |
| **Decide** | `node_decide` | Maps weighted total to interview (≥3.5) / hold (≥2.0) / reject (<2.0), appends to shortlist |
| **Finalize** | `node_finalize` | Sorts shortlist by score descending, assigns ranks |
| **Schedule** | `node_check_availability` | For interview candidates, runs `check_availability` + `propose_interview` (returns `pending_approval`) |

### Routing Logic

| From | Condition | Next |
|---|---|---|
| Plan | Always | Parse |
| Parse | Current candidate parsed? | Yes → Score / No → Parse (next) |
| Score | Current candidate scored? | Yes → Decide / No → Score |
| Decide | More candidates remaining? | Yes → Parse / No → Finalize |
| Finalize | Any interview-recommended? | Yes → Schedule / No → End |
| Schedule | Always | End |

---

## 4 Tools

| Tool | Input | Output | Type | Description |
|---|---|---|---|---|
| `parse_resume` | `resume_text: str` | `CandidateProfile` | Read | Extracts structured profile from raw resume text (name, skills, experience, projects, certifications) |
| `score_candidate` | `profile: CandidateProfile`, `rubric: dict` | `ScoreCard` | Read | Scores each rubric criterion 0-5, returns weighted total + evidence citations |
| `check_availability` | `candidate_name: str`, `week: str` | `list[InterviewSlot]` | Read | Returns mock interview slots (3 days x 3 times) for the candidate |
| `propose_interview` | `candidate_name: str`, `slot: InterviewSlot` | `InterviewProposal` | **Action** | Creates a proposal with `pending_approval` status — requires human gate |

---

## Scoring Rubric

| Criterion | Weight | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| **Python Proficiency** | 25% | No experience | Basic syntax | Wrote scripts | Built apps | Production code | OSS contributions |
| **ML Fundamentals** | 25% | No knowledge | Theoretical | Coursework | Real projects | Production models | Published research |
| **Tooling & Frameworks** | 20% | None | 1-2 tools | 2-3 tools | Working proficiency | Deep ML stack | Expert, contributor |
| **Data Engineering** | 10% | None | Basic SQL | Scripts | Built pipelines | Production pipelines | Distributed systems |
| **Relevant Projects** | 10% | None | Coursework | Personal | Real-world | Production-grade | Industry-recognized |
| **Communication** | 10% | No evidence | Basic team | Contributor | Presentations | Mentor/lead | Cross-functional leader |

**Evidence rule**: Every score must cite a specific line from the candidate's resume. Scores without evidence are invalid.

---

## Candidates

| Candidate | Background | Key Skills | Weighted Score | Recommendation |
|---|---|---|---|---|
| **Priya Sharma** | B.Tech CS (AI/ML) — IIT Hyderabad | Python, PyTorch, scikit-learn, AWS, MLflow | **4.80 / 5.0** | **INTERVIEW** |
| **Rahul Verma** | B.Tech Mechanical — VIT Vellore | Python, Flask, Docker, pandas, scikit-learn | **2.85 / 5.0** | **HOLD** |
| **Meera Patel** | B.Des Communication Design — NID | HTML, CSS, Figma, beginner Python | **1.20 / 5.0** | **REJECT** |

---

## 5 Guardrails

| # | Guardrail | Implementation | What it protects against |
|---|---|---|---|
| 1 | **Human-in-the-Loop** | `propose_interview` returns `pending_approval`; Streamlit button required to approve | Unauthorized calendar booking |
| 2 | **Step Cap** | `recursion_limit=30` in LangGraph config | Infinite loops / budget waste |
| 3 | **Injection Defence** | Scans resume text for 5 override patterns (`system override`, `ignore your instructions`, etc.) | Prompt injection via resumes |
| 4 | **Fairness Check** | Compares scores on JD-relevant criteria only; reports name-blind discrepancy | Bias in scoring |
| 5 | **Audit Log** | Full trajectory (thought → action → observation → decision) persisted per run | Decision reconstruction |

---

## Streamlit UI

Run `streamlit run src/app.py` to open the dashboard with 4 tabs:

1. **Shortlist** — Ranked candidates with verdict badges, weighted scores, evidence-cited justifications, and pending interview approval buttons
2. **Trajectory** — Step-by-step reasoning trace (thought → action → observation) with full JSON audit log
3. **Guardrails** — Live status of all 5 guardrails (injection blocked, steps used, HITL pending)
4. **Fairness Check** — Pairwise name-blind comparison of relevant scores

---

## CLI Reference

```bash
python main.py                    # Run agent, print final shortlist
python main.py --stream           # Stream each step live

# Output format (normal mode):
#   FINAL SHORTLIST
#   #1 Priya — INTERVIEW (4.80/5.0)
#     Interview: 2026-07-16 @ 10:00 [pending_approval]
#     Justification: Python: 5/5 — Experience, line: ...
#
#   [!] Prompt injection attempt was detected and blocked.
#   Total steps: 12
```

---

## Tests

```bash
python tests/test_tools.py
```

Tests cover:
- Resume parsing (normal + empty)
- Scoring against rubric
- Injection detection (positive + negative)
- Injection guardrail function
- Availability checking
- Interview proposal creation
- Fairness check (identical candidates = same score)
- Open-source keyword detection
- False positive avoidance (`oss` not matching `across`)
