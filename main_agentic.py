import os
import cv2
import argparse
from dotenv import load_dotenv
from agentic.graph import create_fall_detection_graph
from agentic.state import AgentState
from agentic.audio.extractor import AudioExtractor
from agentic.agent.runner import AgentRunner

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Agentic Fall Detection System")
    parser.add_argument("--video", required=True, help="Input video path")
    parser.add_argument("--output", default="output/result_agentic.mp4", help="Output video path")
    parser.add_argument("--model", default="models/yolov26n-pose.pt", help="YOLO model path")
    parser.add_argument("--skip-vlm", action="store_true", help="Skip VLM analysis for faster processing")
    parser.add_argument("--skip-audio", action="store_true", help="Skip audio analysis")
    parser.add_argument("--agent-mode", action="store_true", help="Use LLM agent for decision (requires Ollama)")
    args = parser.parse_args()

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 경로 설정
    video_path = os.path.join(base_dir, args.video) if not os.path.isabs(args.video) else args.video
    output_path = os.path.join(base_dir, args.output) if not os.path.isabs(args.output) else args.output
    model_path = os.path.join(base_dir, args.model) if not os.path.isabs(args.model) else args.model

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # LangGraph 생성
    agent_runner = AgentRunner(
        db_path=os.path.join(base_dir, "incidents.db"),
        skip_llm=not args.agent_mode,
    )

    print("🚀 Agentic Fall Detection 시스템 시작...")
    print(f"   - 입력: {video_path}")
    print(f"   - 모델: {model_path}")
    print(f"   - VLM: {'OFF' if args.skip_vlm else 'ON'}")
    print(f"   - Agent Mode: {'ON (LLM)' if args.agent_mode else 'OFF (Rule)'}")

    graph = create_fall_detection_graph(
        model_path=model_path,
        db_path=os.path.join(base_dir, "incidents.db"),
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_receiver=os.getenv("EMAIL_RECEIVER"),
        skip_vlm=args.skip_vlm,
        skip_audio=args.skip_audio,
        agent_runner=agent_runner,
    )

    # 비디오 처리
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ 비디오 파일을 열 수 없습니다: {video_path}")
        return

    width, height = 980, 740
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0

    # 오디오 추출
    if not args.skip_audio:
        audio_extractor = AudioExtractor.from_video_file(video_path, video_fps=fps)
        print(f"   - 오디오: {audio_extractor.duration_seconds:.1f}초 추출됨")
    else:
        audio_extractor = AudioExtractor.silent(video_fps=fps)
        print(f"   - 오디오: OFF")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    fall_events = 0

    print("🎬 영상 처리 중...")

    # State persists across frames for tracking history
    current_state: AgentState = {
        "frame": None,
        "fall_detected": False,
        "pose_data": {},
        "no_movement_seconds": 0.0,
        "track_id": None,
        "annotated_frame": None,
        "scene_description": "",
        "estimated_age": "unknown",
        "location_type": "other",
        "hazards_detected": [],
        "severity": "LOW",
        "severity_score": 0,
        "recommended_actions": [],
        "auto_action_required": False,
        "actions_taken": [],
        "incident_id": None,
        "snapshot_path": None,
        # Decision Mode
        "use_llm_decision": args.agent_mode,
        # Audio
        "audio_chunk": None,
        "audio_scream_detected": False,
        "audio_impact_detected": False,
        "audio_confidence": 0.0,
        "audio_detected_labels": [],
    }

    alert_frames_remaining = 0
    last_severity = "LOW"
    last_score = 0
    last_actions = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        frame = cv2.resize(frame, (width, height))
        current_state["frame"] = frame.copy()
        current_state["audio_chunk"] = audio_extractor.get_chunk_for_frame(frame_count)

        # 그래프 실행
        result = graph.invoke(current_state)
        current_state = result

        # 결과 프레임
        annotated = result.get("annotated_frame")
        if annotated is None:
            annotated = frame.copy()

        # 낙상 감지 이벤트 로깅 및 알럿 지속시간 설정
        if result.get("fall_detected"):
            alert_frames_remaining = 60  # Hold alert for ~3 seconds
            last_severity = result.get("severity", "LOW")
            last_score = result.get("severity_score", 0)
            last_actions = len(result.get("actions_taken", []))

            if result.get("incident_id"):
                fall_events += 1
                print(f"   🚨 [{frame_count}] 낙상 감지! 심각도: {last_severity}, ID: {result['incident_id']}")

        # 알럿 지속 시간 동안 화면에 표시
        if alert_frames_remaining > 0:
            color = {"LOW": (0, 255, 0), "MEDIUM": (0, 165, 255), "HIGH": (0, 0, 255)}.get(last_severity, (0, 255, 0))

            # HUD 표시
            cv2.rectangle(annotated, (10, 10), (300, 120), (0, 0, 0), -1)
            cv2.rectangle(annotated, (10, 10), (300, 120), color, 2)
            cv2.putText(annotated, f"SEVERITY: {last_severity}", (20, 45),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.putText(annotated, f"Score: {last_score}/100", (20, 75),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            cv2.putText(annotated, f"Actions: {last_actions}", (20, 105),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # 중앙 대형 경고 문구
            if last_severity in ["HIGH", "MEDIUM"]:
                cv2.putText(annotated, f"[{last_severity}] FALL DETECTED!", (width//2 - 250, height//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 4)

            # 화면 가장자리 붉은 테두리
            if last_severity == "HIGH":
                cv2.rectangle(annotated, (0, 0), (width, height), (0, 0, 255), 10)

            alert_frames_remaining -= 1

        out.write(annotated)

        if frame_count % 100 == 0:
            print(f"   ⏳ {frame_count} 프레임 처리 완료...")

    cap.release()
    out.release()

    # 비동기 Agent 완료 대기 및 결과 출력
    print("\n⏳ 비동기 Agent 판단 대기 중...")
    agent_runner.wait_all(timeout=30.0)
    agent_results = agent_runner.get_results()
    if agent_results:
        print(f"\n🧠 Agent 후속 판단 결과 ({len(agent_results)}건):")
        for r in agent_results:
            esc = "⚠️ 에스컬레이션 필요" if r.get("escalation_needed") else "✓ 추가 조치 불필요"
            print(f"   [{r['incident_id']}] {esc}")
            print(f"   → {r['final_assessment'][:100]}")
    else:
        print("\n🧠 비동기 Agent 판단: 해당 없음 (MEDIUM 이상 인시던트 없음)")

    print(f"\n✅ 처리 완료!")
    print(f"   - 총 프레임: {frame_count}")
    print(f"   - 낙상 이벤트: {fall_events}")
    print(f"   - 출력 파일: {output_path}")

if __name__ == "__main__":
    main()
