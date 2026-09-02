import type { Stats } from "@/types";

export function StatsPanel({ stats, isAlert, audioEnabled, toggleAudio }: {
  stats: Stats;
  isAlert: boolean;
  audioEnabled: boolean;
  toggleAudio: () => void;
}) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-2.5 border-b border-g-border bg-g-surface/30 shrink-0">
        <span className="text-[15px] font-semibold text-g-text">사건 현황</span>
      </div>
      <div className="flex flex-col gap-2 p-3 flex-1 justify-center">
      <div className="grid grid-cols-3 gap-[1px] bg-g-border rounded-lg overflow-hidden">
        {[
          { value: stats.total, label: "전체", color: "text-g-text" },
          { value: stats.high, label: "위험", color: isAlert ? "text-g-red" : "text-g-text" },
          { value: stats.medium, label: "주의", color: "text-g-orange" },
        ].map((s) => (
          <div key={s.label} className="text-center bg-g-surface py-2">
            <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
            <span className="text-[13px] text-g-muted">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="bg-g-surface px-3 py-2 rounded-lg">
        <div className="flex items-center gap-2">
          <span className="text-[14px] text-g-text-secondary font-medium">소리 감지</span>
          <button
            onClick={toggleAudio}
            className={`w-9 h-5 rounded-full transition-colors relative ml-auto ${audioEnabled ? "bg-g-green" : "bg-g-border2"}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${audioEnabled ? "translate-x-4" : ""}`} />
          </button>
        </div>
        <span className={`text-[13px] mt-1 block ${audioEnabled ? "text-g-green" : "text-g-muted"}`}>
          {audioEnabled ? "소리 감지 켜짐" : "꺼짐"}
        </span>
      </div>
      </div>
    </div>
  );
}
