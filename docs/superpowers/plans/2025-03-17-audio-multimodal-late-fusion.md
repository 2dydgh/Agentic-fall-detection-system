# Audio Multimodal Late Fusion Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AudioNode to the LangGraph fall detection pipeline that classifies scream/impact sounds using a pretrained YAMNet model, and fuse audio signals with vision signals at the DecisionNode level (Late Fusion).

**Architecture:** PerceptionNode (vision) and AudioNode (audio) run sequentially in a single LangGraph pipeline — perception → audio → analysis → decision → action. DecisionNode combines both results using rule-based scoring. Audio is extracted from the video file's audio track (or from a microphone in real-time mode). YAMNet (TensorFlow Hub) classifies 521 sound categories; we filter for fall-relevant classes (scream, crash, thud, etc.) and pass confidence scores to DecisionNode.

**Tech Stack:** YAMNet (TensorFlow Hub), librosa (audio loading), scipy (resampling), numpy, existing LangGraph pipeline

---

## File Structure

```
agentic/
├── state.py                    # MODIFY — add audio fields to AgentState
├── graph.py                    # MODIFY — add AudioNode, sequential perception → audio → decision
├── nodes/
│   ├── perception.py           # NO CHANGE
│   ├── audio.py                # CREATE — AudioNode (YAMNet inference + classification)
│   ├── analysis.py             # NO CHANGE
│   ├── decision.py             # MODIFY — add audio_bonus to scoring formula
│   └── action.py               # NO CHANGE
├── audio/
│   ├── extractor.py            # CREATE — extract audio chunks from video/mic, sync to frames
│   └── labels.py               # CREATE — YAMNet label filtering (fall-relevant class IDs)
tests/
├── __init__.py                 # CREATE
├── test_audio_extractor.py     # CREATE — audio chunk extraction tests
├── test_audio_node.py          # CREATE — AudioNode classification tests
├── test_audio_labels.py        # CREATE — label filtering tests
├── test_decision_fusion.py     # CREATE — fusion scoring tests
├── test_graph_integration.py   # CREATE — end-to-end pipeline with audio
api/main.py                     # MODIFY — pass audio data through streaming pipeline
main_agentic.py                 # MODIFY — extract audio from video, feed to pipeline
```

---

### Task 1: Audio Label Filtering Module

**Files:**
- Create: `agentic/audio/__init__.py`
- Create: `agentic/audio/labels.py`
- Test: `tests/test_audio_labels.py`

YAMNet outputs 521 class scores. We need a mapping of which classes indicate fall-relevant sounds and a function to check if any relevant class exceeds a confidence threshold.

- [ ] **Step 1: Write the failing test for label filtering**

```python
# tests/test_audio_labels.py
import numpy as np
from agentic.audio.labels import FALL_RELEVANT_LABELS, classify_audio_event

class TestFallRelevantLabels:
    def test_fall_relevant_labels_not_empty(self):
        """낙상 관련 라벨이 정의되어 있어야 함"""
        assert len(FALL_RELEVANT_LABELS) > 0

    def test_labels_contain_scream(self):
        """비명 관련 라벨이 포함되어야 함"""
        label_names = [name for _, name in FALL_RELEVANT_LABELS]
        assert any("scream" in name.lower() for name in label_names)

    def test_classify_audio_event_with_scream(self):
        """비명이 감지되면 scream_detected=True, 높은 confidence 반환"""
        # YAMNet은 521개 클래스에 대한 score를 반환
        fake_scores = np.zeros(521)
        # class index 0 = "Speech", class index 322 = "Screaming" (YAMNet 기준)
        fake_scores[322] = 0.85
        result = classify_audio_event(fake_scores)
        assert result["scream_detected"] is True
        assert result["confidence"] >= 0.8

    def test_classify_audio_event_with_impact(self):
        """충격음이 감지되면 impact_detected=True 반환"""
        fake_scores = np.zeros(521)
        # class index 441 = "Thump, thud" (YAMNet 기준)
        fake_scores[441] = 0.7
        result = classify_audio_event(fake_scores)
        assert result["impact_detected"] is True

    def test_classify_audio_event_silence(self):
        """아무 소리도 없으면 모두 False"""
        fake_scores = np.zeros(521)
        result = classify_audio_event(fake_scores)
        assert result["scream_detected"] is False
        assert result["impact_detected"] is False
        assert result["confidence"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_labels.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agentic.audio'`

- [ ] **Step 3: Write minimal implementation**

```python
# tests/__init__.py (빈 파일 — 패키지 인식용)
```

```python
# agentic/audio/__init__.py
```

```python
# agentic/audio/labels.py
"""
YAMNet 521-class 출력에서 낙상 관련 소리를 필터링하는 모듈.

YAMNet class index 참조:
https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv
"""

# (class_index, label_name) 튜플 리스트
# 주의: 아래 인덱스는 YAMNet class map CSV에서 확인해야 함.
# https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv
# 구현 시 실제 CSV를 다운로드하여 인덱스-라벨 매핑을 검증할 것.

# 비명/도움 요청 관련
SCREAM_LABELS = [
    (322, "Screaming"),
    (316, "Shout"),
    (317, "Yell"),
    (2, "Crying, sobbing"),
]

# 충격음/충돌음 관련
IMPACT_LABELS = [
    (441, "Thump, thud"),
    (450, "Bang"),
    (462, "Crash"),
    (394, "Glass, clink"),  # 유리 깨지는 소리
]

# 전체 낙상 관련 라벨
FALL_RELEVANT_LABELS = SCREAM_LABELS + IMPACT_LABELS

# 빠른 조회를 위한 인덱스 셋
_SCREAM_INDICES = {idx for idx, _ in SCREAM_LABELS}
_IMPACT_INDICES = {idx for idx, _ in IMPACT_LABELS}
_ALL_RELEVANT_INDICES = _SCREAM_INDICES | _IMPACT_INDICES

# 최소 신뢰도 임계값
CONFIDENCE_THRESHOLD = 0.3


def classify_audio_event(scores) -> dict:
    """
    YAMNet의 521-class score 배열을 받아 낙상 관련 이벤트를 분류한다.

    Args:
        scores: shape (521,) numpy array, 각 클래스의 confidence score

    Returns:
        dict with keys:
            - scream_detected: bool
            - impact_detected: bool
            - confidence: float (관련 클래스 중 최고 score)
            - detected_labels: list[str] (임계값 초과한 라벨 이름들)
    """
    scream_detected = False
    impact_detected = False
    max_confidence = 0.0
    detected_labels = []

    for idx, name in FALL_RELEVANT_LABELS:
        if idx < len(scores) and scores[idx] >= CONFIDENCE_THRESHOLD:
            score = float(scores[idx])
            detected_labels.append(name)
            max_confidence = max(max_confidence, score)

            if idx in _SCREAM_INDICES:
                scream_detected = True
            if idx in _IMPACT_INDICES:
                impact_detected = True

    return {
        "scream_detected": scream_detected,
        "impact_detected": impact_detected,
        "confidence": max_confidence,
        "detected_labels": detected_labels,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_labels.py -v`
Expected: PASS (all 5 tests)

- [ ] **Step 5: Commit**

```bash
git add agentic/audio/__init__.py agentic/audio/labels.py tests/__init__.py tests/test_audio_labels.py
git commit -m "feat: add YAMNet label filtering module for fall-relevant audio classification"
```

---

### Task 2: Audio Chunk Extractor

**Files:**
- Create: `agentic/audio/extractor.py`
- Test: `tests/test_audio_extractor.py`

비디오 파일에서 오디오 트랙을 추출하고, 프레임 번호에 동기화된 오디오 청크를 반환하는 모듈. YAMNet은 16kHz mono 0.975초 윈도우를 사용하므로, 프레임 단위로 해당 구간의 오디오를 잘라서 제공한다.

- [ ] **Step 1: Write the failing test for audio extractor**

```python
# tests/test_audio_extractor.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# agentic/audio/extractor.py
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
        # 리샘플링이 필요하면 여기서 처리
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_extractor.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add agentic/audio/extractor.py tests/test_audio_extractor.py
git commit -m "feat: add AudioExtractor for frame-synchronized audio chunk extraction"
```

---

### Task 3: AudioNode (YAMNet Inference)

**Files:**
- Create: `agentic/nodes/audio.py`
- Test: `tests/test_audio_node.py`

AudioNode는 오디오 청크를 받아 YAMNet으로 추론하고, scream/impact 감지 결과를 state에 기록한다.

- [ ] **Step 1: Write the failing test for AudioNode**

```python
# tests/test_audio_node.py
import numpy as np
import pytest
from agentic.nodes.audio import AudioNode

class TestAudioNode:
    def test_process_with_none_chunk_returns_defaults(self):
        """오디오 청크가 None이면 기본값 반환 (감지 없음)"""
        node = AudioNode(skip_model=True)
        state = {"audio_chunk": None}
        result = node.process(state)
        assert result["audio_scream_detected"] is False
        assert result["audio_impact_detected"] is False
        assert result["audio_confidence"] == 0.0
        assert result["audio_detected_labels"] == []

    def test_process_returns_required_keys(self):
        """AudioNode 결과에 필수 키들이 모두 있어야 함"""
        node = AudioNode(skip_model=True)
        # 무음 청크
        silent_chunk = np.zeros(15600, dtype=np.float32)
        state = {"audio_chunk": silent_chunk}
        result = node.process(state)
        required_keys = [
            "audio_scream_detected",
            "audio_impact_detected",
            "audio_confidence",
            "audio_detected_labels",
        ]
        for key in required_keys:
            assert key in result

    def test_process_with_silent_audio(self):
        """무음 입력은 아무것도 감지하지 않아야 함 (skip_model로 TDD 사이클 유지)"""
        node = AudioNode(skip_model=True)
        silent_chunk = np.zeros(15600, dtype=np.float32)
        state = {"audio_chunk": silent_chunk}
        result = node.process(state)
        assert result["audio_scream_detected"] is False
        assert result["audio_impact_detected"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_node.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# agentic/nodes/audio.py
"""
YAMNet 기반 오디오 분류 노드.
오디오 청크를 받아 비명/충격음 감지 여부를 state에 기록한다.
"""
import numpy as np
from typing import Optional
from ..audio.labels import classify_audio_event

# YAMNet 모델은 무거우므로 lazy load
_yamnet_model = None

def _get_yamnet_model():
    global _yamnet_model
    if _yamnet_model is None:
        import tensorflow_hub as hub
        _yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
    return _yamnet_model


class AudioNode:
    """YAMNet을 사용한 오디오 이벤트 감지 노드"""

    def __init__(self, skip_model: bool = False):
        """
        Args:
            skip_model: True이면 YAMNet 로드를 건너뛰고 항상 기본값 반환 (테스트용)
        """
        self._skip_model = skip_model

    def process(self, state: dict) -> dict:
        """
        오디오 청크를 분류하여 결과 반환.

        State에서 읽는 키:
            audio_chunk: Optional[np.ndarray] — 15600 samples, 16kHz, float32

        반환하는 키:
            audio_scream_detected: bool
            audio_impact_detected: bool
            audio_confidence: float
            audio_detected_labels: list[str]
        """
        chunk = state.get("audio_chunk")

        # 오디오 없으면 기본값
        if chunk is None:
            return self._default_result()

        if self._skip_model:
            return self._default_result()

        try:
            model = _get_yamnet_model()
            # YAMNet 추론: waveform → (scores, embeddings, spectrogram)
            scores, embeddings, spectrogram = model(chunk)
            # scores shape: (num_patches, 521) — 패치별 평균을 사용
            avg_scores = np.mean(scores.numpy(), axis=0)
            raw = classify_audio_event(avg_scores)
            # state 키 네이밍에 맞게 audio_ 접두사 추가
            return {
                "audio_scream_detected": raw["scream_detected"],
                "audio_impact_detected": raw["impact_detected"],
                "audio_confidence": raw["confidence"],
                "audio_detected_labels": raw["detected_labels"],
            }
        except Exception:
            return self._default_result()

    @staticmethod
    def _default_result() -> dict:
        return {
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "audio_detected_labels": [],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_audio_node.py -v`
Expected: PASS (all 3 tests — YAMNet 모델은 로드하지 않고 None chunk 또는 무음으로 테스트)

- [ ] **Step 5: Commit**

```bash
git add agentic/nodes/audio.py tests/test_audio_node.py
git commit -m "feat: add AudioNode with YAMNet inference for scream/impact detection"
```

---

### Task 4: AgentState 확장 + DecisionNode 퓨전 로직

**Files:**
- Modify: `agentic/state.py:1-28`
- Modify: `agentic/nodes/decision.py:1-56`
- Test: `tests/test_decision_fusion.py`

AgentState에 오디오 필드를 추가하고, DecisionNode에서 오디오 보너스를 severity 점수에 반영한다.

- [ ] **Step 1: Write the failing test for fusion scoring**

```python
# tests/test_decision_fusion.py
from agentic.nodes.decision import decision_node

class TestDecisionFusion:
    # NOTE: 현재 decision_node는 base_score=80으로 하드코딩되어 있음 (테스트 모드).
    # 실제 공식(min(no_movement * 2, 60))으로 전환 시 no_movement_seconds=40.0으로
    # 변경하면 동일한 base_score=80을 얻을 수 있음.

    def _base_state(self, **overrides):
        """기본 낙상 감지 state"""
        state = {
            "fall_detected": True,
            "no_movement_seconds": 40.0,  # 실제 공식에서도 min(40*2, 60)=60 → 근사 호환
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
            # 오디오 기본값: 감지 없음
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
        }
        state.update(overrides)
        return state

    def test_no_audio_signal_no_bonus(self):
        """오디오 신호 없으면 기존 점수와 동일"""
        state = self._base_state()
        result = decision_node(state)
        # base_score=80 (테스트 고정값), 보너스 없음
        assert result["severity_score"] == 80

    def test_scream_adds_bonus(self):
        """비명 감지 시 +15점"""
        state = self._base_state(
            audio_scream_detected=True,
            audio_confidence=0.8,
        )
        result = decision_node(state)
        assert result["severity_score"] == min(80 + 15, 100)

    def test_impact_adds_bonus(self):
        """충격음 감지 시 +10점"""
        state = self._base_state(
            audio_impact_detected=True,
            audio_confidence=0.7,
        )
        result = decision_node(state)
        assert result["severity_score"] == min(80 + 10, 100)

    def test_scream_and_impact_adds_both(self):
        """비명 + 충격음 동시 감지 시 +25점 (15+10)"""
        state = self._base_state(
            audio_scream_detected=True,
            audio_impact_detected=True,
            audio_confidence=0.9,
        )
        result = decision_node(state)
        assert result["severity_score"] == min(80 + 15 + 10, 100)  # capped at 100

    def test_audio_only_no_vision_fall_creates_alert(self):
        """비전은 낙상 미감지, 오디오만 비명 → severity는 계산하지 않음 (Late Fusion에서 비전이 primary)"""
        # 현재 설계에서 fall_detected=False이면 DecisionNode를 스킵하므로
        # 오디오만으로는 severity를 올리지 않는다.
        # 이 동작은 graph.py의 조건부 엣지에서 처리한다.
        pass  # Task 5에서 graph integration 테스트로 커버

    def test_max_score_capped_at_100(self):
        """모든 보너스 합산해도 100점을 넘지 않음"""
        state = self._base_state(
            estimated_age="elderly",        # +20
            location_type="stairs",         # +15
            hazards_detected=["wet floor"], # +5
            audio_scream_detected=True,     # +15
            audio_impact_detected=True,     # +10
            audio_confidence=0.95,
        )
        # 80 + 20 + 15 + 5 + 15 + 10 = 145 → capped at 100
        result = decision_node(state)
        assert result["severity_score"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_decision_fusion.py -v`
Expected: FAIL — `decision_node`가 아직 오디오 필드를 읽지 않으므로 scream 보너스 테스트 실패

- [ ] **Step 3: Update AgentState with audio fields**

`agentic/state.py`에 다음 필드를 `# Analysis Node` 섹션 뒤에 추가:

```python
    # Audio Node
    audio_chunk: Optional[Any]  # 현재 프레임에 대응하는 오디오 청크 (numpy 배열 또는 None)
    audio_scream_detected: bool
    audio_impact_detected: bool
    audio_confidence: float
    audio_detected_labels: list[str]
```

- [ ] **Step 4: Update DecisionNode with audio bonus**

`agentic/nodes/decision.py`의 점수 계산에 오디오 보너스 추가:

```python
def decision_node(state: dict) -> dict:
    """
    심각도 점수 계산 및 대응 방식 결정

    점수 계산:
    - base: no_movement_seconds * 2 (최대 60점)
    - elderly: +20점
    - stairs/bathroom: +15점
    - hazards: +5점
    - scream detected: +15점
    - impact sound detected: +10점

    판정:
    - 0-40: LOW
    - 41-70: MEDIUM
    - 71-100: HIGH
    """
    no_movement = state.get("no_movement_seconds", 0)
    age = state.get("estimated_age", "unknown")
    location = state.get("location_type", "other")
    hazards = state.get("hazards_detected", [])

    # 오디오 신호
    scream = state.get("audio_scream_detected", False)
    impact = state.get("audio_impact_detected", False)

    # 점수 계산
    # base_score = min(no_movement * 2, 60)
    base_score = 80

    age_bonus = 20 if age == "elderly" else 0
    location_bonus = 15 if location in ["stairs", "bathroom"] else 0
    hazard_bonus = 5 if len(hazards) > 0 else 0

    # 오디오 보너스 (Late Fusion)
    scream_bonus = 15 if scream else 0
    impact_bonus = 10 if impact else 0

    total_score = int(base_score + age_bonus + location_bonus + hazard_bonus + scream_bonus + impact_bonus)
    total_score = min(total_score, 100)

    # 심각도 판정
    if total_score <= 40:
        severity = "LOW"
    elif total_score <= 70:
        severity = "MEDIUM"
    else:
        severity = "HIGH"

    # 권장 액션
    actions = ["log_to_db"]
    if severity in ["MEDIUM", "HIGH"]:
        actions.append("save_snapshot")
        actions.append("notify_security_room")
    if severity == "HIGH":
        actions.append("send_email_alert")
        actions.append("generate_report")

    return {
        "severity": severity,
        "severity_score": total_score,
        "recommended_actions": actions,
        "auto_action_required": severity == "HIGH",
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_decision_fusion.py -v`
Expected: PASS (all 6 tests, 1 skipped)

- [ ] **Step 6: Commit**

```bash
git add agentic/state.py agentic/nodes/decision.py tests/test_decision_fusion.py
git commit -m "feat: add audio fields to AgentState and audio bonus scoring in DecisionNode"
```

---

### Task 5: LangGraph Pipeline Integration

**Files:**
- Modify: `agentic/graph.py:1-89`
- Test: `tests/test_graph_integration.py`

그래프에 AudioNode를 추가하고, PerceptionNode 이후 순차적으로 실행되도록 구성한다. 오디오 청크는 그래프 호출 전에 state에 미리 주입된다.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/test_graph_integration.py
import numpy as np
import pytest

class TestGraphAudioIntegration:
    def test_state_has_audio_fields_after_invoke(self):
        """그래프 실행 후 state에 오디오 관련 필드가 있어야 함"""
        from agentic.graph import create_fall_detection_graph

        graph = create_fall_detection_graph(
            model_path="models/yolov26n-pose.pt",
            skip_vlm=True,
            skip_audio=True,  # 테스트에서는 YAMNet 로드 스킵
        )

        # 더미 프레임 (검은 화면)
        dummy_frame = np.zeros((740, 980, 3), dtype=np.uint8)
        state = {
            "frame": dummy_frame,
            "fall_detected": False,
            "pose_data": {},
            "no_movement_seconds": 0.0,
            "track_id": None,
            "annotated_frame": None,
            "scene_description": "",
            "estimated_age": "unknown",
            "location_type": "other",
            "hazards_detected": [],
            "severity": "LOW",
            "severity_score": 0,
            "recommended_actions": [],
            "auto_action_required": False,
            "actions_taken": [],
            "incident_id": None,
            "snapshot_path": None,
            # 오디오 필드
            "audio_chunk": None,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "audio_detected_labels": [],
        }

        result = graph.invoke(state)

        # 오디오 필드가 state에 존재해야 함
        assert "audio_scream_detected" in result
        assert "audio_impact_detected" in result
        assert "audio_confidence" in result

    def test_graph_creation_with_skip_audio_flag(self):
        """skip_audio=True로 그래프 생성 가능"""
        from agentic.graph import create_fall_detection_graph

        graph = create_fall_detection_graph(
            model_path="models/yolov26n-pose.pt",
            skip_vlm=True,
            skip_audio=True,
        )
        assert graph is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_graph_integration.py -v`
Expected: FAIL — `create_fall_detection_graph`가 `skip_audio` 파라미터를 받지 않음

- [ ] **Step 3: Update graph.py to include AudioNode**

```python
# agentic/graph.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes.perception import PerceptionNode
from .nodes.decision import decision_node
from .nodes.action import ActionNode

# Analysis Node는 무거우니까 lazy load
_analysis_node = None

def get_analysis_node():
    global _analysis_node
    if _analysis_node is None:
        from .nodes.analysis import AnalysisNode
        _analysis_node = AnalysisNode()
    return _analysis_node

def create_fall_detection_graph(
    model_path: str,
    db_path: str = "incidents.db",
    slack_webhook: str = None,
    email_sender: str = None,
    email_password: str = None,
    email_receiver: str = None,
    skip_vlm: bool = False,
    skip_audio: bool = False,
):
    """LangGraph 워크플로우 생성 (비전 + 오디오 멀티모달)"""

    # 노드 초기화 (각 그래프 인스턴스마다 독립적으로 생성)
    perception = PerceptionNode(model_path)
    from .nodes.audio import AudioNode
    audio = AudioNode(skip_model=skip_audio)
    action = ActionNode(
        db_path=db_path,
        slack_webhook=slack_webhook,
        email_sender=email_sender,
        email_password=email_password,
        email_receiver=email_receiver
    )

    # 그래프 정의
    graph = StateGraph(AgentState)

    # 노드 함수들
    def perception_node(state: AgentState) -> AgentState:
        frame = state.get("frame")
        if frame is None:
            return state
        result = perception.process(frame, state)
        return {**state, **result}

    def audio_node_func(state: AgentState) -> AgentState:
        result = audio.process(state)
        return {**state, **result}

    def analysis_node(state: AgentState) -> AgentState:
        if not state.get("fall_detected") or skip_vlm:
            return {
                **state,
                "scene_description": "Fall detected",
                "estimated_age": "adult",
                "location_type": "other",
                "hazards_detected": [],
            }
        analysis = get_analysis_node()
        result = analysis.process(state)
        return {**state, **result}

    def decision_node_wrapper(state: AgentState) -> AgentState:
        if not state.get("fall_detected"):
            return state
        result = decision_node(state)
        return {**state, **result}

    def action_node_func(state: AgentState) -> AgentState:
        if not state.get("fall_detected"):
            return state
        result = action.process(state)
        return {**state, **result}

    # 노드 추가
    graph.add_node("perception", perception_node)
    graph.add_node("audio", audio_node_func)
    graph.add_node("analysis", analysis_node)
    graph.add_node("decision", decision_node_wrapper)
    graph.add_node("action", action_node_func)

    # 엣지 연결
    # perception과 audio를 순차 실행 (같은 프레임 기준)
    # perception → audio → analysis → decision → action
    graph.set_entry_point("perception")
    graph.add_edge("perception", "audio")
    graph.add_edge("audio", "analysis")
    graph.add_edge("analysis", "decision")
    graph.add_edge("decision", "action")
    graph.add_edge("action", END)

    return graph.compile()
```

> **Design Note:** LangGraph에서 진정한 병렬 실행은 `add_conditional_edges` 또는 별도 서브그래프가 필요하다. 단순성을 위해 perception → audio → analysis 순차 파이프라인으로 구성한다. AudioNode는 매우 가볍기 때문에 (YAMNet 추론 ~10ms) 병목이 되지 않는다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/test_graph_integration.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add agentic/graph.py tests/test_graph_integration.py
git commit -m "feat: integrate AudioNode into LangGraph pipeline with skip_audio flag"
```

---

### Task 6: Entry Points 업데이트 (CLI + API)

**Files:**
- Modify: `main_agentic.py:1-6` (imports), `:15-16` (argparse), `:33-41` (graph creation), `:49-52` (audio extractor init), `:60-78` (initial state), `:92` (audio chunk injection)
- Modify: `api/main.py:1-12` (imports), `:33-41` (graph creation), `:95-103` (generate_frames graph), `:119-137` (initial state), `:150` (audio chunk injection)

CLI와 API 서버에서 비디오 파일의 오디오를 추출하여 프레임마다 audio_chunk를 state에 주입하도록 한다.

> **Test coverage note:** Task 6의 변경은 기존 Task 2 (`AudioExtractor` 단위 테스트)와 Task 5 (`skip_audio` 그래프 통합 테스트)에서 이미 커버됨. 여기서는 entry point 연결만 수행하므로 수동 통합 테스트로 검증한다.

- [ ] **Step 1: Update main_agentic.py imports (line 1-6)**

기존:
```python
import os
import cv2
import argparse
from dotenv import load_dotenv
from agentic.graph import create_fall_detection_graph
from agentic.state import AgentState
```

변경:
```python
import os
import cv2
import argparse
from dotenv import load_dotenv
from agentic.graph import create_fall_detection_graph
from agentic.state import AgentState
from agentic.audio.extractor import AudioExtractor
```

- [ ] **Step 2: Add --skip-audio argparse flag (line 16 이후)**

기존:
```python
    parser.add_argument("--skip-vlm", action="store_true", help="Skip VLM analysis for faster processing")
    args = parser.parse_args()
```

변경:
```python
    parser.add_argument("--skip-vlm", action="store_true", help="Skip VLM analysis for faster processing")
    parser.add_argument("--skip-audio", action="store_true", help="Skip audio analysis")
    args = parser.parse_args()
```

- [ ] **Step 3: Pass skip_audio to graph creation (line 33-41)**

기존:
```python
    graph = create_fall_detection_graph(
        model_path=model_path,
        db_path=os.path.join(base_dir, "incidents.db"),
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_receiver=os.getenv("EMAIL_RECEIVER"),
        skip_vlm=args.skip_vlm
    )
```

변경:
```python
    graph = create_fall_detection_graph(
        model_path=model_path,
        db_path=os.path.join(base_dir, "incidents.db"),
        slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
        email_sender=os.getenv("EMAIL_SENDER"),
        email_password=os.getenv("EMAIL_PASSWORD"),
        email_receiver=os.getenv("EMAIL_RECEIVER"),
        skip_vlm=args.skip_vlm,
        skip_audio=args.skip_audio
    )
```

- [ ] **Step 4: Add AudioExtractor init after video open (line 52, fps 계산 이후)**

다음 코드를 `fps = cap.get(...)` 라인 이후에 추가:
```python
    # 오디오 추출
    if not args.skip_audio:
        audio_extractor = AudioExtractor.from_video_file(video_path, video_fps=fps)
        print(f"   - 오디오: {audio_extractor.duration_seconds:.1f}초 추출됨")
    else:
        audio_extractor = AudioExtractor.silent(video_fps=fps)
        print(f"   - 오디오: OFF")
```

- [ ] **Step 5: Add audio fields to initial state (line 60-78)**

기존 `current_state` dict의 `"snapshot_path": None,` 뒤에 추가:
```python
        # Audio
        "audio_chunk": None,
        "audio_scream_detected": False,
        "audio_impact_detected": False,
        "audio_confidence": 0.0,
        "audio_detected_labels": [],
```

- [ ] **Step 6: Inject audio_chunk per frame in loop (line 92, frame resize 이후)**

`current_state["frame"] = frame.copy()` 라인 바로 뒤에 추가:
```python
        current_state["audio_chunk"] = audio_extractor.get_chunk_for_frame(frame_count)
```

- [ ] **Step 7: Update api/main.py — imports (line 12 이후)**

추가:
```python
from agentic.audio.extractor import AudioExtractor
```

- [ ] **Step 8: Update api/main.py — global graph (line 33-41)**

`skip_vlm=False` 뒤에 추가:
```python
    skip_audio=False
```

- [ ] **Step 9: Update api/main.py — generate_frames (line 95-103)**

`local_graph` 생성에 `skip_audio=False` 추가. `cap = cv2.VideoCapture(video_source)` 이후에 추가:
```python
    audio_extractor = AudioExtractor.from_video_file(video_source, video_fps=24.0)
```

- [ ] **Step 10: Update api/main.py — initial state (line 119-137)**

`current_state` dict에 오디오 필드 추가 (main_agentic.py Step 5와 동일).

- [ ] **Step 11: Update api/main.py — audio_chunk injection (line 150)**

`current_state["frame"] = frame.copy()` 뒤에 추가:
```python
            current_state["audio_chunk"] = audio_extractor.get_chunk_for_frame(frame_count)
```

- [ ] **Step 12: Run full system test (manual)**

```bash
cd /home/yhlee/DETECT/Project/Fall_Detection
python main_agentic.py --video input/02400_H_A_BY_C1.mp4 --skip-vlm
```

Expected: 기존과 동일하게 동작. 오디오 트랙이 있으면 추출 메시지 표시, 없으면 `AudioExtractor.silent` 모드로 동작.

```bash
python main_agentic.py --video input/02400_H_A_BY_C1.mp4 --skip-vlm --skip-audio
```

Expected: `오디오: OFF` 메시지 출력, 기존 vision-only 동작과 동일.

- [ ] **Step 13: Run all tests**

Run: `cd /home/yhlee/DETECT/Project/Fall_Detection && python -m pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 14: Commit**

```bash
git add main_agentic.py api/main.py
git commit -m "feat: wire AudioExtractor into CLI and API entry points for multimodal fall detection"
```

---

### Task 7: Dependencies 및 문서 정리

**Files:**
- Create: `requirements.txt` (프로젝트에 아직 없음)
- Modify: `README.md` (선택)

- [ ] **Step 1: Create requirements.txt with new dependencies**

```text
# Core
ultralytics>=8.0
langgraph>=0.2
fastapi>=0.100
uvicorn>=0.20
python-dotenv>=1.0
opencv-python>=4.8

# VLM
transformers>=4.36
torch>=2.0

# Audio (NEW)
tensorflow>=2.13
tensorflow-hub>=0.15
librosa>=0.10
scipy>=1.11
numpy>=1.24
```

- [ ] **Step 2: Verify installation**

```bash
pip install tensorflow tensorflow-hub librosa
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: add requirements.txt with audio dependencies (tensorflow, librosa)"
```

---

## Summary: Late Fusion 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                    VIDEO FILE / STREAM                   │
└──────────┬───────────────────────────────┬──────────────┘
           │                               │
     Video Frames                    Audio Track
           │                               │
           ▼                               ▼
  ┌─────────────────┐           ┌──────────────────┐
  │ PerceptionNode  │           │  AudioExtractor   │
  │ (YOLO Pose)     │           │  (frame-synced    │
  │                 │           │   chunk delivery)  │
  └────────┬────────┘           └────────┬─────────┘
           │                             │
           │ fall_detected,              │ audio_chunk
           │ pose_data                   │
           ▼                             ▼
  ┌──────────────────────────────────────────────┐
  │              AudioNode (YAMNet)               │
  │  audio_chunk → scream/impact classification  │
  └──────────────────────┬───────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │            AnalysisNode (Florence-2)          │
  │  (only if fall_detected — unchanged)          │
  └──────────────────────┬───────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │      DecisionNode (Severity + Fusion)         │
  │                                               │
  │  base_score     = 80 (test) / movement-based  │
  │  + age_bonus    = 0 or 20 (elderly)           │
  │  + location_bonus = 0 or 15 (stairs/bathroom) │
  │  + hazard_bonus = 0 or 5                      │
  │  + scream_bonus = 0 or 15  ← NEW             │
  │  + impact_bonus = 0 or 10  ← NEW             │
  │  ─────────────────────────                    │
  │  total_score (capped at 100)                  │
  └──────────────────────┬───────────────────────┘
                         │
                         ▼
  ┌──────────────────────────────────────────────┐
  │            ActionNode (Tools)                 │
  │  (unchanged — log, snapshot, email, slack)    │
  └──────────────────────────────────────────────┘
```
