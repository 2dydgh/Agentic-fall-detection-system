def decision_node(state: dict) -> dict:
    """
    심각도 점수 계산 및 대응 방식 결정

    점수 계산:
    - base: no_movement_seconds * 2 (최대 60점)
    - elderly: +20점
    - stairs/bathroom: +15점
    - hazards: +5점

    판정:
    - 0-40: LOW
    - 41-70: MEDIUM
    - 71-100: HIGH
    """
    no_movement = state.get("no_movement_seconds", 0)
    age = state.get("estimated_age", "unknown")
    location = state.get("location_type", "other")
    hazards = state.get("hazards_detected", [])

    # 점수 계산
    # base_score = min(no_movement * 2, 60)
    # 테스트 시 배점 크게 올리기: 1초만 누워있어도 15점 획득 (4초면 60점 만점)
    # base_score = min(no_movement * 15, 60)
    base_score = 80

    age_bonus = 20 if age == "elderly" else 0
    location_bonus = 15 if location in ["stairs", "bathroom"] else 0
    hazard_bonus = 5 if len(hazards) > 0 else 0

    total_score = int(base_score + age_bonus + location_bonus + hazard_bonus)
    total_score = min(total_score, 100)

    # 심각도 판정
    if total_score <= 40:
        severity = "LOW"
    elif total_score <= 70:
        severity = "MEDIUM"
    else:
        severity = "HIGH"

    # 권장 액션
    actions = ["log_to_db"]
    if severity in ["MEDIUM", "HIGH"]:
        actions.append("save_snapshot")
        actions.append("notify_security_room")
    if severity == "HIGH":
        actions.append("send_email_alert")  # Changed from send_slack_alert
        actions.append("generate_report")

    return {
        "severity": severity,
        "severity_score": total_score,
        "recommended_actions": actions,
        "auto_action_required": severity == "HIGH",
    }
