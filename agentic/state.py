from typing import TypedDict, Literal, Optional, Any

class AgentState(TypedDict):
    # Perception Node
    frame: Optional[Any]  # numpy array
    fall_detected: bool
    pose_data: dict
    no_movement_seconds: float
    track_id: Optional[int]
    annotated_frame: Optional[Any]  # numpy array

    # Analysis Node
    scene_description: str
    estimated_age: Literal["child", "adult", "elderly", "unknown"]
    location_type: Literal["stairs", "bathroom", "hallway", "outdoor", "other"]
    hazards_detected: list[str]

    # Audio Node
    audio_chunk: Optional[Any]  # 현재 프레임에 대응하는 오디오 청크 (numpy 배열 또는 None)
    audio_scream_detected: bool
    audio_impact_detected: bool
    audio_confidence: float
    audio_detected_labels: list[str]

    # Decision Node
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    severity_score: int
    recommended_actions: list[str]
    auto_action_required: bool

    # Decision Mode
    use_llm_decision: bool  # True: LLM Agent 판단, False: 룰 기반 (기본)

    # Action Node
    actions_taken: list[dict]
    incident_id: Optional[str]
    snapshot_path: Optional[str]
