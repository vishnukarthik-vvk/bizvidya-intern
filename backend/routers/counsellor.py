"""W6 / Counsellor Portal — student report view and counsellor notes.

Tracker rows covered:
  Dashboard -> GET /counsellor/students, GET /counsellor/students/{id}
  Notes     -> POST/GET/PATCH/DELETE /counsellor/students/{id}/notes

Access rules, in order of precedence:
  1. Caller must hold the counsellor or admin role.
  2. Counsellors only see students in their own institution. Admins see all.
  3. A student's identified data is only shown if they granted the
     `counsellor_sharing` consent. Without it the counsellor still sees the
     scores (which is the clinically useful part) but the identity is masked
     and free text is PII-scrubbed.

Rule 3 is the one that's easy to skip and the one that matters — a portal that
shows every student's open-ended answers by default is a privacy incident
waiting to happen.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.models import (
    AssessmentReport,
    ChatMessage,
    ChatSession,
    ConsentRecord,
    CounsellorNote,
    MCQResult,
    Project,
    ProgressLog,
    User,
)
from security import (
    ROLE_ADMIN,
    ROLE_COUNSELLOR,
    ROLE_STUDENT,
    get_current_user,
    mask_name,
    mask_pii,
    require_role,
)

router = APIRouter(prefix="/counsellor", tags=["counsellor"])

staff_only = require_role(ROLE_COUNSELLOR, ROLE_ADMIN)


# ---------------------------------------------------------------- helpers


def _has_sharing_consent(db: Session, student_id: int) -> bool:
    rec = (
        db.query(ConsentRecord)
        .filter(
            ConsentRecord.user_id == student_id,
            ConsentRecord.scope == "counsellor_sharing",
        )
        .first()
    )
    return bool(rec and rec.granted)


def _accessible_student(db: Session, staff: User, student_id: int) -> User:
    student = (
        db.query(User)
        .filter(User.id == student_id, User.role == ROLE_STUDENT)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="student not found")
    if staff.role != ROLE_ADMIN and student.institution != staff.institution:
        # 404 rather than 403 — don't confirm the student exists to someone
        # outside their institution.
        raise HTTPException(status_code=404, detail="student not found")
    return student


def _category_percentages(mcq: Optional[MCQResult]) -> dict:
    if not mcq or not mcq.category_scores:
        return {}
    try:
        scores = json.loads(mcq.category_scores)
        maxes = json.loads(mcq.max_category_scores or "{}")
        return {
            k: round(100.0 * float(v) / float(maxes[k]), 1)
            for k, v in scores.items()
            if maxes.get(k)
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {}


# ---------------------------------------------------------------- schemas


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    visibility: str = Field(default="private", pattern="^(private|shared)$")
    tag: Optional[str] = Field(default=None, max_length=40)


class NoteUpdate(BaseModel):
    body: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    visibility: Optional[str] = Field(default=None, pattern="^(private|shared)$")
    tag: Optional[str] = Field(default=None, max_length=40)


# ---------------------------------------------------------------- dashboard


@router.get("/students")
def list_students(
    q: Optional[str] = None,
    needs_attention: bool = False,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    """Roster view. Returns enough to triage, not enough to browse for fun."""
    query = db.query(User).filter(User.role == ROLE_STUDENT, User.is_active.is_(True))
    if staff.role != ROLE_ADMIN:
        if not staff.institution:
            raise HTTPException(
                status_code=400,
                detail="Your account isn't linked to an institution yet — ask an admin to set it.",
            )
        query = query.filter(User.institution == staff.institution)

    students = query.order_by(User.id.desc()).limit(500).all()

    out = []
    for s in students:
        consented = _has_sharing_consent(db, s.id)
        report = (
            db.query(AssessmentReport).filter(AssessmentReport.user_id == s.id).first()
        )
        mcq = (
            db.query(MCQResult)
            .filter(MCQResult.user_id == s.id)
            .order_by(MCQResult.created_at.desc().nullslast(), MCQResult.id.desc())
            .first()
        )
        pct = _category_percentages(mcq)
        overall = round(sum(pct.values()) / len(pct), 1) if pct else None
        weakest = sorted(pct.items(), key=lambda kv: kv[1])[:3]

        active_projects = (
            db.query(Project)
            .filter(Project.user_id == s.id, Project.status == "in_progress")
            .count()
        )
        flagged = (
            db.query(ChatMessage)
            .join(ChatSession, ChatMessage.session_id == ChatSession.id)
            .filter(
                ChatSession.user_id == s.id,
                ChatMessage.needs_review.is_(True),
                ChatMessage.reviewed_at.is_(None),
            )
            .count()
        )

        row = {
            "student_id": s.id,
            "display_name": s.fullName if consented else mask_name(s.fullName),
            "email": s.email if consented else None,
            "identified": consented,
            "education_level": s.educationLevel,
            "domain": s.professional_domain,
            "career_goal": s.career_goal,
            "assessment_complete": report is not None,
            "overall_score": overall,
            "weakest_categories": [{"category": c, "score": v} for c, v in weakest],
            "active_projects": active_projects,
            "flagged_messages": flagged,
        }
        if needs_attention and not (flagged or (overall is not None and overall < 45)):
            continue
        out.append(row)

    # Surface the students who need a human first.
    out.sort(key=lambda r: (-r["flagged_messages"], r["overall_score"] if r["overall_score"] is not None else 999))
    return {"students": out, "count": len(out)}


@router.get("/students/{student_id}")
def student_detail(
    student_id: int,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    student = _accessible_student(db, staff, student_id)
    consented = _has_sharing_consent(db, student.id)

    mcq = (
        db.query(MCQResult)
        .filter(MCQResult.user_id == student.id)
        .order_by(MCQResult.created_at.desc().nullslast(), MCQResult.id.desc())
        .first()
    )
    pct = _category_percentages(mcq)
    report = db.query(AssessmentReport).filter(AssessmentReport.user_id == student.id).first()

    # The narrative sections of the report are the student's own words filtered
    # through an LLM. Only show them with consent, and scrub PII either way.
    narrative = {}
    if report and report.report_data:
        try:
            blob = json.loads(report.report_data)
            if consented:
                narrative = {
                    "assessment_summary": mask_pii(
                        (blob.get("assessmentSummary") or {}).get("assessment_summary")
                        if isinstance(blob.get("assessmentSummary"), dict)
                        else blob.get("assessmentSummary")
                    ),
                    "reflection_summary": mask_pii(
                        (blob.get("reflectionSummary") or {}).get("reflection_summary")
                        if isinstance(blob.get("reflectionSummary"), dict)
                        else blob.get("reflectionSummary")
                    ),
                    "career_recommendations": blob.get("careerRecommendations"),
                }
        except ValueError:
            pass

    projects = (
        db.query(Project)
        .filter(Project.user_id == student.id)
        .order_by(Project.id.desc())
        .all()
    )
    project_rows = []
    for p in projects:
        logs = (
            db.query(ProgressLog)
            .filter(ProgressLog.project_id == p.id)
            .order_by(ProgressLog.week_key.desc())
            .limit(4)
            .all()
        )
        project_rows.append(
            {
                "id": p.id,
                "title": p.title,
                "focus_category": p.focus_category,
                "origin": p.origin,
                "status": p.status,
                "current_phase": p.current_phase,
                "completion_pct": p.completion_pct,
                "recent_logs": [
                    {
                        "week_key": l.week_key,
                        "hours_spent": l.hours_spent,
                        "confidence": l.confidence,
                        "what_blocked_me": mask_pii(l.what_blocked_me) if consented else None,
                    }
                    for l in logs
                ],
            }
        )

    flagged = (
        db.query(ChatMessage)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == student.id, ChatMessage.needs_review.is_(True))
        .order_by(ChatMessage.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "student": {
            "student_id": student.id,
            "display_name": student.fullName if consented else mask_name(student.fullName),
            "email": student.email if consented else None,
            "identified": consented,
            "age": student.age if consented else None,
            "education_level": student.educationLevel,
            "domain": student.professional_domain,
            "career_goal": student.career_goal,
        },
        "consent": {
            "counsellor_sharing": consented,
            "note": None
            if consented
            else "This student hasn't consented to identified sharing. "
            "Scores are shown; identity and free-text answers are withheld.",
        },
        "scores": [{"category": k, "score": v} for k, v in sorted(pct.items(), key=lambda kv: kv[1])],
        "overall_score": round(sum(pct.values()) / len(pct), 1) if pct else None,
        "narrative": narrative,
        "projects": project_rows,
        "flagged_messages": [
            {
                "id": m.id,
                "role": m.role,
                # never surface the raw text of a flagged turn in a list view;
                # the reason is what the counsellor needs to decide to reach out
                "reason": m.guardrail_reason,
                "flag": m.guardrail_flag,
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "reviewed": m.reviewed_at is not None,
            }
            for m in flagged
        ],
    }


@router.post("/messages/{message_id}/reviewed")
def mark_reviewed(
    message_id: int,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    from models.models import utcnow

    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="message not found")
    session = db.query(ChatSession).filter(ChatSession.id == msg.session_id).first()
    _accessible_student(db, staff, session.user_id)
    msg.reviewed_at = utcnow()
    db.commit()
    return {"message": "marked as reviewed"}


# ---------------------------------------------------------------- notes


@router.post("/students/{student_id}/notes")
def create_note(
    student_id: int,
    payload: NoteCreate,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    _accessible_student(db, staff, student_id)
    note = CounsellorNote(
        student_id=student_id,
        counsellor_id=staff.id,
        body=payload.body,
        visibility=payload.visibility,
        tag=payload.tag,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "message": "note saved"}


@router.get("/students/{student_id}/notes")
def list_notes(
    student_id: int,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    _accessible_student(db, staff, student_id)
    rows = (
        db.query(CounsellorNote)
        .filter(CounsellorNote.student_id == student_id)
        .order_by(CounsellorNote.created_at.desc())
        .all()
    )
    authors = {
        u.id: u.fullName or u.email
        for u in db.query(User).filter(User.id.in_([r.counsellor_id for r in rows] or [0])).all()
    }
    return {
        "notes": [
            {
                "id": r.id,
                "body": r.body,
                "visibility": r.visibility,
                "tag": r.tag,
                "author": authors.get(r.counsellor_id, "Counsellor"),
                "is_mine": r.counsellor_id == staff.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.patch("/notes/{note_id}")
def update_note(
    note_id: int,
    payload: NoteUpdate,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    note = db.query(CounsellorNote).filter(CounsellorNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="note not found")
    if note.counsellor_id != staff.id and staff.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="you can only edit your own notes")
    if payload.body is not None:
        note.body = payload.body
    if payload.visibility is not None:
        note.visibility = payload.visibility
    if payload.tag is not None:
        note.tag = payload.tag
    db.commit()
    return {"message": "note updated"}


@router.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    staff: User = Depends(staff_only),
    db: Session = Depends(get_db),
):
    note = db.query(CounsellorNote).filter(CounsellorNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="note not found")
    if note.counsellor_id != staff.id and staff.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="you can only delete your own notes")
    db.delete(note)
    db.commit()
    return {"message": "note deleted"}


# ---------------------------------------------------------------- student side


@router.get("/my-notes")
def my_shared_notes(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Students see only the notes a counsellor chose to share with them."""
    rows = (
        db.query(CounsellorNote)
        .filter(
            CounsellorNote.student_id == user.id,
            CounsellorNote.visibility == "shared",
        )
        .order_by(CounsellorNote.created_at.desc())
        .all()
    )
    return {
        "notes": [
            {
                "id": r.id,
                "body": r.body,
                "tag": r.tag,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }
