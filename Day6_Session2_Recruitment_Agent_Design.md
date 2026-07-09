# GenAI & Agentic AI Engineering · Day 6 · Session 2
## Hands-On: Design an AI Recruitment Agent

---

## Exercise 1 · Design the Recruitment Agent — Four Decisions

### Decision 1: THE TASK
The agent receives a job description and 3 candidate profiles, then autonomously evaluates each candidate against the JD, identifies skill gaps, generates tailored interview questions, and produces a ranked shortlist with a hiring recommendation — all without a human-in-the-loop during execution.

### Decision 2: THE TOOLS

| Tool | Description | Input Parameters | Return Type |
|------|-------------|-----------------|-------------|
| `extract_requirements` | Parses a job description and extracts structured required and nice-to-have skills | `jd_text: string` | `{required: string[], nice_to_have: string[]}` |
| `score_candidate` | Scores a single candidate against JD requirements, identifying strengths and weaknesses | `candidate_id: string, name: string, profile: object, requirements: object` | `{candidate_id: string, score: float (0-100), strengths: string[], weaknesses: string[]}` |
| `analyze_gaps` | Takes score result and produces categorized skill gaps for interview targeting | `candidate_id: string, score_result: object` | `{candidate_id: string, critical_gaps: string[], moderate_gaps: string[]}` |
| `generate_questions` | Generates technical and behavioral interview questions targeting identified gaps | `candidate_id: string, gaps: {critical: string[], moderate: string[]}` | `{candidate_id: string, technical_questions: string[], behavioral_questions: string[]}` |
| `rank_candidates` | Aggregates all results, ranks candidates, and produces final recommendation | `all_results: array` | `{ranked_list: array, recommendation: string, summary: string}` |

### Decision 3: THE STOPPING CONDITION
The agent stops when **all three candidates have been fully processed** (scored → gap-analyzed → questions generated) **AND** the final ranked output has been produced and returned. Verifiable yes/no check: `processed_count == total_candidates AND final_report_generated == true`.

### Decision 4: THE OUTPUT FORMAT
A structured JSON report:
```json
{
  "job_role": "Junior AI Engineer",
  "ranked_candidates": [
    {
      "rank": 1,
      "name": "Meera",
      "score": 85,
      "strengths": ["LangChain", "LangGraph", "embeddings", "RAG knowledge"],
      "critical_gaps": ["Docker", "CI/CD"],
      "interview_questions": { "technical": [...], "behavioral": [...] }
    },
    {
      "rank": 2,
      "name": "Priya",
      "score": 78,
      "strengths": ["Python", "RAG", "ChromaDB", "communication"],
      "critical_gaps": ["LangGraph"],
      "interview_questions": { "technical": [...], "behavioral": [...] }
    },
    {
      "rank": 3,
      "name": "Rahul",
      "score": 45,
      "strengths": ["Python", "Docker", "CI/CD"],
      "critical_gaps": ["LangChain", "RAG", "vector databases"],
      "interview_questions": { "technical": [...], "behavioral": [...] }
    }
  ],
  "recommendation": "Hire Meera (85) — strongest alignment. Priya (78) is a strong alternative.",
  "next_steps": "Schedule technical interviews focusing on critical gaps."
}
```

---

## Exercise 2 · Trace the Agent Execution for Candidate B (Rahul)

**JD Requirements (already extracted):** Required: Python, LangChain, RAG, vector databases, communication. Nice-to-have: LangGraph, Docker, CI/CD.

**Candidate B (Rahul):** B.Tech IT, Python + Java, no RAG experience, knows Docker and CI/CD, built REST APIs, average communication.

| Step | REASON | ACT | OBSERVE | DECIDE |
|------|--------|-----|---------|--------|
| **Step 1** | "I need to process Rahul. First, score him against JD requirements." | `score_candidate(candidate_id="C002", name="Rahul", profile={...}, requirements={required: ["Python","LangChain","RAG","vector databases","communication"], nice_to_have: ["LangGraph","Docker","CI/CD"]})` | `{score: 45, strengths: ["Python","Docker","CI/CD"], weaknesses: ["No LangChain","No RAG","No vector DB experience","Average communication"]}` | Score obtained (45%). Move to gap analysis. |
| **Step 2** | "Rahul scored 45%. I need to identify specific skill gaps to generate targeted questions." | `analyze_gaps(candidate_id="C002", score_result={score:45, strengths:[...], weaknesses:[...]})` | `{critical_gaps: ["LangChain","RAG","vector databases"], moderate_gaps: ["communication"]}` | Gaps identified. Move to question generation. |
| **Step 3** | "Rahul's critical gaps are LangChain, RAG, and vector databases. I need to generate questions that probe these gaps and verify his claimed strengths in Python/Docker/CI/CD." | `generate_questions(candidate_id="C002", gaps={critical:["LangChain","RAG","vector databases"], moderate:["communication"]})` | `{technical: ["Explain how RAG retrieves documents from a vector store","How would you build a LangChain agent with memory?","Compare FAISS and ChromaDB — which would you use and why?"], behavioral: ["Describe a time you explained a technical concept to a non-technical stakeholder."]}` | Rahul fully processed. Mark as complete. |
| **Final** | "Rahul processed. Score: 45%. Critical gaps in LangChain, RAG, vector DBs. Questions generated targeting those gaps. Storing results for final ranking. Moving to next candidate." | — | — | Done with Rahul. Proceed to remaining candidates (or finalize if last). |

---

## Exercise 3 · Write the Agent System Prompt

```
You are the TechVest Recruitment Agent — an autonomous AI system that processes
job candidates for a given role. Your goal is to produce a ranked shortlist with
tailored interview questions. You are NOT a chatbot. You receive a GOAL and you
execute it step by step using the tools available to you.

AVAILABLE TOOLS:
1. extract_requirements(jd_text: string) -> {required: string[], nice_to_have: string[]}
   - Parses a job description to extract structured skill requirements.

2. score_candidate(candidate_id: string, name: string, profile: object,
   requirements: object) -> {candidate_id: string, score: float, strengths: string[],
   weaknesses: string[]}
   - Scores one candidate against the JD. Score is 0–100.

3. analyze_gaps(candidate_id: string, score_result: object) ->
   {candidate_id: string, critical_gaps: string[], moderate_gaps: string[]}
   - Produces categorized gaps for interview targeting.

4. generate_questions(candidate_id: string, gaps: {critical: string[],
   moderate: string[]}) -> {candidate_id: string, technical_questions: string[],
   behavioral: string[]}
   - Generates interview questions targeting the specific gaps.

5. rank_candidates(all_results: array) -> {ranked_list: array, recommendation: string,
   summary: string}
   - Produces the final ranked output.

REASONING RULES:
- Always start by calling extract_requirements on the JD.
- Process candidates ONE AT A TIME in this order: score_candidate →
  analyze_gaps → generate_questions.
- NEVER re-process a candidate who has already been fully processed.
- NEVER call a tool without a clear reason. Before each tool call, think:
  "Why am I calling this tool, and what do I expect back?"
- After each observation, decide: continue to next step, or stop if all done.

STOPPING CONDITION:
Stop when ALL of: (a) all candidates have been scored, (b) all candidates have
had gap analysis, (c) all candidates have had questions generated, AND
(d) rank_candidates has been called and its output returned.

OUTPUT FORMAT:
You must return a final JSON object with: ranked list (ordered by score
descending), per-candidate strengths + critical gaps + interview questions,
and an overall hiring recommendation.

ERROR HANDLING:
- If a tool returns an error, log the error and retry ONCE with corrected input.
- If the retry also fails, skip that step, mark the candidate as
  "partially_processed", and continue. Include the error in the final report.
- NEVER hallucinate tool outputs. If you don't have data, say so.
- If a tool receives an incorrectly formatted input, check the schema and retry.
```

---

## Exercise 4 · Identify Failure Modes in This Agent

### Scenario A: The agent extracts requirements, then calls score_candidate for Priya, then calls score_candidate for Priya again, then again. It never moves to Rahul or Meera.

| Aspect | Details |
|--------|---------|
| **Failure Mode** | **Repetition / Infinite Loop** — the agent is stuck re-processing the same candidate. |
| **Root Cause** | No state tracking or checkpointing. The agent has no memory that Priya was already scored. Each loop iteration presents the same decision without any "already processed" signal. |
| **Fix** | Add a `processed_candidates` set to the agent's state. Before scoring any candidate, check if that candidate is already in `processed_candidates`. If so, skip to the next unprocessed candidate. Also add a step counter limit (max N tool calls) as a hard stop. |

### Scenario B: After correctly processing all 3 candidates, the agent calls extract_requirements again on the same JD, then starts re-scoring Priya. The task was already complete.

| Aspect | Details |
|--------|---------|
| **Failure Mode** | **No Termination Guard** — the agent doesn't recognize task completion. |
| **Root Cause** | The stopping condition checks candidate count but the agent re-enters the reasoning loop without a "task_complete" flag. After producing the final report, the loop resets. |
| **Fix** | Add a `task_complete` boolean flag that is set to `true` after `rank_candidates` returns. The ReAct loop checks this flag as its first action — if `true`, terminate immediately. Also consider idempotency: `extract_requirements` should return cached results if already called. |

### Scenario C: The agent processes Priya (score: 78%) and Meera (score: 85%) correctly. When it gets to Rahul (score: 45%), it generates interview questions about "embedding models" and "publication experience" — these are Meera's strengths, not Rahul's gaps.

| Aspect | Details |
|--------|---------|
| **Failure Mode** | **Context Confusion / Data Leakage** — the agent mixes Meera's profile data into Rahul's processing. |
| **Root Cause** | The LLM's context window contains both Meera's and Rahul's data. Without explicit context isolation, the model can attend to the wrong candidate's information when generating questions, especially when the prompt is long. |
| **Fix** | (1) Clear per-candidate context before processing each new candidate — only inject the current candidate's profile into the prompt. (2) Add a validation step: after generating questions, verify each question maps to Rahul's specific gaps before accepting. (3) Use structured output schemas that enforce candidate_id alignment. |

### Scenario D: The agent calls generate_questions("Rahul", gaps="many"). The tool expects a structured object {critical: [], moderate: []}, not a string. It crashes.

| Aspect | Details |
|--------|---------|
| **Failure Mode** | **Type Error / Input Validation Failure** — the agent passes a malformed argument. |
| **Root Cause** | The system prompt describes the tool's input format but the LLM generated a free-text string instead of the required structured object. The tool has no input validation or graceful error handling. |
| **Fix** | (1) Add input validation at the tool boundary — if `gaps` is a string, return a clear error message showing the expected schema. (2) Improve the system prompt with an explicit **example** of correct input format for each tool. (3) Implement a retry mechanism: on schema error, inform the LLM of the format requirement and let it re-call with correct input. |

---

## Exercise 5 · Agent vs Pipeline: The Design Decision

### 1. Argue FOR the agent — 3 scenarios where dynamic decision-making is necessary

**Scenario A: Adaptive scoring depth.** If a candidate scores borderline (e.g., 50-60%), the agent could decide to call an additional tool — e.g., `deep_dive_analysis` — to check certification projects or GitHub repos before making a final call. A pipeline would apply the same treatment to everyone.

**Scenario B: Conditional branching on gaps.** If a candidate's critical gaps include a nice-to-have skill (e.g., LangGraph for Rahul), the agent could decide to skip that gap and focus only on required-skill gaps. If gaps are severe, it could skip question generation entirely and mark the candidate as "not shortlisted." A pipeline cannot make this judgment call.

**Scenario C: Tie-breaking between close scores.** If Priya (78%) and Meera (85%) were actually Priya (82%) and Meera (83%), the agent could decide to call a `compare_candidates` tool to do a nuanced comparison and generate a justification, rather than blindly ranking by score.

### 2. Argue AGAINST the agent — when a fixed pipeline is simpler

A fixed pipeline — `extract → for each candidate: [score → gaps → questions] → rank` — is:
- **Deterministic**: identical inputs always produce identical outputs. No hallucination, no looping, no context leakage.
- **Testable**: each stage is an isolated unit with known inputs/outputs.
- **Cheaper**: zero LLM orchestration cost. You only need an LLM call for `generate_questions` (the creative step). Scoring, gap analysis, and ranking can be rule-based.
- **Reliable**: no risk of the agent getting stuck, re-processing, or misformatting tool calls. For 3 predictable steps × 3 candidates = 9 fixed steps, an agent is overkill.

### 3. Design a hybrid: fixed outer loop + agent inner loop

```
┌──────────────────────────────────────────────────┐
│              FIXED OUTER LOOP                     │
│  for each candidate in [Priya, Rahul, Meera]:     │
│     ┌────────────────────────────────────────┐   │
│     │      AGENT INNER LOOP (ReAct)          │   │
│     │                                        │   │
│     │  Step 1: score_candidate()             │   │
│     │       ↓                                │   │
│     │  Step 2: IF score ≥ 80% → skip gaps    │   │
│     │          generate_advanced_questions()  │   │
│     │          ELSE → analyze_gaps()          │   │
│     │             ↓                          │   │
│     │             IF critical_gaps empty →    │   │
│     │               generate_standard_qs()    │   │
│     │             ELSE → agent decides which  │   │
│     │               areas to probe + retry    │   │
│     │               logic on malformed input  │   │
│     │                                        │   │
│     │  Agent decides when done with this     │   │
│     │  candidate, returns structured result   │   │
│     └────────────────────────────────────────┘   │
│       ↓                                          │
│  Aggregate all results                           │
│  Call rank_candidates()                          │
│  Return final output                             │
└──────────────────────────────────────────────────┘
```

This hybrid gives you reliability (the outer loop guarantees every candidate is processed exactly once) + flexibility (the inner agent adapts its behavior per candidate).

### 4. What changes if you go from 3 candidates to 300?

**Agent pattern (pure ReAct):** Does NOT scale. 300 candidates × ~4 tool calls each = 1,200 LLM calls. At ~$0.01–0.03 per call (GPT-4o), that's **$12–36 per run**. Add latency: 1,200 sequential calls at 3–5 seconds each = **1–1.7 hours**. Plus the risk of looping increases with more iterations.

**Pipeline pattern:** Scales well. Batch-score all 300 candidates with a single LLM call (or rule-based scoring). Filter to top 10–20. Then run the agent inner loop only on those shortlisted candidates. Cost: ~$1–2. Time: ~2 minutes.

**Hybrid for 300 candidates:**
1. **Batch filter** (pipeline stage): Score all 300 candidates using a fast, cheap embedding-similarity approach (no LLM). Keep top 20.
2. **Agent inner loop** (for top 20): Run the ReAct agent on each shortlisted candidate for nuanced gap analysis and question generation.
3. **Final rank** (pipeline stage): Aggregate and produce the report.

**Verdict:** The pure agent pattern works for 3–10 candidates. Beyond that, a pipeline-first approach with agentic depth only on the shortlist is the practical architecture.
