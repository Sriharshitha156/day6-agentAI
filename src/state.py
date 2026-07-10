from typing import TypedDict, Optional, Annotated, Any
from langgraph.graph.message import add_messages
from src.schemas import CandidateProfile, ScoreCard, ShortlistEntry, TrajectoryStep


def reduce_shortlist(existing: list[ShortlistEntry], update: list[ShortlistEntry]) -> list[ShortlistEntry]:
    return update if update else (existing or [])


def reduce_trajectory(existing: list[TrajectoryStep], update: list[TrajectoryStep]) -> list[TrajectoryStep]:
    if update:
        return (existing or []) + update
    return existing or []


def reduce_parsed(existing: dict[str, CandidateProfile], update: dict[str, CandidateProfile]) -> dict[str, CandidateProfile]:
    merged = dict(existing or {})
    if update:
        merged.update(update)
    return merged


def reduce_scorecards(existing: dict[str, ScoreCard], update: dict[str, ScoreCard]) -> dict[str, ScoreCard]:
    merged = dict(existing or {})
    if update:
        merged.update(update)
    return merged


class AgentState(TypedDict):
    job_description: str
    rubric: dict
    candidates: dict[str, str]
    parsed_profiles: Annotated[dict[str, CandidateProfile], reduce_parsed]
    scorecards: Annotated[dict[str, ScoreCard], reduce_scorecards]
    shortlist: Annotated[list[ShortlistEntry], reduce_shortlist]
    trajectory: Annotated[list[TrajectoryStep], reduce_trajectory]
    current_candidate: Optional[str]
    candidates_remaining: list[str]
    phase: str
    step_count: int
    human_approval_pending: Optional[dict]
    injection_attempt_detected: bool
    fairness_checked: bool
    error: Optional[str]
    messages: Annotated[list, add_messages]
    llm_mode: bool
    api_key: str
    provider: str
