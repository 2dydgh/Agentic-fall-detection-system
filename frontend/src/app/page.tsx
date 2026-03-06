"use client";

import { useEffect, useState } from "react";
import { AlertCircle, FileText, Camera, ShieldAlert, Cpu, Activity, Clock, WifiOff } from "lucide-react";

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
      setCurrentTime(now.toLocaleString('en-US', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ' TST');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const hasHighSeverity = stats.logs.length > 0 &&
    stats.logs[0].severity === "HIGH" &&
    (new Date().getTime() - new Date(stats.logs[0].timestamp).getTime() < 10000); // 10 seconds

  return (
    <div className={`min-h-screen bg-black text-gray-300 font-mono p-4 flex flex-col transition-colors duration-1000 ${hasHighSeverity ? 'shadow-[inset_0_0_100px_rgba(255,0,0,0.15)] bg-red-950/10' : ''}`}>

      {/* Top Navigation Bar */}
      <header className="border-b border-cyan-900/50 pb-4 mb-4 flex items-center justify-between z-20">
        <div className="flex items-center gap-4 border border-cyan-800 bg-cyan-950/20 px-4 py-2 rounded-sm backdrop-blur-sm">
          <ShieldAlert className={`w-6 h-6 ${hasHighSeverity ? 'text-red-500 animate-pulse' : 'text-cyan-400'}`} />
          <h1 className="text-xl font-black tracking-[0.2em] text-white">AI FALL_DETECT_SYS</h1>
        </div>

        <div className="flex gap-4">
          <div className="flex flex-col items-end justify-center border border-cyan-900/50 px-4 py-1 bg-black/40">
            <span className="text-[0.6rem] text-gray-400 tracking-widest uppercase">System Time</span>
            <span className="text-sm text-white tracking-widest">{currentTime}</span>
          </div>
          <div className="flex items-center gap-3 border border-green-900/50 bg-green-950/20 px-4 py-1">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            <span className="text-xs font-bold tracking-widest text-green-400 uppercase">SYS_ONLINE</span>
          </div>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-4 xl:grid-cols-5 gap-4">

        {/* Left Stats Panel */}
        <section className="lg:col-span-1 flex flex-col gap-4">
          <div className="border border-cyan-900/50 bg-cyan-950/10 p-4 h-full relative overflow-hidden flex flex-col">
            <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,255,0.03)_1px,transparent_1px)] bg-[size:20px_20px] pointer-events-none"></div>

            <div className="flex items-center gap-2 mb-6 border-b border-cyan-900/50 pb-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs tracking-widest uppercase text-white font-bold">Threat Metrics</h2>
            </div>

            <div className="flex flex-col gap-6 relative z-10">
              <div className="bg-black/50 border border-cyan-900/30 p-4 shadow-[0_0_15px_rgba(0,255,255,0.05)]">
                <p className="text-gray-400 text-[0.65rem] uppercase tracking-widest mb-1">Total Monitored Incidents</p>
                <div key={stats.total} className="animate-[pulse_0.5s_ease-out]">
                  <p className="text-4xl text-white font-light tracking-wider">{stats.total.toString().padStart(3, '0')}</p>
                </div>
              </div>

              <div className={`bg-black/50 border p-4 transition-all duration-500 ${hasHighSeverity ? 'border-red-500/50 shadow-[0_0_20px_rgba(255,0,0,0.2)]' : 'border-cyan-900/30'}`}>
                <p className="text-red-900 text-[0.65rem] uppercase tracking-widest mb-1">Critical (Level 1) Events</p>
                <div className="flex items-baseline gap-2">
                  <div key={stats.high} className="animate-[pulse_0.5s_ease-out]">
                    <p className="text-4xl text-red-500 font-bold">{stats.high.toString().padStart(2, '0')}</p>
                  </div>
                  {hasHighSeverity && <span className="text-[0.6rem] text-red-500 animate-pulse tracking-widest">ACTIVE THREAT</span>}
                </div>
              </div>

              <div className="bg-black/50 border border-amber-900/30 p-4">
                <p className="text-amber-800 text-[0.65rem] uppercase tracking-widest mb-1">Warning (Level 2) Events</p>
                <div key={stats.medium} className="animate-[pulse_0.5s_ease-out]">
                  <p className="text-3xl text-amber-500 font-light">{stats.medium.toString().padStart(2, '0')}</p>
                </div>
              </div>
            </div>

            <div className="mt-auto pt-6">
              <div className="flex items-center justify-between text-[0.6rem] text-gray-500 border-t border-cyan-900/30 pt-2">
                <span>VLM Core: FLORENCE-2</span>
                <span>Pose: YOLOv8-N</span>
              </div>
            </div>
          </div>
        </section>

        {/* Center Multi-Camera & Terminal Log */}
        <section className="lg:col-span-2 xl:col-span-3 flex flex-col gap-4">

          {/* CAMERA GRID */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 h-[60vh]">
            {/* CAMERA 01: LIVING ROOM */}
            <div className={`relative group overflow-hidden border transition-colors duration-500 bg-[#050505] flex items-center justify-center ${hasHighSeverity ? 'border-red-900/50 shadow-[0_0_30px_rgba(255,0,0,0.1)]' : 'border-cyan-800/50 shadow-[0_0_30px_rgba(0,255,255,0.05)]'}`}>
              <div className="absolute top-0 w-full p-2 flex justify-between items-start z-10 pointer-events-none">
                <div className="bg-black/80 border border-cyan-800 px-2 py-1 flex items-center gap-2">
                  <span className="text-[0.55rem] text-white tracking-widest flex items-center gap-2 font-bold">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
                    ZONE_01_LIVING_RM
                  </span>
                </div>
                <div className="text-[0.55rem] text-gray-400 tracking-widest text-right flex flex-col items-end">
                  <span>FPS: 24.0</span>
                  <span className="text-cyan-400 flex items-center gap-1 mt-1"><Cpu className="w-2 h-2" /> YOLO_ACTIVE</span>
                </div>
              </div>

              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[1px] bg-cyan-500/10 z-10 pointer-events-none"></div>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[120%] w-[1px] bg-cyan-500/10 z-10 pointer-events-none"></div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="http://localhost:8000/video_feed?video_path=input/02342_H_A_BY_C5.mp4"
                alt="Living Room Feed"
                className={`w-full h-full object-contain transition-opacity duration-1000 ${hasHighSeverity ? 'opacity-90 grayscale-[20%] sepia-[30%] hue-rotate-[-50deg]' : 'opacity-80'}`}
              />
              {hasHighSeverity && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-950/80 border border-red-500 text-red-500 px-6 py-2 text-[0.6rem] font-bold tracking-[0.2em] animate-pulse z-20 backdrop-blur-sm">
                  CRITICAL EVENT DETECTED
                </div>
              )}
            </div>

            {/* CAMERA 02: CORRIDOR */}
            <div className={`relative group overflow-hidden border transition-colors duration-500 bg-[#050505] flex items-center justify-center ${hasHighSeverity ? 'border-red-900/50 shadow-[0_0_30px_rgba(255,0,0,0.1)]' : 'border-cyan-800/50 shadow-[0_0_30px_rgba(0,255,255,0.05)]'}`}>
              <div className="absolute top-0 w-full p-2 flex justify-between items-start z-10 pointer-events-none">
                <div className="bg-black/80 border border-cyan-800 px-2 py-1 flex items-center gap-2">
                  <span className="text-[0.55rem] text-white tracking-widest flex items-center gap-2 font-bold">
                    <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></span>
                    ZONE_02_CORRIDOR
                  </span>
                </div>
                <div className="text-[0.55rem] text-gray-400 tracking-widest text-right flex flex-col items-end">
                  <span>FPS: 24.0</span>
                  <span className="text-cyan-400 flex items-center gap-1 mt-1"><Cpu className="w-2 h-2" /> YOLO_ACTIVE</span>
                </div>
              </div>

              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[1px] bg-cyan-500/10 z-10 pointer-events-none"></div>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[120%] w-[1px] bg-cyan-500/10 z-10 pointer-events-none"></div>

              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="http://localhost:8000/video_feed?video_path=input/01491_O_F_BY_C8.mp4"
                alt="Corridor Feed"
                className={`w-full h-full object-contain transition-opacity duration-1000 ${hasHighSeverity ? 'opacity-90 grayscale-[20%] sepia-[30%] hue-rotate-[-50deg]' : 'opacity-80'}`}
              />
              {hasHighSeverity && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-950/80 border border-red-500 text-red-500 px-6 py-2 text-[0.6rem] font-bold tracking-[0.2em] animate-pulse z-20 backdrop-blur-sm">
                  CRITICAL EVENT DETECTED
                </div>
              )}
            </div>
          </div>

          {/* LIVE TERMINAL LOG */}
          <div className="flex-1 bg-[#020202] border border-cyan-900/50 p-3 flex flex-col overflow-hidden">
            <div className="border-b border-cyan-900/50 pb-2 mb-2 flex items-center justify-between pointer-events-none">
              <span className="text-[0.6rem] text-gray-300 tracking-widest uppercase inline-flex items-center gap-2 font-bold">
                &gt;_ SYSTEM_LOG_OUTPUT
              </span>
              <span className="text-[0.5rem] text-gray-500 font-mono animate-pulse">
                POLLING_DB_SYNC...
              </span>
            </div>
            <div className="flex-1 overflow-y-auto font-mono text-[0.65rem] scrollbar-thin scrollbar-thumb-cyan-900 text-gray-400">
              {stats.logs.map((log, index) => (
                <div key={index} className="mb-1 flex gap-2 w-full break-all">
                  <span className="text-gray-500">[{log.timestamp}]</span>
                  <span className={log.severity === "HIGH" ? "text-red-400 font-bold" : log.severity === "MEDIUM" ? "text-amber-400" : "text-gray-300"}>
                    {`[AGENT] Event ID: ${log.id} | Severity Evaluated: ${log.severity} (Score: ${log.score})`}
                  </span>
                </div>
              ))}
              <div className="text-gray-500 animate-pulse mt-1">&gt; _</div>
            </div>
          </div>
        </section>

        {/* Right Incident Log Section */}
        <section className="lg:col-span-1 border border-cyan-900/50 bg-cyan-950/5 flex flex-col h-[calc(100vh-6rem)] relative">

          <div className="p-3 border-b border-cyan-900/50 bg-black/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <h2 className="text-xs uppercase tracking-[0.2em] text-white font-bold">Incident Registry</h2>
            </div>
            <Clock className="w-3 h-3 text-cyan-400" />
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2 scrollbar-thin scrollbar-thumb-cyan-900 scrollbar-track-transparent">
            {stats.logs.length === 0 ? (
              <div className="text-center text-gray-500 text-xs tracking-widest flex items-center justify-center h-32 border border-dashed border-cyan-900/50 mx-2 mt-2">
                AWAITING_DATA //
              </div>
            ) : (
              stats.logs.map((incident) => (
                <div
                  key={incident.id}
                  className={`p-3 relative group transition-colors ${incident.severity === "HIGH"
                    ? "bg-red-950/10 border border-red-900/40 hover:bg-red-900/30"
                    : incident.severity === "MEDIUM"
                      ? "bg-amber-950/10 border border-amber-900/40 hover:bg-amber-900/20"
                      : "bg-cyan-950/10 border border-cyan-900/30 hover:bg-cyan-900/20"
                    }`}
                >
                  <div className={`absolute left-0 top-0 bottom-0 w-1 ${incident.severity === "HIGH" ? "bg-red-500 shadow-[0_0_10px_rgba(255,0,0,0.8)]" :
                    incident.severity === "MEDIUM" ? "bg-amber-500" : "bg-cyan-800"
                    }`}></div>

                  <div className="flex justify-between items-start mb-1 pl-2">
                    <span className={`text-[0.65rem] font-bold px-1.5 py-0.5 uppercase tracking-widest ${incident.severity === "HIGH"
                      ? "bg-red-500/20 text-red-400"
                      : incident.severity === "MEDIUM"
                        ? "bg-amber-500/20 text-amber-400"
                        : "bg-cyan-900/50 text-white"
                      }`}>
                      LVL_{incident.severity.substring(0, 3)}
                    </span>
                    <span className="text-[0.6rem] text-gray-400 font-mono">
                      {incident.timestamp.split(' ')[1] || incident.timestamp}
                    </span>
                  </div>
                  <div className="pl-2 mt-2 flex flex-col gap-1">
                    <span className="text-gray-400 text-[0.6rem] tracking-wider uppercase mb-0.5">ID: {incident.id.substring(4, 20)}...</span>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300 text-[0.7rem] uppercase">AI Confidence</span>
                      <span className={`font-bold text-xs ${incident.severity === "HIGH" ? "text-red-400" :
                        incident.severity === "MEDIUM" ? "text-amber-400" : "text-white"
                        }`}>{incident.score.toString().padStart(3, '0')}</span>
                    </div>
                    {/* Fake progress bar pattern */}
                    <div className="w-full h-1 bg-black overflow-hidden mt-1 flex border border-cyan-900/30">
                      <div className={`h-full opacity-80 ${incident.severity === "HIGH" ? "bg-red-500" :
                        incident.severity === "MEDIUM" ? "bg-amber-500" : "bg-cyan-500"
                        }`} style={{ width: `${incident.score}%` }}></div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
