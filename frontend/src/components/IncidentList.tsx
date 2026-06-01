import { Volume2, Zap } from "lucide-react";
import type { Incident } from "@/types";

export function IncidentList({ incidents }: { incidents: Incident[] }) {
  const recent = incidents.slice(0, 5);

  const severityColor = (s: string) =>
    s === "HIGH" ? "text-red-400" : s === "MEDIUM" ? "text-indigo-300" : "text-slate-400";
  const severityDot = (s: string) =>
    s === "HIGH" ? "bg-red-500" : s === "MEDIUM" ? "bg-indigo-500" : "bg-slate-500";
  const severityBar = (s: string) =>
    s === "HIGH" ? "bg-red-500" : s === "MEDIUM" ? "bg-indigo-500" : "bg-slate-500";

  return (
    <div className="flex flex-col h-full p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-white">Incidents</span>
        <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">{incidents.length}</span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5">
        {recent.length === 0 ? (
          <span className="text-xs text-slate-600">No incidents</span>
        ) : (
          recent.map((incident) => (
            <div key={incident.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/40">
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${severityDot(incident.severity)}`} />
              <span className={`text-[11px] font-semibold w-12 ${severityColor(incident.severity)}`}>{incident.severity}</span>
              <span className="text-[10px] text-slate-500 flex-1 truncate">
                {incident.timestamp.split("T")[1]?.substring(0, 8) || incident.timestamp.split(" ")[1] || incident.timestamp}
              </span>
              <div className="flex items-center gap-1">
                {incident.audio_scream && <Volume2 className="w-2.5 h-2.5 text-indigo-400" />}
                {incident.audio_impact && <Zap className="w-2.5 h-2.5 text-cyan-400" />}
              </div>
              <div className="w-10 h-1 bg-slate-700/50 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${severityBar(incident.severity)}`} style={{ width: `${incident.score}%` }} />
              </div>
              <span className={`text-[10px] font-medium w-5 text-right ${severityColor(incident.severity)}`}>{incident.score}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
