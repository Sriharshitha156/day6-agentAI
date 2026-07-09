# TechVest Recruitment Agent

Autonomous AI-powered recruitment agent built with **LangGraph**. Takes a job description and three candidate résumés, parses them, scores against a weighted rubric, ranks candidates, checks availability, and produces an auditable shortlist — all with guardrails for safe, fair operation.

## Architecture

```
JD + Résumés → [Plan → Parse → Score → Decide → Schedule → Finalize] → Shortlist + Trajectory
```

- **Framework**: LangGraph (stateful graph with typed state, conditional edges, checkpointing)
- **UI**: Streamlit (shortlist view, trajectory trace, guardrail dashboard)
- **LLM**: Pluggable (defaults to deterministic scoring engine; drop in GPT-4o or Claude via `langchain-openai`)

## Project Structure

```
├── data/
│   ├── job_description.md          # TechVest Junior AI Engineer JD
│   ├── rubric.json                 # Weighted scoring rubric (0-5 scale, evidence-based)
│   └── candidates/
│       ├── priya.md                # Strong fit candidate
│       ├── rahul.md                # Borderline fit candidate
│       └── meera.md                # Weak fit candidate (contains prompt injection test)
├── src/
│   ├── schemas.py                  # Pydantic models (CandidateProfile, ScoreCard, etc.)
│   ├── state.py                    # LangGraph TypedDict state with reducers
│   ├── tools.py                    # 4 tools: parse_resume, score_candidate, check_availability, propose_interview
│   ├── graph.py                    # LangGraph wiring (nodes, conditional edges, checkpointer)
│   ├── guardrails.py               # Injection defence, fairness check
│   └── app.py                      # Streamlit UI
├── tests/
│   └── test_tools.py               # Unit tests for all tools and guardrails
├── main.py                         # CLI entry point (with --stream flag)
├── requirements.txt
└── .gitignore
```

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Usage

### CLI

```bash
python main.py                  # Run agent, print final shortlist
python main.py --stream         # Stream step-by-step trajectory
```

### Streamlit UI

```bash
streamlit run src/app.py
```

### Run Tests

```bash
python tests/test_tools.py
```

## How It Works

### Agent Loop (5 Phases)

| Phase | Node | What it does |
|---|---|---|
| 1 | **Plan** | Agent plans the workflow: parse → score → decide → schedule |
| 2 | **Parse** | Reads candidate résumé, extracts structured profile (injection defence runs here) |
| 3 | **Score** | Applies weighted rubric to each candidate, produces scorecard with evidence |
| 4 | **Decide** | Routes candidates to interview/hold/reject based on weighted total score |
| 5 | **Finalize** | Ranks shortlist, checks availability, proposes interview slots (pending approval) |

### 4 Tools

| Tool | Type | Description |
|---|---|---|
| `parse_resume` | Read | Extracts structured `CandidateProfile` from raw résumé text |
| `score_candidate` | Read | Scores profile against rubric, returns `ScoreCard` with evidence citations |
| `check_availability` | Read | Returns mock interview slots for a candidate |
| `propose_interview` | **Action** | Books interview — requires human approval to fire |

### Guardrails

| Guardrail | Implementation |
|---|---|
| **Step Cap** | `recursion_limit=30` in LangGraph config |
| **Human-in-the-Loop** | `propose_interview` returns `pending_approval` status; UI requires button click to approve |
| **Injection Defence** | Scans résumé text for override patterns; blocks and logs attempts |
| **Fairness Check** | Compares scores on JD-relevant criteria only (name-blind); reports any discrepancy |
| **Audit Log** | Full trajectory (thought → action → observation) persisted per run |

## Candidates

| Candidate | Profile | Expected Outcome |
|---|---|---|
| **Priya Sharma** | Strong Python/ML background, fraud detection project, PyTorch, AWS, published paper | **INTERVIEW** |
| **Rahul Verma** | Software engineer with some ML exposure, less depth in AI/ML | **HOLD** |
| **Meera Patel** | UI/UX designer with beginner Python; contains a planted prompt-injection line | **REJECT** + injection blocked |

## Scoring Rubric

| Criterion | Weight | What it measures |
|---|---|---|
| Python Proficiency | 25% | Hands-on Python, production code, ecosystem |
| ML Fundamentals | 25% | Model building, evaluation, feature engineering |
| Tooling & Frameworks | 20% | scikit-learn, pandas, numpy, PyTorch/TF, SQL |
| Data Engineering | 10% | Data pipelines, ETL, processing at scale |
| Relevant Projects | 10% | AI/ML projects, fintech relevance |
| Communication | 10% | Teamwork, presentations, mentoring |

All scores are **0–5 with mandatory evidence citations**.
