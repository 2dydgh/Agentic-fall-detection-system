import sqlite3
import json
import uuid
from datetime import datetime

def init_db(db_path: str = "incidents.db"):
    """SQLite DB 초기화"""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE,
            timestamp TEXT,
            severity TEXT,
            severity_score INTEGER,
            scene_description TEXT,
            actions_taken TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_to_db(
    db_path: str,
    severity: str,
    scene_description: str,
    severity_score: int,
    actions_taken: list
) -> str:
    """이벤트를 DB에 저장하고 incident_id 반환"""
    now = datetime.now()
    # UUID 추가로 동일 초 내 중복 방지
    incident_id = f"INC-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO incidents (incident_id, timestamp, severity, severity_score, scene_description, actions_taken)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        incident_id,
        now.isoformat(),
        severity,
        severity_score,
        scene_description,
        json.dumps(actions_taken)
    ))
    conn.commit()
    conn.close()

    return incident_id
