SCORE_OPENENDED_RESPONSES_PROMPT = """
Score this open-ended answer for the listed skill categories.

User: Age {age}, {education_level}, {field}, Goal: {career_goal}

Question {question_number}: {question}
Answer: {answer}
Categories to score: {categories}

For each category assign a score 0-100 and a 1-line justification.

Return ONLY valid JSON:

{{ 
  "scores": [
    {{ 
      "question": {question_number},
      "category": "Category Name",
      "score": 75,
      "justification": "Reason."
    }}
  ]
}}
"""

SCORE_OPENENDED_RESPONSES_SYSTEM_PROMPT = """
You are a skill evaluator.
Return only valid JSON.
"""