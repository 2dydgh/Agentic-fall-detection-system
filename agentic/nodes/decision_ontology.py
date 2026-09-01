"""
온톨로지 + Prolog 규칙 기반 판정 노드 (4번째 모드).

기존 세 모드와 달리 점수를 계산하지 않는다. 규칙이 발동했는지 여부만으로
심각도 범주를 정하고, 발동한 규칙 목록을 판단 근거로 함께 반환한다.

severity_score 는 기존 스키마 호환을 위한 고정 매핑이며 판정에 관여하지 않는다.
"""
from dataclasses import asdict

from agentic.ontology.engine import get_engine
from agentic.ontology.facts import state_to_facts

SEVERITY_SCORE = {"LOW": 25, "MEDIUM": 60, "HIGH": 90}


def decision_node_ontology(state: dict) -> dict:
    """온톨로지 추론으로 심각도와 대응 액션을 판정한다."""
    try:
        engine = get_engine()
        facts = state_to_facts(state)
        judgement = engine.judge(facts)
    except Exception as e:  # noqa: BLE001 — 파이프라인을 멈추지 않는다
        print(f"[DecisionOntology] Prolog 엔진 실패, 룰 기반 폴백: {e}")
        from .decision import decision_node_rule

        fallback = decision_node_rule(state)
        fallback["fired_rules"] = []
        fallback["decision_mode"] = "ontology_fallback"
        return fallback

    rules_desc = ", ".join(
        f"{r.rule_id}({r.severity})" for r in judgement.fired_rules
    ) or "없음"
    print(f"[DecisionOntology] {judgement.severity} - 발동 규칙: {rules_desc}")

    return {
        "severity": judgement.severity,
        "severity_score": SEVERITY_SCORE[judgement.severity],
        "recommended_actions": judgement.actions,
        "auto_action_required": judgement.severity == "HIGH",
        "fired_rules": [asdict(r) for r in judgement.fired_rules],
        "decision_mode": "ontology",
    }
