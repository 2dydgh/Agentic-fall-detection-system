"use client";

import { useState } from "react";
import { LayoutDashboard, Camera, FileText, BarChart3, Bell, Settings, GitBranch, Layers } from "lucide-react";

export type PageId = "dashboard" | "incidents" | "analytics" | "ontology" | "architecture";

const NAV_ITEMS: { icon: typeof LayoutDashboard; label: string; ko: string; page: PageId | null }[] = [
  { icon: LayoutDashboard, label: "Dashboard", ko: "대시보드", page: "dashboard" },
  { icon: Camera, label: "Cameras", ko: "카메라", page: null },
  { icon: FileText, label: "Incidents", ko: "사건 기록", page: "incidents" },
  { icon: BarChart3, label: "Analytics", ko: "분석", page: "analytics" },
  { icon: GitBranch, label: "Ontology", ko: "온톨로지", page: "ontology" },
  { icon: Layers, label: "Architecture", ko: "시스템 구성", page: "architecture" },
  { icon: Bell, label: "Alerts", ko: "알림", page: null },
  { icon: Settings, label: "Settings", ko: "설정", page: null },
];

export function Sidebar({ activePage, onNavigate }: {
  activePage: PageId;
  onNavigate: (page: PageId) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <aside
      onMouseEnter={() => setExpanded(true)}
      onMouseLeave={() => setExpanded(false)}
      className={`shrink-0 bg-g-panel flex flex-col py-3 gap-0.5 border-r border-g-border transition-all duration-300 ease-in-out overflow-hidden ${
        expanded ? "w-[200px]" : "w-[48px]"
      }`}
    >
      <div className={`flex items-center mb-4 gap-3 ${expanded ? "px-3" : "px-0 justify-center"}`}>
        <div className="w-8 h-8 bg-g-bg border border-g-border flex items-center justify-center shrink-0 rounded-lg">
          <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
            <path d="M5 12 L5 5 L12 5" stroke="#6e9ef8" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M27 12 L27 5 L20 5" stroke="#6e9ef8" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M5 20 L5 27 L12 27" stroke="#6e9ef8" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M27 20 L27 27 L20 27" stroke="#6e9ef8" strokeWidth="2.5" strokeLinecap="round" />
            <g transform="translate(16,15.5) rotate(30)">
              <circle cx="0" cy="-5.5" r="2.8" fill="#e4e7ed" />
              <line x1="0" y1="-2.5" x2="0" y2="3.5" stroke="#e4e7ed" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="-3.5" y1="0" x2="3.5" y2="-0.5" stroke="#e4e7ed" strokeWidth="2" strokeLinecap="round" />
              <line x1="0" y1="3.5" x2="-3" y2="7.5" stroke="#e4e7ed" strokeWidth="2" strokeLinecap="round" />
              <line x1="0" y1="3.5" x2="2.5" y2="7" stroke="#e4e7ed" strokeWidth="2" strokeLinecap="round" />
            </g>
          </svg>
        </div>
        <div className={`flex flex-col transition-opacity duration-200 ${expanded ? "opacity-100" : "opacity-0 w-0"}`}>
          <span className="text-[15px] font-bold text-g-text tracking-wide whitespace-nowrap">DETECT</span>
          <span className="text-[9px] text-g-muted whitespace-nowrap">Agentic · Ontology</span>
        </div>
      </div>

      <nav className="flex flex-col gap-0 flex-1 w-full">
        {NAV_ITEMS.map((item) => {
          const isActive = item.page === activePage;
          const isDisabled = item.page === null;
          return (
            <button
              key={item.label}
              title={expanded ? undefined : item.ko}
              disabled={isDisabled}
              onClick={() => item.page && onNavigate(item.page)}
              className={`w-full flex items-center transition-colors relative ${
                expanded ? "px-3 py-2 gap-3" : "px-0 py-2.5 justify-center"
              } ${
                isActive
                  ? "bg-g-card text-g-text"
                  : isDisabled
                    ? "text-g-muted/40 cursor-not-allowed"
                    : "text-g-muted hover:text-g-text hover:bg-g-card cursor-pointer"
              }`}
            >
              {isActive && (
                <span className="absolute left-0 top-1 bottom-1 w-[2px] bg-g-orange" />
              )}
              <item.icon className={`w-[18px] h-[18px] shrink-0 ${!expanded ? "ml-0" : ""}`} />
              <span className={`text-[15px] whitespace-nowrap transition-opacity duration-200 ${
                expanded ? "opacity-100" : "opacity-0 w-0 overflow-hidden"
              } ${isActive ? "font-semibold" : "font-medium"}`}>
                {item.ko}
              </span>
            </button>
          );
        })}
      </nav>

      <div className={`flex items-center gap-2 mt-2 ${expanded ? "px-4" : "px-0 justify-center"}`}>
        <div className="w-2 h-2 rounded-full bg-g-green shrink-0" />
        <span className={`text-[13px] text-g-muted whitespace-nowrap transition-opacity duration-200 ${
          expanded ? "opacity-100" : "opacity-0 w-0 overflow-hidden"
        }`}>시스템 정상</span>
      </div>
    </aside>
  );
}
