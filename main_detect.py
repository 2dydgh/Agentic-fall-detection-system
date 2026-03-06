import cv2
import cvzone
import math
from ultralytics import YOLO
import os 

base_dir = os.path.dirname(os.path.abspath(__file__))

input_video = os.path.join(base_dir, 'input', '50waystofall.mp4')
output_dir = os.path.join(base_dir, 'output')
output_video = os.path.join(output_dir, 'output_queda2.mp4')
model_path = os.path.join(base_dir, 'models', 'yolov8n-pose.pt')

# 비디오 파일 불러오기
cap = cv2.VideoCapture(input_video)

model = YOLO(model_path)

classnames = []
with open('classes.txt', 'r') as f:
    classnames = f.read().splitlines()

# 기존 (Box 방식): "박스가 납작해졌니?" (박스 전체 크기만 봄)

# ---------------------------------------------------------
# [추가됨] 결과를 동영상 파일로 저장하기 위한 설정
# ---------------------------------------------------------
# 우리가 리사이즈할 크기 (가로, 세로)
target_width = 980
target_height = 740

# 저장할 동영상 설정 (파일명: output_detect.mp4)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, 20.0, (target_width, target_height))
# ---------------------------------------------------------

while True:
    ret, frame = cap.read()
    
    # 동영상이 끝나면 루프 종료
    if not ret:
        break

    # 프레임 크기 조절
    frame = cv2.resize(frame, (target_width, target_height))

    results = model(frame)

    for info in results:
        parameters = info.boxes
        for box in parameters:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            confidence = box.conf[0]
            class_detect = box.cls[0]
            class_detect = int(class_detect)
            
            # 클래스 인덱스가 범위 내에 있는지 안전장치
            if class_detect < len(classnames):
                class_name = classnames[class_detect]
            else:
                class_name = str(class_detect)
                
            conf = math.ceil(confidence * 100)

            # implement fall detection
            height = y2 - y1
            width = x2 - x1
            threshold = height - width

            # 'person'이고 신뢰도가 80% 이상일 때만 박스 그리기
            if conf > 80 and class_name == 'person':
                cvzone.cornerRect(frame, [x1, y1, width, height], l=30, rt=6)
                cvzone.putTextRect(frame, f'{class_name} {conf}%', [x1 + 8, y1 - 12], thickness=2, scale=2)
            
                # 낙상 감지 로직 (width가 height보다 길어지면 넘어짐으로 간주)
                if threshold < 0:
                    # [수정] 텍스트 위치를 [height, width]가 아니라 박스 위쪽 [x1, y1] 근처로 수정
                    cvzone.putTextRect(frame, 'Fall Detected', [x1, y1 - 50], thickness=2, scale=2, colorR=(0,0,255))
            
            else:
                pass

    # ---------------------------------------------------------
    # [수정됨] 화면 띄우기 대신 파일 저장
    # ---------------------------------------------------------
    
    # 1. 동영상 파일에 현재 프레임 쓰기 (나중에 영상으로 확인 가능)
    out.write(frame)
    
    # 2. 이미지 파일로도 계속 덮어쓰기 (실행 중인지 확인용)
    cv2.imwrite('result_detect.jpg', frame)
    
    # 진행 상황 로그 출력 (end='\r'로 한 줄에서 갱신)
    print("Processing video... Saving to output.mp4", end='\r')

    # cv2.imshow('frame', frame)  <-- 에러 원인 주석 처리
    # if cv2.waitKey(1) & 0xFF == ord('t'): <-- GUI 없으므로 주석 처리
    #    break

# 작업 완료 후 자원 해제
cap.release()
out.release() # 저장 파일 닫기 (중요)
cv2.destroyAllWindows()

print("\nProcessing Complete! Check 'output_detect_50.mp4' and 'result_detect.jpg'.")