import pytest

from agentic.nodes.decision_ontology import SEVERITY_SCORE, decision_node_ontology


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    """판정 테스트가 로컬 incidents.db 상태에 영향받지 않게 한다."""
    import agentic.nodes.decision_ontology as mod

    monkeypatch.setattr(mod, "DB_PATH", str(tmp_path / "empty.db"))


class TestDecisionNodeOntology:
    def _base_state(self, **overrides):
        state = {
            "fall_detected": True,
            "no_movement_seconds": 45.0,
            "estimated_age": "elderly",
            "location_type": "bathroom",
            "hazards_detected": [],
            "pose_data": {"angle": 75, "velocity": 20},
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "camera_id": "01",
        }
        state.update(overrides)
        return state

    def test_returns_all_required_keys(self):
        r = decision_node_ontology(self._base_state())
        for key in (
            "severity",
            "severity_score",
            "recommended_actions",
            "auto_action_required",
            "fired_rules",
            "decision_mode",
        ):
            assert key in r, f"{key} 누락"

    def test_bathroom_elderly_long_immobility_is_high(self):
        r = decision_node_ontology(self._base_state())
        assert r["severity"] == "HIGH"
        assert r["auto_action_required"] is True

    def test_score_is_fixed_mapping(self):
        r = decision_node_ontology(self._base_state())
        assert r["severity_score"] == SEVERITY_SCORE["HIGH"] == 90

    def test_score_never_varies_for_same_severity(self):
        a = decision_node_ontology(self._base_state())
        b = decision_node_ontology(self._base_state(location_type="stairs"))
        assert a["severity"] == b["severity"] == "HIGH"
        assert a["severity_score"] == b["severity_score"]

    def test_fired_rules_are_serialisable_dicts(self):
        r = decision_node_ontology(self._base_state())
        assert r["fired_rules"]
        for item in r["fired_rules"]:
            assert set(item) == {"rule_id", "severity", "description"}
            assert isinstance(item["rule_id"], str)

    def test_mode_is_ontology(self):
        r = decision_node_ontology(self._base_state())
        assert r["decision_mode"] == "ontology"

    def test_repeated_calls_are_identical(self):
        """난수가 없으므로 10회 호출 결과가 완전히 같아야 한다."""
        results = [decision_node_ontology(self._base_state()) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_low_case_logs_only(self):
        r = decision_node_ontology(
            self._base_state(
                location_type="hallway",
                estimated_age="adult",
                no_movement_seconds=2.0,
                pose_data={"angle": 20, "velocity": 0},
            )
        )
        assert r["severity"] == "LOW"
        assert r["recommended_actions"] == ["log_to_db"]
        assert r["auto_action_required"] is False


class TestFallback:
    def test_engine_failure_falls_back_visibly(self, monkeypatch):
        """엔진이 죽어도 파이프라인은 살아야 하되, 폴백이 보여야 한다."""
        import agentic.nodes.decision_ontology as mod

        def boom():
            raise RuntimeError("prolog down")

        monkeypatch.setattr(mod, "get_engine", boom)

        r = mod.decision_node_ontology({
            "no_movement_seconds": 40.0,
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
            "pose_data": {"angle": 40, "velocity": 0},
        })
        assert r["severity"] in ("LOW", "MEDIUM", "HIGH")
        assert r["decision_mode"] == "ontology_fallback"
        assert r["fired_rules"] == []


class TestNodeUsesHistory:
    def test_node_passes_camera_id_to_history(self, monkeypatch):
        import agentic.nodes.decision_ontology as mod

        seen = {}

        def fake_history(db_path, camera_id, within_days=3):
            seen["camera_id"] = camera_id
            return ["prior_incident('INC-A', '07', 1440)"]

        monkeypatch.setattr(mod, "history_facts", fake_history)

        r = mod.decision_node_ontology({
            "no_movement_seconds": 12.0,
            "estimated_age": "adult",
            "location_type": "hallway",
            "hazards_detected": [],
            "pose_data": {"angle": 30, "velocity": 0},
            "camera_id": "07",
        })
        assert seen["camera_id"] == "07"
        assert r["severity"] == "HIGH"
        assert "r6" in [x["rule_id"] for x in r["fired_rules"]]
