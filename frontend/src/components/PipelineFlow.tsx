import { GitBranch, Bot } from "lucide-react";
import type { AgentResult } from "@/types";

export function PipelineFlow({ isAlert, agentResult }: { isAlert: boolean; agentResult?: AgentResult }) {
  const nodes = [
    { label: "Perception", desc: "YOLO11n", active: true, always: true },
    { label: "Audio", desc: "YAMNet", active: true, always: true },
    { label: "fall?", desc: "", active: true, isCondition: true, always: true },
    { label: "Analysis", desc: "Florence-2", active: isAlert, alert: isAlert },
    { label: "Decision", desc: "심각도 산출", active: isAlert, alert: isAlert },
    { label: "Action", desc: "DB·알림", active: isAlert, alert: isAlert },
  ];

  return (
    <div className="flex flex-col h-full p-4 justify-center">
      <div className="flex items-center gap-2 mb-3">
        <GitBranch className="w-4 h-4 text-indigo-400" />
        <span className="text-base font-medium text-white">Pipeline Flow</span>
        <span className={`text-sm px-2 py-0.5 rounded font-medium ml-auto ${isAlert ? "bg-red-500/10 text-red-400" : "bg-cyan-500/10 text-cyan-400"}`}>
          {isAlert ? "FALL DETECTED" : "MONITORING"}
        </span>
      </div>

      {/* Main pipeline row */}
      <div className="flex items-start gap-0">
        {nodes.map((node, i) => {
          const dotColor = node.active
            ? node.alert ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"
              : "bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.6)]"
            : "bg-slate-600";
          const textColor = node.active
            ? node.alert ? "text-red-300" : "text-indigo-300"
            : "text-slate-500";
          const descColor = node.active ? "text-slate-400" : "text-slate-600";
          const isLast = i === nodes.length - 1;
          const isConditionEdge = i === 2; // line after fall?

          return (
            <div key={i} className="flex items-start flex-1 min-w-0">
              <div className="flex flex-col items-center gap-0.5 w-full">
                <div className={`w-3 h-3 rounded-full ${dotColor} transition-all duration-500 ${node.isCondition ? "rotate-45 rounded" : ""}`} />
                <span className={`text-sm font-semibold whitespace-nowrap ${textColor}`}>{node.label}</span>
                {node.desc && <span className={`text-[12px] leading-tight ${descColor}`}>{node.desc}</span>}
                {node.always && !node.isCondition && <span className="text-[9px] text-indigo-400/50">always</span>}
                {node.isCondition && (
                  <span className={`text-[9px] ${isAlert ? "text-red-400/70" : "text-slate-500/70"}`}>
                    {isAlert ? "Yes ↓" : "No → END"}
                  </span>
                )}
              </div>
              {!isLast && (
                <div className={`w-full mt-1.5 shrink-0 ${isConditionEdge
                  ? isAlert ? "h-px bg-red-500/30 border-t border-dashed border-red-500/30" : "h-px bg-slate-700/20"
                  : node.active ? "h-px bg-indigo-500/40" : "h-px bg-slate-700/30"
                }`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Agent branch from Action */}
      <div className="flex items-center mt-2">
        {/* Spacer to align under Action */}
        <div className="flex-1" />
        <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/40 rounded-lg px-3 py-1.5">
          <div className={`w-px h-3 ${isAlert ? "bg-cyan-500/50" : "bg-slate-700/30"}`} />
          <Bot className={`w-3.5 h-3.5 ${isAlert ? "text-cyan-400" : "text-slate-600"}`} />
          <span className={`text-sm font-semibold ${isAlert ? "text-cyan-300" : "text-slate-500"}`}>Agent</span>
          <span className={`text-[12px] ${isAlert ? "text-slate-400" : "text-slate-600"}`}>ReAct async</span>
          {agentResult && (
            <>
              <span className="text-slate-600">·</span>
              <span className={`text-[12px] font-medium ${agentResult.escalation_needed ? "text-red-400" : "text-cyan-400"}`}>
                {agentResult.escalation_needed ? "Escalated" : "OK"}
              </span>
              <span className="text-[12px] text-slate-500">{agentResult.actions_taken.length} calls</span>
            </>
          )}
          {!agentResult && isAlert && (
            <span className="text-[12px] text-cyan-400/60 animate-pulse">...</span>
          )}
        </div>
      </div>
    </div>
  );
}
