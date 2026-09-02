# 개발 내용 및 성과

이 문서는 프로젝트의 주요 개발 항목을 다룬다. 전체 개요는 [README](../README.md), 설계 근거는 [ARCHITECTURE.md](ARCHITECTURE.md), 온톨로지 기반 판정은 [ONTOLOGY.md](ONTOLOGY.md)를 참고.

---

### 1. Agentic Workflow 설계 — LangGraph 기반 자율 판단 파이프라인

| 항목 | 내용 |
|------|------|
| **기존 방식의 한계** | `if fallen → alert()` 형태의 정적 룰 기반 로직 |
| **해결 방법** | LangGraph로 `PerceptionNode → AudioNode → AnalysisNode → DecisionNode → ActionNode` 파이프라인 구현 |
| **핵심 효과** | 비전 + 오디오 멀티모달 Late Fusion, 장소/위험 요소에 따라 동적으로 **심각도(Severity) 점수** 산출 |

PerceptionNode는 **다중 신호 판정**으로 낙상을 감지한다. 단순 각도 임계치 대신 네 가지
독립 신호(각도·높이 전이·하강 속도·종횡비)를 종합하여 카메라 앵글에 의한 미감지를
보정한다. 상세는 [ARCHITECTURE.md](ARCHITECTURE.md#perceptionnode--다중-신호-낙상-감지) 참고.

> **결과:** 가짜 알람(False Positive) 대폭 감소 + 카메라 앵글에 의한 미감지(False Negative) 보정

---

### 2. Attention-based Multimodal Fusion — 동적 모달리티 가중치 학습

```
비디오 프레임               오디오 청크 (0.975초)         장면 이미지
    │                           │                          │
    ▼                           ▼                          ▼
 YOLO11n-pose               YAMNet (521클래스)         Florence-2 VLM
 (각도/속도/부동시간)       (비명/충격음/신뢰도)       (나이/장소/위험요소)
    │                           │                          │
    ▼                           ▼                          ▼
 Pose Feature (6d)         Audio Feature (6d)         VLM Feature (6d)
    │                           │                          │
    └───────────────────────────┼──────────────────────────┘
                                ▼
                   Multi-Head Self-Attention (4 heads)
                   + Modality Embedding + LayerNorm
                                │
                                ▼
                    ┌───────────┴───────────┐
                    ▼                       ▼
              Score Head               Class Head
           (severity 0~100)        (LOW/MEDIUM/HIGH)
```

| 항목 | 내용 |
|------|------|
| **문제** | 기존 Rule-based Late Fusion은 고정 가중치(`비명 +15점`, `충격음 +10점`) → 모달리티 간 상호작용 무시 |
| **해결** | PyTorch Multi-Head Self-Attention으로 3개 모달리티(Pose, Audio, VLM) 간 동적 가중치 학습 |
| **학습 방식** | 도메인 지식 기반 9개 시나리오에서 10,000개 학습 데이터 생성, 모달리티 간 상호작용(비명+큰 각도, 고령자+위험 장소 등) 반영 |
| **효과** | Validation Accuracy 91.0%, Score MAE 6.85점 달성. 상황에 따라 Pose/Audio/VLM 가중치가 동적으로 변화 |

**Attention Weight 분석 — 모달리티별 중요도:**
```
Pose:  0.6122 ##############################
Audio: 0.2152 ##########
VLM:   0.1726 ########
```

> **결과:** Rule-based 고정 가중치 → Attention 동적 가중치 전환으로, 비명+급격한 낙상은 Audio 가중치 상승, 고령자+위험 장소는 VLM 가중치 상승 — **상황별 최적 모달리티 조합을 자동으로 학습**

---

### 3. LLM Agent Mode — Ollama 기반 지능형 판단 (on/off 전환)

| 항목 | 내용 |
|------|------|
| **기존 방식** | 룰 기반 점수 계산 (`if score > 75 → HIGH`) — 빠르지만 맥락 이해 불가 |
| **Agent Mode** | Ollama 로컬 LLM이 센서 데이터를 종합 판단 — "계단 + 고령자 + 비명 → 119 필요" |
| **설계 철학** | 실시간 관제에서는 룰 기반(빠름), 정밀 분석 시 LLM(똑똑함)으로 on/off 전환 |

```bash
# 룰 기반 (기본, ~0.001ms)
python main_agentic.py --video input/sample.mp4

# LLM Agent 모드 (Ollama 필요, ~5-8초/판단)
python main_agentic.py --video input/sample.mp4 --agent-mode

# API 런타임 토글
curl -X POST http://localhost:8000/api/agent_toggle
```

| | 룰 기반 (OFF) | LLM Agent (ON) |
|--|--------------|----------------|
| 속도 | ~0.001ms (실측) | ~5-8초 (실측, 3B 모델 기준) |
| 판단력 | 고정 점수 계산 | 맥락 기반 종합 판단 |
| 비용 | 없음 | 없음 (로컬 Ollama) |
| LLM 실패 시 | — | 자동 룰 기반 폴백 |

> **설계 근거:** 낙상 감지는 골든타임이 생명이므로 **실시간 경로는 룰 기반(~0.001ms)으로 즉시 대응**하고, LLM은 비동기 후속 판단 또는 사후 정밀 분석 용도로 설계. "Agentic하게 만들 수 있느냐"와 "만들어야 하느냐"는 다른 문제 — **의도적으로 속도를 우선한 엔지니어링 판단**

---

### 4. 다중 카메라 동시 스트리밍 — FastAPI Async 아키텍처

```python
# YOLO 추론이 asyncio 이벤트 루프를 블로킹하지 않도록 처리
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(executor, yolo_inference, frame)
```

| 항목 | 내용 |
|------|------|
| **문제** | 무거운 YOLO 추론이 단일 스레드 이벤트 루프를 블로킹 |
| **해결** | `run_in_executor` 기반 멀티스레딩 MJPEG 스트리밍 |
| **효과** | YOLO 추론을 별도 스레드로 분리하여 다중 카메라 동시 스트리밍 가능 |

---

### 5. 포즈 추정 휴리스틱 튜닝 — False Positive/Negative 제거

<details>
<summary><b>낙상 판정 알고리즘 상세 (클릭하여 펼치기)</b></summary>

```
False Positive (오탐) 방지:
  - 쪼그려 앉기(Squatting) → 낙상으로 오인 (기울기 유사)
  - 빠른 전진 동작 → 순간적으로 낙상 각도 통과
  → 해결: 5프레임 연속 확인 + 60프레임 쿨다운

False Negative (미감지) 방지:
  - 카메라를 정면으로 향한 상태에서 쓰러짐 → 각도가 작게 측정됨
  - 느린 주저앉기 → 단일 임계치로 잡히지 않음
  → 해결: 다중 신호 판정 (각도·높이 전이·하강 속도·종횡비)

핵심 로직:
  1. 4개 독립 신호 중 1개 이상 충족 시 낙상 후보
  2. 5프레임 연속 유지 시 최종 낙상 판정
  3. 판정 후 60프레임 쿨다운으로 중복 감지 방지
  4. 서 있을 때 코 Y좌표를 EMA(α=0.2)로 추적하여 높이 전이 기준 유지
```

</details>

> **결과:** 일상 동작 오탐 방지 + 카메라 앵글에 의한 미감지 보정. 상세는 [ARCHITECTURE.md](ARCHITECTURE.md#perceptionnode--다중-신호-낙상-감지) 참고.

---

### 6. 관제실 특화 대시보드 — Next.js + TailwindCSS

**주요 UI 기능:**
- 낙상 감지 즉시 **화면 전체 붉은색 맥박(Pulse) 점멸**
- **출동 요원 배치** 타이포그래피 오버레이 자동 출력
- SQLite DB와 **2초 폴링**으로 실시간 통계 갱신
- **다크 모드 전용 UI**

---

### 7. 📧 실시간 자동 긴급 이메일 발송 — 오프라인 2중 안전장치

```
낙상 감지 (HIGH Severity)
        │
        ├── 해당 프레임 캡처
        ├── Florence-2 상황 분석 보고서 생성 (TXT)
        └── Gmail SMTP → 담당자 스마트폰으로 즉시 전송
              └── 첨부: 낙상 스냅샷 + 분석 보고서
```

> **결과:** 보안 담당자가 자리를 비운 **최악의 시나리오에서도** 스마트폰으로 즉시 상황 파악 가능

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="figures/mail_list.PNG" alt="Email List" width="280" /><br/>
        <sub><b>이메일함 — 다중 낙상 감지 알림</b><br/>발생할 때마다 자동으로 긴급 메일 수신</sub>
      </td>
      <td align="center">
        <img src="figures/mail_content.PNG" alt="Email Content" width="280" /><br/>
        <sub><b>이메일 본문 — 현장 상황 요약</b><br/>Florence-2 VLM이 진단한 상황 분석 포함</sub>
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="figures/snapshot.PNG" alt="Fall Snapshot" width="280" /><br/>
        <sub><b>낙상 감지 스냅샷</b><br/>낙상 발생 순간 자동 캡처된 현장 사진</sub>
      </td>
      <td align="center">
        <img src="figures/report.PNG" alt="Incident Report" width="280" /><br/>
        <sub><b>자동 생성 긴급 상황 보고서</b><br/>심각도·위치·권고 조치가 담긴 TXT 보고서</sub>
      </td>
    </tr>
  </table>
</div>

---

---

### 8. 🧠 비동기 에스컬레이션 Agent — LangGraph ReAct 그래프 기반 후속 판단

```
[실시간 경로 — 즉시 대응]                [비동기 경로 — LangGraph ReAct 그래프]
Perception → Audio → fall?             EscalationAgent (별도 스레드)
  └─ Yes → Decision → Action ────▶       reason ──(조건)──▶ act ──▶ reason
  └─ No  → END                             │                       (루프)
                                            └──(done/timeout)──▶ END
                                                     │
                                                     ▼
                                              agent_results DB 저장
```

| 항목 | 내용 |
|------|------|
| **문제** | 실시간 경로의 룰 기반 판단은 빠르지만 맥락 이해 불가 (반복 오탐, 패턴 분석 등) |
| **해결** | ActionNode에서 낙상 감지 시 별도 스레드로 `EscalationAgent` 비동기 실행 — 실시간 경로 블로킹 없음 |
| **Agent 도구** | `query_incident_history` (이력 조회), `reanalyze_with_vlm` (Florence-2 재분석), `escalate_emergency` (119 에스컬레이션), `update_severity` (심각도 수정) |
| **안전장치** | max_iterations=4, timeout=30s 이중 제한 + LLM 실패 시 룰 기반 폴백 |

> 이 비동기 경로가 **Tool Calling + ReAct 루프 + 자율 판단을 갖춘 진짜 AI Agent**. 실시간 경로는 속도, 비동기 경로는 지능 — 2-Track Architecture의 핵심.

---
