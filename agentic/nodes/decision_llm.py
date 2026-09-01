"""
LLM 기반 의사결정 노드 (Ollama 로컬 무료 LLM).
룰 기반 decision_node 대신 LLM이 상황을 종합 판단한다.
실패 시 룰 기반으로 자동 폴백.
"""
import json

_llm_client = None


def _get_client():
    global _llm_client
    if _llm_client is None:
        import ollama
        _llm_client = ollama
    return _llm_client


DECISION_PROMPT = """You are a fall detection severity assessment agent.
A fall has been detected by the vision system. Analyze all sensor data and decide the severity level and required response actions.

## Current Situation
- Body tilt angle: {angle} degrees (>35 = lying down)
- Fall velocity: {velocity}
- Time on ground without movement: {no_movement_seconds} seconds
- Scream detected: {scream}
- Impact sound detected: {impact}
- Audio confidence: {audio_confidence}
- Location type: {location_type}
- Estimated age group: {estimated_age}
- Scene description (from VLM): {scene_description}
- Hazards in scene: {hazards}

## Available Actions
- log_to_db: Record incident in database (always include this)
- save_snapshot: Save camera frame capture
- notify_security_room: Alert on-site security personnel
- send_email_alert: Send emergency email with snapshot and report
- generate_report: Generate detailed incident report

## Guidelines
- LOW (0-50): Minor incident, just log it
- MEDIUM (51-75): Needs attention, save snapshot and notify security
- HIGH (76-100): Emergency, full response including email and report
- Elderly + stairs/bathroom = higher risk
- Scream or impact sound = stronger evidence of real fall
- Long time on ground without movement = more severe

Respond with ONLY valid JSON, no markdown or explanation:
{{"severity": "LOW|MEDIUM|HIGH", "severity_score": 0-100, "recommended_actions": ["action1", ...], "reasoning": "brief explanation"}}"""


OLLAMA_MODEL = "qwen2.5:7b"
VALID_ACTIONS = {"log_to_db", "save_snapshot", "notify_security_room", "send_email_alert", "generate_report"}


def decision_node_llm(state: dict) -> dict:
    """LLM 기반 낙상 심각도 판단"""
    pose_data = state.get("pose_data", {})

    prompt = DECISION_PROMPT.format(
        angle=round(pose_data.get("angle", 0), 1),
        velocity=round(abs(pose_data.get("velocity", 0)), 1),
        no_movement_seconds=round(state.get("no_movement_seconds", 0), 1),
        scream=state.get("audio_scream_detected", False),
        impact=state.get("audio_impact_detected", False),
        audio_confidence=round(state.get("audio_confidence", 0.0), 2),
        location_type=state.get("location_type", "unknown"),
        estimated_age=state.get("estimated_age", "unknown"),
        scene_description=state.get("scene_description", ""),
        hazards=state.get("hazards_detected", []),
    )

    try:
        client = _get_client()
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        result = json.loads(response["message"]["content"])

        # 응답 검증
        severity = result.get("severity", "MEDIUM")
        if severity not in ("LOW", "MEDIUM", "HIGH"):
            severity = "MEDIUM"

        score = max(0, min(100, int(result.get("severity_score", 50))))

        actions = [a for a in result.get("recommended_actions", []) if a in VALID_ACTIONS]
        if "log_to_db" not in actions:
            actions.insert(0, "log_to_db")

        reasoning = result.get("reasoning", "")
        print(f"[DecisionLLM] {severity} (score={score}) - {reasoning}")

        return {
            "severity": severity,
            "severity_score": score,
            "recommended_actions": actions,
            "auto_action_required": severity == "HIGH",
        }

    except Exception as e:
        print(f"[DecisionLLM] LLM 호출 실패, 룰 기반 폴백: {e}")
        from .decision import decision_node
        return decision_node(state)
