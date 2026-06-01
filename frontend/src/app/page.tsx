"use client";

import { useIncidents } from "@/hooks/useIncidents";
import { useAudioStatus } from "@/hooks/useAudioStatus";
import { useClock } from "@/hooks/useClock";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { CameraGrid } from "@/components/CameraGrid";
import { BottomBar } from "@/components/BottomBar";

export default function Home() {
  const stats = useIncidents();
  const { audioEnabled, toggleAudio } = useAudioStatus();
  const currentTime = useClock();

  const now = new Date().getTime();
  const alertIncidents = stats.logs.filter(
    (inc) => inc.severity === "HIGH" && (now - new Date(inc.timestamp).getTime() < 15000)
  );
  const isAlert = alertIncidents.length > 0;

  return (
    <div className="h-screen w-screen overflow-hidden bg-g-bg text-g-text flex font-[family-name:var(--font-sans)]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Header isAlert={isAlert} currentTime={currentTime} alertIncidents={alertIncidents} />
        <main className="flex-1 p-2 min-h-0">
          <CameraGrid incidents={stats.logs} />
        </main>
        <section className="h-[25vh] min-h-[160px] p-2 pt-0">
          <BottomBar
            stats={stats}
            isAlert={isAlert}
            audioEnabled={audioEnabled}
            toggleAudio={toggleAudio}
          />
        </section>
      </div>
    </div>
  );
}
