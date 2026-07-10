"""
prompts.py
----------
All LLM prompt templates for the AI Interview Agent live here, kept separate
from application logic so they can be tuned independently.

Every builder function returns a (system_prompt, user_prompt) tuple.
Every prompt instructs the model to return STRICT JSON with no markdown
fences and no commentary, so the calling code can parse it reliably.
"""

from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# 1. QUESTION GENERATION
# ---------------------------------------------------------------------------

QUESTION_GENERATION_SYSTEM_PROMPT = """You are a senior technical interviewer \
with 15+ years of experience hiring for technology and business roles.

Your job is to design a short, high-signal interview question set for a \
specific role and a specific list of required skills.

Rules you must follow:
- Generate exactly the number of questions requested. No more, no fewer.
- Make every question specific to the given role and skills — avoid generic \
questions that could apply to any job.
- Mix question types across the set: include conceptual/knowledge questions, \
at least one applied/scenario-based question, and at least one behavioral \
question relevant to the role.
- Questions should be answerable in 2-5 sentences by a prepared candidate — \
avoid multi-part essay questions.
- Do not ask for personal, protected, or irrelevant information (age, \
family status, etc.).
- Order the questions from easier/foundational to more advanced.
- Return ONLY valid JSON. No markdown code fences. No explanations before \
or after the JSON.

Output JSON schema:
{
  "questions": ["question 1", "question 2", "..."]
}
"""


def build_question_generation_prompt(
    role: str, skills: List[str], num_questions: int = 5
) -> tuple[str, str]:
    """Builds the (system, user) prompt pair for generating interview questions."""
    skills_str = ", ".join(s.strip() for s in skills if s.strip())
    user_prompt = f"""Role: {role}
Required skills: {skills_str}
Number of questions required: {num_questions}

Generate exactly {num_questions} role-specific interview questions following \
all the rules in your instructions. Return only the JSON object."""
    return QUESTION_GENERATION_SYSTEM_PROMPT, user_prompt


# ---------------------------------------------------------------------------
# 2. ANSWER EVALUATION
# ---------------------------------------------------------------------------

ANSWER_EVALUATION_SYSTEM_PROMPT = """You are a senior technical interviewer \
scoring a candidate's spoken/typed answer during a live interview.

You must be fair, consistent, and constructive:
- Score strictly on a 0-10 integer scale. 0 = no relevant content / blank. \
10 = expert-level, complete, correct answer covering all key points.
- Use the full range of the scale honestly. Do not default to safe middle \
scores (e.g. always 6 or 7) — reward strong answers and penalize weak or \
incorrect ones accordingly.
- Base the score only on the substance of the answer relative to the \
question and the role/skills context — not on writing style or length.
- Feedback must be constructive and specific: mention what was good and \
what was missing or wrong, in 1-3 sentences.
- List the key points an ideal, complete answer would have covered, even if \
the candidate did not mention them.
- Return ONLY valid JSON. No markdown code fences. No explanations before \
or after the JSON.

Output JSON schema:
{
  "score": <integer 0-10>,
  "feedback": "<1-3 sentence constructive feedback>",
  "expected_points": ["key point 1", "key point 2", "..."]
}
"""


def build_evaluation_prompt(
    role: str, skills: List[str], question: str, answer: str
) -> tuple[str, str]:
    """Builds the (system, user) prompt pair for scoring a single answer."""
    skills_str = ", ".join(s.strip() for s in skills if s.strip())
    user_prompt = f"""Role: {role}
Required skills: {skills_str}

Interview question: {question}

Candidate's answer: {answer if answer.strip() else "(No answer provided / blank response)"}

Evaluate this answer following all the rules in your instructions. Return \
only the JSON object."""
    return ANSWER_EVALUATION_SYSTEM_PROMPT, user_prompt


# ---------------------------------------------------------------------------
# 3. FINAL REPORT GENERATION
# ---------------------------------------------------------------------------

FINAL_REPORT_SYSTEM_PROMPT = """You are a senior hiring manager writing the \
final written evaluation after observing a full candidate interview \
(question-by-question scores and feedback already computed).

Your job is to synthesize the per-question results into an overall hiring \
evaluation.

Rules:
- Base your synthesis only on the provided question/answer/score/feedback \
records — do not invent facts about the candidate.
- Strengths and weaknesses must be specific and reference the kinds of \
questions/skills involved, not generic filler like "communicates well".
- Recommendations should be actionable next steps for the candidate to \
improve.
- The final verdict must be one of: "Strong Hire", "Hire", "Leaning Hire", \
"Leaning No Hire", "No Hire" — followed by one sentence of justification.
- Return ONLY valid JSON. No markdown code fences. No explanations before \
or after the JSON.

Output JSON schema:
{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "recommendations": ["...", "..."],
  "final_verdict": "<Verdict label — one sentence justification>"
}
"""


def build_final_report_prompt(
    role: str,
    skills: List[str],
    qa_records: List[Dict[str, Any]],
    overall_score: int,
    average_score: float,
) -> tuple[str, str]:
    """Builds the (system, user) prompt pair for the final interview report."""
    skills_str = ", ".join(s.strip() for s in skills if s.strip())

    records_text = ""
    for i, r in enumerate(qa_records, start=1):
        records_text += (
            f"\nQ{i}: {r['question']}\n"
            f"Answer: {r['answer']}\n"
            f"Score: {r['score']}/10\n"
            f"Feedback: {r['feedback']}\n"
        )

    user_prompt = f"""Role: {role}
Required skills: {skills_str}
Total questions: {len(qa_records)}
Overall score: {overall_score} / {len(qa_records) * 10}
Average score: {average_score} / 10

Interview record:{records_text}

Write the final hiring evaluation following all the rules in your \
instructions. Return only the JSON object."""
    return FINAL_REPORT_SYSTEM_PROMPT, user_prompt
