"""W6 / Project Module — templates, auto assignment, lifecycle, progress logs, ideas.

Tracker rows covered:
  Template Library     -> GET /projects/templates (seeded from data/project_templates.py)
  Auto Assignment      -> POST /projects/assign  (assigns based on focus chapters)
  Project Lifecycle    -> Discover / Design / Build / Present via /projects/{id}/phase/...
  Progress Logs        -> POST/GET /projects/{id}/logs  (weekly tracking)
  Self-Chosen Projects -> POST /projects/ideas  (5 ideas from chosen domain)
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from data.project_templates import PHASE_LABELS, PHASE_ORDER
from database import get_db
from models.models import (
    MCQResult,
    OpenEndedResult,
    ProgressLog,
    Project,
    ProjectPhase,
    ProjectTemplate,
    User,
    utcnow,
)
from prompts.buddy import PROJECT_IDEAS_PROMPT, PROJECT_IDEAS_SYSTEM_PROMPT
from security import get_current_user, rate_limit
from services.llm_services import llm_services

router = APIRouter(prefix="/projects", tags=["projects"])

MAX_ACTIVE_PROJECTS = 3


# ---------------------------------------------------------------- scoring


def latest_category_percentages(db: Session, user_id: int) -> Dict[str, float]:
    """Combined MCQ + open-ended percentage per category, 0-100.

    MCQ is weighted 0.7 and open-ended 0.3, matching the weighting already used
    by /generate_mentor_insights in app.py so the two never disagree.
    """
    mcq = (
        db.query(MCQResult)
        .filter(MCQResult.user_id == user_id)
        .order_by(MCQResult.created_at.desc().nullslast(), MCQResult.id.desc())
        .first()
    )
    pct: Dict[str, float] = {}
    if mcq and mcq.category_scores:
        try:
            scores = json.loads(mcq.category_scores)
            maxes = json.loads(mcq.max_category_scores or "{}")
            for cat, val in scores.items():
                m = maxes.get(cat) or 0
                if m > 0:
                    pct[cat] = round(100.0 * float(val) / float(m), 1)
        except (ValueError, TypeError):
            pass

    open_row = (
        db.query(OpenEndedResult)
        .filter(OpenEndedResult.user_id == user_id)
        .order_by(OpenEndedResult.created_at.desc().nullslast(), OpenEndedResult.id.desc())
        .first()
    )
    open_pct: Dict[str, List[float]] = {}
    if open_row and open_row.scores:
        try:
            for item in json.loads(open_row.scores):
                cat = item.get("category")
                sc = item.get("score")
                if cat and isinstance(sc, (int, float)):
                    open_pct.setdefault(cat, []).append(float(sc))
        except (ValueError, TypeError):
            pass

    combined: Dict[str, float] = {}
    for cat in set(pct) | set(open_pct):
        m = pct.get(cat)
        o = None
        if cat in open_pct and open_pct[cat]:
            o = sum(open_pct[cat]) / len(open_pct[cat])
        if m is not None and o is not None:
            combined[cat] = round(0.7 * m + 0.3 * o, 1)
        elif m is not None:
            combined[cat] = m
        elif o is not None:
            combined[cat] = round(o, 1)
    return combined


def _difficulty_for(score: float) -> str:
    if score < 45:
        return "starter"
    if score < 70:
        return "core"
    return "stretch"


# ---------------------------------------------------------------- lifecycle


def _create_phases(db: Session, project: Project, phase_briefs: Dict[str, List[str]]) -> None:
    for idx, name in enumerate(PHASE_ORDER):
        db.add(
            ProjectPhase(
                project_id=project.id,
                name=name,
                order_index=idx,
                brief=json.dumps(phase_briefs.get(name, [])),
                status="active" if idx == 0 else "locked",
                started_at=utcnow() if idx == 0 else None,
            )
        )
    db.commit()


def _recompute_progress(db: Session, project: Project) -> None:
    phases = (
        db.query(ProjectPhase)
        .filter(ProjectPhase.project_id == project.id)
        .order_by(ProjectPhase.order_index)
        .all()
    )
    done = [p for p in phases if p.status == "complete"]
    project.completion_pct = int(round(100 * len(done) / max(len(phases), 1)))

    active = next((p for p in phases if p.status in ("active", "submitted")), None)
    if active:
        project.current_phase = active.name
        if project.status == "not_started":
            project.status = "in_progress"
            project.started_at = project.started_at or utcnow()
    elif len(done) == len(phases) and phases:
        project.status = "completed"
        project.current_phase = PHASE_ORDER[-1]
        project.completed_at = project.completed_at or utcnow()
    db.commit()


def _serialise(db: Session, project: Project) -> dict:
    phases = (
        db.query(ProjectPhase)
        .filter(ProjectPhase.project_id == project.id)
        .order_by(ProjectPhase.order_index)
        .all()
    )
    return {
        "id": project.id,
        "title": project.title,
        "summary": project.summary,
        "focus_category": project.focus_category,
        "domain": project.domain,
        "difficulty": project.difficulty,
        "origin": project.origin,
        "assignment_rationale": project.assignment_rationale,
        "status": project.status,
        "current_phase": project.current_phase,
        "completion_pct": project.completion_pct,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "phases": [
            {
                "name": p.name,
                "label": PHASE_LABELS.get(p.name, p.name.title()),
                "order_index": p.order_index,
                "status": p.status,
                "checklist": json.loads(p.brief) if p.brief else [],
                "deliverable_note": p.deliverable_note,
                "deliverable_url": p.deliverable_url,
                "completed_at": p.completed_at.isoformat() if p.completed_at else None,
            }
            for p in phases
        ],
    }


def _owned(db: Session, user: User, project_id: int) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if not p:
        raise HTTPException(status_code=404, detail="project not found")
    return p


# ---------------------------------------------------------------- schemas


class AssignRequest(BaseModel):
    count: int = Field(default=2, ge=1, le=3)
    domain: Optional[str] = None


class PhaseSubmit(BaseModel):
    note: str = Field(min_length=1, max_length=4000)
    url: Optional[str] = None


class LogCreate(BaseModel):
    week_key: Optional[str] = None            # defaults to the current ISO week
    hours_spent: Optional[float] = Field(default=None, ge=0, le=80)
    what_i_did: Optional[str] = Field(default=None, max_length=2000)
    what_blocked_me: Optional[str] = Field(default=None, max_length=2000)
    confidence: Optional[int] = Field(default=None, ge=1, le=5)


class IdeasRequest(BaseModel):
    domain: str
    effort: str = "about 4 hours a week"


class AdoptIdea(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    summary: str = Field(min_length=1, max_length=1000)
    difficulty: str = "core"
    estimated_hours: int = Field(default=12, ge=1, le=200)
    skills_built: List[str] = []
    deliverable: Optional[str] = None
    first_step: Optional[str] = None


# ---------------------------------------------------------------- templates


@router.get("/templates")
def list_templates(
    focus_category: Optional[str] = None,
    domain: Optional[str] = None,
    difficulty: Optional[str] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(ProjectTemplate).filter(ProjectTemplate.is_active.is_(True))
    if focus_category:
        q = q.filter(ProjectTemplate.focus_category == focus_category)
    if difficulty:
        q = q.filter(ProjectTemplate.difficulty == difficulty)
    rows = q.all()
    if domain:
        rows = [r for r in rows if r.domain in (None, domain)]
    return {
        "templates": [
            {
                "id": r.id,
                "slug": r.slug,
                "title": r.title,
                "summary": r.summary,
                "focus_category": r.focus_category,
                "domain": r.domain,
                "difficulty": r.difficulty,
                "estimated_hours": r.estimated_hours,
                "deliverables": json.loads(r.deliverables) if r.deliverables else [],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------- assignment


@router.post("/assign")
def auto_assign(
    payload: AssignRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """W6 Auto Assignment — assign projects based on the student's focus chapters.

    Focus chapters = the lowest-scoring assessment categories. Difficulty is set
    from the score itself so a 20% category gets a starter project and a 75%
    category gets a stretch one.
    """
    active = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.status.in_(["not_started", "in_progress"]))
        .count()
    )
    remaining = MAX_ACTIVE_PROJECTS - active
    if remaining <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"You already have {active} projects on the go. Finish one before taking another.",
        )
    # Clamp to the free slots. Without this, asking for 2 while 2 are already
    # active passes the check above and then creates 2 more — 4 active, over cap.
    wanted = min(payload.count, remaining)

    scores = latest_category_percentages(db, user.id)
    if not scores:
        raise HTTPException(
            status_code=400,
            detail="Complete the assessment first — projects are assigned from your results.",
        )

    focus = sorted(scores.items(), key=lambda kv: kv[1])[:3]

    used_template_ids = {
        p.template_id
        for p in db.query(Project).filter(Project.user_id == user.id).all()
        if p.template_id
    }

    domain = payload.domain or user.professional_domain
    all_templates = db.query(ProjectTemplate).filter(ProjectTemplate.is_active.is_(True)).all()

    def pick(category: str, score: float) -> Optional[ProjectTemplate]:
        want = _difficulty_for(score)
        pool = [t for t in all_templates if t.id not in used_template_ids]

        def rank(t: ProjectTemplate) -> tuple:
            primary = 0 if t.focus_category == category else 1
            secondary = 0
            if primary == 1:
                try:
                    secondary = 0 if category in json.loads(t.secondary_categories or "[]") else 1
                except ValueError:
                    secondary = 1
            dom = 0 if t.domain == domain else (1 if t.domain is None else 2)
            diff = 0 if t.difficulty == want else 1
            return (primary, secondary, dom, diff, t.estimated_hours)

        pool.sort(key=rank)
        # only accept a template that at least touches the category
        for t in pool:
            try:
                sec = json.loads(t.secondary_categories or "[]")
            except ValueError:
                sec = []
            if t.focus_category == category or category in sec:
                return t
        return pool[0] if pool else None

    created = []
    for category, score in focus[:wanted]:
        tpl = pick(category, score)
        if tpl is None:
            break
        used_template_ids.add(tpl.id)

        project = Project(
            user_id=user.id,
            template_id=tpl.id,
            title=tpl.title,
            summary=tpl.summary,
            focus_category=category,
            domain=tpl.domain or domain,
            difficulty=tpl.difficulty,
            origin="auto",
            assignment_rationale=(
                f"{category} is one of your three lowest areas at {score:.0f}%. "
                f"This is a {tpl.difficulty} project (~{tpl.estimated_hours} hrs) that puts "
                f"you in situations where that skill is the thing being tested."
            ),
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        try:
            briefs = json.loads(tpl.phase_briefs)
        except ValueError:
            briefs = {}
        _create_phases(db, project, briefs)
        _recompute_progress(db, project)
        created.append(_serialise(db, project))

    if not created:
        raise HTTPException(
            status_code=409,
            detail="No unused templates left that match your focus areas. Try a self-chosen project.",
        )

    return {"assigned": created, "focus_categories": [c for c, _ in focus]}


@router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Project)
        .filter(Project.user_id == user.id)
        .order_by(Project.created_at.desc().nullslast(), Project.id.desc())
        .all()
    )
    return {"projects": [_serialise(db, p) for p in rows]}


@router.get("/{project_id}")
def get_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _serialise(db, _owned(db, user, project_id))


# ---------------------------------------------------------------- lifecycle


@router.post("/{project_id}/phase/{phase_name}/submit")
def submit_phase(
    project_id: int,
    phase_name: str,
    payload: PhaseSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Complete a phase and unlock the next one.

    Phases are strictly ordered — you can't submit Build before Design is done.
    That ordering is the point of the lifecycle; without it students skip
    straight to building, which is the behaviour this module exists to change.
    """
    if phase_name not in PHASE_ORDER:
        raise HTTPException(status_code=400, detail="unknown phase")

    project = _owned(db, user, project_id)
    phases = (
        db.query(ProjectPhase)
        .filter(ProjectPhase.project_id == project.id)
        .order_by(ProjectPhase.order_index)
        .all()
    )
    phase = next((p for p in phases if p.name == phase_name), None)
    if phase is None:
        raise HTTPException(status_code=404, detail="phase not found")
    if phase.status == "locked":
        prev = PHASE_ORDER[PHASE_ORDER.index(phase_name) - 1]
        raise HTTPException(
            status_code=400,
            detail=f"Finish the {PHASE_LABELS[prev]} phase first.",
        )
    if phase.status == "complete":
        raise HTTPException(status_code=400, detail="This phase is already done.")

    phase.status = "complete"
    phase.deliverable_note = payload.note
    phase.deliverable_url = payload.url
    phase.completed_at = utcnow()

    nxt = next((p for p in phases if p.order_index == phase.order_index + 1), None)
    if nxt and nxt.status == "locked":
        nxt.status = "active"
        nxt.started_at = utcnow()

    db.commit()
    _recompute_progress(db, project)
    return _serialise(db, project)


@router.post("/{project_id}/abandon")
def abandon_project(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    if project.status == "completed":
        raise HTTPException(status_code=400, detail="This project is already finished.")
    project.status = "abandoned"
    db.commit()
    return {"message": "project closed", "id": project.id}


# ---------------------------------------------------------------- progress logs


def current_week_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    year, week, _ = d.isocalendar()
    return f"{year}-W{week:02d}"


@router.post("/{project_id}/logs")
def upsert_log(
    project_id: int,
    payload: LogCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """One log per project per ISO week. Re-posting the same week updates it."""
    project = _owned(db, user, project_id)
    week = payload.week_key or current_week_key()

    row = (
        db.query(ProgressLog)
        .filter(ProgressLog.project_id == project.id, ProgressLog.week_key == week)
        .first()
    )
    if row is None:
        row = ProgressLog(project_id=project.id, user_id=user.id, week_key=week)
        db.add(row)

    row.phase = project.current_phase
    if payload.hours_spent is not None:
        row.hours_spent = payload.hours_spent
    if payload.what_i_did is not None:
        row.what_i_did = payload.what_i_did
    if payload.what_blocked_me is not None:
        row.what_blocked_me = payload.what_blocked_me
    if payload.confidence is not None:
        row.confidence = payload.confidence

    db.commit()
    db.refresh(row)
    return {"message": "progress saved", "week_key": row.week_key, "id": row.id}


@router.get("/{project_id}/logs")
def list_logs(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _owned(db, user, project_id)
    rows = (
        db.query(ProgressLog)
        .filter(ProgressLog.project_id == project.id)
        .order_by(ProgressLog.week_key.asc())
        .all()
    )
    total_hours = sum(r.hours_spent or 0 for r in rows)

    # streak = consecutive ISO weeks logged, counting back from this week
    logged = {r.week_key for r in rows}
    streak = 0
    probe = datetime.now(timezone.utc)
    while current_week_key(probe) in logged:
        streak += 1
        probe -= timedelta(weeks=1)

    return {
        "logs": [
            {
                "week_key": r.week_key,
                "phase": r.phase,
                "hours_spent": r.hours_spent,
                "what_i_did": r.what_i_did,
                "what_blocked_me": r.what_blocked_me,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "total_hours": round(total_hours, 1),
        "weeks_logged": len(rows),
        "current_streak_weeks": streak,
        "current_week_key": current_week_key(),
    }


# ---------------------------------------------------------------- self-chosen


@router.post("/ideas")
def generate_ideas(
    payload: IdeasRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """W6 Self-Chosen Projects — 5 project ideas from the student's chosen domain."""
    rate_limit(f"project-ideas:{user.id}", limit=10, window_seconds=3600)

    scores = latest_category_percentages(db, user.id)
    ranked = sorted(scores.items(), key=lambda kv: kv[1])
    weak = ", ".join(c for c, _ in ranked[:3]) or "not yet assessed"
    strong = ", ".join(c for c, _ in ranked[-2:]) or "not yet assessed"

    prompt = PROJECT_IDEAS_PROMPT.format(
        name=user.fullName or "the student",
        education_level=user.educationLevel or "not specified",
        domain=payload.domain,
        career_goal=user.career_goal or "not specified",
        weak_categories=weak,
        strong_categories=strong,
        effort=payload.effort,
    )

    try:
        data, raw = llm_services.generate(
            prompt=prompt,
            system_message=PROJECT_IDEAS_SYSTEM_PROMPT,
            client=4,
            max_tokens=1800,
        )
        ideas = (data or {}).get("ideas")
        if not isinstance(ideas, list) or not ideas:
            raise ValueError(f"missing 'ideas' key; raw={str(raw)[:200]}")
        return {"ideas": ideas[:5], "focus_categories": [c for c, _ in ranked[:3]]}
    except Exception as e:  # noqa: BLE001
        print(f"[IDEAS] generation failed for user {user.id}: {e}")
        # Fall back to the template library rather than returning nothing —
        # the student still gets five real, buildable options.
        rows = (
            db.query(ProjectTemplate)
            .filter(ProjectTemplate.is_active.is_(True))
            .all()
        )
        rows = [r for r in rows if r.domain in (None, payload.domain)][:5]
        return {
            "ideas": [
                {
                    "title": r.title,
                    "summary": r.summary,
                    "difficulty": r.difficulty,
                    "estimated_hours": r.estimated_hours,
                    "skills_built": [r.focus_category],
                    "deliverable": (json.loads(r.deliverables) or [""])[0] if r.deliverables else "",
                    "first_step": (json.loads(r.phase_briefs).get("discover") or [""])[0],
                }
                for r in rows
            ],
            "focus_categories": [c for c, _ in ranked[:3]],
            "fallback": True,
        }


@router.post("/adopt")
def adopt_idea(
    payload: AdoptIdea,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Turn a generated idea into a real project with the same four-phase lifecycle."""
    active = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.status.in_(["not_started", "in_progress"]))
        .count()
    )
    if active >= MAX_ACTIVE_PROJECTS:
        raise HTTPException(
            status_code=400,
            detail=f"You already have {active} projects on the go. Finish one first.",
        )

    project = Project(
        user_id=user.id,
        template_id=None,
        title=payload.title,
        summary=payload.summary,
        focus_category=(payload.skills_built or [None])[0],
        domain=user.professional_domain,
        difficulty=payload.difficulty,
        origin="self",
        assignment_rationale="You chose this one yourself.",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Generic four-phase scaffold for self-chosen work. Deliberately generic —
    # the student's own idea supplies the specifics.
    generic = {
        "discover": [
            "Write down the problem in one sentence and why it's worth your time",
            "Find two examples of someone solving something similar",
            payload.first_step or "Do the smallest possible version of step one today",
        ],
        "design": [
            "Decide what's in scope and, explicitly, what's out",
            "Sketch the approach before building anything",
            "Write down how you'll know it worked",
        ],
        "build": [
            f"Build toward: {payload.deliverable or 'the deliverable you defined'}",
            "Log progress weekly, including the weeks that go badly",
            "Show it to one person before you think it's ready",
        ],
        "present": [
            "Produce the finished deliverable",
            "Write 300 words on what you'd do differently",
            "Show it to someone whose opinion you'd find uncomfortable",
        ],
    }
    _create_phases(db, project, generic)
    _recompute_progress(db, project)
    return _serialise(db, project)
