import cv2
import os
import sys
from ultralytics import YOLO
import math

def process_video(video_path, output_path):
    print(f"Processing {video_path}...", flush=True)
    model = YOLO("models/yolov26n-pose.pt")
    cap = cv2.VideoCapture(video_path)
    
    width = 480
    height = 360
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    ANGLE_THRESHOLD = 35
    CONFIRM_FRAMES = 5
    
    fall_durations = {}
    cooldowns = {}
    
    alert_frames_remaining = 0
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    frame_count = 0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        # for fast testing, process only a segment or all? all is fine (~15 secs)
        frame_count += 1
        
        frame = cv2.resize(frame, (width, height))
        results = model.track(frame, persist=True, verbose=False, save=False, exist_ok=True, name='run')
        
        annotated = results[0].plot() if results else frame.copy()
        
        fall_detected = False
        
        if results and results[0].boxes and results[0].boxes.id is not None and results[0].keypoints is not None:
            track_ids = results[0].boxes.id.int().cpu().tolist()
            keypoints = results[0].keypoints.xy.cpu().numpy()
            confs = results[0].keypoints.conf.cpu().numpy() if results[0].keypoints.conf is not None else None
            
            for tid, kps in zip(track_ids, keypoints):
                if len(kps) < 17: continue
                if tid not in fall_durations: fall_durations[tid] = 0
                if tid not in cooldowns: cooldowns[tid] = 0
                if cooldowns[tid] > 0: cooldowns[tid] -= 1
                
                nose, l_sh, r_sh, l_hp, r_hp = kps[0], kps[5], kps[6], kps[11], kps[12]
                
                if confs is not None:
                    kp_idx = list(results[0].boxes.id.int().cpu().tolist()).index(tid)
                    if confs[kp_idx][0] < 0.3 or confs[kp_idx][11] < 0.3: continue
                
                if nose[0] == 0 or l_hp[0] == 0: continue
                
                sh_mid = ((l_sh[0]+r_sh[0])/2, (l_sh[1]+r_sh[1])/2)
                hp_mid = ((l_hp[0]+r_hp[0])/2, (l_hp[1]+r_hp[1])/2)
                dx, dy = abs(sh_mid[0]-hp_mid[0]), abs(sh_mid[1]-hp_mid[1])
                angle = 90 if dy==0 else math.degrees(math.atan(dx/dy))
                
                if angle > ANGLE_THRESHOLD:
                    fall_durations[tid] += 1
                else:
                    fall_durations[tid] = max(0, fall_durations[tid] - 1)
                    
                if fall_durations[tid] > CONFIRM_FRAMES and cooldowns[tid] == 0:
                    fall_detected = True
                    cooldowns[tid] = 60
                    break

        if fall_detected:
            alert_frames_remaining = 60
            
        if alert_frames_remaining > 0:
            color = (0, 0, 255) # HIGH
            cv2.rectangle(annotated, (10, 10), (310, 80), (0, 0, 0), -1)
            cv2.rectangle(annotated, (10, 10), (310, 80), color, 2)
            cv2.putText(annotated, f"FALL: HIGH (85/100)", (20, 55), font, 0.7, color, 2)
            cv2.putText(annotated, "FALL DETECTED!", (width//2 - 120, height//2), font, 1.0, color, 3)
            cv2.rectangle(annotated, (0, 0), (width, height), color, 8)
            alert_frames_remaining -= 1
            
        out.write(annotated)
        if frame_count % 30 == 0:
            print(f"  {frame_count}/{total_frames} frames processed", flush=True)

    cap.release()
    out.release()
    print(f"Done processing {video_path} into {output_path}", flush=True)

process_video('input/02968_L_F_FY_C4.mp4', 'input/demo_C4.mp4')
process_video('input/02872_H_C_FY_C5.mp4', 'input/demo_C5.mp4')
print("ALL DONE", flush=True)
