import numpy as np
import pytest
from agentic.nodes.audio import AudioNode


class TestAudioNode:
    def test_process_with_none_chunk_returns_defaults(self):
        """오디오 청크가 None이면 기본값 반환 (감지 없음)"""
        node = AudioNode(skip_model=True)
        state = {"audio_chunk": None}
        result = node.process(state)
        assert result["audio_scream_detected"] is False
        assert result["audio_impact_detected"] is False
        assert result["audio_confidence"] == 0.0
        assert result["audio_detected_labels"] == []

    def test_process_returns_required_keys(self):
        """AudioNode 결과에 필수 키들이 모두 있어야 함"""
        node = AudioNode(skip_model=True)
        # 무음 청크
        silent_chunk = np.zeros(15600, dtype=np.float32)
        state = {"audio_chunk": silent_chunk}
        result = node.process(state)
        required_keys = [
            "audio_scream_detected",
            "audio_impact_detected",
            "audio_confidence",
            "audio_detected_labels",
        ]
        for key in required_keys:
            assert key in result

    def test_process_with_silent_audio(self):
        """무음 입력은 아무것도 감지하지 않아야 함 (skip_model로 TDD 사이클 유지)"""
        node = AudioNode(skip_model=True)
        silent_chunk = np.zeros(15600, dtype=np.float32)
        state = {"audio_chunk": silent_chunk}
        result = node.process(state)
        assert result["audio_scream_detected"] is False
        assert result["audio_impact_detected"] is False
