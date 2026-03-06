import os
import cv2
import numpy as np

def save_snapshot(
    frame: np.ndarray,
    incident_id: str,
    output_dir: str = "snapshots"
) -> str:
    """낙상 순간 이미지 저장"""
    os.makedirs(output_dir, exist_ok=True)

    filename = f"{incident_id}.jpg"
    filepath = os.path.join(output_dir, filename)

    cv2.imwrite(filepath, frame)

    return filepath
