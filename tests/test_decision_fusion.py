import random
from agentic.nodes.decision import decision_node_rule as decision_node


class TestDecisionFusion:
    def _base_state(self, **overrides):
        """기본 낙상 감지 state (deterministic pose_data)"""
        state = {
            "fall_detected": True,
            "no_movement_seconds": 40.0,
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
            "pose_data": {"angle": 40, "velocity": 0},
            # 오디오 기본값: 감지 없음
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
        }
        state.update(overrides)
        return state

    def test_no_audio_signal_no_bonus(self):
        """오디오 신호 없으면 기존 점수와 동일 (오디오 보너스 0)"""
        random.seed(42)
        state_no_audio = self._base_state()
        result_no_audio = decision_node(state_no_audio)

        random.seed(42)
        state_with_defaults = self._base_state(
            audio_scream_detected=False,
            audio_impact_detected=False,
        )
        result_defaults = decision_node(state_with_defaults)

        assert result_no_audio["severity_score"] == result_defaults["severity_score"]

    def test_scream_adds_bonus(self):
        """비명 감지 시 점수가 15점 증가"""
        random.seed(42)
        state_no_audio = self._base_state()
        score_no_audio = decision_node(state_no_audio)["severity_score"]

        random.seed(42)
        state_scream = self._base_state(
            audio_scream_detected=True,
            audio_confidence=0.8,
        )
        score_scream = decision_node(state_scream)["severity_score"]

        # 비명 보너스는 +15, 단 100점 cap 적용
        expected = min(score_no_audio + 15, 100)
        assert score_scream == expected

    def test_impact_adds_bonus(self):
        """충격음 감지 시 점수가 10점 증가"""
        random.seed(42)
        state_no_audio = self._base_state()
        score_no_audio = decision_node(state_no_audio)["severity_score"]

        random.seed(42)
        state_impact = self._base_state(
            audio_impact_detected=True,
            audio_confidence=0.7,
        )
        score_impact = decision_node(state_impact)["severity_score"]

        expected = min(score_no_audio + 10, 100)
        assert score_impact == expected

    def test_scream_and_impact_adds_both(self):
        """비명 + 충격음 동시 감지 시 +25점 (15+10)"""
        random.seed(42)
        state_no_audio = self._base_state()
        score_no_audio = decision_node(state_no_audio)["severity_score"]

        random.seed(42)
        state_both = self._base_state(
            audio_scream_detected=True,
            audio_impact_detected=True,
            audio_confidence=0.9,
        )
        score_both = decision_node(state_both)["severity_score"]

        expected = min(score_no_audio + 25, 100)
        assert score_both == expected

    def test_max_score_capped_at_100(self):
        """모든 보너스 합산해도 100점을 넘지 않음"""
        state = self._base_state(
            estimated_age="elderly",
            location_type="stairs",
            hazards_detected=["wet floor"],
            audio_scream_detected=True,
            audio_impact_detected=True,
            audio_confidence=0.95,
            pose_data={"angle": 80, "velocity": 50},  # 높은 기본 점수
        )
        result = decision_node(state)
        assert result["severity_score"] <= 100
