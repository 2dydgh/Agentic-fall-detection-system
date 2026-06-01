import type { Stats } from "@/types";

export function StatsPanel({ stats, isAlert, audioEnabled, toggleAudio }: {
  stats: Stats;
  isAlert: boolean;
  audioEnabled: boolean;
  toggleAudio: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 p-4 h-full justify-center">
      <div className="grid grid-cols-3 gap-2">
        <div className="text-center">
          <p className="text-2xl font-bold text-g-text font-mono">{stats.total}</p>
          <span className="text-xs text-g-muted">Total</span>
        </div>
        <div className="text-center">
          <p className={`text-2xl font-bold font-mono ${isAlert ? "text-g-red" : "text-g-text"}`}>{stats.high}</p>
          <span className="text-xs text-g-muted">Critical</span>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-g-orange font-mono">{stats.medium}</p>
          <span className="text-xs text-g-muted">Warning</span>
        </div>
      </div>

      <div className="border-t border-g-border pt-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-g-muted">Audio</span>
          <button
            onClick={toggleAudio}
            className={`w-8 h-4 rounded-full transition-colors relative ml-auto ${audioEnabled ? "bg-g-green" : "bg-g-border2"}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${audioEnabled ? "translate-x-4" : ""}`} />
          </button>
        </div>
        <span className={`text-[11px] mt-1 block ${audioEnabled ? "text-g-green" : "text-g-muted"}`}>
          {audioEnabled ? "YAMNet active" : "Disabled"}
        </span>
      </div>
    </div>
  );
}
