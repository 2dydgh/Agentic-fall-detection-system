"use client";

import { useState } from "react";
import type { Stats } from "@/types";
import { StatsPanel } from "./StatsPanel";
import { MonitorTable } from "./MonitorTable";
import { HistoryPanel } from "./HistoryPanel";

export function BottomBar({ stats, isAlert, audioEnabled, toggleAudio }: {
  stats: Stats;
  isAlert: boolean;
  audioEnabled: boolean;
  toggleAudio: () => void;
}) {
  const [selectedCam, setSelectedCam] = useState<string | null>(null);

  return (
    <div className="flex gap-2 h-full min-h-0">
      <div className="w-[200px] shrink-0 bg-g-panel border border-g-border rounded overflow-hidden">
        <StatsPanel stats={stats} isAlert={isAlert} audioEnabled={audioEnabled} toggleAudio={toggleAudio} />
      </div>
      <div className="flex-1 min-w-0 bg-g-panel border border-g-border rounded overflow-hidden">
        <MonitorTable incidents={stats.logs} selectedCam={selectedCam} onSelectCam={setSelectedCam} />
      </div>
      <div className={`shrink-0 bg-g-panel border rounded overflow-hidden history-panel ${selectedCam ? "history-panel-open border-g-blue/30" : "history-panel-closed border-transparent"}`}>
        {selectedCam && (
          <HistoryPanel cameraId={selectedCam} incidents={stats.logs} onClose={() => setSelectedCam(null)} />
        )}
      </div>
    </div>
  );
}
