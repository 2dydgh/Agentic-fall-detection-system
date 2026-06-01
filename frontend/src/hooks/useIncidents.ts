import { useEffect, useState } from "react";
import type { Stats } from "@/types";

export function useIncidents() {
  const [stats, setStats] = useState<Stats>({ total: 0, high: 0, medium: 0, logs: [] });

  useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/incidents");
        const data = await res.json();
        if (data && Array.isArray(data.logs)) setStats(data);
      } catch (error) {
        console.error("Failed to fetch incidents:", error);
      }
    };
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 2000);
    return () => clearInterval(interval);
  }, []);

  return stats;
}
