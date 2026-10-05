import os
import time
import json
import re

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

from rag import RAGEngine

from database import (
    create_tables,
    save_chat,
    get_chat_history,
    clear_chat_history,
    save_quiz_result,
    get_quiz_results,
    save_study_plan,
    get_study_plans
)

from dashboard import show_dashboard


# =========================================================
# 1. PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="EduMind AI",
    page_icon="🎓",
    layout="wide"
)


# =========================================================
# 2. ENVIRONMENT
# =========================================================

load_dotenv()

API_KEY = st.secrets("GEMINI_API_KEY")

if not API_KEY:
    st.error(
        "🔑 Gemini API key not found.\n\n"
        "Please check your .env file and make sure "
        "GEMINI_API_KEY is configured correctly."
    )
    st.stop()

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    st.error(
        f"⚠️ Could not initialize Gemini API client.\n\n{str(e)}"
    )
    st.stop()


# =========================================================
# DATABASE
# =========================================================

try:
    create_tables()
except Exception as e:
    st.error(
        f"⚠️ Database initialization failed.\n\n{str(e)}"
    )
    st.stop()


# =========================================================
# 3. CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>
    .block-container { padding-top: 2.2rem; padding-bottom: 2rem; max-width: 1250px; }
    [data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,0.18); }
    [data-testid="stSidebar"] .block-container { padding-top: 1.4rem; padding-left: 1.1rem; padding-right: 1.1rem; }
    .main-title { font-size: clamp(32px,4vw,48px); font-weight: 800; letter-spacing: -1.2px; margin-bottom: 3px; line-height: 1.1; }
    .subtitle { font-size: 17px; opacity: 0.72; margin-bottom: 20px; }
    .hero-card { padding: 24px 26px; border-radius: 18px; border: 1px solid rgba(128,128,128,0.20); background: rgba(128,128,128,0.045); margin: 8px 0 22px 0; }
    .hero-kicker { font-size: 12px; font-weight: 700; letter-spacing: 1.4px; text-transform: uppercase; opacity: 0.65; margin-bottom: 7px; }
    .hero-heading { font-size: 25px; font-weight: 750; margin-bottom: 6px; }
    .hero-text { font-size: 15px; opacity: 0.78; line-height: 1.55; margin: 0; }
    .feature-box, .quiz-box, .history-card, .source-box, .export-box { padding: 18px 20px; border-radius: 15px; border: 1px solid rgba(128,128,128,0.20); background: rgba(128,128,128,0.035); margin-bottom: 14px; }
    .section-label { font-size: 12px; font-weight: 700; letter-spacing: 1.1px; text-transform: uppercase; opacity: 0.58; margin: 4px 0 8px 0; }
    .status-card { padding: 13px 15px; border-radius: 12px; border: 1px solid rgba(128,128,128,0.18); background: rgba(128,128,128,0.035); margin: 8px 0; }
    .metric-card { padding: 16px; border-radius: 14px; border: 1px solid rgba(128,128,128,0.18); background: rgba(128,128,128,0.035); min-height: 95px; }
    .app-footer { text-align: center; opacity: 0.55; font-size: 12px; padding: 18px 0 4px 0; }
    div[data-testid="stButton"] > button, div[data-testid="stDownloadButton"] > button { border-radius: 10px; min-height: 42px; font-weight: 600; }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea, div[data-testid="stSelectbox"] div[data-baseweb="select"] > div { border-radius: 10px; }
    [data-testid="stExpander"] { border-radius: 12px; overflow: hidden; }
    hr { margin: 1.25rem 0; opacity: 0.25; }
    @media (max-width: 768px) { .block-container { padding-top: 1.2rem; padding-left: 1rem; padding-right: 1rem; } .hero-card { padding: 18px; } .subtitle { font-size: 15px; } }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 4. SESSION STATE
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "mode" not in st.session_state:
    st.session_state.mode = "General Academic"

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

if "pdf_pages" not in st.session_state:
    st.session_state.pdf_pages = 0

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = ""

if "pdf_page_data" not in st.session_state:
    st.session_state.pdf_page_data = []

if "rag_engine" not in st.session_state:
    try:
        st.session_state.rag_engine = RAGEngine()
    except Exception as e:
        st.error(
            "⚠️ Semantic search engine could not be initialized.\n\n"
            f"{str(e)}"
        )
        st.session_state.rag_engine = None

if "rag_ready" not in st.session_state:
    st.session_state.rag_ready = False

if "study_action" not in st.session_state:
    st.session_state.study_action = None

if "last_study_result" not in st.session_state:
    st.session_state.last_study_result = ""

if "last_study_title" not in st.session_state:
    st.session_state.last_study_title = ""


# =========================================================
# QUIZ STATE
# =========================================================

if "quiz_questions" not in st.session_state:
    st.session_state.quiz_questions = []

if "quiz_current" not in st.session_state:
    st.session_state.quiz_current = 0

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}

if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False

if "quiz_finished" not in st.session_state:
    st.session_state.quiz_finished = False

if "quiz_saved" not in st.session_state:
    st.session_state.quiz_saved = False

if "last_quiz_score" not in st.session_state:
    st.session_state.last_quiz_score = 0

if "last_quiz_total" not in st.session_state:
    st.session_state.last_quiz_total = 0

if "last_quiz_percentage" not in st.session_state:
    st.session_state.last_quiz_percentage = 0


# =========================================================
# STUDY PLANNER STATE
# =========================================================

if "planner_result" not in st.session_state:
    st.session_state.planner_result = ""

if "planner_open" not in st.session_state:
    st.session_state.planner_open = False


# =========================================================
# CODING ASSISTANT STATE
# =========================================================

if "coding_open" not in st.session_state:
    st.session_state.coding_open = False

if "coding_result" not in st.session_state:
    st.session_state.coding_result = ""


# =========================================================
# HISTORY STATE
# =========================================================

if "history_open" not in st.session_state:
    st.session_state.history_open = False


# =========================================================
# DASHBOARD STATE
# =========================================================

if "dashboard_open" not in st.session_state:
    st.session_state.dashboard_open = False


# =========================================================
# EXPORT STATE
# =========================================================

if "export_open" not in st.session_state:
    st.session_state.export_open = False


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🎓 EduMind AI</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">AI-Powered Academic Learning & Study Assistant</div>',
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-kicker">Academic Intelligence Workspace</div>
        <div class="hero-heading">Learn smarter. Prepare better. Track your progress.</div>
        <p class="hero-text">
            Ask academic questions, work with your study material, generate practice content,
            plan your preparation and analyze your learning from one focused workspace.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def clean_json_response(text):

    if not text:
        raise ValueError("AI returned an empty response.")

    text = text.strip()

    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"^```\s*",
        "",
        text
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    return text.strip()


def get_ai_text(response):

    if response is None:
        raise ValueError("AI returned no response.")

    text = getattr(response, "text", None)

    if not text or not text.strip():
        raise ValueError(
            "AI returned an empty response. Please try again."
        )

    return text.strip()


def is_quota_error(error):

    error_text = str(error).lower()

    return (
        "429" in error_text
        or "resource_exhausted" in error_text
        or "quota" in error_text
    )


def show_ai_error(error, feature_name="AI feature"):

    if is_quota_error(error):

        st.error(
            f"⚠️ Gemini API quota is currently exhausted.\n\n"
            f"{feature_name} is ready, but AI generation will "
            f"work after the quota resets."
        )

    else:

        st.error(
            f"⚠️ {feature_name} encountered an error.\n\n"
            f"{str(error)}"
        )


def build_quiz_report():

    questions = st.session_state.quiz_questions
    answers = st.session_state.quiz_answers

    if not questions:
        return ""

    score = 0

    for i, question in enumerate(questions):

        correct_answer = question["answer"]
        user_answer = answers.get(i)

        if user_answer == correct_answer:
            score += 1

    total = len(questions)
    percentage = (score / total) * 100

    report = f"""
EDUMIND AI
QUIZ PERFORMANCE REPORT
=======================

Study Material:
{st.session_state.pdf_name or "Not specified"}

Score:
{score}/{total}

Percentage:
{percentage:.0f}%

Performance:
"""

    if percentage >= 80:
        report += "Excellent\n"
    elif percentage >= 60:
        report += "Good\n"
    elif percentage >= 40:
        report += "Needs Revision\n"
    else:
        report += "Keep Practicing\n"

    report += "\nANSWER REVIEW\n"
    report += "==============\n\n"

    for i, question in enumerate(questions):

        correct_index = question["answer"]
        user_index = answers.get(i)

        report += f"Q{i + 1}. {question['question']}\n"

        if (
            user_index is not None
            and isinstance(user_index, int)
            and 0 <= user_index < len(question["options"])
        ):

            report += (
                f"Your Answer: "
                f"{question['options'][user_index]}\n"
            )

        else:

            report += "Your Answer: Not answered\n"

        report += (
            f"Correct Answer: "
            f"{question['options'][correct_index]}\n"
        )

        if question.get("explanation"):

            report += (
                f"Explanation: "
                f"{question['explanation']}\n"
            )

        report += "\n"

    return report


def build_mcq_export(data):

    text = (
        "EDUMIND AI\n"
        "AI GENERATED MCQs\n"
        "====================\n\n"
    )

    for i, q in enumerate(data, start=1):

        text += f"Q{i}. {q.get('question', '')}\n\n"

        options = q.get("options", [])

        for index, option in enumerate(options):

            letter = chr(65 + index)

            text += f"{letter}. {option}\n"

        answer = q.get("answer", 0)

        if (
            isinstance(answer, int)
            and 0 <= answer < len(options)
        ):

            text += (
                f"\nCorrect Answer: "
                f"{chr(65 + answer)}. "
                f"{options[answer]}\n"
            )

        if q.get("explanation"):

            text += (
                f"Explanation: "
                f"{q['explanation']}\n"
            )

        text += "\n" + "-" * 50 + "\n\n"

    return text


def build_viva_export(text):

    return (
        "EDUMIND AI\n"
        "VIVA PREPARATION\n"
        "====================\n\n"
        + text
    )


def build_summary_export(title, text):

    return (
        "EDUMIND AI\n"
        f"{title}\n"
        "====================\n\n"
        + text
    )


# =========================================================
# STUDY TOOL PROMPTS
# =========================================================

def generate_study_tool_prompt(action):

    if not st.session_state.pdf_text:
        return None

    material = st.session_state.pdf_text[:12000]

    prompts = {

        "summarize": f"""
You are EduMind AI, an academic learning assistant.

Create a clear summary of the uploaded study material.

Requirements:
- Start with a short overview.
- Identify major concepts.
- Use headings and bullet points.
- Explain difficult concepts simply.
- Make it useful for exam revision.
- Do not invent information.
- Use only the supplied study material.

Study Material:

{material}

Create the summary.
""",

        "important_points": f"""
You are EduMind AI, an academic exam preparation assistant.

Extract the most important points from the study material.

Requirements:
- Give 10 to 15 important points.
- Include important definitions.
- Include important concepts.
- Include keywords.
- Keep points short.
- Make it useful for revision.
- Do not invent information.

Study Material:

{material}

Generate the important points.
""",

        "mcqs": f"""
You are EduMind AI, an academic assessment generator.

Create 10 multiple-choice questions from the study material.

For each question provide:
- Question
- Option A
- Option B
- Option C
- Option D
- Correct answer
- Short explanation

Return ONLY valid JSON in this exact format:

[
  {{
    "question": "Question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": 0,
    "explanation": "Short explanation"
  }}
]

The answer value must be:
0 for A
1 for B
2 for C
3 for D

Requirements:
- Questions must come from the study material.
- Mix easy, medium and difficult questions.
- Avoid duplicates.

Study Material:

{material}
""",

        "viva": f"""
You are EduMind AI, a college viva preparation assistant.

Create 10 important viva questions from the study material.

For every question provide:
Question:
Answer:
Why this is important:

Requirements:
- Cover important concepts.
- Start with basic questions.
- Include conceptual questions.
- Include some deeper questions.
- Keep answers easy to speak.
- Do not invent information.

Study Material:

{material}
"""
    }

    return prompts.get(action)


# =========================================================
# QUIZ PROMPT
# =========================================================

def generate_quiz_prompt():

    if not st.session_state.pdf_text:
        return None

    material = st.session_state.pdf_text[:12000]

    return f"""
You are EduMind AI, an academic quiz generator.

Create exactly 10 multiple-choice questions from the
uploaded study material.

Return ONLY valid JSON.

Required format:

[
  {{
    "question": "Question text",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answer": 0,
    "explanation": "Short explanation"
  }}
]

Rules:

- answer must be 0, 1, 2 or 3.
- 0 = A
- 1 = B
- 2 = C
- 3 = D
- Questions must be based on the uploaded material.
- Mix easy, medium and difficult questions.
- Do not repeat questions.
- Keep options clear.
- Keep explanations short.

Study Material:

{material}
"""


# =========================================================
# CODING ASSISTANT PROMPT
# =========================================================

def coding_assistant_prompt(language, code, task):

    return f"""
You are EduMind AI Coding Assistant.

Programming Language:
{language}

Student's Code:

---------------- START CODE ----------------

{code}

---------------- END CODE ----------------

Student wants:
{task}

Analyze the code and provide:

1. 🔍 Problem/Error
2. 💡 Simple Explanation
3. ✅ Corrected Code
4. 🧠 Short Logic Explanation
5. 📌 One useful improvement
6. 🎤 One viva question related to the code

Rules:

- Be beginner-friendly.
- If there is no error, clearly say that.
- Do not unnecessarily rewrite working code.
- Keep the explanation simple.
- Return properly formatted code.
"""


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "<div class='section-label'>EDUMIND AI</div>",
        unsafe_allow_html=True
    )
    st.header("⚙️ Academic Workspace")

    mode_options = [
        "General Academic",
        "Exam Preparation",
        "Programming Help",
        "Viva Preparation",
        "Assignment Help",
        "Study Planning"
    ]

    mode = st.selectbox(
        "Choose Academic Mode",
        mode_options,
        index=mode_options.index(
            st.session_state.mode
        )
    )

    st.session_state.mode = mode

    st.divider()

    # =====================================================
    # PDF UPLOAD
    # =====================================================

    st.subheader("📚 Study Material")

    uploaded_file = st.file_uploader(
        "Upload a PDF",
        type=["pdf"],
        help=(
            "Upload notes, textbook chapters, "
            "research papers or study material."
        )
    )

    if uploaded_file is not None:

        if st.session_state.pdf_name != uploaded_file.name:

            try:

                pdf_reader = PdfReader(uploaded_file)

                total_pdf_pages = len(
                    pdf_reader.pages
                )

                if total_pdf_pages == 0:

                    raise ValueError(
                        "The uploaded PDF contains no pages."
                    )

                extracted_text = ""

                page_data = []

                for page_number, page in enumerate(
                    pdf_reader.pages,
                    start=1
                ):

                    try:

                        page_text = (
                            page.extract_text()
                            or ""
                        )

                    except Exception:

                        page_text = ""

                    extracted_text += (
                        page_text + "\n"
                    )

                    if page_text.strip():

                        page_data.append(
                            (
                                page_number,
                                page_text
                            )
                        )

                if not extracted_text.strip():

                    st.warning(
                        "⚠️ No readable text was found "
                        "in this PDF.\n\n"
                        "It may be a scanned/image-only PDF."
                    )

                    st.session_state.pdf_text = ""
                    st.session_state.pdf_page_data = []
                    st.session_state.pdf_name = (
                        uploaded_file.name
                    )
                    st.session_state.pdf_pages = (
                        total_pdf_pages
                    )
                    st.session_state.rag_ready = False

                else:

                    st.session_state.pdf_text = (
                        extracted_text
                    )

                    st.session_state.pdf_page_data = (
                        page_data
                    )

                    st.session_state.pdf_name = (
                        uploaded_file.name
                    )

                    st.session_state.pdf_pages = (
                        total_pdf_pages
                    )

                    if st.session_state.rag_engine is None:

                        st.warning(
                            "⚠️ Semantic search engine "
                            "is unavailable."
                        )

                        st.session_state.rag_ready = False

                    else:

                        with st.spinner(
                            "🔎 Preparing study material..."
                        ):

                            chunk_count = (
                                st.session_state
                                .rag_engine
                                .build_index(
                                    page_data
                                )
                            )

                        st.session_state.rag_ready = (
                            chunk_count > 0
                        )

                        if not st.session_state.rag_ready:

                            st.warning(
                                "⚠️ PDF text was extracted, "
                                "but semantic search could "
                                "not create searchable chunks."
                            )

                st.session_state.quiz_questions = []
                st.session_state.quiz_current = 0
                st.session_state.quiz_answers = {}
                st.session_state.quiz_started = False
                st.session_state.quiz_finished = False
                st.session_state.quiz_saved = False

            except Exception as e:

                st.error(
                    "⚠️ Could not process the PDF.\n\n"
                    f"{str(e)}"
                )

                st.session_state.rag_ready = False

    # =====================================================
    # PDF STATUS
    # =====================================================

    if st.session_state.pdf_name:

        st.success(
            f"📄 {st.session_state.pdf_name}"
        )

        st.write(
            f"Pages: {st.session_state.pdf_pages}"
        )

        if st.session_state.pdf_text:

            st.info(
                "📄 Text extraction successful"
            )

        if st.session_state.rag_ready:

            st.info(
                "🧠 Semantic search ready"
            )

        elif st.session_state.pdf_text:

            st.warning(
                "⚠️ Semantic search unavailable"
            )

    else:

        st.caption(
            "Upload a PDF to unlock Study Tools."
        )

    # =====================================================
    # STUDY TOOLS
    # =====================================================

    st.divider()

    st.subheader("📚 Study Tools")

    if st.button(
        "📝 Summarize Material",
        use_container_width=True
    ):

        st.session_state.study_action = "summarize"

    if st.button(
        "🔑 Important Points",
        use_container_width=True
    ):

        st.session_state.study_action = "important_points"

    if st.button(
        "❓ Generate MCQs",
        use_container_width=True
    ):

        st.session_state.study_action = "mcqs"

    if st.button(
        "🎤 Viva Questions",
        use_container_width=True
    ):

        st.session_state.study_action = "viva"

    # =====================================================
    # QUIZ
    # =====================================================

    st.divider()

    st.subheader("🎯 Quiz Mode")

    if st.button(
        "🚀 Start AI Quiz",
        use_container_width=True
    ):

        st.session_state.study_action = "quiz"

    # =====================================================
    # STUDY PLANNER
    # =====================================================

    st.divider()

    st.subheader("📅 Study Planner")

    if st.button(
        "📅 Create Study Plan",
        use_container_width=True
    ):

        st.session_state.planner_open = True

    # =====================================================
    # CODING ASSISTANT
    # =====================================================

    st.divider()

    st.subheader("💻 Coding")

    if st.button(
        "💻 Open Coding Assistant",
        use_container_width=True
    ):

        st.session_state.coding_open = True

    # =====================================================
    # HISTORY
    # =====================================================

    st.divider()

    st.subheader("🗂️ Database")

    if st.button(
        "📜 View History",
        use_container_width=True
    ):

        st.session_state.history_open = True

    # =====================================================
    # DASHBOARD
    # =====================================================

    st.divider()

    st.subheader("📊 Analytics")

    if st.button(
        "📊 Student Dashboard",
        use_container_width=True
    ):

        st.session_state.dashboard_open = True

    # =====================================================
    # EXPORT CENTER
    # =====================================================

    st.divider()

    st.subheader("📥 Export")

    if st.button(
        "📥 Export Center",
        use_container_width=True
    ):

        st.session_state.export_open = True

    # =====================================================
    # CLEAR CURRENT CHAT
    # =====================================================

    st.divider()

    if st.button(
        "🗑️ Clear Current Chat",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()

    # =====================================================
    # FOOTER
    # =====================================================

    st.divider()

    st.markdown(
        '<div class="app-footer">EduMind AI · Academic Learning Assistant</div>',
        unsafe_allow_html=True
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

if st.session_state.dashboard_open:

    show_dashboard(
        st.session_state.pdf_name,
        st.session_state.pdf_pages
    )

    if st.button(
        "✖️ Close Dashboard"
    ):

        st.session_state.dashboard_open = False

        st.rerun()


# =========================================================
# EXPORT CENTER
# =========================================================

if st.session_state.export_open:

    st.markdown("---")

    st.markdown(
        "## 📥 Export Center"
    )

    st.write(
        "Download your generated academic content "
        "for revision, submission or future reference."
    )

    st.markdown("### 💬 Chat Export")

    if st.session_state.messages:

        chat_export = (
            "EDUMIND AI\n"
            "ACADEMIC CHAT EXPORT\n"
            "====================\n\n"
        )

        for message in st.session_state.messages:

            role = (
                "Student"
                if message["role"] == "user"
                else "EduMind AI"
            )

            chat_export += (
                f"{role}:\n"
                f"{message['content']}\n\n"
                + "-" * 60
                + "\n\n"
            )

        st.download_button(
            "⬇️ Download Chat",
            data=chat_export,
            file_name="edumind_chat.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:

        st.info(
            "No current chat available for export."
        )

    st.markdown("### 📚 Study Material Exports")

    if st.session_state.last_study_result:

        st.info(
            f"Last generated content: "
            f"{st.session_state.last_study_title}"
        )

        st.download_button(
            "⬇️ Download Last Study Tool Result",
            data=st.session_state.last_study_result,
            file_name="edumind_study_result.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:

        st.info(
            "Generate Summary, Important Points, "
            "MCQs or Viva Questions first."
        )

    st.markdown("### 📅 Study Plan Export")

    if st.session_state.planner_result:

        planner_export = (
            "EDUMIND AI\n"
            "PERSONALIZED STUDY PLAN\n"
            "=======================\n\n"
            + st.session_state.planner_result
        )

        st.download_button(
            "⬇️ Download Study Plan",
            data=planner_export,
            file_name="edumind_study_plan.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:

        st.info(
            "Create a study plan first."
        )

    st.markdown("### 🎯 Quiz Export")

    if st.session_state.quiz_finished:

        quiz_report = build_quiz_report()

        st.download_button(
            "⬇️ Download Quiz Report",
            data=quiz_report,
            file_name="edumind_quiz_report.txt",
            mime="text/plain",
            use_container_width=True
        )

    else:

        st.info(
            "Complete a quiz first to export the result."
        )

    st.divider()

    if st.button(
        "✖️ Close Export Center"
    ):

        st.session_state.export_open = False

        st.rerun()


# =========================================================
# CODING ASSISTANT
# =========================================================

if st.session_state.coding_open:

    st.markdown("---")

    st.markdown(
        "## 💻 AI Coding Assistant"
    )

    st.write(
        "Paste your code and EduMind AI will analyze "
        "errors, explain the problem and suggest corrected code."
    )

    col1, col2 = st.columns(2)

    with col1:

        coding_language = st.selectbox(
            "Programming Language",
            [
                "Python",
                "Java",
                "SQL",
                "C",
                "C++",
                "JavaScript"
            ],
            key="coding_language"
        )

    with col2:

        coding_task = st.selectbox(
            "What do you want help with?",
            [
                "Find and fix errors",
                "Explain this code",
                "Improve this code",
                "Optimize this code",
                "Prepare this code for viva"
            ],
            key="coding_task"
        )

    code_input = st.text_area(
        "Paste your code here",
        height=300,
        placeholder="Paste your program here...",
        key="coding_input"
    )

    if st.button(
        "🔍 Analyze Code",
        use_container_width=True
    ):

        if not code_input.strip():

            st.warning(
                "Please paste your code first."
            )

        else:

            with st.spinner(
                "🤖 Analyzing your code..."
            ):

                try:

                    prompt = coding_assistant_prompt(
                        coding_language,
                        code_input,
                        coding_task
                    )

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.4,
                            max_output_tokens=1800
                        )
                    )

                    st.session_state.coding_result = (
                        get_ai_text(response)
                    )

                except Exception as e:

                    show_ai_error(
                        e,
                        "Coding Assistant"
                    )

    if st.session_state.coding_result:

        st.markdown("### 🧠 Analysis")

        st.markdown(
            st.session_state.coding_result
        )

        st.download_button(
            "⬇️ Download Coding Analysis",
            data=st.session_state.coding_result,
            file_name="edumind_coding_analysis.txt",
            mime="text/plain"
        )

    if st.button(
        "✖️ Close Coding Assistant"
    ):

        st.session_state.coding_open = False
        st.session_state.coding_result = ""

        st.rerun()


# =========================================================
# STUDY TOOL EXECUTION
# =========================================================

if st.session_state.study_action:

    action = st.session_state.study_action

    st.session_state.study_action = None

    # =====================================================
    # QUIZ GENERATION
    # =====================================================

    if action == "quiz":

        st.markdown("---")

        st.markdown(
            "## 🎯 AI Quiz Mode"
        )

        if not st.session_state.pdf_text:

            st.warning(
                "📚 Please upload a PDF study material first."
            )

        else:

            with st.spinner(
                "🤖 Creating your quiz..."
            ):

                try:

                    start_time = time.time()

                    prompt = generate_quiz_prompt()

                    if not prompt:

                        raise ValueError(
                            "Quiz material is empty."
                        )

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.4,
                            max_output_tokens=2500
                        )
                    )

                    raw_text = get_ai_text(response)

                    cleaned = clean_json_response(
                        raw_text
                    )

                    questions = json.loads(
                        cleaned
                    )

                    if not isinstance(
                        questions,
                        list
                    ):

                        raise ValueError(
                            "Quiz format is invalid."
                        )

                    valid_questions = []

                    for q in questions:

                        if not isinstance(q, dict):
                            continue

                        if (
                            "question" in q
                            and "options" in q
                            and "answer" in q
                        ):

                            if (
                                isinstance(
                                    q["question"],
                                    str
                                )
                                and q["question"].strip()
                                and isinstance(
                                    q["options"],
                                    list
                                )
                                and len(
                                    q["options"]
                                ) == 4
                                and all(
                                    isinstance(
                                        option,
                                        str
                                    )
                                    and option.strip()
                                    for option in q["options"]
                                )
                                and q["answer"] in [0, 1, 2, 3]
                            ):

                                valid_questions.append(q)

                    if len(valid_questions) < 5:

                        raise ValueError(
                            "AI generated fewer than "
                            "5 valid quiz questions."
                        )

                    st.session_state.quiz_questions = (
                        valid_questions[:10]
                    )

                    st.session_state.quiz_current = 0

                    st.session_state.quiz_answers = {}

                    st.session_state.quiz_started = True

                    st.session_state.quiz_finished = False

                    st.session_state.quiz_saved = False

                    elapsed = (
                        time.time()
                        - start_time
                    )

                    st.success(
                        f"🎯 Quiz created with "
                        f"{len(valid_questions[:10])} questions."
                    )

                    st.caption(
                        f"Generated in {elapsed:.2f} seconds"
                    )

                except Exception as e:

                    show_ai_error(
                        e,
                        "Quiz generation"
                    )

    # =====================================================
    # OTHER STUDY TOOLS
    # =====================================================

    elif action in [
        "summarize",
        "important_points",
        "mcqs",
        "viva"
    ]:

        titles = {

            "summarize":
                "📝 AI Study Material Summary",

            "important_points":
                "🔑 Important Exam Points",

            "mcqs":
                "❓ AI Generated MCQs",

            "viva":
                "🎤 Viva Preparation"
        }

        st.markdown(
            f"## {titles[action]}"
        )

        if not st.session_state.pdf_text:

            st.warning(
                "📚 Please upload a PDF study material first."
            )

        else:

            with st.spinner(
                "🤖 EduMind AI is preparing your study material..."
            ):

                try:

                    start_time = time.time()

                    prompt = generate_study_tool_prompt(
                        action
                    )

                    if not prompt:

                        raise ValueError(
                            "Study material is empty."
                        )

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.5,
                            max_output_tokens=1800
                        )
                    )

                    answer = get_ai_text(response)

                    elapsed = (
                        time.time()
                        - start_time
                    )

                    st.session_state.last_study_title = (
                        titles[action]
                    )

                    if action == "mcqs":

                        try:

                            cleaned = clean_json_response(
                                answer
                            )

                            mcq_data = json.loads(
                                cleaned
                            )

                            if not isinstance(
                                mcq_data,
                                list
                            ):

                                raise ValueError(
                                    "MCQ response is not a list."
                                )

                            valid_mcqs = []

                            for q in mcq_data:

                                if not isinstance(q, dict):
                                    continue

                                options = q.get(
                                    "options",
                                    []
                                )

                                answer_index = q.get(
                                    "answer"
                                )

                                if (
                                    isinstance(
                                        q.get("question"),
                                        str
                                    )
                                    and q["question"].strip()
                                    and isinstance(
                                        options,
                                        list
                                    )
                                    and len(options) == 4
                                    and isinstance(
                                        answer_index,
                                        int
                                    )
                                    and 0 <= answer_index < 4
                                ):

                                    valid_mcqs.append(q)

                            if not valid_mcqs:

                                raise ValueError(
                                    "No valid MCQs were generated."
                                )

                            st.write(
                                f"Generated "
                                f"{len(valid_mcqs)} MCQs"
                            )

                            for i, q in enumerate(
                                valid_mcqs,
                                start=1
                            ):

                                st.markdown(
                                    f"### Q{i}. "
                                    f"{q['question']}"
                                )

                                for index, option in enumerate(
                                    q["options"]
                                ):

                                    letter = chr(
                                        65 + index
                                    )

                                    st.write(
                                        f"**{letter}.** "
                                        f"{option}"
                                    )

                                correct = q["answer"]

                                st.success(
                                    f"Correct Answer: "
                                    f"{chr(65 + correct)}"
                                )

                                if q.get("explanation"):

                                    st.caption(
                                        q["explanation"]
                                    )

                            st.session_state.last_study_result = (
                                build_mcq_export(
                                    valid_mcqs
                                )
                            )

                        except Exception:

                            st.warning(
                                "⚠️ AI returned MCQs in an "
                                "unexpected format. Showing the "
                                "generated response instead."
                            )

                            st.markdown(answer)

                            st.session_state.last_study_result = (
                                answer
                            )

                    else:

                        st.markdown(answer)

                        if action == "viva":

                            st.session_state.last_study_result = (
                                build_viva_export(answer)
                            )

                        else:

                            st.session_state.last_study_result = (
                                build_summary_export(
                                    titles[action],
                                    answer
                                )
                            )

                    with st.expander(
                        "⚙️ Tool Details"
                    ):

                        st.write(
                            f"⏱️ Generation time: "
                            f"{elapsed:.2f} seconds"
                        )

                        st.write(
                            f"📄 Source: "
                            f"{st.session_state.pdf_name}"
                        )

                except Exception as e:

                    show_ai_error(
                        e,
                        "Study Tool"
                    )


# =========================================================
# INTERACTIVE QUIZ
# =========================================================

if (
    st.session_state.quiz_started
    and not st.session_state.quiz_finished
    and len(st.session_state.quiz_questions) > 0
):

    st.markdown("---")

    st.markdown(
        "## 🎯 Interactive Quiz"
    )

    total_questions = len(
        st.session_state.quiz_questions
    )

    current = st.session_state.quiz_current

    if current < 0 or current >= total_questions:

        st.error(
            "⚠️ Quiz state is invalid. Please start a new quiz."
        )

        st.session_state.quiz_started = False

    else:

        question_data = (
            st.session_state.quiz_questions[current]
        )

        st.progress(
            (current + 1) / total_questions
        )

        st.caption(
            f"Question {current + 1} "
            f"of {total_questions}"
        )

        st.markdown(
            f"### Q{current + 1}. "
            f"{question_data['question']}"
        )

        options = question_data["options"]

        selected = st.radio(
            "Choose your answer:",
            options,
            index=None,
            key=f"quiz_option_{current}"
        )

        if selected is not None:

            selected_index = options.index(
                selected
            )

            st.session_state.quiz_answers[current] = (
                selected_index
            )

        col1, col2 = st.columns(2)

        with col1:

            if current > 0:

                if st.button(
                    "⬅️ Previous",
                    use_container_width=True
                ):

                    st.session_state.quiz_current -= 1

                    st.rerun()

        with col2:

            if current < total_questions - 1:

                if st.button(
                    "Next ➡️",
                    use_container_width=True
                ):

                    if current not in st.session_state.quiz_answers:

                        st.warning(
                            "Please select an answer first."
                        )

                    else:

                        st.session_state.quiz_current += 1

                        st.rerun()

            else:

                if st.button(
                    "🏁 Submit Quiz",
                    use_container_width=True
                ):

                    if current not in st.session_state.quiz_answers:

                        st.warning(
                            "Please select an answer first."
                        )

                    else:

                        st.session_state.quiz_finished = True

                        st.rerun()


# =========================================================
# QUIZ RESULT
# =========================================================

if (
    st.session_state.quiz_finished
    and len(st.session_state.quiz_questions) > 0
):

    st.markdown("---")

    st.markdown(
        "## 🏆 Quiz Result"
    )

    questions = st.session_state.quiz_questions

    answers = st.session_state.quiz_answers

    score = 0

    for i, question in enumerate(questions):

        correct_answer = question["answer"]

        user_answer = answers.get(i)

        if user_answer == correct_answer:

            score += 1

    total = len(questions)

    if total == 0:

        st.error(
            "⚠️ No quiz questions available."
        )

    else:

        percentage = (score / total) * 100

        st.session_state.last_quiz_score = score
        st.session_state.last_quiz_total = total
        st.session_state.last_quiz_percentage = percentage

        if not st.session_state.quiz_saved:

            try:

                save_quiz_result(
                    score,
                    total
                )

                st.session_state.quiz_saved = True

            except Exception as e:

                st.warning(
                    "⚠️ Quiz result could not be saved "
                    "to the database."
                )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Score",
                f"{score}/{total}"
            )

        with col2:

            st.metric(
                "Percentage",
                f"{percentage:.0f}%"
            )

        with col3:

            if percentage >= 80:

                result = "Excellent 🎉"

            elif percentage >= 60:

                result = "Good 👍"

            elif percentage >= 40:

                result = "Needs Revision 📚"

            else:

                result = "Keep Practicing 💪"

            st.metric(
                "Performance",
                result
            )

        st.download_button(
            "⬇️ Download Quiz Report",
            data=build_quiz_report(),
            file_name="edumind_quiz_report.txt",
            mime="text/plain"
        )

        st.markdown(
            "### 📋 Answer Review"
        )

        for i, question in enumerate(questions):

            user_answer = answers.get(i)

            correct_answer = question["answer"]

            if user_answer == correct_answer:

                st.success(
                    f"Q{i + 1}: Correct ✅"
                )

            else:

                st.error(
                    f"Q{i + 1}: Incorrect ❌"
                )

                st.write(
                    f"Correct answer: "
                    f"{question['options'][correct_answer]}"
                )

            if question.get("explanation"):

                st.caption(
                    question["explanation"]
                )

        if st.button(
            "🔄 Start New Quiz"
        ):

            st.session_state.quiz_questions = []

            st.session_state.quiz_current = 0

            st.session_state.quiz_answers = {}

            st.session_state.quiz_started = False

            st.session_state.quiz_finished = False

            st.session_state.quiz_saved = False

            st.rerun()


# =========================================================
# STUDY PLANNER
# =========================================================

if st.session_state.planner_open:

    st.markdown("---")

    st.markdown(
        "## 📅 AI Study Planner"
    )

    st.write(
        "Create a personalized study plan based on "
        "your subjects, available time and exam deadline."
    )

    col1, col2 = st.columns(2)

    with col1:

        subjects = st.text_area(
            "📚 Subjects",
            placeholder=(
                "Example:\n"
                "Python\n"
                "DBMS\n"
                "Statistics\n"
                "AI"
            )
        )

        days = st.number_input(
            "📆 Number of days",
            min_value=1,
            max_value=90,
            value=7
        )

    with col2:

        hours_per_day = st.number_input(
            "⏰ Study hours per day",
            min_value=0.5,
            max_value=12.0,
            value=2.0,
            step=0.5
        )

        goal = st.text_input(
            "🎯 Goal",
            placeholder=(
                "Example: Semester exam preparation"
            )
        )

    if st.button(
        "✨ Generate My Study Plan",
        use_container_width=True
    ):

        if not subjects.strip():

            st.warning(
                "Please enter at least one subject."
            )

        elif days < 1:

            st.warning(
                "Number of days must be at least 1."
            )

        elif hours_per_day <= 0:

            st.warning(
                "Study hours must be greater than 0."
            )

        else:

            planner_prompt = f"""
You are EduMind AI, an intelligent academic study planner.

Create a practical study plan for a college student.

Subjects:
{subjects}

Number of days:
{days}

Available study time per day:
{hours_per_day} hours

Student goal:
{goal if goal.strip() else "Academic exam preparation"}

Requirements:

1. Create a day-by-day plan.
2. Divide the available study time realistically.
3. Include revision.
4. Include practice/questions where useful.
5. Give priority to difficult subjects.
6. Do not overload one day.
7. Keep the plan practical.
8. Include a final revision period.
9. Use a clear table or structured format.
"""

            with st.spinner(
                "🤖 Creating your personalized study plan..."
            ):

                try:

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=planner_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.6,
                            max_output_tokens=2200
                        )
                    )

                    planner_text = get_ai_text(
                        response
                    )

                    st.session_state.planner_result = (
                        planner_text
                    )

                    try:

                        save_study_plan(
                            subjects,
                            days,
                            hours_per_day,
                            (
                                goal
                                if goal.strip()
                                else "Academic exam preparation"
                            ),
                            planner_text
                        )

                    except Exception:

                        st.warning(
                            "⚠️ Study plan was generated, "
                            "but could not be saved to history."
                        )

                    st.markdown(
                        planner_text
                    )

                    st.download_button(
                        "⬇️ Download Study Plan",
                        data=(
                            "EDUMIND AI\n"
                            "PERSONALIZED STUDY PLAN\n"
                            "=======================\n\n"
                            + planner_text
                        ),
                        file_name="edumind_study_plan.txt",
                        mime="text/plain"
                    )

                except Exception as e:

                    show_ai_error(
                        e,
                        "Study Planner"
                    )

    elif st.session_state.planner_result:

        st.markdown(
            st.session_state.planner_result
        )


# =========================================================
# DATABASE HISTORY
# =========================================================

if st.session_state.history_open:

    st.markdown("---")

    st.markdown(
        "## 🗂️ EduMind AI History"
    )

    st.write(
        "Your previous chats, quiz results and study plans "
        "are stored locally using SQLite."
    )

    history_tab1, history_tab2, history_tab3 = st.tabs(
        [
            "💬 Chat History",
            "🎯 Quiz History",
            "📅 Study Plans"
        ]
    )

    with history_tab1:

        try:

            chat_history = get_chat_history(
                limit=50
            )

        except Exception as e:

            chat_history = []

            st.error(
                f"⚠️ Could not load chat history.\n\n{str(e)}"
            )

        if not chat_history:

            st.info(
                "No saved chat history yet."
            )

        else:

            for role, content, timestamp in chat_history:

                icon = (
                    "👤"
                    if role == "user"
                    else "🤖"
                )

                st.markdown(
                    f"**{icon} "
                    f"{role.title()}**  "
                    f"_{timestamp}_"
                )

                st.markdown(
                    content
                )

                st.divider()

        if st.button(
            "🗑️ Delete Saved Chat History"
        ):

            try:

                clear_chat_history()

                st.success(
                    "Saved chat history deleted."
                )

                st.rerun()

            except Exception as e:

                st.error(
                    f"⚠️ Could not delete history.\n\n{str(e)}"
                )

    with history_tab2:

        try:

            quiz_history = get_quiz_results(
                limit=20
            )

        except Exception as e:

            quiz_history = []

            st.error(
                f"⚠️ Could not load quiz history.\n\n{str(e)}"
            )

        if not quiz_history:

            st.info(
                "No quiz results saved yet."
            )

        else:

            for (
                score,
                total,
                percentage,
                timestamp
            ) in quiz_history:

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Score",
                        f"{score}/{total}"
                    )

                with col2:

                    st.metric(
                        "Percentage",
                        f"{percentage:.0f}%"
                    )

                with col3:

                    st.write(
                        "**Date & Time**"
                    )

                    st.write(
                        timestamp
                    )

                st.divider()

    with history_tab3:

        try:

            plans = get_study_plans(
                limit=10
            )

        except Exception as e:

            plans = []

            st.error(
                f"⚠️ Could not load study plans.\n\n{str(e)}"
            )

        if not plans:

            st.info(
                "No saved study plans yet."
            )

        else:

            for (
                subjects_saved,
                days_saved,
                hours_saved,
                goal_saved,
                plan_saved,
                timestamp
            ) in plans:

                with st.expander(
                    f"📅 {timestamp}"
                ):

                    st.write(
                        f"**Subjects:** "
                        f"{subjects_saved}"
                    )

                    st.write(
                        f"**Days:** "
                        f"{days_saved}"
                    )

                    st.write(
                        f"**Hours per day:** "
                        f"{hours_saved}"
                    )

                    st.write(
                        f"**Goal:** "
                        f"{goal_saved}"
                    )

                    st.markdown("---")

                    st.markdown(
                        plan_saved
                    )

                    st.download_button(
                        "⬇️ Download This Plan",
                        data=(
                            "EDUMIND AI\n"
                            "STUDY PLAN\n"
                            "================\n\n"
                            + plan_saved
                        ),
                        file_name="study_plan_history.txt",
                        mime="text/plain",
                        key=f"download_plan_{timestamp}"
                    )

    if st.button(
        "✖️ Close History"
    ):

        st.session_state.history_open = False

        st.rerun()


# =========================================================
# WELCOME SCREEN
# =========================================================

if (
    len(st.session_state.messages) == 0
    and not st.session_state.quiz_started
    and not st.session_state.quiz_finished
    and not st.session_state.planner_open
    and not st.session_state.coding_open
    and not st.session_state.history_open
    and not st.session_state.dashboard_open
    and not st.session_state.export_open
):

    st.markdown(
        "### 👋 Welcome to EduMind AI"
    )

    st.write(
        "Your academic assistant for learning, revision, "
        "programming, exams, viva preparation and study planning."
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            """
            <div class="feature-box">
            <b>💬 AI Chat</b><br>
            Ask academic questions and get contextual answers.
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            """
            <div class="feature-box">
            <b>📚 PDF Study Assistant</b><br>
            Upload study material and ask questions from it.
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            """
            <div class="feature-box">
            <b>🎯 Interactive Quiz</b><br>
            Test your knowledge and track your score.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown(
        "### 💡 Try asking"
    )

    examples = [
        "Explain artificial intelligence in simple words.",
        "Give me important viva questions for Python.",
        "Create a 7-day study plan.",
        "Explain SQL joins with examples."
    ]

    for question in examples:

        st.write(
            f"• {question}"
        )


# =========================================================
# CHAT HISTORY DISPLAY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

prompt = st.chat_input(
    "Ask EduMind AI anything about your studies..."
)


# =========================================================
# CHAT RESPONSE
# =========================================================

if prompt:

    prompt = prompt.strip()

    if not prompt:

        st.warning(
            "Please enter a question before sending."
        )

    else:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt
            }
        )

        try:

            save_chat(
                "user",
                prompt
            )

        except Exception:

            pass

        with st.chat_message(
            "user"
        ):

            st.markdown(
                prompt
            )

        with st.chat_message(
            "assistant"
        ):

            with st.spinner(
                "🤖 EduMind AI is thinking..."
            ):

                try:

                    total_start = time.time()

                    # =================================================
                    # ACADEMIC MODE
                    # =================================================

                    mode_instructions = {

                        "General Academic":
                            "Explain academic concepts clearly using simple language and examples.",

                        "Exam Preparation":
                            "Focus on exam-oriented answers, important points and revision.",

                        "Programming Help":
                            "Act as a programming tutor. Explain logic, errors and corrected code.",

                        "Viva Preparation":
                            "Give direct viva-style answers with short explanations.",

                        "Assignment Help":
                            "Provide structured academic help suitable for assignments.",

                        "Study Planning":
                            "Create practical study plans based on the student's available time."
                    }

                    mode_instruction = (
                        mode_instructions.get(
                            st.session_state.mode,
                            mode_instructions[
                                "General Academic"
                            ]
                        )
                    )

                    # =================================================
                    # RAG SEARCH
                    # =================================================

                    material_context = ""

                    source_results = []

                    search_time = 0

                    if (
                        st.session_state.rag_ready
                        and st.session_state.rag_engine is not None
                    ):

                        search_start = time.time()

                        source_results = (
                            st.session_state
                            .rag_engine
                            .search(
                                prompt,
                                top_k=3
                            )
                        )

                        search_time = (
                            time.time()
                            - search_start
                        )

                        if source_results:

                            context_parts = []

                            for result in source_results:

                                context_parts.append(
                                    f"[Page {result['page']}]\n"
                                    f"{result['text']}"
                                )

                            material_context = (
                                "\n\n".join(
                                    context_parts
                                )
                            )

                            material_context = (
                                material_context[:6000]
                            )

                    # =================================================
                    # SOURCE INSTRUCTION
                    # =================================================

                    if material_context:

                        source_instruction = f"""
The student has uploaded academic study material.

Use the retrieved material when relevant.

IMPORTANT:
- Do not invent information.
- Prefer the uploaded material for PDF-related questions.
- If the answer is not supported by the retrieved material,
  clearly say so.

Retrieved material:

{material_context}
"""

                    elif st.session_state.rag_ready:

                        source_instruction = """
The student has uploaded study material,
but no strongly matching section was retrieved.

Use general academic knowledge if appropriate.

Do not claim the answer came from the PDF.
"""

                    else:

                        source_instruction = """
No PDF study material is currently available.

Use general academic knowledge.
"""

                    # =================================================
                    # CONVERSATION CONTEXT
                    # =================================================

                    recent_messages = (
                        st.session_state.messages[-6:]
                    )

                    conversation_context = ""

                    for message in recent_messages:

                        conversation_context += (
                            f"{message['role'].upper()}: "
                            f"{message['content']}\n"
                        )

                    # =================================================
                    # FULL PROMPT
                    # =================================================

                    full_prompt = f"""
You are EduMind AI, an AI-powered academic learning
assistant for college students.

Current academic mode:
{st.session_state.mode}

Mode instructions:
{mode_instruction}

Rules:

1. Give accurate academic information.
2. Explain difficult concepts simply.
3. Use headings and bullet points when useful.
4. For programming questions, give correct code.
5. For exam questions, highlight important points.
6. For viva questions, keep answers direct.
7. Use uploaded study material when relevant.
8. Never invent information from uploaded material.
9. Maintain conversation context.
10. Keep the answer useful and focused.

{source_instruction}

Recent conversation:

{conversation_context}

Current student question:

{prompt}

Answer now.
"""

                    # =================================================
                    # GEMINI
                    # =================================================

                    ai_start = time.time()

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                            max_output_tokens=1200
                        )
                    )

                    ai_time = (
                        time.time()
                        - ai_start
                    )

                    answer = get_ai_text(
                        response
                    )

                    st.markdown(
                        answer
                    )

                    # =================================================
                    # SOURCE CITATIONS
                    # =================================================

                    if source_results:

                        st.markdown(
                            "### 📚 Sources from Uploaded Material"
                        )

                        seen_pages = set()

                        for source_index, result in enumerate(
                            source_results,
                            start=1
                        ):

                            page = result.get(
                                "page",
                                "Unknown"
                            )

                            if page in seen_pages:
                                continue

                            seen_pages.add(page)

                            with st.expander(
                                f"📄 Page {page} — Source {source_index}"
                            ):

                                st.write(
                                    result.get(
                                        "text",
                                        "Source text unavailable."
                                    )
                                )

                                st.caption(
                                    f"Semantic relevance score: "
                                    f"{result.get('score', 0):.2f}"
                                )

                    elif st.session_state.rag_ready:

                        st.caption(
                            "ℹ️ No strongly matching PDF source "
                            "was found for this question."
                        )

                    # =================================================
                    # SAVE ASSISTANT MESSAGE
                    # =================================================

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer
                        }
                    )

                    try:

                        save_chat(
                            "assistant",
                            answer
                        )

                    except Exception:

                        pass

                    # =================================================
                    # CHAT EXPORT
                    # =================================================

                    st.download_button(
                        "⬇️ Download This Answer",
                        data=answer,
                        file_name="edumind_answer.txt",
                        mime="text/plain"
                    )

                    # =================================================
                    # RESPONSE DETAILS
                    # =================================================

                    total_time = (
                        time.time()
                        - total_start
                    )

                    with st.expander(
                        "⚙️ Response details"
                    ):

                        st.write(
                            f"🔎 Semantic search: "
                            f"{search_time:.2f} seconds"
                        )

                        st.write(
                            f"🤖 AI generation: "
                            f"{ai_time:.2f} seconds"
                        )

                        st.write(
                            f"⏱️ Total: "
                            f"{total_time:.2f} seconds"
                        )

                        if source_results:

                            unique_pages = sorted(
                                {
                                    r["page"]
                                    for r in source_results
                                    if "page" in r
                                }
                            )

                            if unique_pages:

                                st.write(
                                    f"📚 Source pages: "
                                    f"{', '.join(map(str, unique_pages))}"
                                )

                except Exception as e:

                    if is_quota_error(e):

                        error_message = (
                            "⚠️ Gemini API quota is currently "
                            "exhausted. Please try again after "
                            "the quota resets."
                        )

                    else:

                        error_message = (
                            "⚠️ Something went wrong while "
                            "processing your question.\n\n"
                            f"{str(e)}"
                        )

                    st.error(
                        error_message
                    )

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": error_message
                        }
                    )

                    try:

                        save_chat(
                            "assistant",
                            error_message
                        )

                    except Exception:

                        pass