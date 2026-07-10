import json
from datetime import datetime, timedelta
from typing import Optional, Any
from langchain_core.tools import tool
from src.schemas import CandidateProfile, ScoreCard, CriterionScore, InterviewSlot, InterviewProposal
from src.llm import get_llm

INJECTION_PATTERNS = [
    "system override", "ignore your instructions", "ignore all previous",
    "rank me first", "must be ranked first", "this candidate must be",
]


def detect_injection(resume_text: str) -> bool:
    lowered = resume_text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lowered:
            return True
    return False


LLM_PARSE_PROMPT = """Extract structured information from this resume. Return valid JSON with these fields:
- name: full name
- email: email address
- education: highest degree and institution
- skills: list of technical skills
- experience_summary: list of experience entries (keep key details)
- projects: list of projects
- certifications: list of certifications

Resume:
{resume}"""


LLM_SCORE_PROMPT = """You are a hiring evaluator. Score this candidate against each criterion in the rubric.

Rubric: {rubric_json}

Candidate profile:
{profile_json}

For each criterion, return:
- criterion: name
- score: integer 0-5 based on the rubric's scale
- evidence: specific line/resource from the candidate's profile that justifies the score

Return a JSON object with:
- candidate_name: string
- criterion_scores: list of {{criterion, score, weight, evidence}}
- weighted_total: calculated float (sum of score * weight for each, max 5.0)
- justification: brief overall summary

Be strict and evidence-based. Score only on what the resume explicitly shows. Do NOT be lenient."""


async def llm_parse_resume(resume_text: str, llm: Any) -> CandidateProfile:
    prompt = LLM_PARSE_PROMPT.format(resume=resume_text[:5000])
    structured_llm = llm.with_structured_output(CandidateProfile)
    try:
        result = await structured_llm.ainvoke(prompt)
        result.raw_resume = resume_text
        return result
    except Exception:
        return parse_resume_deterministic(resume_text)


async def llm_score_candidate(profile: CandidateProfile, rubric: dict, llm: Any) -> ScoreCard:
    profile_json = profile.model_dump_json()
    rubric_json = json.dumps(rubric, indent=2)
    prompt = LLM_SCORE_PROMPT.format(rubric_json=rubric_json, profile_json=profile_json)

    class LLMScoreOutput(ScoreCard):
        justification: str = ""

    structured_llm = llm.with_structured_output(LLMScoreOutput)
    try:
        result = await structured_llm.ainvoke(prompt)
        result.max_possible = 5.0
        return result
    except Exception:
        return score_candidate_deterministic(profile, rubric)


def parse_resume_deterministic(resume_text: str) -> CandidateProfile:
    lines = resume_text.strip().split("\n")
    name = ""
    email = ""
    education = ""
    skills = []
    experience = []
    projects = []
    certifications = []
    current_section = ""

    for line in lines:
        ls = line.strip()
        if ls.startswith("# "):
            name = ls.lstrip("# ")
        elif ls.startswith("**Email:**"):
            email = ls.replace("**Email:**", "").strip()
        elif ls.startswith("## "):
            current_section = ls.lstrip("## ").lower()
        if "skills" in current_section and ls and not ls.startswith("##") and not ls.startswith("**"):
            for s in ls.split(","):
                s = s.strip().lstrip("- *")
                if s and len(s) > 1:
                    skills.append(s)
        if ls.startswith("- ") or ls.startswith("* "):
            item = ls.lstrip("- *").strip()
            if "skills" in current_section:
                for s in item.split(","):
                    s = s.strip()
                    if s:
                        skills.append(s)
            elif any(x in current_section for x in ["experience", "intern", "freelance"]):
                if len(item) > 15:
                    experience.append(item)
            elif "projects" in current_section:
                if len(item) > 10:
                    projects.append(item)
            elif "certifications" in current_section:
                certifications.append(item)
        elif "**" in ls and "education" in current_section:
            education = ls.replace("**", "").strip()

    skills = list(dict.fromkeys(skills))
    return CandidateProfile(
        name=name, email=email, education=education,
        skills=skills or ["Not specified"],
        experience_summary=experience or ["No experience listed"],
        projects=projects or ["No projects listed"],
        certifications=certifications or ["No certifications listed"],
        raw_resume=resume_text,
    )


_CRITERION_WEIGHTS = {
    "python": [("open-source", "open source"), ("production", "deployed"), ("pandas", "numpy")],
}


def _keyword_score(cname: str, text: str, skills: list[str], exp: list[str], proj: list[str]) -> tuple[int, str]:
    text_lower = text.lower()
    skills_lower = [s.lower() for s in skills]
    exp_concat = " ".join(e.lower() for e in exp)
    proj_concat = " ".join(p.lower() for p in proj)

    def _ml_check():
        if "published" in text_lower or "paper" in text_lower:
            return 5
        if "production" in exp_concat and ("model" in exp_concat or " ml " in exp_concat):
            return 4
        if "model" in proj_concat or ("scikit-learn" in skills_lower and "project" in proj_concat):
            return 3
        if any(x in skills_lower for x in ["machine learning", "ml"]):
            return 2
        return 1

    checks = {
        "python": lambda: (
            5 if any(k in " ".join(exp + proj).lower() for k in ["open-source", "open source"])
            else 4 if ("production" in exp_concat or "deployed" in exp_concat) and "python" in skills_lower
            else 3 if "python" in skills_lower and ("pandas" in skills_lower or "numpy" in skills_lower)
            else 2 if "python" in skills_lower else 1
        ),
        "ml": _ml_check,
        "machine learning": _ml_check,
        "fundamental": _ml_check,
        "tool": lambda: min(1 + sum(1 for t in ["pandas", "numpy", "scikit-learn", "pytorch", "tensorflow", "sql"] if t in skills_lower), 5),
        "framework": lambda: min(1 + sum(1 for t in ["pandas", "numpy", "scikit-learn", "pytorch", "tensorflow", "sql"] if t in skills_lower), 5),
        "data": lambda: 4 if any(x in exp_concat for x in ["pipeline", "etl"]) else 3 if "sql" in skills_lower and ("pipeline" in text_lower or "processing" in text_lower) else 2 if "sql" in skills_lower else 1 if any("data" in s.lower() for s in skills) else 0,
        "project": lambda: min(5, sum(1 for kw in ["ml", "machine learning", "nlp", "fraud", "recommendation", "forecast", "lstm", "transformer", "sentiment"] if kw in proj_concat or kw in exp_concat) + 1),
        "relevant": lambda: min(5, sum(1 for kw in ["ml", "machine learning", "nlp", "fraud", "recommendation", "forecast", "lstm", "transformer", "sentiment"] if kw in proj_concat or kw in exp_concat) + 1),
        "communication": lambda: 4 if any(x in exp_concat for x in ["mentor", "lead"]) else 3 if any(x in exp_concat for x in ["present", "presented"]) else 2 if any(x in exp_concat for x in ["collaborat", "team"]) else 1,
        "collaboration": lambda: 4 if any(x in exp_concat for x in ["mentor", "lead"]) else 3 if any(x in exp_concat for x in ["present", "presented"]) else 2 if any(x in exp_concat for x in ["collaborat", "team"]) else 1,
    }
    for key, fn in checks.items():
        if key in cname:
            return fn()
    return 2


def _find_evidence_deterministic(cname: str, profile: CandidateProfile) -> str:
    cl = cname.lower()
    sk = [s.lower() for s in profile.skills]
    for kw, terms in [
        ("python", (("python", "Experience"),)),
        ("ml", (("model", "Experience"), ("ml", "Experience"))),
    ]:
        if kw in cl:
            for term, prefix in terms:
                for e in profile.experience_summary:
                    if term in e.lower():
                        return f"{prefix}, line: {e[:100]}"
            if kw == "python" and "python" in sk:
                return "Skills section lists Python"
            return ""
    if any(x in cl for x in ["tool", "framework"]):
        found = [s for s in profile.skills if s.lower() in ["scikit-learn", "pandas", "numpy", "pytorch", "tensorflow", "sql"]]
        return f"Skills section: {', '.join(found[:4])}" if found else ""
    if "data" in cl:
        for e in profile.experience_summary:
            if any(x in e.lower() for x in ["pipeline", "etl", "sql"]):
                return f"Experience, line: {e[:100]}"
        return ""
    if any(x in cl for x in ["project", "relevant"]):
        for p in profile.projects:
            if any(kw in p.lower() for kw in ["ml", "machine learning", "nlp", "fraud", "recommendation", "forecast"]):
                return f"Projects, line: {p[:100]}"
        for e in profile.experience_summary:
            if any(kw in e.lower() for kw in ["ml", "fraud", "model", "forecast"]):
                return f"Experience, line: {e[:100]}"
        return ""
    if any(x in cl for x in ["communication", "collaboration"]):
        for e in profile.experience_summary:
            if any(x in e.lower() for x in ["present", "mentor", "collaborat"]):
                return f"Experience, line: {e[:100]}"
        return ""
    return ""


def score_candidate_deterministic(profile: CandidateProfile, rubric: dict) -> ScoreCard:
    text = (
        f"Name: {profile.name}\nEducation: {profile.education}\n"
        f"Skills: {', '.join(profile.skills)}\n"
        f"Experience: {'; '.join(profile.experience_summary)}\n"
        f"Projects: {'; '.join(profile.projects)}\n"
        f"Certifications: {'; '.join(profile.certifications)}"
    )
    scores = []
    for c in rubric["criteria"]:
        cname = c["name"].lower()
        score = _keyword_score(cname, text, profile.skills, profile.experience_summary, profile.projects)
        evidence = _find_evidence_deterministic(cname, profile) or "No direct evidence found in resume"
        scores.append(CriterionScore(criterion=c["name"], score=score, weight=c["weight"], evidence=evidence))
    total = round(min(sum(s.score * s.weight for s in scores), 5.0), 2)
    return ScoreCard(candidate_name=profile.name, criterion_scores=scores, weighted_total=total)


def check_availability(candidate_name: str, week: str = "next") -> list[InterviewSlot]:
    base = datetime.now() + timedelta(days=7 if week == "next" else 14)
    slots = []
    for day_offset in range(3):
        day = base + timedelta(days=day_offset)
        for hour in [10, 14, 16]:
            slots.append(InterviewSlot(
                candidate=candidate_name,
                date=day.strftime("%Y-%m-%d"),
                time=f"{hour:02d}:00",
                duration_minutes=45,
            ))
    return slots


def propose_interview(candidate_name: str, slot: InterviewSlot) -> InterviewProposal:
    return InterviewProposal(
        candidate=candidate_name,
        slot=slot,
        status="pending_approval",
    )


def _check_availability_dict(candidate_name: str, week: str = "next") -> list[dict]:
    base = datetime.now() + timedelta(days=7 if week == "next" else 14)
    slots = []
    for day_offset in range(3):
        day = base + timedelta(days=day_offset)
        for hour in [10, 14, 16]:
            slots.append({
                "candidate": candidate_name,
                "date": day.strftime("%Y-%m-%d"),
                "time": f"{hour:02d}:00",
                "duration_minutes": 45,
            })
    return slots


def _propose_interview_dict(candidate_name: str, slot: dict) -> dict:
    return {
        "candidate": candidate_name,
        "slot": slot,
        "status": "pending_approval",
    }


@tool
def tool_parse_resume(resume_text: str) -> str:
    """Parse a candidate's raw resume text into a structured profile. Takes the full resume text. Returns a JSON string with name, skills, experience, etc."""
    profile = parse_resume_deterministic(resume_text)
    return profile.model_dump_json()


@tool
def tool_score_candidate(profile_json: str, rubric_json: str) -> str:
    """Score a parsed candidate profile against a rubric. Takes profile JSON and rubric JSON. Returns a JSON string with per-criterion scores, evidence, and weighted total."""
    try:
        rubric = json.loads(rubric_json) if isinstance(rubric_json, str) else rubric_json
        profile = CandidateProfile.model_validate_json(profile_json) if isinstance(profile_json, str) else profile_json
    except Exception:
        return json.dumps({"error": "Invalid profile or rubric JSON"})
    scorecard = score_candidate_deterministic(profile, rubric)
    return scorecard.model_dump_json()


@tool
def tool_check_availability(candidate_name: str, week: str = "next") -> str:
    """Check interview availability for a candidate. Returns a JSON list of available slots with date, time, and duration."""
    slots = _check_availability_dict(candidate_name, week)
    return json.dumps(slots)


@tool
def tool_propose_interview(candidate_name: str, slot_json: str) -> str:
    """Propose an interview slot for a candidate. Returns a confirmation JSON with status=pending_approval. This tool REQUIRES human approval before it can proceed."""
    try:
        slot = json.loads(slot_json) if isinstance(slot_json, str) else slot_json
    except Exception:
        return json.dumps({"error": "Invalid slot JSON"})
    result = _propose_interview_dict(candidate_name, slot)
    return json.dumps(result)


AVAILABLE_TOOLS = [tool_parse_resume, tool_score_candidate, tool_check_availability, tool_propose_interview]
TOOL_NAME_MAP = {t.name: t for t in AVAILABLE_TOOLS}

# backward-compat aliases for existing imports
parse_resume = parse_resume_deterministic
score_candidate = score_candidate_deterministic
check_availability_legacy = check_availability
propose_interview_legacy = propose_interview
