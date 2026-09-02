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
      <div className="flex items-center justify-between px-4 py-2 bg-g-panel border-b border-g-border">
        <div className="flex items-center gap-3">
          <span className="text-[14px] font-semibold text-g-text">Agentic Safety Intelligence</span>
          <span className="text-[12px] text-g-muted bg-g-surface px-1.5 py-0.5 font-mono rounded-md">Ontology · LangGraph</span>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-[14px] text-g-text-secondary tabular-nums font-mono">{currentTime}</span>
          <div className={`flex items-center gap-2 text-[14px] font-semibold px-2.5 py-1 rounded-md ${
            isAlert ? "bg-g-red/15 text-g-red" : "bg-g-surface text-g-green"
          }`}>
            <span className={`h-2 w-2 rounded-full ${isAlert ? "bg-g-red animate-pulse" : "bg-g-green"}`} />
            {isAlert ? "경고 발생" : "정상 운영"}
          </div>
        </div>
      </div>

      {isAlert && alertIncidents.length > 0 && (
        <div className="flex items-center justify-center gap-5 px-4 py-2 bg-g-sev-high border-b border-g-red/30">
          <span className="text-white text-[14px] font-bold tracking-widest">
            낙상 감지
          </span>
          {alertIncidents.map((inc) => (
            <span key={inc.id} className="flex items-center gap-2 text-[14px]">
              <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
              <span className="text-white font-semibold">CAM {inc.camera_id}</span>
              <span className="text-white/70">{CAMERA_LABELS[inc.camera_id]}</span>
              <span className="text-white font-mono font-bold">{inc.score}점</span>
            </span>
          ))}
        </div>
      )}
    </header>
  );
}
