"""FIXED — bug B3.

The JSON example previously used single braces while the string is passed to
`.format()` in app.py, so every call raised
    KeyError: '\\n  "peer_benchmark"'
before the LLM was ever reached, and the bare `except Exception` returned the
canned fallback to every user.

All literal braces are now doubled. Verified with:
    PEER_BENCHMARK_PROMPT.format(name=..., domain=..., ...)  ->  no exception
"""

PEER_BENCHMARK_SYSTEM_PROMPT = """
You are a career market intelligence analyst.
Return only valid JSON responses without any additional text or formatting.
"""

PEER_BENCHMARK_PROMPT = """
## ROLE
You are acting as a career market intelligence analyst for a skill-assessment platform.

Your goal is to generate highly personalized, market-aligned insights that compare the
user's performance to peers and map their skills to in-demand industry traits.

---

## CONTEXT
- Name: {name}
- Domain: {domain}
- Career Goal: {career_goal}
- Experience Level: {exp_level}
- Combined Score: {combined_score:.1f}/100
- MCQ Scores: {mcq_scores}
- Open-Ended Scores: {open_scores}
- Strong Categories: {strong_categories}
- Weak Categories: {weak_categories}
- Benchmarks: {benchmarks}

---

1. Percentile Positioning
- Estimate the user's skill percentile vs. peers in the same domain and career goal.
- Ground the estimate in the scores and benchmarks above, not in invented survey data.
- Phrase it as an estimate, e.g. "Around the 72nd percentile among peers in {domain}".

2. Peer Benchmark Narrative
- One engaging sentence comparing the user to typical peers, naming both a
  competitive edge and a gap. Use the actual category names given above.

3. In-Demand Traits Mapping
- Map exactly two in-demand traits to the user's strongest and weakest areas.
- Be specific about the kind of role or hiring context each trait matters for.

Return ONLY valid JSON in this exact shape:

{{
  "peer_benchmark": {{
    "percentile": "Around the 72nd percentile among peers in {domain}",
    "narrative": "Your performance outpaces many peers in problem-solving, but lags in communication skills.",
    "in_demand_traits": [
      "Strong analytical thinking aligns with current hiring demand for data-driven roles",
      "Moderate teamwork scores limit opportunities in agile-based internships"
    ]
  }}
}}
"""
