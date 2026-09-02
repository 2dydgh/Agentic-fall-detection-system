"use client";

import { useState } from "react";
import { useIncidents } from "@/hooks/useIncidents";
import { useAudioStatus } from "@/hooks/useAudioStatus";
import { useClock } from "@/hooks/useClock";
import { Sidebar, type PageId } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { CameraGrid } from "@/components/CameraGrid";
import { BottomBar } from "@/components/BottomBar";
import { IncidentsPage } from "@/components/IncidentsPage";
import { AnalyticsPage } from "@/components/AnalyticsPage";
import { OntologyPage } from "@/components/OntologyPage";
import { ArchitecturePage } from "@/components/ArchitecturePage";

export default function Home() {
  const [page, setPage] = useState<PageId>("dashboard");
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
      <Sidebar activePage={page} onNavigate={setPage} />
      <div className="flex-1 flex flex-col min-w-0">
        <Header isAlert={isAlert} currentTime={currentTime} alertIncidents={alertIncidents} />

        {page === "dashboard" && (
          <>
            <main className="flex-1 min-h-0">
              <CameraGrid incidents={stats.logs} />
            </main>
            <section className="h-[25vh] min-h-[160px]">
              <BottomBar
                stats={stats}
                isAlert={isAlert}
                audioEnabled={audioEnabled}
                toggleAudio={toggleAudio}
              />
            </section>
          </>
        )}

        {page === "incidents" && (
          <div className="flex-1 min-h-0">
            <IncidentsPage incidents={stats.logs} />
          </div>
        )}

        {page === "analytics" && (
          <div className="flex-1 min-h-0">
            <AnalyticsPage incidents={stats.logs} />
          </div>
        )}

        {page === "ontology" && (
          <div className="flex-1 min-h-0">
            <OntologyPage />
          </div>
        )}

        {page === "architecture" && (
          <div className="flex-1 min-h-0">
            <ArchitecturePage />
          </div>
        )}
      </div>
    </div>
  );
}
