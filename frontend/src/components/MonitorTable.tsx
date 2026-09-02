"use client";

import { CAMERAS } from "@/types";
import type { Incident } from "@/types";

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 10) return "방금";
  if (diff < 60) return `${diff}초 전`;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

export function MonitorTable({ incidents, selectedCam, onSelectCam }: {
  incidents: Incident[];
  selectedCam: string | null;
  onSelectCam: (id: string | null) => void;
}) {
  const cameraStatuses = CAMERAS.map((cam) => {
    const camIncidents = incidents.filter((inc) => inc.camera_id === cam.id);
    const latest = camIncidents[0];
    const recentMs = latest ? Date.now() - new Date(latest.timestamp).getTime() : Infinity;
    const isActive = recentMs < 15000;

    return {
      id: cam.id,
      label: cam.label,
      latest,
      isActive,
      totalIncidents: camIncidents.length,
    };
  });

  const sevBadge = (s?: string) =>
    s === "HIGH"
      ? "bg-g-sev-high text-white"
      : s === "MEDIUM"
        ? "bg-g-sev-med text-white"
        : s === "LOW"
          ? "bg-g-surface text-g-text-secondary"
          : "";

  const sevLabel = (s?: string) =>
    s === "HIGH" ? "위험" : s === "MEDIUM" ? "주의" : s === "LOW" ? "낮음" : "—";

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-g-border bg-g-surface/30">
        <span className="text-[15px] font-semibold text-g-text">실시간 모니터링</span>
        <span className="text-[13px] text-g-muted font-mono bg-g-surface px-2 py-0.5 rounded-md">{incidents.length}건</span>
      </div>

      <div className="grid grid-cols-[1fr_1.5fr_1fr_0.8fr_1.2fr_0.8fr] gap-2 px-3 py-1.5 text-[12px] text-g-muted uppercase tracking-wider bg-g-surface font-medium mb-[1px]">
        <span>카메라</span>
        <span>위치</span>
        <span>심각도</span>
        <span>점수</span>
        <span>시간</span>
        <span>누적</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {cameraStatuses.map((cam) => {
          const isSelected = selectedCam === cam.id;
          const severity = cam.latest?.severity;
          const rowBg = cam.isActive && severity === "HIGH"
            ? "bg-g-sev-high/10"
            : isSelected ? "bg-g-surface" : "hover:bg-g-card";

          return (
            <div
              key={cam.id}
              onClick={() => onSelectCam(isSelected ? null : cam.id)}
              className={`grid grid-cols-[1fr_1.5fr_1fr_0.8fr_1.2fr_0.8fr] gap-2 px-3 py-2 text-[14px] items-center cursor-pointer transition-colors border-b border-g-border/30 ${rowBg} ${isSelected ? "bg-g-surface" : ""}`}
            >
              <span className="text-g-text font-semibold">{cam.id}</span>
              <span className="text-g-text-secondary">{cam.label}</span>
              <span>
                {cam.latest ? (
                  <span className="flex items-center gap-1.5">
                    {cam.isActive && <span className="inline-block w-1.5 h-1.5 rounded-full bg-g-red animate-pulse" />}
                    <span className={`text-[12px] font-semibold px-1.5 py-0.5 rounded ${sevBadge(severity)}`}>{sevLabel(severity)}</span>
                  </span>
                ) : <span className="text-g-muted">—</span>}
              </span>
              <span className="font-semibold font-mono text-g-text-secondary">{cam.latest?.score || "—"}</span>
              <span className={`text-[13px] font-mono ${cam.isActive ? "text-g-red font-semibold" : "text-g-muted"}`}>
                {cam.latest ? timeAgo(cam.latest.timestamp) : "—"}
              </span>
              <span className="text-g-muted text-center font-mono">{cam.totalIncidents}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
