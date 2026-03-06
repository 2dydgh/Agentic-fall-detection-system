import cv2
import cvzone
import math
import numpy as np
from ultralytics import YOLO
import os

# 1. 파일 설정
# -----------------------------------------------------------
# [핵심] 절대 경로 자동 설정 (이제 어디서 실행하든 상관없음)
# -----------------------------------------------------------
# 1. 현재 이 파이썬 파일(main_pose_upgrade.py)이 있는 위치를 찾습니다.
base_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 파일 경로를 '현재 파일 위치' 기준으로 조립합니다.
# 예: ~/DETECT/Project/Fall_Detection/input/50waystofall.mp4
input_video = os.path.join(base_dir, 'input', 'fall.mp4')
output_dir = os.path.join(base_dir, 'output')
output_video = os.path.join(output_dir, 'output_fall_yolo26.mp4')
model_path = os.path.join(base_dir, 'models', 'yolov26n-pose.pt')

# 2. 모델 로드
# Pose 모델을 사용합니다.
model = YOLO(model_path)

# 저장 설정
cap = cv2.VideoCapture(input_video)
target_width = 980
target_height = 740
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, 20.0, (target_width, target_height))

# -----------------------------------------------------------
# [상태 저장소] 과거의 데이터를 기억하기 위한 변수들
# -----------------------------------------------------------
# 사람 ID별로 코의 Y좌표를 저장 (속도 계산용)
previous_nose_y = {} 

# 사람 ID별로 넘어진 상태가 몇 프레임 유지됐는지 저장 (체류 시간용)
fall_duration_counter = {} 

# [파라미터 설정] (환경에 따라 조절 가능)
VELOCITY_THRESHOLD = 15   # 코가 1프레임당 15픽셀 이상 떨어지면 '빠르다'고 판단
ANGLE_THRESHOLD = 50      # 몸의 기울기가 50도 이상 기울면 '누웠다'고 판단 (0도:수직, 90도:수평)
CONFIRM_FRAMES = 15       # 약 0.7초 이상 누워있어야 낙상으로 확정 (20fps 기준)
# -----------------------------------------------------------

frame_count = 0
frame_skip = 1 # 2프레임마다 1번씩 처리 (속도 최적화)

while True:
    ret, frame = cap.read()
    if not ret: break

    frame_count += 1
    # 추적 성능을 위해 프레임을 너무 많이 건너뛰면 안됩니다.
    if frame_count % frame_skip != 0: continue

    frame = cv2.resize(frame, (target_width, target_height))

    # 3. 모델 추론 (Tracking 모드)
    # persist=True: 이전 프레임의 사람 ID를 기억함
    results = model.track(frame, persist=True, verbose=False)
    
    # 뼈대 그리기
    annotated_frame = results[0].plot()

    # 데이터 추출
    if results[0].boxes.id is not None and results[0].keypoints is not None:
        # ID와 관절 정보를 묶어서 가져옵니다.
        track_ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.xy.cpu().numpy()

        for track_id, kps in zip(track_ids, keypoints):
            # 관절이 17개가 다 안 잡히면 패스
            if len(kps) < 17: continue

            # (1) 주요 관절 좌표 가져오기
            nose = kps[0]           # 코 (인덱스 0)
            left_shoulder = kps[5]  # 왼쪽 어깨 (5)
            right_shoulder = kps[6] # 오른쪽 어깨 (6)
            left_hip = kps[11]      # 왼쪽 골반 (11)
            right_hip = kps[12]     # 오른쪽 골반 (12)

            # 좌표가 0(감지실패)인 경우 건너뜀
            if nose[0] == 0 or left_hip[0] == 0 or left_shoulder[0] == 0: continue

            # ---------------------------------------------------
            # [논리 1] 척추 각도 (Body Angle) 계산
            # ---------------------------------------------------
            # 어깨 중앙점 계산
            shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2
            # 골반 중앙점 계산
            hip_mid_x = (left_hip[0] + right_hip[0]) / 2
            hip_mid_y = (left_hip[1] + right_hip[1]) / 2

            # 수직선 대비 몸의 기울기 계산
            dx = abs(shoulder_mid_x - hip_mid_x)
            dy = abs(shoulder_mid_y - hip_mid_y)
            
            # dy가 0이면 완전 수평(90도), 아니면 아크탄젠트로 각도 계산
            if dy == 0: angle = 90 
            else: angle = math.degrees(math.atan(dx / dy))

            # ---------------------------------------------------
            # [논리 2] 하강 속도 (Vertical Velocity) 계산
            # ---------------------------------------------------
            current_nose_y = nose[1]
            velocity = 0
            
            # 이전에 기록된 위치가 있다면 속도 계산 (현재위치 - 과거위치)
            if track_id in previous_nose_y:
                velocity = current_nose_y - previous_nose_y[track_id]
            
            # 현재 위치를 저장 (다음 프레임 비교용)
            previous_nose_y[track_id] = current_nose_y

            # ---------------------------------------------------
            # [논리 3] 종합 판단 및 바닥 체류 시간 (Duration)
            # ---------------------------------------------------
            # 조건 1: 몸이 많이 기울었는가? (Angle Check)
            is_lying_down = angle > ANGLE_THRESHOLD
            
            # 조건 2: 갑자기 떨어졌는가? (Velocity Check)
            # (선택 사항: 속도는 순간적이므로, 누워있는 상태라면 카운트를 올림)
            is_fast_drop = velocity > VELOCITY_THRESHOLD

            # 상태 카운터 초기화
            if track_id not in fall_duration_counter:
                fall_duration_counter[track_id] = 0

            # 판단 로직:
            # 몸이 기울어져 있고, (속도가 빨랐거나 OR 이미 카운트가 진행 중이라면)
            if is_lying_down:
                fall_duration_counter[track_id] += 1
            else:
                # 다시 일어났으면 카운터 리셋
                fall_duration_counter[track_id] = 0

            # ---------------------------------------------------
            # [결과 출력]
            # ---------------------------------------------------
            cx, cy = int(shoulder_mid_x), int(shoulder_mid_y)

            # 일정 시간(CONFIRM_FRAMES) 이상 누워있으면 '낙상' 확정
            if fall_duration_counter[track_id] > CONFIRM_FRAMES:
                # 빨간색 경고
                cvzone.putTextRect(annotated_frame, 'FALL DETECTED', [cx, cy - 60], 
                                   scale=3, thickness=3, colorR=(0, 0, 255))
                print(f"ID {track_id}: FALL CONFIRMED! (Frames: {fall_duration_counter[track_id]})", end='\r')
            
            elif is_lying_down and is_fast_drop:
                 # 주황색 경고 (떨어지는 순간)
                cvzone.putTextRect(annotated_frame, 'Falling...', [cx, cy - 60], 
                                   scale=2, thickness=2, colorR=(0, 165, 255))

    # 영상 저장
    out.write(annotated_frame)
    
    # 진행 상황 출력
    if frame_count % 10 == 0:
        print(f"Processing frame {frame_count}...", end='\r')

cap.release()
out.release()
cv2.destroyAllWindows()

print(f"\nProcessing Complete! Check '{output_video}'.")