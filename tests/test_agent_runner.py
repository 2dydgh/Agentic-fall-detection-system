import os
import time
import tempfile
import pytest
from agentic.agent.runner import AgentRunner


class TestAgentRunner:
    def test_dispatch_runs_in_background(self):
        """dispatch가 블로킹하지 않고 즉시 반환해야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            runner = AgentRunner(db_path=db_path, skip_llm=True)
            context = {
                "incident_id": "INC-TEST-001",
                "severity": "HIGH",
                "severity_score": 85,
                "scene_description": "test",
                "estimated_age": "elderly",
                "location_type": "stairs",
                "audio_scream_detected": True,
                "audio_impact_detected": False,
                "no_movement_seconds": 8.0,
                "db_path": db_path,
            }
            start = time.time()
            runner.dispatch(context)
            elapsed = time.time() - start
            assert elapsed < 1.0
            runner.wait_all(timeout=5.0)
        finally:
            os.unlink(db_path)

    def test_get_results_returns_completed(self):
        """완료된 Agent 결과를 메모리와 DB 모두에서 조회할 수 있어야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            runner = AgentRunner(db_path=db_path, skip_llm=True)
            context = {
                "incident_id": "INC-TEST-002",
                "severity": "HIGH",
                "severity_score": 90,
                "scene_description": "test",
                "estimated_age": "elderly",
                "location_type": "stairs",
                "audio_scream_detected": True,
                "audio_impact_detected": True,
                "no_movement_seconds": 10.0,
                "db_path": db_path,
            }
            runner.dispatch(context)
            runner.wait_all(timeout=5.0)

            # 메모리 캐시 확인
            results = runner.get_results()
            assert len(results) >= 1
            assert results[0]["incident_id"] == "INC-TEST-002"
            assert "final_assessment" in results[0]

            # DB 영속 저장 확인
            db_results = runner.get_results_from_db()
            assert len(db_results) >= 1
            assert db_results[0]["incident_id"] == "INC-TEST-002"
            assert "final_assessment" in db_results[0]
        finally:
            os.unlink(db_path)

    def test_dispatch_skips_low_severity(self):
        """LOW severity는 Agent를 실행하지 않아야 함"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            from agentic.tools.db import init_db
            init_db(db_path)
            runner = AgentRunner(db_path=db_path, skip_llm=True)
            context = {
                "incident_id": "INC-TEST-003",
                "severity": "LOW",
                "severity_score": 30,
                "scene_description": "test",
                "db_path": db_path,
            }
            runner.dispatch(context)
            runner.wait_all(timeout=2.0)
            results = runner.get_results()
            assert len(results) == 0
        finally:
            os.unlink(db_path)


class TestFiredRulesPropagation:
    """온톨로지 모드의 발동 규칙이 Track 2 까지 전달되는지 검증한다.

    Track 1(심볼릭 추론)이 확정한 판정 근거를 Track 2(생성형 판단)가
    입력으로 받는 구조이며, 이 연결이 끊기면 Track 2 는 같은 정보를
    도구 호출로 다시 찾아야 한다.
    """

    def _action_node(self, db_path, captured):
        from agentic.nodes.action import ActionNode

        class _FakeRunner:
            def dispatch(self, context):
                captured.append(context)

        node = ActionNode(db_path=db_path, agent_runner=_FakeRunner())
        return node

    def _state(self, **overrides):
        state = {
            "severity": "HIGH",
            "severity_score": 90,
            "recommended_actions": ["log_to_db"],
            "scene_description": "",
            "estimated_age": "elderly",
            "location_type": "bathroom",
            "no_movement_seconds": 45.0,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
        }
        state.update(overrides)
        return state

    def test_action_node_forwards_fired_rules(self):
        captured = []
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            node = self._action_node(db_path, captured)
            rules = [{"rule_id": "r1", "severity": "high", "description": "고위험 구역 30초"}]
            node.process(self._state(fired_rules=rules))
            assert captured, "dispatch 가 호출되지 않음"
            assert captured[0]["fired_rules"] == rules
        finally:
            os.unlink(db_path)

    def test_action_node_defaults_to_empty_list(self):
        """다른 판정 모드에서는 fired_rules 가 없다. 키는 있어야 한다."""
        captured = []
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            node = self._action_node(db_path, captured)
            node.process(self._state())
            assert captured[0]["fired_rules"] == []
        finally:
            os.unlink(db_path)


class TestEscalationPromptCarriesRules:
    def _context(self, **overrides):
        ctx = {
            "incident_id": "INC-TEST",
            "severity": "HIGH",
            "severity_score": 90,
            "db_path": "/tmp/x.db",
        }
        ctx.update(overrides)
        return ctx

    def test_prompt_lists_fired_rules(self, monkeypatch):
        from agentic.agent import escalation_agent as mod

        captured = {}

        def fake_chat(model, messages, format=None, **kw):
            captured["user"] = messages[-1]["content"]
            return {"message": {"content": '{"done": true, "final_assessment": "ok", "escalation_needed": false}'}}

        monkeypatch.setattr(mod, "_get_client", lambda: type("C", (), {"chat": staticmethod(fake_chat)})())

        mod.EscalationAgent(max_iterations=1).run(self._context(fired_rules=[
            {"rule_id": "r1", "severity": "high", "description": "고위험 구역 30초"},
            {"rule_id": "r5", "severity": "high", "description": "취약 계층 + 고위험 구역"},
        ]))

        assert "Fired rules" in captured["user"]
        assert "r1" in captured["user"] and "r5" in captured["user"]
        assert "고위험 구역 30초" in captured["user"]

    def test_prompt_omits_line_when_no_rules(self, monkeypatch):
        """온톨로지 모드가 아닐 때 빈 줄이 들어가면 안 된다."""
        from agentic.agent import escalation_agent as mod

        captured = {}

        def fake_chat(model, messages, format=None, **kw):
            captured["user"] = messages[-1]["content"]
            return {"message": {"content": '{"done": true, "final_assessment": "ok", "escalation_needed": false}'}}

        monkeypatch.setattr(mod, "_get_client", lambda: type("C", (), {"chat": staticmethod(fake_chat)})())

        mod.EscalationAgent(max_iterations=1).run(self._context())
        assert "Fired rules" not in captured["user"]
