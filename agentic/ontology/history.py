"""
incidents DB 의 과거 사건을 Prolog 시간축 사실로 변환한다.

기존 세 판정 경로는 현재 프레임만 보고 판단하므로 재낙상을 인지하지 못한다.
이 모듈이 그 정보를 규칙 엔진에 공급한다.

구역 식별에는 camera_id 를 사용한다. 카메라 1대가 구역 1개를 담당하는
설치 방식을 전제하며, incidents 테이블에 location_type 이 채워지기 전에도
동작하게 하기 위함이다.
"""
from datetime import datetime

from agentic.tools.db import query_recent_incidents

from .facts import quote_atom


def history_facts(
    db_path: str,
    camera_id: str,
    within_days: int = 3,
    now: datetime | None = None,
) -> list[str]:
    """
    최근 N일 동일 카메라 이력 → prior_incident/3 사실 목록.

    생성 형식: prior_incident(PriorId, CameraId, MinutesAgo)
      - PriorId    : 과거 사건의 incident_id (인용 아톰)
      - CameraId   : 카메라 식별자 (인용 아톰)
      - MinutesAgo : 경과 분 (정수, 내림)

    경과 시간을 분 단위로 싣는 이유는 rules.pl 의 시간축 규칙(r6/r13)이
    '같은 낙상의 재검출'과 '진짜 재낙상'을 구분해야 하기 때문이다.
    일 단위로는 당일 재낙상과 몇 초 전 재검출이 똑같이 0 이 되어 구분할 수 없다.

    DB 조회에 실패해도 빈 목록을 반환한다. 이력이 없다고 판정이 멈추면 안 된다.
    """
    now = now or datetime.now()

    try:
        rows = query_recent_incidents(db_path, camera_id, within_days, now=now)
    except Exception as e:  # noqa: BLE001
        print(f"[History] 이력 조회 실패, 시간축 사실 없이 진행: {e}")
        return []

    facts: list[str] = []
    for row in rows:
        try:
            when = datetime.fromisoformat(row["timestamp"])
        except (ValueError, TypeError):
            continue
        minutes_ago = int((now - when).total_seconds() // 60)
        facts.append(
            f"prior_incident({quote_atom(row['incident_id'])}, "
            f"{quote_atom(camera_id)}, {minutes_ago})"
        )
    return facts
