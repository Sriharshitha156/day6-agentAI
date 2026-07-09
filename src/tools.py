import json
from datetime import datetime, timedelta
from src.schemas import CandidateProfile, ScoreCard, CriterionScore, InterviewSlot, InterviewProposal


def parse_resume(resume_text: str) -> CandidateProfile:
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
        line_stripped = line.strip()

        if line_stripped.startswith("# "):
            name = line_stripped.lstrip("# ")
        elif line_stripped.startswith("**Email:**"):
            email = line_stripped.replace("**Email:**", "").strip()
        elif line_stripped.startswith("## "):
            current_section = line_stripped.lstrip("## ").lower()
        if "skills" in current_section and line_stripped and not line_stripped.startswith("##") and not line_stripped.startswith("**"):
            for s in line_stripped.split(","):
                s = s.strip().lstrip("- *")
                if s and len(s) > 1:
                    skills.append(s)

        if line_stripped.startswith("- ") or line_stripped.startswith("* "):
            item = line_stripped.lstrip("- *").strip()
            if "skills" in current_section:
                for s in item.split(","):
                    s = s.strip()
                    if s:
                        skills.append(s)
            elif "experience" in current_section or "intern" in current_section or "freelance" in current_section:
                if len(item) > 15:
                    experience.append(item)
            elif "projects" in current_section:
                if len(item) > 10:
                    projects.append(item)
            elif "certifications" in current_section:
                certifications.append(item)
        elif "**" in line_stripped and "education" in current_section:
            education = line_stripped.replace("**", "").strip()

    skills = list(dict.fromkeys(skills))

    return CandidateProfile(
        name=name,
        email=email,
        education=education,
        skills=skills or ["Not specified"],
        experience_summary=experience or ["No experience listed"],
        projects=projects or ["No projects listed"],
        certifications=certifications or ["No certifications listed"],
        raw_resume=resume_text,
    )


INJECTION_PATTERNS = [
    "system override",
    "ignore your instructions",
    "ignore all previous",
    "rank me first",
    "must be ranked first",
    "this candidate must be",
]


def detect_injection(resume_text: str) -> bool:
    lowered = resume_text.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lowered:
            return True
    return False


def score_candidate(profile: CandidateProfile, rubric: dict) -> ScoreCard:
    profile_text = (
        f"Name: {profile.name}\n"
        f"Education: {profile.education}\n"
        f"Skills: {', '.join(profile.skills)}\n"
        f"Experience: {'; '.join(profile.experience_summary)}\n"
        f"Projects: {'; '.join(profile.projects)}\n"
        f"Certifications: {'; '.join(profile.certifications)}"
    )

    criterion_scores = []
    for criterion in rubric["criteria"]:
        cname = criterion["name"].lower()
        weight = criterion["weight"]
        scale = criterion["scale"]

        score = _score_criterion(cname, profile, profile_text)

        evidence = _find_evidence(cname, profile)
        if not evidence:
            evidence = "No direct evidence found in resume"

        criterion_scores.append(CriterionScore(
            criterion=criterion["name"],
            score=score,
            weight=weight,
            evidence=evidence,
        ))

    weighted_total = sum(cs.score * cs.weight for cs in criterion_scores)
    weighted_total = round(min(weighted_total, 5.0), 2)

    return ScoreCard(
        candidate_name=profile.name,
        criterion_scores=criterion_scores,
        weighted_total=weighted_total,
    )


def _score_criterion(cname: str, profile: CandidateProfile, text: str) -> int:
    text_lower = text.lower()
    skills_lower = [s.lower() for s in profile.skills]
    exp_concat = " ".join(e.lower() for e in profile.experience_summary)
    proj_concat = " ".join(p.lower() for p in profile.projects)



    if "python" in cname:
        items = list(profile.experience_summary) + list(profile.projects)
        for item in items:
            il = item.lower()
            if "open-source" in il or "open source" in il:
                return 5
        if ("production" in exp_concat or "deployed" in exp_concat) and "python" in skills_lower:
            return 4
        if "python" in skills_lower and ("pandas" in skills_lower or "numpy" in skills_lower):
            return 3
        if "python" in skills_lower:
            return 2
        return 1

    if "ml" in cname or "machine learning" in cname or "fundamental" in cname:
        if "published" in text_lower or "paper" in text_lower:
            return 5
        if "production" in exp_concat and ("model" in exp_concat or " ml " in exp_concat or exp_concat.startswith("ml ") or exp_concat.endswith(" ml")):
            return 4
        if "model" in proj_concat or ("scikit-learn" in skills_lower and "project" in proj_concat):
            return 3
        if "machine learning" in skills_lower or " ml" in (" " + " ".join(skills_lower) + " "):
            return 2
        return 1

    if "tool" in cname or "framework" in cname:
        score = 1
        if "pandas" in skills_lower:
            score += 1
        if "numpy" in skills_lower:
            score += 1
        if "scikit-learn" in skills_lower:
            score += 1
        if "pytorch" in skills_lower or "tensorflow" in skills_lower:
            score += 1
        if "sql" in skills_lower:
            score += 1
        return min(score, 5)

    if "data" in cname or "etl" in cname or "pipe" in cname:
        if "pipeline" in exp_concat or "etl" in exp_concat:
            return 4
        if "sql" in skills_lower and ("pipeline" in text_lower or "processing" in text_lower):
            return 3
        if "sql" in skills_lower:
            return 2
        if any("data" in s.lower() for s in profile.skills):
            return 1
        return 0

    if "project" in cname or "relevant" in cname:
        ml_keywords = ["ml", "machine learning", "deep learning", "nlp", "fraud", "recommendation", "forecast", "lstm", "transformer", "sentiment"]
        match_count = sum(1 for kw in ml_keywords if kw in proj_concat or kw in exp_concat)
        if match_count >= 4:
            return 5
        if match_count >= 3:
            return 4
        if match_count >= 2:
            return 3
        if match_count >= 1:
            return 2
        return 1

    if "communication" in cname or "collaboration" in cname:
        if "mentor" in exp_concat or "lead" in exp_concat:
            return 4
        if "present" in exp_concat or "presented" in exp_concat:
            return 3
        if "collaborat" in exp_concat or "team" in exp_concat:
            return 2
        return 1

    return 2


def _find_evidence(cname: str, profile: CandidateProfile) -> str:
    cname_lower = cname.lower()

    if "python" in cname_lower:
        for e in profile.experience_summary:
            if "python" in e.lower():
                return f"Experience, line: {e[:100]}"
        if "python" in [s.lower() for s in profile.skills]:
            return f"Skills section lists Python"
        return ""

    if "ml" in cname_lower or "fundamental" in cname_lower:
        for e in profile.experience_summary:
            el = e.lower()
            if "model" in el or " ml " in el or el.startswith("ml ") or el.endswith(" ml"):
                return f"Experience, line: {e[:100]}"
        for p in profile.projects:
            pl = p.lower()
            if "model" in pl or " ml " in pl or pl.startswith("ml ") or pl.endswith(" ml"):
                return f"Projects, line: {p[:100]}"
        return ""

    if "tool" in cname_lower or "framework" in cname_lower:
        tools_found = [s for s in profile.skills if s.lower() in ["scikit-learn", "pandas", "numpy", "pytorch", "tensorflow", "sql"]]
        if tools_found:
            return f"Skills section: {', '.join(tools_found[:4])}"
        return ""

    if "data" in cname_lower:
        for e in profile.experience_summary:
            if "pipeline" in e.lower() or "etl" in e.lower() or "sql" in e.lower():
                return f"Experience, line: {e[:100]}"
        return ""

    if "project" in cname_lower or "relevant" in cname_lower:
        for p in profile.projects:
            ml_kws = ["ml", "machine learning", "nlp", "fraud", "recommendation", "forecast"]
            if any(kw in p.lower() for kw in ml_kws):
                return f"Projects, line: {p[:100]}"
        for e in profile.experience_summary:
            ml_kws = ["ml", "machine learning", "fraud", "model", "forecast"]
            if any(kw in e.lower() for kw in ml_kws):
                return f"Experience, line: {e[:100]}"
        return ""

    if "communication" in cname_lower or "collaboration" in cname_lower:
        for e in profile.experience_summary:
            if "present" in e.lower() or "mentor" in e.lower() or "collaborat" in e.lower():
                return f"Experience, line: {e[:100]}"
        return ""

    return ""


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
