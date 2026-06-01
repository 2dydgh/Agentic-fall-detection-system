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

  const borderClass = isAlert
    ? "border-g-red border-2 alert-pulse"
    : isMedium
      ? "border-g-orange border-2"
      : "border-g-border";

  return (
    <div className={`relative rounded overflow-hidden bg-g-bg border transition-all h-full ${borderClass}`}>
      {/* Top bar */}
      <div className="absolute top-0 left-0 right-0 px-2 py-1 flex justify-between items-center z-10 bg-gradient-to-b from-black/70 to-transparent">
        <span className={`text-g-text font-medium ${compact ? "text-[11px]" : "text-xs"}`}>CAM {id} · {label}</span>
        <span className={`font-medium ${compact ? "text-[10px]" : "text-xs"} ${isAlert ? "text-g-red" : "text-g-green"}`}>
          {isAlert ? "ALERT" : "LIVE"}
        </span>
      </div>

      {/* Video feed */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`http://localhost:8000/video_feed?video_path=${video}&audio_path=${audio}&camera_id=${id}`}
        alt={`${label} Feed`}
        className="w-full h-full object-contain"
      />

      {/* Alert overlay */}
      {isFallRecent && latest && (
        <>
          <div className={`absolute inset-0 pointer-events-none alert-overlay ${isAlert ? "bg-g-red/15" : isMedium ? "bg-g-orange/10" : "bg-g-blue/10"}`} />
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none z-10">
            {compact ? (
              <span className={`text-sm font-bold tracking-wider ${isAlert ? "text-g-red alert-text" : "text-g-orange"}`}>
                {severity} · {latest.score}
              </span>
            ) : (
              <>
                <span className={`text-xl font-bold tracking-widest drop-shadow-lg ${isAlert ? "text-g-red alert-text" : isMedium ? "text-g-orange" : "text-g-text"}`}>
                  FALL DETECTED
                </span>
                <div className="flex items-center gap-3 mt-2">
                  <span className={`text-base font-semibold px-3 py-1 rounded-sm ${isAlert ? "bg-g-red text-white" : isMedium ? "bg-g-orange text-white" : "bg-g-blue text-white"}`}>
                    {severity}
                  </span>
                  <span className="text-white/90 text-base font-medium font-mono bg-black/60 px-2 py-1 rounded-sm">
                    {latest.score}/100
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
