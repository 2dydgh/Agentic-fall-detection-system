import cv2
import cvzone
import math
import numpy as np
from ultralytics import YOLO
import os
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
from unittest.mock import patch             # <--- [추가] 가짜 검사 통과용
from transformers.dynamic_module_utils import get_imports

# -----------------------------------------------------------
# [PART 1] Moondream2 모델 로드 (Florence-2 대신 사용)
# -----------------------------------------------------------
print("▶ Moondream2 모델 로딩 중... (가볍고 빠릅니다!)")
from transformers import AutoTokenizer, AutoModelForCausalLM

vlm_model_id = "vikhyatk/moondream2"
# Moondream은 버전 업데이트가 잦아서 특정 리비전(버전)을 고정하는 게 안전합니다.
revision = "2024-08-26" 
device = "cuda" if torch.cuda.is_available() else "cpu"

vlm_model = AutoModelForCausalLM.from_pretrained(
    vlm_model_id, 
    trust_remote_code=True, 
    revision=revision
).to(device)

vlm_tokenizer = AutoTokenizer.from_pretrained(vlm_model_id, revision=revision)

print(f"✅ Moondream2 로드 성공! (Device: {device})")


device = "cuda" if torch.cuda.is_available() else "cpu"

# -----------------------------------------------------------
# [PART 2] VLM 분석 함수 (Moondream2 전용)
# -----------------------------------------------------------
def analyze_with_vlm(frame_bgr):
    """
    Moondream2를 사용하여 이미지를 설명합니다.
    """
    # OpenCV(BGR) -> PIL(RGB) 변환
    image_pil = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))

    # 1. 이미지를 먼저 모델이 이해할 수 있는 숫자로 변환 (Encoding)
    enc_image = vlm_model.encode_image(image_pil)

    # 2. 질문 정의 (Moondream은 태그 없이 그냥 영어로 물어봅니다)
    # Florence-2 때처럼 상세하게 물어봅니다.
    question = "Describe the person's clothing, gender, and surrounding hazards in this fall accident scene in detail."

    # 3. 답변 생성 (answer_question 함수가 내장되어 있어 편합니다)
    answer = vlm_model.answer_question(enc_image, question, vlm_tokenizer)

    # -------------------------------------------------------------
    # [톤 보정] Florence-2 때처럼 '편안하다'는 말을 '위급하다'로 변경
    # -------------------------------------------------------------
    replacements = {
        "relaxed": "unresponsive",
        "resting": "collapsed",
        "sleeping": "unconscious",
        "lying": "fallen",
        "The image shows": "EMERGENCY REPORT:" 
    }
    
    final_report = answer
    for old, new in replacements.items():
        final_report = final_report.replace(old, new)
        
    return final_report

# -----------------------------------------------------------
# [PART 3] 기존 YOLO 설정
# -----------------------------------------------------------
base_dir = os.path.dirname(os.path.abspath(__file__))
input_video = os.path.join(base_dir, 'input', 'fall.mp4')
output_dir = os.path.join(base_dir, 'output')
output_video = os.path.join(output_dir, 'output_fall_moondream.mp4') # 파일명 변경
model_path = os.path.join(base_dir, 'models', 'yolov8n-pose.pt')

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

model = YOLO(model_path)
cap = cv2.VideoCapture(input_video)
target_width = 980
target_height = 740
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_video, fourcc, 20.0, (target_width, target_height))

# 상태 변수들
previous_nose_y = {} 
fall_duration_counter = {} 
# [NEW] VLM 분석을 이미 했는지 체크하는 집합 (중복 분석 방지)
analyzed_track_ids = set()
# [NEW] 화면에 띄울 리포트 내용 저장소
vlm_reports = {} 

VELOCITY_THRESHOLD = 15 
ANGLE_THRESHOLD = 50 
CONFIRM_FRAMES = 15 
frame_count = 0
frame_skip = 1 

print("▶ 영상 처리 시작...")

while True:
    ret, frame = cap.read()
    if not ret: break

    frame_count += 1
    if frame_count % frame_skip != 0: continue

    frame = cv2.resize(frame, (target_width, target_height))
    
    # 원본 프레임 복사 (VLM 분석용 - 선 그리기 전의 깨끗한 이미지)
    clean_frame = frame.copy()

    results = model.track(frame, persist=True, verbose=False)
    annotated_frame = results[0].plot()

    if results[0].boxes.id is not None and results[0].keypoints is not None:
        track_ids = results[0].boxes.id.int().cpu().tolist()
        keypoints = results[0].keypoints.xy.cpu().numpy()

        for track_id, kps in zip(track_ids, keypoints):
            if len(kps) < 17: continue

            nose = kps[0]
            left_shoulder = kps[5]
            right_shoulder = kps[6]
            left_hip = kps[11]
            right_hip = kps[12]

            if nose[0] == 0 or left_hip[0] == 0 or left_shoulder[0] == 0: continue

            # 1. 각도 계산
            shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2
            hip_mid_x = (left_hip[0] + right_hip[0]) / 2
            hip_mid_y = (left_hip[1] + right_hip[1]) / 2

            dx = abs(shoulder_mid_x - hip_mid_x)
            dy = abs(shoulder_mid_y - hip_mid_y)
            if dy == 0: angle = 90 
            else: angle = math.degrees(math.atan(dx / dy))

            # 2. 속도 계산
            current_nose_y = nose[1]
            velocity = 0
            if track_id in previous_nose_y:
                velocity = current_nose_y - previous_nose_y[track_id]
            previous_nose_y[track_id] = current_nose_y

            # 3. 낙상 판단
            is_lying_down = angle > ANGLE_THRESHOLD
            
            if track_id not in fall_duration_counter:
                fall_duration_counter[track_id] = 0

            if is_lying_down:
                fall_duration_counter[track_id] += 1
            else:
                fall_duration_counter[track_id] = 0
                # 일어났으면 분석 기록 초기화 (다시 넘어지면 또 분석하게)
                if track_id in analyzed_track_ids:
                    analyzed_track_ids.remove(track_id)
                if track_id in vlm_reports:
                    del vlm_reports[track_id]

            cx, cy = int(shoulder_mid_x), int(shoulder_mid_y)

            # -----------------------------------------------------------
            # [핵심] 낙상 확정 시 -> VLM 분석 트리거
            # -----------------------------------------------------------
            if fall_duration_counter[track_id] > CONFIRM_FRAMES:
                # 1단계: 화면에 기본 경고 표시
                cvzone.putTextRect(annotated_frame, 'FALL DETECTED', [cx, cy - 60], 
                                   scale=3, thickness=3, colorR=(0, 0, 255))
                
                # 2단계: VLM 분석 (아직 안 했다면)
                if track_id not in analyzed_track_ids:
                    print(f"\n[ID:{track_id}] 🚨 낙상 감지! MoonDream 분석 시작...")
                    
                    # 잠시 화면에 'Analyzing...' 표시 (UX)
                    cvzone.putTextRect(annotated_frame, 'AI Analyzing...', [cx, cy - 100], 
                                       scale=2, thickness=2, colorR=(255, 0, 0))
                    # cv2.imshow("Result", annotated_frame)
                    # cv2.waitKey(1) # 화면 갱신

                    # VLM 호출 (여기서 약간 멈칫할 수 있음 - 정상)
                    report = analyze_with_vlm(clean_frame)
                    
                    # 결과 저장
                    vlm_reports[track_id] = report
                    analyzed_track_ids.add(track_id)
                    print(f"[ID:{track_id}] 📝 리포트: {report}")

                # 3단계: 분석된 리포트 화면에 띄우기 (여러 줄로 나누기)
                if track_id in vlm_reports:
                    # 1. 데이터 파싱 (이전과 동일)
                    report_text = vlm_reports[track_id].replace("EMERGENCY REPORT:", "").strip()
                    sentences = report_text.split('. ')
                    structured_data = {"STATUS": "🚨 FALL DETECTED (Unresponsive)", "WHO": "", "WEAR": "", "LOC": ""}
                    
                    for s in sentences:
                        s = s.strip()
                        if len(s) < 5: continue
                        s_lower = s.lower()
                        if not structured_data["WHO"] and any(word in s_lower for word in ["man", "woman", "person", "victim", "male", "female"]):
                            structured_data["WHO"] = s
                            continue
                        if any(word in s_lower for word in ["wearing", "dressed", "jacket", "jeans", "shoes"]):
                            structured_data["WEAR"] = s
                            continue
                        if any(word in s_lower for word in ["floor", "warehouse", "ground", "concrete", "background"]):
                            if structured_data["LOC"]:
                                if len(structured_data["LOC"]) < 30: structured_data["LOC"] += " " + s
                            else:
                                structured_data["LOC"] = s

                    # 2. HUD 박스 그리기 (크기 대폭 증가!)
                    box_x, box_y = 20, 20
                    box_w, box_h = 600, 280 # 너비와 높이를 늘렸습니다.
                    
                    overlay = annotated_frame.copy()
                    cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 0), -1)
                    cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), (0, 0, 255), 2)
                    annotated_frame = cv2.addWeighted(overlay, 0.6, annotated_frame, 0.4, 0)

                    # 3. 텍스트 출력 설정
                    start_text_x = box_x + 20
                    start_text_y = box_y + 40
                    line_gap = 30
                    font_scale = 0.6 # 폰트 크기 살짝 키움
                    font_thickness = 1
                    
                    # [핵심 기능] 긴 텍스트 자동 줄바꿈 함수
                    def draw_multiline_text(img, text, x, y, max_width_chars, color):
                        current_y = y
                        lines = []
                        while len(text) > max_width_chars:
                            # max_width_chars 길이 근처의 공백을 찾아서 자름
                            split_idx = text.rfind(' ', 0, max_width_chars)
                            if split_idx == -1: split_idx = max_width_chars # 공백 없으면 그냥 자름
                            lines.append(text[:split_idx])
                            text = text[split_idx:].strip()
                        lines.append(text) # 남은 부분 추가
                        
                        for line in lines:
                            cv2.putText(img, line, (x, current_y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)
                            current_y += line_gap
                        return current_y # 다음 텍스트가 시작될 Y좌표 반환

                    # 헤더 출력
                    cv2.putText(annotated_frame, "EMERGENCY ALERT", (start_text_x, start_text_y), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    current_y = start_text_y + 40
                    cv2.line(annotated_frame, (start_text_x, start_text_y + 10), (box_x + box_w - 20, start_text_y + 10), (255, 255, 255), 1)

                    # 내용 출력 (자동 줄바꿈 적용)
                    max_chars = 55 # 한 줄에 들어갈 최대 글자 수
                    
                    if structured_data["WHO"]:
                        prefix = "WHO: "
                        current_y = draw_multiline_text(annotated_frame, prefix + structured_data["WHO"], start_text_x, current_y, max_chars, (255, 255, 255))
                    
                    if structured_data["WEAR"]:
                        prefix = "WEAR: "
                        # "He is wearing" 같은 불필요한 앞부분 제거
                        clean_wear = structured_data["WEAR"].replace("He is wearing ", "").replace("She is wearing ", "")
                        current_y = draw_multiline_text(annotated_frame, prefix + clean_wear, start_text_x, current_y, max_chars, (0, 255, 255))

                    if structured_data["LOC"]:
                        prefix = "LOC : "
                        current_y = draw_multiline_text(annotated_frame, prefix + structured_data["LOC"], start_text_x, current_y, max_chars, (200, 200, 200))
    out.write(annotated_frame)
    # cv2.imshow("Result", annotated_frame)
    
    # if cv2.waitKey(1) & 0xFF == ord('q'):
    #     break

cap.release()
out.release()
cv2.destroyAllWindows()
print(f"\n✅ 완료! 저장된 파일: {output_video}")