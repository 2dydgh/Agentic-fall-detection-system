import os
from typing import Optional
from ..tools.db import log_to_db, init_db
from ..tools.snapshot import save_snapshot
from ..tools.slack import send_slack_alert
from ..tools.email_sender import send_email_alert
from ..tools.report import generate_report
from ..tools.mock import notify_security_room

class ActionNode:
    """심각도에 따른 Tool 실행"""

    def __init__(
        self,
        db_path: str = "incidents.db",
        snapshot_dir: str = "snapshots",
        report_dir: str = "reports",
        slack_webhook: Optional[str] = None,
        email_sender: Optional[str] = None,
        email_password: Optional[str] = None,
        email_receiver: Optional[str] = None,
        agent_runner=None
    ):
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        self.report_dir = report_dir
        self.slack_webhook = slack_webhook
        self.email_sender = email_sender
        self.email_password = email_password
        self.email_receiver = email_receiver
        self.agent_runner = agent_runner

        init_db(db_path)

    def process(self, state: dict) -> dict:
        """권장 액션 실행"""
        actions = state.get("recommended_actions", [])
        severity = state.get("severity", "LOW")

        actions_taken = []
        incident_id = None
        snapshot_path = None

        # 1. DB 로깅 (항상)
        if "log_to_db" in actions:
            incident_id = log_to_db(
                db_path=self.db_path,
                severity=severity,
                scene_description=state.get("scene_description", ""),
                severity_score=state.get("severity_score", 0),
                actions_taken=actions,
                audio_scream_detected=state.get("audio_scream_detected", False),
                audio_impact_detected=state.get("audio_impact_detected", False),
                audio_confidence=state.get("audio_confidence", 0.0),
                camera_id=state.get("camera_id", "01"),
            )
            actions_taken.append({"tool": "log_to_db", "incident_id": incident_id})

        # 2. 스냅샷 저장
        if "save_snapshot" in actions and state.get("frame") is not None:
            snapshot_path = save_snapshot(
                frame=state["frame"],
                incident_id=incident_id or "UNKNOWN",
                output_dir=self.snapshot_dir
            )
            actions_taken.append({"tool": "save_snapshot", "path": snapshot_path})

        # 3. 관제실 알림 (Mock)
        if "notify_security_room" in actions:
            result = notify_security_room(
                incident_id=incident_id or "UNKNOWN",
                severity=severity,
                location=state.get("location_type", "Unknown")
            )
            actions_taken.append({"tool": "notify_security_room", "result": result})

        # 4. 보고서 생성 (이메일에 첨부하기 위해 먼저 생성)
        report_path = None
        if "generate_report" in actions:
            report_path = generate_report(
                incident_id=incident_id or "UNKNOWN",
                severity=severity,
                severity_score=state.get("severity_score", 0),
                scene_description=state.get("scene_description", ""),
                estimated_age=state.get("estimated_age", "unknown"),
                location_type=state.get("location_type", "other"),
                recommended_actions=actions,
                output_dir=self.report_dir
            )
            actions_taken.append({"tool": "generate_report", "path": report_path})

        # 5. 이메일 알림
        if "send_email_alert" in actions and self.email_sender and self.email_password:
            success = send_email_alert(
                sender_email=self.email_sender,
                sender_password=self.email_password,
                receiver_email=self.email_receiver,
                severity=severity,
                scene_description=state.get("scene_description", ""),
                incident_id=incident_id or "UNKNOWN",
                snapshot_path=snapshot_path,
                report_path=report_path
            )
            actions_taken.append({"tool": "send_email_alert", "success": success})

        # 6. 비동기 Agent 디스패치 (블로킹하지 않음)
        if self.agent_runner is not None:
            self.agent_runner.dispatch({
                "incident_id": incident_id,
                "severity": severity,
                "severity_score": state.get("severity_score", 0),
                "scene_description": state.get("scene_description", ""),
                "estimated_age": state.get("estimated_age", "unknown"),
                "location_type": state.get("location_type", "other"),
                "audio_scream_detected": state.get("audio_scream_detected", False),
                "audio_impact_detected": state.get("audio_impact_detected", False),
                "no_movement_seconds": state.get("no_movement_seconds", 0),
            })
            actions_taken.append({"tool": "async_agent_dispatched"})

        return {
            "actions_taken": actions_taken,
            "incident_id": incident_id,
            "snapshot_path": snapshot_path,
        }
