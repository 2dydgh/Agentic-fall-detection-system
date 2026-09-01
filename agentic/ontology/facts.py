"""
AgentState 를 Prolog 사실 문자열로 변환한다.

이 모듈은 순수 함수만 포함한다. 난수를 쓰지 않으며, 동일 입력은 항상
동일한 사실 목록을 만든다. 판정의 재현성이 여기서 보장된다.

반환되는 문자열에는 마침표가 없다. pyswip 의 assertz() 입력 형식이다.
"""

# state.py 의 Literal 값 → 온톨로지 아톰
ZONE_MAP = {
    "stairs": "stairs",
    "bathroom": "bathroom",
    "hallway": "hallway",
    "outdoor": "outdoor",
    "other": "other_zone",
}

AGE_MAP = {
    "elderly": "elderly",
    "child": "child",
    "adult": "adult",
    "unknown": "unknown_person",
}

COLLAPSED_ANGLE = 70
LEANING_ANGLE = 45


def posture_of(angle: float) -> str:
    """몸통 각도를 자세 개념으로 변환한다."""
    if angle >= COLLAPSED_ANGLE:
        return "collapsed"
    if angle >= LEANING_ANGLE:
        return "leaning"
    return "upright"


def quote_atom(text: str) -> str:
    """임의 문자열을 Prolog 인용 아톰으로 만든다."""
    escaped = str(text).replace("'", "''")
    return f"'{escaped}'"


def state_to_facts(state: dict, incident_id: str = "current") -> list[str]:
    """
    AgentState → Prolog 사실 목록.

    Args:
        state: AgentState (누락 키는 기본값 사용)
        incident_id: 사실의 주어가 될 아톰

    Returns:
        마침표 없는 사실 문자열 목록
    """
    inc = incident_id
    facts: list[str] = []

    zone = ZONE_MAP.get(state.get("location_type", "other"), "other_zone")
    facts.append(f"occurred_in({inc}, {zone})")

    person = AGE_MAP.get(state.get("estimated_age", "unknown"), "unknown_person")
    facts.append(f"involves({inc}, {person})")

    pose = state.get("pose_data") or {}
    facts.append(f"has_posture({inc}, {posture_of(pose.get('angle', 0.0))})")

    seconds = int(state.get("no_movement_seconds") or 0)
    facts.append(f"no_movement_duration({inc}, {seconds})")

    if state.get("audio_scream_detected"):
        facts.append(f"has_audio_event({inc}, scream)")
    if state.get("audio_impact_detected"):
        facts.append(f"has_audio_event({inc}, impact_sound)")

    for hazard in state.get("hazards_detected") or []:
        facts.append(f"has_hazard({inc}, {quote_atom(hazard)})")

    return facts
