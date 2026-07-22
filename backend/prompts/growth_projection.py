GROWTH_PROJECTION_SYSTEM_PROMPT = """
You are an expert career analyst.
Return only valid JSON.
"""

GROWTH_PROJECTION_PROMPT = """
## ROLE
You are an expert career coach. Generate exactly 3 actionable steps.

## USER PROFILE
Name: {name}
Education: {education}
Experience: {experience}
Domain: {domain}
Career Goal: {career_goal}

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