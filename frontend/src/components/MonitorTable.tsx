"use client";

import { CAMERAS } from "@/types";
import type { Incident } from "@/types";

function timeAgo(timestamp: string): string {
  const diff = Math.floor((Date.now() - new Date(timestamp).getTime()) / 1000);
  if (diff < 10) return "just now";
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
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

  const severityColor = (s?: string) =>
    s === "HIGH" ? "text-g-red" : s === "MEDIUM" ? "text-g-orange" : "text-g-text-muted";

  return (
    <div className="flex flex-col h-full p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-base font-semibold text-g-text">Live Monitoring</span>
        <span className="text-sm text-g-muted font-mono">{incidents.length} total</span>
      </div>

      {/* Header */}
      <div className="grid grid-cols-[1fr_1.5fr_1.2fr_1fr_1.2fr_1fr] gap-2 px-2 py-1.5 text-xs text-g-muted uppercase tracking-wider border-b border-g-border">
        <span>CAM</span>
        <span>Location</span>
        <span>Severity</span>
        <span>Score</span>
        <span>When</span>
        <span>Total</span>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {cameraStatuses.map((cam) => {
          const isSelected = selectedCam === cam.id;
          const severity = cam.latest?.severity;
          const rowBg = cam.isActive && severity === "HIGH"
            ? "bg-g-red/5"
            : isSelected ? "bg-g-blue/5" : "";

          return (
            <div
              key={cam.id}
              onClick={() => onSelectCam(isSelected ? null : cam.id)}
              className={`grid grid-cols-[1fr_1.5fr_1.2fr_1fr_1.2fr_1fr] gap-2 px-2 py-2 text-sm items-center border-b border-g-border/50 cursor-pointer hover:bg-g-border/20 transition-colors ${rowBg} ${isSelected ? "border-l-2 border-l-g-blue" : ""}`}
            >
              <span className="text-g-text font-medium">{cam.id}</span>
              <span className="text-g-text-muted">{cam.label}</span>
              <span className="font-medium">
                {cam.latest ? (
                  <span className="flex items-center gap-1">
                    {cam.isActive && <span className="inline-block w-1.5 h-1.5 rounded-full bg-g-red animate-pulse" />}
                    <span className={severityColor(severity)}>{severity}</span>
                  </span>
                ) : <span className="text-g-border-light">—</span>}
              </span>
              <span className={`font-medium font-mono ${severityColor(severity)}`}>{cam.latest?.score || "—"}</span>
              <span className={`text-xs font-mono ${cam.isActive ? "text-g-red" : "text-g-muted"}`}>
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
