"""
YAMNet 521-class 출력에서 낙상 관련 소리를 필터링하는 모듈.

YAMNet class index 참조:
https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv
"""

# (class_index, label_name) 튜플 리스트
# 주의: 아래 인덱스는 YAMNet class map CSV에서 확인해야 함.
# https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv
# 구현 시 실제 CSV를 다운로드하여 인덱스-라벨 매핑을 검증할 것.

# 비명/도움 요청 관련
SCREAM_LABELS = [
    (322, "Screaming"),
    (316, "Shout"),
    (317, "Yell"),
    (2, "Crying, sobbing"),
]

# 충격음/충돌음 관련
IMPACT_LABELS = [
    (441, "Thump, thud"),
    (450, "Bang"),
    (462, "Crash"),
    (394, "Glass, clink"),
]

# 전체 낙상 관련 라벨
FALL_RELEVANT_LABELS = SCREAM_LABELS + IMPACT_LABELS

# 빠른 조회를 위한 인덱스 셋
_SCREAM_INDICES = {idx for idx, _ in SCREAM_LABELS}
_IMPACT_INDICES = {idx for idx, _ in IMPACT_LABELS}
_ALL_RELEVANT_INDICES = _SCREAM_INDICES | _IMPACT_INDICES

# 최소 신뢰도 임계값
CONFIDENCE_THRESHOLD = 0.3


def classify_audio_event(scores) -> dict:
    scream_detected = False
    impact_detected = False
    max_confidence = 0.0
    detected_labels = []

    for idx, name in FALL_RELEVANT_LABELS:
        if idx < len(scores) and scores[idx] >= CONFIDENCE_THRESHOLD:
            score = float(scores[idx])
            detected_labels.append(name)
            max_confidence = max(max_confidence, score)

            if idx in _SCREAM_INDICES:
                scream_detected = True
            if idx in _IMPACT_INDICES:
                impact_detected = True

    return {
        "scream_detected": scream_detected,
        "impact_detected": impact_detected,
        "confidence": max_confidence,
        "detected_labels": detected_labels,
    }
