"""
비동기 Agent가 Tool Calling으로 호출할 수 있는 도구 모음.
각 도구는 순수 함수이며, TOOL_SCHEMAS에 JSON 스키마가 정의된다.
"""
import os
import sqlite3

TOOL_SCHEMAS = [
    {
        "name": "query_incident_history",
        "description": "Query past incident records from DB for a specific location. Use this to check if there were recent false positives or missed detections in the area.",
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string"},
                "location": {"type": "string", "description": "Location type to filter (e.g. stairs, hallway)"},
                "limit": {"type": "integer", "description": "Max number of records to return"},
            },
            "required": ["db_path"],
        },
    },
    {
        "name": "escalate_emergency",
        "description": "Escalate the incident to emergency services (119) or additional responders. Use when the situation is critical and requires immediate external help.",
        "parameters": {
            "type": "object",
            "properties": {
                "incident_id": {"type": "string"},
                "reason": {"type": "string", "description": "Why escalation is needed"},
                "action": {"type": "string", "enum": ["call_119", "dispatch_nurse", "alert_family"]},
            },
            "required": ["incident_id", "reason", "action"],
        },
    },
    {
        "name": "update_severity",
        "description": "Update the severity level of an existing incident in the DB after re-evaluation. Use when agent analysis determines the initial severity was incorrect.",
        "parameters": {
            "type": "object",
            "properties": {
                "db_path": {"type": "string"},
                "incident_id": {"type": "string"},
                "new_severity": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                "new_score": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["db_path", "incident_id", "new_severity", "new_score", "reason"],
        },
    },
    {
        "name": "reanalyze_with_vlm",
        "description": "Re-analyze the incident snapshot with Florence-2 VLM for a more detailed scene description. Use when the initial scene context is insufficient for making a decision.",
        "parameters": {
            "type": "object",
            "properties": {
                "snapshot_path": {"type": "string", "description": "Path to the incident snapshot image"},
            },
            "required": ["snapshot_path"],
        },
    },
]


def _query_incident_history(db_path: str, location: str = None, limit: int = 10) -> list:
    """과거 인시던트 이력 조회"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        if location:
            rows = conn.execute(
                "SELECT incident_id, timestamp, severity, severity_score, scene_description "
                "FROM incidents WHERE scene_description LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{location}%", limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT incident_id, timestamp, severity, severity_score, scene_description "
                "FROM incidents ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def _escalate_emergency(incident_id: str, reason: str, action: str) -> dict:
    """긴급 에스컬레이션 (Mock — 실제 구현 시 119 API/전화 연동)"""
    print(f"[ESCALATION] incident={incident_id} action={action} reason={reason}")
    return {
        "escalated": True,
        "incident_id": incident_id,
        "action": action,
        "reason": reason,
    }


def _update_severity(db_path: str, incident_id: str, new_severity: str, new_score: int, reason: str) -> dict:
    """인시던트 심각도 업데이트"""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "UPDATE incidents SET severity=?, severity_score=? WHERE incident_id=?",
            (new_severity, new_score, incident_id)
        )
        conn.commit()
        if cursor.rowcount == 0:
            return {"updated": False, "error": f"No incident found with id: {incident_id}"}
        print(f"[AGENT] Severity updated: {incident_id} -> {new_severity} ({new_score}) reason={reason}")
        return {"updated": True, "incident_id": incident_id, "new_severity": new_severity}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()


def _reanalyze_with_vlm(snapshot_path: str) -> dict:
    """Florence-2 VLM으로 스냅샷 재분석"""
    if not os.path.exists(snapshot_path):
        return {"error": f"Snapshot not found: {snapshot_path}"}
    try:
        from agentic.nodes.analysis import AnalysisNode
        import cv2
        frame = cv2.imread(snapshot_path)
        if frame is None:
            return {"error": f"Failed to read image: {snapshot_path}"}
        node = AnalysisNode()
        state = {"frame": frame, "fall_detected": True, "scene_description": ""}
        result = node.process(state)
        return {
            "scene_description": result.get("scene_description", ""),
            "estimated_age": result.get("estimated_age", "unknown"),
            "location_type": result.get("location_type", "other"),
            "hazards_detected": result.get("hazards_detected", []),
        }
    except Exception as e:
        return {"error": f"VLM analysis failed: {e}"}


_TOOL_MAP = {
    "query_incident_history": _query_incident_history,
    "escalate_emergency": _escalate_emergency,
    "update_severity": _update_severity,
    "reanalyze_with_vlm": _reanalyze_with_vlm,
}


def execute_tool(name: str, args: dict):
    """도구 이름과 인자로 도구를 실행하고 결과 반환"""
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return {"error": f"Unknown tool: {name}"}
    return fn(**args)
