"use client";

import { useEffect, useState } from "react";
import type { Incident } from "@/types";

const MODALITIES = [
  { key: "pose" as const, label: "자세", icon: "P", color: "var(--color-g-blue)" },
  { key: "audio" as const, label: "오디오", icon: "A", color: "var(--color-g-orange)" },
  { key: "vlm" as const, label: "시각", icon: "V", color: "var(--color-g-green)" },
];

function AnimatedBar({ value, color, delay }: { value: number; color: string; delay: number }) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setWidth(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return (
    <div className="h-2.5 bg-g-bg overflow-hidden flex-1">
      <div
        className="h-full transition-all duration-700 ease-out"
        style={{ width: `${width}%`, background: color }}
      />
    </div>
  );
}

export function AttentionPanel({ incidents }: { incidents: Incident[] }) {
  const latest = incidents.find((inc) => inc.attention_weights !== null);

  if (!latest || !latest.attention_weights) {
    return (
      <div className="flex flex-col h-full p-4 justify-center items-center">
        <span className="text-[15px] text-g-text-secondary font-medium">감지 비중</span>
        <span className="text-[13px] text-g-muted mt-1">데이터 없음</span>
      </div>
    );
  }

  const weights = latest.attention_weights;
  const maxWeight = Math.max(weights.pose, weights.audio, weights.vlm);
  const total = weights.pose + weights.audio + weights.vlm;

  const sevLabel = latest.severity === "HIGH" ? "위험" : latest.severity === "MEDIUM" ? "주의" : "낮음";
  const sevColor = latest.severity === "HIGH" ? "bg-g-sev-high" : latest.severity === "MEDIUM" ? "bg-g-sev-med" : "bg-g-sev-low";

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-g-border bg-g-surface/30">
        <span className="text-[15px] font-semibold text-g-text">감지 비중</span>
        <span className={`text-[13px] font-semibold text-white px-2 py-0.5 rounded-md ${sevColor}`}>
          {sevLabel} {latest.score}
        </span>
      </div>

      <div className="flex flex-col gap-3 flex-1 justify-center px-4 py-3">
        {MODALITIES.map((mod, i) => {
          const w = weights[mod.key];
          const pct = total > 0 ? (w / total) * 100 : 0;
          const isTop = w === maxWeight;

          return (
            <div key={mod.key} className="flex items-center gap-2.5">
              <div
                className="w-6 h-6 flex items-center justify-center text-[12px] font-bold text-white shrink-0 rounded"
                style={{ background: mod.color, opacity: isTop ? 1 : 0.4 }}
              >
                {mod.icon}
              </div>
              <AnimatedBar value={pct} color={mod.color} delay={i * 100} />
              <span
                className="text-[14px] font-mono w-10 text-right shrink-0 font-semibold"
                style={{ color: isTop ? mod.color : "var(--color-g-muted)" }}
              >
                {pct.toFixed(0)}%
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex gap-3 justify-center text-[12px] text-g-muted bg-g-surface py-1.5 mx-4 mb-3 rounded-md">
        {MODALITIES.map((mod) => (
          <span key={mod.key} className="flex items-center gap-1.5">
            <span className="w-2 h-2" style={{ background: mod.color }} />
            {mod.label}
          </span>
        ))}
      </div>
    </div>
  );
}
