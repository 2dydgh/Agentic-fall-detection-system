"""
각 모달리티(Pose, Audio, VLM)의 raw 출력을 고정 크기 feature vector로 변환.

Pose  → 6-dim: [angle, velocity, no_movement_seconds, angle_norm, vel_norm, duration_norm]
Audio → 6-dim: [scream, impact, confidence, scream_and_impact, high_confidence, any_detection]
VLM   → 6-dim: [is_elderly, is_stairs, is_bathroom, has_hazards, hazard_count_norm, dangerous_location]

총 3개 모달리티 x 6-dim = (3, 6) 텐서 → Self-Attention 입력
"""

import torch
import numpy as np


FEATURE_DIM = 6  # 각 모달리티 feature 차원


def _pose_features(state: dict) -> np.ndarray:
    """Pose 모달리티 → 6-dim feature vector"""
    pose_data = state.get("pose_data", {})
    angle = pose_data.get("angle", 0.0)
    velocity = abs(pose_data.get("velocity", 0.0))
    no_movement = state.get("no_movement_seconds", 0.0)

    return np.array([
        angle / 90.0,                          # 각도 정규화 (0~1)
        min(velocity / 30.0, 1.0),             # 속도 정규화 (0~1)
        min(no_movement / 10.0, 1.0),          # 부동 시간 정규화 (0~1)
        1.0 if angle > 35 else 0.0,            # 각도 임계치 초과 여부
        1.0 if velocity > 15 else 0.0,         # 속도 임계치 초과 여부
        min(no_movement / 5.0, 1.0),           # 부동 시간 심각도
    ], dtype=np.float32)


def _audio_features(state: dict) -> np.ndarray:
    """Audio 모달리티 → 6-dim feature vector"""
    scream = float(state.get("audio_scream_detected", False))
    impact = float(state.get("audio_impact_detected", False))
    confidence = state.get("audio_confidence", 0.0)

    return np.array([
        scream,                                 # 비명 감지 (0/1)
        impact,                                 # 충격음 감지 (0/1)
        min(confidence, 1.0),                   # YAMNet confidence (0~1)
        scream * impact,                        # 비명+충격음 동시 감지
        1.0 if confidence > 0.5 else 0.0,       # 높은 신뢰도 여부
        max(scream, impact),                    # 오디오 이벤트 감지 여부
    ], dtype=np.float32)


def _vlm_features(state: dict) -> np.ndarray:
    """VLM(장면 이해) 모달리티 → 6-dim feature vector"""
    age = state.get("estimated_age", "unknown")
    location = state.get("location_type", "other")
    hazards = state.get("hazards_detected", [])

    is_elderly = 1.0 if age == "elderly" else 0.0
    is_stairs = 1.0 if location == "stairs" else 0.0
    is_bathroom = 1.0 if location == "bathroom" else 0.0
    has_hazards = 1.0 if len(hazards) > 0 else 0.0

    return np.array([
        is_elderly,                             # 고령자 여부
        is_stairs,                              # 계단 여부
        is_bathroom,                            # 욕실 여부
        has_hazards,                            # 위험 요소 존재
        min(len(hazards) / 3.0, 1.0),          # 위험 요소 수 정규화
        max(is_stairs, is_bathroom),            # 위험 장소 여부
    ], dtype=np.float32)


def extract_features(state: dict) -> torch.Tensor:
    """
    State에서 3개 모달리티 feature를 추출하여 (3, 6) 텐서 반환.

    Returns:
        torch.Tensor: shape (3, FEATURE_DIM) — [pose, audio, vlm]
    """
    pose = _pose_features(state)
    audio = _audio_features(state)
    vlm = _vlm_features(state)

    features = np.stack([pose, audio, vlm], axis=0)  # (3, 6)
    return torch.tensor(features, dtype=torch.float32)
