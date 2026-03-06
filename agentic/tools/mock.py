def notify_security_room(
    incident_id: str,
    severity: str,
    location: str = "Unknown"
) -> dict:
    """관제실 알림 시뮬레이션 (Mock)"""
    msg = f"DISPATCH: {incident_id} | Team: GUARD_1 | ETA: 2m"
    print(f"[MOCK] ========== 관제실 알림 ==========")
    print(f"[MOCK] 사건번호: {incident_id}")
    print(f"[MOCK] 심각도: {severity}")
    print(f"[MOCK] 위치: {location}")
    print(f"[MOCK] 담당자: 경비1팀 배정됨")
    print(f"[MOCK] 예상 도착: 2분")
    print(f"[MOCK] ================================")

    return {
        "notified": True,
        "assigned_team": "경비1팀",
        "eta_minutes": 2,
        "message": msg
    }
