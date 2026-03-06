import os
from datetime import datetime

def generate_report(
    incident_id: str,
    severity: str,
    severity_score: int,
    scene_description: str,
    estimated_age: str,
    location_type: str,
    recommended_actions: list,
    output_dir: str = "reports"
) -> str:
    """상황 보고서 생성 (템플릿 기반)"""
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
=====================================
       긴급 상황 보고서
=====================================
사건번호: {incident_id}
발생시각: {timestamp}
심각도: {severity} (점수: {severity_score}/100)

[상황 요약]
{scene_description}

[대상자 정보]
- 추정 연령대: {estimated_age}
- 발생 위치: {location_type}

[권장 조치]
{chr(10).join(f'- {action}' for action in recommended_actions)}

[조치 권고]
{'즉시 현장 확인 및 119 신고 권고' if severity == 'HIGH' else '관제실 확인 필요'}
=====================================
"""

    filepath = os.path.join(output_dir, f"{incident_id}_report.txt")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return filepath
