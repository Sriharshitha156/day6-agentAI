from pydantic import BaseModel, Field
from typing import Optional


class CandidateProfile(BaseModel):
    name: str
    email: str
    education: str
    skills: list[str]
    experience_summary: list[str]
    projects: list[str]
    certifications: list[str]
    raw_resume: str


class CriterionScore(BaseModel):
    criterion: str
    score: int
    weight: float
    evidence: str


class ScoreCard(BaseModel):
    candidate_name: str
    criterion_scores: list[CriterionScore]
    weighted_total: float
    max_possible: float = 5.0


class InterviewSlot(BaseModel):
    candidate: str
    date: str
    time: str
    duration_minutes: int = 45


class InterviewProposal(BaseModel):
    candidate: str
    slot: InterviewSlot
    status: str = "pending_approval"


class ShortlistEntry(BaseModel):
    candidate_name: str
    rank: int
    recommendation: str
    scorecard: ScoreCard
    justification: str
    proposed_action: Optional[InterviewProposal] = None


class FinalDecision(BaseModel):
    shortlist: list[ShortlistEntry]
    trajectory: list[dict]


class TrajectoryStep(BaseModel):
    step_number: int
    thought: str
    action: str
    action_input: dict
    observation: str
    timestamp: str
