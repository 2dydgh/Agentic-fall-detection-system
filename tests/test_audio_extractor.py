import numpy as np
import pytest
from agentic.audio.extractor import AudioExtractor

class TestAudioExtractor:
    def test_init_with_silent_audio(self):
        """무음 오디오 배열로 초기화"""
        # 16kHz, 5초 분량의 무음
        silent_audio = np.zeros(16000 * 5, dtype=np.float32)
        extractor = AudioExtractor.from_waveform(silent_audio, sample_rate=16000, video_fps=20.0)
        assert extractor.duration_seconds == pytest.approx(5.0, abs=0.1)

    def test_get_chunk_for_frame(self):
        """특정 프레임에 해당하는 오디오 청크 반환"""
        # 1초짜리 사인파 (440Hz)
        sr = 16000
        t = np.linspace(0, 1.0, sr, dtype=np.float32)
        audio = np.sin(2 * np.pi * 440 * t)
        extractor = AudioExtractor.from_waveform(audio, sample_rate=sr, video_fps=20.0)

        chunk = extractor.get_chunk_for_frame(frame_number=0)
        # YAMNet 윈도우: 0.975초 = 15600 samples at 16kHz
        assert chunk is not None
        assert len(chunk) == 15600

    def test_get_chunk_beyond_duration_returns_none(self):
        """비디오 길이를 초과하는 프레임은 None 반환"""
        audio = np.zeros(16000, dtype=np.float32)  # 1초
        extractor = AudioExtractor.from_waveform(audio, sample_rate=16000, video_fps=20.0)
        # 프레임 1000 = 50초 시점 → 1초 오디오 범위 밖
        chunk = extractor.get_chunk_for_frame(frame_number=1000)
        assert chunk is None

    def test_from_video_file_no_audio_returns_none_chunks(self):
        """오디오 트랙 없는 비디오는 항상 None 반환하는 extractor 생성"""
        extractor = AudioExtractor.silent(video_fps=20.0)
        chunk = extractor.get_chunk_for_frame(frame_number=0)
        assert chunk is None
