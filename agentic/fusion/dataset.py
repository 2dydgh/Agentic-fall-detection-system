"""
학습 데이터 생성기.

도메인 지식 기반으로 다양한 낙상 시나리오의 feature 조합을 생성하고,
rule-based 시스템보다 정교한 severity label을 부여.

Rule-based와의 차이점:
- 모달리티 간 상호작용 반영 (예: 비명+큰 각도 → HIGH 강화)
- 연속적인 severity score 분포 (rule-based의 불연속 bonus 대신)
- 경계 케이스에서 더 세밀한 판정
"""

import numpy as np
import torch
from torch.utils.data import Dataset

from .feature import _pose_features, _audio_features, _vlm_features


# 시나리오 정의: (이름, state 범위, severity_score 범위)
SCENARIOS = [
    # === LOW severity 시나리오 ===
    {
        "name": "minor_stumble",
        "weight": 3,
        "pose": {"angle": (20, 40), "velocity": (0, 10), "no_movement": (0, 1)},
        "audio": {"scream": 0.05, "impact": 0.1, "confidence": (0, 0.3)},
        "vlm": {"elderly": 0.1, "stairs": 0.05, "bathroom": 0.05, "hazards": 0},
        "score": (10, 45),
    },
    {
        "name": "soft_fall_safe_location",
        "weight": 2,
        "pose": {"angle": (35, 55), "velocity": (5, 15), "no_movement": (0, 2)},
        "audio": {"scream": 0.05, "impact": 0.2, "confidence": (0.1, 0.4)},
        "vlm": {"elderly": 0.1, "stairs": 0.0, "bathroom": 0.0, "hazards": 0},
        "score": (25, 50),
    },
    # === MEDIUM severity 시나리오 ===
    {
        "name": "moderate_fall",
        "weight": 3,
        "pose": {"angle": (40, 65), "velocity": (10, 25), "no_movement": (1, 4)},
        "audio": {"scream": 0.2, "impact": 0.4, "confidence": (0.2, 0.6)},
        "vlm": {"elderly": 0.2, "stairs": 0.1, "bathroom": 0.1, "hazards": 0.2},
        "score": (45, 72),
    },
    {
        "name": "fall_with_impact_sound",
        "weight": 2,
        "pose": {"angle": (35, 55), "velocity": (8, 20), "no_movement": (1, 3)},
        "audio": {"scream": 0.1, "impact": 0.8, "confidence": (0.4, 0.8)},
        "vlm": {"elderly": 0.15, "stairs": 0.1, "bathroom": 0.1, "hazards": 0.1},
        "score": (50, 70),
    },
    {
        "name": "elderly_minor_fall",
        "weight": 2,
        "pose": {"angle": (30, 50), "velocity": (5, 15), "no_movement": (1, 3)},
        "audio": {"scream": 0.15, "impact": 0.2, "confidence": (0.1, 0.4)},
        "vlm": {"elderly": 0.9, "stairs": 0.05, "bathroom": 0.1, "hazards": 0.1},
        "score": (50, 72),
    },
    # === HIGH severity 시나리오 ===
    {
        "name": "severe_fall_with_scream",
        "weight": 2,
        "pose": {"angle": (55, 85), "velocity": (15, 30), "no_movement": (3, 8)},
        "audio": {"scream": 0.85, "impact": 0.6, "confidence": (0.5, 0.9)},
        "vlm": {"elderly": 0.3, "stairs": 0.15, "bathroom": 0.15, "hazards": 0.3},
        "score": (72, 95),
    },
    {
        "name": "elderly_fall_dangerous_location",
        "weight": 2,
        "pose": {"angle": (45, 75), "velocity": (10, 25), "no_movement": (2, 7)},
        "audio": {"scream": 0.3, "impact": 0.5, "confidence": (0.3, 0.7)},
        "vlm": {"elderly": 0.9, "stairs": 0.4, "bathroom": 0.4, "hazards": 0.5},
        "score": (70, 92),
    },
    {
        "name": "fall_prolonged_immobile",
        "weight": 2,
        "pose": {"angle": (50, 80), "velocity": (5, 15), "no_movement": (5, 10)},
        "audio": {"scream": 0.4, "impact": 0.3, "confidence": (0.2, 0.6)},
        "vlm": {"elderly": 0.4, "stairs": 0.1, "bathroom": 0.2, "hazards": 0.2},
        "score": (68, 90),
    },
    {
        "name": "catastrophic_fall",
        "weight": 1,
        "pose": {"angle": (70, 90), "velocity": (20, 30), "no_movement": (5, 10)},
        "audio": {"scream": 0.9, "impact": 0.9, "confidence": (0.7, 1.0)},
        "vlm": {"elderly": 0.5, "stairs": 0.3, "bathroom": 0.3, "hazards": 0.6},
        "score": (85, 100),
    },
]

AGE_CHOICES = ["child", "adult", "elderly", "unknown"]
LOCATION_CHOICES = ["stairs", "bathroom", "hallway", "outdoor", "other"]
HAZARD_POOL = ["wet_floor", "sharp_object", "broken_railing", "dim_lighting", "clutter"]


def _sample_state(scenario: dict, rng: np.random.Generator) -> dict:
    """시나리오 정의에서 랜덤 state를 샘플링"""
    p = scenario["pose"]
    a = scenario["audio"]
    v = scenario["vlm"]

    angle = rng.uniform(*p["angle"])
    velocity = rng.uniform(*p["velocity"])
    no_movement = rng.uniform(*p["no_movement"])

    scream = rng.random() < a["scream"]
    impact = rng.random() < a["impact"]
    confidence = rng.uniform(*a["confidence"])

    is_elderly = rng.random() < v["elderly"]
    is_stairs = rng.random() < v["stairs"]
    is_bathroom = rng.random() < v["bathroom"] if not is_stairs else False
    num_hazards = int(rng.random() < v["hazards"]) * rng.integers(1, 4)

    age = "elderly" if is_elderly else rng.choice(["child", "adult", "unknown"])
    location = "stairs" if is_stairs else ("bathroom" if is_bathroom else rng.choice(["hallway", "outdoor", "other"]))
    hazards = list(rng.choice(HAZARD_POOL, size=min(num_hazards, len(HAZARD_POOL)), replace=False)) if num_hazards > 0 else []

    return {
        "pose_data": {"angle": angle, "velocity": velocity},
        "no_movement_seconds": no_movement,
        "audio_scream_detected": bool(scream),
        "audio_impact_detected": bool(impact),
        "audio_confidence": float(confidence),
        "estimated_age": age,
        "location_type": location,
        "hazards_detected": hazards,
    }


def _compute_label(state: dict, score_range: tuple, rng: np.random.Generator) -> tuple[float, int]:
    """
    도메인 지식 기반 severity label 생성.
    모달리티 간 상호작용을 반영하여 score_range 내에서 점수를 조정.
    """
    base = rng.uniform(*score_range)

    # 모달리티 간 상호작용 보정
    angle = state["pose_data"]["angle"]
    scream = state["audio_scream_detected"]
    impact = state["audio_impact_detected"]
    elderly = state["estimated_age"] == "elderly"
    dangerous = state["location_type"] in ["stairs", "bathroom"]

    # 비명 + 큰 각도 → 위험도 상승
    if scream and angle > 50:
        base += rng.uniform(3, 8)
    # 고령자 + 위험 장소 → 위험도 상승
    if elderly and dangerous:
        base += rng.uniform(3, 10)
    # 충격음 + 오래 움직이지 않음 → 위험도 상승
    if impact and state["no_movement_seconds"] > 3:
        base += rng.uniform(2, 7)
    # 비명 + 충격음 동시 → 시너지
    if scream and impact:
        base += rng.uniform(2, 5)

    score = max(0, min(100, base))

    # 클래스 결정
    if score <= 50:
        cls = 0  # LOW
    elif score <= 75:
        cls = 1  # MEDIUM
    else:
        cls = 2  # HIGH

    return score, cls


def generate_dataset(
    n_samples: int = 5000, seed: int = 42
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    학습 데이터 생성.

    Returns:
        features: (n_samples, 3, 6) — 모달리티 feature 텐서
        scores: (n_samples,) — severity score (0~100)
        classes: (n_samples,) — severity class (0=LOW, 1=MEDIUM, 2=HIGH)
    """
    rng = np.random.default_rng(seed)

    # 시나리오별 가중치에 따라 샘플 수 배분
    weights = np.array([s["weight"] for s in SCENARIOS], dtype=float)
    weights /= weights.sum()
    counts = np.round(weights * n_samples).astype(int)
    counts[-1] = n_samples - counts[:-1].sum()  # 반올림 보정

    all_features = []
    all_scores = []
    all_classes = []

    for scenario, count in zip(SCENARIOS, counts):
        for _ in range(count):
            state = _sample_state(scenario, rng)
            score, cls = _compute_label(state, scenario["score"], rng)

            # Feature extraction
            pose_feat = _pose_features(state)
            audio_feat = _audio_features(state)
            vlm_feat = _vlm_features(state)
            feat = np.stack([pose_feat, audio_feat, vlm_feat], axis=0)  # (3, 6)

            all_features.append(feat)
            all_scores.append(score)
            all_classes.append(cls)

    features = torch.tensor(np.array(all_features), dtype=torch.float32)
    scores = torch.tensor(np.array(all_scores), dtype=torch.float32)
    classes = torch.tensor(np.array(all_classes), dtype=torch.long)

    # Shuffle (seed 고정으로 재현성 보장)
    gen = torch.Generator().manual_seed(seed)
    perm = torch.randperm(n_samples, generator=gen)
    return features[perm], scores[perm], classes[perm]


class FusionDataset(Dataset):
    def __init__(self, features: torch.Tensor, scores: torch.Tensor, classes: torch.Tensor):
        self.features = features
        self.scores = scores
        self.classes = classes

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.scores[idx], self.classes[idx]
