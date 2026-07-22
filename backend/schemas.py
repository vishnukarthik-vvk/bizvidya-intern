from pydantic import BaseModel
from typing import Dict, List, Any

class UserCreate(BaseModel):
    fullName: str
    age: int
    educationLevel: str
    workExperience: str
    currentRole: str
    professionalDomain: str
    careerGoals: str
    hobbies: str
    preferredLanguage: str


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class MCQResultCreate(BaseModel):
    user_id: int
    answers: Dict[str, str]
    total_score: float
    max_possible_score: float
    category_scores: Dict[str, float]
    max_category_scores: Dict[str, float]


class OpenEndedResultCreate(BaseModel):
    user_id: int
    answers: List[Dict[str, str]]
    scores: List[Dict[str, Any]]


class AssessmentReportSave(BaseModel):
    user_id: int
    report: Dict[str, Any]


class ProgressSave(BaseModel):
    user_id: int
    stage: str
    data: Dict[str, Any]