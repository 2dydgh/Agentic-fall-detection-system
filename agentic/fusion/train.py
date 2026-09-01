"""
Attention Fusion Model 학습 스크립트.

Usage:
    python -m agentic.fusion.train                     # 기본 학습
    python -m agentic.fusion.train --epochs 100        # 에포크 지정
    python -m agentic.fusion.train --compare           # rule-based 비교 실험
"""

import argparse
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import classification_report, confusion_matrix

from .dataset import generate_dataset, FusionDataset
from .model import AttentionFusionModel, SEVERITY_CLASSES


def train(epochs: int = 80, lr: float = 1e-3, batch_size: int = 64, n_samples: int = 10000):
    print(f"=== Attention Fusion Model 학습 ===")
    print(f"Epochs: {epochs}, LR: {lr}, Samples: {n_samples}\n")

    # 데이터 생성
    features, scores, classes = generate_dataset(n_samples=n_samples, seed=42)
    dataset = FusionDataset(features, scores, classes)

    # Train/Val split (80/20)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_set, val_set = random_split(dataset, [train_size, val_size])

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_set, batch_size=batch_size)

    print(f"Train: {train_size}, Val: {val_size}")
    print(f"Class distribution: LOW={int((classes==0).sum())}, MEDIUM={int((classes==1).sum())}, HIGH={int((classes==2).sum())}\n")

    # 모델
    model = AttentionFusionModel(d_model=64, num_heads=4, dropout=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # Loss: score regression + class classification (multi-task)
    score_loss_fn = nn.MSELoss()
    class_loss_fn = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    best_state = None

    for epoch in range(1, epochs + 1):
        # --- Train ---
        model.train()
        train_score_loss = 0
        train_class_loss = 0
        train_correct = 0
        train_total = 0

        for feat, score, cls in train_loader:
            out = model(feat)

            loss_s = score_loss_fn(out["score"], score)
            loss_c = class_loss_fn(out["logits"], cls)
            loss = loss_s + loss_c  # multi-task loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_score_loss += loss_s.item() * feat.size(0)
            train_class_loss += loss_c.item() * feat.size(0)
            train_correct += (out["logits"].argmax(dim=-1) == cls).sum().item()
            train_total += feat.size(0)

        scheduler.step()

        # --- Validation ---
        model.eval()
        val_score_loss = 0
        val_class_loss = 0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for feat, score, cls in val_loader:
                out = model(feat)
                val_score_loss += score_loss_fn(out["score"], score).item() * feat.size(0)
                val_class_loss += class_loss_fn(out["logits"], cls).item() * feat.size(0)
                val_correct += (out["logits"].argmax(dim=-1) == cls).sum().item()
                val_total += feat.size(0)

        train_acc = train_correct / train_total
        val_acc = val_correct / val_total
        avg_train_s = train_score_loss / train_total
        avg_val_s = val_score_loss / val_total

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d} | Train Acc: {train_acc:.4f} Score MSE: {avg_train_s:.2f} | "
                  f"Val Acc: {val_acc:.4f} Score MSE: {avg_val_s:.2f}")

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state = model.state_dict().copy()

    # 최적 모델 저장
    model.load_state_dict(best_state)
    save_path = "models/fusion_model.pt"
    torch.save(best_state, save_path)
    print(f"\nBest Val Accuracy: {best_val_acc:.4f}")
    print(f"Model saved to {save_path}")

    # --- Validation set 상세 평가 ---
    print("\n=== Validation Set Evaluation ===")
    evaluate(model, val_loader)

    return model


def evaluate(model: AttentionFusionModel, loader: DataLoader):
    """모델 평가 + attention weight 분석"""
    model.eval()
    all_preds = []
    all_labels = []
    all_score_errors = []
    all_attn_weights = []

    with torch.no_grad():
        for feat, score, cls in loader:
            out = model(feat, return_attention=True)
            preds = out["logits"].argmax(dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(cls.cpu().numpy())
            all_score_errors.extend((out["score"] - score).abs().cpu().numpy())
            all_attn_weights.append(out["attn_weights"].cpu().numpy())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    print("\n[Classification Report]")
    print(classification_report(all_labels, all_preds, target_names=SEVERITY_CLASSES))

    print("[Confusion Matrix]")
    cm = confusion_matrix(all_labels, all_preds)
    print(f"{'':>8} {'LOW':>6} {'MED':>6} {'HIGH':>6}")
    for i, name in enumerate(["LOW", "MED", "HIGH"]):
        print(f"{name:>8} {cm[i][0]:6d} {cm[i][1]:6d} {cm[i][2]:6d}")

    print(f"\nMean Absolute Score Error: {np.mean(all_score_errors):.2f}")

    # Attention weight 분석
    attn = np.concatenate(all_attn_weights, axis=0)  # (N, 3, 3)
    mean_attn = attn.mean(axis=0)
    modalities = ["Pose", "Audio", "VLM"]
    print(f"\n[Mean Attention Weights]")
    print(f"{'':>8} {'Pose':>8} {'Audio':>8} {'VLM':>8}")
    for i, name in enumerate(modalities):
        print(f"{name:>8} {mean_attn[i][0]:8.4f} {mean_attn[i][1]:8.4f} {mean_attn[i][2]:8.4f}")

    # 각 모달리티가 받는 평균 attention (column mean)
    print(f"\n[Modality Importance (mean attention received)]")
    col_mean = mean_attn.mean(axis=0)
    for name, val in zip(modalities, col_mean):
        bar = "#" * int(val * 50)
        print(f"  {name:>5}: {val:.4f} {bar}")


def compare_with_rule_based(n_samples: int = 2000):
    """Rule-based vs Attention-based 비교 실험"""
    from agentic.nodes.decision import decision_node

    print("\n=== Rule-based vs Attention-based 비교 실험 ===\n")

    features, scores, classes = generate_dataset(n_samples=n_samples, seed=99)
    model = AttentionFusionModel()
    state_dict = torch.load("models/fusion_model.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict)
    model.eval()

    # Attention-based 예측
    attn_preds = []
    with torch.no_grad():
        out = model(features, return_attention=False)
        attn_preds = out["logits"].argmax(dim=-1).numpy()

    attn_acc = (attn_preds == classes.numpy()).mean()

    # Rule-based 예측 (동일 데이터에 대해)
    # features를 다시 state로 복원해서 rule-based 적용
    rule_preds = []
    dataset = generate_dataset(n_samples=n_samples, seed=99)
    # 다시 생성하여 원본 state 복원
    rng = np.random.default_rng(99)
    from .dataset import SCENARIOS, _sample_state, _compute_label
    weights = np.array([s["weight"] for s in SCENARIOS], dtype=float)
    weights /= weights.sum()
    counts = np.round(weights * n_samples).astype(int)
    counts[-1] = n_samples - counts[:-1].sum()

    all_states = []
    for scenario, count in zip(SCENARIOS, counts):
        for _ in range(count):
            state = _sample_state(scenario, rng)
            all_states.append(state)

    perm = torch.randperm(n_samples, generator=torch.Generator().manual_seed(99))

    rule_correct = 0
    for idx in range(n_samples):
        state = all_states[perm[idx]]
        result = decision_node(state)
        rule_cls = SEVERITY_CLASSES.index(result["severity"])
        if rule_cls == classes[idx].item():
            rule_correct += 1

    rule_acc = rule_correct / n_samples

    print(f"Rule-based Accuracy:     {rule_acc:.4f}")
    print(f"Attention-based Accuracy: {attn_acc:.4f}")
    print(f"Improvement:             {(attn_acc - rule_acc)*100:+.2f}%p")

    # 클래스별 비교
    print(f"\n[Class-wise Accuracy]")
    for i, name in enumerate(SEVERITY_CLASSES):
        mask = classes.numpy() == i
        if mask.sum() == 0:
            continue
        attn_cls_acc = (attn_preds[mask] == i).mean()
        print(f"  {name}: Attention={attn_cls_acc:.4f} (n={mask.sum()})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--compare", action="store_true", help="Rule-based 비교 실험")
    args = parser.parse_args()

    import os
    os.makedirs("models", exist_ok=True)

    model = train(epochs=args.epochs, lr=args.lr, n_samples=args.samples)

    if args.compare:
        compare_with_rule_based()
