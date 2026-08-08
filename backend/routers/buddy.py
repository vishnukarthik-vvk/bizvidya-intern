"""W5 / AI Buddy — chat APIs, context memory, reference generation, guardrails.

Tracker rows covered:
  Conversation APIs     -> POST /buddy/sessions, POST /buddy/chat, GET /buddy/sessions/{id}
  Context Memory        -> services/memory.py, ChatSession.summary
  Reference Generation  -> POST /buddy/references
  Safety Guardrails     -> services/guardrails.py, applied on input and output

Assumes the existing `services.llm_services` interface:
    generate(prompt, system_message, client=..., max_tokens=..., temperature=...) -> (dict, str)
    generate_text(prompt, system_message, temperature=..., max_tokens=...) -> str
If your llm_services exposes a `messages=[...]` parameter, prefer it over the
flattened transcript in `_build_chat_prompt`.
"""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.models import (
    ChatMessage,
    ChatSession,
    ConsentRecord,
    GeneratedReference,
    Project,
    ProjectPhase,
    User,
)
from prompts.buddy import (
    BUDDY_SYSTEM_PROMPT,
    REFERENCE_PROMPT,
    REFERENCE_SYSTEM_PROMPT,
)
from security import client_key, get_current_user, mask_pii, rate_limit
from services import guardrails
from services.llm_services import llm_services
from services.memory import build_profile_block, load_context, maybe_summarise

router = APIRouter(prefix="/buddy", tags=["buddy"])

MAX_SESSIONS_PER_USER = 25


# ---------------------------------------------------------------- schemas


class SessionCreate(BaseModel):
    title: Optional[str] = None
    project_id: Optional[int] = None


class SessionOut(BaseModel):
    id: int
    title: Optional[str]
    project_id: Optional[int]
    message_count: int
    updated_at: Optional[str]


class ChatRequest(BaseModel):
    session_id: Optional[int] = None
    message: str = Field(min_length=1, max_length=4000)
    project_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    guardrail_flag: Optional[str] = None
    created_at: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: int
    reply: str
    guardrail_flag: str
    escalated: bool = False


class ReferenceRequest(BaseModel):
    project_id: int
    phase: Optional[str] = None
    refresh: bool = False


# ---------------------------------------------------------------- helpers


def _consented(db: Session, user: User) -> bool:
    """W6 privacy: Buddy stores conversation content, so it needs its own consent."""
    rec = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user.id, ConsentRecord.scope == "ai_buddy")
        .first()
    )
    return bool(rec and rec.granted)


def _get_session(db: Session, user: User, session_id: int) -> ChatSession:
    s = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="conversation not found")
    return s


def _build_chat_prompt(summary: str, history: List[dict], user_message: str) -> str:
    """Flatten the live window into one prompt string.

    Kept separate so it's a one-line change if llm_services gains native
    multi-turn support.
    """
    parts = []
    if summary:
        parts.append(f"[Earlier in this conversation]\n{summary}\n")
    for m in history:
        speaker = "Student" if m["role"] == "user" else "Buddy"
        parts.append(f"{speaker}: {m['content']}")
    parts.append(f"Student: {user_message}")
    parts.append("Buddy:")
    return "\n\n".join(parts)


def _record(
    db: Session,
    session: ChatSession,
    role: str,
    content: str,
    flag: Optional[str] = None,
    reason: Optional[str] = None,
    needs_review: bool = False,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session.id,
        role=role,
        content=content,
        guardrail_flag=flag,
        guardrail_reason=reason,
        needs_review=needs_review,
    )
    db.add(msg)
    session.message_count = (session.message_count or 0) + 1
    db.commit()
    db.refresh(msg)
    return msg


# ---------------------------------------------------------------- endpoints


@router.post("/sessions", response_model=SessionOut)
def create_session(
    payload: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _consented(db, user):
        raise HTTPException(
            status_code=403,
            detail="Turn on AI Buddy in your privacy settings to start a conversation.",
        )

    open_count = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.is_archived.is_(False))
        .count()
    )
    if open_count >= MAX_SESSIONS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail="You have a lot of open conversations. Archive one to start another.",
        )

    if payload.project_id:
        owns = (
            db.query(Project)
            .filter(Project.id == payload.project_id, Project.user_id == user.id)
            .first()
        )
        if not owns:
            raise HTTPException(status_code=404, detail="project not found")

    s = ChatSession(
        user_id=user.id,
        title=(payload.title or "New conversation")[:120],
        project_id=payload.project_id,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return SessionOut(
        id=s.id,
        title=s.title,
        project_id=s.project_id,
        message_count=0,
        updated_at=s.updated_at.isoformat() if s.updated_at else None,
    )


@router.get("/sessions", response_model=List[SessionOut])
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id, ChatSession.is_archived.is_(False))
        .order_by(ChatSession.updated_at.desc().nullslast(), ChatSession.id.desc())
        .all()
    )
    return [
        SessionOut(
            id=r.id,
            title=r.title,
            project_id=r.project_id,
            message_count=r.message_count or 0,
            updated_at=r.updated_at.isoformat() if r.updated_at else None,
        )
        for r in rows
    ]


@router.get("/sessions/{session_id}/messages", response_model=List[MessageOut])
def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_session(db, user, session_id)
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == s.id, ChatMessage.role != "system")
        .order_by(ChatMessage.id.asc())
        .all()
    )
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            guardrail_flag=m.guardrail_flag,
            created_at=m.created_at.isoformat() if m.created_at else None,
        )
        for m in rows
    ]


@router.delete("/sessions/{session_id}")
def archive_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_session(db, user, session_id)
    s.is_archived = True
    db.commit()
    return {"message": "conversation archived"}


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _consented(db, user):
        raise HTTPException(
            status_code=403,
            detail="Turn on AI Buddy in your privacy settings to use chat.",
        )

    # Each LLM turn costs money; cap it per user rather than per IP so shared
    # campus networks don't lock each other out.
    rate_limit(f"buddy-chat:{user.id}", limit=40, window_seconds=600)
    rate_limit(client_key(request, "buddy-ip"), limit=120, window_seconds=600)

    # ---- session
    if payload.session_id:
        session = _get_session(db, user, payload.session_id)
    else:
        session = ChatSession(
            user_id=user.id,
            title=payload.message[:60],
            project_id=payload.project_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # ---- guardrails: input --------------------------------------------------
    verdict = guardrails.check_input(payload.message)

    # PII is stripped before storage regardless of verdict — we never want a
    # phone number sitting in chat_messages.
    stored_user_text = mask_pii(payload.message)
    _record(
        db,
        session,
        "user",
        stored_user_text,
        flag=verdict.flag if verdict.flag != guardrails.OK else None,
        reason=verdict.reason,
        needs_review=verdict.needs_review,
    )

    if verdict.canned_response:
        msg = _record(
            db,
            session,
            "assistant",
            verdict.canned_response,
            flag=verdict.flag,
            reason=verdict.reason,
            needs_review=verdict.needs_review,
        )
        return ChatResponse(
            session_id=session.id,
            reply=msg.content,
            guardrail_flag=verdict.flag,
            escalated=verdict.needs_review,
        )

    if verdict.flag == guardrails.BLOCKED:
        return ChatResponse(
            session_id=session.id,
            reply=guardrails.REDIRECT_GENERIC,
            guardrail_flag=guardrails.BLOCKED,
        )

    # ---- context ------------------------------------------------------------
    summary, history = load_context(db, session)
    system_prompt = BUDDY_SYSTEM_PROMPT.format(
        profile_block=build_profile_block(db, user),
        memory_summary=summary or "(nothing yet — this is the start of the conversation)",
        language=user.preferred_language or "English",
    )
    prompt = _build_chat_prompt(summary, history[:-1] if history else [], payload.message)

    # ---- model --------------------------------------------------------------
    try:
        reply = llm_services.generate_text(
            prompt=prompt,
            system_message=system_prompt,
            temperature=0.6,
            max_tokens=700,
        )
    except Exception as e:  # noqa: BLE001
        print(f"[BUDDY] generation failed for session {session.id}: {e}")
        reply = (
            "I couldn't reach my brain just then. Give it another go in a moment — "
            "your conversation is saved."
        )
        msg = _record(db, session, "assistant", reply, flag="error", reason=str(e)[:200])
        return ChatResponse(session_id=session.id, reply=reply, guardrail_flag="error")

    # ---- guardrails: output -------------------------------------------------
    out_verdict = guardrails.check_output(reply)
    if out_verdict.canned_response:
        reply = out_verdict.canned_response

    msg = _record(
        db,
        session,
        "assistant",
        reply,
        flag=out_verdict.flag if out_verdict.flag != guardrails.OK else None,
        reason=out_verdict.reason,
        needs_review=out_verdict.needs_review,
    )

    # ---- memory (best effort, never blocks the reply) -----------------------
    try:
        maybe_summarise(db, session, llm_services)
    except Exception as e:  # noqa: BLE001
        print(f"[BUDDY] memory update skipped: {e}")

    return ChatResponse(
        session_id=session.id,
        reply=msg.content,
        guardrail_flag=out_verdict.flag,
        escalated=out_verdict.needs_review,
    )


# ---------------------------------------------------------------- references


_FALLBACK_REFERENCES = [
    {
        "title": "Search your library's database for a primary source on this topic",
        "type": "practice",
        "link": None,
        "how_to_find": "Use your institution's e-resource portal; start with a review paper",
        "effort": "45 min",
        "why": "Grounding the phase in one primary source beats five blog posts.",
    },
    {
        "title": "Find one person who has done this and read their writeup",
        "type": "article",
        "link": None,
        "how_to_find": "Search GitHub, Medium or LinkedIn for the project type plus 'writeup'",
        "effort": "30 min",
        "why": "Seeing someone else's finished version tells you what 'done' looks like.",
    },
]


@router.post("/references")
def generate_references(
    payload: ReferenceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """W5 Reference Generation — project-specific resources, cached per phase."""
    project = (
        db.query(Project)
        .filter(Project.id == payload.project_id, Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    phase = payload.phase or project.current_phase

    cached = (
        db.query(GeneratedReference)
        .filter(
            GeneratedReference.project_id == project.id,
            GeneratedReference.phase == phase,
        )
        .first()
    )
    if cached and not payload.refresh:
        return {"references": json.loads(cached.payload), "cached": True}

    rate_limit(f"buddy-refs:{user.id}", limit=15, window_seconds=3600)

    phase_row = (
        db.query(ProjectPhase)
        .filter(ProjectPhase.project_id == project.id, ProjectPhase.name == phase)
        .first()
    )
    phase_brief = ""
    if phase_row and phase_row.brief:
        try:
            phase_brief = "; ".join(json.loads(phase_row.brief))
        except ValueError:
            phase_brief = phase_row.brief

    prompt = REFERENCE_PROMPT.format(
        education_level=user.educationLevel or "not specified",
        domain=user.professional_domain or project.domain or "general",
        career_goal=user.career_goal or "not specified",
        focus_category=project.focus_category or "general skills",
        project_title=project.title,
        project_summary=project.summary or "",
        phase=phase,
        phase_brief=phase_brief or "not specified",
    )

    references = _FALLBACK_REFERENCES
    try:
        data, raw = llm_services.generate(
            prompt=prompt,
            system_message=REFERENCE_SYSTEM_PROMPT,
            client=2,
            max_tokens=1200,
        )
        got = (data or {}).get("references")
        if isinstance(got, list) and got:
            references = got[:4]
        else:
            print(f"[REFERENCES] unexpected payload, using fallback. raw={str(raw)[:300]}")
    except Exception as e:  # noqa: BLE001
        print(f"[REFERENCES] generation failed for project {project.id}: {e}")

    if cached:
        cached.payload = json.dumps(references)
    else:
        db.add(
            GeneratedReference(
                user_id=user.id,
                project_id=project.id,
                phase=phase,
                payload=json.dumps(references),
            )
        )
    db.commit()

    return {"references": references, "cached": False}
