"""
Prompt templates for Career Recommendation generation.
"""

CAREER_RECOMMENDATION_SYSTEM_PROMPT = """
You are a senior academic and career counselor.
Return only valid JSON responses without any additional text or formatting.
"""

CAREER_RECOMMENDATION_PROMPT = """
## ROLE
You are a senior academic and career counselor advising a student on next steps.

## USER PROFILE
Name: {name}
Age: {age}
Education Level: {education_level}
Field of Study: {field}
Career Goal: {career_goal}

## SKILL CATEGORY SCORES
{scores_block}

Strong Categories: {strong_categories}
Weak Categories: {weak_categories}

## REFLECTION SUMMARY
{reflection_summary}

## TASK
Based on the profile, scores, and reflection summary above, recommend:

1. One to three academic streams or majors that best fit the student.
2. Two to four career domains that best fit the student.

Each recommendation must include a short, specific explanation (1–2 sentences) that is grounded in the student's scores, strengths, weaknesses, or reflection themes. Avoid generic advice.

## OUTPUT FORMAT

Return ONLY valid JSON in this exact format:

{{
  "streams": [
    {{
      "name": "Stream Name",
      "explanation": "Why this stream fits."
    }}
  ],
  "careers": [
    {{
      "name": "Career Domain",
      "explanation": "Why this career fits."
    }}
  ]
}}
"""

print(CAREER_RECOMMENDATION_SYSTEM_PROMPT)