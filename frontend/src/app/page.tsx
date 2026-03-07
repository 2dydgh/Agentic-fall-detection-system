"use client";

import { useEffect, useState } from "react";
import { FileText, ShieldAlert, Cpu, Activity, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

type Incident = {
  id: string;
  timestamp: string;
  severity: string;
  score: number;
};

type Stats = {
  total: number;
  high: number;
  medium: number;
  logs: Incident[];
}

export default function Home() {
  const [stats, setStats] = useState<Stats>({ total: 0, high: 0, medium: 0, logs: [] });
  const [currentTime, setCurrentTime] = useState("");

  // Fetch incidents periodically
  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/incidents");
        const data = await res.json();
        if (data && Array.isArray(data.logs)) {
          setStats(data);
        }
      } catch (error) {
        console.error("Failed to fetch incidents:", error);
      }
    };

    fetchIncidents();
    const interval = setInterval(fetchIncidents, 2000);
    return () => clearInterval(interval);
  }, []);

  // Update real-time clock
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toLocaleString('en-US', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const hasHighSeverity = stats.logs.length > 0 &&
    stats.logs[0].severity === "HIGH" &&
    (new Date().getTime() - new Date(stats.logs[0].timestamp).getTime() < 10000); // 10 seconds

  return (
    <div className={`h-screen w-screen overflow-hidden bg-neutral-900 text-neutral-200 font-sans p-4 flex flex-col transition-colors duration-700 ${hasHighSeverity ? 'bg-red-950/20' : ''}`}>

      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between mb-6 pb-4 border-b border-neutral-700/60">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${hasHighSeverity ? 'bg-red-500/20 text-red-500 animate-pulse' : 'bg-blue-500/20 text-blue-500'}`}>
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-neutral-50 tracking-tight">CCTV Command Center</h1>
            <p className="text-xs text-neutral-400 font-medium tracking-wide uppercase mt-0.5">Agentic Fall Detection System</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-[0.65rem] text-neutral-400 font-semibold uppercase tracking-wider">Local Time</span>
            <span className="text-sm font-mono text-neutral-200">{currentTime}</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
            <div className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </div>
            <span className="text-xs font-semibold tracking-wide text-emerald-500">System Online</span>
          </div>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-4 xl:grid-cols-12 gap-6 min-h-0 overflow-hidden">

        {/* Left Stats Panel */}
        <section className="col-span-1 lg:col-span-1 xl:col-span-3 flex flex-col gap-4">
          <div className="bg-neutral-800/50 border border-neutral-700/60 rounded-2xl p-5 h-full flex flex-col shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <Activity className="w-4 h-4 text-blue-500" />
              <h2 className="text-sm font-semibold text-neutral-100 tracking-wide">Threat Metrics</h2>
            </div>

            <div className="flex flex-col gap-4">
              <div className="bg-neutral-900/50 border border-neutral-700/60 rounded-xl p-4">
                <p className="text-neutral-400 text-xs font-medium uppercase tracking-wider mb-1">Total Incidents</p>
                <div key={stats.total} className="animate-[fade-in_0.5s_ease-out]">
                  <p className="text-3xl font-semibold text-neutral-100">{stats.total}</p>
                </div>
              </div>

              <div className={`border rounded-xl p-4 transition-all duration-300 ${hasHighSeverity ? 'bg-red-500/10 border-red-500/30 shadow-[0_0_15px_rgba(239,68,68,0.1)]' : 'bg-neutral-900/50 border-neutral-700/60'}`}>
                <p className={`text-xs font-medium uppercase tracking-wider mb-1 ${hasHighSeverity ? 'text-red-400' : 'text-neutral-400'}`}>Critical Threats</p>
                <div className="flex items-baseline justify-between">
                  <div key={stats.high} className="animate-[fade-in_0.5s_ease-out]">
                    <p className={`text-3xl font-semibold ${hasHighSeverity ? 'text-red-500' : 'text-neutral-100'}`}>{stats.high}</p>
                  </div>
                  {hasHighSeverity && (
                    <div className="flex items-center gap-1.5 text-red-500">
                      <AlertTriangle className="w-4 h-4 animate-pulse" />
                      <span className="text-[0.65rem] font-bold tracking-wider">ACTIVE</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="bg-neutral-900/50 border border-neutral-700/60 rounded-xl p-4">
                <p className="text-amber-500/80 text-xs font-medium uppercase tracking-wider mb-1">Warnings</p>
                <div key={stats.medium} className="animate-[fade-in_0.5s_ease-out]">
                  <p className="text-3xl font-semibold text-amber-500/90">{stats.medium}</p>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-6">
              <div className="flex items-center justify-between text-[0.65rem] text-neutral-400 border-t border-neutral-700/50 pt-3 font-medium">
                <span className="flex items-center gap-1.5"><Cpu className="w-3 h-3" /> Core: FLORENCE-2</span>
                <span>Pose Engine: YOLOv11</span>
              </div>
            </div>
          </div>
        </section>

        {/* Center Multi-Camera & Terminal Log */}
        <section className="col-span-1 lg:col-span-2 xl:col-span-6 flex flex-col gap-4 min-h-0">

          {/* CAMERA GRID */}
          <div className="grid grid-cols-2 grid-rows-2 gap-4 flex-1 min-h-0">
            {/* CAMERA 01 */}
            <div className={`relative rounded-2xl overflow-hidden bg-neutral-900 border-2 transition-colors duration-500 shadow-xl col-span-1 row-span-1 h-full w-full min-h-0 ${hasHighSeverity ? 'border-red-500/50' : 'border-neutral-700/50'}`}>
              <div className="absolute top-0 left-0 w-full p-3 flex justify-between items-start z-10 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
                <div className="flex items-center gap-2 bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2.5 py-1">
                  <span className="flex h-1.5 w-1.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500"></span>
                  </span>
                  <span className="text-[0.65rem] font-medium text-neutral-100 tracking-wide uppercase">Cam 01 - Corridor</span>
                </div>
                <div className="bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2 py-1">
                  <span className="text-[0.6rem] font-mono text-blue-400">FPS: 24</span>
                </div>
              </div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="http://localhost:8000/video_feed?video_path=input/corridor.mp4"
                alt="Corridor Feed"
                className="w-full h-full object-contain"
              />

              {hasHighSeverity && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-500 text-white rounded-full px-4 py-1.5 text-xs font-bold tracking-wide animate-pulse shadow-lg flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  INCIDENT DETECTED
                </div>
              )}
            </div>

            {/* CAMERA 02 */}
            <div className={`relative rounded-2xl overflow-hidden bg-neutral-900 border-2 transition-colors duration-500 shadow-xl col-span-1 row-span-1 h-full w-full min-h-0 ${hasHighSeverity ? 'border-red-500/50' : 'border-neutral-700/50'}`}>
              <div className="absolute top-0 left-0 w-full p-3 flex justify-between items-start z-10 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
                <div className="flex items-center gap-2 bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2.5 py-1">
                  <span className="flex h-1.5 w-1.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500"></span>
                  </span>
                  <span className="text-[0.65rem] font-medium text-neutral-100 tracking-wide uppercase">Cam 02 - Hospital</span>
                </div>
                <div className="bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2 py-1">
                  <span className="text-[0.6rem] font-mono text-blue-400">FPS: 24</span>
                </div>
              </div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="http://localhost:8000/video_feed?video_path=input/hospital.mp4"
                alt="Hospital Feed"
                className="w-full h-full object-contain"
              />

              {hasHighSeverity && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-500 text-white rounded-full px-4 py-1.5 text-xs font-bold tracking-wide animate-pulse shadow-lg flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  INCIDENT DETECTED
                </div>
              )}
            </div>

            {/* CAMERA 03 */}
            <div className={`relative rounded-2xl overflow-hidden bg-neutral-900 border-2 transition-colors duration-500 shadow-xl col-span-1 row-span-1 h-full w-full min-h-0 ${hasHighSeverity ? 'border-red-500/50' : 'border-neutral-700/50'}`}>
              <div className="absolute top-0 left-0 w-full p-3 flex justify-between items-start z-10 bg-gradient-to-b from-black/80 to-transparent pointer-events-none">
                <div className="flex items-center gap-2 bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2.5 py-1">
                  <span className="flex h-1.5 w-1.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-red-500"></span>
                  </span>
                  <span className="text-[0.65rem] font-medium text-neutral-100 tracking-wide uppercase">Cam 03 - Street</span>
                </div>
                <div className="bg-neutral-900/40 backdrop-blur-md border border-neutral-600/50 rounded-lg px-2 py-1">
                  <span className="text-[0.6rem] font-mono text-blue-400">FPS: 30</span>
                </div>
              </div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="http://localhost:8000/video_feed?video_path=input/street.mp4"
                alt="Street Feed"
                className="w-full h-full object-contain"
              />

              {hasHighSeverity && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-500 text-white rounded-full px-4 py-1.5 text-xs font-bold tracking-wide animate-pulse shadow-lg flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  INCIDENT DETECTED
                </div>
              )}
            </div>
            {/* SYSTEM LOG (GRID QUADRANT 4) */}
            <div className="bg-neutral-800/40 border border-neutral-700/60 rounded-2xl p-4 flex flex-col col-span-1 row-span-1 h-full w-full min-h-0 shadow-sm relative z-0">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-neutral-300 tracking-wide uppercase">Event Log</span>
              <span className="text-[0.65rem] text-neutral-400 font-medium px-2 py-0.5 bg-neutral-700/50 rounded-full">Sync Active</span>
            </div>
            <div className="flex-1 overflow-y-auto font-mono text-[0.7rem] scrollbar-thin scrollbar-thumb-neutral-600 scrollbar-track-transparent">
              {stats.logs.map((log, index) => (
                <div key={index} className="mb-1.5 flex gap-3 items-start p-1.5 hover:bg-neutral-700/30 rounded-md transition-colors">
                  <span className="text-neutral-400 shrink-0">[{log.timestamp.split('T')[1] || log.timestamp.split(' ')[1] || log.timestamp}]</span>
                  <span className={`break-words ${log.severity === "HIGH" ? "text-red-400 font-medium" : log.severity === "MEDIUM" ? "text-amber-400 font-medium" : "text-neutral-200"}`}>
                    System Alert: Processed Event {log.id}. Status level evaluated to {log.severity} with AI Confidence {log.score}
                  </span>
                </div>
              ))}
              <div className="text-neutral-500 px-1 mt-1 animate-pulse">_</div>
            </div>
            </div>
          </div>
        </section>

        {/* Right Incident Log Section */}
        <section className="col-span-1 lg:col-span-1 xl:col-span-3 min-h-0">
          <div className="bg-neutral-800/50 border border-neutral-700/60 rounded-2xl flex flex-col h-full overflow-hidden shadow-sm">
            <div className="p-4 border-b border-neutral-700/60 bg-neutral-800/80 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-neutral-300" />
                <h2 className="text-sm font-semibold text-neutral-100 tracking-wide">Incident Registry</h2>
              </div>
              <Clock className="w-4 h-4 text-neutral-400" />
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin scrollbar-thumb-neutral-600 scrollbar-track-transparent">
              {stats.logs.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-neutral-400 gap-2">
                  <CheckCircle2 className="w-8 h-8 opacity-20" />
                  <p className="text-xs font-medium tracking-wide">No recent incidents</p>
                </div>
              ) : (
                stats.logs.map((incident) => (
                  <div
                    key={incident.id}
                    className={`p-3.5 rounded-xl border transition-all duration-300 shadow-sm ${incident.severity === "HIGH"
                      ? "bg-red-500/10 border-red-500/20 hover:border-red-500/40"
                      : incident.severity === "MEDIUM"
                        ? "bg-amber-500/5 border-amber-500/20 hover:border-amber-500/40"
                        : "bg-neutral-700/30 border-neutral-600/50 hover:border-neutral-500/50"
                      }`}
                  >
                    <div className="flex justify-between items-start mb-2.5">
                      <div className="flex items-center gap-2">
                        <span className={`flex w-2.5 h-2.5 rounded-full ${incident.severity === "HIGH" ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" : incident.severity === "MEDIUM" ? "bg-amber-500" : "bg-blue-500"}`}></span>
                        <span className="text-xs font-bold text-neutral-100">LVL_{incident.severity.substring(0, 3)}</span>
                      </div>
                      <span className="text-[0.65rem] font-medium text-neutral-300">
                        {incident.timestamp.split('T')[1]?.substring(0, 8) || incident.timestamp.split(' ')[1] || incident.timestamp}
                      </span>
                    </div>

                    <div className="flex flex-col gap-2.5">
                      <span className="text-neutral-300 text-[0.65rem] font-mono bg-neutral-900/50 px-2 py-1 rounded inline-block w-fit border border-neutral-700/80">
                        {incident.id.substring(4, 20)}...
                      </span>

                      <div>
                        <div className="flex justify-between items-center mb-1.5">
                          <span className="text-neutral-300 text-[0.7rem] font-medium">Confidence Score</span>
                          <span className={`font-bold text-xs ${incident.severity === "HIGH" ? "text-red-400" : incident.severity === "MEDIUM" ? "text-amber-400" : "text-neutral-200"}`}>
                            {incident.score.toString().padStart(3, '0')}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-neutral-700 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all duration-1000 ${incident.severity === "HIGH" ? "bg-red-500" : incident.severity === "MEDIUM" ? "bg-amber-500" : "bg-blue-500"}`} style={{ width: `${incident.score}%` }}></div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
