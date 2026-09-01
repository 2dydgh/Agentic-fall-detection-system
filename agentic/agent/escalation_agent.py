"""
비동기 에스컬레이션 Agent — LangGraph ReAct 그래프.

실시간 경로에서 낙상이 감지된 후, 이 Agent가 비동기로 실행되어:
1. 과거 인시던트 이력을 조회 (Tool Call)
2. 상황을 종합 분석 (LLM Reasoning)
3. 에스컬레이션 여부를 결정 (Tool Call)
4. 결과를 확인하고 추가 행동 여부를 판단 (Loop)

기존 순수 Python for 루프를 LangGraph StateGraph로 전환하여
조건부 분기(reason → act or END)와 피드백 루프(act → reason)를
그래프 구조로 명시적으로 표현한다.
"""
import json
import time
from typing import TypedDict

from langgraph.graph import StateGraph, END
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


# ---------------------------------------------------------------------------
# LangGraph ReAct 그래프 상태
# ---------------------------------------------------------------------------

class _ReActState(TypedDict):
    messages: list[dict]
    actions_taken: list[dict]
    context: dict
    iteration: int
    max_iterations: int
    timeout: float
    start_time: float
    final_assessment: str
    escalation_needed: bool
    pending_tool: str
    pending_args: dict


# ---------------------------------------------------------------------------
# 그래프 노드
# ---------------------------------------------------------------------------

def _reason_node(state: _ReActState) -> dict:
    """LLM이 다음 행동을 결정한다 (Reason 단계)"""
    client = _get_client()

    response = client.chat(
        model=OLLAMA_MODEL,
        messages=state["messages"],
        format="json",
    )
    content = response["message"]["content"]

    new_messages = state["messages"] + [{"role": "assistant", "content": content}]

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return {
            "messages": new_messages,
            "final_assessment": content,
            "escalation_needed": False,
            "pending_tool": "",
            "pending_args": {},
        }

    # Agent가 완료를 선언한 경우
    if parsed.get("done"):
        return {
            "messages": new_messages,
            "final_assessment": parsed.get("final_assessment", ""),
            "escalation_needed": parsed.get("escalation_needed", False),
            "pending_tool": "",
            "pending_args": {},
        }

    # Tool Call 요청
    return {
        "messages": new_messages,
        "pending_tool": parsed.get("tool", ""),
        "pending_args": parsed.get("args", {}),
    }


def _act_node(state: _ReActState) -> dict:
    """도구를 실행하고 결과를 메시지에 추가한다 (Act 단계)"""
    tool_name = state["pending_tool"]
    tool_args = dict(state["pending_args"])
    context = state["context"]

    # db_path를 context에서 주입 (보안: LLM이 임의 경로 접근 방지)
    if "db_path" in {
        p for s in TOOL_SCHEMAS if s["name"] == tool_name
        for p in s["parameters"].get("properties", {})
    }:
        tool_args["db_path"] = context["db_path"]

    result = execute_tool(tool_name, tool_args)

    iteration = state["iteration"] + 1
    print(f"[Agent] Iteration {iteration}: called {tool_name} -> {result}")

    new_messages = state["messages"] + [{
        "role": "user",
        "content": f"Tool '{tool_name}' result: {json.dumps(result, ensure_ascii=False, default=str)}",
    }]

    new_actions = state["actions_taken"] + [{
        "tool": tool_name,
        "args": tool_args,
        "result": result,
    }]

    return {
        "messages": new_messages,
        "actions_taken": new_actions,
        "iteration": iteration,
        "pending_tool": "",
        "pending_args": {},
    }


# ---------------------------------------------------------------------------
# 조건 분기: reason 이후 act로 갈지, 종료할지
# ---------------------------------------------------------------------------

def _route_after_reason(state: _ReActState) -> str:
    """LLM 응답을 보고 다음 경로를 결정한다"""
    # 타임아웃 체크
    if time.time() - state["start_time"] > state["timeout"]:
        return END
    # max_iterations 체크
    if state["iteration"] >= state["max_iterations"]:
        return END
    # Tool Call이 있으면 act로, 없으면 종료 (done 또는 파싱 실패)
    if state.get("pending_tool"):
        return "act"
    return END


# ---------------------------------------------------------------------------
# 그래프 빌드
# ---------------------------------------------------------------------------

def _build_react_graph():
    """
    ReAct 루프를 LangGraph StateGraph로 구성.

        reason ──(조건)──▶ act ──▶ reason  (피드백 루프)
          │
          └──(done/timeout/max)──▶ END
    """
    graph = StateGraph(_ReActState)

    graph.add_node("reason", _reason_node)
    graph.add_node("act", _act_node)

    graph.set_entry_point("reason")
    graph.add_conditional_edges("reason", _route_after_reason, {
        "act": "act",
        END: END,
    })
    graph.add_edge("act", "reason")  # 피드백 루프: 도구 결과를 보고 다시 판단

    return graph.compile()


# ---------------------------------------------------------------------------
# 외부 인터페이스 (기존과 동일)
# ---------------------------------------------------------------------------

class EscalationAgent:
    """LangGraph ReAct 그래프 기반 에스컬레이션 Agent"""

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

        return self._run_graph(context)

    def _run_graph(self, context: dict) -> dict:
        """LangGraph ReAct 그래프 실행"""
        tool_descriptions = "\n".join(
            f"- {t['name']}: {t['description']}" for t in TOOL_SCHEMAS
        )
        system_msg = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)

        # 온톨로지 모드가 판정 근거로 남긴 규칙 목록. 다른 판정 모드에서는 비어 있다.
        fired = context.get("fired_rules") or []
        if fired:
            rules_line = "- Fired rules (symbolic reasoning): " + ", ".join(
                f"{r.get('rule_id')} ({r.get('description')})" for r in fired
            ) + "\n"
        else:
            rules_line = ""

        user_msg = (
            f"Fall incident detected. Here is the context:\n"
            f"- Incident ID: {context['incident_id']}\n"
            f"- Current severity: {context['severity']} (score: {context['severity_score']})\n"
            f"{rules_line}"
            f"- Scene: {context.get('scene_description', 'N/A')}\n"
            f"- Age group: {context.get('estimated_age', 'unknown')}\n"
            f"- Location: {context.get('location_type', 'unknown')}\n"
            f"- Scream detected: {context.get('audio_scream_detected', False)}\n"
            f"- Impact sound: {context.get('audio_impact_detected', False)}\n"
            f"- Time on ground: {context.get('no_movement_seconds', 0)}s\n"
            f"- DB path: {context['db_path']}\n\n"
            f"Analyze this situation. Start by checking incident history."
        )

        initial_state: _ReActState = {
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "actions_taken": [],
            "context": context,
            "iteration": 0,
            "max_iterations": self._max_iterations,
            "timeout": self._timeout,
            "start_time": time.time(),
            "final_assessment": "",
            "escalation_needed": False,
            "pending_tool": "",
            "pending_args": {},
        }

        try:
            graph = _build_react_graph()
            final_state = graph.invoke(initial_state)

            assessment = final_state.get("final_assessment", "")
            if not assessment and final_state["iteration"] >= self._max_iterations:
                assessment = "Max iterations reached. Manual review recommended."
            elif not assessment:
                assessment = f"Timeout after {self._timeout}s. Manual review recommended."

            return {
                "actions_taken": final_state.get("actions_taken", []),
                "final_assessment": assessment,
                "escalation_needed": final_state.get("escalation_needed", False),
            }
        except Exception as e:
            print(f"[Agent] ReAct graph error, falling back to rules: {e}")
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
