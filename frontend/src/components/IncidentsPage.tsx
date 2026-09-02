"use client";

import { useState, useMemo } from "react";
import type { Incident } from "@/types";
import { CAMERAS } from "@/types";

const SEV_ORDER: Record<string, number> = { HIGH: 0, MEDIUM: 1, LOW: 2 };

function timeAgo(ts: string): string {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 10) return "방금";
  if (diff < 60) return `${diff}초 전`;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

function formatTs(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const camLabel = (id: string) =>
  CAMERAS.find((c) => c.id === id)?.label ?? id;

function AttentionBar({ value, total, color, label }: { value: number; total: number; color: string; label: string }) {
  const pct = total > 0 ? (value / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[13px] text-g-muted w-10">{label}</span>
      <div className="flex-1 h-2 bg-g-bg overflow-hidden max-w-[120px]">
        <div
          className="h-full transition-all duration-500"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-[13px] font-mono tabular-nums w-12 text-right" style={{ color }}>{pct.toFixed(1)}%</span>
    </div>
  );
}

export function IncidentsPage({ incidents }: { incidents: Incident[] }) {
  const [sevFilter, setSevFilter] = useState<string>("ALL");
  const [camFilter, setCamFilter] = useState<string>("ALL");
  const [sortKey, setSortKey] = useState<"time" | "score" | "severity">("time");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = useMemo(() => {
    let list = incidents;
    if (sevFilter !== "ALL") list = list.filter((i) => i.severity === sevFilter);
    if (camFilter !== "ALL") list = list.filter((i) => i.camera_id === camFilter);

    if (sortKey === "score") list = [...list].sort((a, b) => b.score - a.score);
    else if (sortKey === "severity")
      list = [...list].sort((a, b) => (SEV_ORDER[a.severity] ?? 3) - (SEV_ORDER[b.severity] ?? 3));

    return list;
  }, [incidents, sevFilter, camFilter, sortKey]);

  const sevBg = (s: string) =>
    s === "HIGH" ? "bg-g-sev-high text-white" : s === "MEDIUM" ? "bg-g-sev-med text-white" : "bg-g-surface text-g-text-secondary";

  const scoreColor = (s: string) =>
    s === "HIGH" ? "var(--color-g-red)" : s === "MEDIUM" ? "var(--color-g-orange)" : "var(--color-g-muted)";

  const uniqueCams = [...new Set(incidents.map((i) => i.camera_id))].sort();

  const highCount = incidents.filter((i) => i.severity === "HIGH").length;
  const medCount = incidents.filter((i) => i.severity === "MEDIUM").length;
  const lowCount = incidents.filter((i) => i.severity === "LOW").length;

  return (
    <div className="flex flex-col h-full p-4 gap-4 overflow-hidden">
      {/* Header + KPIs */}
      <div className="flex items-end justify-between shrink-0 pb-3 border-b border-g-border">
        <div>
          <h1 className="text-xl font-bold text-g-text">사건 기록</h1>
          <p className="text-base text-g-muted mt-0.5">총 {incidents.length}건 기록됨</p>
        </div>
        <div className="flex items-center gap-[1px] bg-g-border rounded-lg overflow-hidden">
          {[
            { label: "위험", count: highCount, color: "var(--color-g-red)" },
            { label: "주의", count: medCount, color: "var(--color-g-orange)" },
            { label: "낮음", count: lowCount, color: "var(--color-g-muted)" },
          ].map((s) => (
            <div key={s.label} className="flex items-center gap-2 px-3 py-1.5 bg-g-surface">
              <span className="w-2 h-2 rounded-full" style={{ background: s.color }} />
              <span className="font-mono font-semibold text-base tabular-nums" style={{ color: s.color }}>{s.count}</span>
              <span className="text-[13px] text-g-muted">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="flex items-center gap-0 bg-g-surface rounded-lg overflow-hidden">
          {["ALL", "HIGH", "MEDIUM", "LOW"].map((s) => (
            <button
              key={s}
              onClick={() => setSevFilter(s)}
              className={`px-2.5 py-1 text-[14px] font-medium transition-colors ${
                sevFilter === s ? "bg-g-orange text-white" : "text-g-muted hover:text-g-text"
              }`}
            >
              {s === "ALL" ? "전체" : s}
            </button>
          ))}
        </div>

        <select
          value={camFilter}
          onChange={(e) => setCamFilter(e.target.value)}
          className="bg-g-surface px-2.5 py-1.5 text-[14px] text-g-text cursor-pointer focus:outline-none border border-g-border rounded"
        >
          <option value="ALL">전체 카메라</option>
          {uniqueCams.map((c) => (
            <option key={c} value={c}>CAM {c} · {camLabel(c)}</option>
          ))}
        </select>

        <span className="text-[13px] text-g-muted ml-1">
          {filtered.length !== incidents.length && `${filtered.length} of `}{incidents.length}
        </span>

        <div className="flex items-center gap-0 ml-auto bg-g-surface rounded-lg overflow-hidden">
          {([["time", "시간"], ["score", "점수"], ["severity", "심각도"]] as const).map(([k, label]) => (
            <button
              key={k}
              onClick={() => setSortKey(k)}
              className={`px-2.5 py-1 text-[14px] font-medium transition-colors ${
                sortKey === k ? "bg-g-blue text-white" : "text-g-muted hover:text-g-text"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-y-auto min-h-0 border border-g-border rounded-xl overflow-hidden">
        <div className="grid grid-cols-[72px_110px_76px_64px_1fr_100px_130px] gap-2 px-3 py-2.5 text-[12px] text-g-muted uppercase tracking-wider bg-g-surface font-medium border-b border-g-border sticky top-0 z-10">
          <span>ID</span>
          <span>카메라</span>
          <span>심각도</span>
          <span>점수</span>
          <span>퓨전</span>
          <span>오디오</span>
          <span>시간</span>
        </div>

        {filtered.map((inc) => {
          const isOpen = expanded === inc.id;
          const total = inc.attention_weights
            ? inc.attention_weights.pose + inc.attention_weights.audio + inc.attention_weights.vlm
            : 0;

          return (
            <div key={inc.id}>
              <div
                onClick={() => setExpanded(isOpen ? null : inc.id)}
                className={`grid grid-cols-[72px_110px_76px_64px_1fr_100px_130px] gap-2 px-3 py-2.5 text-[15px] items-center cursor-pointer transition-colors border-b border-g-border/30 ${
                  isOpen ? "bg-g-surface" : "hover:bg-g-card"
                }`}
              >
                <span className="text-g-muted font-mono text-[13px] truncate" title={inc.id}>
                  {inc.id.slice(-6)}
                </span>
                <span className="flex items-center gap-1.5 text-g-text text-[14px]">
                  <span className="text-g-muted font-mono text-[12px]">{inc.camera_id}</span>
                  {camLabel(inc.camera_id)}
                </span>
                <span className={`text-[12px] font-semibold px-2 py-0.5 w-fit rounded ${sevBg(inc.severity)}`}>
                  {inc.severity}
                </span>
                <span className="font-mono font-semibold tabular-nums" style={{ color: scoreColor(inc.severity) }}>
                  {inc.score}
                </span>
                <div className="flex items-center gap-2">
                  {inc.attention_weights ? (
                    <>
                      <span className="text-[9px] px-1.5 py-0.5 bg-g-blue text-white font-mono font-semibold rounded">ATTN</span>
                      <div className="flex gap-[3px] flex-1 max-w-[100px]">
                        {(["pose", "audio", "vlm"] as const).map((k, i) => {
                          const colors = ["var(--color-g-blue)", "var(--color-g-orange)", "var(--color-g-green)"];
                          const pct = total > 0 ? (inc.attention_weights![k] / total) * 100 : 0;
                          return (
                            <div key={k} className="flex-1 h-[6px] bg-g-bg overflow-hidden" title={`${k}: ${pct.toFixed(1)}%`}>
                              <div
                                className="h-full transition-all duration-500"
                                style={{ width: `${pct}%`, background: colors[i] }}
                              />
                            </div>
                          );
                        })}
                      </div>
                    </>
                  ) : (
                    <span className="text-[9px] px-1.5 py-0.5 bg-g-surface text-g-muted font-mono rounded">RULE</span>
                  )}
                </div>
                <div className="flex gap-1.5">
                  {inc.audio_scream && <span className="text-[9px] px-1.5 py-0.5 bg-g-red/15 text-g-red font-semibold rounded">비명</span>}
                  {inc.audio_impact && <span className="text-[9px] px-1.5 py-0.5 bg-g-orange/15 text-g-orange font-semibold rounded">충격음</span>}
                  {!inc.audio_scream && !inc.audio_impact && <span className="text-g-muted text-[13px]">—</span>}
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[13px] text-g-muted flex-1" title={formatTs(inc.timestamp)}>{timeAgo(inc.timestamp)}</span>
                  <span className={`text-[9px] text-g-muted/30 transition-transform duration-200 ${isOpen ? "rotate-90" : ""}`}>&#9654;</span>
                </div>
              </div>

              {/* Expanded detail */}
              {isOpen && (
                <div className="border-b border-g-border">
                  <div className="px-5 py-4 bg-g-panel">
                    <div className="grid grid-cols-[1fr_1fr_1fr] gap-6 text-[14px]">
                      <div className="space-y-3">
                        <div>
                          <span className="text-g-muted text-[12px] uppercase tracking-wider block mb-1">사건 ID</span>
                          <span className="text-g-text font-mono text-[13px]">{inc.id}</span>
                        </div>
                        <div>
                          <span className="text-g-muted text-[12px] uppercase tracking-wider block mb-1">발생 시각</span>
                          <span className="text-g-text font-mono text-[13px]">{formatTs(inc.timestamp)}</span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div>
                          <span className="text-g-muted text-[12px] uppercase tracking-wider block mb-1">판정 모드</span>
                          <span className={`text-[12px] font-mono px-1.5 py-0.5 rounded ${
                            inc.decision_mode === "attention" ? "bg-g-blue text-white" : "bg-g-surface text-g-muted"
                          }`}>
                            {inc.decision_mode === "attention" ? "어텐션 퓨전" : "규칙 기반"}
                          </span>
                        </div>
                        <div>
                          <span className="text-g-muted text-[12px] uppercase tracking-wider block mb-1">오디오 신뢰도</span>
                          <div className="flex items-center gap-2">
                            <div className="flex-1 h-1.5 bg-g-bg overflow-hidden max-w-[80px]">
                              <div
                                className="h-full bg-g-orange"
                                style={{ width: `${inc.audio_confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-g-text font-mono text-[13px] tabular-nums">{(inc.audio_confidence * 100).toFixed(1)}%</span>
                          </div>
                        </div>
                      </div>

                      {inc.attention_weights && (
                        <div>
                          <span className="text-g-muted text-[12px] uppercase tracking-wider block mb-2.5">어텐션 가중치</span>
                          <div className="space-y-2">
                            <AttentionBar value={inc.attention_weights.pose} total={total} color="var(--color-g-blue)" label="자세" />
                            <AttentionBar value={inc.attention_weights.audio} total={total} color="var(--color-g-orange)" label="오디오" />
                            <AttentionBar value={inc.attention_weights.vlm} total={total} color="var(--color-g-green)" label="시각" />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="px-4 py-12 text-center">
            <span className="text-g-muted text-base">현재 필터에 일치하는 사건이 없습니다.</span>
          </div>
        )}
      </div>
    </div>
  );
}
