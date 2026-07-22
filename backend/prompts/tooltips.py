TOOLTIP_SYSTEM_PROMPT = """
You are a career advisor AI.
Return only valid JSON responses without any additional text or formatting.
"""

TOOLTIP_PROMPT = """
As a career advisor AI, generate a single personalized tooltip for a skill category comparison.

[User Profile]
Education: {education_level}
Experience: Not specified
Domain: {field}
Career Goal: {career_goal}

[Skill Category]
{category}:
- Your Score: {user_score:.1f}%
- Benchmark: {benchmark_score}%

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