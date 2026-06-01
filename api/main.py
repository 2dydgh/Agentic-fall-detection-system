import os
import cv2
import json
import sqlite3
import asyncio
import threading
import queue
from fastapi import FastAPI, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic.graph import create_fall_detection_graph
from agentic.state import AgentState
from agentic.audio.extractor import AudioExtractor
from agentic.agent.runner import AgentRunner

load_dotenv()

app = FastAPI(title="Fall Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(base_dir, "models/yolov26n-pose.pt")
db_path = os.path.join(base_dir, "incidents.db")

# 글로벌 토글
audio_enabled = True
agent_mode_enabled = False  # LLM Agent 판단 on/off

# 글로벌 Agent Runner (모든 스트림에서 공유)
_global_agent_runner = AgentRunner(db_path=db_path, skip_llm=True)

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"status": "Fall Detection API is running"}

@app.get("/api/audio_status")
def get_audio_status():
    """오디오 분석 상태 조회"""
    return {"enabled": audio_enabled}

@app.post("/api/audio_toggle")
def toggle_audio():
    """오디오 분석 on/off 토글"""
    global audio_enabled
    audio_enabled = not audio_enabled
    return {"enabled": audio_enabled}

@app.get("/api/agent_status")
def get_agent_status():
    """Agent Mode 상태 조회"""
    return {"enabled": agent_mode_enabled}

@app.post("/api/agent_toggle")
def toggle_agent_mode():
    """Agent Mode on/off 토글 (LLM 판단 vs 룰 기반)"""
    global agent_mode_enabled
    agent_mode_enabled = not agent_mode_enabled
    mode = "LLM Agent" if agent_mode_enabled else "Rule-based"
    print(f"[API] Decision mode changed: {mode}")
    return {"enabled": agent_mode_enabled, "mode": mode}

@app.get("/api/agent_results")
def get_agent_results(limit: int = 20):
    """비동기 Agent의 에스컬레이션 판단 결과 조회 (DB 영속 데이터)"""
    if _global_agent_runner is None:
        return {"results": []}
    results = _global_agent_runner.get_results_from_db(limit=limit)
    return {"results": results}

@app.get("/api/incidents")
def get_recent_incidents(limit: int = 20):
    """최근 발생한 낙상 알람 DB에서 가져오기 및 전체 통계 반환"""
    try:
        conn = get_db_connection()
        logs = conn.execute(
            "SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()

        total_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        high_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity='HIGH'").fetchone()[0]
        medium_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity='MEDIUM'").fetchone()[0]

        conn.close()

        formatted_logs = []
        for log in logs:
            d = dict(log)
            formatted_logs.append({
                "id": d.get("incident_id", str(d.get("id"))),
                "camera_id": d.get("camera_id", "01"),
                "timestamp": d.get("timestamp", ""),
                "severity": d.get("severity", "LOW"),
                "score": d.get("severity_score", 0),
                "audio_scream": bool(d.get("audio_scream_detected", 0)),
                "audio_impact": bool(d.get("audio_impact_detected", 0)),
                "audio_confidence": d.get("audio_confidence", 0.0),
            })

        return {
            "total": total_count,
            "high": high_count,
            "medium": medium_count,
            "logs": formatted_logs
        }
    except Exception as e:
        return {"error": str(e)}


class VideoStream:
    """
    백그라운드 스레드에서 YOLO 추론을 실행하고,
    스트리밍은 원본 비디오 속도로 독립적으로 동작하는 클래스.
    
    - reader_thread: 비디오 프레임을 읽어 inference_queue에 넣음
    - inference_thread: YOLO+LangGraph 추론 후 latest_annotated 업데이트
    - generate(): 최신 annotated 프레임을 MJPEG으로 스트림
    """

    FRAME_SKIP = 8      # 추론 스킵 (8프레임마다 YOLO 실행)
    WIDTH = 640
    HEIGHT = 480
    TARGET_FPS = 20.0   # 스트림 목표 FPS

    def __init__(self, video_source: str, audio_source: str = None, camera_id: str = "01"):
        self.video_source = video_source
        self.camera_id = camera_id
        self.stopped = False

        # 최신 annotated 프레임 (스트리밍 스레드가 읽음)
        self.latest_annotated: bytes | None = None
        self.latest_lock = threading.Lock()

        # 추론 입력 큐 (maxsize=1 → 항상 최신 프레임만 처리)
        self.inference_queue: queue.Queue = queue.Queue(maxsize=1)

        # 알럿 상태 (inference 스레드에서 업데이트, 읽기 스레드에서 오버레이)
        self.alert_frames_remaining = 0
        self.last_severity = "LOW"
        self.last_score = 0

        # LangGraph 그래프 (추론 스레드 전용)
        self.graph = create_fall_detection_graph(
            model_path=model_path,
            db_path=db_path,
            slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
            email_sender=os.getenv("EMAIL_SENDER"),
            email_password=os.getenv("EMAIL_PASSWORD"),
            email_receiver=os.getenv("EMAIL_RECEIVER"),
            skip_vlm=True,
            skip_audio=False,
            agent_runner=_global_agent_runner,
        )

        # 오디오 추출 (별도 WAV 파일이 있으면 사용, 없으면 비디오에서 추출)
        if audio_source and os.path.exists(audio_source):
            self.audio_extractor = AudioExtractor.from_wav_file(audio_source, video_fps=self.TARGET_FPS)
            print(f"[Stream] 별도 오디오 소스 사용: {audio_source} ({self.audio_extractor.duration_seconds:.1f}s)")
        else:
            self.audio_extractor = AudioExtractor.from_video_file(video_source, video_fps=self.TARGET_FPS)

        # 스레드 시작
        self._inference_thread = threading.Thread(target=self._inference_worker, daemon=True)
        self._inference_thread.start()

    def _inference_worker(self):
        """백그라운드: YOLO+LangGraph 추론 전담 스레드"""
        state: AgentState = {
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
            # Camera
            "camera_id": self.camera_id,
            # Decision Mode
            "use_llm_decision": False,
            # Audio
            "audio_chunk": None,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "audio_detected_labels": [],
        }

        inference_frame_count = 0
        while not self.stopped:
            try:
                frame = self.inference_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            inference_frame_count += 1
            state["frame"] = frame
            state["audio_chunk"] = self.audio_extractor.get_chunk_for_frame(inference_frame_count) if audio_enabled else None
            state["use_llm_decision"] = agent_mode_enabled
            try:
                result = self.graph.invoke(state)
                state = result
            except Exception as e:
                print(f"[InferenceWorker] 추론 오류: {e}")
                continue

            annotated = result.get("annotated_frame")
            if annotated is None:
                annotated = frame.copy()

            # 낙상 감지 시 알럿 상태 업데이트
            if result.get("fall_detected"):
                self.alert_frames_remaining = 60
                self.last_severity = result.get("severity", "LOW")
                self.last_score = result.get("severity_score", 0)
                print(f"🚨 [Stream] 낙상 감지! 심각도={self.last_severity}, 점수={self.last_score}")

            # 알럿 카운트다운 (프론트엔드가 오버레이 담당)
            if self.alert_frames_remaining > 0:
                self.alert_frames_remaining -= 1

            # JPEG 인코딩 후 공유 변수에 저장 (Quality 40으로 낮춰 전송 속도 향상)
            _, buf = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
            with self.latest_lock:
                self.latest_annotated = buf.tobytes()

    async def generate(self):
        """MJPEG 스트림 생성기: 비디오 원본 속도로 프레임 전송"""
        cap = cv2.VideoCapture(self.video_source)
        if not cap.isOpened():
            print(f"[Stream] 비디오 열기 실패: {self.video_source}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or self.TARGET_FPS
        frame_delay = 1.0 / fps
        frame_count = 0

        try:
            while not self.stopped:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                frame_count += 1
                frame = cv2.resize(frame, (self.WIDTH, self.HEIGHT))

                # FRAME_SKIP마다 추론 큐에 제출 (큐가 가득 차면 드롭 → 블로킹 없음)
                if frame_count % self.FRAME_SKIP == 0:
                    try:
                        self.inference_queue.put_nowait(frame.copy())
                    except queue.Full:
                        pass  # 이전 추론이 아직 처리 중 → 이 프레임은 드롭

                # 최신 annotated 프레임이 있으면 전송, 없으면 원본 전송
                with self.latest_lock:
                    frame_bytes = self.latest_annotated

                if frame_bytes is None:
                    # 추론 결과 아직 없음 → 원본 프레임 그냥 전송 (Quality 40)
                    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frame_bytes = buf.tobytes()

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                await asyncio.sleep(frame_delay)

        finally:
            cap.release()

    def stop(self):
        self.stopped = True


@app.get("/video_feed")
async def video_feed(video_path: str = "input/02872_H_C_FY_C4.mp4", audio_path: str = None, camera_id: str = "01"):
    """Returns the continuous MJPEG video stream"""
    from fastapi.responses import StreamingResponse
    source = os.path.join(base_dir, video_path)
    audio_source = os.path.join(base_dir, audio_path) if audio_path else None
    stream = VideoStream(source, audio_source=audio_source, camera_id=camera_id)
    return StreamingResponse(stream.generate(), media_type="multipart/x-mixed-replace; boundary=frame")


async def _raw_frame_generator(video_source: str, speed: float = 1.0):
    """YOLO 추론 없이 원본 비디오를 원래 속도로 스트리밍 (GIF 캡쳐용 데모)"""
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    frame_delay = 1.0 / (fps * speed)
    W, H = 640, 480

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = cv2.resize(frame, (W, H))

            # 좌상단 데모 워터마크
            cv2.rectangle(frame, (8, 8), (220, 32), (0, 0, 0), -1)
            cv2.putText(frame, "AGENTIC FALL DETECTION", (14, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 180), 1)

            _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
            await asyncio.sleep(frame_delay)
    finally:
        cap.release()


@app.get("/raw_feed")
async def raw_feed(video_path: str = "input/02872_H_C_FY_C4.mp4", speed: float = 1.0):
    """
    YOLO 없이 원본 비디오를 원래 속도로 스트리밍.
    GIF 캡쳐용 데모에 사용. speed=2.0 이면 2배속.
    """
    from fastapi.responses import StreamingResponse
    source = os.path.join(base_dir, video_path)
    return StreamingResponse(
        _raw_frame_generator(source, speed),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/seed_demo_data")
def seed_demo_data():
    """
    GIF 데모용: DB에 샘플 낙상 이벤트 데이터를 넣어서
    Incident Registry / 통계 카드가 채워진 상태를 연출합니다.
    """
    from agentic.tools.db import init_db
    import uuid
    from datetime import datetime, timedelta

    init_db(db_path)
    conn = get_db_connection()

    samples = [
        ("01", "HIGH",   92, "Elder person fell near staircase. No movement for 8s."),
        ("01", "HIGH",   87, "Individual collapsed in corridor. Possible head injury."),
        ("02", "MEDIUM", 65, "Person slipped in bathroom. Sitting on floor."),
        ("03", "MEDIUM", 58, "Subject fell near entrance. Got up after 3s."),
        ("02", "LOW",    32, "Person crouched quickly. Recovered immediately."),
        ("03", "HIGH",   95, "Fall detected in living room. No response for 12s."),
    ]

    now = datetime.now()
    for i, (cam_id, sev, score, desc) in enumerate(samples):
        ts = now - timedelta(minutes=i * 7 + 2)
        inc_id = f"INC-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        try:
            conn.execute(
                "INSERT INTO incidents (incident_id, camera_id, timestamp, severity, severity_score, scene_description, actions_taken) VALUES (?,?,?,?,?,?,?)",
                (inc_id, cam_id, ts.isoformat(), sev, score, desc, '["log_to_db","save_snapshot","notify_security_room"]')
            )
        except Exception:
            pass  # 중복 무시

    conn.commit()
    conn.close()
    return {"status": "ok", "inserted": len(samples)}

