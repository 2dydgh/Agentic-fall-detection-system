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
        if not state.get("fall_detected") or skip_vlm:
            # VLM 스킵 시 기본값
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
        if not state.get("fall_detected"):
            return state
        if state.get("use_llm_decision"):
            from .nodes.decision_llm import decision_node_llm
            result = decision_node_llm(state)
        else:
            result = decision_node(state)
        return {**state, **result}

    def action_node_func(state: AgentState) -> AgentState:
        if not state.get("fall_detected"):
            return state
        result = action.process(state)
        return {**state, **result}

    # 노드 추가
    graph.add_node("perception", perception_node)
    graph.add_node("audio", audio_node_func)
    graph.add_node("analysis", analysis_node)
    graph.add_node("decision", decision_node_wrapper)
    graph.add_node("action", action_node_func)

    # 엣지 연결: perception → audio → analysis → decision → action
    graph.set_entry_point("perception")
    graph.add_edge("perception", "audio")
    graph.add_edge("audio", "analysis")
    graph.add_edge("analysis", "decision")
    graph.add_edge("decision", "action")
    graph.add_edge("action", END)

    return graph.compile()
