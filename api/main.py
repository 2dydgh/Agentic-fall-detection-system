import os
import cv2
import json
import sqlite3
import asyncio
from fastapi import FastAPI, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentic.graph import create_fall_detection_graph
from agentic.state import AgentState

load_dotenv()

app = FastAPI(title="Fall Detection API")

# Setup CORS to allow Next.js frontend to access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model_path = os.path.join(base_dir, "models/yolov26n-pose.pt")
db_path = os.path.join(base_dir, "incidents.db")

graph = create_fall_detection_graph(
    model_path=model_path,
    db_path=db_path,
    slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
    email_sender=os.getenv("EMAIL_SENDER"),
    email_password=os.getenv("EMAIL_PASSWORD"),
    email_receiver=os.getenv("EMAIL_RECEIVER"),
    skip_vlm=False
)

# Global variables for streaming state
active_camera = None

def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"status": "Fall Detection API is running"}

@app.get("/api/incidents")
def get_recent_incidents(limit: int = 20):
    """최근 발생한 낙상 알람 DB에서 가져오기 및 전체 통계 반환"""
    try:
        conn = get_db_connection()
        logs = conn.execute(
            "SELECT * FROM incidents ORDER BY timestamp DESC LIMIT ?", 
            (limit,)
        ).fetchall()
        
        # 실제 누적 통계치 계산
        total_count = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        high_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity='HIGH'").fetchone()[0]
        medium_count = conn.execute("SELECT COUNT(*) FROM incidents WHERE severity='MEDIUM'").fetchone()[0]
        
        conn.close()
        
        formatted_logs = []
        for log in logs:
            d = dict(log)
            formatted_logs.append({
                "id": d.get("incident_id", str(d.get("id"))),
                "timestamp": d.get("timestamp", ""),
                "severity": d.get("severity", "LOW"),
                "score": d.get("severity_score", 0)
            })
            
        return {
            "total": total_count,
            "high": high_count,
            "medium": medium_count,
            "logs": formatted_logs
        }
    except Exception as e:
        return {"error": str(e)}

async def generate_frames(video_source):
    """비디오 프레임을 가져와 LangGraph를 돌리고 MJPEG 형식으로 변환하여 송출"""
    
    # 각 스트림마다 독립적인 그래프 엔진을 가동해야 메모리 간섭이 없음
    local_graph = create_fall_detection_graph(
        model_path=model_path,
        db_path=db_path,
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_receiver=os.getenv("EMAIL_RECEIVER"),
        skip_vlm=False
    )
    
    # For testing, we can use 0 for webcam or a specific test video file path
    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print(f"Failed to open video source: {video_source}")
        return

    width, height = 980, 740
    frame_count = 0
    alert_frames_remaining = 0
    last_severity = "LOW"
    last_score = 0
    last_dispatch_msg = ""
    
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
    }

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                # Loop video for continuous testing
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame_count += 1

            frame = cv2.resize(frame, (width, height))
            current_state["frame"] = frame.copy()

            # 그래프 실행 (동기 함수이므로 ThreadPoolExecutor를 사용해 비동기 I/O를 막지 않게 분리)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, local_graph.invoke, current_state)
            
            # Update persisted state with result from LangGraph
            current_state = result

            # 결과 프레임 꾸미기
            annotated = result.get("annotated_frame")
            if annotated is None:
                annotated = frame.copy()

            if result.get("fall_detected"):
                alert_frames_remaining = 60  # Hold alert for ~3 seconds
                last_severity = result.get("severity", "LOW")
                last_score = result.get("severity_score", 0)
                
                for action in result.get("actions_taken", []):
                    if action.get("tool") == "notify_security_room":
                        last_dispatch_msg = action.get("result", {}).get("message", "")

            if alert_frames_remaining > 0:
                color = {"LOW": (0, 255, 0), "MEDIUM": (0, 165, 255), "HIGH": (0, 0, 255)}.get(last_severity, (0, 255, 0))
                
                # 좌측 상단 정보 박스
                cv2.rectangle(annotated, (10, 10), (300, 120), (0, 0, 0), -1)
                cv2.rectangle(annotated, (10, 10), (300, 120), color, 2)
                cv2.putText(annotated, f"SEVERITY: {last_severity}", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(annotated, f"Score: {last_score}/100", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # 중앙 대형 경고 문구 (붉은색/노란색)
                if last_severity in ["HIGH", "MEDIUM"]:
                    cv2.putText(annotated, f"[{last_severity}] FALL DETECTED!", (width//2 - 250, height//2), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 4)
                    if last_dispatch_msg:
                        cv2.putText(annotated, last_dispatch_msg, (width//2 - 350, height//2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

                # 화면 가장자리 붉은 테두리
                if last_severity == "HIGH":
                    cv2.rectangle(annotated, (0, 0), (width, height), (0, 0, 255), 10)

                alert_frames_remaining -= 1

            # Encode as JPEG
            _, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()

            # Yield frame for multipart response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # small delay to prevent cpu overload for non-realtime streams
            await asyncio.sleep(0.01)

    finally:
        cap.release()

@app.get("/video_feed")
async def video_feed(video_path: str = "input/02400_H_A_BY_C1.mp4"):
    """Returns the continuous MJPEG video stream"""
    from fastapi.responses import StreamingResponse
    source = os.path.join(base_dir, video_path)
    return StreamingResponse(generate_frames(source), media_type="multipart/x-mixed-replace; boundary=frame")
