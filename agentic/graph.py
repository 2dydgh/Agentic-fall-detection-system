from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes.perception import PerceptionNode
from .nodes.decision import decision_node
from .nodes.action import ActionNode
from .agent.runner import AgentRunner

# Analysis Node는 무거우니까 lazy load
_analysis_node = None

def get_analysis_node():
    global _analysis_node
    if _analysis_node is None:
        from .nodes.analysis import AnalysisNode
        _analysis_node = AnalysisNode()
    return _analysis_node


def create_fall_detection_graph(
    model_path: str,
    db_path: str = "incidents.db",
    slack_webhook: str = None,
    email_sender: str = None,
    email_password: str = None,
    email_receiver: str = None,
    skip_vlm: bool = False,
    skip_audio: bool = False,
    agent_runner=None,
):
    """LangGraph 워크플로우 생성 (비전 + 오디오 멀티모달)"""

    # 노드 초기화
    perception = PerceptionNode(model_path)
    from .nodes.audio import AudioNode
    audio = AudioNode(skip_model=skip_audio)

    # Agent Runner: 외부 주입 또는 내부 생성
    if agent_runner is None:
        agent_runner = AgentRunner(db_path=db_path, skip_llm=skip_audio)

    action = ActionNode(
        db_path=db_path,
        slack_webhook=slack_webhook,
        email_sender=email_sender,
        email_password=email_password,
        email_receiver=email_receiver,
        agent_runner=agent_runner,
    )

    # 그래프 정의
    graph = StateGraph(AgentState)

    # 노드 함수들
    def perception_node(state: AgentState) -> AgentState:
        frame = state.get("frame")
        if frame is None:
            return state
        result = perception.process(frame, state)
        return {**state, **result}

    def audio_node_func(state: AgentState) -> AgentState:
        result = audio.process(state)
        return {**state, **result}

    def analysis_node(state: AgentState) -> AgentState:
        if skip_vlm:
            return {
                **state,
                "scene_description": "Fall detected",
                "estimated_age": "adult",
                "location_type": "other",
                "hazards_detected": [],
            }
        analysis = get_analysis_node()
        result = analysis.process(state)
        return {**state, **result}

    def decision_node_wrapper(state: AgentState) -> AgentState:
        mode = state.get("decision_mode")
        if mode is None:  # 하위 호환: 기존 use_llm_decision 플래그
            mode = "llm" if state.get("use_llm_decision") else "auto"

        if mode == "ontology":
            from .nodes.decision_ontology import decision_node_ontology
            result = decision_node_ontology(state)
        elif mode == "llm":
            from .nodes.decision_llm import decision_node_llm
            result = decision_node_llm(state)
        elif mode == "rule":
            from .nodes.decision import decision_node_rule
            result = decision_node_rule(state)
        else:  # auto — 기존 동작 유지 (fusion 모델 있으면 attention)
            result = decision_node(state)
        return {**state, **result}

    def action_node_func(state: AgentState) -> AgentState:
        result = action.process(state)
        return {**state, **result}

    # 노드 추가
    graph.add_node("perception", perception_node)
    graph.add_node("audio", audio_node_func)
    graph.add_node("analysis", analysis_node)
    graph.add_node("decision", decision_node_wrapper)
    graph.add_node("action", action_node_func)

    # --- 조건 분기: 낙상 감지 여부에 따라 분석 경로 또는 즉시 종료 ---
    def route_after_audio(state: AgentState) -> str:
        if state.get("fall_detected"):
            return "analysis"
        return END

    # 엣지 연결
    # perception → audio는 항상 실행 (매 프레임 포즈 추정 + 오디오 분석)
    graph.set_entry_point("perception")
    graph.add_edge("perception", "audio")

    # audio 이후 조건 분기: 낙상 감지 시에만 후속 분석
    graph.add_conditional_edges("audio", route_after_audio, {
        "analysis": "analysis",
        END: END,
    })

    # 낙상 감지 경로: analysis → decision → action → END
    graph.add_edge("analysis", "decision")
    graph.add_edge("decision", "action")
    graph.add_edge("action", END)

    return graph.compile()
