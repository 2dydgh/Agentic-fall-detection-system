"""
비디오/오디오 소스에서 프레임 동기화된 오디오 청크를 추출하는 모듈.
YAMNet은 16kHz mono, 0.975초(15600 samples) 윈도우를 사용한다.
"""
import numpy as np
from typing import Optional

YAMNET_SAMPLE_RATE = 16000
YAMNET_WINDOW_SAMPLES = 15600  # 0.975초 * 16000Hz


class AudioExtractor:
    """프레임 번호에 동기화된 오디오 청크 제공"""

    def __init__(self, waveform: Optional[np.ndarray], sample_rate: int, video_fps: float):
        """
        Args:
            waveform: 16kHz mono float32 배열, None이면 무음 모드
            sample_rate: 오디오 샘플레이트 (리샘플링 후 16kHz여야 함)
            video_fps: 비디오 프레임레이트
        """
        self._waveform = waveform
        self._sample_rate = sample_rate
        self._video_fps = video_fps

    @classmethod
    def from_waveform(cls, waveform: np.ndarray, sample_rate: int, video_fps: float) -> "AudioExtractor":
        """이미 로드된 waveform으로 초기화"""
        if sample_rate != YAMNET_SAMPLE_RATE:
            from scipy.signal import resample
            num_samples = int(len(waveform) * YAMNET_SAMPLE_RATE / sample_rate)
            waveform = resample(waveform, num_samples).astype(np.float32)
        return cls(waveform=waveform, sample_rate=YAMNET_SAMPLE_RATE, video_fps=video_fps)

    @classmethod
    def from_video_file(cls, video_path: str, video_fps: float) -> "AudioExtractor":
        """비디오 파일에서 오디오 트랙 추출. 오디오가 없으면 silent 모드."""
        try:
            import librosa
            waveform, sr = librosa.load(video_path, sr=YAMNET_SAMPLE_RATE, mono=True)
            return cls(waveform=waveform.astype(np.float32), sample_rate=YAMNET_SAMPLE_RATE, video_fps=video_fps)
        except Exception:
            return cls.silent(video_fps=video_fps)

    @classmethod
    def silent(cls, video_fps: float) -> "AudioExtractor":
        """오디오 없는 모드 — 모든 청크가 None"""
        return cls(waveform=None, sample_rate=YAMNET_SAMPLE_RATE, video_fps=video_fps)

    @property
    def duration_seconds(self) -> float:
        if self._waveform is None:
            return 0.0
        return len(self._waveform) / self._sample_rate

    def get_chunk_for_frame(self, frame_number: int) -> Optional[np.ndarray]:
        """
        프레임 번호에 대응하는 오디오 청크 반환.

        프레임의 중심 타임스탬프를 기준으로 ±0.4875초 윈도우를 잡는다.
        범위를 벗어나면 None 반환.
        """
        if self._waveform is None:
            return None

        # 프레임의 중심 시각 (초)
        center_time = frame_number / self._video_fps
        half_window = YAMNET_WINDOW_SAMPLES / (2 * self._sample_rate)

        start_time = center_time - half_window
        end_time = center_time + half_window

        start_sample = int(start_time * self._sample_rate)
        end_sample = start_sample + YAMNET_WINDOW_SAMPLES

        # 범위 체크
        if start_sample < 0:
            start_sample = 0
            end_sample = YAMNET_WINDOW_SAMPLES

        if end_sample > len(self._waveform):
            return None

        return self._waveform[start_sample:end_sample]
