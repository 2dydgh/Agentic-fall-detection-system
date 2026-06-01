"use client";

import type { Incident } from "@/types";

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 10) return "just now";
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

const severityColor = (s: string) =>
  s === "HIGH" ? "text-g-red" : s === "MEDIUM" ? "text-g-orange" : "text-g-text-muted";

export function HistoryPanel({ cameraId, incidents, onClose }: {
  cameraId: string;
  incidents: Incident[];
  onClose: () => void;
}) {
  const camIncidents = incidents.filter((inc) => inc.camera_id === cameraId);

  return (
    <div className="flex flex-col h-full p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-semibold text-g-text">CAM {cameraId} History</span>
        <button onClick={onClose} className="text-xs text-g-blue hover:text-g-blue/80">
          Close
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1">
        {camIncidents.length === 0 ? (
          <span className="text-[11px] text-g-text-muted">No incidents</span>
        ) : (
          camIncidents.map((inc) => (
            <div key={inc.id} className="flex items-center gap-2 px-2 py-1.5 rounded-sm bg-g-bg border border-g-border/50 text-[11px]">
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${inc.severity === "HIGH" ? "bg-g-red" : inc.severity === "MEDIUM" ? "bg-g-orange" : "bg-g-border-light"}`} />
              <span className={`font-medium w-12 ${severityColor(inc.severity)}`}>{inc.severity}</span>
              <span className={`font-mono ${severityColor(inc.severity)} w-6`}>{inc.score}</span>
              {inc.audio_scream && <span className="text-[9px] text-g-orange">scream</span>}
              {inc.audio_impact && <span className="text-[9px] text-g-blue">impact</span>}
              <span className="text-g-text-muted ml-auto shrink-0">{timeAgo(inc.timestamp)}</span>
            </div>
          ))
        )}
      </div>

      {camIncidents.length > 0 && (
        <div className="pt-2 mt-2 border-t border-g-border text-[10px] text-g-text-muted">
          {camIncidents.length} incidents · Last: {timeAgo(camIncidents[0].timestamp)}
        </div>
      )}
    </div>
  );
}
