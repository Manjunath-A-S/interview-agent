# 🎤 AI Interview Agent

Built for the **Rooman AI Challenge — 24-Hour AI Agent Challenge**
(Category 1 — HR & Recruitment: *Interview Agent*).

An AI agent that conducts a structured mock interview: it generates
role-specific questions, asks them one at a time, scores every answer with
constructive feedback, and produces a final hiring evaluation.

---

## 1. Project Overview

**Input:** a job role + a list of required skills.
**Process:** the agent generates 5 role-specific interview questions, asks
them one at a time in a Streamlit UI, scores each typed answer (0-10) with
feedback and expected key points, then synthesizes everything into a final
report.
**Output:** a full transcript (`outputs/transcript.txt`) and a structured
final report (`outputs/interview_report.json`).

> My agent takes a job role + required skills and produces a scored,
> question-by-question mock interview plus a final hiring recommendation.

---

## 2. Features

- ✅ Generates exactly 5 role-specific interview questions from a job role +
  skills input
- ✅ Asks one question at a time (typed answers)
- ✅ Scores every answer 0-10 with constructive feedback + expected key points
- ✅ Produces a final report: overall score, average score, strengths,
  weaknesses, recommendations, and a final hiring verdict
- ✅ JSON-structured LLM outputs throughout, parsed defensively
- ✅ Provider-agnostic: works with **Groq** (default, free tier) or
  **OpenAI** — swap with one `.env` variable
- ✅ Persists every run to `outputs/transcript.txt` and
  `outputs/interview_report.json`, downloadable from the UI

---

## 3. Folder Structure

```
Interview-Agent/
├── app.py                     # Streamlit UI — orchestrates the full flow
├── interview.py                # Question generation logic
├── evaluator.py                 # Answer scoring + final report generation
├── prompts.py                    # All LLM system/user prompt templates
├── utils.py                       # LLM client, JSON parsing, file I/O
├── requirements.txt
├── README.md
├── .env.example
├── outputs/
│   ├── interview_report.json   # Sample output (generated fresh on each run)
│   └── transcript.txt          # Sample output (generated fresh on each run)
└── screenshots/
    └── README.md               # Placeholder — add UI screenshots here
```

---

## 4. Installation

Requires **Python 3.11+**.

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd Interview-Agent

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 5. Environment Variables

Copy the example file and fill in your key:

```bash
cp .env.example .env
```

`.env.example` contents:

```env
# Which provider to use: "groq" (default, recommended) or "openai"
LLM_PROVIDER=groq

# --- Groq (default) ---
# Get a free key at https://console.groq.com/keys
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# --- OpenAI (optional swap) ---
# Only needed if LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

To switch to OpenAI later, just change two lines — no code changes needed:
```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

---

## 6. Running the App

```bash
streamlit run app.py
```

This opens the app in your browser (default: `http://localhost:8501`).

**Flow:**
1. Enter a **Job Role** and comma-separated **Required Skills** → *Start Interview*
2. Answer each of the 5 questions in the text box → *Submit Answer* → see
   score + feedback → *Next Question*
3. After question 5 → *See Final Report* → view + download the report and
   transcript

---

## 7. Sample Interview

A full sample run (Backend Engineer role) is included at:
- [`outputs/transcript.txt`](outputs/transcript.txt) — full Q&A transcript with scores and feedback
- [`outputs/interview_report.json`](outputs/interview_report.json) — structured final report

Final report shape:
```json
{
  "overall_score": 34,
  "average_score": 6.8,
  "strengths": ["...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "recommendations": ["...", "...", "..."],
  "final_verdict": "Leaning Hire — ..."
}
```

Per-answer evaluation shape (shown live during the interview):
```json
{
  "score": 8,
  "feedback": "...",
  "expected_points": ["...", "...", "..."]
}
```

> Note: the sample files in `outputs/` are illustrative examples committed
> for review convenience. Running the app end-to-end will overwrite them
> with your own live session's results.

---

## 8. Screenshots

See [`screenshots/`](screenshots/) — add UI screenshots there (setup screen,
in-progress question, final report).

---

## 9. Design Choices & Tradeoffs

**Model choice (Groq + Llama 3.3 70B by default):** Groq's free tier and low
latency make the question-by-question feedback loop feel responsive, which
matters for a live interview UX. The provider layer in `utils.py` is a thin
OpenAI-compatible wrapper, so switching to OpenAI's `gpt-4o-mini` (better
JSON-following consistency, small cost) is a one-line `.env` change — no
code changes required in `interview.py` / `evaluator.py`.

**Deterministic scoring math, LLM-generated qualitative content:**
`overall_score` and `average_score` are always computed in plain Python from
the individual scores — never trusted to the LLM — so the numbers in the
final report can never be arithmetically wrong or hallucinated. Only the
qualitative synthesis (strengths/weaknesses/recommendations/verdict) is
LLM-generated, and it's explicitly grounded in the full Q&A record passed
into the prompt.

**Robust JSON parsing (`extract_json`):** LLMs occasionally wrap JSON in
markdown fences or add a sentence of preamble even when told not to.
Rather than trusting `json.loads` on raw output, `extract_json()` strips
fences and falls back to regex-extracting the first `{...}` block. This
avoids a single wrapping quirk causing a hard crash mid-interview.

**One question at a time, state held in `st.session_state`:** Streamlit
reruns the whole script on every interaction, so all interview state
(questions, current index, per-question records, last evaluation) lives in
`st.session_state` rather than local variables. This keeps `app.py` a state
machine (`setup → interview → complete`) instead of a single long script.

**Score clamping and defensive coercion:** Model output is coerced to an
int and clamped to `[0, 10]` in `evaluator.py` in case of formatting drift
(e.g. the model returns `"8/10"` or `8.0`), so a slightly malformed model
response degrades gracefully instead of crashing the session.

**What I'd improve with more time:**
- Add automatic retry-with-backoff on transient API failures instead of
  surfacing the error immediately.
- Support voice input (speech-to-text) for a more realistic interview feel,
  reusing the same evaluation pipeline.
- Add a lightweight rubric config per role (e.g. weight system-design
  questions higher for senior roles) instead of a flat 0-10 scale for every
  question.
- Persist multiple candidates' sessions to a small SQLite store instead of
  overwriting a single `outputs/` file, so a recruiter could compare
  candidates side by side.
- Add unit tests around `extract_json` and the scoring/clamping logic in
  `evaluator.py` (currently manually verified, not covered by an automated
  test suite, due to the 24-hour time box).

---

## 10. Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| UI | Streamlit |
| LLM | Groq (`llama-3.3-70b-versatile`) — swappable to OpenAI |
| Prompting | Structured JSON-only prompts, modular in `prompts.py` |
| Storage | JSON + plain text files in `outputs/` |
