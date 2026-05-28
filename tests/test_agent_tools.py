import os
import sqlite3
import tempfile
import pytest
from agentic.agent.tools import TOOL_SCHEMAS, execute_tool


class TestAgentTools:
    def test_tool_schemas_has_required_tools(self):
        """Agent에 필요한 도구 스키마가 모두 정의되어 있어야 함"""
        tool_names = {t["name"] for t in TOOL_SCHEMAS}
        assert "query_incident_history" in tool_names
        assert "escalate_emergency" in tool_names
        assert "update_severity" in tool_names
        assert "reanalyze_with_vlm" in tool_names

    def test_each_schema_has_required_fields(self):
        """각 도구 스키마에 name, description, parameters가 있어야 함"""
        for schema in TOOL_SCHEMAS:
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema

    def test_query_incident_history_returns_list(self):
        """query_incident_history가 리스트를 반환해야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            result = execute_tool("query_incident_history", {
                "db_path": db_path,
                "location": "hallway",
                "limit": 5,
            })
            assert isinstance(result, list)
        finally:
            os.unlink(db_path)

    def test_escalate_emergency_returns_dict(self):
        """escalate_emergency가 결과 dict를 반환해야 함"""
        result = execute_tool("escalate_emergency", {
            "incident_id": "INC-TEST-001",
            "reason": "elderly person, no movement for 10s",
            "action": "call_119",
        })
        assert isinstance(result, dict)
        assert "escalated" in result

    def test_update_severity_modifies_db(self):
        """update_severity가 DB의 severity를 변경해야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db, log_to_db
            init_db(db_path)
            inc_id = log_to_db(
                db_path=db_path,
                severity="MEDIUM",
                scene_description="test",
                severity_score=60,
                actions_taken=["log_to_db"],
            )
            result = execute_tool("update_severity", {
                "db_path": db_path,
                "incident_id": inc_id,
                "new_severity": "HIGH",
                "new_score": 90,
                "reason": "agent escalation",
            })
            assert result["updated"] is True

            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT severity, severity_score FROM incidents WHERE incident_id=?",
                (inc_id,)
            ).fetchone()
            conn.close()
            assert row[0] == "HIGH"
            assert row[1] == 90
        finally:
            os.unlink(db_path)

    def test_execute_unknown_tool_returns_error(self):
        """존재하지 않는 도구 호출 시 에러 반환"""
        result = execute_tool("nonexistent_tool", {})
        assert "error" in result

    def test_reanalyze_with_vlm_nonexistent_path_returns_error(self):
        """존재하지 않는 스냅샷 경로로 호출 시 에러 반환"""
        result = execute_tool("reanalyze_with_vlm", {"snapshot_path": "/nonexistent/path.jpg"})
        assert "error" in result

    def test_update_severity_nonexistent_incident_returns_not_updated(self):
        """존재하지 않는 incident_id로 update_severity 호출 시 updated=False 반환"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            result = execute_tool("update_severity", {
                "db_path": db_path,
                "incident_id": "INC-NONEXISTENT-999",
                "new_severity": "HIGH",
                "new_score": 90,
                "reason": "test nonexistent",
            })
            assert result["updated"] is False
        finally:
            os.unlink(db_path)
