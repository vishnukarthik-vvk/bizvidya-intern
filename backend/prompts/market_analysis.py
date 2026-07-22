MARKET_ANALYSIS_SYSTEM_PROMPT = """
You are a senior AI career strategist.
Return only valid JSON responses without any additional text or formatting.
"""

MARKET_ANALYSIS_PROMPT = """
As a senior AI career strategist, generate an honest, constructive market position analysis.

[User Profile]
- Name: {name}
- Education: {education}
- Experience Level: {exp_level}
- Domain: {domain}
- Career Goal: {career_goal}

[Assessment Results]
- Combined Score: {score:.1f}/100
- Career Tier: {tier}
- Market Percentile: {percentile:.1f}%
- Strengths: {strengths}
- Weaknesses: {weaknesses}

[Market Benchmarks]
{benchmark_scores}

### INSTRUCTIONS
1. Return each section as 1–2 short bullet points.
2. Tone: supportive but realistic and frank.
3. If the percentile is low, acknowledge it directly and suggest improvement.
4. Be second-person.
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