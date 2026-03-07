import math
from ultralytics import YOLO

class PerceptionNode:
    """YOLO Pose 기반 낙상 감지"""

    VELOCITY_THRESHOLD = 15
    ANGLE_THRESHOLD = 35   # 낮출수록 더 잘 감지 (45→35: 완만히 누운 자세도 포착)
    CONFIRM_FRAMES = 5     # 연속 프레임 수 완화 (15→5)
    COOLDOWN_FRAMES = 60   # Cooldown of 3 seconds (assuming 20fps) to prevent spam

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        self.previous_nose_y = {}
        self.fall_duration_counter = {}
        self.cooldown_counter = {}

    def process(self, frame, state: dict) -> dict:
        """프레임 처리 후 state 업데이트"""
        # save=False 파라미터를 명시하여 불필요한 빈 폴더(project/track) 생성을 막습니다
        results = self.model.track(frame, persist=True, verbose=False, save=False, exist_ok=True, name="run")

        fall_detected = False
        pose_data = {}
        no_movement_seconds = 0
        track_id = None

        if results[0].boxes.id is not None and results[0].keypoints is not None:
            track_ids = results[0].boxes.id.int().cpu().tolist()
            keypoints = results[0].keypoints.xy.cpu().numpy()

            for tid, kps in zip(track_ids, keypoints):
                if len(kps) < 17:
                    continue

                if tid not in self.cooldown_counter:
                    self.cooldown_counter[tid] = 0

                # Cooldown decreases safely
                if self.cooldown_counter[tid] > 0:
                    self.cooldown_counter[tid] -= 1

                nose = kps[0]
                left_shoulder, right_shoulder = kps[5], kps[6]
                left_hip, right_hip = kps[11], kps[12]

                # 키포인트 신뢰도 체크
                confs = None
                if results[0].keypoints.conf is not None:
                    confs = results[0].keypoints.conf.cpu().numpy()
                    kp_idx = list(results[0].boxes.id.int().cpu().tolist()).index(tid)
                    nose_conf  = confs[kp_idx][0]
                    hip_conf   = confs[kp_idx][11]
                    if nose_conf < 0.3 or hip_conf < 0.3:
                        continue

                if nose[0] == 0 or left_hip[0] == 0:
                    continue

                # 각도 계산
                shoulder_mid = ((left_shoulder[0] + right_shoulder[0]) / 2,
                               (left_shoulder[1] + right_shoulder[1]) / 2)
                hip_mid = ((left_hip[0] + right_hip[0]) / 2,
                          (left_hip[1] + right_hip[1]) / 2)

                dx = abs(shoulder_mid[0] - hip_mid[0])
                dy = abs(shoulder_mid[1] - hip_mid[1])
                angle = 90 if dy == 0 else math.degrees(math.atan(dx / dy))

                # 속도 계산
                velocity = 0
                if tid in self.previous_nose_y:
                    velocity = nose[1] - self.previous_nose_y[tid]
                self.previous_nose_y[tid] = nose[1]

                # 낙상 판단 로직 보완: 
                # 오랫동안 누워 있음 (각도 임계치 초과 유지)
                is_lying = angle > self.ANGLE_THRESHOLD

                if tid not in self.fall_duration_counter:
                    self.fall_duration_counter[tid] = 0

                if is_lying:
                    self.fall_duration_counter[tid] += 1
                else:
                    # 즉시 리셋 대신 서서히 감소 (하이스테리시스)
                    # → 1~2프레임 오감지가 있어도 카운터가 유지됨
                    self.fall_duration_counter[tid] = max(0, self.fall_duration_counter[tid] - 1)

                # 디버그 로그: 각도와 카운터 상태 출력
                print(f"[Perception] ID={tid} 각도={angle:.1f}° (임계={self.ANGLE_THRESHOLD}) "
                      f"누움={is_lying} 카운터={self.fall_duration_counter[tid]}/{self.CONFIRM_FRAMES} "
                      f"쿨다운={self.cooldown_counter[tid]}")

                # Check logic with cooldown
                if self.fall_duration_counter[tid] > self.CONFIRM_FRAMES and self.cooldown_counter[tid] == 0:
                    fall_detected = True
                    track_id = tid

                    # Prevent instant re-triggering for the same fall
                    self.cooldown_counter[tid] = self.COOLDOWN_FRAMES

                    # 20fps 기준 프레임 → 초 변환
                    no_movement_seconds = self.fall_duration_counter[tid] / 20.0
                    pose_data = {
                        "angle": angle,
                        "velocity": velocity,
                        "keypoints": kps.tolist()
                    }
                    print(f"🚨 [Perception] 낙상 감지! ID={tid}, 각도={angle:.1f}°, 지속={no_movement_seconds:.1f}s")
                    break

        return {
            "frame": frame,
            "fall_detected": fall_detected,
            "pose_data": pose_data,
            "no_movement_seconds": no_movement_seconds,
            "track_id": track_id,
            "annotated_frame": results[0].plot() if results else frame
        }
