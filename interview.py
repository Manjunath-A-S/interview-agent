"""
interview.py
------------
Handles the "question generation" side of the interview agent: given a role
and required skills, ask the LLM for a set of role-specific questions.
"""

from typing import List

import prompts
from utils import call_llm, extract_json


def generate_questions(
    role: str, skills: List[str], num_questions: int = 5
) -> List[str]:
    """
    Generates `num_questions` role-specific interview questions using the LLM.

    Raises:
        ValueError: if the model output can't be parsed or doesn't contain
        enough questions.
    """
    if not role.strip():
        raise ValueError("Job role must not be empty.")
    if not skills:
        raise ValueError("At least one required skill must be provided.")

    system_prompt, user_prompt = prompts.build_question_generation_prompt(
        role=role, skills=skills, num_questions=num_questions
    )

    raw_output = call_llm(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.6,
        json_mode=True,
    )

    data = extract_json(raw_output)
    questions = data.get("questions", [])

    if not isinstance(questions, list) or len(questions) < num_questions:
        raise ValueError(
            f"Expected {num_questions} questions from the model but got "
            f"{len(questions) if isinstance(questions, list) else 0}. "
            f"Raw output: {raw_output[:300]}"
        )

    # Trim to exactly num_questions and ensure clean strings.
    return [str(q).strip() for q in questions[:num_questions]]
