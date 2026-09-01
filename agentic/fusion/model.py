"""
Attention-based Multimodal Fusion Model.

3개 모달리티(Pose, Audio, VLM)의 feature vector에 Multi-Head Self-Attention을 적용하여
모달리티 간 동적 가중치를 학습하고, severity score(0~100)와 severity class를 예측.

Architecture:
    Input (3, 6) → Linear Projection (3, d_model)
                 → + Modality Embedding
                 → Multi-Head Self-Attention (num_heads=4)
                 → LayerNorm + Residual
                 → Mean Pooling (d_model,)
                 → MLP Head → severity_score (1,) + severity_class (3,)
"""

import torch
import torch.nn as nn
import os

from .feature import FEATURE_DIM


NUM_MODALITIES = 3  # pose, audio, vlm
SEVERITY_CLASSES = ["LOW", "MEDIUM", "HIGH"]


class AttentionFusionModel(nn.Module):
    def __init__(self, d_model: int = 64, num_heads: int = 4, dropout: float = 0.1):
        super().__init__()
        self.d_model = d_model

        # 각 모달리티 feature를 d_model 차원으로 projection
        self.input_proj = nn.Linear(FEATURE_DIM, d_model)

        # 학습 가능한 modality embedding (어떤 모달리티인지 구분)
        self.modality_embedding = nn.Embedding(NUM_MODALITIES, d_model)

        # Multi-Head Self-Attention
        self.self_attn = nn.MultiheadAttention(
            embed_dim=d_model,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )
        self.attn_norm = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

        # Feed-Forward Network (attention 후)
        self.ffn = nn.Sequential(
            nn.Linear(d_model, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, d_model),
        )
        self.ffn_norm = nn.LayerNorm(d_model)

        # Classification head: severity score (regression) + class (classification)
        self.score_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),  # 0~1 출력 → 0~100으로 스케일
        )
        self.class_head = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.GELU(),
            nn.Linear(32, len(SEVERITY_CLASSES)),
        )

    def forward(
        self, x: torch.Tensor, return_attention: bool = False
    ) -> dict[str, torch.Tensor]:
        """
        Args:
            x: (batch, 3, FEATURE_DIM) — 3개 모달리티 feature
            return_attention: True면 attention weight도 반환

        Returns:
            dict with keys:
                - score: (batch,) severity score 0~100
                - logits: (batch, 3) severity class logits
                - attn_weights: (batch, 3, 3) attention weights (optional)
        """
        batch_size = x.size(0)

        # Linear projection: (batch, 3, 6) → (batch, 3, d_model)
        h = self.input_proj(x)

        # Modality embedding 추가
        mod_ids = torch.arange(NUM_MODALITIES, device=x.device)
        mod_emb = self.modality_embedding(mod_ids)  # (3, d_model)
        h = h + mod_emb.unsqueeze(0)  # broadcast to batch

        # Self-Attention + Residual + LayerNorm
        attn_out, attn_weights = self.self_attn(h, h, h, need_weights=True)
        h = self.attn_norm(h + self.dropout(attn_out))

        # FFN + Residual + LayerNorm
        ffn_out = self.ffn(h)
        h = self.ffn_norm(h + self.dropout(ffn_out))

        # Mean pooling across modalities: (batch, 3, d_model) → (batch, d_model)
        pooled = h.mean(dim=1)

        # Prediction heads
        score = self.score_head(pooled).squeeze(-1) * 100  # 0~100
        logits = self.class_head(pooled)

        result = {"score": score, "logits": logits}
        if return_attention:
            result["attn_weights"] = attn_weights

        return result

    def predict(self, x: torch.Tensor) -> dict:
        """
        단일 샘플 추론용. Attention weight 포함.

        Args:
            x: (3, FEATURE_DIM) 단일 샘플 feature

        Returns:
            dict: score (float), severity (str), attn_weights (3x3 numpy)
        """
        self.eval()
        with torch.no_grad():
            if x.dim() == 2:
                x = x.unsqueeze(0)  # (1, 3, 6)
            out = self.forward(x, return_attention=True)

            score = out["score"].item()
            score = max(0, min(100, score))

            class_idx = out["logits"].argmax(dim=-1).item()
            severity = SEVERITY_CLASSES[class_idx]

            attn = out["attn_weights"].squeeze(0).cpu().numpy()

        return {
            "severity_score": int(round(score)),
            "severity": severity,
            "attn_weights": attn,  # (3, 3) — [pose, audio, vlm] x [pose, audio, vlm]
        }


def load_fusion_model(
    model_path: str = "models/fusion_model.pt", device: str = "cpu"
) -> AttentionFusionModel:
    """학습된 fusion model 로드. 파일 없으면 None 반환."""
    if not os.path.exists(model_path):
        return None
    model = AttentionFusionModel()
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    return model
