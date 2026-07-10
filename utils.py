"""
utils.py
--------
Shared helpers: LLM client construction (Groq by default, OpenAI as a drop-in
swap), robust JSON extraction from model output, and simple file I/O for
saving transcripts and reports.
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# LLM PROVIDER / CLIENT
# ---------------------------------------------------------------------------

def get_provider() -> str:
    """Returns the configured LLM provider ('groq' or 'openai')."""
    return os.getenv("LLM_PROVIDER", "groq").strip().lower()


def get_model() -> str:
    """Returns the model name for the active provider."""
    provider = get_provider()
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def get_client():
    """
    Builds and returns an LLM client based on LLM_PROVIDER.

    Both Groq and OpenAI expose an OpenAI-compatible `chat.completions.create`
    interface, which is why swapping providers only requires changing the
    client construction here — nothing in interview.py / evaluator.py needs
    to change.
    """
    provider = get_provider()

    if provider == "groq":
        try:
            from groq import Groq
        except ImportError as exc:
            raise ImportError(
                "The 'groq' package is not installed. Run: pip install groq"
            ) from exc
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is not set. Copy .env.example to .env and add "
                "your key."
            )
        return Groq(api_key=api_key)

    if provider == "openai":
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The 'openai' package is not installed. Run: pip install openai"
            ) from exc
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. Copy .env.example to .env and add "
                "your key."
            )
        return OpenAI(api_key=api_key)

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}'. Use 'groq' or 'openai'."
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.4,
    max_tokens: int = 1200,
    json_mode: bool = True,
) -> str:
    """
    Sends a chat completion request and returns the raw text response.

    Tries JSON response-format mode first (supported by most current Groq /
    OpenAI models). Falls back to a plain completion if the model/provider
    rejects that parameter — extract_json() below is robust enough to handle
    either case.
    """
    client = get_client()
    model = get_model()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    if json_mode:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except Exception:
            # Some models/providers don't support response_format — fall
            # through to a plain call below.
            pass

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# JSON PARSING
# ---------------------------------------------------------------------------

def extract_json(text: str) -> Dict[str, Any]:
    """
    Robustly extracts a JSON object from raw LLM output.

    Handles the common failure modes: markdown code fences, leading/trailing
    commentary, or extra text around the JSON body.
    """
    if not text:
        raise ValueError("Empty response from model — nothing to parse.")

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: grab the first {...} block in the text.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"Could not parse JSON from model output. Raw output (truncated): "
        f"{cleaned[:300]}"
    )


# ---------------------------------------------------------------------------
# FILE I/O
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def save_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def save_transcript(
    role: str,
    skills: List[str],
    qa_records: List[Dict[str, Any]],
    report: Dict[str, Any],
    path: Path,
) -> None:
    """Writes a human-readable full interview transcript to a text file."""
    lines = []
    lines.append("=" * 70)
    lines.append("AI INTERVIEW AGENT — MOCK INTERVIEW TRANSCRIPT")
    lines.append("=" * 70)
    lines.append(f"Generated: {timestamp()}")
    lines.append(f"Role: {role}")
    lines.append(f"Required skills: {', '.join(skills)}")
    lines.append(f"Total questions: {len(qa_records)}")
    lines.append("-" * 70)

    for i, r in enumerate(qa_records, start=1):
        lines.append(f"\nQ{i}: {r['question']}")
        lines.append(f"Candidate's Answer: {r['answer']}")
        lines.append(f"Score: {r['score']}/10")
        lines.append(f"Feedback: {r['feedback']}")
        if r.get("expected_points"):
            lines.append("Expected key points:")
            for p in r["expected_points"]:
                lines.append(f"  - {p}")

    lines.append("\n" + "=" * 70)
    lines.append("FINAL EVALUATION SUMMARY")
    lines.append("=" * 70)
    lines.append(f"Overall score: {report['overall_score']} / {len(qa_records) * 10}")
    lines.append(f"Average score: {report['average_score']} / 10")

    lines.append("\nStrengths:")
    for s in report.get("strengths", []):
        lines.append(f"  - {s}")

    lines.append("\nWeaknesses:")
    for w in report.get("weaknesses", []):
        lines.append(f"  - {w}")

    lines.append("\nRecommendations:")
    for rec in report.get("recommendations", []):
        lines.append(f"  - {rec}")

    lines.append(f"\nFinal verdict: {report.get('final_verdict', 'N/A')}")
    lines.append("=" * 70)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
