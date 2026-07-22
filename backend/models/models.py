from sqlalchemy import Column , Integer , String, Text, Float, ForeignKey, UniqueConstraint
from database import Base

class User(Base):
    __tablename__  = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    fullName = Column(String)
    age = Column(Integer)
    educationLevel = Column(String)
    work_experience = Column(String)
    current_role = Column(String)
    professional_domain = Column(String)
    career_goal = Column(String)
    hobbies = Column(String)
    preferred_language = Column(String)


class MCQResult(Base):
    __tablename__ = "mcq_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(Text)              # JSON string: {question_id: "A"/"B"/...}
    total_score = Column(Float)
    max_possible_score = Column(Float)
    category_scores = Column(Text)      # JSON string: {category: score}
    max_category_scores = Column(Text)  # JSON string: {category: max_score}


class OpenEndedResult(Base):
    __tablename__ = "open_ended_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answers = Column(Text)   # JSON string: [{question, answer}, ...]
    scores = Column(Text)    # JSON string: [{question, category, score, justification}, ...]


class AssessmentReport(Base):
    __tablename__ = "assessment_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    report_data = Column(Text)  # full JSON blob: every LLM-generated section from Results.js


class AssessmentProgress(Base):
    __tablename__ = "assessment_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stage = Column(String, nullable=False)   # "mcq" or "open_ended"
    progress_data = Column(Text)             # JSON blob: whatever that stage needs to resume

    __table_args__ = (
        UniqueConstraint('user_id', 'stage', name='uq_user_stage_progress'),
    )