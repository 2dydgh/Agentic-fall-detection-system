"use client";

import { useState } from "react";
import { Search, AlertTriangle, RefreshCw, Eye } from "lucide-react";

/* ══════════════════════════════════════════════════════
   System Architecture — LangGraph Pipeline, 2-Track
   Decision, and Escalation Agent visualization
   ══════════════════════════════════════════════════════ */

const V = {
  blue: "var(--color-g-blue)",
  green: "var(--color-g-green)",
  red: "var(--color-g-red)",
  orange: "var(--color-g-orange)",
  yellow: "var(--color-g-yellow)",
  purple: "var(--color-g-purple)",
  pink: "var(--color-g-pink)",
  muted: "var(--color-g-muted)",
};

const PIPELINE = [
  { id: "perception", label: "인지", model: "YOLO11n-pose", color: V.blue, file: "perception.py",
    details: ["키포인트 추적 (17관절)", "각도 임계값 = 35°", "확인 프레임 = 5", "쿨다운 = 60 프레임", "신뢰도 ≥ 0.3"] },
  { id: "audio", label: "오디오", model: "YAMNet", color: V.orange, file: "audio.py",
    details: ["프레임 동기 0.975s 청크", "16kHz × 15600 샘플", "521클래스 분류", "비명 / 충격음 감지"] },
  { id: "branch", label: "낙상?", model: "", color: V.yellow, file: "graph.py",
    details: ["조건부 분기", "fall_detected = True → 계속", "fall_detected = False → 종료", "단락 최적화"] },
  { id: "analysis", label: "분석", model: "Florence-2", color: V.green, file: "analysis.py",
    details: ["VLM 장면 기술", "지연 로딩 (GPU 사용)", "생략 가능 (--skip-vlm)", "판정에 컨텍스트 제공"] },
  { id: "decision", label: "판정", model: "Rule / LLM", color: V.pink, file: "decision.py",
    details: ["2-Track 구조", "Track 1: 규칙 기반 점수", "Track 2: LLM (Ollama)", "어텐션 퓨전 가중치"] },
  { id: "action", label: "조치", model: "Dispatch", color: V.red, file: "action.py",
    details: ["DB 기록", "스냅샷 저장", "Slack / Email 전송", "보안실 알림", "비동기 에이전트 트리거"] },
];

const AGENT_TOOLS = [
  { name: "query_incident_history", desc: "최근 사건 이력 조회 (30분 이내)", Icon: Search, color: V.blue },
  { name: "escalate_emergency", desc: "119 긴급 호출 / 보안실 알림 발동", Icon: AlertTriangle, color: V.red },
  { name: "update_severity", desc: "심각도 재평가 및 DB 업데이트", Icon: RefreshCw, color: V.orange },
  { name: "reanalyze_with_vlm", desc: "Florence-2 재분석 요청", Icon: Eye, color: V.green },
];

/* ── Components ── */

function PipelineNode({ stage, isActive, onClick }: {
  stage: typeof PIPELINE[number]; isActive: boolean; onClick: () => void;
}) {
  const isDiamond = stage.id === "branch";

  if (isDiamond) {
    return (
      <button onClick={onClick} className="flex flex-col items-center gap-2.5 group cursor-pointer mx-5 shrink-0">
        <div
          className="w-[56px] h-[56px] rotate-45 rounded-lg flex items-center justify-center transition-all duration-300"
          style={{
            background: isActive
              ? `color-mix(in srgb, ${stage.color} 20%, transparent)`
              : "var(--color-g-surface)",
            border: `2px solid ${isActive ? stage.color : "var(--color-g-border)"}`,
            boxShadow: isActive ? `0 0 24px color-mix(in srgb, ${stage.color} 25%, transparent)` : "none",
          }}
        >
          <span className="-rotate-45 text-[15px] font-bold whitespace-nowrap" style={{ color: stage.color }}>
            {stage.label}
          </span>
        </div>
        <span className="text-[12px] text-g-muted group-hover:text-g-text-secondary transition-colors">
          conditional
        </span>
      </button>
    );
  }

  return (
    <button onClick={onClick} className="flex flex-col items-center gap-1 group cursor-pointer shrink-0">
      <div
        className="min-w-[104px] px-4 py-3 rounded-xl flex flex-col items-center justify-center transition-all duration-300"
        style={{
          background: isActive
            ? `color-mix(in srgb, ${stage.color} 12%, transparent)`
            : "var(--color-g-surface)",
          border: `2px solid ${isActive ? stage.color : "var(--color-g-border)"}`,
          boxShadow: isActive ? `0 0 24px color-mix(in srgb, ${stage.color} 20%, transparent)` : "none",
        }}
      >
        <span className="text-[15px] font-bold" style={{ color: stage.color }}>
          {stage.label}
        </span>
        {stage.model && (
          <span className="text-[11px] text-g-muted mt-0.5">{stage.model}</span>
        )}
      </div>
    </button>
  );
}

function PipelineArrow({ active }: { active?: boolean }) {
  return (
    <div className="flex items-center shrink-0">
      <div className={`w-10 h-[2px] transition-colors duration-300 ${active ? "bg-g-orange" : "bg-g-border2"}`} />
      <svg width="8" height="12" viewBox="0 0 8 12" className={`transition-colors ${active ? "text-g-orange" : "text-g-border2"}`}>
        <path d="M0 0L8 6L0 12Z" fill="currentColor" />
      </svg>
    </div>
  );
}

function ReActLoop() {
  const [step, setStep] = useState(0);
  const steps = ["reason", "select_tool", "execute", "observe"];
  const stepLabels = ["추론", "도구 선택", "실행", "관찰"];
  const stepColors = [V.blue, V.orange, V.red, V.green];

  return (
    <div className="relative">
      <div className="flex items-center justify-center gap-3">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-3">
            <button
              onClick={() => setStep(i)}
              className="w-[72px] h-[72px] rounded-full flex flex-col items-center justify-center transition-all duration-300 cursor-pointer"
              style={{
                background: step === i
                  ? `color-mix(in srgb, ${stepColors[i]} 15%, transparent)`
                  : "var(--color-g-surface)",
                border: step === i ? `2px solid ${stepColors[i]}` : "1px solid var(--color-g-border)",
                boxShadow: step === i ? `0 0 20px color-mix(in srgb, ${stepColors[i]} 20%, transparent)` : "none",
                transform: step === i ? "scale(1.08)" : "scale(1)",
              }}
            >
              <span className="text-[14px] font-bold" style={{ color: stepColors[i] }}>
                {i + 1}
              </span>
              <span className="text-[12px] font-medium mt-0.5" style={{ color: stepColors[i], opacity: step === i ? 1 : 0.5 }}>
                {stepLabels[i]}
              </span>
            </button>
            {i < steps.length - 1 && (
              <svg width="28" height="14" viewBox="0 0 28 14" className="text-g-border2">
                <path d="M0 7h20M16 3l6 4-6 4" fill="none" stroke="currentColor" strokeWidth="1.5" />
              </svg>
            )}
          </div>
        ))}
      </div>

      <div className="flex items-center justify-center mt-2">
        <svg width="420" height="32" viewBox="0 0 420 32" className="text-g-border2">
          <path d="M360 5 Q395 5 395 16 Q395 27 25 27 Q0 27 0 16 L0 13" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="4 3" />
          <text x="198" y="24" textAnchor="middle" fill="var(--color-g-muted)" fontSize="11">반복 (최대 4회, 제한시간 30초)</text>
        </svg>
      </div>

      <div className="mt-4 px-5 py-4 bg-g-panel border border-g-border rounded-xl">
        {step === 0 && (
          <div>
            <span className="text-[15px] font-semibold" style={{ color: stepColors[0] }}>추론</span>
            <p className="text-[14px] text-g-text-secondary mt-1.5">LLM이 현재 상태를 분석하고 다음 행동을 결정합니다.</p>
            <pre className="text-[12px] text-g-blue/60 mt-3 leading-relaxed px-3 py-2.5 bg-g-surface rounded-lg whitespace-pre-wrap">
{`ollama.chat(model="llama3.2", format="json")
→ { "action": "query_incident_history",
     "reasoning": "최근 유사 사건 확인 필요" }`}
            </pre>
          </div>
        )}
        {step === 1 && (
          <div>
            <span className="text-[15px] font-semibold" style={{ color: stepColors[1] }}>도구 선택</span>
            <p className="text-[14px] text-g-text-secondary mt-1.5">4개 도구 중 하나를 선택합니다.</p>
            <div className="grid grid-cols-2 gap-2.5 mt-3">
              {AGENT_TOOLS.map((t) => (
                <div key={t.name} className="flex items-center gap-2.5 px-3 py-2 bg-g-surface border border-g-border rounded-lg">
                  <t.Icon className="w-4 h-4 shrink-0" style={{ color: t.color }} />
                  <span className="text-[12px] font-mono truncate" style={{ color: t.color }}>{t.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {step === 2 && (
          <div>
            <span className="text-[15px] font-semibold" style={{ color: stepColors[2] }}>실행</span>
            <p className="text-[14px] text-g-text-secondary mt-1.5">선택된 도구를 실행하고 결과를 수집합니다.</p>
            <pre className="text-[12px] text-g-orange/60 mt-3 leading-relaxed px-3 py-2.5 bg-g-surface rounded-lg whitespace-pre-wrap">
{`tool_result = query_incident_history(
    camera_id="01", minutes=30
)
→ [INC-20260902-143022-a1b2c3, ...]`}
            </pre>
          </div>
        )}
        {step === 3 && (
          <div>
            <span className="text-[15px] font-semibold" style={{ color: stepColors[3] }}>관찰</span>
            <p className="text-[14px] text-g-text-secondary mt-1.5">실행 결과를 관찰하고, 추가 행동이 필요한지 판단합니다.</p>
            <pre className="text-[12px] text-g-green/60 mt-3 leading-relaxed px-3 py-2.5 bg-g-surface rounded-lg whitespace-pre-wrap">
{`observation: "30분 내 2건의 유사 사건 발견"
→ decision: escalate (재낙상 패턴 확인)
→ next: escalate_emergency`}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main page ── */
export function ArchitecturePage() {
  const [activeStage, setActiveStage] = useState<string>("perception");
  const activeInfo = PIPELINE.find((s) => s.id === activeStage)!;

  return (
    <div className="flex flex-col h-full p-4 gap-5 overflow-hidden">
      <div className="shrink-0 pb-3 border-b border-g-border">
        <h1 className="text-xl font-bold text-g-text">시스템 아키텍처</h1>
        <p className="text-base text-g-muted mt-0.5">LangGraph 파이프라인 · 2-Track 판정 · 비동기 에스컬레이션 에이전트</p>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto space-y-5">
        {/* ── Section 1: LangGraph Pipeline ── */}
        <div className="bg-g-card border border-g-border rounded-xl">
          <div className="flex items-center gap-2.5 px-5 py-3.5 bg-g-surface/50 border-b border-g-border rounded-t-xl">
            <div className="w-2.5 h-2.5 rounded-full bg-g-orange" />
            <h2 className="text-[16px] font-semibold text-g-text">LangGraph 파이프라인</h2>
            <span className="text-[12px] text-g-muted ml-auto">StateGraph over AgentState</span>
          </div>
          <div className="px-6 pt-8 pb-6">
            <div className="flex items-center justify-center gap-1">
              {PIPELINE.map((stage, i) => (
                <div key={stage.id} className="flex items-center">
                  <PipelineNode stage={stage} isActive={activeStage === stage.id} onClick={() => setActiveStage(stage.id)} />
                  {i < PIPELINE.length - 1 && <PipelineArrow active={activeStage === stage.id || activeStage === PIPELINE[i + 1]?.id} />}
                </div>
              ))}
              <div className="flex items-center ml-2 shrink-0">
                <div className="w-6 h-[2px] bg-g-border2" />
                <div className="w-12 h-12 rounded-full bg-g-surface border-2 border-g-border flex items-center justify-center">
                  <span className="text-[12px] font-semibold text-g-muted">END</span>
                </div>
              </div>
            </div>

            {/* Active stage detail */}
            <div className="mt-6 px-5 py-4 bg-g-surface border border-g-border rounded-xl transition-all duration-300">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: activeInfo.color }} />
                <span className="text-[17px] font-bold" style={{ color: activeInfo.color }}>{activeInfo.label}Node</span>
                <span className="text-[12px] text-g-muted">agentic/nodes/{activeInfo.file}</span>
                {activeInfo.model && (
                  <span className="text-[12px] font-medium px-2.5 py-1 ml-auto rounded-lg shrink-0" style={{
                    background: `color-mix(in srgb, ${activeInfo.color} 10%, transparent)`, color: activeInfo.color,
                  }}>{activeInfo.model}</span>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {activeInfo.details.map((d) => (
                  <span key={d} className="text-[13px] text-g-text-secondary px-3 py-1.5 bg-g-panel border border-g-border rounded-lg">{d}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── Section 2: 2-Track Decision ── */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-g-card border border-g-border rounded-xl">
            <div className="flex items-center gap-2.5 px-4 py-3 bg-g-surface/50 border-b border-g-border rounded-t-xl">
              <div className="w-7 h-7 flex items-center justify-center text-[13px] font-bold rounded-lg bg-g-blue/20 text-g-blue">T1</div>
              <div>
                <h3 className="text-[15px] font-semibold text-g-text">Track 1 — 규칙 기반</h3>
                <span className="text-[12px] text-g-muted">실시간 · decision.py</span>
              </div>
              <span className="text-[11px] font-semibold px-2 py-0.5 bg-g-green text-white ml-auto rounded-md">실시간</span>
            </div>
            <div className="space-y-3.5 p-4">
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">점수 산출</span>
                <div className="flex items-center gap-2.5">
                  <div className="flex-1 h-4 bg-g-bg overflow-hidden rounded-sm flex">
                    <div className="h-full bg-g-green/35" style={{ width: "50%" }} />
                    <div className="h-full bg-g-orange/35" style={{ width: "25%" }} />
                    <div className="h-full bg-g-red/35" style={{ width: "25%" }} />
                  </div>
                  <span className="font-mono text-g-muted text-[12px] w-12 text-right">0-100</span>
                </div>
                <div className="flex gap-4 mt-2 text-[12px] text-g-muted">
                  <span>낮음 ≤ 50</span><span>주의 ≤ 75</span><span>위험 &gt; 75</span>
                </div>
              </div>
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">후기 퓨전</span>
                <div className="flex gap-2">
                  {[
                    { m: "자세", c: V.blue },
                    { m: "오디오", c: V.orange },
                    { m: "시각", c: V.green },
                  ].map((f) => (
                    <div key={f.m} className="flex items-center gap-1.5 px-2.5 py-1.5 bg-g-surface border border-g-border rounded-lg">
                      <span className="w-2 h-2 rounded-full" style={{ background: f.c }} />
                      <span className="text-[13px] font-medium" style={{ color: f.c }}>{f.m}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">오디오 보너스</span>
                <div className="flex gap-4 text-[13px] font-mono">
                  <span className="text-g-orange">비명 +15</span>
                  <span className="text-g-blue">충격음 +10</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-g-card border border-g-border rounded-xl">
            <div className="flex items-center gap-2.5 px-4 py-3 bg-g-surface/50 border-b border-g-border rounded-t-xl">
              <div className="w-7 h-7 flex items-center justify-center text-[13px] font-bold rounded-lg bg-g-pink/20 text-g-pink">T2</div>
              <div>
                <h3 className="text-[15px] font-semibold text-g-text">Track 2 — LLM 에이전트</h3>
                <span className="text-[12px] text-g-muted">비동기 · decision_llm.py</span>
              </div>
              <span className="text-[11px] font-semibold px-2 py-0.5 bg-g-orange text-white ml-auto rounded-md">심층</span>
            </div>
            <div className="space-y-3.5 p-4">
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">모델</span>
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface border border-g-border rounded-lg">
                  <span className="text-[14px] font-mono text-g-text">Ollama / llama3.2</span>
                  <span className="text-[12px] text-g-muted ml-auto">JSON mode</span>
                </div>
              </div>
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">입력 컨텍스트</span>
                <div className="flex flex-wrap gap-2">
                  {["severity_score", "scene_description", "audio_events", "pose_angles"].map((f) => (
                    <span key={f} className="text-[12px] font-mono px-2 py-1 bg-g-surface text-g-blue rounded-md">{f}</span>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">폴백</span>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-g-green" />
                  <span className="text-[13px] text-g-text-secondary">예외 발생 → 규칙 기반 폴백 (Track 1)</span>
                </div>
              </div>
              <div>
                <span className="text-g-text-secondary text-[13px] font-medium block mb-1.5">토글</span>
                <div className="flex items-center gap-2 text-[13px]">
                  <span className="font-mono text-g-muted">use_llm_decision: bool</span>
                  <span className="text-g-muted">·</span>
                  <span className="font-mono text-g-muted">/api/agent_toggle</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Section 3: Escalation Agent ── */}
        <div className="bg-g-card border border-g-border rounded-xl">
          <div className="flex items-center gap-2.5 px-5 py-3.5 bg-g-surface/50 border-b border-g-border rounded-t-xl">
            <div className="w-2.5 h-2.5 rounded-full bg-g-red animate-pulse" />
            <h2 className="text-[16px] font-semibold text-g-text">비동기 에스컬레이션 에이전트</h2>
            <span className="text-[12px] text-g-muted ml-auto">ReAct pattern · agentic/agent/</span>
          </div>

          <div className="p-5 space-y-5">
            {/* Trigger flow */}
            <div>
              <span className="text-[13px] font-medium text-g-muted uppercase tracking-wider mb-3 block">발동 흐름</span>
              <div className="flex items-center gap-2.5">
                <div className="flex items-center gap-2 px-3.5 py-2.5 bg-g-surface border border-g-border rounded-xl">
                  <div className="w-2 h-2 rounded-full" style={{ background: V.red }} />
                  <span className="text-[14px] font-semibold text-g-text">ActionNode</span>
                  <span className="text-[12px] text-g-muted">사건 감지 완료</span>
                </div>
                <svg width="28" height="14" viewBox="0 0 28 14" className="text-g-border2 shrink-0">
                  <path d="M0 7h20M16 3l6 4-6 4" fill="none" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <div className="flex items-center gap-2 px-3.5 py-2.5 bg-g-surface border border-g-border rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-g-yellow" />
                  <span className="text-[14px] font-semibold text-g-text">심각도 확인</span>
                  <span className="text-[12px] text-g-muted">LOW → 종료</span>
                </div>
                <svg width="28" height="14" viewBox="0 0 28 14" className="text-g-orange shrink-0">
                  <path d="M0 7h20M16 3l6 4-6 4" fill="none" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <div className="flex items-center gap-2 px-3.5 py-2.5 border rounded-xl" style={{
                  background: "color-mix(in srgb, var(--color-g-red) 8%, transparent)",
                  borderColor: "color-mix(in srgb, var(--color-g-red) 30%, transparent)",
                }}>
                  <div className="w-2 h-2 rounded-full bg-g-red animate-pulse" />
                  <span className="text-[14px] font-bold text-g-red">에이전트 발동</span>
                  <span className="text-[12px] text-g-muted">백그라운드 스레드</span>
                </div>
                <svg width="28" height="14" viewBox="0 0 28 14" className="text-g-border2 shrink-0">
                  <path d="M0 7h20M16 3l6 4-6 4" fill="none" stroke="currentColor" strokeWidth="1.5" />
                </svg>
                <div className="flex items-center gap-2 px-3.5 py-2.5 bg-g-surface border border-g-border rounded-xl">
                  <div className="w-2 h-2 rounded-full bg-g-green" />
                  <span className="text-[14px] font-semibold text-g-text">결과 저장</span>
                  <span className="text-[12px] text-g-muted">agent_results DB</span>
                </div>
              </div>
              <p className="text-[13px] text-g-muted mt-3">
                주의(MEDIUM) 또는 위험(HIGH) 사건이 감지되면, 메인 파이프라인과 별도로 백그라운드에서 에이전트가 자동 실행됩니다. 에이전트는 과거 이력을 조회하고, 에스컬레이션 여부를 자율 판단합니다.
              </p>
            </div>

            <div className="border-t border-g-border" />

            {/* ReAct loop + tools */}
            <div className="grid grid-cols-[1fr_300px] gap-5">
              <div>
                <span className="text-[13px] font-medium text-g-muted uppercase tracking-wider mb-3 block">ReAct 추론 루프</span>
                <ReActLoop />
              </div>

              <div>
                <span className="text-[13px] font-medium text-g-muted uppercase tracking-wider mb-3 block">에이전트 도구</span>
                <div className="rounded-xl border border-g-border overflow-hidden">
                  {AGENT_TOOLS.map((t, i) => (
                    <div key={t.name} className={`px-4 py-3 bg-g-surface hover:bg-g-card transition-colors ${i < AGENT_TOOLS.length - 1 ? "border-b border-g-border" : ""}`}>
                      <div className="flex items-center gap-2.5">
                        <t.Icon className="w-4 h-4 shrink-0" style={{ color: t.color }} />
                        <span className="text-[13px] font-mono font-medium" style={{ color: t.color }}>{t.name}</span>
                      </div>
                      <p className="text-[13px] text-g-muted mt-1 ml-7">{t.desc}</p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t border-g-border space-y-2.5 text-[13px]">
                  {[
                    { label: "최대 반복", value: "4회" },
                    { label: "제한시간", value: "30초" },
                    { label: "LLM 폴백", value: "skip_llm=True (규칙)" },
                    { label: "저장소", value: "incidents.db → agent_results" },
                  ].map((row) => (
                    <div key={row.label} className="flex items-center justify-between text-g-muted">
                      <span>{row.label}</span>
                      <span className="font-mono text-g-text-secondary">{row.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Section 4: Data flow summary ── */}
        <div className="bg-g-card border border-g-border rounded-xl">
          <div className="flex items-center gap-2.5 px-5 py-3.5 bg-g-surface/50 border-b border-g-border rounded-t-xl">
            <div className="w-2.5 h-2.5 rounded-full bg-g-purple" />
            <h2 className="text-[16px] font-semibold text-g-text">데이터 흐름 요약</h2>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-5 gap-3">
              {[
                { label: "입력", items: ["MJPEG 스트림", "WAV 오디오", "카메라 ID"], color: V.muted },
                { label: "인지", items: ["키포인트 (17)", "각도 / 속도", "낙상 휴리스틱"], color: V.blue },
                { label: "퓨전", items: ["어텐션 가중치", "오디오 보너스", "VLM 컨텍스트"], color: V.orange },
                { label: "추론", items: ["OWL 분류", "Prolog 13규칙", "심각도 0-100"], color: V.purple },
                { label: "출력", items: ["DB 사건 기록", "Slack / Email", "에이전트 에스컬레이션"], color: V.red },
              ].map((col) => (
                <div key={col.label} className="text-center">
                  <div className="text-[14px] font-semibold uppercase tracking-wider mb-2.5" style={{ color: col.color }}>{col.label}</div>
                  <div className="space-y-1.5">
                    {col.items.map((item) => (
                      <div key={item} className="text-[13px] text-g-text-secondary px-3 py-2 bg-g-surface rounded-lg">{item}</div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <div className="flex items-center justify-center mt-4 gap-1">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="flex items-center">
                  <div className="w-20 h-[1.5px] bg-g-border2" />
                  <svg width="8" height="10" viewBox="0 0 8 10"><path d="M0 0L8 5L0 10Z" fill="var(--color-g-border2)" /></svg>
                  {i < 3 && <div className="w-6" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
