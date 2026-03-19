"""
YAMNet 기반 오디오 분류 노드.
오디오 청크를 받아 비명/충격음 감지 여부를 state에 기록한다.
"""
import numpy as np
from typing import Optional
from ..audio.labels import classify_audio_event

# YAMNet 모델은 무거우므로 lazy load
_yamnet_model = None


def _get_yamnet_model():
    global _yamnet_model
    if _yamnet_model is None:
        import tensorflow_hub as hub
        _yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
    return _yamnet_model


class AudioNode:
    """YAMNet을 사용한 오디오 이벤트 감지 노드"""

    def __init__(self, skip_model: bool = False):
        """
        Args:
            skip_model: True이면 YAMNet 로드를 건너뛰고 항상 기본값 반환 (테스트용)
        """
        self._skip_model = skip_model

    def process(self, state: dict) -> dict:
        """
        오디오 청크를 분류하여 결과 반환.

        State에서 읽는 키:
            audio_chunk: Optional[np.ndarray] — 15600 samples, 16kHz, float32

        반환하는 키:
            audio_scream_detected: bool
            audio_impact_detected: bool
            audio_confidence: float
            audio_detected_labels: list[str]
        """
        chunk = state.get("audio_chunk")

        # 오디오 없으면 기본값
        if chunk is None:
            return self._default_result()

        if self._skip_model:
            return self._default_result()

        try:
            model = _get_yamnet_model()
            # YAMNet 추론: waveform → (scores, embeddings, spectrogram)
            scores, embeddings, spectrogram = model(chunk)
            # scores shape: (num_patches, 521) — 패치별 평균을 사용
            avg_scores = np.mean(scores.numpy(), axis=0)
            raw = classify_audio_event(avg_scores)
            return {
                "audio_scream_detected": raw["scream_detected"],
                "audio_impact_detected": raw["impact_detected"],
                "audio_confidence": raw["confidence"],
                "audio_detected_labels": raw["detected_labels"],
            }
        except Exception:
            return self._default_result()

    @staticmethod
    def _default_result() -> dict:
        return {
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "audio_detected_labels": [],
        }
