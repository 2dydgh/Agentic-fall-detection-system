"""
Prolog 추론 엔진 래퍼.

SWI-Prolog 엔진은 프로세스당 하나이며 스레드 안전하지 않다. api/main.py 가
VideoStream 마다 추론 스레드를 만들기 때문에, 모든 질의를 전역 Lock 으로
직렬화한다. 실측상 락 오버헤드는 관측되지 않는다(질의 0.021ms).

또한 엔진이 장기 실행되므로 판정마다 이전 사실을 모두 제거한다.
판정이 입력 사실만의 함수가 되도록 보장하는 장치다.
"""
import os
import threading
from dataclasses import dataclass, field

from .schema import GENERATED_PL

_HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PL = os.path.join(_HERE, "rules.pl")

# 판정마다 비워야 하는 동적 술어 (이름, 인자 수)
_DYNAMIC_PREDICATES = [
    ("occurred_in", 2),
    ("involves", 2),
    ("has_posture", 2),
    ("has_audio_event", 2),
    ("no_movement_duration", 2),
    ("has_hazard", 2),
    ("prior_incident", 3),
]

_SEVERITY_UP = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}


@dataclass
class FiredRule:
    rule_id: str
    severity: str
    description: str


@dataclass
class Judgement:
    severity: str
    fired_rules: list[FiredRule] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


class PrologEngine:
    """규칙 파일과 온톨로지 사실을 적재한 Prolog 엔진."""

    def __init__(self, rules_path: str = RULES_PL, ontology_path: str = GENERATED_PL):
        from pyswip import Prolog

        self._lock = threading.Lock()
        self._pl = Prolog()
        # 온톨로지 사실을 먼저 적재해야 rules.pl 의 kind_of/2 가 참조할 수 있다
        self._pl.consult(ontology_path.replace("\\", "/"))
        self._pl.consult(rules_path.replace("\\", "/"))

    def _retract_all(self) -> None:
        for name, arity in _DYNAMIC_PREDICATES:
            args = ",".join("_" for _ in range(arity))
            list(self._pl.query(f"retractall({name}({args}))"))

    def _query_severity(self, inc: str) -> str:
        rows = list(self._pl.query(f"severity({inc}, S)"))
        return str(rows[0]["S"]) if rows else "low"

    def _query_fired(self, inc: str) -> list[FiredRule]:
        rows = list(self._pl.query(f"fired({inc}, R, Sev), rule_text(R, D)"))
        seen: set[str] = set()
        fired: list[FiredRule] = []
        for row in rows:
            rule_id = str(row["R"])
            if rule_id in seen:
                continue
            seen.add(rule_id)
            fired.append(
                FiredRule(
                    rule_id=rule_id,
                    severity=str(row["Sev"]),
                    description=str(row["D"]),
                )
            )
        fired.sort(key=lambda r: (r.rule_id[0], int(r.rule_id[1:])))
        return fired

    def _query_actions(self, severity_atom: str) -> list[str]:
        rows = list(
            self._pl.query(
                f"requires_action({severity_atom}, A), action_tool(A, T)"
            )
        )
        actions: list[str] = []
        for row in rows:
            tool = str(row["T"])
            if tool not in actions:
                actions.append(tool)
        return actions

    def judge(self, facts: list[str], incident_id: str = "current") -> Judgement:
        """
        사실 목록으로 심각도를 판정한다.

        Args:
            facts: 마침표 없는 Prolog 사실 문자열 목록
            incident_id: 질의 주어 아톰

        Returns:
            Judgement (severity 는 대문자)
        """
        with self._lock:
            self._retract_all()
            for fact in facts:
                self._pl.assertz(fact)

            severity_atom = self._query_severity(incident_id)
            fired = self._query_fired(incident_id)
            actions = self._query_actions(severity_atom)

        return Judgement(
            severity=_SEVERITY_UP.get(severity_atom, "LOW"),
            fired_rules=fired,
            actions=actions,
            facts=list(facts),
        )


_engine: PrologEngine | None = None
_engine_lock = threading.Lock()


def get_engine() -> PrologEngine:
    """지연 생성 싱글턴. 기존 모듈들의 lazy loading 패턴을 따른다."""
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = PrologEngine()
    return _engine
