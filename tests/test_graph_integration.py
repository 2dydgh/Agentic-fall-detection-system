import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    not pytest.importorskip("ultralytics", reason="ultralytics not installed"),
    reason="ultralytics required for graph integration tests",
)


class TestGraphAudioIntegration:
    def test_state_has_audio_fields_after_invoke(self):
        """그래프 실행 후 state에 오디오 관련 필드가 있어야 함"""
        from agentic.graph import create_fall_detection_graph

        graph = create_fall_detection_graph(
            model_path="models/yolov26n-pose.pt",
            skip_vlm=True,
            skip_audio=True,
        )

        # 더미 프레임 (검은 화면)
        dummy_frame = np.zeros((740, 980, 3), dtype=np.uint8)
        state = {
            "frame": dummy_frame,
            "fall_detected": False,
            "pose_data": {},
            "no_movement_seconds": 0.0,
            "track_id": None,
            "annotated_frame": None,
            "scene_description": "",
            "estimated_age": "unknown",
            "location_type": "other",
            "hazards_detected": [],
            "severity": "LOW",
            "severity_score": 0,
            "recommended_actions": [],
            "auto_action_required": False,
            "actions_taken": [],
            "incident_id": None,
            "snapshot_path": None,
            # 오디오 필드
            "audio_chunk": None,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "audio_detected_labels": [],
        }

        result = graph.invoke(state)

        # 오디오 필드가 state에 존재해야 함
        assert "audio_scream_detected" in result
        assert "audio_impact_detected" in result
        assert "audio_confidence" in result

    def test_graph_creation_with_skip_audio_flag(self):
        """skip_audio=True로 그래프 생성 가능"""
        from agentic.graph import create_fall_detection_graph

        graph = create_fall_detection_graph(
            model_path="models/yolov26n-pose.pt",
            skip_vlm=True,
            skip_audio=True,
        )
        assert graph is not None
