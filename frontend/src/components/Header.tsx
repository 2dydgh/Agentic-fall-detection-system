import type { Incident } from "@/types";
import { CAMERAS } from "@/types";

const CAMERA_LABELS: Record<string, string> = Object.fromEntries(
  CAMERAS.map((c) => [c.id, c.label])
);

export function Header({ isAlert, currentTime, alertIncidents }: {
  isAlert: boolean;
  currentTime: string;
  alertIncidents: Incident[];
}) {
  return (
    <header>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-g-border">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold text-g-orange tracking-wide">DETECT</span>
          <span className="text-sm text-g-muted">Agentic Fall Detection</span>
        </div>
        <div className="flex items-center gap-5">
          <span className="text-sm text-g-muted tabular-nums font-mono">{currentTime}</span>
          <div className={`flex items-center gap-2 text-sm font-semibold ${isAlert ? "text-g-red" : "text-g-green"}`}>
            <span className={`h-2.5 w-2.5 rounded-full ${isAlert ? "bg-g-red animate-pulse" : "bg-g-green"}`} />
            {isAlert ? "ALERT" : "Online"}
          </div>
        </div>
      </div>

      {isAlert && alertIncidents.length > 0 && (
        <div className="flex items-center justify-center gap-5 px-4 py-2 bg-g-red/10 border-b border-g-red/30">
          <span className="text-g-red text-sm font-bold tracking-widest alert-text">
            FALL DETECTED
          </span>
          {alertIncidents.map((inc) => (
            <span key={inc.id} className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full bg-g-red animate-pulse" />
              <span className="text-g-red font-semibold">CAM {inc.camera_id}</span>
              <span className="text-g-muted">{CAMERA_LABELS[inc.camera_id]}</span>
              <span className="text-g-red font-mono font-bold">{inc.score}</span>
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
