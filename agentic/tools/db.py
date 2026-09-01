import os
import sqlite3
import json
import uuid
from datetime import datetime, timedelta

def init_db(db_path: str = "incidents.db"):
    """SQLite DB 초기화"""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id TEXT UNIQUE,
            camera_id TEXT DEFAULT '01',
            timestamp TEXT,
            severity TEXT,
            severity_score INTEGER,
            scene_description TEXT,
            actions_taken TEXT,
            audio_scream_detected INTEGER DEFAULT 0,
            audio_impact_detected INTEGER DEFAULT 0,
            audio_confidence REAL DEFAULT 0.0,
            location_type TEXT DEFAULT 'other',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migration: add camera_id column if table already existed without it
    cursor = conn.execute("PRAGMA table_info(incidents)")
    columns = [row[1] for row in cursor.fetchall()]
    if "camera_id" not in columns:
        conn.execute("ALTER TABLE incidents ADD COLUMN camera_id TEXT DEFAULT '01'")
    if "location_type" not in columns:
        conn.execute(
            "ALTER TABLE incidents ADD COLUMN location_type TEXT DEFAULT 'other'"
        )
    conn.commit()
    conn.close()

def log_to_db(
    db_path: str,
    severity: str,
    scene_description: str,
    severity_score: int,
    actions_taken: list,
    audio_scream_detected: bool = False,
    audio_impact_detected: bool = False,
    audio_confidence: float = 0.0,
    camera_id: str = "01",
    location_type: str = "other",
) -> str:
    """이벤트를 DB에 저장하고 incident_id 반환"""
    now = datetime.now()
    # UUID 추가로 동일 초 내 중복 방지
    incident_id = f"INC-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO incidents (incident_id, camera_id, timestamp, severity, severity_score, scene_description, actions_taken, audio_scream_detected, audio_impact_detected, audio_confidence, location_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        incident_id,
        camera_id,
        now.isoformat(),
        severity,
        severity_score,
        scene_description,
        json.dumps(actions_taken),
        int(audio_scream_detected),
        int(audio_impact_detected),
        audio_confidence,
        location_type,
    ))
    conn.commit()
    conn.close()

    return incident_id


def query_recent_incidents(
    db_path: str,
    camera_id: str,
    within_days: int = 3,
    now: datetime | None = None,
) -> list[dict]:
    """
    지정 카메라의 최근 N일 사건 이력을 최신순으로 반환한다.

    timestamp 컬럼은 ISO 8601 문자열이므로 사전식 비교가 시간순 비교와 일치한다.

    Args:
        now: 기준 시각. 테스트에서 고정 시각을 주입하기 위한 인자.
    """
    if not os.path.exists(db_path):
        return []

    now = now or datetime.now()
    cutoff = (now - timedelta(days=within_days)).isoformat()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT incident_id, timestamp, severity, location_type "
            "FROM incidents "
            "WHERE camera_id = ? AND timestamp >= ? "
            "ORDER BY timestamp DESC",
            (camera_id, cutoff),
        ).fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]
