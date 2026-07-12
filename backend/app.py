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


load_dotenv() 

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
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
groq_client_2 = Groq(api_key=os.getenv("GROQ_API_KEY_2"))
groq_client_3 = Groq(api_key=os.getenv("GROQ_API_KEY_3"))
groq_client_4 = Groq(api_key=os.getenv("GROQ_API_KEY_4"))

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

@app.post("/generate_open_ended_questions")
def generate_open_ended_questions(req: OpenEndedRequest):
    prompt = f"""
You are an expert skill assessor tasked with generating 1 personalized open-ended question that covers the following 5 core skill categories:

1. Cognitive & Creative Skills  
2. Work & Professional Behavior  
3. Emotional & Social Competence  
4. Personal Management & Wellness  
5. Family & Relationships

Instructions:
- Use the user's profile and their MCQ performance to generate *1 diverse, personalized, open-ended question* that covers all 5 categories collectively (at least once per category ).
- The question should be mapped to a *primary category* and optionally *secondary categories*.
- Prioritize weaker-scoring categories from the MCQs when assigning primary categories.
- Question should be clear, real-world oriented, and require a reflective response.

User Profile:
- Age: {req.user_profile.age}
- Education Level: {req.user_profile.education_level}
- Field of Study/Profession: {req.user_profile.field}
- Interests: {', '.join(req.user_profile.interests)}
- Aspirations: {req.user_profile.career_goal}
              
MCQ Scores by Category (0–100):
{{
  "Subject Interest & Domain Curiosity": {req.mcq_scores.Subject_Interest_Domain_Curiosity},
  "Cognitive & Creative Skills": {req.mcq_scores.Cognitive_and_Creative_Skills},
  "Academic Aptitude & Learning Style": {req.mcq_scores.Academic_Aptitude_Learning_Style},
  "Digital & Technological Orientation": {req.mcq_scores.Digital_Technological_Orientation},
  "Values & Lifestyle Priorities": {req.mcq_scores.Values_Lifestyle_Priorities},
  "Financial Awareness & Constraints": {req.mcq_scores.Financial_Awareness_Constraints},
  "Risk Appetite & Ambiguity Tolerance": {req.mcq_scores.Risk_Appetite_Ambiguity_Tolerance},
  "Emotional & Social Competence": {req.mcq_scores.Emotional_and_Social_Competence},
  "Communication & Language Preference": {req.mcq_scores.Communication_Language_Preference},
  "Personal Management & Wellness": {req.mcq_scores.Personal_Management_Wellness}
}}

Return ONLY in the following JSON format:
{{
  "questions": [
    {{
      "question": "Describe a time you had to resolve a misunderstanding with a family member.",
      "primary_category": "Family & Relationships",
      "secondary_categories": ["Emotional & Social Competence"]
    }}
  ]
}}
Only return valid JSON. Do not include anything else.
    """
    try:
        
        response = groq_client_3.chat.completions.create(
            model="openai/gpt-oss-120b", 
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert skill assessor. Return only valid JSON responses without any additional text or formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            stream=False,
            stop=None
        )
        
        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq response:", raw_text)

       
        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()

       
        json_data = json.loads(clean_text)

        if "questions" not in json_data:
            raise HTTPException(status_code=500, detail="Response missing 'questions' key")

        return json_data 

    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Raw response: {raw_text}")
        raise HTTPException(status_code=500, detail="Failed to parse JSON from Groq API response")
    except Exception as e:
        print(f"Groq API error: {e}")
        raise HTTPException(status_code=500, detail=f"Groq API error: {e}")
    

def make_groq_request(prompt: str, system_message: str = "You are a helpful AI assistant. Return only valid JSON responses without any additional text or formatting.", max_tokens: int = 1500, temperature: float = 0.7):
    """Helper function to make Groq API requests with consistent error handling"""
    try:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            stream=False,
            stop=None
        )
        
        raw_text = response.choices[0].message.content.strip()
        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        return json.loads(clean_text), raw_text
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse JSON from Groq API response")
    except Exception as e:
        print(f"Groq API error: {e}")
        raise HTTPException(status_code=500, detail=f"Groq API error: {e}")
    

def make_groq_request_2(prompt: str, system_message: str = "You are a helpful AI assistant. Return only valid JSON responses without any additional text or formatting.", max_tokens: int = 1500, temperature: float = 0.7):
    """Helper function to make Groq API requests with consistent error handling"""
    try:
        response = groq_client_2.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=1,
            stream=False,
            stop=None
        )
        
        raw_text = response.choices[0].message.content.strip()
        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        return json.loads(clean_text), raw_text
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse JSON from Groq API response")
    except Exception as e:
        print(f"Groq API error: {e}")
        raise HTTPException(status_code=500, detail=f"Groq API error: {e}")


class OpenEndedAnswer(BaseModel):
    question: str
    answer: str
    categories: List[str]

class ScoreOpenEndedRequest(BaseModel):
    user_profile: UserProfile
    answers: List[OpenEndedAnswer]

@app.post("/score_open_ended_responses")
def score_open_ended_responses(req: ScoreOpenEndedRequest):
    all_scores = []
    clients = [groq_client, groq_client_2, groq_client_3]

    for idx, q in enumerate(req.answers):
        prompt = f"""Score this open-ended answer for the listed skill categories.

User: Age {req.user_profile.age}, {req.user_profile.education_level}, {req.user_profile.field}, Goal: {req.user_profile.career_goal}

Question {idx+1}: {q.question}
Answer: {q.answer}
Categories to score: {', '.join(q.categories) if q.categories else "Subject Interest & Domain Curiosity, Cognitive & Creative Skills, Academic Aptitude & Learning Style, Digital & Technological Orientation, Values & Lifestyle Priorities, Financial Awareness & Constraints, Risk Appetite & Ambiguity Tolerance, Emotional & Social Competence, Communication & Language Preference, Personal Management & Wellness"}

For each category assign a score 0-100 and a 1-line justification.
Return ONLY valid JSON:
{{
  "scores": [
    {{"question": {idx+1}, "category": "Category Name", "score": 75, "justification": "Reason."}}
  ]
}}"""

        try:
            client = clients[idx % len(clients)]
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a skill evaluator. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                top_p=1,
                stream=False,
                stop=None
            )
            raw = response.choices[0].message.content.strip()
            clean = re.sub(r"^```json\s*|```$", "", raw, flags=re.DOTALL).strip()
            data = json.loads(clean)
            all_scores.extend(data.get("scores", []))

        except Exception as e:
            print(f"Groq error on question {idx+1}: {e}")
            raise HTTPException(status_code=500, detail=f"Groq API error on Q{idx+1}: {e}")

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


@app.post("/generate_tooltips")
def generate_tooltip(req: TooltipRequest):
    prompt = f"""
As a career advisor AI, generate a single personalized tooltip for a skill category comparison.

[User Profile]
Education: {req.user_profile.education_level}
Experience: Not specified
Domain: {req.user_profile.field}
Career Goal: {req.user_profile.career_goal}

[Skill Category]
{req.category}:
- Your Score: {req.user_score:.1f}%
- Benchmark: {req.benchmark_score}%

Instructions:
1. Create only ONE tooltip (max 30 words).
2. Acknowledge current performance.
3. Provide constructive feedback.
4. Use an encouraging and motivational tone.

Return in JSON format:
{{
    "user_tooltip": "Your personalized feedback..."
}}
"""

    try:
        json_data, raw_text = make_groq_request(
            prompt,
            "You are a career advisor AI. Return only valid JSON responses without any additional text or formatting."
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

   
    prompt = f"""
## ROLE
You are an expert career coach. Generate exactly 3 actionable steps.

## USER PROFILE
Name: {req.user_data.name}
Education: {req.user_data.education_level}
Experience: {req.user_data.exp_level}
Domain: {req.user_data.domain}
Career Goal: {req.user_data.career_goal}

## RULES
- Max 15 words per step
- Measurable, specific, and relevant to the domain
- Use strong action verbs
- Return only valid JSON:
{{
  "action_steps": [
    "Step 1 here",
    "Step 2 here",
    "Step 3 here"
  ]
}}
"""

    try:
        json_data, raw_text = make_groq_request_2(
            prompt,
            "You are an expert career analyst. Return only valid JSON.",
            max_tokens=300
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

    # Prompt for Groq
    MARKET_ANALYSIS_PROMPT = f"""
As a senior AI career strategist, generate an honest, constructive market position analysis.

[User Profile]
- Name: {user_data.get("name", "User")}
- Education: {user_data.get("education", "Not specified")}
- Experience Level: {user_data.get("exp_level", "Not specified")}
- Domain: {user_data.get("domain", "Not specified")}
- Career Goal: {user_data.get("career_goal", "Not specified")}

[Assessment Results]
- Combined Score: {score:.1f}/100
- Career Tier: {tier}
- Market Percentile: {percentile:.1f}%
- Strengths: {', '.join(strengths) if strengths else 'None'}
- Weaknesses: {', '.join(weaknesses) if weaknesses else 'None'}

[Market Benchmarks]
{', '.join([f"{cat}: {val}%" for cat, val in benchmark_scores.items()])}

### INSTRUCTIONS
1. Return each section as 1–2 short bullet points.
2. Tone: supportive but *realistic* and *frank* — don't overhype low scores.
3. If the percentile is low, acknowledge it directly and suggest improvement.
4. Be second-person (e.g., "You have shown…"). Avoid long paragraphs.
5. Label the tier, experience, salary, and give overall feedback.

### OUTPUT JSON FORMAT:
{{
  "tier": {{
    "label": "{tier}",
    "bullets": ["...", "...", "..."]
  }},
  "experience": {{
    "label": "Estimated experience range",
    "bullets": ["...", "..."]
  }},
  "salary": {{
    "label": "Expected salary range",
    "bullets": ["...", "..."]
  }}
}}
"""

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
        response = groq_client_3.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a senior AI career strategist. Return only valid JSON responses without any additional text or formatting."},
                {"role": "user", "content": MARKET_ANALYSIS_PROMPT}
            ],
            temperature=0.7, max_tokens=2000, top_p=1, stream=False, stop=None
        )
        raw_text = response.choices[0].message.content.strip()
        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        json_data = json.loads(clean_text)
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

@app.post("/generate_peer_benchmark")
def generate_peer_benchmark(req: PeerBenchmarkRequest):
    """Generate peer benchmark and in-demand traits analysis report using groq_client_2"""

    prompt = f"""
## ROLE
You are acting as a **career market intelligence analyst** for a skill-assessment platform.  
Your goal: Generate **highly personalized, market-aligned insights** that compare the user's performance to peers and map their skills to in-demand industry traits.

---

## CONTEXT
- Name: {req.user_data.name}
- Domain: {req.user_data.domain}
- Career Goal: {req.user_data.career_goal}
- Experience Level: {req.user_data.exp_level}
- Combined Score: {req.combined_score:.1f}/100
- MCQ Scores: {json.dumps(req.mcq_scores)}
- Open-Ended Scores: {json.dumps(req.open_scores)}
- Strong Categories: {', '.join(req.strong_categories) or 'None'}
- Weak Categories: {', '.join(req.weak_categories) or 'None'}
- Benchmarks: {json.dumps(req.benchmarks)}

---

1. **Percentile Positioning**  
   - Predict the user's skill percentile vs. peers in the same **domain & career goal** (e.g., "Top 72% among final-year AI engineering students").  
   - Justify percentile using **peer performance trends or aggregated test-taker data**.

2. **Peer Benchmark Narrative**  
   - Write **1 engaging sentence** comparing the user to typical peers, highlighting both competitive edges and gaps.

3. **In-Demand Traits Mapping**  
   - Map **2 in-demand traits** (from current job market, internships, or hiring trends) to the user's strongest/weakest areas.  
   - Be **specific** (e.g., "Your high score in Work Behavior aligns with demand for reliable agile team contributors").

Return ONLY valid JSON in this format:
{{
  "peer_benchmark": {{
    "percentile": "Top 72% among peers in {req.user_data.domain}",
    "narrative": "Your performance outpaces many peers in problem-solving, but lags in communication skills.",
    "in_demand_traits": [
      "Strong analytical thinking aligns with current hiring demand for data-driven roles",
      "Moderate teamwork scores limit opportunities in agile-based internships"
    ]
  }}
}}
"""

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
        response = groq_client_4.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert skill assessor. Return only valid JSON responses without any additional text or formatting."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            stream=False
        )

        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq peer benchmark response:", raw_text)

        # Clean markdown JSON fences if present
        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()

        json_data = json.loads(clean_text)

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
    prompt = f"""
## ROLE  
You are a **personalized career coach and skill strategist**.  
Your task: **Design a hyper-personalized, practical 90-day career development roadmap** for a professional, based entirely on their **scores, benchmark gaps, and profile**.

---

## CONTEXT – User Data  
Name: {req.user_data.name}  
Education: {req.user_data.education_level}  
Experience Level: {req.user_data.exp_level}  
Professional Domain: {req.user_data.domain}  
Career Goal: {req.user_data.career_goal}  

Current Overall Score: {current_avg:.1f}  
Category-wise Scores vs Market Benchmarks:  
{chr(10).join([
    f"- {cat}: {combined_scores.get(cat, 0)} vs {req.market_benchmarks.get(cat, 'N/A')}"
    for cat in combined_scores
])}

Strong Categories: {', '.join(req.strong_categories) or 'None'}  
Moderate Categories: {', '.join(req.moderate_categories) or 'None'}  
Weak Categories: {', '.join(req.weak_categories) or 'None'}  

---

## TASK – 90-Day Roadmap Only  

✅ **STRICTLY output ONLY a 3-phase roadmap** (no ROI narrative, no extra sections).  
✅ **Make it feel like a website-style career roadmap** → clean, simple, motivational.  
✅ **Be extremely personalized**: Mention the user's domain, role, and specific skill gaps.  
✅ **Use bullet points, short sentences, and practical weekly steps.**  
✅ **Include measurable progress milestones.**  

---

### **OUTPUT FORMAT (STRICT)**

90-DAY PERSONALIZED ROADMAP

### PHASE 1 (0–30 Days) – [Motivational Title]
- **Focus Areas:** [Specific weak categories & why (personalized)]
- **Weekly Actions:**
  - Week 1: [Specific step]
  - Week 2: [Step]
  - Week 3: [...]
  - Week 4: [...]
- **Milestone by Day 30:** [Score target or tangible skill achievement]

### PHASE 2 (31–60 Days) – [Motivational Title]
- **Focus Areas:** [Moderate skill clusters, why they matter for career goal]
- **Weekly Actions:**
  - Week 5: [...]
  - Week 6: [...]
  - Week 7: [...]
  - Week 8: [...]
- **Milestone by Day 60:** [Clear achievement]

### PHASE 3 (61–90 Days) – [Motivational Title]
- **Focus Areas:** [Strong categories → leadership & visibility, very role-specific]
- **Weekly Actions:**
  - Week 9: [...]
  - Week 10: [...]
  - Week 11: [...]
  - Week 12: [...]
- **Milestone by Day 90:** [E.g., "Score crosses 75%+, ready for mid-level role"]

---

## STYLE RULES
- Be **personal, encouraging, and clear** (like talking directly to the user).
- Avoid paragraphs – keep it **structured and scannable**.
- **DO NOT** generate generic career roadmaps found online – strictly use **this user's data**.
- No extra ROI text, no reporting metrics – **ONLY the roadmap**.
"""

    try:
        
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a personalized career coach and skill strategist. Generate detailed, practical career roadmaps based on user data."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=2500,
            top_p=1,
            stream=False,
            stop=None
        )
        
        roadmap_text = response.choices[0].message.content.strip()
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

@app.post("/generate_growth_opportunities")
def generate_growth_opportunities(req: GrowthOpportunitiesRequest):
    """
    Generate 3–4 personalized growth opportunities using Groq
    """
    prompt = f"""
## ROLE
You are a career development strategist. Generate 3-4 personalized growth opportunities.

## USER PROFILE
Name: {req.user_profile.name}
Domain: {req.user_profile.domain}
Career Goal: {req.user_profile.career_goal}
Experience Level: {req.user_profile.exp_level}

## SKILL SCORES vs BENCHMARKS
{chr(10).join([f"- {cat}: {req.scores.get(cat, 0):.1f} (Benchmark: {req.benchmarks.get(cat, 0)})" for cat in req.scores])}

## TASK
- Generate 3-4 growth opportunities that leverage strengths and moderate skills
- Focus on future-focused career advancement
- Make each opportunity specific and actionable
- Include why it's recommended based on their profile

## OUTPUT FORMAT (JSON)
{{
  "opportunities": [
    {{
      "category": "Category Name",
      "opportunity": "Description of opportunity",
      "why": "Reason why recommended"
    }},
    ...
  ]
}}
"""

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
        response = groq_client_2.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are an expert skill assessor. Return only valid JSON responses without any additional text or formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            stream=False
        )

        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq response:", raw_text)

        clean = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        parsed = json.loads(clean)

        if "opportunities" not in parsed:
            raise ValueError("Missing 'opportunities' key")

        return parsed

    except Exception as e:
        print(f"[ERROR] Growth opportunity generation failed: {str(e)}")
        return fallback

class MentorInsightsRequest(BaseModel):
    user_data: UserProfile
    mcq_scores: Dict[str, float]
    open_scores: Dict[str, float]
    benchmarks: Dict[str, float]
    categories: List[str] = []

@app.post("/generate_mentor_insights")
def generate_mentor_insights(req: MentorInsightsRequest):
    """Generate mentor insights for each skill category based on scores vs benchmark"""

    insights = {}

    for category in req.categories:
        user_score = (req.mcq_scores.get(category, 0) * 0.7) + (req.open_scores.get(category, 0) * 0.3)
        benchmark = req.benchmarks.get(category, 0)
        performance = "Above benchmark" if user_score >= benchmark else "Below benchmark"

        prompt = f"""
## ROLE
You are a senior career mentor for {req.user_data.domain}.
Generate personalized, actionable insights for this specific skill category.

## USER PROFILE
Career Goal: {req.user_data.career_goal}
Experience Level: {req.user_data.exp_level}
Domain: {req.user_data.domain}

## SKILL ASSESSMENT
Category: {category}
- Your Score: {user_score:.1f}%
- Benchmark: {benchmark}%
- Performance: {performance}

## TASK
Generate personalized insights in this EXACT JSON format without any additional text:
{{
  "mentor_insight": "💬 1-sentence personalized insight",
  "score_context": "🎯 Score context",
  "immediate_step": "✅ 1 specific action step",
  "weekly_focus": "📆 1 weekly focus area",
  "career_impact": "📈 Career impact statement",
  "encouragement": "✨ Encouraging tagline"
}}

## RULES
- Be specific to {category} and {req.user_data.career_goal}
- Be simple, actionable, and concise
- Start each field with the specified emoji
- Keep each field under 20 words
"""

        try:
            response = groq_client_3.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are an expert skill assessor. Return only valid JSON responses without any additional text or formatting."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                top_p=1,
                stream=False
            )

            raw = response.choices[0].message.content.strip()
            print(f"Raw Groq response for {category}:", raw)

            clean = re.sub(r"^```json\s*|```$", "", raw, flags=re.DOTALL).strip()
            parsed = json.loads(clean)

            if not all(k in parsed for k in [
                "mentor_insight", "score_context", "immediate_step",
                "weekly_focus", "career_impact", "encouragement"
            ]):
                raise ValueError("Incomplete insight JSON")
            
            insights[category] = parsed

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

    prompt = f"""
## ROLE
You are a senior educational psychologist and career assessor writing the "Assessment Summary"
section of a student's professional skill-assessment report.

## USER PROFILE
Name: {req.user_profile.name}
Age: {req.user_profile.age}
Education Level: {req.user_profile.education_level}
Field of Study: {req.user_profile.field}
Career Goal: {req.user_profile.career_goal}

## ASSESSMENT RESULTS
Overall Score: {req.overall_score:.1f}/100
Performance Level: {req.performance_level}
Strongest Skill: {req.strongest_skill}

## SKILL CATEGORY SCORES
{scores_block}

## OPEN-ENDED RESPONSES
{answers_block}

## TASK
Write ONE cohesive, professional assessment summary that naturally weaves in ALL of the following:
1. Overall personality
2. Strengths
3. Areas for improvement
4. Learning style
5. Communication style
6. Motivation

## RULES
- Length MUST be between 180 and 250 words.
- Write in flowing paragraphs (2-4 paragraphs). Do NOT use bullet points or headers.
- Tone: professional, evidence-based, and encouraging - never generic or overhyped.
- Ground every statement in the scores and responses given above; do not invent facts.
- Refer to the student as "{student_name}" once near the start, and "they/their" thereafter.

## OUTPUT FORMAT
Return ONLY valid JSON, no extra text:
{{
  "assessment_summary": "The full 180-250 word summary text here."
}}
"""

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
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educational psychologist and career assessor. Return only valid JSON responses without any additional text or formatting."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
            top_p=1,
            stream=False,
            stop=None
        )

        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq assessment summary response:", raw_text)

        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        json_data = json.loads(clean_text)

        if not json_data.get("assessment_summary", "").strip():
            raise ValueError("Missing or empty 'assessment_summary' key")

        return json_data

    except Exception as e:
        print(f"[ERROR] Assessment summary generation failed: {str(e)}")
        return fallback


class ReflectionSummaryRequest(BaseModel):
    user_profile: UserProfile
    open_ended_answers: List[OpenEndedAnswer] = []


@app.post("/generate_reflection_summary")
def generate_reflection_summary(req: ReflectionSummaryRequest):
    """Summarize the student's open-ended reflections into themes, interests, values, aspirations and traits."""

    if not req.open_ended_answers:
        return {"reflection_summary": "No open-ended responses were submitted for reflection."}

    answers_block = "\n\n".join(
        [f"Q{i + 1}: {a.question}\nA{i + 1}: {a.answer}" for i, a in enumerate(req.open_ended_answers)]
    )

    prompt = f"""
## ROLE
You are an expert career counselor skilled at reading between the lines of a student's own words.

## USER PROFILE
Name: {req.user_profile.name}
Age: {req.user_profile.age}
Field: {req.user_profile.field}
Career Goal: {req.user_profile.career_goal}

## STUDENT'S OPEN-ENDED RESPONSES
{answers_block}

## TASK
Write a concise reflection summary (100-150 words) that synthesizes these responses. Do NOT quote
or restate the answers verbatim - paraphrase and synthesize instead. Identify and describe:
- Recurring themes across the responses
- Interests suggested by the responses
- Values that come through
- Aspirations expressed or implied
- Personality traits reflected in how the student thinks and responds

## RULES
- Write in flowing prose (1-2 short paragraphs), not bullet points or headers.
- Speak about the student in third person.
- Be specific and grounded in what was actually said, but always paraphrase rather than quote.

## OUTPUT FORMAT
Return ONLY valid JSON, no extra text:
{{
  "reflection_summary": "The full reflection summary here."
}}
"""

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
        response = groq_client_2.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert career counselor. Return only valid JSON responses without any additional text or formatting."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600,
            top_p=1,
            stream=False,
            stop=None
        )

        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq reflection summary response:", raw_text)

        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        json_data = json.loads(clean_text)

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


@app.post("/generate_career_recommendations")
def generate_career_recommendations(req: CareerRecommendationsRequest):
    """Generate recommended academic streams and career domains from scores + reflection summary."""

    scores_block = "\n".join(
        [f"- {cat}: {score:.1f}/100" for cat, score in req.category_scores.items()]
    ) or "No category scores available."

    prompt = f"""
## ROLE
You are a senior academic and career counselor advising a student on next steps.

## USER PROFILE
Name: {req.user_profile.name}
Age: {req.user_profile.age}
Education Level: {req.user_profile.education_level}
Field of Study: {req.user_profile.field}
Career Goal: {req.user_profile.career_goal}

## SKILL CATEGORY SCORES
{scores_block}

Strong Categories: {', '.join(req.strong_categories) or 'None identified'}
Weak Categories: {', '.join(req.weak_categories) or 'None identified'}

## REFLECTION SUMMARY
{req.reflection_summary or 'Not available'}

## TASK
Based on the profile, scores, and reflection summary above, recommend:
1. 1 to 3 academic streams/majors best suited to this student
2. 2 to 4 career domains/fields best suited to this student

Each recommendation must include a short, specific 1-2 sentence explanation grounded in the
student's actual scores, strengths, or reflection themes - not generic advice.

## OUTPUT FORMAT
Return ONLY valid JSON in this exact format, no extra text:
{{
  "streams": [
    {{"name": "Stream name", "explanation": "Why this stream fits, 1-2 sentences."}}
  ],
  "careers": [
    {{"name": "Career domain name", "explanation": "Why this domain fits, 1-2 sentences."}}
  ]
}}
"""

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
        response = groq_client_4.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior academic and career counselor. Return only valid JSON responses without any additional text or formatting."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
            stream=False,
            stop=None
        )

        raw_text = response.choices[0].message.content.strip()
        print("Raw Groq career recommendations response:", raw_text)

        clean_text = re.sub(r"^```json\s*|```$", "", raw_text, flags=re.DOTALL).strip()
        json_data = json.loads(clean_text)

        if "streams" not in json_data or "careers" not in json_data:
            raise ValueError("Missing 'streams' or 'careers' key")

        return json_data

    except Exception as e:
        print(f"[ERROR] Career recommendations generation failed: {str(e)}")
        return fallback
