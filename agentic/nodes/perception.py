import math
from ultralytics import YOLO

class PerceptionNode:
    """YOLO Pose 기반 낙상 감지 — 다중 신호 판정"""

    ANGLE_THRESHOLD = 35
    ANGLE_THRESHOLD_SOFT = 20      # 높이 전이 동반 시 완화된 각도 임계치
    VELOCITY_THRESHOLD = 15        # 코 Y좌표 하강 속도 (px/frame)
    NOSE_DROP_RATIO = 0.12         # 프레임 높이 대비 코 하강 비율
    CONFIRM_FRAMES = 5
    COOLDOWN_FRAMES = 60
    STANDING_UPDATE_ANGLE = 20     # 이 각도 미만이면 "서 있음"으로 간주

    def __init__(self, model_path: str):
        self.model = YOLO(model_path)
        self.previous_nose_y = {}
        self.fall_duration_counter = {}
        self.cooldown_counter = {}
        self.standing_nose_y = {}       # 서 있을 때 코 Y 위치 (프레임 상단 = 작은 값)
        self.bbox_ratio_history = {}    # 바운딩박스 종횡비

    def _detect_height_drop(self, tid, nose_y, frame_height):
        """코 Y좌표가 서 있을 때보다 크게 하강했는지 판정"""
        if tid not in self.standing_nose_y:
            self.standing_nose_y[tid] = nose_y
            return False

        drop = (nose_y - self.standing_nose_y[tid]) / frame_height
        return drop > self.NOSE_DROP_RATIO

    def _update_standing_height(self, tid, nose_y, angle):
        """서 있는 상태일 때 기준 높이를 갱신 (지수 이동 평균)"""
        if angle < self.STANDING_UPDATE_ANGLE:
            if tid in self.standing_nose_y:
                self.standing_nose_y[tid] = 0.8 * self.standing_nose_y[tid] + 0.2 * nose_y
            else:
                self.standing_nose_y[tid] = nose_y

    def _get_bbox_ratio(self, kps):
        """키포인트에서 신체 종횡비 계산 (가로/세로). >1이면 수평"""
        nose, l_hip, r_hip = kps[0], kps[11], kps[12]
        l_shoulder, r_shoulder = kps[5], kps[6]

        xs = [nose[0], l_shoulder[0], r_shoulder[0], l_hip[0], r_hip[0]]
        ys = [nose[1], l_shoulder[1], r_shoulder[1], l_hip[1], r_hip[1]]

        width = max(xs) - min(xs)
        height = max(ys) - min(ys)

        if height < 1:
            return 0
        return width / height

    def process(self, frame, state: dict) -> dict:
        """프레임 처리 후 state 업데이트"""
        results = self.model.track(frame, persist=True, verbose=False, save=False, exist_ok=True, name="run")
        frame_height = frame.shape[0]

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

                if self.cooldown_counter[tid] > 0:
                    self.cooldown_counter[tid] -= 1

                nose = kps[0]
                left_shoulder, right_shoulder = kps[5], kps[6]
                left_hip, right_hip = kps[11], kps[12]

                # 키포인트 신뢰도 체크
                if results[0].keypoints.conf is not None:
                    confs = results[0].keypoints.conf.cpu().numpy()
                    kp_idx = list(results[0].boxes.id.int().cpu().tolist()).index(tid)
                    nose_conf = confs[kp_idx][0]
                    hip_conf = confs[kp_idx][11]
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

                # 속도 계산 (코 Y좌표 변화량, 양수 = 하강)
                velocity = 0
                if tid in self.previous_nose_y:
                    velocity = nose[1] - self.previous_nose_y[tid]
                self.previous_nose_y[tid] = nose[1]

                # 높이 전이 감지
                has_height_drop = self._detect_height_drop(tid, nose[1], frame_height)
                has_velocity = velocity > self.VELOCITY_THRESHOLD

                # 서 있을 때 기준 높이 갱신
                self._update_standing_height(tid, nose[1], angle)

                # 바운딩박스 종횡비
                bbox_ratio = self._get_bbox_ratio(kps)
                is_horizontal = bbox_ratio > 1.0

                # ── 다중 신호 낙상 판정 ──
                # 신호 1: 각도 기반 (기존)
                angle_signal = angle > self.ANGLE_THRESHOLD
                # 신호 2: 완화 각도 + 높이 전이 (카메라 앵글 보정)
                drop_signal = angle > self.ANGLE_THRESHOLD_SOFT and has_height_drop
                # 신호 3: 높이 전이 + 하강 속도 (빠른 낙상)
                velocity_signal = has_height_drop and has_velocity
                # 신호 4: 종횡비 반전 + 높이 전이 (수평 자세 전환)
                ratio_signal = is_horizontal and has_height_drop

                is_falling = angle_signal or drop_signal or velocity_signal or ratio_signal

                if tid not in self.fall_duration_counter:
                    self.fall_duration_counter[tid] = 0

                if is_falling:
                    self.fall_duration_counter[tid] += 1
                else:
                    self.fall_duration_counter[tid] = max(0, self.fall_duration_counter[tid] - 1)

                # 디버그 로그
                signals = []
                if angle_signal: signals.append("각도")
                if drop_signal: signals.append("전이")
                if velocity_signal: signals.append("속도")
                if ratio_signal: signals.append("종횡비")
                signal_str = "+".join(signals) if signals else "-"

                print(f"[Perception] ID={tid} 각도={angle:.1f}° "
                      f"속도={velocity:.1f} 종횡비={bbox_ratio:.2f} "
                      f"높이전이={has_height_drop} "
                      f"신호=[{signal_str}] "
                      f"카운터={self.fall_duration_counter[tid]}/{self.CONFIRM_FRAMES} "
                      f"쿨다운={self.cooldown_counter[tid]}")

                if self.fall_duration_counter[tid] > self.CONFIRM_FRAMES and self.cooldown_counter[tid] == 0:
                    fall_detected = True
                    track_id = tid

                    self.cooldown_counter[tid] = self.COOLDOWN_FRAMES
                    no_movement_seconds = self.fall_duration_counter[tid] / 20.0
                    pose_data = {
                        "angle": angle,
                        "velocity": velocity,
                        "bbox_ratio": bbox_ratio,
                        "height_drop": has_height_drop,
                        "signals": signals,
                        "keypoints": kps.tolist()
                    }
                    print(f"[Perception] 낙상 감지! ID={tid}, 신호=[{signal_str}], "
                          f"각도={angle:.1f}°, 속도={velocity:.1f}, 지속={no_movement_seconds:.1f}s")
                    break

        return {
            "frame": frame,
            "fall_detected": fall_detected,
            "pose_data": pose_data,
            "no_movement_seconds": no_movement_seconds,
            "track_id": track_id,
            "annotated_frame": results[0].plot() if results else frame
        }
