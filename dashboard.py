import streamlit as st

from database import (
    get_connection,
    get_chat_history,
    get_quiz_results,
    get_study_plans
)


def get_dashboard_stats():

    conn = get_connection()
    cursor = conn.cursor()

    # Total chat messages
    cursor.execute(
        "SELECT COUNT(*) FROM chats"
    )

    total_chats = cursor.fetchone()[0]

    # User questions
    cursor.execute(
        "SELECT COUNT(*) FROM chats WHERE role = 'user'"
    )

    total_questions = cursor.fetchone()[0]

    # AI responses
    cursor.execute(
        "SELECT COUNT(*) FROM chats WHERE role = 'assistant'"
    )

    total_answers = cursor.fetchone()[0]

    # Quiz count
    cursor.execute(
        "SELECT COUNT(*) FROM quiz_results"
    )

    total_quizzes = cursor.fetchone()[0]

    # Average quiz score
    cursor.execute(
        "SELECT AVG(percentage) FROM quiz_results"
    )

    avg_score = cursor.fetchone()[0]

    # Best quiz score
    cursor.execute(
        "SELECT MAX(percentage) FROM quiz_results"
    )

    best_score = cursor.fetchone()[0]

    # Study plans
    cursor.execute(
        "SELECT COUNT(*) FROM study_plans"
    )

    total_plans = cursor.fetchone()[0]

    conn.close()

    return {
        "total_chats": total_chats,
        "total_questions": total_questions,
        "total_answers": total_answers,
        "total_quizzes": total_quizzes,
        "avg_score": avg_score or 0,
        "best_score": best_score or 0,
        "total_plans": total_plans
    }


def show_dashboard(pdf_name="", pdf_pages=0):

    st.markdown("---")

    st.markdown(
        "## 📊 Student Dashboard"
    )

    st.write(
        "Track your learning activity, quiz performance "
        "and study planning progress."
    )

    stats = get_dashboard_stats()


    # =====================================================
    # TOP METRICS
    # =====================================================

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "💬 Questions Asked",
            stats["total_questions"]
        )

    with col2:

        st.metric(
            "🎯 Quizzes",
            stats["total_quizzes"]
        )

    with col3:

        st.metric(
            "🏆 Average Score",
            f"{stats['avg_score']:.0f}%"
        )

    with col4:

        st.metric(
            "📅 Study Plans",
            stats["total_plans"]
        )


    # =====================================================
    # LEARNING OVERVIEW
    # =====================================================

    st.markdown(
        "### 📚 Learning Overview"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.info(
            f"""
            **💬 Chat Activity**

            Total interactions:  
            **{stats["total_chats"]}**

            Student questions:  
            **{stats["total_questions"]}

            AI responses:  
            **{stats["total_answers"]}
            """
        )

    with col2:

        st.info(
            f"""
            **🎯 Quiz Performance**

            Quizzes attempted:  
            **{stats["total_quizzes"]}

            Average score:  
            **{stats["avg_score"]:.0f}%**

            Best score:  
            **{stats["best_score"]:.0f}%**
            """
        )

    with col3:

        st.info(
            f"""
            **📅 Study Planning**

            Plans created:  
            **{stats["total_plans"]}

            Current material:  
            **{pdf_name if pdf_name else "No PDF"}**

            Pages:  
            **{pdf_pages if pdf_pages else 0}**
            """
        )


    # =====================================================
    # QUIZ PERFORMANCE
    # =====================================================

    st.markdown(
        "### 📈 Quiz Performance"
    )

    quiz_results = get_quiz_results(
        limit=20
    )

    if quiz_results:

        for index, (
            score,
            total,
            percentage,
            timestamp
        ) in enumerate(
            quiz_results,
            start=1
        ):

            col1, col2, col3 = st.columns(3)

            with col1:

                st.write(
                    f"**Quiz {index}**"
                )

            with col2:

                st.write(
                    f"Score: **{score}/{total}**"
                )

            with col3:

                st.write(
                    f"**{percentage:.0f}%** "
                    f"— {timestamp}"
                )

            st.progress(
                min(
                    max(
                        percentage / 100,
                        0.0
                    ),
                    1.0
                )

            )

    else:

        st.info(
            "Complete a quiz to see your performance here."
        )


    # =====================================================
    # RECENT CHAT ACTIVITY
    # =====================================================

    st.markdown(
        "### 💬 Recent Learning Activity"
    )

    recent_chats = get_chat_history(
        limit=8
    )

    if recent_chats:

        for role, content, timestamp in recent_chats:

            if role == "user":

                st.markdown(
                    f"👤 **You** — {timestamp}"
                )

                st.write(
                    content[:250]
                )

            else:

                st.markdown(
                    f"🤖 **EduMind AI** — {timestamp}"
                )

                st.write(
                    content[:250]
                )

            st.divider()

    else:

        st.info(
            "No learning activity recorded yet."
        )


    # =====================================================
    # STUDY PLAN HISTORY
    # =====================================================

    st.markdown(
        "### 📅 Recent Study Plans"
    )

    plans = get_study_plans(
        limit=5
    )

    if plans:

        for (
            subjects,
            days,
            hours,
            goal,
            plan,
            timestamp
        ) in plans:

            with st.expander(
                f"📅 {timestamp} — {goal}"
            ):

                st.write(
                    f"**Subjects:** {subjects}"
                )

                st.write(
                    f"**Duration:** {days} days"
                )

                st.write(
                    f"**Study time:** "
                    f"{hours} hours/day"
                )

                st.markdown(
                    "---"
                )

                st.markdown(
                    plan
                )

    else:

        st.info(
            "Create a study plan to see it here."
        )


    # =====================================================
    # LEARNING STATUS
    # =====================================================

    st.markdown(
        "### 🧠 Learning Status"
    )

    if stats["total_quizzes"] == 0:

        st.warning(
            "🎯 Start your first quiz to begin tracking "
            "your academic performance."
        )

    elif stats["avg_score"] >= 80:

        st.success(
            "🌟 Excellent performance! "
            "Keep maintaining your consistency."
        )

    elif stats["avg_score"] >= 60:

        st.info(
            "👍 Good progress! "
            "Focus on revision to improve your score."
        )

    else:

        st.warning(
            "📚 More revision is recommended. "
            "Use the Study Tools and Quiz Mode regularly."
        )