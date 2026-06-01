"use client";

import { LayoutDashboard, Camera, FileText, BarChart3, Bell, Settings } from "lucide-react";

const NAV_ITEMS = [
  { icon: LayoutDashboard, label: "Dashboard", active: true },
  { icon: Camera, label: "Cameras", active: false },
  { icon: FileText, label: "Incidents", active: false },
  { icon: BarChart3, label: "Analytics", active: false },
  { icon: Bell, label: "Alerts", active: false },
  { icon: Settings, label: "Settings", active: false },
];

export function Sidebar() {
  return (
    <aside className="w-14 shrink-0 bg-g-panel border-r border-g-border flex flex-col items-center py-3 gap-1.5">
      {/* Logo */}
      <div className="w-9 h-9 rounded bg-g-orange/15 flex items-center justify-center mb-4">
        <span className="text-g-orange text-sm font-bold">D</span>
      </div>

      {/* Nav icons */}
      <nav className="flex flex-col gap-1.5 flex-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            title={item.label}
            className={`w-10 h-10 rounded flex items-center justify-center transition-colors ${
              item.active
                ? "bg-g-orange/10 text-g-orange"
                : "text-g-muted hover:text-g-text hover:bg-g-border/30"
            }`}
          >
            <item.icon className="w-5 h-5" />
          </button>
        ))}
      </nav>

      {/* Bottom indicator */}
      <div className="w-2 h-2 rounded-full bg-g-green" title="System Online" />
    </aside>
  );
}
