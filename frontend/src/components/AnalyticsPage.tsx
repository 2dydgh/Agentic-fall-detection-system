"use client";

import { useState, useMemo } from "react";
import type { Incident } from "@/types";

/* ── Ontology data (from ontology.ttl) ── */
type OntologyNode = { id: string; label: string; children: OntologyNode[] };

const ONTOLOGY_TREE: OntologyNode[] = [
  {
    id: "incident", label: "Incident", children: [
      {
        id: "zone", label: "Zone", children: [
          {
            id: "high_risk_zone", label: "HighRiskZone", children: [
              {
                id: "wet_area", label: "WetArea", children: [
                  { id: "bathroom", label: "Bathroom", children: [] },
                  { id: "kitchen", label: "Kitchen", children: [] },
                ],
              },
              { id: "stairs", label: "Stairs", children: [] },
              { id: "balcony", label: "Balcony", children: [] },
            ],
          },
          {
            id: "normal_zone", label: "NormalZone", children: [
              { id: "hallway", label: "Hallway", children: [] },
              { id: "living_room", label: "LivingRoom", children: [] },
              { id: "bedroom", label: "Bedroom", children: [] },
            ],
          },
          {
            id: "unclassified_zone", label: "UnclassifiedZone", children: [
              { id: "outdoor", label: "Outdoor", children: [] },
              { id: "other_zone", label: "OtherZone", children: [] },
            ],
          },
        ],
      },
      {
        id: "person", label: "Person", children: [
          {
            id: "vulnerable_person", label: "VulnerablePerson", children: [
              { id: "elderly", label: "Elderly", children: [] },
              { id: "child", label: "Child", children: [] },
            ],
          },
          { id: "adult", label: "Adult", children: [] },
          { id: "unknown_person", label: "UnknownPerson", children: [] },
        ],
      },
      {
        id: "posture", label: "Posture", children: [
          { id: "collapsed", label: "Collapsed", children: [] },
          { id: "leaning", label: "Leaning", children: [] },
          { id: "upright", label: "Upright", children: [] },
        ],
      },
      {
        id: "audio_event", label: "AudioEvent", children: [
          {
            id: "distress_sound", label: "DistressSound", children: [
              { id: "scream", label: "Scream", children: [] },
            ],
          },
          { id: "impact_sound", label: "ImpactSound", children: [] },
        ],
      },
      {
        id: "severity_cls", label: "Severity", children: [
          { id: "high", label: "High", children: [] },
          { id: "medium", label: "Medium", children: [] },
          { id: "low", label: "Low", children: [] },
        ],
      },
      {
        id: "response_action", label: "ResponseAction", children: [
          { id: "log_action", label: "LogAction", children: [] },
          { id: "alert_action", label: "AlertAction", children: [] },
          { id: "emergency_action", label: "EmergencyAction", children: [] },
        ],
      },
    ],
  },
];

const T = {
  blue: "var(--color-g-blue)",
  green: "var(--color-g-green)",
  red: "var(--color-g-red)",
  orange: "var(--color-g-orange)",
  yellow: "var(--color-g-yellow)",
  purple: "var(--color-g-purple)",
  pink: "var(--color-g-pink)",
  muted: "var(--color-g-muted)",
};

const NODE_COLORS: Record<string, string> = {
  incident: T.orange,
  zone: T.blue,
  high_risk_zone: T.red, wet_area: T.red, bathroom: T.red, kitchen: T.red,
  stairs: T.red, balcony: T.red,
  normal_zone: T.green, hallway: T.green, living_room: T.green, bedroom: T.green,
  unclassified_zone: T.muted, outdoor: T.muted, other_zone: T.muted,
  person: T.yellow,
  vulnerable_person: T.pink, elderly: T.pink, child: T.pink,
  adult: T.green, unknown_person: T.muted,
  posture: T.purple, collapsed: T.red, leaning: T.yellow, upright: T.green,
  audio_event: T.orange, distress_sound: T.red, scream: T.red, impact_sound: T.yellow,
  severity_cls: T.blue, high: T.red, medium: T.yellow, low: T.green,
  response_action: T.purple, log_action: T.green, alert_action: T.yellow, emergency_action: T.red,
};

function TreeNode({ node, depth = 0, isLast = false }: { node: OntologyNode; depth?: number; isLast?: boolean }) {
  const [open, setOpen] = useState(depth < 2);
  const hasChildren = node.children.length > 0;
  const color = NODE_COLORS[node.id] ?? T.muted;
  const indent = depth * 20;

  return (
    <div className="relative">
      {depth > 0 && (
        <>
          <div
            className="absolute border-l border-g-border"
            style={{ left: `${indent - 10}px`, top: 0, height: isLast ? "14px" : "100%" }}
          />
          <div
            className="absolute border-t border-g-border"
            style={{ left: `${indent - 10}px`, top: "14px", width: "10px" }}
          />
        </>
      )}
      <div
        className="flex items-center gap-2 py-1 hover:bg-g-card px-1.5 cursor-pointer transition-colors relative"
        style={{ paddingLeft: `${indent + 4}px` }}
        onClick={() => hasChildren && setOpen(!open)}
      >
        {hasChildren ? (
          <span className={`text-[9px] text-g-muted w-3 text-center transition-transform duration-200 ${open ? "rotate-90" : ""}`}>&#9654;</span>
        ) : (
          <span className="w-3 text-center text-g-muted text-[8px]">&#9679;</span>
        )}
        <span className="w-2.5 h-2.5 shrink-0" style={{ background: color }} />
        <span className={`text-[15px] ${hasChildren ? "font-medium text-g-text" : "text-g-text-secondary"}`}>{node.label}</span>
        {hasChildren && (
          <span className="text-[12px] text-g-muted ml-0.5">{node.children.length}</span>
        )}
        {!hasChildren && (
          <span className="text-[9px] font-mono text-g-muted ml-auto mr-1">단말</span>
        )}
      </div>
      {open && hasChildren && (
        <div className="relative">
          {node.children.map((child, i) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} isLast={i === node.children.length - 1} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Stat tile ── */
function StatTile({ value, label, sub, color }: { value: string | number; label: string; sub?: string; color?: string }) {
  return (
    <div className="bg-g-surface border border-g-border p-3 rounded flex flex-col">
      <span className="text-[13px] text-g-muted uppercase tracking-wider">{label}</span>
      <span className="text-2xl font-bold font-mono mt-1" style={{ color: color ?? "var(--color-g-text)" }}>{value}</span>
      {sub && <span className="text-[12px] text-g-muted mt-0.5">{sub}</span>}
    </div>
  );
}

/* ── Severity bar chart ── */
function SeverityChart({ incidents }: { incidents: Incident[] }) {
  const counts = useMemo(() => {
    const h = incidents.filter((i) => i.severity === "HIGH").length;
    const m = incidents.filter((i) => i.severity === "MEDIUM").length;
    const l = incidents.filter((i) => i.severity === "LOW").length;
    const max = Math.max(h, m, l, 1);
    return [
      { label: "위험", count: h, pct: (h / max) * 100, color: T.red },
      { label: "주의", count: m, pct: (m / max) * 100, color: T.orange },
      { label: "낮음", count: l, pct: (l / max) * 100, color: T.green },
    ];
  }, [incidents]);

  return (
    <div className="flex flex-col gap-2.5">
      {counts.map((s) => (
        <div key={s.label} className="flex items-center gap-3">
          <span className="text-[13px] font-medium w-14 text-right tracking-wide" style={{ color: s.color }}>{s.label}</span>
          <div className="flex-1 h-[18px] bg-g-bg overflow-hidden">
            <div
              className="h-full transition-all duration-700 ease-out"
              style={{ width: `${s.pct}%`, background: s.color }}
            />
          </div>
          <span className="text-base font-mono w-10 text-right text-g-text tabular-nums">{s.count}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Decision mode donut ── */
function DecisionModeChart({ incidents }: { incidents: Incident[] }) {
  const attn = incidents.filter((i) => i.decision_mode === "attention").length;
  const rule = incidents.length - attn;
  const total = incidents.length || 1;
  const attnPct = (attn / total) * 100;
  const circumference = 2 * Math.PI * 14;

  return (
    <div className="flex items-center gap-8">
      <div className="relative w-[72px] h-[72px] shrink-0">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r="14" fill="none" stroke="var(--color-g-border)" strokeWidth="3.5" />
          <circle
            cx="18" cy="18" r="14" fill="none" stroke="var(--color-g-blue)" strokeWidth="3.5"
            strokeDasharray={`${(attnPct / 100) * circumference} ${circumference}`}
            strokeLinecap="round"
            className="transition-all duration-700"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[15px] font-bold font-mono text-g-text">{attnPct.toFixed(0)}%</span>
        </div>
      </div>
      <div className="flex flex-col gap-2.5 text-[15px] flex-1">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5" style={{ background: T.blue }} />
          <span className="text-g-text">어텐션 퓨전</span>
          <span className="text-g-muted font-mono ml-auto tabular-nums">{attn}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 bg-g-surface" />
          <span className="text-g-text">규칙 기반</span>
          <span className="text-g-muted font-mono ml-auto tabular-nums">{rule}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Attention weight averages ── */
function AttentionAvgChart({ incidents }: { incidents: Incident[] }) {
  const avg = useMemo(() => {
    const withAttn = incidents.filter((i) => i.attention_weights);
    if (withAttn.length === 0) return null;
    const sum = withAttn.reduce(
      (acc, i) => {
        const w = i.attention_weights!;
        return { pose: acc.pose + w.pose, audio: acc.audio + w.audio, vlm: acc.vlm + w.vlm };
      },
      { pose: 0, audio: 0, vlm: 0 },
    );
    const total = sum.pose + sum.audio + sum.vlm;
    return {
      pose: (sum.pose / total) * 100,
      audio: (sum.audio / total) * 100,
      vlm: (sum.vlm / total) * 100,
      count: withAttn.length,
    };
  }, [incidents]);

  if (!avg) return <span className="text-base text-g-muted">어텐션 데이터 없음</span>;

  const bars = [
    { key: "자세", pct: avg.pose, color: T.blue, model: "YOLO11n" },
    { key: "오디오", pct: avg.audio, color: T.orange, model: "YAMNet" },
    { key: "시각", pct: avg.vlm, color: T.green, model: "Florence-2" },
  ];

  return (
    <div className="flex flex-col gap-3">
      {bars.map((b) => (
        <div key={b.key}>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ background: b.color }} />
              <span className="text-[14px] font-medium text-g-text">{b.key}</span>
              <span className="text-[12px] text-g-muted font-mono">{b.model}</span>
            </div>
            <span className="text-[14px] font-mono tabular-nums" style={{ color: b.color }}>{b.pct.toFixed(1)}%</span>
          </div>
          <div className="h-[14px] bg-g-bg overflow-hidden">
            <div
              className="h-full transition-all duration-700 ease-out"
              style={{ width: `${b.pct}%`, background: b.color }}
            />
          </div>
        </div>
      ))}
      <span className="text-[12px] text-g-muted mt-0.5">
        어텐션 모드 {avg.count}건 기준
      </span>
    </div>
  );
}

/* ── Per-camera stacked bars ── */
function CameraChart({ incidents }: { incidents: Incident[] }) {
  const counts = useMemo(() => {
    const map: Record<string, { high: number; med: number; low: number }> = {};
    incidents.forEach((i) => {
      if (!map[i.camera_id]) map[i.camera_id] = { high: 0, med: 0, low: 0 };
      if (i.severity === "HIGH") map[i.camera_id].high++;
      else if (i.severity === "MEDIUM") map[i.camera_id].med++;
      else map[i.camera_id].low++;
    });
    return Object.entries(map)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([cam, c]) => ({ cam, ...c, total: c.high + c.med + c.low }));
  }, [incidents]);

  const maxTotal = Math.max(...counts.map((c) => c.total), 1);

  return (
    <div className="flex flex-col gap-2">
      {counts.map((c) => (
        <div key={c.cam} className="flex items-center gap-3">
          <span className="text-[13px] font-mono w-12 text-g-muted text-right">CAM {c.cam}</span>
          <div className="flex-1 h-[14px] bg-g-bg overflow-hidden flex gap-[2px]">
            {c.high > 0 && (
              <div className="h-full" style={{ width: `${(c.high / maxTotal) * 100}%`, background: T.red }} />
            )}
            {c.med > 0 && (
              <div className="h-full" style={{ width: `${(c.med / maxTotal) * 100}%`, background: T.orange }} />
            )}
            {c.low > 0 && (
              <div className="h-full" style={{ width: `${(c.low / maxTotal) * 100}%`, background: T.green }} />
            )}
          </div>
          <span className="text-[13px] font-mono w-8 text-right text-g-text tabular-nums">{c.total}</span>
        </div>
      ))}
      <div className="flex gap-4 mt-1">
        {[
          { label: "위험", color: T.red },
          { label: "주의", color: T.orange },
          { label: "낮음", color: T.green },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-1 text-[12px] text-g-muted">
            <span className="w-1.5 h-1.5 rounded-full" style={{ background: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ── Main page ── */
export function AnalyticsPage({ incidents }: { incidents: Incident[] }) {
  const attnCount = incidents.filter((i) => i.attention_weights).length;

  return (
    <div className="flex flex-col h-full p-4 gap-5 overflow-hidden">
      {/* Header + KPIs */}
      <div className="flex items-end justify-between shrink-0 pb-3 border-b border-g-border">
        <div>
          <h1 className="text-xl font-bold text-g-text">분석</h1>
          <p className="text-base text-g-muted mt-0.5">온톨로지 추론, 퓨전 분석, 사건 분포</p>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-4 gap-[1px] bg-g-border shrink-0">
        <StatTile value={incidents.length} label="전체 사건" sub="누적" />
        <StatTile value={incidents.filter((i) => i.severity === "HIGH").length} label="위험" color={T.red} sub="HIGH 등급" />
        <StatTile value={attnCount} label="어텐션 모드" color={T.blue} sub={`전체의 ${incidents.length ? ((attnCount / incidents.length) * 100).toFixed(0) : 0}%`} />
        <StatTile value={13} label="Prolog 규칙" color={T.purple} sub="6 HIGH + 7 MEDIUM" />
      </div>

      <div className="flex-1 grid grid-cols-[280px_1fr] gap-0 min-h-0 overflow-hidden border border-g-border rounded-xl">
        {/* Left: Ontology tree (compact) */}
        <div className="flex flex-col min-h-0 overflow-hidden bg-g-card border-r border-g-border">
          <div className="flex items-center gap-2 px-3 py-2.5 border-b border-g-border shrink-0 bg-g-surface/30">
            <div className="w-2 h-2 rounded-full bg-g-purple" />
            <span className="text-[14px] font-semibold text-g-text">온톨로지 계층</span>
            <span className="text-[11px] text-g-muted ml-auto">OWL</span>
          </div>

          <div className="flex-1 overflow-y-auto p-2.5">
            <div className="flex flex-wrap gap-2 mb-2.5 pb-2 border-b border-g-border">
              {[
                { label: "고위험", color: T.red },
                { label: "일반", color: T.green },
                { label: "취약", color: T.pink },
                { label: "오디오", color: T.orange },
                { label: "로직", color: T.purple },
                { label: "중립", color: T.muted },
              ].map((l) => (
                <span key={l.label} className="flex items-center gap-1 text-[11px] text-g-muted">
                  <span className="w-1.5 h-1.5" style={{ background: l.color }} />
                  {l.label}
                </span>
              ))}
            </div>
            {ONTOLOGY_TREE.map((node) => (
              <TreeNode key={node.id} node={node} />
            ))}
          </div>
        </div>

        {/* Right: Charts */}
        <div className="flex flex-col min-h-0 overflow-y-auto">
          <div className="bg-g-card border-b border-g-border">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-g-border/50 bg-g-surface/30">
              <div className="w-2 h-2 rounded-full" style={{ background: T.red }} />
              <h3 className="text-[15px] font-semibold text-g-text">심각도 분포</h3>
              <span className="text-[12px] text-g-muted font-mono ml-auto">건수</span>
            </div>
            <div className="p-4"><SeverityChart incidents={incidents} /></div>
          </div>

          <div className="bg-g-card border-b border-g-border">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-g-border/50 bg-g-surface/30">
              <div className="w-2 h-2 rounded-full" style={{ background: T.blue }} />
              <h3 className="text-[15px] font-semibold text-g-text">판정 모드</h3>
              <span className="text-[12px] text-g-muted font-mono ml-auto">어텐션 vs 규칙</span>
            </div>
            <div className="p-4"><DecisionModeChart incidents={incidents} /></div>
          </div>

          <div className="bg-g-card border-b border-g-border">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-g-border/50 bg-g-surface/30">
              <div className="w-2 h-2 rounded-full" style={{ background: T.orange }} />
              <h3 className="text-[15px] font-semibold text-g-text">평균 어텐션 가중치</h3>
              <span className="text-[12px] text-g-muted font-mono ml-auto">멀티모달 기여도</span>
            </div>
            <div className="p-4"><AttentionAvgChart incidents={incidents} /></div>
          </div>

          <div className="bg-g-card">
            <div className="flex items-center gap-2 px-4 py-2.5 border-b border-g-border/50 bg-g-surface/30">
              <div className="w-2 h-2 rounded-full" style={{ background: T.green }} />
              <h3 className="text-[15px] font-semibold text-g-text">카메라별 사건</h3>
              <span className="text-[12px] text-g-muted font-mono ml-auto">누적</span>
            </div>
            <div className="p-4"><CameraChart incidents={incidents} /></div>
          </div>
        </div>
      </div>
    </div>
  );
}
