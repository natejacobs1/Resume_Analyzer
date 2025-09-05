import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "resumes.db"

def _get_conn():
    return sqlite3.connect(DB_PATH)

def init_database():
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payload TEXT NOT NULL,
            created_at TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resume_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER,
            payload TEXT NOT NULL,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_resume_data(resume_payload: dict):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO resume_data (payload, created_at) VALUES (?, ?)",
                (json.dumps(resume_payload), resume_payload.get("created_at")))
    resume_id = cur.lastrowid
    conn.commit()
    conn.close()
    return resume_id

def save_analysis_data(resume_id, analysis_payload: dict):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO resume_analysis (resume_id, payload, created_at) VALUES (?, ?, ?)",
                (resume_id, json.dumps(analysis_payload), analysis_payload.get("created_at")))
    conn.commit()
    conn.close()