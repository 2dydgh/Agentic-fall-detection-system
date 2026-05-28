import os
import tempfile
import pytest
from agentic.agent.escalation_agent import EscalationAgent


class TestEscalationAgent:
    def _make_context(self, db_path: str, **overrides):
        """테스트용 인시던트 컨텍스트"""
        ctx = {
            "incident_id": "INC-TEST-001",
            "severity": "HIGH",
            "severity_score": 85,
            "scene_description": "Elderly person fell on stairs",
            "estimated_age": "elderly",
            "location_type": "stairs",
            "audio_scream_detected": True,
            "audio_impact_detected": True,
            "no_movement_seconds": 8.0,
            "db_path": db_path,
        }
        ctx.update(overrides)
        return ctx

    def test_agent_returns_required_keys(self):
        """Agent 결과에 필수 키가 있어야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            agent = EscalationAgent(skip_llm=True)
            ctx = self._make_context(db_path)
            result = agent.run(ctx)
            assert "actions_taken" in result
            assert "final_assessment" in result
            assert isinstance(result["actions_taken"], list)
        finally:
            os.unlink(db_path)

    def test_agent_skip_llm_uses_fallback(self):
        """skip_llm=True일 때 룰 기반 폴백으로 동작"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            agent = EscalationAgent(skip_llm=True)
            ctx = self._make_context(db_path)
            result = agent.run(ctx)
            assert result["final_assessment"] != ""
        finally:
            os.unlink(db_path)

    def test_agent_max_iterations_prevents_infinite_loop(self):
        """max_iterations로 무한 루프 방지"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            agent = EscalationAgent(skip_llm=True, max_iterations=2)
            ctx = self._make_context(db_path)
            result = agent.run(ctx)
            assert len(result["actions_taken"]) <= 2
        finally:
            os.unlink(db_path)
