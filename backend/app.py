import os
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import json  
import re
from typing import Dict  
from typing import Optional
from google.oauth2 import service_account  
import random
from groq import Groq
import requests
from database import engine,Base,get_db
from models.models import User, MCQResult, OpenEndedResult, AssessmentReport, AssessmentProgress
from sqlalchemy.orm import Session
from fastapi import Depends
from schemas import UserCreate, MCQResultCreate, OpenEndedResultCreate, AssessmentReportSave, SignupRequest, LoginRequest, ProgressSave
load_dotenv() 

Base.metadata.create_all(bind=engine)
app = FastAPI()

origins = [  
    "https://skill-assessment-1.onrender.com",
    "http://localhost",
    "https://skill-assessment-n1dm.onrender.com",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-pro")


from services.llm_services import llm_services

def load_questions():
    df = pd.read_csv("Assessment_chat_v2.csv")
    if 'ID' not in df.columns:
        df['ID'] = df.index + 1
    return df

questions_df = load_questions()

class UserProfile(BaseModel):
    name: Optional[str]
    age: Optional[int]
    education_level: Optional[str]
    field: Optional[str]
    domain: Optional[str]
    exp_level: Optional[str]
    career_goal: Optional[str]
    interests: Optional[List[str]]

# Replace the old model:
class MCQScoreDict(BaseModel):
    Subject_Interest_Domain_Curiosity: int = 0
    Cognitive_and_Creative_Skills: int = 0
    Academic_Aptitude_Learning_Style: int = 0
    Digital_Technological_Orientation: int = 0
    Values_Lifestyle_Priorities: int = 0
    Financial_Awareness_Constraints: int = 0
    Risk_Appetite_Ambiguity_Tolerance: int = 0
    Emotional_and_Social_Competence: int = 0
    Communication_Language_Preference: int = 0
    Personal_Management_Wellness: int = 0
class OpenEndedRequest(BaseModel):
    user_profile: UserProfile
    mcq_scores: MCQScoreDict


@app.get("/")
def root():
    return {"message": "Skill Assessment Backend Running"}


class OpenEndedAnswer(BaseModel):
    question: str
    answer: str
    categories: List[str]

class ScoreOpenEndedRequest(BaseModel):
    user_profile: UserProfile
    answers: List[OpenEndedAnswer]
from prompts.score_openended_responses import (
    SCORE_OPENENDED_RESPONSES_PROMPT,
    SCORE_OPENENDED_RESPONSES_SYSTEM_PROMPT,
)
from schemas import UserCreate, MCQResultCreate, OpenEndedResultCreate, AssessmentReportSave, SignupRequest, LoginRequest
from Auth import hash_password , verify_password
@app.post("/signup")
def signup(payload: SignupRequest , db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code = 400,
            detail = "please enter valid email address.",
        )
    if len(payload.password) < 8:
        raise HTTPException(
            status_code = 400,
            detail = "password must contain atleast 8 characters",
        )
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code = 400,
            detail = "email already in use",
        )
    db_user = User(
        email = email,
        hashed_password = hash_password(payload.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return{
        "message":"account created sucessfully",
        "user_id": db_user.id,
        "email" : db_user.email
    }

@app.post("/save_progress")
def save_progress(payload: ProgressSave, db: Session = Depends(get_db)):
    existing = db.query(AssessmentProgress).filter(
        AssessmentProgress.user_id == payload.user_id,
        AssessmentProgress.stage == payload.stage
    ).first()

    if existing:
        existing.progress_data = json.dumps(payload.data)
    else:
        existing = AssessmentProgress(
            user_id=payload.user_id,
            stage=payload.stage,
            progress_data=json.dumps(payload.data),
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return {"message": "Progress saved successfully", "stage": payload.stage}


@app.get("/get_progress/{user_id}/{stage}")
def get_progress(user_id: int, stage: str, db: Session = Depends(get_db)):
    record = db.query(AssessmentProgress).filter(
        AssessmentProgress.user_id == user_id,
        AssessmentProgress.stage == stage
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="No saved progress found")

    return {"stage": record.stage, "data": json.loads(record.progress_data)}


@app.delete("/clear_progress/{user_id}/{stage}")
def clear_progress(user_id: int, stage: str, db: Session = Depends(get_db)):
    record = db.query(AssessmentProgress).filter(
        AssessmentProgress.user_id == user_id,
        AssessmentProgress.stage == stage
    ).first()

    if record:
        db.delete(record)
        db.commit()

    return {"message": "Progress cleared successfully", "stage": stage}

@app.post("/users")
def create_user(user : UserCreate , db : Session = Depends(get_db)):
    db_user = User(
        fullName = user.fullName,
        age = user.age,
        educationLevel=user.educationLevel,
        current_role = user.currentRole,
        work_experience = user.workExperience,
        professional_domain = user.professionalDomain,
        career_goal = user.careerGoals,
        hobbies = user.hobbies,
        preferred_language = user.preferredLanguage

    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return{
        "message":"user created successfully",
        "user_id": db_user.id
    }


@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "fullName": db_user.fullName,
        "age": db_user.age,
        "educationLevel": db_user.educationLevel,
        "workExperience": db_user.work_experience,
        "currentRole": db_user.current_role,
        "professionalDomain": db_user.professional_domain,
        "careerGoals": db_user.career_goal,
        "hobbies": db_user.hobbies,
        "preferredLanguage": db_user.preferred_language,
    }


@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.fullName = user.fullName
    db_user.age = user.age
    db_user.educationLevel = user.educationLevel
    db_user.work_experience = user.workExperience
    db_user.current_role = user.currentRole
    db_user.professional_domain = user.professionalDomain
    db_user.career_goal = user.careerGoals
    db_user.hobbies = user.hobbies
    db_user.preferred_language = user.preferredLanguage

    db.commit()
    db.refresh(db_user)

    return {"message": "user updated successfully", "user_id": db_user.id}


@app.post("/login")

@app.post("/login")
def login(payload:LoginRequest , db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    db_user = db.query(User).filter(User.email == email).first()

    if not db_user or not verify_password(payload.password , db_user.hashed_password):
        raise HTTPException(
            status_code = 400,
            detail = "Invalid email or password",
        )
    
    return {
        "message" : "Login sucessful",
        "user_id" : db_user.id,
        "email": db_user.email,
        "fullName" : db_user.fullName,
    }


@app.post("/save_mcq_results")
def save_mcq_results(payload: MCQResultCreate, db: Session = Depends(get_db)):
    db_result = MCQResult(
        user_id=payload.user_id,
        answers=json.dumps(payload.answers),
        total_score=payload.total_score,
        max_possible_score=payload.max_possible_score,
        category_scores=json.dumps(payload.category_scores),
        max_category_scores=json.dumps(payload.max_category_scores),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    return {
        "message": "MCQ results saved successfully",
        "result_id": db_result.id
    }


@app.post("/save_open_ended_results")
def save_open_ended_results(payload: OpenEndedResultCreate, db: Session = Depends(get_db)):
    db_result = OpenEndedResult(
        user_id=payload.user_id,
        answers=json.dumps(payload.answers),
        scores=json.dumps(payload.scores),
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)

    return {
        "message": "Open-ended results saved successfully",
        "result_id": db_result.id
    }


@app.post("/save_assessment_report")
def save_assessment_report(payload: AssessmentReportSave, db: Session = Depends(get_db)):
    existing = db.query(AssessmentReport).filter(
        AssessmentReport.user_id == payload.user_id
    ).first()

    if existing:
        existing.report_data = json.dumps(payload.report)
    else:
        existing = AssessmentReport(
            user_id=payload.user_id,
            report_data=json.dumps(payload.report),
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return {
        "message": "Assessment report saved successfully",
        "user_id": payload.user_id
    }


@app.post("/score_open_ended_responses")
def score_open_ended_responses(req: ScoreOpenEndedRequest):
    all_scores = []

    for idx, q in enumerate(req.answers):
        prompt = SCORE_OPENENDED_RESPONSES_PROMPT.format(
            age=req.user_profile.age,
            education_level=req.user_profile.education_level,
            field=req.user_profile.field,
            career_goal=req.user_profile.career_goal,
            question_number=idx + 1,
            question=q.question,
            answer=q.answer,
            categories=", ".join(q.categories) if q.categories else
                "Subject Interest & Domain Curiosity, Cognitive & Creative Skills, Academic Aptitude & Learning Style, Digital & Technological Orientation, Values & Lifestyle Priorities, Financial Awareness & Constraints, Risk Appetite & Ambiguity Tolerance, Emotional & Social Competence, Communication & Language Preference, Personal Management & Wellness",
        )

        data,raw = llm_services.generate(
            prompt=prompt,
            system_message=SCORE_OPENENDED_RESPONSES_SYSTEM_PROMPT,
            client = (idx %3)+1,
            max_tokens = 1500,
            temperature=0.7,
        )
        all_scores.extend(data.get("scores", []))

    return {"scores": all_scores}

    
class TooltipRequest(BaseModel):
    category: str
    user_score: float
    benchmark_score: float
    user_profile: UserProfile


# Hardcoded benchmark tooltips
BENCHMARK_TOOLTIPS = {
    "Cognitive & Creative Skills": "Reach 70% benchmark by practicing teamwork and time management!",
    "Work & Professional Behavior": "The 65% benchmark indicates industry average. Focus on improving your skills to reach and surpass this target.",
    "Emotional & Social Competence": "Benchmark is 63%. Develop emotional intelligence and practice teamwork to reach this target .",
    "Personal Management & Wellness": "Reach 68% benchmark by prioritizing tasks and practicing mindfulness to excel .",
    "Family & Relationships": "Reach 60% benchmark by practicing empathy and teamwork to excel"
}

from prompts.tooltips import (
    TOOLTIP_PROMPT,
    TOOLTIP_SYSTEM_PROMPT,
)
@app.post("/generate_tooltips")
def generate_tooltip(req: TooltipRequest):

    prompt = TOOLTIP_PROMPT.format(
        education_level=req.user_profile.education_level,
        field=req.user_profile.field,
        career_goal=req.user_profile.career_goal,
        category=req.category,
        user_score=req.user_score,
        benchmark_score=req.benchmark_score,
    )
    try:
        json_data, raw_text = llm_services.generate(
            prompt=prompt,
            system_message=TOOLTIP_SYSTEM_PROMPT,
            client=1,
        )
        print("Raw Groq tooltip response:", raw_text)

        if "user_tooltip" not in json_data:
            raise HTTPException(status_code=500, detail="Tooltip key missing in Groq response")

        # Add benchmark tooltip from hardcoded constants
        benchmark_tooltip = BENCHMARK_TOOLTIPS.get(req.category)

        return {
            "user_tooltip": json_data["user_tooltip"],
            "benchmark_tooltip": benchmark_tooltip
        }

    except Exception as e:
        print(f"Groq tooltip error: {e}")
        # Fallback tooltip if Groq fails
        return {
            "user_tooltip": f"Your {req.user_score:.1f}% in {req.category} shows strong potential. Keep practicing and applying skills to improve further.",
            "benchmark_tooltip": BENCHMARK_TOOLTIPS.get(req.category)
        }




class GrowthProjectionRequest(BaseModel):
    user_data: UserProfile
    user_scores: Dict[str, float]
    benchmark_scores: Dict[str, float]
    tier: str  

from prompts.growth_projection import (
    GROWTH_PROJECTION_PROMPT,
    GROWTH_PROJECTION_SYSTEM_PROMPT,
)
@app.post("/generate_growth_projection")
def generate_growth_projection(req: GrowthProjectionRequest):
    """Career Growth Projection Generator – points calculated locally, steps from LLM"""

   
    avg_score = sum(req.user_scores.values()) / len(req.user_scores) if req.user_scores else 0

    
    growth_projection = {
        "current_score": round(avg_score, 1),
        "3_months": round(avg_score * 1.05, 1),   
        "6_months": round(avg_score * 1.10, 1),   
        "12_months": round(avg_score * 1.15, 1), 
        "peer_percentile": round(
            min(99, max(1, (avg_score / max(req.benchmark_scores.values() or [100])) * 100)),
            1
        ),
        "tier": req.tier
    }

    prompt = GROWTH_PROJECTION_PROMPT.format(
        name=req.user_data.name,
        education=req.user_data.education_level,
        experience=req.user_data.exp_level,
        domain=req.user_data.domain,
        career_goal=req.user_data.career_goal,
    )


    try:
        json_data, raw_text = llm_services.generate(
            prompt=prompt,
            system_message=GROWTH_PROJECTION_SYSTEM_PROMPT,
            client=2,
            max_tokens=300,
        )

        print("Raw Groq action steps response:", raw_text)

        action_steps = json_data.get("action_steps", [])

        return {
            "growth_projection": growth_projection,
            "action_steps": action_steps
        }

    except Exception as e:
        print(f"[ERROR] Groq action steps generation failed: {str(e)}")

        
        return {
            "growth_projection": growth_projection,
            "action_steps": [
                "Complete 1 hands-on project this month",
                "Practice weekly domain-specific challenges",
                "Join 1 professional community for peer learning"
            ]
        }


    

class MarketAnalysisRequest(BaseModel):
    user_profile: UserProfile
    final_score: float
    overall_percentage: float
    percentile: float
    strengths: List[str]
    weaknesses: List[str]
    benchmark_scores: Dict[str, float]
    tier:str

from prompts.generate_market_analysis import (
    MARKET_ANALYSIS_PROMPT,
    MARKET_ANALYSIS_SYSTEM_PROMPT,
)
@app.post("/generate_market_analysis")
def generate_market_analysis(req: MarketAnalysisRequest):
    user_data = {
        "name": req.user_profile.name,
        "education": req.user_profile.education_level,
        "exp_level": req.user_profile.exp_level,
        "domain": req.user_profile.domain,
        "career_goal": req.user_profile.career_goal,
    }

    score = req.final_score
    percentile = req.percentile
    strengths = req.strengths
    weaknesses = req.weaknesses
    benchmark_scores = req.benchmark_scores
    tier=req.tier

    prompt = MARKET_ANALYSIS_PROMPT.format(
        name=user_data.get("name", "User"),
        education=user_data.get("education", "Not specified"),
        exp_level=user_data.get("exp_level", "Not specified"),
        domain=user_data.get("domain", "Not specified"),
        career_goal=user_data.get("career_goal", "Not specified"),
        score=score,
        tier=tier,
        percentile=percentile,
        strengths=", ".join(strengths) if strengths else "None",
        weaknesses=", ".join(weaknesses) if weaknesses else "None",
        benchmark_scores=", ".join(
            f"{cat}: {val}%"
            for cat, val in benchmark_scores.items()
        ),
    )

    # Fallback response
    def get_fallback_market_analysis():
        return {
            "tier": {
                "label": tier,
                "bullets": [
                    f"You are currently positioned as {tier}, which reflects early-stage potential.",
                    "This tier indicates you're just beginning to explore professional development.",
                    "Foundational skills need reinforcement before advancing to next tier."
                ]
            },
            "experience": {
                "label": "Less than 1 year",
                "bullets": [
                    "Your profile aligns with entry-level or fresher roles.",
                    "Building confidence and consistency is key at this stage."
                ]
            },
            "salary": {
                "label": "Estimated salary band",
                "bullets": [
                    "Based on your tier, expected roles fall in entry-level brackets (₹3–6 LPA).",
                    "Upskilling consistently can boost this to ₹8–10 LPA in 1–2 years."
                ]
            },
             "readiness_score": round(req.overall_percentage, 1)
        }

    # Groq integration
    try:
        json_data,raw_text = llm_services.generate(
            prompt=prompt,
            system_message=MARKET_ANALYSIS_SYSTEM_PROMPT,
            client = 3,
            max_tokens=2000,

        )
        print("Raw Groq market analysis response:", raw_text)

        required_keys = ["tier", "experience", "salary"]
        if all(k in json_data for k in required_keys):
            return {
                **json_data,
                "readiness_score": round(req.overall_percentage, 1)
            }
    except Exception as e:
        print(f"[ERROR] Market analysis generation failed: {str(e)}")

    return get_fallback_market_analysis()
    
class PeerBenchmarkRequest(BaseModel):
    user_data: UserProfile
    combined_score: float
    mcq_scores: Dict[str, float]
    open_scores: Dict[str, float]
    strong_categories: List[str]
    weak_categories: List[str]
    benchmarks: Dict[str, float]


from prompts.peer_benchmark import (
    PEER_BENCHMARK_PROMPT,
    PEER_BENCHMARK_SYSTEM_PROMPT,
)
@app.post("/generate_peer_benchmark")
def generate_peer_benchmark(req: PeerBenchmarkRequest):
    """Generate peer benchmark and in-demand traits analysis report using groq_client_2"""

    prompt = PEER_BENCHMARK_PROMPT.format(
        name=req.user_data.name,
        domain=req.user_data.domain,
        career_goal=req.user_data.career_goal,
        exp_level=req.user_data.exp_level,
        combined_score=req.combined_score,
        mcq_scores=json.dumps(req.mcq_scores),
        open_scores=json.dumps(req.open_scores),
        strong_categories=", ".join(req.strong_categories) or "None",
        weak_categories=", ".join(req.weak_categories) or "None",
        benchmarks=json.dumps(req.benchmarks),
    )


    def fallback_response():
        return {
            "peer_benchmark": {
                "percentile": "Top 70% among peers",
                "narrative": "Your skills are competitive in your domain with strengths in key areas.",
                "in_demand_traits": [
                    "Technical proficiency matches industry requirements",
                    "Leadership skills align with management expectations"
                ]
            }
        }

    try:

        json_data , raw_text = llm_services.generate(
            prompt = prompt,
            client = 4,
            max_tokens= 2000,
            system_message=PEER_BENCHMARK_SYSTEM_PROMPT,

        )
        if "peer_benchmark" not in json_data:
            raise HTTPException(status_code=500, detail="Response missing 'peer_benchmark' key")

        return json_data

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode error: {e}")
        print(f"Raw response: {raw_text}")
        return fallback_response()

    except Exception as e:
        print(f"[ERROR] Groq API error: {e}")
        return fallback_response()


class ActionPlanRequest(BaseModel):
    user_data: UserProfile
    mcq_scores: Dict[str, float]
    open_scores: Dict[str, float]
    market_benchmarks: Dict[str, float]
    strong_categories: List[str]
    moderate_categories: List[str]
    weak_categories: List[str]


from prompts.action_plan import (
    ACTION_PLAN_PROMPT,
    ACTION_PLAN_SYSTEM_PROMPT,
)
@app.post("/generate_action_plan")
def generate_action_plan(req: ActionPlanRequest):
    """Generate a personalized 90-day roadmap based on skill scores and benchmarks"""

    # Combine MCQ + Open scores → average per category
    combined_scores = {}
    for k in set(req.mcq_scores) | set(req.open_scores):
        mcq = req.mcq_scores.get(k, 0)
        open_ = req.open_scores.get(k, 0)
        combined_scores[k] = round((mcq + open_) / 2, 1)

    # Average score
    current_avg = np.mean(list(combined_scores.values()))

    # Groq prompt
   
    score_vs_benchmark = "\n".join(
        f"- {cat}: {combined_scores.get(cat, 0)} vs {req.market_benchmarks.get(cat, 'N/A')}"
        for cat in combined_scores
    )

    prompt = ACTION_PLAN_PROMPT.format(
        name=req.user_data.name,
        education=req.user_data.education_level,
        exp_level=req.user_data.exp_level,
        domain=req.user_data.domain,
        career_goal=req.user_data.career_goal,
        current_avg=current_avg,
        score_vs_benchmark=score_vs_benchmark,
        strong_categories=", ".join(req.strong_categories) or "None",
        moderate_categories=", ".join(req.moderate_categories) or "None",
        weak_categories=", ".join(req.weak_categories) or "None",
    )

    try:
        
        
        roadmap_text = llm_services.generate_text(
            prompt = prompt,
            system_message=ACTION_PLAN_SYSTEM_PROMPT,
            temperature=0.8,
            max_tokens=2500,
        )
        print("Raw Groq action plan response:", roadmap_text)
        
        return {"roadmap_text": roadmap_text}
        
    except Exception as e:
        print(f"[ERROR] Groq 90-day roadmap generation failed: {str(e)}")
        return {
            "roadmap_text": """90-DAY PERSONALIZED ROADMAP

### PHASE 1 (0–30 Days) – Build Foundation in Core Gaps
- **Focus Areas:** Time Management, Data Interpretation
- **Weekly Actions:**
  - Week 1: Use Pomodoro timer daily
  - Week 2: Analyze 1 dataset using Excel weekly
  - Week 3: Practice case-based MCQs
  - Week 4: Join 1 peer learning group
- **Milestone by Day 30:** 20% score increase in 2 weakest categories

### PHASE 2 (31–60 Days) – Strengthen for Career Goal
- **Focus Areas:** Communication, Research
- **Weekly Actions:**
  - Week 5: Record weekly domain summary videos
  - Week 6: Analyze 2 research papers
  - Week 7: Write weekly reflection journal
  - Week 8: Peer presentation or webinar
- **Milestone by Day 60:** Public portfolio submission

### PHASE 3 (61–90 Days) – Demonstrate Strengths with Visibility
- **Focus Areas:** Leadership, Critical Thinking
- **Weekly Actions:**
  - Week 9: Lead 1 project meeting
  - Week 10: Mentor a junior peer
  - Week 11: Publish insight article
  - Week 12: Pitch for internship/freelance role
- **Milestone by Day 90:** Ready for higher responsibility or role transition"""
        }

class GrowthSourcesRequest(BaseModel):
    user_data: UserProfile
    weak_categories: List[str]
    strong_categories: List[str]
    moderate_categories: List[str]
    combined_scores: Dict[str, float]

# ==== HARD-CODED SOURCE LIBRARY ====

RECOMMENDED_SOURCES = {
    "Cognitive & Creative Skills": {
        "below_70": [
            {
                "title": "Think Again – Book by Adam Grant",
                "link": "https://adamgrant.net/book/think-again/",
                "duration": "6–8 hrs (audiobook or print)",
                "outcome": "Helps rethink assumptions, build mental flexibility, and sharpen cognitive agility."
            },
            {
                "title": "NPR Hidden Brain – Cognitive Bias Series",
                "link": "https://www.npr.org/series/423302056/hidden-brain",
                "duration": "20 mins/episode (choose 4 episodes)",
                "outcome": "Explores how thinking errors affect decisions, encouraging awareness and self-correction."
            },
            {
                "title": "Design Your Career – Stanford Life Design Lab",
                "link": "https://lifedesignlab.stanford.edu/",
                "duration": "4–5 hrs (self-paced)",
                "outcome": "Encourages creative problem framing and career prototyping based on design thinking."
            },
            {
                "title": "Critical Thinking – Coursera (U of Edinburgh)",
                "link": "https://www.coursera.org/learn/critical-thinking-skills",
                "duration": "8 hrs (2 weeks)",
                "outcome": "Sharpens logical thinking, argument evaluation, and clarity in decision-making."
            },
            {
                "title": "Problem-Solving Strategies – FutureLearn",
                "link": "https://www.futurelearn.com/courses/problem-solving",
                "duration": "2 weeks (3 hrs/week)",
                "outcome": "Teaches structured approaches to personal and workplace problem-solving."
            }
        ],
        "above_70": [
            {
                "title": "Kaggle Active Competitions",
                "link": "https://www.kaggle.com/competitions",
                "duration": "3–5 hrs/week (2 weeks)",
                "outcome": "Applies real-world analytical thinking and encourages structured experimentation."
            },
            {
                "title": "IDEO U: Creative Problem Solving",
                "link": "https://www.ideou.com/products/problem-solving",
                "duration": "3 weeks (1–2 hrs/week)",
                "outcome": "Design thinking–based course for framing complex challenges and innovating."
            },
            {
                "title": "Think Again – Book by Adam Grant",
                "link": "https://adamgrant.net/book/think-again/",
                "duration": "6–8 hrs",
                "outcome": "Reinforces mental agility and creative self-questioning for experienced professionals."
            },
            {
                "title": "Hidden Brain – Workplace Decision Series",
                "link": "https://www.npr.org/series/423302056/hidden-brain",
                "duration": "Listen to 4 episodes (80 mins total)",
                "outcome": "Deepens insight into unconscious reasoning patterns and creative reframing."
            },
            {
                "title": "Design Your Career – Stanford Life Design Lab",
                "link": "https://lifedesignlab.stanford.edu/",
                "duration": "4–5 hrs (self-guided)",
                "outcome": "Great for high performers to explore innovative career pathways and passion alignment."
            }
        ]
    },
    "Work & Professional Behavior": {
        "below_70": [
            {
                "title": "Time Management Mastery – LinkedIn Learning",
                "link": "https://www.linkedin.com/learning/time-management-fundamentals",
                "duration": "45 mins (self-paced)",
                "outcome": "Master essential time-blocking and prioritization techniques"
            },
            {
                "title": "Workplace Communication Strategies – MindTools",
                "link": "https://www.mindtools.com/CommSkll/CommunicationIntro.htm",
                "duration": "10 mins/module",
                "outcome": "Improve professional tone and workplace clarity"
            },
            {
                "title": "Asana Guide to Effective Team Collaboration",
                "link": "https://asana.com/resources/team-collaboration",
                "duration": "20 mins",
                "outcome": "Learn async communication strategies and goal alignment"
            },
            {
                "title": "Career Planning Toolkit – Indeed",
                "link": "https://www.indeed.com/career-advice/career-development/career-planning",
                "duration": "30 mins",
                "outcome": "Plan realistic professional growth paths and expectations"
            },
            {
                "title": "The Feedback Guide – Atlassian Work Life",
                "link": "https://www.atlassian.com/blog/teamwork/how-to-give-feedback",
                "duration": "10 mins",
                "outcome": "Learn to give and receive feedback constructively"
            }
        ],
        "above_70": [
            {
                "title": "Leadership Live (Podcast) – How to Work With (Almost) Anyone",
                "link": "https://podcasts.apple.com/in/podcast/leadership-live/id1524072573",
                "duration": "30–40 mins/episode",
                "outcome": "Sharpen collaboration and leadership relationship skills"
            },
            {
                "title": "Coaching for Leaders (Podcast)",
                "link": "https://podcasts.apple.com/in/podcast/coaching-for-leaders/id458827716",
                "duration": "20–25 mins/episode",
                "outcome": "Deepen influence and team management skills"
            },
            {
                "title": "The Pitch (Podcast) – Real Startup Pitches",
                "link": "https://open.spotify.com/show/5CnDmMUG0S5bSSw612fs8C",
                "duration": "30 mins/episode",
                "outcome": "Learn persuasive presentation and operational decision-making"
            },
            {
                "title": "Masters of Scale (Podcast)",
                "link": "https://mastersofscale.com/",
                "duration": "35–45 mins/episode",
                "outcome": "Absorb executive insights on team culture and adaptability"
            },
            {
                "title": "Team Icebreakers & Logic Games – SurfOffice Blog",
                "link": "https://www.surfoffice.com/blog/problem-solving-games",
                "duration": "15 mins each",
                "outcome": "Boost team engagement and creative collaboration"
            }
        ]
    },
    "Emotional & Social Competence": {
        "below_70": [
            {
                "title": "Emotional Intelligence Toolkit – University of Nottingham",
                "link": "https://www.nottingham.ac.uk/studentservices/documents/emotional-intelligence-toolkit.pdf",
                "duration": "1–2 hrs",
                "outcome": "Build self-awareness and emotional control through a structured workbook"
            },
            {
                "title": "Emotion Regulation Exercises – PositivePsychology.com",
                "link": "https://positivepsychology.com/emotion-regulation-worksheets/",
                "duration": "30 mins daily (1 week)",
                "outcome": "Enhance ability to manage emotions under stress"
            },
            {
                "title": "Six Seconds EQ Mini Assessment",
                "link": "https://6sec.org/test/eq/",
                "duration": "10 mins",
                "outcome": "Get a quick snapshot of your emotional intelligence level"
            },
            {
                "title": "Calm in Chaos – Verywell Mind Audio Guide",
                "link": "https://www.verywellmind.com/what-is-emotional-intelligence-2795423",
                "duration": "10 mins",
                "outcome": "Learn how to stay calm and respond, not react"
            },
            {
                "title": "EQ Self-Reflection Journal (Free Template)",
                "link": "https://www.canva.com/design/DAFqbHvbAsY/view?utm_content=DAFqbHvbAsY&utm_campaign=designshare&utm_medium=link&utm_source=publishsharelink",
                "duration": "5–10 mins/day",
                "outcome": "Track triggers, reactions, and emotional growth over time"
            }
        ],
        "above_70": [
            {
                "title": "Emotional Intelligence Coaching Podcast – Apple",
                "link": "https://podcasts.apple.com/us/podcast/emotional-intelligence-coaching/id1470081541",
                "duration": "10–20 mins per episode",
                "outcome": "Deepen your empathy, conflict navigation, and leadership EQ"
            },
            {
                "title": "The EQ Edge Workbook – Self-Coaching Exercises",
                "link": "https://eqedge.files.wordpress.com/2011/11/eq-edge-handbook.pdf",
                "duration": "2 hrs/week (4 weeks)",
                "outcome": "Apply practical EQ-building techniques from a proven leadership manual"
            },
            {
                "title": "Empathy & Listening Skills – PositivePsychology Toolkit",
                "link": "https://positivepsychology.com/empathy-worksheets/",
                "duration": "30–45 mins/session",
                "outcome": "Sharpen emotional responsiveness and social attunement"
            },
            {
                "title": "Power of Emotions at Work – Verywell Mind Guide",
                "link": "https://www.verywellmind.com/the-importance-of-emotional-intelligence-in-the-workplace-4164713",
                "duration": "15 mins",
                "outcome": "Use emotions strategically to navigate team dynamics and relationships"
            },
            {
                "title": "EQ Reflection Tools – Six Seconds Library",
                "link": "https://www.6seconds.org/resources/",
                "duration": "Varies (choose relevant tools)",
                "outcome": "Expand your EQ toolkit with frameworks used by global leaders"
            }
        ]
    }
}


DEFAULT_RECOMMENDATIONS = [
    {
        "category": "General",
        "title": "LinkedIn Learning: Career Development",
        "link": "https://www.linkedin.com/learning",
        "why": "Broad career development resources to strengthen your professional profile",
        "duration": "Varies",
        "outcome": "Improve key professional skills"
    },
    {
        "category": "General",
        "title": "Coursera: Professional Development Courses",
        "link": "https://www.coursera.org",
        "why": "High-quality courses to enhance your career skills",
        "duration": "Varies",
        "outcome": "Develop professional skills across multiple domains"
    }
]

# ==== FUNCTION ====

def generate_recommended_sources(user_data, weak_categories, moderate_categories, combined_scores):
    recommendations = []
    career_goal = user_data.get("career_goal", "your career goal")

    # Prioritize weak categories
    for category in weak_categories:
        if len(recommendations) >= 3:
            break
        if category in RECOMMENDED_SOURCES:
            score = combined_scores.get(category, 0)
            tier = "below_70" if score < 70 else "above_70"
            source = random.choice(RECOMMENDED_SOURCES[category][tier])
            recommendations.append({
                "category": category,
                "title": source["title"],
                "link": source["link"],
                "why": f"Your {category} score ({score:.1f}) needs improvement for {career_goal}",
                "duration": source["duration"],
                "outcome": source["outcome"]
            })

    # Add moderate if not enough
    for category in moderate_categories:
        if len(recommendations) >= 3:
            break
        if category in RECOMMENDED_SOURCES and category not in [r['category'] for r in recommendations]:
            score = combined_scores.get(category, 0)
            tier = "below_70" if score < 70 else "above_70"
            source = random.choice(RECOMMENDED_SOURCES[category][tier])
            recommendations.append({
    "category": category,
    "title": source["title"],
    "why": f"Your {category} score ({score:.1f}) needs improvement for {career_goal}",  # Map why -> description
    "link": source["link"],
    "duration": source["duration"],
    "outcome": source["outcome"]
})

    # Fallback: add generic ones
    if len(recommendations) < 2:
        recommendations.extend(DEFAULT_RECOMMENDATIONS[:2 - len(recommendations)])

    return recommendations[:3]

# ==== ENDPOINT ====

@app.post("/generate_growth_sources")
def generate_growth_sources(req: GrowthSourcesRequest):
    """Generate personalized growth sources based on skill scores"""
    try:
        sources = generate_recommended_sources(
            user_data=req.user_data.dict(),
            weak_categories=req.weak_categories,
            moderate_categories=req.moderate_categories,
            combined_scores=req.combined_scores
        )
        return {"sources": sources}
    except Exception as e:
        print(f"[ERROR] Failed to generate growth sources: {str(e)}")
        return {"sources": DEFAULT_RECOMMENDATIONS[:2]}

class MomentumAction(BaseModel):
    title: str
    description: str
    why: str
    effort: str

@app.post("/generate_momentum_toolkit")
def generate_momentum_toolkit():
    """Return 3 non-technical, easy-to-apply actions to build momentum"""

    formatted_actions = []
    IMMEDIATE_ACTIONS = {
        "Cognitive & Focus Boosters": [
            {
                "title": "The 20-Second Reset Rule",
                "description": "Stand, breathe deeply, and stretch for 20 seconds every 2 hours.",
                "why": "Resets mental fatigue instantly and keeps your brain sharp.",
                "effort": "🟢 Easy"
            },
            {
                "title": "The 1% Upgrade Rule",
                "description": "Do one small thing 1% better than yesterday.",
                "why": "Tiny daily upgrades compound into massive performance over time.",
                "effort": "🟡 Moderate"
            }
        ],
        "Work & Professional Behavior": [
            {
                "title": "Morning Priority Ritual",
                "description": "Write down 3 Most Important Tasks (MITs) first thing in the morning.",
                "why": "Starting with clarity increases reliability & consistency.",
                "effort": "🟢 Easy"
            },
            {
                "title": "Ask One Question Rule",
                "description": "Ask 1 thoughtful question in a meeting or to a peer daily.",
                "why": "Positions you as curious, proactive, and engaged.",
                "effort": "🟡 Moderate"
            }
        ],
        "Emotional & Social Competence": [
            {
                "title": "Mirror Pep Talk",
                "description": "Say 1 positive line to yourself every morning ('I can solve harder problems today than yesterday').",
                "why": "Boosts self-belief before the day begins.",
                "effort": "🟢 Easy"
            },
            {
                "title": "One Compliment a Day",
                "description": "Give 1 sincere compliment to a colleague or peer.",
                "why": "Strengthens social bonds effortlessly.",
                "effort": "🟢 Easy"
            }
        ],
        "Mindset & Reflection": [
            {
                "title": "The 'Why Not Me?' Question",
                "description": "Before starting any task, ask yourself 'If others can grow fast, why not me?'.",
                "why": "Triggers immediate motivation and action bias.",
                "effort": "🟢 Easy"
            },
            {
                "title": "What Did I Learn Today? Note",
                "description": "Write 1 line daily about something you learned today.",
                "why": "Creates awareness of daily growth & builds a habit of reflection.",
                "effort": "🟢 Easy"
            }
        ]
    }

    selected_actions = []
    categories = list(IMMEDIATE_ACTIONS.keys())
    random.shuffle(categories)

    for category in categories:
        if len(selected_actions) >= 3:
            break
        available = [a for a in IMMEDIATE_ACTIONS[category] if a not in selected_actions]
        if available:
            selected_actions.append(random.choice(available))

    if len(selected_actions) < 3:
        all_actions = [a for group in IMMEDIATE_ACTIONS.values() for a in group]
        selected_actions.extend(random.sample(all_actions, 3 - len(selected_actions)))

        
    for action in selected_actions:
        formatted_actions.append({
            "name": action["title"],  # Map title -> name
            "description": action["description"],
            "link": None  
        })
    return {"momentum_toolkit": formatted_actions}

class GrowthOpportunitiesRequest(BaseModel):
    user_profile: UserProfile
    scores: Dict[str, float]
    benchmarks: Dict[str, float]

from prompts.growth_opportunities import (
    GROWTH_OPPORTUNITIES_PROMPT,
    GROWTH_OPPORTUNITIES_SYSTEM_PROMPT,
)
@app.post("/generate_growth_opportunities")
def generate_growth_opportunities(req: GrowthOpportunitiesRequest):
    """
    Generate 3–4 personalized growth opportunities using Groq
    """
    score_benchmarks = "\n".join(
        f"- {cat}: {req.scores.get(cat, 0):.1f} (Benchmark: {req.benchmarks.get(cat, 0)})"
        for cat in req.scores
    )
    prompt = GROWTH_OPPORTUNITIES_PROMPT.format(
        name=req.user_profile.name,
        domain=req.user_profile.domain,
        career_goal=req.user_profile.career_goal,
        exp_level=req.user_profile.exp_level,
        score_benchmarks=score_benchmarks,
    )


    fallback = {
        "opportunities": [
            {
                "category": "Workplace Strategy",
                "opportunity": "Take initiative to lead a mini-project in your domain.",
                "why": "Leadership experience early on aligns with your goal and showcases initiative."
            },
            {
                "category": "Technical Proficiency",
                "opportunity": "Enroll in an advanced-level online course relevant to your domain.",
                "why": "Strengthens technical depth and bridges minor gaps from benchmarks."
            },
            {
                "category": "Professional Branding",
                "opportunity": "Publish one insight or learning weekly on LinkedIn.",
                "why": "Builds visibility and credibility in your domain of interest."
            }
        ]
    }

    try:
        prased,raw_text = llm_services.generate(
            prompt = prompt,
            system_message =  GROWTH_OPPORTUNITIES_SYSTEM_PROMPT,
            client = 2,
            max_tokens = 1000,
        )
        print("Raw Groq response:", raw_text)

        if "opportunities" not in prased:
            raise ValueError("Missing 'opportunities' key")

        return prased

    except Exception as e:
        print(f"[ERROR] Growth opportunity generation failed: {str(e)}")
        return fallback

class MentorInsightsRequest(BaseModel):
    user_data: UserProfile
    mcq_scores: Dict[str, float]
    open_scores: Dict[str, float]
    benchmarks: Dict[str, float]
    categories: List[str] = []


from prompts.mentor_insights import (
    MENTOR_INSIGHTS_PROMPT,
    MENTOR_INSIGHTS_SYSTEM_PROMPT,
)
@app.post("/generate_mentor_insights")
def generate_mentor_insights(req: MentorInsightsRequest):
    """Generate mentor insights for each skill category based on scores vs benchmark"""

    insights = {}

    for category in req.categories:
        user_score = (req.mcq_scores.get(category, 0) * 0.7) + (req.open_scores.get(category, 0) * 0.3)
        benchmark = req.benchmarks.get(category, 0)
        performance = "Above benchmark" if user_score >= benchmark else "Below benchmark"

        prompt = MENTOR_INSIGHTS_PROMPT.format(
            domain=req.user_data.domain,
            career_goal=req.user_data.career_goal,
            exp_level=req.user_data.exp_level,
            category=category,
            user_score=user_score,
            benchmark=benchmark,
            performance=performance,
        )
        try:
            prased,raw = llm_services.generate(
                prompt = prompt,
                system_message=MENTOR_INSIGHTS_SYSTEM_PROMPT,
                client=3,
                max_tokens=800,

            )
            print(f"Raw Grpq response for {category}" ,raw)

        except Exception as e:
            print(f"[ERROR] Mentor insight fallback for {category}: {str(e)}")
            insights[category] = {
                "mentor_insight": f"💬 Focus on improving your {category} skills",
                "score_context": f"🎯 Your score: {user_score:.1f}% | Benchmark: {benchmark}%",
                "immediate_step": f"✅ Take one step in {category} today",
                "weekly_focus": f"📆 Spend 2–3 hrs this week building this skill",
                "career_impact": f"📈 Strength in this area supports your goal: {req.user_data.career_goal}",
                "encouragement": f"✨ Progress is built step by step!"
            }

    return {"mentor_insights": insights}


# ============================================================
# Assessment Summary / Reflection Summary / Career Recommendations
# ============================================================

class AssessmentSummaryRequest(BaseModel):
    user_profile: UserProfile
    category_scores: Dict[str, float] = {}
    open_ended_answers: List[OpenEndedAnswer] = []
    overall_score: float = 0
    performance_level: str = ""
    strongest_skill: str = ""

from prompts.assessment_summary import (
    ASSESSMENT_SUMMARY_PROMPT,
    ASSESSMENT_SUMMARY_SYSTEM_PROMPT,
)
@app.post("/generate_assessment_summary")
def generate_assessment_summary(req: AssessmentSummaryRequest):
    """Generate a 180-250 word professional assessment summary using Groq/Llama."""

    scores_block = "\n".join(
        [f"- {cat}: {score:.1f}/100" for cat, score in req.category_scores.items()]
    ) or "No category scores available."

    answers_block = "\n\n".join(
        [f"Q: {a.question}\nA: {a.answer}" for a in req.open_ended_answers]
    ) or "No open-ended responses provided."

    student_name = req.user_profile.name or "The student"


    prompt = ASSESSMENT_SUMMARY_PROMPT.format(
        name=req.user_profile.name,
        age=req.user_profile.age,
        education_level=req.user_profile.education_level,
        field=req.user_profile.field,
        career_goal=req.user_profile.career_goal,
        overall_score=req.overall_score,
        performance_level=req.performance_level,
        strongest_skill=req.strongest_skill,
        scores_block=scores_block,
        answers_block=answers_block,
        student_name=student_name,
    )

    fallback = {
        "assessment_summary": (
            f"{student_name} demonstrates a {req.performance_level.lower() if req.performance_level else 'developing'} "
            f"overall performance in this assessment, with particular strength in {req.strongest_skill or 'multiple areas'}. "
            "Their responses reflect a thoughtful, curious personality with genuine interest in learning and "
            "self-improvement. They show solid analytical and problem-solving ability alongside a collaborative "
            "approach to challenges, and they engage sincerely with open-ended questions rather than giving "
            "surface-level answers. Areas for growth include building greater consistency across skill categories "
            "and developing more structured approaches to complex or ambiguous tasks. Their learning style leans "
            "toward practical, experience-based engagement over purely theoretical study, and they communicate "
            "ideas clearly, though there is room to build more confidence when articulating complex or nuanced "
            "thoughts. Motivation appears largely intrinsic, driven by curiosity and a desire for mastery rather "
            "than external validation, which positions them well for sustained growth with focused effort, "
            "consistent practice, and the right guidance and mentorship along the way."
        )
    }

    try:
        json_data,raw_text = llm_services.generate(
            prompt = prompt,
            system_message = ASSESSMENT_SUMMARY_SYSTEM_PROMPT,
            client = 1,
            max_tokens = 800,
        )
        print("raw grpq assesment summary response:", raw_text)
        if not json_data.get("assessment_summary", "").strip():
            raise ValueError("Missing or empty 'assessment_summary' key")

        return json_data

    except Exception as e:
        print(f"[ERROR] Assessment summary generation failed: {str(e)}")
        return fallback


class ReflectionSummaryRequest(BaseModel):
    user_profile: UserProfile
    open_ended_answers: List[OpenEndedAnswer] = []

from prompts.reflection_summary import (
    REFLECTION_SUMMARY_PROMPT,
    REFLECTION_SUMMARY_SYSTEM_PROMPT,
)
@app.post("/generate_reflection_summary")
def generate_reflection_summary(req: ReflectionSummaryRequest):
    """Summarize the student's open-ended reflections into themes, interests, values, aspirations and traits."""

    if not req.open_ended_answers:
        return {"reflection_summary": "No open-ended responses were submitted for reflection."}

    answers_block = "\n\n".join(
        [f"Q{i + 1}: {a.question}\nA{i + 1}: {a.answer}" for i, a in enumerate(req.open_ended_answers)]
    )

    prompt = REFLECTION_SUMMARY_PROMPT.format(
        name=req.user_profile.name,
        age=req.user_profile.age,
        field=req.user_profile.field,
        career_goal=req.user_profile.career_goal,
        answers_block=answers_block,
    )


    fallback = {
        "reflection_summary": (
            "Across their responses, the student shows consistent curiosity about how things work and a "
            "preference for hands-on problem-solving over purely theoretical thinking. Recurring themes "
            "include a value for honesty, teamwork, and personal growth, alongside a quiet ambition to build "
            "a meaningful, purpose-driven career. Their tone suggests a reflective, empathetic personality "
            "that stays thoughtful under pressure and remains genuinely open to learning from experience "
            "and feedback from others."
        )
    }

    try:
        json_data,raw_text = llm_services.generate(
            prompt=prompt,
            system_message=REFLECTION_SUMMARY_SYSTEM_PROMPT,
            max_tokens=600,
        )

        print("Raw Groq reflection summary response:", raw_text)

        if not json_data.get("reflection_summary", "").strip():
            raise ValueError("Missing or empty 'reflection_summary' key")

        return json_data

    except Exception as e:
        print(f"[ERROR] Reflection summary generation failed: {str(e)}")
        return fallback


class CareerRecommendationsRequest(BaseModel):
    user_profile: UserProfile
    category_scores: Dict[str, float] = {}
    reflection_summary: str = ""
    strong_categories: List[str] = []
    weak_categories: List[str] = []

from prompts.career_recommendation import(
    CAREER_RECOMMENDATION_SYSTEM_PROMPT,
    CAREER_RECOMMENDATION_PROMPT,
)
@app.post("/generate_career_recommendations")
def generate_career_recommendations(req: CareerRecommendationsRequest):
    """Generate recommended academic streams and career domains from scores + reflection summary."""

    scores_block = "\n".join(
        [f"- {cat}: {score:.1f}/100" for cat, score in req.category_scores.items()]
    ) or "No category scores available."


    prompt = CAREER_RECOMMENDATION_PROMPT.format(
        name=req.user_profile.name,
        age=req.user_profile.age,
        education_level=req.user_profile.education_level,
        field=req.user_profile.field,
        career_goal=req.user_profile.career_goal,
        scores_block=scores_block,
        strong_categories=", ".join(req.strong_categories) or "None identified",
        weak_categories=", ".join(req.weak_categories) or "None identified",
        reflection_summary=req.reflection_summary or "Not available",
    )

    

    fallback = {
        "streams": [
            {
                "name": "Science (PCM/PCB)",
                "explanation": "Solid analytical and problem-solving scores support a strong foundation for a science-based academic track."
            }
        ],
        "careers": [
            {
                "name": "Technology & Engineering",
                "explanation": "Cognitive and digital orientation scores align well with technology-driven, problem-solving careers."
            },
            {
                "name": "Business & Management",
                "explanation": "A balance of communication and values-driven scores suggests strong potential in people-facing, leadership roles."
            }
        ]
    }

    try:
        json_data, raw_text = llm_services.generate(
            prompt=prompt,
            system_message=CAREER_RECOMMENDATION_SYSTEM_PROMPT,
            client=4,
            max_tokens=1000,
        )

        print("Raw Groq career recommendations response:", raw_text)

        if "streams" not in json_data or "careers" not in json_data:
            raise ValueError("Missing 'streams' or 'careers' key")

        return json_data

    except Exception as e:
        print(f"[ERROR] Career recommendations generation failed: {str(e)}")
        return fallback