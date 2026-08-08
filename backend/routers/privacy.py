"""W6 / Security / Privacy Controls — consent screens and data rights.

Tracker row: "PII masking and consent screens".

Four consent scopes:
  data_processing      required to use the platform at all (assessment storage)
  ai_buddy             required for W5 chat, because chat content is stored
  counsellor_sharing   optional; controls whether the portal sees identity + free text
  research_anonymised  optional; aggregate research use

Each is separately revocable. Revoking `ai_buddy` archives the conversations
rather than silently keeping them — a consent toggle that doesn't change what's
stored isn't a consent toggle.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.models import (
    AssessmentProgress,
    AssessmentReport,
    ChatMessage,
    ChatSession,
    ConsentRecord,
    MCQResult,
    OpenEndedResult,
    User,
    utcnow,
)
from security import get_current_user

router = APIRouter(prefix="/privacy", tags=["privacy"])

POLICY_VERSION = "1.0"

SCOPES: Dict[str, dict] = {
    "data_processing": {
        "label": "Store my assessment results",
        "required": True,
        "description": (
            "We save your answers, scores and report so you can come back to them "
            "and so your progress carries across devices. Without this the "
            "assessment can't work."
        ),
    },
    "ai_buddy": {
        "label": "Use AI Buddy",
        "required": False,
        "description": (
            "Your messages to Buddy are stored so it remembers your context "
            "between sessions. Turn this off and your conversations are archived "
            "and Buddy stops responding."
        ),
    },
    "counsellor_sharing": {
        "label": "Share my results with my counsellor",
        "required": False,
        "description": (
            "Lets a counsellor at your institution see your name, email and your "
            "written answers alongside your scores. With this off they still see "
            "your scores, but your identity and free-text answers stay hidden."
        ),
    },
    "research_anonymised": {
        "label": "Allow anonymised research use",
        "required": False,
        "description": (
            "Your scores may be included in aggregate statistics. Nothing that "
            "identifies you is ever included, and you can withdraw at any time."
        ),
    },
}


class ConsentUpdate(BaseModel):
    scope: str
    granted: bool


class ConsentBatch(BaseModel):
    consents: List[ConsentUpdate] = Field(min_length=1)


def _upsert(db: Session, user: User, scope: str, granted: bool, ip: Optional[str]) -> ConsentRecord:
    rec = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user.id, ConsentRecord.scope == scope)
        .first()
    )
    if rec is None:
        rec = ConsentRecord(user_id=user.id, scope=scope)
        db.add(rec)
    rec.granted = granted
    rec.policy_version = POLICY_VERSION
    if granted:
        rec.granted_at = utcnow()
        rec.revoked_at = None
    else:
        rec.revoked_at = utcnow()
    rec.source_ip = ip
    return rec


@router.get("/scopes")
def list_scopes():
    """Content for the consent screen. No auth — it's public policy text."""
    return {
        "policy_version": POLICY_VERSION,
        "scopes": [{"scope": k, **v} for k, v in SCOPES.items()],
    }


@router.get("/consent")
def my_consent(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = {
        r.scope: r
        for r in db.query(ConsentRecord).filter(ConsentRecord.user_id == user.id).all()
    }
    return {
        "policy_version": POLICY_VERSION,
        "needs_consent": "data_processing" not in rows or not rows["data_processing"].granted,
        "consents": [
            {
                "scope": scope,
                "label": meta["label"],
                "required": meta["required"],
                "description": meta["description"],
                "granted": bool(rows.get(scope) and rows[scope].granted),
                "updated_at": (
                    (rows[scope].granted_at or rows[scope].revoked_at).isoformat()
                    if scope in rows and (rows[scope].granted_at or rows[scope].revoked_at)
                    else None
                ),
            }
            for scope, meta in SCOPES.items()
        ],
    }


@router.post("/consent")
def set_consent(
    payload: ConsentBatch,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else None))

    for item in payload.consents:
        if item.scope not in SCOPES:
            raise HTTPException(status_code=400, detail=f"unknown consent scope: {item.scope}")
        if SCOPES[item.scope]["required"] and not item.granted:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Storing your assessment results is required to use the platform. "
                    "If you want your data removed, use Delete my data instead."
                ),
            )
        _upsert(db, user, item.scope, item.granted, ip)

        # Revoking ai_buddy must actually take effect, not just flip a flag.
        if item.scope == "ai_buddy" and not item.granted:
            db.query(ChatSession).filter(ChatSession.user_id == user.id).update(
                {"is_archived": True}, synchronize_session=False
            )

    db.commit()
    return my_consent(user=user, db=db)


@router.get("/export")
def export_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Right of access — everything we hold, in one JSON payload."""
    import json as _json

    def _load(s):
        try:
            return _json.loads(s) if s else None
        except ValueError:
            return s

    mcq = db.query(MCQResult).filter(MCQResult.user_id == user.id).all()
    oe = db.query(OpenEndedResult).filter(OpenEndedResult.user_id == user.id).all()
    report = db.query(AssessmentReport).filter(AssessmentReport.user_id == user.id).first()
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).all()

    return {
        "profile": {
            "email": user.email,
            "fullName": user.fullName,
            "age": user.age,
            "educationLevel": user.educationLevel,
            "workExperience": user.work_experience,
            "currentRole": user.current_role,
            "professionalDomain": user.professional_domain,
            "careerGoals": user.career_goal,
            "hobbies": user.hobbies,
            "preferredLanguage": user.preferred_language,
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
        "mcq_results": [
            {
                "attempt_no": r.attempt_no,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "answers": _load(r.answers),
                "category_scores": _load(r.category_scores),
                "total_score": r.total_score,
            }
            for r in mcq
        ],
        "open_ended_results": [
            {
                "attempt_no": r.attempt_no,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "answers": _load(r.answers),
                "scores": _load(r.scores),
            }
            for r in oe
        ],
        "assessment_report": _load(report.report_data) if report else None,
        "buddy_conversations": [
            {
                "title": s.title,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "messages": [
                    {"role": m.role, "content": m.content,
                     "created_at": m.created_at.isoformat() if m.created_at else None}
                    for m in db.query(ChatMessage)
                    .filter(ChatMessage.session_id == s.id)
                    .order_by(ChatMessage.id)
                    .all()
                ],
            }
            for s in sessions
        ],
        "consents": [
            {"scope": c.scope, "granted": c.granted, "policy_version": c.policy_version}
            for c in db.query(ConsentRecord).filter(ConsentRecord.user_id == user.id).all()
        ],
    }


class DeleteConfirm(BaseModel):
    confirm_email: str


@router.post("/delete")
def delete_my_data(
    payload: DeleteConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Right to erasure.

    Deletes assessment, chat and progress data and anonymises the account row.
    The row itself is kept (not dropped) because foreign keys from
    counsellor_notes reference it; the identifying fields are cleared and the
    account is deactivated, which is the standard way to satisfy erasure without
    corrupting referential integrity.
    """
    if payload.confirm_email.strip().lower() != (user.email or "").lower():
        raise HTTPException(status_code=400, detail="Type your email exactly to confirm.")

    session_ids = [
        s.id for s in db.query(ChatSession).filter(ChatSession.user_id == user.id).all()
    ]
    if session_ids:
        db.query(ChatMessage).filter(ChatMessage.session_id.in_(session_ids)).delete(
            synchronize_session=False
        )
    db.query(ChatSession).filter(ChatSession.user_id == user.id).delete(synchronize_session=False)
    db.query(MCQResult).filter(MCQResult.user_id == user.id).delete(synchronize_session=False)
    db.query(OpenEndedResult).filter(OpenEndedResult.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(AssessmentReport).filter(AssessmentReport.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(AssessmentProgress).filter(AssessmentProgress.user_id == user.id).delete(
        synchronize_session=False
    )
    db.query(ConsentRecord).filter(ConsentRecord.user_id == user.id).delete(
        synchronize_session=False
    )

    user.email = f"deleted-{user.id}@removed.invalid"
    user.fullName = None
    user.age = None
    user.google_id = None
    user.hashed_password = None
    user.hobbies = None
    user.current_role = None
    user.career_goal = None
    user.professional_domain = None
    user.preferred_language = None
    user.is_active = False
    user.is_verified = False

    db.commit()
    return {"message": "Your data has been deleted and your account closed."}
