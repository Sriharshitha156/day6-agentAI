from src.schemas import CandidateProfile, ScoreCard
from src.tools import detect_injection


def check_injection_defence(resume_text: str) -> dict:
    detected = detect_injection(resume_text)
    return {
        "detected": detected,
        "blocked": detected,
        "message": "Prompt injection detected and blocked." if detected else "No injection detected.",
    }


def fairness_check(profile_a: CandidateProfile, profile_b: CandidateProfile, score_a: ScoreCard, score_b: ScoreCard) -> dict:
    name_a = profile_a.name
    name_b = profile_b.name

    relevant_a = sum(
        cs.score * cs.weight
        for cs in score_a.criterion_scores
        if cs.criterion.lower() not in ["communication & collaboration"]
    )
    relevant_b = sum(
        cs.score * cs.weight
        for cs in score_b.criterion_scores
        if cs.criterion.lower() not in ["communication & collaboration"]
    )

    return {
        "passed": abs(relevant_a - relevant_b) < 0.5,
        "candidate_a": name_a,
        "candidate_b": name_b,
        "relevant_score_a": round(relevant_a, 2),
        "relevant_score_b": round(relevant_b, 2),
        "note": "Fairness check compares scores on JD-relevant criteria only.",
    }
