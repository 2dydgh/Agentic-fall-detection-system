import cv2
import cvzone
import math
from ultralytics import YOLO
import numpy as np

import os

# 1. 파일 설정
# -----------------------------------------------------------
# [핵심] 절대 경로 자동 설정 (이제 어디서 실행하든 상관없음)
# -----------------------------------------------------------
# 1. 현재 이 파이썬 파일(main_pose_upgrade.py)이 있는 위치를 찾습니다.
base_dir = os.path.dirname(os.path.abspath(__file__))

# 2. 파일 경로를 '현재 파일 위치' 기준으로 조립합니다.
# 예: ~/DETECT/Project/Fall_Detection/input/50waystofall.mp4
input_video = os.path.join(base_dir, 'input', 'queda.mp4')
output_dir = os.path.join(base_dir, 'output')
output_video = os.path.join(output_dir, 'output_queda2.mp4')
model_path = os.path.join(base_dir, 'models', 'yolov8n-pose.pt')

# 2. 모델 로드
# Pose 모델을 사용합니다.
model = YOLO(model_path)

# 저장 설정
cap = cv2.VideoCapture(input_video)

# 저장 설정
target_width = 980
target_height = 740
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, 20.0, (target_width, target_height))

# 속도 향상을 위한 설정
frame_skip = 1  # 처리할 프레임 간격
frame_count = 0


while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # 프레임 스킵 적용 -> 속도 향상
    if frame_count % frame_skip != 0:
        continue

    frame = cv2.resize(frame, (target_width, target_height))

    # 3. 모델 추론
    results = model(frame)

    # 4. 뼈대 그리기 (시각화용)
    annotated_frame = results[0].plot()

    # 5. [핵심] 관절 좌표(Keypoints) 가져오기
    # results[0].keypoints.xy는 (사람수, 17개관절, x/y좌표) 형태의 데이터입니다.
    if results[0].keypoints is not None:
        keypoints_data = results[0].keypoints.xy.cpu().numpy()

        for kps in keypoints_data:
            # kps는 한 사람의 관절 데이터 (17개 점)
            # 0번: 코(Nose), 15번: 왼발목, 16번: 오른발목 (COCO 포맷 기준)
            
            # 관절이 감지되지 않으면(0,0) 계산에서 제외하기 위해 체크
            if len(kps) < 17: continue

            nose = kps[0]         # [x, y]
            left_ankle = kps[15]  # [x, y]
            right_ankle = kps[16] # [x, y]

            # 발목이나 코가 제대로 안 찍혔으면(좌표가 0이면) 건너뜀
            if nose[0] == 0 or left_ankle[0] == 0 or right_ankle[0] == 0:
                continue

            # 두 발목의 평균 위치 계산
            ankle_y = (left_ankle[1] + right_ankle[1]) / 2
            ankle_x = (left_ankle[0] + right_ankle[0]) / 2

            # 6. 낙상 판단 로직 (관절 기반)
            
            # (1) 수직 길이 (머리부터 발목까지 Y 거리)
            vertical_dist = abs(ankle_y - nose[1])
            
            # (2) 수평 길이 (머리부터 발목까지 X 거리)
            horizontal_dist = abs(ankle_x - nose[0])

            # (3) 판단: 수평 길이가 수직 길이보다 길어지면 낙상!
            # (Box 방식보다 정확한 이유: 빈 공간이 아니라 실제 뼈대 길이를 비교함)
            if horizontal_dist > vertical_dist:
                
                # 시각화 (머리 위치에 경고 띄우기)
                x_nose, y_nose = int(nose[0]), int(nose[1])
                cvzone.putTextRect(annotated_frame, 'Fall Detected', [x_nose, y_nose - 50], 
                                   scale=2, thickness=2, colorR=(0, 0, 255))
                
                print("Fall Detected using Keypoints!", end='\r')

    # 저장 및 출력
    out.write(annotated_frame)
    # 이미지 파일은 선택 -> 오래 걸릴 수 있어 주석 처리
    # cv2.imwrite('result_pose_real.jpg', annotated_frame)

cap.release()
out.release()
cv2.destroyAllWindows()

print(f"\nProcessing Complete! Check '{output_video}'.")