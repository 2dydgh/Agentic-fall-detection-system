import { useEffect, useState } from "react";
import type { AgentResult } from "@/types";

export function useAgentResults() {
  const [agentResults, setAgentResults] = useState<AgentResult[]>([]);

  useEffect(() => {
    const fetchAgentResults = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/agent_results");
        const data = await res.json();
        if (data && Array.isArray(data.results)) setAgentResults(data.results);
      } catch { /* ignore */ }
    };
    fetchAgentResults();
    const interval = setInterval(fetchAgentResults, 3000);
    return () => clearInterval(interval);
  }, []);

  return agentResults;
}
