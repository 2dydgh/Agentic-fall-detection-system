"use client";

import { useState } from "react";
import type { Stats } from "@/types";
import { StatsPanel } from "./StatsPanel";
import { AttentionPanel } from "./AttentionPanel";
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
    <div className="flex h-full min-h-0 border-t border-g-border">
      <div className="w-[200px] shrink-0 bg-g-card border-r border-g-border overflow-hidden">
        <StatsPanel stats={stats} isAlert={isAlert} audioEnabled={audioEnabled} toggleAudio={toggleAudio} />
      </div>
      <div className="w-[240px] shrink-0 bg-g-card border-r border-g-border overflow-hidden">
        <AttentionPanel incidents={stats.logs} />
      </div>
      <div className="flex-1 min-w-0 bg-g-card overflow-hidden">
        <MonitorTable incidents={stats.logs} selectedCam={selectedCam} onSelectCam={setSelectedCam} />
      </div>
      <div className={`shrink-0 bg-g-card overflow-hidden border-l border-g-border history-panel ${selectedCam ? "history-panel-open" : "history-panel-closed"}`}>
        {selectedCam && (
          <HistoryPanel cameraId={selectedCam} incidents={stats.logs} onClose={() => setSelectedCam(null)} />
        )}
      </div>
    </div>
  );
}
