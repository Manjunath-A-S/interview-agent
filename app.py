"""
app.py
------
Streamlit front-end for the AI Interview Agent.

Flow:
  1. SETUP    -> user enters job role + required skills
  2. INTERVIEW -> exactly 5 questions asked one at a time, each answer scored
                  and given feedback immediately
  3. COMPLETE -> final report is generated, shown, and saved to disk

Run with:  streamlit run app.py
"""

from pathlib import Path

import streamlit as st

from interview import generate_questions
from evaluator import evaluate_answer, generate_final_report
from utils import get_provider, get_model, save_json, save_transcript

NUM_QUESTIONS = 5
OUTPUT_DIR = Path(__file__).parent / "outputs"
REPORT_PATH = OUTPUT_DIR / "interview_report.json"
TRANSCRIPT_PATH = OUTPUT_DIR / "transcript.txt"


# ---------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------------------------

def init_state() -> None:
    defaults = {
        "stage": "setup",       # setup -> interview -> complete
        "role": "",
        "skills": [],
        "questions": [],
        "current_index": 0,
        "qa_records": [],       # list of {question, answer, score, feedback, expected_points}
        "last_evaluation": None,  # holds the just-submitted answer's evaluation for display
        "report": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def restart_interview() -> None:
    for key in [
        "stage", "role", "skills", "questions", "current_index",
        "qa_records", "last_evaluation", "report",
    ]:
        del st.session_state[key]
    init_state()


# ---------------------------------------------------------------------------
# PAGE CONFIG + SIDEBAR
# ---------------------------------------------------------------------------

st.set_page_config(page_title="AI Interview Agent", page_icon="🎤", layout="centered")
init_state()

with st.sidebar:
    st.header("⚙️ Configuration")
    try:
        st.write(f"**Provider:** {get_provider()}")
        st.write(f"**Model:** {get_model()}")
    except Exception as e:
        st.error(f"Config error: {e}")
    st.divider()
    st.caption(
        "Set LLM_PROVIDER, GROQ_API_KEY / OPENAI_API_KEY, and the model "
        "name in your .env file. See .env.example."
    )
    if st.session_state.stage != "setup":
        if st.button("🔄 Restart Interview", use_container_width=True):
            restart_interview()
            st.rerun()

st.title("🎤 AI Interview Agent")
st.caption("Interview Agent")


# ---------------------------------------------------------------------------
# STAGE 1: SETUP
# ---------------------------------------------------------------------------

if st.session_state.stage == "setup":
    st.subheader("Step 1 — Interview Setup")
    st.write("Enter the role you're hiring for and the key skills to assess.")

    with st.form("setup_form"):
        role = st.text_input(
            "Job Role", placeholder="e.g. Backend Engineer (Python)"
        )
        skills_raw = st.text_input(
            "Required Skills (comma-separated)",
            placeholder="e.g. Python, REST APIs, SQL, System Design",
        )
        submitted = st.form_submit_button("Start Interview", use_container_width=True)

    if submitted:
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]
        if not role.strip() or not skills:
            st.error("Please enter both a job role and at least one skill.")
        else:
            with st.spinner("Generating interview questions..."):
                try:
                    questions = generate_questions(role, skills, NUM_QUESTIONS)
                    st.session_state.role = role.strip()
                    st.session_state.skills = skills
                    st.session_state.questions = questions
                    st.session_state.stage = "interview"
                    st.session_state.current_index = 0
                    st.session_state.qa_records = []
                    st.session_state.last_evaluation = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate questions: {e}")


# ---------------------------------------------------------------------------
# STAGE 2: INTERVIEW LOOP
# ---------------------------------------------------------------------------

elif st.session_state.stage == "interview":
    idx = st.session_state.current_index
    total = len(st.session_state.questions)

    st.subheader(f"Step 2 — Question {idx + 1} of {total}")
    st.progress(idx / total)

    st.info(f"**{st.session_state.questions[idx]}**")

    # If this question has already been evaluated, show the result and a
    # "Next" button instead of the answer box again.
    if st.session_state.last_evaluation is not None:
        eval_result = st.session_state.last_evaluation
        st.metric("Score", f"{eval_result['score']} / 10")
        st.write(f"**Feedback:** {eval_result['feedback']}")
        if eval_result["expected_points"]:
            with st.expander("Expected key points"):
                for p in eval_result["expected_points"]:
                    st.write(f"- {p}")

        button_label = "Next Question ➜" if idx + 1 < total else "See Final Report ➜"
        if st.button(button_label, use_container_width=True):
            st.session_state.current_index += 1
            st.session_state.last_evaluation = None
            if st.session_state.current_index >= total:
                st.session_state.stage = "complete"
            st.rerun()

    else:
        answer = st.text_area("Your answer", key=f"answer_{idx}", height=150)
        if st.button("Submit Answer", use_container_width=True):
            with st.spinner("Evaluating your answer..."):
                try:
                    result = evaluate_answer(
                        role=st.session_state.role,
                        skills=st.session_state.skills,
                        question=st.session_state.questions[idx],
                        answer=answer,
                    )
                    st.session_state.qa_records.append(
                        {
                            "question": st.session_state.questions[idx],
                            "answer": answer if answer.strip() else "(No answer provided)",
                            "score": result["score"],
                            "feedback": result["feedback"],
                            "expected_points": result["expected_points"],
                        }
                    )
                    st.session_state.last_evaluation = result
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to evaluate answer: {e}")


# ---------------------------------------------------------------------------
# STAGE 3: FINAL REPORT
# ---------------------------------------------------------------------------

elif st.session_state.stage == "complete":
    st.subheader("Step 3 — Final Interview Report")

    if st.session_state.report is None:
        with st.spinner("Generating final report..."):
            try:
                report = generate_final_report(
                    role=st.session_state.role,
                    skills=st.session_state.skills,
                    qa_records=st.session_state.qa_records,
                )
                st.session_state.report = report

                # Persist outputs to disk for the challenge deliverables.
                save_json(report, REPORT_PATH)
                save_transcript(
                    role=st.session_state.role,
                    skills=st.session_state.skills,
                    qa_records=st.session_state.qa_records,
                    report=report,
                    path=TRANSCRIPT_PATH,
                )
            except Exception as e:
                st.error(f"Failed to generate final report: {e}")
                st.stop()

    report = st.session_state.report
    total_possible = len(st.session_state.qa_records) * 10

    col1, col2 = st.columns(2)
    col1.metric("Overall Score", f"{report['overall_score']} / {total_possible}")
    col2.metric("Average Score", f"{report['average_score']} / 10")

    st.markdown("### ✅ Strengths")
    for s in report["strengths"]:
        st.write(f"- {s}")

    st.markdown("### ⚠️ Weaknesses")
    for w in report["weaknesses"]:
        st.write(f"- {w}")

    st.markdown("### 💡 Recommendations")
    for r in report["recommendations"]:
        st.write(f"- {r}")

    st.markdown("### 🏁 Final Verdict")
    st.success(report["final_verdict"])

    st.divider()
    st.caption(f"Saved to `{REPORT_PATH}` and `{TRANSCRIPT_PATH}`.")

    if TRANSCRIPT_PATH.exists():
        st.download_button(
            "⬇️ Download Transcript (.txt)",
            data=TRANSCRIPT_PATH.read_text(encoding="utf-8"),
            file_name="transcript.txt",
            use_container_width=True,
        )
    if REPORT_PATH.exists():
        st.download_button(
            "⬇️ Download Report (.json)",
            data=REPORT_PATH.read_text(encoding="utf-8"),
            file_name="interview_report.json",
            use_container_width=True,
        )
