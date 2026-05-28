"""
비동기 에스컬레이션 Agent — ReAct (Reason + Act) 루프.

실시간 경로에서 낙상이 감지된 후, 이 Agent가 비동기로 실행되어:
1. 과거 인시던트 이력을 조회 (Tool Call)
2. 상황을 종합 분석 (LLM Reasoning)
3. 에스컬레이션 여부를 결정 (Tool Call)
4. 결과를 확인하고 추가 행동 여부를 판단 (Loop)
"""
import json
from .tools import TOOL_SCHEMAS, execute_tool

_llm_client = None

OLLAMA_MODEL = "llama3.2"


def _get_client():
    global _llm_client
    if _llm_client is None:
        import ollama
        _llm_client = ollama
    return _llm_client


SYSTEM_PROMPT = """You are an emergency escalation agent for a fall detection system.
A fall has been detected and initial response (DB logging, snapshot, security notification) has already been sent by the real-time pipeline.

Your job is to perform FOLLOW-UP analysis:
1. Check past incident history for this area
2. Assess if the situation needs escalation beyond the initial response
3. Take additional actions if needed (call 119, dispatch nurse, update severity)

You have access to these tools:
{tool_descriptions}

IMPORTANT RULES:
- Always start by querying incident history to check for patterns
- Only escalate if the evidence strongly supports it
- You can call multiple tools across multiple turns
- When you're done analyzing, respond with a JSON object with "done": true and "final_assessment": "your conclusion"
- For tool calls, respond with: {{"tool": "tool_name", "args": {{...}}}}
- For final answer, respond with: {{"done": true, "final_assessment": "...", "escalation_needed": true/false}}"""


class EscalationAgent:
    """ReAct 루프 기반 에스컬레이션 Agent"""

    def __init__(self, skip_llm: bool = False, max_iterations: int = 4, timeout: float = 30.0):
        self._skip_llm = skip_llm
        self._max_iterations = max_iterations
        self._timeout = timeout

    def run(self, context: dict) -> dict:
        """
        Agent 실행. context에는 인시던트 정보가 담겨 있다.

        Returns:
            {"actions_taken": [...], "final_assessment": "..."}
        """
        if self._skip_llm:
            return self._fallback_rules(context)

        return self._react_loop(context)

    def _react_loop(self, context: dict) -> dict:
        """LLM 기반 ReAct 루프 (max_iterations + timeout 이중 안전장치)"""
        import time
        start_time = time.time()

        tool_descriptions = "\n".join(
            f"- {t['name']}: {t['description']}" for t in TOOL_SCHEMAS
        )
        system_msg = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

        user_msg = (
            f"Fall incident detected. Here is the context:\n"
            f"- Incident ID: {context['incident_id']}\n"
            f"- Current severity: {context['severity']} (score: {context['severity_score']})\n"
            f"- Scene: {context.get('scene_description', 'N/A')}\n"
            f"- Age group: {context.get('estimated_age', 'unknown')}\n"
            f"- Location: {context.get('location_type', 'unknown')}\n"
            f"- Scream detected: {context.get('audio_scream_detected', False)}\n"
            f"- Impact sound: {context.get('audio_impact_detected', False)}\n"
            f"- Time on ground: {context.get('no_movement_seconds', 0)}s\n"
            f"- DB path: {context['db_path']}\n\n"
            f"Analyze this situation. Start by checking incident history."
        )

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        actions_taken = []

        try:
            client = _get_client()

            for i in range(self._max_iterations):
                # 타임아웃 체크
                if time.time() - start_time > self._timeout:
                    return {
                        "actions_taken": actions_taken,
                        "final_assessment": f"Timeout after {self._timeout}s. Manual review recommended.",
                        "escalation_needed": False,
                    }

                response = client.chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    format="json",
                )
                content = response["message"]["content"]
                messages.append({"role": "assistant", "content": content})

                parsed = json.loads(content)

                # 종료 조건: Agent가 완료 선언
                if parsed.get("done"):
                    return {
                        "actions_taken": actions_taken,
                        "final_assessment": parsed.get("final_assessment", ""),
                        "escalation_needed": parsed.get("escalation_needed", False),
                    }

                # Tool Call 실행
                tool_name = parsed.get("tool")
                tool_args = parsed.get("args", {})

                if tool_name:
                    # db_path를 context에서 주입 (보안: LLM이 임의 경로 접근 방지)
                    if "db_path" in {p for s in TOOL_SCHEMAS if s["name"] == tool_name for p in s["parameters"].get("properties", {})}:
                        tool_args["db_path"] = context["db_path"]

                    result = execute_tool(tool_name, tool_args)
                    actions_taken.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result,
                    })

                    # 도구 결과를 대화에 추가하여 LLM이 다음 판단에 활용
                    messages.append({
                        "role": "user",
                        "content": f"Tool '{tool_name}' result: {json.dumps(result, ensure_ascii=False, default=str)}",
                    })
                    print(f"[Agent] Iteration {i+1}: called {tool_name} -> {result}")
                else:
                    # 도구 호출도 종료 선언도 아닌 경우 종료
                    return {
                        "actions_taken": actions_taken,
                        "final_assessment": content,
                        "escalation_needed": False,
                    }

            # max_iterations 도달
            return {
                "actions_taken": actions_taken,
                "final_assessment": "Max iterations reached. Manual review recommended.",
                "escalation_needed": False,
            }

        except Exception as e:
            print(f"[Agent] ReAct loop error, falling back to rules: {e}")
            return self._fallback_rules(context)

    def _fallback_rules(self, context: dict) -> dict:
        """LLM 없이 룰 기반 폴백 에스컬레이션"""
        actions_taken = []
        escalation_needed = False
        reasons = []

        severity = context.get("severity", "LOW")
        age = context.get("estimated_age", "unknown")
        location = context.get("location_type", "other")
        scream = context.get("audio_scream_detected", False)
        no_movement = context.get("no_movement_seconds", 0)

        # 룰 1: HIGH + 고령자 -> 에스컬레이션
        if severity == "HIGH" and age == "elderly":
            escalation_needed = True
            reasons.append("HIGH severity with elderly person")

        # 룰 2: 비명 + 장시간 무반응 -> 에스컬레이션
        if scream and no_movement > 5.0:
            escalation_needed = True
            reasons.append(f"Scream detected with {no_movement}s no movement")

        # 룰 3: 위험 장소 + HIGH -> 에스컬레이션
        if location in ("stairs", "bathroom") and severity == "HIGH":
            escalation_needed = True
            reasons.append(f"HIGH severity in dangerous location ({location})")

        if escalation_needed:
            incident_id = context.get("incident_id", "UNKNOWN")
            result = execute_tool("escalate_emergency", {
                "incident_id": incident_id,
                "reason": "; ".join(reasons),
                "action": "call_119",
            })
            actions_taken.append({
                "tool": "escalate_emergency",
                "args": {"incident_id": incident_id, "reason": "; ".join(reasons)},
                "result": result,
            })

        assessment = f"Fallback analysis: escalation={'needed' if escalation_needed else 'not needed'}. {'; '.join(reasons) if reasons else 'No escalation criteria met.'}"

        return {
            "actions_taken": actions_taken,
            "final_assessment": assessment,
            "escalation_needed": escalation_needed,
        }
