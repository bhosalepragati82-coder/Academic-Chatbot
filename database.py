import sqlite3
from datetime import datetime


DB_NAME = "edumind.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subjects TEXT NOT NULL,
            days INTEGER NOT NULL,
            hours REAL NOT NULL,
            goal TEXT NOT NULL,
            plan TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_chat(role, content):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO chats (role, content, timestamp)
        VALUES (?, ?, ?)
        """,
        (
            role,
            content,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


def get_chat_history(limit=50):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content, timestamp
        FROM chats
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def clear_chat_history():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM chats")

    conn.commit()
    conn.close()


def save_quiz_result(score, total):

    conn = get_connection()
    cursor = conn.cursor()

    percentage = (score / total) * 100

    cursor.execute(
        """
        INSERT INTO quiz_results
        (score, total, percentage, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (
            score,
            total,
            percentage,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


def get_quiz_results(limit=10):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT score, total, percentage, timestamp
        FROM quiz_results
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def save_study_plan(
    subjects,
    days,
    hours,
    goal,
    plan
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO study_plans
        (subjects, days, hours, goal, plan, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            subjects,
            days,
            hours,
            goal,
            plan,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    conn.commit()
    conn.close()


def get_study_plans(limit=10):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT subjects, days, hours, goal, plan, timestamp
        FROM study_plans
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows