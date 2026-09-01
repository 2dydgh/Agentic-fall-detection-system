"""Attention-based Multimodal Fusion 테스트"""

import numpy as np
import torch
import pytest

from agentic.fusion.feature import (
    extract_features, _pose_features, _audio_features, _vlm_features, FEATURE_DIM,
)
from agentic.fusion.model import AttentionFusionModel, SEVERITY_CLASSES
from agentic.fusion.dataset import generate_dataset, FusionDataset


# ── Feature Extraction 테스트 ──

class TestFeatureExtraction:
    def _base_state(self, **overrides):
        state = {
            "pose_data": {"angle": 60, "velocity": 20},
            "no_movement_seconds": 3.0,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
        }
        state.update(overrides)
        return state

    def test_extract_features_shape(self):
        """extract_features 출력은 (3, 6) 텐서"""
        feat = extract_features(self._base_state())
        assert feat.shape == (3, FEATURE_DIM)
        assert feat.dtype == torch.float32

    def test_pose_features_angle_normalized(self):
        """각도 90도 → 정규화 값 1.0"""
        feat = _pose_features({"pose_data": {"angle": 90, "velocity": 0}, "no_movement_seconds": 0})
        assert feat[0] == pytest.approx(1.0)

    def test_pose_features_velocity_capped(self):
        """속도 정규화는 1.0을 초과하지 않음"""
        feat = _pose_features({"pose_data": {"angle": 0, "velocity": 100}, "no_movement_seconds": 0})
        assert feat[1] == pytest.approx(1.0)

    def test_audio_features_scream_detection(self):
        """비명 감지 시 첫 번째 feature가 1.0"""
        feat = _audio_features({"audio_scream_detected": True, "audio_impact_detected": False, "audio_confidence": 0.8})
        assert feat[0] == 1.0
        assert feat[1] == 0.0

    def test_audio_features_both_detection(self):
        """비명+충격음 동시 감지 시 synergy feature가 1.0"""
        feat = _audio_features({"audio_scream_detected": True, "audio_impact_detected": True, "audio_confidence": 0.9})
        assert feat[3] == 1.0  # scream * impact

    def test_vlm_features_elderly_stairs(self):
        """고령자 + 계단 → 해당 feature 1.0"""
        feat = _vlm_features({"estimated_age": "elderly", "location_type": "stairs", "hazards_detected": []})
        assert feat[0] == 1.0  # elderly
        assert feat[1] == 1.0  # stairs
        assert feat[5] == 1.0  # dangerous_location

    def test_vlm_features_default_state(self):
        """기본 state → 모든 VLM feature 0.0"""
        feat = _vlm_features({"estimated_age": "adult", "location_type": "other", "hazards_detected": []})
        assert np.all(feat == 0.0)

    def test_features_all_values_in_range(self):
        """모든 feature 값이 0~1 범위"""
        state = self._base_state(
            audio_scream_detected=True, audio_impact_detected=True,
            audio_confidence=0.9, estimated_age="elderly",
            location_type="stairs", hazards_detected=["wet_floor", "clutter"],
            pose_data={"angle": 80, "velocity": 25},
            no_movement_seconds=8.0,
        )
        feat = extract_features(state)
        assert feat.min() >= 0.0
        assert feat.max() <= 1.0


# ── Model 테스트 ──

class TestAttentionFusionModel:
    @pytest.fixture
    def model(self):
        return AttentionFusionModel(d_model=64, num_heads=4, dropout=0.0)

    def test_forward_output_shapes(self, model):
        """forward 출력 shape 검증"""
        x = torch.randn(4, 3, FEATURE_DIM)
        out = model(x, return_attention=True)

        assert out["score"].shape == (4,)
        assert out["logits"].shape == (4, 3)
        assert out["attn_weights"].shape == (4, 3, 3)

    def test_forward_score_range(self, model):
        """score 출력은 0~100 범위 (sigmoid * 100)"""
        x = torch.randn(10, 3, FEATURE_DIM)
        out = model(x)
        assert out["score"].min() >= 0.0
        assert out["score"].max() <= 100.0

    def test_forward_without_attention(self, model):
        """return_attention=False일 때 attn_weights 없음"""
        x = torch.randn(2, 3, FEATURE_DIM)
        out = model(x, return_attention=False)
        assert "attn_weights" not in out

    def test_attention_weights_sum_to_one(self, model):
        """각 row의 attention weight 합이 1.0"""
        x = torch.randn(4, 3, FEATURE_DIM)
        out = model(x, return_attention=True)
        row_sums = out["attn_weights"].sum(dim=-1)
        assert torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-5)

    def test_predict_single_sample(self, model):
        """predict는 단일 샘플에서 severity, score, attn_weights 반환"""
        x = torch.randn(3, FEATURE_DIM)
        result = model.predict(x)

        assert result["severity"] in SEVERITY_CLASSES
        assert 0 <= result["severity_score"] <= 100
        assert result["attn_weights"].shape == (3, 3)

    def test_predict_batch_input(self, model):
        """predict에 batch 입력도 동작"""
        x = torch.randn(1, 3, FEATURE_DIM)
        result = model.predict(x)
        assert result["severity"] in SEVERITY_CLASSES

    def test_model_deterministic_in_eval(self, model):
        """eval 모드에서 동일 입력 → 동일 출력"""
        model.eval()
        x = torch.randn(2, 3, FEATURE_DIM)
        with torch.no_grad():
            out1 = model(x)
            out2 = model(x)
        assert torch.allclose(out1["score"], out2["score"])
        assert torch.allclose(out1["logits"], out2["logits"])


# ── Dataset 테스트 ──

class TestFusionDataset:
    def test_generate_dataset_shapes(self):
        """생성된 데이터셋 shape 검증"""
        features, scores, classes = generate_dataset(n_samples=100, seed=42)
        assert features.shape == (100, 3, FEATURE_DIM)
        assert scores.shape == (100,)
        assert classes.shape == (100,)

    def test_generate_dataset_score_range(self):
        """severity score는 0~100 범위"""
        _, scores, _ = generate_dataset(n_samples=500, seed=42)
        assert scores.min() >= 0.0
        assert scores.max() <= 100.0

    def test_generate_dataset_class_values(self):
        """severity class는 0, 1, 2 중 하나"""
        _, _, classes = generate_dataset(n_samples=500, seed=42)
        assert set(classes.unique().tolist()).issubset({0, 1, 2})

    def test_generate_dataset_all_classes_present(self):
        """충분한 샘플에서 3개 클래스 모두 존재"""
        _, _, classes = generate_dataset(n_samples=1000, seed=42)
        assert len(classes.unique()) == 3

    def test_generate_dataset_reproducible(self):
        """동일 seed → 동일 데이터"""
        f1, s1, c1 = generate_dataset(n_samples=50, seed=123)
        f2, s2, c2 = generate_dataset(n_samples=50, seed=123)
        assert torch.equal(f1, f2)
        assert torch.equal(s1, s2)
        assert torch.equal(c1, c2)

    def test_fusion_dataset_len_and_getitem(self):
        """FusionDataset의 __len__과 __getitem__ 동작"""
        features, scores, classes = generate_dataset(n_samples=50, seed=42)
        ds = FusionDataset(features, scores, classes)
        assert len(ds) == 50

        feat, score, cls = ds[0]
        assert feat.shape == (3, FEATURE_DIM)
        assert score.dim() == 0  # scalar
        assert cls.dim() == 0


# ── Decision Node 통합 테스트 ──

class TestDecisionNodeIntegration:
    def test_decision_node_attention_with_trained_model(self):
        """학습된 모델이 있으면 attention-based decision 사용"""
        import os
        model_path = os.path.join(os.path.dirname(__file__), "../models/fusion_model.pt")
        if not os.path.exists(model_path):
            pytest.skip("fusion_model.pt not found")

        from agentic.nodes.decision import decision_node_attention
        state = {
            "pose_data": {"angle": 70, "velocity": 25},
            "no_movement_seconds": 5.0,
            "audio_scream_detected": True,
            "audio_impact_detected": True,
            "audio_confidence": 0.9,
            "estimated_age": "elderly",
            "location_type": "stairs",
            "hazards_detected": ["wet_floor"],
        }
        result = decision_node_attention(state)
        assert result["severity"] in ["LOW", "MEDIUM", "HIGH"]
        assert 0 <= result["severity_score"] <= 100
        assert "log_to_db" in result["recommended_actions"]

    def test_decision_node_fallback_without_model(self):
        """모델 파일 없으면 rule-based로 fallback"""
        from agentic.nodes.decision import decision_node_rule
        state = {
            "pose_data": {"angle": 50, "velocity": 10},
            "no_movement_seconds": 2.0,
            "audio_scream_detected": False,
            "audio_impact_detected": False,
            "audio_confidence": 0.0,
            "estimated_age": "adult",
            "location_type": "other",
            "hazards_detected": [],
        }
        result = decision_node_rule(state)
        assert result["severity"] in ["LOW", "MEDIUM", "HIGH"]
        assert 0 <= result["severity_score"] <= 100
