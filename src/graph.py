import json
from datetime import datetime
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import AgentState
from src.schemas import (
    CandidateProfile, ScoreCard, ShortlistEntry, InterviewProposal,
    InterviewSlot, TrajectoryStep,
)
from src.tools import parse_resume, score_candidate, check_availability, propose_interview, detect_injection
from src.guardrails import check_injection_defence, fairness_check

MAX_STEPS = 30


def _log(state: AgentState, thought: str, action: str, action_input: dict, observation: str) -> AgentState:
    step = TrajectoryStep(
        step_number=state.get("step_count", 0) + 1,
        thought=thought,
        action=action,
        action_input=action_input,
        observation=observation[:500],
        timestamp=datetime.now().isoformat(),
    )
    return {"trajectory": [step], "step_count": state.get("step_count", 0) + 1}


def node_plan(state: AgentState) -> AgentState:
    thought = "Planning the recruitment workflow: parse each candidate, score against rubric, check availability for top candidates, then produce shortlist."
    return _log(state, thought, "plan", {"candidates": list(state["candidates"].keys())}, "Plan created: parse -> score -> check availability -> shortlist")


def node_parse_next(state: AgentState) -> AgentState:
    remaining = state.get("candidates_remaining", [])
    if not remaining:
        return _log(state, "No candidates remaining to parse.", "parse", {}, "All candidates parsed.")

    name = remaining[0]
    resume_text = state["candidates"][name]

    injection_check = check_injection_defence(resume_text)
    parsed = parse_resume(resume_text)

    updates = {
        "parsed_profiles": {name: parsed},
        "candidates_remaining": remaining[1:],
        "current_candidate": name,
        "injection_attempt_detected": state.get("injection_attempt_detected", False) or injection_check["detected"],
    }

    obs = f"Parsed {name}: {parsed.skills[:5] if parsed.skills else 'No skills found'}"
    if injection_check["detected"]:
        obs += " | INJECTION ATTEMPT DETECTED AND BLOCKED"

    log_updates = _log(state, f"Parsing resume for {name}", "parse_resume", {"candidate": name}, obs)
    updates.update(log_updates)
    return updates


def node_score_next(state: AgentState) -> AgentState:
    current = state.get("current_candidate")
    if not current:
        return _log(state, "No current candidate to score.", "score", {}, "Nothing to score.")

    profile = state["parsed_profiles"].get(current)
    if not profile:
        return _log(state, f"No parsed profile for {current}", "score", {}, "Profile missing — skipping.")

    scorecard = score_candidate(profile, state["rubric"])
    obs = f"{current} scored {scorecard.weighted_total:.2f}/5.0"

    updates = {"scorecards": {current: scorecard}}
    log_updates = _log(state, f"Scoring {current} against rubric", "score_candidate", {"candidate": current}, obs)
    updates.update(log_updates)
    return updates


def node_decide(state: AgentState) -> AgentState:
    current = state.get("current_candidate")
    scorecard = state["scorecards"].get(current)
    if not scorecard:
        return _log(state, "No scorecard to decide on.", "decide", {}, "Skipping.")

    total = scorecard.weighted_total
    if total >= 3.5:
        recommendation = "interview"
    elif total >= 2.0:
        recommendation = "hold"
    else:
        recommendation = "reject"

    justifications = []
    for cs in scorecard.criterion_scores:
        justifications.append(f"{cs.criterion}: {cs.score}/5 (weight {cs.weight}) — {cs.evidence}")

    entry = ShortlistEntry(
        candidate_name=current,
        rank=0,
        recommendation=recommendation,
        scorecard=scorecard,
        justification="; ".join(justifications),
        proposed_action=None,
    )

    existing = state.get("shortlist", [])
    updated = [e for e in existing if e.candidate_name != current] + [entry]

    obs = f"{current} → {recommendation.upper()} (score: {total:.2f})"
    updates = {"shortlist": updated}
    log_updates = _log(state, f"Deciding recommendation for {current}", "decide", {"candidate": current, "score": total, "recommendation": recommendation}, obs)
    updates.update(log_updates)
    return updates


def node_check_availability(state: AgentState) -> AgentState:
    shortlist = state.get("shortlist", [])
    interview_candidates = [e for e in shortlist if e.recommendation == "interview"]
    if not interview_candidates:
        return _log(state, "No interview candidates to check availability for.", "check_availability", {}, "No candidates need scheduling.")

    for entry in interview_candidates:
        slots = check_availability(entry.candidate_name)
        if slots:
            proposal = propose_interview(entry.candidate_name, slots[0])
            entry.proposed_action = proposal

    obs = f"Availability checked for {len(interview_candidates)} candidate(s). Proposals pending approval."
    return _log(state, "Checking interview availability for shortlisted candidates", "check_availability", {"candidates": [e.candidate_name for e in interview_candidates]}, obs)


def node_route_after_parse(state: AgentState) -> AgentState:
    remaining = state.get("candidates_remaining", [])
    current = state.get("current_candidate")
    if current and current in state.get("parsed_profiles", {}):
        return "score"
    return "wait"


def node_route_after_score(state: AgentState) -> AgentState:
    current = state.get("current_candidate")
    if current and current in state.get("scorecards", {}):
        return "decide"
    return "wait"


def node_route_after_decide(state: AgentState) -> AgentState:
    remaining = state.get("candidates_remaining", [])
    if remaining:
        return "parse"
    return "finalize"


def node_finalize(state: AgentState) -> AgentState:
    shortlist = state.get("shortlist", [])
    shortlist.sort(key=lambda e: e.scorecard.weighted_total, reverse=True)
    for i, entry in enumerate(shortlist):
        entry.rank = i + 1

    obs_lines = ["=== FINAL SHORTLIST ==="]
    for entry in shortlist:
        action = f"Proposed: {entry.proposed_action.slot.date} @ {entry.proposed_action.slot.time} ({entry.proposed_action.status})" if entry.proposed_action else "No action proposed"
        obs_lines.append(f"#{entry.rank} {entry.candidate_name} — {entry.recommendation.upper()} ({entry.scorecard.weighted_total:.2f}/5.0)")
        obs_lines.append(f"  {action}")

    obs = "\n".join(obs_lines)
    updates = {"phase": "completed"}
    log_updates = _log(state, "Finalizing shortlist and ranking candidates", "finalize", {"shortlist": [e.candidate_name for e in shortlist]}, obs)
    updates.update(log_updates)
    return updates


def should_continue_parse(state: AgentState) -> Literal["score", "wait"]:
    current = state.get("current_candidate")
    if current and current in state.get("parsed_profiles", {}):
        return "score"
    return "wait"


def should_continue_score(state: AgentState) -> Literal["decide", "wait"]:
    current = state.get("current_candidate")
    if current and current in state.get("scorecards", {}):
        return "decide"
    return "wait"


def should_continue_decide(state: AgentState) -> Literal["parse", "finalize"]:
    remaining = state.get("candidates_remaining", [])
    return "parse" if remaining else "finalize"


def should_gate_schedule(state: AgentState) -> Literal["schedule", END]:
    shortlist = state.get("shortlist", [])
    if any(e.recommendation == "interview" for e in shortlist):
        return "schedule"
    return END


def build_graph() -> StateGraph:

    workflow = StateGraph(AgentState)

    workflow.add_node("plan", node_plan)
    workflow.add_node("parse", node_parse_next)
    workflow.add_node("score", node_score_next)
    workflow.add_node("decide", node_decide)
    workflow.add_node("schedule", node_check_availability)
    workflow.add_node("finalize", node_finalize)

    workflow.set_entry_point("plan")

    workflow.add_conditional_edges(
        "plan",
        lambda s: "parse",
        {"parse": "parse"},
    )

    workflow.add_conditional_edges(
        "parse",
        should_continue_parse,
        {"score": "score", "wait": "parse"},
    )

    workflow.add_conditional_edges(
        "score",
        should_continue_score,
        {"decide": "decide", "wait": "score"},
    )

    workflow.add_conditional_edges(
        "decide",
        should_continue_decide,
        {"parse": "parse", "finalize": "finalize"},
    )

    workflow.add_conditional_edges(
        "finalize",
        should_gate_schedule,
        {"schedule": "schedule", END: END},
    )

    workflow.add_conditional_edges(
        "schedule",
        lambda s: END,
        {END: END},
    )

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app
