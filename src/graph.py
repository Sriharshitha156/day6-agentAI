import json
from datetime import datetime
from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, BaseMessage

from src.state import AgentState
from src.schemas import (
    CandidateProfile, ScoreCard, ShortlistEntry, TrajectoryStep,
)
from src.tools import (
    parse_resume_deterministic, score_candidate_deterministic,
    check_availability, propose_interview, detect_injection,
    AVAILABLE_TOOLS, TOOL_NAME_MAP, llm_parse_resume, llm_score_candidate,
)
from src.guardrails import check_injection_defence, fairness_check
from src.llm import get_llm

MAX_STEPS = 30

SYSTEM_PROMPT = """You are the TechVest Recruitment Agent, an autonomous hiring assistant.

Job Description:
{jd}

Scoring Rubric (criteria with weights and 0-5 scale):
{rubric}

Candidates to evaluate:
{candidate_names}

You have access to these tools:
1. tool_parse_resume(resume_text: str) - Parse a candidate's raw resume into structured profile
2. tool_score_candidate(profile_json: str, rubric_json: str) - Score a parsed candidate against rubric
3. tool_check_availability(candidate_name: str, week: str) - Get interview time slots
4. tool_propose_interview(candidate_name: str, slot_json: str) - Propose an interview slot (REQUIRES HUMAN APPROVAL)

Process each candidate completely (parse + score) before moving to the next.
After all candidates are scored, propose interviews for top candidates (score >= 3.5).
Call each tool one at a time. Wait for the result before calling the next tool.

When ALL work is done, respond with "FINALIZE" to generate the shortlist."""


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


def router_entry(state: AgentState) -> Literal["plan", "call_llm"]:
    return "call_llm" if state.get("llm_mode") else "plan"


def node_plan(state: AgentState) -> AgentState:
    thought = "Planning the recruitment workflow: parse each candidate, score against rubric, check availability for top candidates, then produce shortlist."
    return _log(state, thought, "plan", {"candidates": list(state["candidates"].keys())}, "Plan created: parse -> score -> check availability -> shortlist")


def node_parse_next(state: AgentState) -> AgentState:
    remaining = state.get("candidates_remaining", [])
    if not remaining:
        return {"current_candidate": None, "step_count": state.get("step_count", 0)}
    name = remaining[0]
    resume_text = state["candidates"][name]
    injection_check = check_injection_defence(resume_text)
    parsed = parse_resume_deterministic(resume_text)
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
    scorecard = score_candidate_deterministic(profile, state["rubric"])
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
    recommendation = "interview" if total >= 3.5 else ("hold" if total >= 2.0 else "reject")
    justifications = [f"{cs.criterion}: {cs.score}/5 (weight {cs.weight}) — {cs.evidence}" for cs in scorecard.criterion_scores]
    entry = ShortlistEntry(
        candidate_name=current, rank=0, recommendation=recommendation,
        scorecard=scorecard, justification="; ".join(justifications), proposed_action=None,
    )
    existing = [e for e in state.get("shortlist", []) if e.candidate_name != current] + [entry]
    obs = f"{current} -> {recommendation.upper()} (score: {total:.2f})"
    updates = {"shortlist": existing}
    log_updates = _log(state, f"Deciding recommendation for {current}", "decide", {"candidate": current, "score": total, "recommendation": recommendation}, obs)
    updates.update(log_updates)
    return updates


def node_check_availability(state: AgentState) -> AgentState:
    interview_candidates = [e for e in state.get("shortlist", []) if e.recommendation == "interview"]
    if not interview_candidates:
        return _log(state, "No interview candidates to check availability for.", "check_availability", {}, "No candidates need scheduling.")
    for entry in interview_candidates:
        slots = check_availability(entry.candidate_name)
        if slots:
            proposal = propose_interview(entry.candidate_name, slots[0])
            entry.proposed_action = proposal
    obs = f"Availability checked for {len(interview_candidates)} candidate(s). Proposals pending approval."
    return _log(state, "Checking interview availability for shortlisted candidates", "check_availability", {"candidates": [e.candidate_name for e in interview_candidates]}, obs)


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


def should_continue_parse(state: AgentState) -> Literal["score", "finalize"]:
    remaining = state.get("candidates_remaining", [])
    if not remaining:
        return "finalize"
    current = state.get("current_candidate")
    return "score" if (current and current in state.get("parsed_profiles", {})) else "finalize"


def should_continue_score(state: AgentState) -> Literal["decide", "finalize"]:
    current = state.get("current_candidate")
    return "decide" if (current and current in state.get("scorecards", {})) else "finalize"


def should_continue_decide(state: AgentState) -> Literal["parse", "finalize"]:
    return "parse" if state.get("candidates_remaining") else "finalize"


def should_gate_schedule(state: AgentState) -> Literal["schedule", END]:
    return "schedule" if any(e.recommendation == "interview" for e in state.get("shortlist", [])) else END


# --- LLM / ReAct nodes ---

def _build_system_message(state: AgentState) -> SystemMessage:
    names = list(state["candidates"].keys())
    rubric_str = json.dumps(state.get("rubric", {}), indent=2)
    return SystemMessage(content=SYSTEM_PROMPT.format(
        jd=state.get("job_description", ""),
        rubric=rubric_str,
        candidate_names=", ".join(names),
    ))


def node_call_llm(state: AgentState) -> AgentState:
    api_key = state.get("api_key", "")
    provider = state.get("provider", "openai")
    if not api_key:
        return {"error": "No API key configured for LLM mode."}

    llm = get_llm(api_key, provider)
    if not llm:
        return {"error": "Failed to initialize LLM."}

    llm_with_tools = llm.bind_tools(AVAILABLE_TOOLS)

    messages = list(state.get("messages", []))
    if not messages or not any(isinstance(m, SystemMessage) for m in messages):
        messages = [_build_system_message(state)] + messages

    try:
        response = llm_with_tools.invoke(messages)
    except Exception as e:
        return {"error": f"LLM call failed: {e}"}

    new_messages = messages + [response]
    aim = response

    all_candidates = list(state["candidates"].keys())
    processed = set(state.get("parsed_profiles", {}).keys())
    remaining = [c for c in all_candidates if c not in processed]

    updates = {"messages": new_messages}

    if remaining:
        updates["candidates_remaining"] = remaining

    obs = f"LLM responded: {aim.content[:200] if aim.content else 'Tool call requested'}"

    if hasattr(aim, "tool_calls") and aim.tool_calls:
        tool_names = [tc["name"] for tc in aim.tool_calls]
        obs = f"LLM requesting tool(s): {tool_names}"

    log_updates = _log(state, "LLM deciding next action", "call_llm", {"messages": len(new_messages)}, obs)
    updates.update(log_updates)
    return updates


def route_after_llm(state: AgentState) -> Literal["execute_tool", "finalize", "wait"]:
    if state.get("error"):
        return "wait"
    messages = state.get("messages", [])
    if not messages:
        return "wait"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "execute_tool"
    return "finalize"


def node_execute_tool(state: AgentState) -> AgentState:
    tool_node = ToolNode(tools=AVAILABLE_TOOLS)
    try:
        result = tool_node.invoke(state)
        tool_messages = []
        for msg in result.get("messages", []):
            if isinstance(msg, ToolMessage):
                tool_messages.append(msg)
        if tool_messages:
            all_messages = list(state.get("messages", [])) + tool_messages
            obs = "; ".join(f"Tool: {m.name} -> {m.content[:100]}" for m in tool_messages)
            for tm in tool_messages:
                try:
                    data = json.loads(tm.content)
                    if isinstance(data, dict) and "candidate" in data and data.get("status") == "pending_approval":
                        if "shortlist" in state:
                            sl = state["shortlist"]
                            for entry in sl:
                                if entry.candidate_name == data["candidate"]:
                                    entry.proposed_action = propose_interview(data["candidate"], data.get("slot", {}))
                                    break
                        return {"messages": all_messages, "human_approval_pending": data}
                except (json.JSONDecodeError, TypeError):
                    pass
            return {"messages": all_messages, **({"messages": tool_messages})}
        return {"messages": state.get("messages", [])}
    except Exception as e:
        return {"error": f"Tool execution failed: {e}"}


def route_tool_continue(state: AgentState) -> Literal["call_llm", "interrupt", END]:
    if state.get("error"):
        return END
    if state.get("human_approval_pending"):
        return "interrupt"
    step_count = state.get("step_count", 0)
    if step_count >= MAX_STEPS:
        return END
    return "call_llm"


def node_interrupt(state: AgentState) -> AgentState:
    pending = state.get("human_approval_pending")
    if pending:
        interrupt({"message": "Human approval required for interview proposal", "pending": pending})
    return state


def route_after_interrupt(state: AgentState) -> Literal["finalize", END]:
    return "finalize"


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("plan", node_plan)
    workflow.add_node("parse", node_parse_next)
    workflow.add_node("score", node_score_next)
    workflow.add_node("decide", node_decide)
    workflow.add_node("schedule", node_check_availability)
    workflow.add_node("finalize", node_finalize)
    workflow.add_node("call_llm", node_call_llm)
    workflow.add_node("execute_tool", node_execute_tool)
    workflow.add_node("interrupt", node_interrupt)

    workflow.set_conditional_entry_point(
        router_entry,
        {"plan": "plan", "call_llm": "call_llm"},
    )

    workflow.add_conditional_edges("plan", lambda s: "parse", {"parse": "parse"})
    workflow.add_conditional_edges("parse", should_continue_parse, {"score": "score", "finalize": "finalize"})
    workflow.add_conditional_edges("score", should_continue_score, {"decide": "decide", "finalize": "finalize"})
    workflow.add_conditional_edges("decide", should_continue_decide, {"parse": "parse", "finalize": "finalize"})
    workflow.add_conditional_edges("finalize", should_gate_schedule, {"schedule": "schedule", END: END})
    workflow.add_conditional_edges("schedule", lambda s: END, {END: END})

    workflow.add_conditional_edges("call_llm", route_after_llm, {"execute_tool": "execute_tool", "finalize": "finalize", "wait": "call_llm"})
    workflow.add_conditional_edges("execute_tool", route_tool_continue, {"call_llm": "call_llm", "interrupt": "interrupt", END: END})
    workflow.add_conditional_edges("interrupt", route_after_interrupt, {"finalize": "finalize", END: END})

    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app
