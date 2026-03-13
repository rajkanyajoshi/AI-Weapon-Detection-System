import sqlite3
from datetime import datetime

DB_PATH = "detections.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id TEXT,
            weapon_type TEXT,
            confidence REAL,
            severity INTEGER,
            date TEXT,
            time TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_detection(camera_id, weapon_type, confidence, severity):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections (camera_id, weapon_type, confidence, severity, date, time)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (camera_id, weapon_type, confidence, severity, date_str, time_str))
    conn.commit()
    conn.close()

def fetch_detections(limit=100):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows
