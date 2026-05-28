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
