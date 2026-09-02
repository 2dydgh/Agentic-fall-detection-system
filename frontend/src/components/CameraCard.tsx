import type { Incident } from "@/types";

type CameraCardProps = {
  id: string;
  label: string;
  video: string;
  audio: string;
  incidents: Incident[];
  compact?: boolean;
};

export function CameraCard({ id, label, video, audio, incidents, compact }: CameraCardProps) {
  const myIncidents = incidents.filter((inc) => inc.camera_id === id);
  const latest = myIncidents[0];
  const now = new Date().getTime();
  const recentMs = latest ? now - new Date(latest.timestamp).getTime() : Infinity;
  const isFallRecent = recentMs < 15000;
  const isAlert = isFallRecent && latest?.severity === "HIGH";
  const isMedium = isFallRecent && latest?.severity === "MEDIUM";
  const severity = latest?.severity;

  return (
    <div className={`relative overflow-hidden bg-g-bg transition-all h-full rounded-lg ${
      isAlert ? "border-2 border-g-red alert-pulse" : isMedium ? "border-2 border-g-orange" : "border border-g-border"
    }`}>
      <div className="absolute top-0 left-0 right-0 px-3 py-2 flex justify-between items-center z-10 bg-gradient-to-b from-black/80 to-transparent">
        <span className={`text-white font-semibold ${compact ? "text-[13px]" : "text-[14px]"}`}>CAM {id} · {label}</span>
        <span className={`font-semibold text-white px-2 py-0.5 text-[12px] rounded ${
          isAlert ? "bg-g-sev-high" : "bg-g-green/80"
        }`}>
          {isAlert ? "경고" : "정상"}
        </span>
      </div>

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/video_feed?video_path=${video}&audio_path=${audio}&camera_id=${id}`}
        alt={`${label} 피드`}
        className="w-full h-full object-contain"
      />

      {isFallRecent && latest && (
        <>
          <div className={`absolute inset-0 pointer-events-none alert-overlay ${isAlert ? "bg-g-red/15" : isMedium ? "bg-g-orange/10" : "bg-g-blue/10"}`} />
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
            {compact ? (
              <span className={`text-base font-bold px-3 py-1 text-white rounded ${
                isAlert ? "bg-g-sev-high alert-text" : isMedium ? "bg-g-sev-med" : "bg-g-surface"
              }`}>
                {severity === "HIGH" ? "위험" : severity === "MEDIUM" ? "주의" : "낮음"} · {latest.score}
              </span>
            ) : (
              <>
                <span className={`text-xl font-bold tracking-widest drop-shadow-lg ${isAlert ? "text-white alert-text" : isMedium ? "text-g-orange" : "text-g-text"}`}>
                  낙상 감지
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <span className={`text-base font-bold px-3 py-1 text-white ${
                    isAlert ? "bg-g-sev-high rounded" : isMedium ? "bg-g-sev-med rounded" : "bg-g-blue rounded"
                  }`}>
                    {severity === "HIGH" ? "위험" : severity === "MEDIUM" ? "주의" : "낮음"}
                  </span>
                  <span className="text-white text-base font-bold font-mono bg-black/60 px-2 py-1 rounded">
                    {latest.score}점
                  </span>
                </div>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
