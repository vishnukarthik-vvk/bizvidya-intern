"""W5 / AI Buddy / Context Memory — store conversation summaries.

Strategy: a live window plus a rolling summary.

  - the last LIVE_WINDOW messages are sent to the model verbatim
  - everything older is folded into ChatSession.summary, one batch at a time
  - the summary is regenerated (not appended) so it can't grow unbounded

This keeps token cost flat no matter how long the conversation runs, which
matters because Buddy sessions are meant to span the whole 90-day roadmap.
"""

import json
from typing import List, Tuple

from sqlalchemy.orm import Session

from models.models import ChatMessage, ChatSession, MCQResult, Project, User
from prompts.buddy import MEMORY_SUMMARY_PROMPT, MEMORY_SUMMARY_SYSTEM_PROMPT

LIVE_WINDOW = 12          # raw messages kept verbatim
SUMMARISE_TRIGGER = 20    # summarise once unsummarised count exceeds this


def build_profile_block(db: Session, user: User) -> str:
    """Static facts about the student, prepended to every Buddy turn."""
    latest = (
        db.query(MCQResult)
        .filter(MCQResult.user_id == user.id)
        .order_by(MCQResult.created_at.desc().nullslast(), MCQResult.id.desc())
        .first()
    )

    lines = [
        f"Name: {user.fullName or 'the student'}",
        f"Education: {user.educationLevel or 'not given'}",
        f"Domain: {user.professional_domain or 'not given'}",
        f"Career goal: {user.career_goal or 'not given'}",
        f"Experience: {user.work_experience or 'not given'}",
    ]

    if latest and latest.category_scores:
        try:
            scores = json.loads(latest.category_scores)
            maxes = json.loads(latest.max_category_scores or "{}")
            pct = {
                k: round(100 * v / maxes[k], 1)
                for k, v in scores.items()
                if maxes.get(k)
            }
            if pct:
                weakest = sorted(pct.items(), key=lambda kv: kv[1])[:3]
                strongest = sorted(pct.items(), key=lambda kv: -kv[1])[:2]
                lines.append(
                    "Weakest areas: "
                    + ", ".join(f"{k} ({v}%)" for k, v in weakest)
                )
                lines.append(
                    "Strongest areas: "
                    + ", ".join(f"{k} ({v}%)" for k, v in strongest)
                )
        except (ValueError, TypeError, ZeroDivisionError):
            pass

    active = (
        db.query(Project)
        .filter(Project.user_id == user.id, Project.status == "in_progress")
        .all()
    )
    if active:
        lines.append(
            "Active projects: "
            + "; ".join(f"{p.title} (phase: {p.current_phase}, {p.completion_pct}%)" for p in active)
        )

    return "\n".join(lines)


def load_context(db: Session, session: ChatSession) -> Tuple[str, List[dict]]:
    """Return (summary_of_older_turns, live_messages_as_openai_style_dicts)."""
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    live = msgs[-LIVE_WINDOW:] if len(msgs) > LIVE_WINDOW else msgs
    history = [{"role": m.role, "content": m.content} for m in live if m.role in ("user", "assistant")]
    return (session.summary or ""), history


def maybe_summarise(db: Session, session: ChatSession, llm_services) -> None:
    """Fold older turns into the rolling summary once the backlog is big enough.

    Called after each assistant reply. Failure here is non-fatal — the worst case
    is that we summarise on the next turn instead.
    """
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.asc())
        .all()
    )
    if len(msgs) <= SUMMARISE_TRIGGER:
        return

    # everything except the live window is fair game
    to_fold = msgs[: len(msgs) - LIVE_WINDOW]
    if len(to_fold) <= session.summarised_upto:
        return

    new_batch = to_fold[session.summarised_upto:]
    if not new_batch:
        return

    transcript = "\n".join(
        f"{'Student' if m.role == 'user' else 'Buddy'}: {m.content}" for m in new_batch
    )

    prompt = MEMORY_SUMMARY_PROMPT.format(
        existing_summary=session.summary or "(nothing yet — this is the first summary)",
        new_transcript=transcript[:8000],
    )

    try:
        data, _raw = llm_services.generate(
            prompt=prompt,
            system_message=MEMORY_SUMMARY_SYSTEM_PROMPT,
            client=2,
            max_tokens=600,
        )
        summary = (data or {}).get("summary", "").strip()
        if summary:
            session.summary = summary
            session.summarised_upto = len(to_fold)
            db.commit()
    except Exception as e:  # noqa: BLE001 — memory is best-effort
        print(f"[MEMORY] summarisation skipped for session {session.id}: {e}")
        db.rollback()
