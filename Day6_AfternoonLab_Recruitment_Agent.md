# Day 6 · Afternoon Lab — TechVest Recruitment Agent

> **Autonomous · Multi-Tool · Your Framework · Your Decisions**
> Take one job description and three candidates, build an agent that plans, calls tools, scores every applicant, and returns an auditable shortlist — in LangGraph or CrewAI.

---

## Mission Overview (80 min)

Build your **first real autonomous agent** — from RAG chatbot (Day 4) → Email Triage (Session 3) → multi-tool Recruitment Agent (this lab).

| Dimension | RAG Chatbot (Day 4) | Recruitment Agent (Day 6) |
|---|---|---|
| Control flow | Single pass — retrieve then generate | Autonomous loop — agent decides each next step |
| Input | College documents | One JD + 3 candidate résumés |
| Tools | None | Multiple — agent picks which to call |
| State | Stateless | Persistent — across candidates and steps |
| Output | A cited answer | Ranked shortlist + full reasoning trace |

---

## Phase 0 — Define the JD, Candidates & Rubric

**Before coding.** Fix the problem first.

1. **Job Description** — Junior AI Engineer (TechVest scenario)
2. **Three Candidates** — Priya, Rahul, Meera (span: strong fit / borderline / weak fit)
3. **Scoring Rubric** — must define:
   - Criteria drawn from the JD (e.g., Python, ML fundamentals, projects, tooling, communication)
   - Weights per criterion (coding > years of experience for a Junior role)
   - 0–5 scale with one-line descriptor per level
   - **Evidence rule** — every score must cite a specific line in the résumé

⚠️ Make candidates genuinely different — if all look the same, the agent has nothing to decide.

---

## Phase 1 — Choose Framework & Design the Agent (15 min)

Pick **one**: LangGraph or CrewAI. **Do not mix them.**

| Choose LangGraph if... | Choose CrewAI if... |
|---|---|
| You want to own the control flow | You want to think in roles |
| Define nodes + typed state + conditional edges | Define agents + tasks, framework handles delegation |
| Maximum transparency | Faster to a working agent |

**Before building, write down:**
- **State** — JD, rubric, candidate list, parsed profiles, scorecards, running shortlist
- **Tools** — the 4 functions (see Phase 2)
- **Stopping condition** — all candidates scored + shortlist produced

---

## Phase 2 — Build the Tools (15 min)

Four typed, callable, testable functions:

| Tool | Input | Output | Type |
|---|---|---|---|
| `parse_resume` | resume_text | `CandidateProfile` | Read (safe) |
| `score_candidate` | profile, rubric | `ScoreCard` | Read (safe) |
| `check_availability` | candidate, week | `[slot]` | Read (safe) |
| `propose_interview` | candidate, slot | `confirmation` | **Action (needs gate)** |

**Key distinction:** `propose_interview` changes the real world — it must **never fire without human approval**.

---

## Phase 3 — Wire the Agent Loop (20 min)

### LangGraph approach
- Nodes: parse → score → decide → schedule (conditional)
- TypedDict state threaded through every node
- Checkpointer (MemorySaver) for pause/resume
- `recursion_limit` set to prevent runaway loops

### CrewAI approach
- Agents: Analyst, Scorer, Coordinator
- Tasks that pass context forward
- Sequential or hierarchical process
- `max_iter` on agents to prevent spinning

⚠️ **Cap the loop before you run it.** Set a hard step/iteration cap and recursion limit.

---

## Phase 4 — Decision Output & Trajectory (15 min)

**Final decision object must contain:**
- Ranked shortlist with recommendation (interview / hold / reject) per candidate
- Per-candidate justification citing specific résumé evidence
- Scorecard behind each ranking (inspectable numbers)
- Proposed action (interview slot) — marked **pending approval**

**Trajectory must log (in order):**
- Every **thought** (what the agent decided to do next)
- Every **action** (which tool, what args)
- Every **observation** (what the tool returned)
- The **final decision**

> The trajectory is your citation — in an agent, it proves the decision came from evidence and rules, not a hunch.

---

## Phase 5 — Guardrails & Safe Autonomy (15 min)

Five non-negotiable guardrails:

| # | Guardrail | What it does |
|---|---|---|
| 1 | **Human-in-the-loop gate** | `propose_interview` pauses for explicit approval |
| 2 | **Step/iteration cap** | Hard limit prevents runaway loops |
| 3 | **Prompt-injection defence** | Résumé text = untrusted; test with planted hostile instruction |
| 4 | **Fairness check** | Score only on JD-relevant criteria; name-swap test must yield same score |
| 5 | **Decision audit log** | Persist full trajectory + final decision for reconstruction |

> An agent that can act is a liability without a gate.

---

## Stretch Goals

- Multi-agent crew (Analyst → Scorer → Coordinator)
- Real calendar via MCP (replace mock `check_availability`)
- Bias audit report (run with swapped names, report differences)
- Second-opinion re-ranking (different model re-scores top candidates)
- Replay the trajectory (Streamlit stepper through saved trace)

---

## Done-by-3:00 Checklist

- [ ] Agent takes JD + 3 résumés and in one run parses, scores, and ranks all candidates
- [ ] Agent chose its own tool order (not a hard-coded pipeline)
- [ ] Every candidate has justification citing specific résumé evidence + scorecard
- [ ] Full trajectory (thought → action → observation → decision) logged and viewable
- [ ] `propose_interview` never fired without human approval
- [ ] Résumé-borne prompt injection did not change the ranking
- [ ] Two identical candidates scored the same regardless of name
- [ ] Peer review: partner feeds a 4th candidate or hostile résumé — handled safely

---

## Recommended Stack

| Component | Recommendation |
|---|---|
| Orchestration | LangGraph **or** CrewAI (pick one, commit) |
| Reasoning LLM | GPT-4o Mini / Claude Sonnet via OpenRouter (must support tool calling) |
| Tool definitions | `@tool` decorator (LangGraph) or `BaseTool` (CrewAI) + Pydantic models |
| Résumé parsing | LLM structured extraction → `CandidateProfile` Pydantic schema |
| State & memory | TypedDict + MemorySaver (LangGraph) or shared task context (CrewAI) |
| Human-in-the-loop | `interrupt`/checkpointer (LangGraph) or `human_input` on task (CrewAI) |
| Observability | LangSmith / Arize Phoenix / structured print logs |
| UI | Streamlit — shortlist view + trajectory + approval button |

---

## Built & Committed — Project Files

| File | Purpose |
|---|---|
| `data/job_description.md` | Junior AI Engineer JD — TechVest |
| `data/candidates/priya.md` | **Strong fit** — ML intern, PyTorch, fraud detection, open-source, published paper |
| `data/candidates/rahul.md` | **Borderline** — SWE with some ML exposure, less depth |
| `data/candidates/meera.md` | **Weak fit** — UI/UX designer + planted `<!-- SYSTEM OVERRIDE -->` injection |
| `data/rubric.json` | 6 weighted criteria (0–5), evidence rule |
| `src/schemas.py` | Pydantic models: `CandidateProfile`, `ScoreCard`, `ShortlistEntry`, etc. |
| `src/state.py` | LangGraph `TypedDict` with custom reducers |
| `src/tools.py` | 4 tools: `parse_resume`, `score_candidate`, `check_availability`, `propose_interview` |
| `src/graph.py` | 6-node LangGraph with conditional edges + MemorySaver checkpointer |
| `src/guardrails.py` | Injection defence + fairness check |
| `src/app.py` | Streamlit UI (shortlist, trajectory, guardrails, fairness tabs) |
| `main.py` | CLI entry point |
| `tests/test_tools.py` | 10 unit tests, all passing |









[•] Install LLM dependencies (langchain-google-genai)
[ ] Add API key input in UI + LLM provider selection
[ ] LLM-based resume parsing (replace deterministic parser)
[ ] LLM-based scoring with evidence (replace _score_criterion)
[ ] ReAct agent loop: LLM decides which tool to call next
[ ] Checkpointer interrupt before propose_interview
[ ] Trajectory stepper in Streamlit UI
[ ] Bias audit report: auto name-swap + re-run
[ ] Update tests for new LLM-based tools
[ ] Commit everything  implment all this steps , and prviode me a test guide md , where i can see how to check each step using giving what as input and what muts be output . give a nice ui with good frameworks . i will check step by step and ask you for changes. you do all the steps and provide detailed guide .