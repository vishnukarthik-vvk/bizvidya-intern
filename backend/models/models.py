"""SQLAlchemy models — full replacement for models/models.py.

Existing tables keep their names and columns so nothing already in the database
breaks. New columns are all nullable or have defaults; see migration.sql.

New in this file:
  W2 (still open)  version + created_at on results, so retakes are ordered history
  W5  ChatSession, ChatMessage, GeneratedReference
  W6  ProjectTemplate, Project, ProjectPhase, ProgressLog, CounsellorNote, ConsentRecord
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def utcnow():
    """`datetime.utcnow` is deprecated from Python 3.12 — use an aware helper."""
    return datetime.now(timezone.utc)


# ============================================================ existing tables


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    auth_provider = Column(String, default="local")
    google_id = Column(String, unique=True, nullable=True, index=True)
    is_verified = Column(Boolean, default=False)
    fullName = Column(String)
    age = Column(Integer, nullable=True)
    educationLevel = Column(String, nullable=True)
    work_experience = Column(String, nullable=True)
    current_role = Column(String, nullable=True)
    professional_domain = Column(String, nullable=True)
    career_goal = Column(String, nullable=True)
    hobbies = Column(String, nullable=True)
    preferred_language = Column(String, nullable=True)

    # --- W6 security -------------------------------------------------------
    # "student" | "counsellor" | "admin". Defaults to student so every existing
    # row stays a student after the migration.
    role = Column(String, nullable=False, default="student", server_default="student")
    # counsellors are scoped to an institution so one counsellor can't list every
    # student in the database
    institution = Column(String, nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=utcnow)
    last_login_at = Column(DateTime, nullable=True)


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    # --- B8: single-use codes with an attempt cap --------------------------
    used = Column(Boolean, nullable=False, default=False, server_default="false")
    attempts = Column(Integer, nullable=False, default=0, server_default="0")


class MCQResult(Base):
    __tablename__ = "mcq_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    answers = Column(Text)
    total_score = Column(Float)
    max_possible_score = Column(Float)
    category_scores = Column(Text)
    max_category_scores = Column(Text)
    # --- W2 versioning (B22) ----------------------------------------------
    attempt_no = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=utcnow, index=True)


class OpenEndedResult(Base):
    __tablename__ = "open_ended_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    answers = Column(Text)
    scores = Column(Text)
    attempt_no = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=utcnow, index=True)


class AssessmentReport(Base):
    __tablename__ = "assessment_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    report_data = Column(Text)
    # denormalised so the counsellor list view doesn't have to parse the blob
    overall_score = Column(Float, nullable=True)
    weakest_categories = Column(Text, nullable=True)  # JSON list of 3 strings
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class AssessmentProgress(Base):
    __tablename__ = "assessment_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stage = Column(String, nullable=False)
    progress_data = Column(Text)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("user_id", "stage", name="uq_user_stage_progress"),)


# ============================================================ W5 — AI Buddy


class ChatSession(Base):
    """One Buddy conversation. Long-term memory lives in `summary`."""

    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=True)
    # optional link to the project being discussed, so Buddy has project context
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    # rolling summary of everything older than the live window (W5 Context Memory)
    summary = Column(Text, nullable=True)
    # how many messages have already been folded into `summary`
    summarised_upto = Column(Integer, nullable=False, default=0, server_default="0")
    message_count = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    is_archived = Column(Boolean, nullable=False, default=False, server_default="false")

    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.id",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String, nullable=False)          # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    # guardrail verdict for this turn: "ok" | "redirected" | "blocked" | "crisis"
    guardrail_flag = Column(String, nullable=True)
    guardrail_reason = Column(String, nullable=True)
    # true when a counsellor should look at this turn (crisis / repeated distress)
    needs_review = Column(Boolean, nullable=False, default=False, server_default="false")
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (Index("ix_chat_messages_review", "needs_review", "created_at"),)


class GeneratedReference(Base):
    """W5 Reference Generation — resources produced for a specific project.

    Cached per (project, phase) so we don't re-bill the LLM every page load.
    """

    __tablename__ = "generated_references"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    phase = Column(String, nullable=True)          # discover | design | build | present
    payload = Column(Text, nullable=False)          # JSON list of resource objects
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("project_id", "phase", name="uq_reference_project_phase"),
    )


# ============================================================ W6 — Projects


class ProjectTemplate(Base):
    """W6 Template Library. Seeded from data/project_templates.py."""

    __tablename__ = "project_templates"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    # skill category this template strengthens — matches the assessment categories
    focus_category = Column(String, nullable=False, index=True)
    secondary_categories = Column(Text, nullable=True)   # JSON list
    domain = Column(String, nullable=True, index=True)   # dataScience | marketing | ...
    difficulty = Column(String, nullable=False)          # starter | core | stretch
    estimated_hours = Column(Integer, nullable=False, default=10)
    # JSON: {"discover": [...], "design": [...], "build": [...], "present": [...]}
    phase_briefs = Column(Text, nullable=False)
    deliverables = Column(Text, nullable=True)           # JSON list
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(Integer, ForeignKey("project_templates.id"), nullable=True)

    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    focus_category = Column(String, nullable=True, index=True)
    domain = Column(String, nullable=True)
    difficulty = Column(String, nullable=True)

    # "auto" (assigned from focus chapters) | "self" (student's own idea)
    origin = Column(String, nullable=False, default="auto", server_default="auto")
    # why this project was assigned — shown to the student and the counsellor
    assignment_rationale = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="not_started", server_default="not_started")
    # not_started | in_progress | completed | abandoned
    current_phase = Column(String, nullable=False, default="discover", server_default="discover")
    completion_pct = Column(Integer, nullable=False, default=0, server_default="0")

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    phases = relationship(
        "ProjectPhase",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectPhase.order_index",
    )
    logs = relationship(
        "ProgressLog",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProgressLog.id",
    )


class ProjectPhase(Base):
    """W6 Project Lifecycle — Discover, Design, Build, Present."""

    __tablename__ = "project_phases"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String, nullable=False)                # discover | design | build | present
    order_index = Column(Integer, nullable=False)
    brief = Column(Text, nullable=True)                  # JSON list of checklist items
    status = Column(String, nullable=False, default="locked", server_default="locked")
    # locked | active | submitted | complete
    deliverable_note = Column(Text, nullable=True)       # what the student submitted
    deliverable_url = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="phases")

    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_phase_name"),
    )


class ProgressLog(Base):
    """W6 Progress Logs — weekly tracking entries."""

    __tablename__ = "progress_logs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # ISO week key, e.g. "2026-W32" — one log per project per week
    week_key = Column(String, nullable=False, index=True)
    phase = Column(String, nullable=True)
    hours_spent = Column(Float, nullable=True)
    what_i_did = Column(Text, nullable=True)
    what_blocked_me = Column(Text, nullable=True)
    confidence = Column(Integer, nullable=True)          # 1-5 self rating
    created_at = Column(DateTime, default=utcnow)

    project = relationship("Project", back_populates="logs")

    __table_args__ = (
        UniqueConstraint("project_id", "week_key", name="uq_progress_log_week"),
    )


# ============================================================ W6 — Counsellor


class CounsellorNote(Base):
    __tablename__ = "counsellor_notes"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    counsellor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    # "private" = counsellor only, "shared" = visible to the student
    visibility = Column(String, nullable=False, default="private", server_default="private")
    tag = Column(String, nullable=True)                  # followup | concern | win | plan
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# ============================================================ W6 — Privacy


class ConsentRecord(Base):
    """W6 Privacy Controls — explicit, versioned, revocable consent."""

    __tablename__ = "consent_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # data_processing | counsellor_sharing | ai_buddy | research_anonymised
    scope = Column(String, nullable=False)
    granted = Column(Boolean, nullable=False, default=False)
    policy_version = Column(String, nullable=False, default="1.0")
    granted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    # kept for audit — proves *when* and *from where* consent was captured
    source_ip = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "scope", name="uq_consent_user_scope"),
    )
