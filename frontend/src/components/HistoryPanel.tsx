"use client";

import type { Incident } from "@/types";

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 10) return "방금";
  if (diff < 60) return `${diff}초 전`;
  if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}시간 전`;
  return `${Math.floor(diff / 86400)}일 전`;
}

const sevBadge = (s: string) =>
  s === "HIGH" ? "bg-g-sev-high text-white" : s === "MEDIUM" ? "bg-g-sev-med text-white" : "bg-g-surface text-g-text-secondary";

const sevLabel = (s: string) =>
  s === "HIGH" ? "위험" : s === "MEDIUM" ? "주의" : "낮음";

export function HistoryPanel({ cameraId, incidents, onClose }: {
  cameraId: string;
  incidents: Incident[];
  onClose: () => void;
}) {
  const camIncidents = incidents.filter((inc) => inc.camera_id === cameraId);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-g-border bg-g-surface/30 shrink-0">
        <span className="text-[15px] font-semibold text-g-text">CAM {cameraId} 이력</span>
        <button onClick={onClose} className="text-[13px] text-g-blue hover:text-g-blue/80 font-medium">
          닫기
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {camIncidents.length === 0 ? (
          <span className="text-[14px] text-g-muted">사건 기록 없음</span>
        ) : (
          camIncidents.map((inc) => (
            <div key={inc.id} className="flex flex-col gap-1.5 px-3 py-2 bg-g-surface text-[13px] border-b border-g-border/30">
              <div className="flex items-center gap-2">
                <span className={`text-[12px] font-semibold px-1.5 py-0.5 rounded ${sevBadge(inc.severity)}`}>{sevLabel(inc.severity)}</span>
                <span className="font-mono font-semibold text-g-text-secondary">{inc.score}</span>
                {inc.audio_scream && <span className="text-[12px] font-semibold text-g-red bg-g-red/15 px-1.5 py-0.5 rounded">비명</span>}
                {inc.audio_impact && <span className="text-[12px] font-semibold text-g-blue bg-g-blue/15 px-1.5 py-0.5 rounded">충격음</span>}
                <span className="text-g-muted ml-auto shrink-0">{timeAgo(inc.timestamp)}</span>
              </div>
              {inc.attention_weights && (
                <div className="flex items-center gap-1 ml-0.5">
                  {[
                    { key: "pose" as const, color: "var(--color-g-blue)" },
                    { key: "audio" as const, color: "var(--color-g-orange)" },
                    { key: "vlm" as const, color: "var(--color-g-green)" },
                  ].map(({ key, color }) => {
                    const total = inc.attention_weights!.pose + inc.attention_weights!.audio + inc.attention_weights!.vlm;
                    const pct = total > 0 ? (inc.attention_weights![key] / total) * 100 : 0;
                    return (
                      <div key={key} className="flex-1 h-1.5 bg-g-bg overflow-hidden">
                        <div className="h-full" style={{ width: `${pct}%`, background: color }} />
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {camIncidents.length > 0 && (
        <div className="pt-2 mt-2 border-t border-g-border text-[13px] text-g-muted">
          총 {camIncidents.length}건 · 마지막: {timeAgo(camIncidents[0].timestamp)}
        </div>
      )}
    </div>
  );
}
