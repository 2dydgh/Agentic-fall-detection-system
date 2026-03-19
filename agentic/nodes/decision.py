import random

def decision_node(state: dict) -> dict:
    """
    심각도 점수 계산 및 대응 방식 결정

    점수 계산:
    - base: 기본 40점 + 각도/속도 추가 점수 + 랜덤 노이즈
    - elderly: +15점
    - stairs/bathroom: +10점
    - hazards: +10점

    판정:
    - 0-50: LOW
    - 51-75: MEDIUM (Warning)
    - 76-100: HIGH (Critical)
    """
    no_movement = state.get("no_movement_seconds", 0)
    age = state.get("estimated_age", "unknown")
    location = state.get("location_type", "other")
    hazards = state.get("hazards_detected", [])
    pose_data = state.get("pose_data", {})

    angle = pose_data.get("angle", 40)
    velocity = abs(pose_data.get("velocity", 0))

    # 기본 점수: 각도가 심할수록, 쓰러지는 속도가 빠를수록 증가 (최소 40 ~ 75)
    angle_bonus = min((angle - 35) * 0.6, 20) if angle > 35 else 0
    vel_bonus = min(velocity * 0.5, 15)
    
    base_score = 40 + angle_bonus + vel_bonus + random.randint(-5, 5)

    age_bonus = 15 if age == "elderly" else 0
    location_bonus = 10 if location in ["stairs", "bathroom"] else 0
    hazard_bonus = 10 if len(hazards) > 0 else 0

    # 오디오 보너스 (Late Fusion)
    scream = state.get("audio_scream_detected", False)
    impact = state.get("audio_impact_detected", False)
    scream_bonus = 15 if scream else 0
    impact_bonus = 10 if impact else 0

    total_score = int(base_score + age_bonus + location_bonus + hazard_bonus + scream_bonus + impact_bonus)
    total_score = max(0, min(total_score, 100))

    # 심각도 판정 (완화된 기준)
    if total_score <= 50:
        severity = "LOW"
    elif total_score <= 75:
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
