import numpy as np
from agentic.audio.labels import FALL_RELEVANT_LABELS, classify_audio_event

class TestFallRelevantLabels:
    def test_fall_relevant_labels_not_empty(self):
        assert len(FALL_RELEVANT_LABELS) > 0

    def test_labels_contain_scream(self):
        label_names = [name for _, name in FALL_RELEVANT_LABELS]
        assert any("scream" in name.lower() for name in label_names)

    def test_classify_audio_event_with_scream(self):
        fake_scores = np.zeros(521)
        fake_scores[322] = 0.85
        result = classify_audio_event(fake_scores)
        assert result["scream_detected"] is True
        assert result["confidence"] >= 0.8

    def test_classify_audio_event_with_impact(self):
        fake_scores = np.zeros(521)
        fake_scores[441] = 0.7
        result = classify_audio_event(fake_scores)
        assert result["impact_detected"] is True

    def test_classify_audio_event_silence(self):
        fake_scores = np.zeros(521)
        result = classify_audio_event(fake_scores)
        assert result["scream_detected"] is False
        assert result["impact_detected"] is False
        assert result["confidence"] == 0.0
