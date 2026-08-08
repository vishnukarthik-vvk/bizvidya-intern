-- Migration for W5 + W6. PostgreSQL. Idempotent — safe to re-run.
--
-- `Base.metadata.create_all()` in app.py creates NEW tables automatically but
-- never ADDS COLUMNS to existing ones. The ALTERs below are the part
-- create_all() will silently skip, so run this before deploying.
--
--   psql "$DATABASE_URL" -f migration.sql

BEGIN;

-- ============================================================ existing tables

ALTER TABLE users ADD COLUMN IF NOT EXISTS role          VARCHAR NOT NULL DEFAULT 'student';
ALTER TABLE users ADD COLUMN IF NOT EXISTS institution   VARCHAR;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active     BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at    TIMESTAMP DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS ix_users_institution ON users (institution);

ALTER TABLE email_otps ADD COLUMN IF NOT EXISTS used     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE email_otps ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0;
-- every code issued before this migration is now dead; users just request a new one
UPDATE email_otps SET used = TRUE WHERE used = FALSE;

ALTER TABLE mcq_results        ADD COLUMN IF NOT EXISTS attempt_no INTEGER NOT NULL DEFAULT 1;
ALTER TABLE mcq_results        ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
ALTER TABLE open_ended_results ADD COLUMN IF NOT EXISTS attempt_no INTEGER NOT NULL DEFAULT 1;
ALTER TABLE open_ended_results ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
CREATE INDEX IF NOT EXISTS ix_mcq_results_user_created  ON mcq_results (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_open_results_user_created ON open_ended_results (user_id, created_at DESC);

ALTER TABLE assessment_reports ADD COLUMN IF NOT EXISTS overall_score       DOUBLE PRECISION;
ALTER TABLE assessment_reports ADD COLUMN IF NOT EXISTS weakest_categories  TEXT;
ALTER TABLE assessment_reports ADD COLUMN IF NOT EXISTS created_at          TIMESTAMP DEFAULT NOW();
ALTER TABLE assessment_reports ADD COLUMN IF NOT EXISTS updated_at          TIMESTAMP DEFAULT NOW();

ALTER TABLE assessment_progress ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Backfill attempt_no so existing rows form real history rather than all being "1".
WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) AS rn FROM mcq_results
)
UPDATE mcq_results m SET attempt_no = r.rn FROM ranked r WHERE m.id = r.id;

WITH ranked AS (
  SELECT id, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY id) AS rn FROM open_ended_results
)
UPDATE open_ended_results o SET attempt_no = r.rn FROM ranked r WHERE o.id = r.id;

-- ============================================================ W6 templates

CREATE TABLE IF NOT EXISTS project_templates (
    id                    SERIAL PRIMARY KEY,
    slug                  VARCHAR UNIQUE NOT NULL,
    title                 VARCHAR NOT NULL,
    summary               TEXT NOT NULL,
    focus_category        VARCHAR NOT NULL,
    secondary_categories  TEXT,
    domain                VARCHAR,
    difficulty            VARCHAR NOT NULL,
    estimated_hours       INTEGER NOT NULL DEFAULT 10,
    phase_briefs          TEXT NOT NULL,
    deliverables          TEXT,
    is_active             BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_templates_focus  ON project_templates (focus_category);
CREATE INDEX IF NOT EXISTS ix_templates_domain ON project_templates (domain);

-- ============================================================ W6 projects

CREATE TABLE IF NOT EXISTS projects (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL REFERENCES users (id),
    template_id           INTEGER REFERENCES project_templates (id),
    title                 VARCHAR NOT NULL,
    summary               TEXT,
    focus_category        VARCHAR,
    domain                VARCHAR,
    difficulty            VARCHAR,
    origin                VARCHAR NOT NULL DEFAULT 'auto',
    assignment_rationale  TEXT,
    status                VARCHAR NOT NULL DEFAULT 'not_started',
    current_phase         VARCHAR NOT NULL DEFAULT 'discover',
    completion_pct        INTEGER NOT NULL DEFAULT 0,
    started_at            TIMESTAMP,
    completed_at          TIMESTAMP,
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_projects_user   ON projects (user_id);
CREATE INDEX IF NOT EXISTS ix_projects_status ON projects (user_id, status);

CREATE TABLE IF NOT EXISTS project_phases (
    id                 SERIAL PRIMARY KEY,
    project_id         INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    name               VARCHAR NOT NULL,
    order_index        INTEGER NOT NULL,
    brief              TEXT,
    status             VARCHAR NOT NULL DEFAULT 'locked',
    deliverable_note   TEXT,
    deliverable_url    VARCHAR,
    started_at         TIMESTAMP,
    completed_at       TIMESTAMP,
    CONSTRAINT uq_project_phase_name UNIQUE (project_id, name)
);

CREATE TABLE IF NOT EXISTS progress_logs (
    id                SERIAL PRIMARY KEY,
    project_id        INTEGER NOT NULL REFERENCES projects (id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users (id),
    week_key          VARCHAR NOT NULL,
    phase             VARCHAR,
    hours_spent       DOUBLE PRECISION,
    what_i_did        TEXT,
    what_blocked_me   TEXT,
    confidence        INTEGER,
    created_at        TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_progress_log_week UNIQUE (project_id, week_key)
);
CREATE INDEX IF NOT EXISTS ix_logs_user_week ON progress_logs (user_id, week_key);

-- ============================================================ W5 buddy

CREATE TABLE IF NOT EXISTS chat_sessions (
    id                SERIAL PRIMARY KEY,
    user_id           INTEGER NOT NULL REFERENCES users (id),
    title             VARCHAR,
    project_id        INTEGER REFERENCES projects (id),
    summary           TEXT,
    summarised_upto   INTEGER NOT NULL DEFAULT 0,
    message_count     INTEGER NOT NULL DEFAULT 0,
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW(),
    is_archived       BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_chat_sessions_user ON chat_sessions (user_id, is_archived);

CREATE TABLE IF NOT EXISTS chat_messages (
    id                SERIAL PRIMARY KEY,
    session_id        INTEGER NOT NULL REFERENCES chat_sessions (id) ON DELETE CASCADE,
    role              VARCHAR NOT NULL,
    content           TEXT NOT NULL,
    guardrail_flag    VARCHAR,
    guardrail_reason  VARCHAR,
    needs_review      BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at       TIMESTAMP,
    created_at        TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_chat_messages_session ON chat_messages (session_id, id);
CREATE INDEX IF NOT EXISTS ix_chat_messages_review  ON chat_messages (needs_review, created_at);

CREATE TABLE IF NOT EXISTS generated_references (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users (id),
    project_id   INTEGER REFERENCES projects (id) ON DELETE CASCADE,
    phase        VARCHAR,
    payload      TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_reference_project_phase UNIQUE (project_id, phase)
);

-- ============================================================ W6 counsellor + privacy

CREATE TABLE IF NOT EXISTS counsellor_notes (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES users (id),
    counsellor_id   INTEGER NOT NULL REFERENCES users (id),
    body            TEXT NOT NULL,
    visibility      VARCHAR NOT NULL DEFAULT 'private',
    tag             VARCHAR,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_notes_student ON counsellor_notes (student_id, created_at DESC);

CREATE TABLE IF NOT EXISTS consent_records (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users (id),
    scope           VARCHAR NOT NULL,
    granted         BOOLEAN NOT NULL DEFAULT FALSE,
    policy_version  VARCHAR NOT NULL DEFAULT '1.0',
    granted_at      TIMESTAMP,
    revoked_at      TIMESTAMP,
    source_ip       VARCHAR,
    created_at      TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_consent_user_scope UNIQUE (user_id, scope)
);

-- Existing users have already been using the platform, so grandfather the
-- required scope. Optional scopes stay OFF — opt-in must be a real choice.
INSERT INTO consent_records (user_id, scope, granted, granted_at)
SELECT id, 'data_processing', TRUE, NOW() FROM users
ON CONFLICT (user_id, scope) DO NOTHING;

COMMIT;
