"use client";

import { useState } from "react";
import { CAMERAS } from "@/types";
import type { Incident } from "@/types";
import { CameraCard } from "./CameraCard";

export function CameraGrid({ incidents }: { incidents: Incident[] }) {
  const [focusedId, setFocusedId] = useState<string | null>(null);

  const handleClick = (id: string) => {
    setFocusedId(focusedId === id ? null : id);
  };

  if (focusedId) {
    const main = CAMERAS.find((c) => c.id === focusedId)!;
    const others = CAMERAS.filter((c) => c.id !== focusedId);

    return (
      <div className="grid grid-cols-[3fr_1fr] h-full min-h-0">
        <div className="cursor-pointer min-h-0 border-r border-g-border" onClick={() => handleClick(main.id)}>
          <CameraCard
            id={main.id}
            label={main.label}
            video={main.video}
            audio={main.audio}
            incidents={incidents}
          />
        </div>
        <div className="flex flex-col min-h-0">
          {others.map((cam, i) => (
            <div key={cam.id} className={`flex-1 min-h-0 cursor-pointer ${i > 0 ? "border-t border-g-border" : ""}`} onClick={() => handleClick(cam.id)}>
              <CameraCard
                id={cam.id}
                label={cam.label}
                video={cam.video}
                audio={cam.audio}
                incidents={incidents}
                compact
              />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 grid-rows-2 h-full min-h-0">
      {CAMERAS.map((cam, i) => (
        <div key={cam.id} className={`cursor-pointer ${
          i % 2 === 0 ? "border-r border-g-border" : ""
        } ${i < 2 ? "border-b border-g-border" : ""}`} onClick={() => handleClick(cam.id)}>
          <CameraCard
            id={cam.id}
            label={cam.label}
            video={cam.video}
            audio={cam.audio}
            incidents={incidents}
          />
        </div>
      ))}
    </div>
  );
}
