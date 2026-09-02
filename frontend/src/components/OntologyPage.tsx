"use client";

import { useState, useMemo } from "react";

/* ═══════════════════════════════════════════════════════
   Ontology Reasoning — Simulator + Interactive Graph
   ═══════════════════════════════════════════════════════ */

/* ── Ontology options (simulator) ── */
const ZONES = [
  { id: "bathroom", label: "욕실", parent: "WetArea → HighRiskZone", risk: "high" as const },
  { id: "kitchen", label: "주방", parent: "WetArea → HighRiskZone", risk: "high" as const },
  { id: "stairs", label: "계단", parent: "HighRiskZone", risk: "high" as const },
  { id: "balcony", label: "발코니", parent: "HighRiskZone", risk: "high" as const },
  { id: "hallway", label: "복도", parent: "NormalZone", risk: "normal" as const },
  { id: "living_room", label: "거실", parent: "NormalZone", risk: "normal" as const },
  { id: "bedroom", label: "침실", parent: "NormalZone", risk: "normal" as const },
  { id: "outdoor", label: "야외", parent: "UnclassifiedZone", risk: "unclassified" as const },
];

const PERSONS = [
  { id: "elderly", label: "고령자", parent: "VulnerablePerson", vulnerable: true },
  { id: "child", label: "아동", parent: "VulnerablePerson", vulnerable: true },
  { id: "adult", label: "성인", parent: "Person", vulnerable: false },
  { id: "unknown", label: "미확인", parent: "UnknownPerson", vulnerable: false },
];

const POSTURES = [
  { id: "collapsed", label: "붕괴", color: "var(--color-g-red)" },
  { id: "leaning", label: "기울임", color: "var(--color-g-orange)" },
  { id: "upright", label: "직립", color: "var(--color-g-green)" },
];

const AUDIO_EVENTS = [
  { id: "none", label: "없음", color: "var(--color-g-muted)" },
  { id: "scream", label: "비명", color: "var(--color-g-red)" },
  { id: "impact", label: "충격음", color: "var(--color-g-orange)" },
  { id: "both", label: "비명 + 충격음", color: "var(--color-g-red)" },
];

/* ── Rules ── */
type SimContext = {
  zone: typeof ZONES[number];
  person: typeof PERSONS[number];
  posture: typeof POSTURES[number];
  audio: typeof AUDIO_EVENTS[number];
  duration: number;
  priorIncident: boolean;
};

type Rule = { id: string; severity: "HIGH" | "MEDIUM"; desc: string; prolog: string; check: (c: SimContext) => boolean };

const RULES: Rule[] = [
  { id: "R1", severity: "HIGH", desc: "고위험 구역 + 무동작 ≥ 30s", prolog: "in_zone(I, high_risk_zone), no_movement_duration(I, S), S >= 30", check: (c) => c.zone.risk === "high" && c.duration >= 30 },
  { id: "R2", severity: "HIGH", desc: "취약 계층 + 비명", prolog: "is_vulnerable(I), has_audio_event(I, scream)", check: (c) => c.person.vulnerable && (c.audio.id === "scream" || c.audio.id === "both") },
  { id: "R3", severity: "HIGH", desc: "무동작 ≥ 60s", prolog: "no_movement_duration(I, S), S >= 60", check: (c) => c.duration >= 60 },
  { id: "R4", severity: "HIGH", desc: "붕괴 + 충격음 + 무동작 ≥ 20s", prolog: "has_posture(I, collapsed), has_audio_event(I, impact_sound), no_movement_duration(I, S), S >= 20", check: (c) => c.posture.id === "collapsed" && (c.audio.id === "impact" || c.audio.id === "both") && c.duration >= 20 },
  { id: "R5", severity: "HIGH", desc: "취약 계층 + 고위험 구역 + 무동작 ≥ 15s", prolog: "is_vulnerable(I), in_zone(I, high_risk_zone), no_movement_duration(I, S), S >= 15", check: (c) => c.person.vulnerable && c.zone.risk === "high" && c.duration >= 15 },
  { id: "R6", severity: "HIGH", desc: "재낙상(5분↑) + 무동작 ≥ 10s", prolog: "prior_incident(_, _, M), M >= 5, no_movement_duration(I, S), S >= 10", check: (c) => c.priorIncident && c.duration >= 10 },
  { id: "R7", severity: "MEDIUM", desc: "고위험 구역 + 무동작 10~30s", prolog: "in_zone(I, high_risk_zone), no_movement_duration(I, S), S >= 10, S < 30", check: (c) => c.zone.risk === "high" && c.duration >= 10 && c.duration < 30 },
  { id: "R8", severity: "MEDIUM", desc: "비명 감지", prolog: "has_audio_event(I, scream)", check: (c) => c.audio.id === "scream" || c.audio.id === "both" },
  { id: "R9", severity: "MEDIUM", desc: "취약 계층 + 무동작 ≥ 15s", prolog: "is_vulnerable(I), no_movement_duration(I, S), S >= 15", check: (c) => c.person.vulnerable && c.duration >= 15 },
  { id: "R10", severity: "MEDIUM", desc: "붕괴 + 무동작 ≥ 10s", prolog: "has_posture(I, collapsed), no_movement_duration(I, S), S >= 10", check: (c) => c.posture.id === "collapsed" && c.duration >= 10 },
  { id: "R11", severity: "MEDIUM", desc: "충격음 + 붕괴 자세", prolog: "has_audio_event(I, impact_sound), has_posture(I, collapsed)", check: (c) => (c.audio.id === "impact" || c.audio.id === "both") && c.posture.id === "collapsed" },
  { id: "R12", severity: "MEDIUM", desc: "위험물 + 붕괴 자세", prolog: "has_hazard(I, _), has_posture(I, collapsed)", check: () => false },
  { id: "R13", severity: "MEDIUM", desc: "재낙상(5분↑ 경과)", prolog: "prior_incident(_, _, M), M >= 5", check: (c) => c.priorIncident },
];

const RESPONSE_ACTIONS: Record<string, { label: string; actions: string[] }> = {
  HIGH: { label: "EmergencyAction", actions: ["119 긴급 호출", "보안실 알림", "Slack/Email 전송", "스냅샷 저장", "DB 기록"] },
  MEDIUM: { label: "AlertAction", actions: ["보안실 알림", "Slack 전송", "DB 기록", "스냅샷 저장"] },
  LOW: { label: "LogAction", actions: ["DB 기록"] },
  NONE: { label: "—", actions: ["모니터링 유지"] },
};

const RISK_COLORS = { high: "var(--color-g-red)", normal: "var(--color-g-green)", unclassified: "var(--color-g-muted)" };

const PRESETS = [
  { label: "욕실 낙상(고령자)", zone: 0, person: 0, posture: 0, audio: 2, duration: 25, prior: false },
  { label: "계단 비명(아동)", zone: 2, person: 1, posture: 1, audio: 1, duration: 5, prior: false },
  { label: "거실 장시간 무동작", zone: 5, person: 2, posture: 0, audio: 0, duration: 65, prior: false },
  { label: "복도 재낙상", zone: 4, person: 0, posture: 0, audio: 2, duration: 12, prior: true },
  { label: "정상 상태", zone: 5, person: 2, posture: 2, audio: 0, duration: 0, prior: false },
];

/* ══════════════════════════════════════════════════════
   Interactive Graph — Tree layout + Bezier + Hover
   ══════════════════════════════════════════════════════ */

type GNode = { id: string; label: string; color: string; children: GNode[] };
type PNode = { id: string; label: string; color: string; x: number; y: number; children: PNode[] };

const C = {
  blue: "var(--color-g-blue)", green: "var(--color-g-green)", red: "var(--color-g-red)",
  orange: "var(--color-g-orange)", yellow: "var(--color-g-yellow)", purple: "var(--color-g-purple)",
  pink: "var(--color-g-pink)", muted: "var(--color-g-muted)",
};

const GRAPH_TREE: GNode = {
  id: "incident", label: "Incident", color: C.orange, children: [
    { id: "zone", label: "Zone", color: C.blue, children: [
      { id: "hrz", label: "HighRiskZone", color: C.red, children: [
        { id: "wetarea", label: "WetArea", color: C.red, children: [] },
        { id: "stairs", label: "Stairs", color: C.red, children: [] },
        { id: "balcony", label: "Balcony", color: C.red, children: [] },
      ] },
      { id: "nz", label: "NormalZone", color: C.green, children: [
        { id: "hallway", label: "Hallway", color: C.green, children: [] },
        { id: "living", label: "LivingRoom", color: C.green, children: [] },
        { id: "bedroom", label: "Bedroom", color: C.green, children: [] },
      ] },
    ] },
    { id: "person", label: "Person", color: C.yellow, children: [
      { id: "vp", label: "VulnerablePerson", color: C.pink, children: [
        { id: "elderly", label: "Elderly", color: C.pink, children: [] },
        { id: "child_p", label: "Child", color: C.pink, children: [] },
      ] },
      { id: "adult_p", label: "Adult", color: C.green, children: [] },
    ] },
    { id: "posture", label: "Posture", color: C.purple, children: [
      { id: "collapsed_p", label: "Collapsed", color: C.red, children: [] },
      { id: "leaning_p", label: "Leaning", color: C.orange, children: [] },
      { id: "upright_p", label: "Upright", color: C.green, children: [] },
    ] },
    { id: "audio_ev", label: "AudioEvent", color: C.orange, children: [
      { id: "distress", label: "DistressSound", color: C.red, children: [
        { id: "scream_a", label: "Scream", color: C.red, children: [] },
      ] },
      { id: "impact_a", label: "ImpactSound", color: C.orange, children: [] },
    ] },
    { id: "severity_c", label: "Severity", color: C.blue, children: [
      { id: "sev_h", label: "High", color: C.red, children: [] },
      { id: "sev_m", label: "Medium", color: C.orange, children: [] },
      { id: "sev_l", label: "Low", color: C.green, children: [] },
    ] },
    { id: "response", label: "ResponseAction", color: C.purple, children: [
      { id: "emergency_a", label: "Emergency", color: C.red, children: [] },
      { id: "alert_a", label: "Alert", color: C.orange, children: [] },
      { id: "log_a", label: "Log", color: C.green, children: [] },
    ] },
  ],
};

const LEAF_W = 52;
const SIB_GAP = 6;
const GRP_GAP = 18;
const LVL_H = 68;
const NH = 24;

function tw(n: GNode, root = false): number {
  if (!n.children.length) return LEAF_W;
  const g = root ? GRP_GAP : SIB_GAP;
  return n.children.reduce((s, c, i) => s + tw(c) + (i ? g : 0), 0);
}

function posTree(n: GNode, l: number, t: number, root = false): PNode {
  const w = tw(n, root);
  const g = root ? GRP_GAP : SIB_GAP;
  const cs: PNode[] = [];
  let x = l;
  for (let i = 0; i < n.children.length; i++) {
    cs.push(posTree(n.children[i], x, t + LVL_H));
    x += tw(n.children[i]) + (i < n.children.length - 1 ? g : 0);
  }
  const cx = cs.length ? (cs[0].x + cs[cs.length - 1].x) / 2 : l + w / 2;
  return { id: n.id, label: n.label, color: n.color, x: cx, y: t, children: cs };
}

function allEdges(n: PNode): { f: PNode; t: PNode }[] {
  return n.children.flatMap((c) => [{ f: n, t: c }, ...allEdges(c)]);
}
function allNodes(n: PNode): PNode[] {
  return [n, ...n.children.flatMap(allNodes)];
}

function pathTo(n: PNode, id: string, trail: string[] = []): string[] | null {
  const t = [...trail, n.id];
  if (n.id === id) return t;
  for (const c of n.children) { const r = pathTo(c, id, t); if (r) return r; }
  return null;
}

function descs(n: PNode): string[] {
  return [n.id, ...n.children.flatMap(descs)];
}

function InteractiveGraph() {
  const [hovered, setHovered] = useState<string | null>(null);

  const root = useMemo(() => posTree(GRAPH_TREE, 24, 32, true), []);
  const edges = useMemo(() => allEdges(root), [root]);
  const nodes = useMemo(() => allNodes(root), [root]);

  const hl = useMemo(() => {
    if (!hovered) return null;
    const path = pathTo(root, hovered) ?? [];
    const hovNode = nodes.find((n) => n.id === hovered);
    const desc = hovNode ? descs(hovNode) : [];
    return new Set([...path, ...desc]);
  }, [hovered, root, nodes]);

  const totalW = tw(GRAPH_TREE, true) + 48;
  const maxDepth = (() => { let d = 0; function walk(n: GNode, lv: number) { d = Math.max(d, lv); n.children.forEach((c) => walk(c, lv + 1)); } walk(GRAPH_TREE, 0); return d; })();
  const totalH = maxDepth * LVL_H + 72;

  return (
    <div className="bg-g-card border border-g-border p-4 overflow-x-auto">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-[14px] font-semibold text-g-text">개념 관계도</h2>
        <span className="text-[12px] text-g-muted ml-auto">각 항목에 마우스를 올리면 관련 개념이 강조됩니다</span>
      </div>

      <svg viewBox={`0 0 ${totalW} ${totalH}`} className="w-full min-w-[700px]" preserveAspectRatio="xMidYMin meet">
        {edges.map((e, i) => {
          const on = hl ? hl.has(e.f.id) && hl.has(e.t.id) : false;
          const my = (e.f.y + NH / 2 + e.t.y - NH / 2) / 2;
          return (
            <path
              key={i}
              d={`M${e.f.x},${e.f.y + NH / 2} C${e.f.x},${my} ${e.t.x},${my} ${e.t.x},${e.t.y - NH / 2}`}
              fill="none"
              stroke={on ? e.t.color : "var(--color-g-border2)"}
              strokeWidth={on ? 2.2 : 1.2}
              opacity={hl ? (on ? 0.9 : 0.12) : 0.7}
              style={{ transition: "all 0.35s ease" }}
            />
          );
        })}

        {nodes.map((n) => {
          const on = hl ? hl.has(n.id) : true;
          const isHov = hovered === n.id;
          const textW = n.label.length * 6.8 + 20;
          return (
            <g
              key={n.id}
              onMouseEnter={() => setHovered(n.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ cursor: "pointer" }}
            >
              <rect
                x={n.x - textW / 2} y={n.y - NH / 2}
                width={textW} height={NH} rx={3}
                fill={on ? `color-mix(in srgb, ${n.color} 15%, transparent)` : "var(--color-g-surface)"}
                stroke={on ? `color-mix(in srgb, ${n.color} 20%, transparent)` : "transparent"}
                strokeWidth={isHov ? 1.5 : 0.5}
                opacity={hl ? (on ? 1 : 0.1) : 0.8}
                style={{ transition: "all 0.35s ease" }}
              />
              <text
                x={n.x} y={n.y + 4}
                textAnchor="middle"
                fill={on ? n.color : "var(--color-g-border)"}
                fontSize={n.children.length > 0 ? "9.5" : "9"}
                fontWeight={n.children.length > 0 ? "600" : "400"}
                fontFamily="Pretendard Variable, sans-serif"
                opacity={hl ? (on ? 1 : 0.12) : 0.85}
                style={{ transition: "all 0.35s ease", pointerEvents: "none" }}
              >
                {n.label}
              </text>
              {isHov && (
                <text
                  x={n.x} y={n.y + NH / 2 + 12}
                  textAnchor="middle" fill={n.color} fontSize="7.5"
                  fontFamily="Roboto Mono, monospace" opacity="0.5"
                  style={{ pointerEvents: "none" }}
                >
                  {n.children.length > 0 ? `하위 개념 ${n.children.length}개` : "최하위 개념"}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <div className="flex flex-wrap gap-5 mt-3 pt-3 border-t border-g-border justify-center">
        {[
          { label: "구역", color: C.blue }, { label: "고위험", color: C.red },
          { label: "정상", color: C.green }, { label: "인물", color: C.yellow },
          { label: "취약", color: C.pink }, { label: "자세", color: C.purple },
          { label: "오디오", color: C.orange },
        ].map((l) => (
          <span key={l.label} className="flex items-center gap-2 text-[14px] text-g-text-secondary font-medium">
            <span className="w-3 h-3 rounded" style={{ background: l.color }} />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   Shared UI Components
   ══════════════════════════════════════════════════════ */

function OptionButton({ selected, onClick, children, color }: {
  selected: boolean; onClick: () => void; children: React.ReactNode; color?: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-[14px] font-medium transition-all rounded ${
        selected ? "" : "bg-g-surface text-g-muted hover:text-g-text hover:bg-g-surface/80"
      }`}
      style={selected ? { color: color ?? C.orange, background: `color-mix(in srgb, ${color ?? C.orange} 15%, transparent)`, boxShadow: `inset 0 0 0 1px color-mix(in srgb, ${color ?? C.orange} 25%, transparent)` } : undefined}
    >
      {children}
    </button>
  );
}

/* ══════════════════════════════════════════════════════
   Main Page
   ══════════════════════════════════════════════════════ */
export function OntologyPage() {
  const [zoneIdx, setZoneIdx] = useState(0);
  const [personIdx, setPersonIdx] = useState(0);
  const [postureIdx, setPostureIdx] = useState(0);
  const [audioIdx, setAudioIdx] = useState(0);
  const [duration, setDuration] = useState(25);
  const [priorIncident, setPriorIncident] = useState(false);
  const [activeTab, setActiveTab] = useState<"simulator" | "graph">("simulator");

  const zone = ZONES[zoneIdx];
  const person = PERSONS[personIdx];
  const posture = POSTURES[postureIdx];
  const audio = AUDIO_EVENTS[audioIdx];
  const ctx: SimContext = { zone, person, posture, audio, duration, priorIncident };

  const firedRules = useMemo(() => RULES.filter((r) => r.check(ctx)), [ctx]);
  const finalSeverity = useMemo(() => {
    if (firedRules.some((r) => r.severity === "HIGH")) return "HIGH";
    if (firedRules.some((r) => r.severity === "MEDIUM")) return "MEDIUM";
    if (posture.id === "collapsed" || duration > 0) return "LOW";
    return "NONE";
  }, [firedRules, posture.id, duration]);

  const responseAction = RESPONSE_ACTIONS[finalSeverity];
  const hasActivity = posture.id !== "upright" || audio.id !== "none" || duration > 0 || priorIncident;

  const applyPreset = (p: typeof PRESETS[number]) => {
    setZoneIdx(p.zone); setPersonIdx(p.person); setPostureIdx(p.posture);
    setAudioIdx(p.audio); setDuration(p.duration); setPriorIncident(p.prior);
  };

  return (
    <div className="flex flex-col h-full p-4 gap-5 overflow-hidden">
      <div className="flex items-end justify-between shrink-0 pb-3 border-b border-g-border">
        <div>
          <h1 className="text-xl font-bold text-g-text">온톨로지 추론</h1>
          <p className="text-base text-g-muted mt-0.5">시스템이 낙상 상황을 어떤 기준으로 판단하는지 확인할 수 있습니다</p>
        </div>
        <div className="flex items-center bg-g-surface border border-g-border rounded-lg overflow-hidden">
          {(["simulator", "graph"] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-3 py-1.5 text-[14px] font-medium transition-colors ${
                activeTab === tab ? "bg-g-orange text-white" : "text-g-muted hover:text-g-text"
              }`}>
              {tab === "simulator" ? "상황별 시뮬레이션" : "개념 관계도"}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "graph" ? (
        <div className="flex-1 min-h-0 overflow-auto space-y-3">
          <InteractiveGraph />

          <div className="grid grid-cols-3 gap-3">
            <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-g-surface/50 border-b border-g-border">
                <h3 className="text-[15px] font-semibold text-g-text">계층 추론</h3>
                <p className="text-[12px] text-g-muted mt-0.5">하위 개념이 상위 개념의 특성을 물려받는 구조</p>
              </div>
              <div className="p-4">
                <div className="flex items-center gap-2 text-[14px] text-g-text-secondary mb-3">
                  <span className="px-2 py-0.5 bg-g-red/15 text-g-red rounded text-[13px]">욕실</span>
                  <span className="text-g-muted">→</span>
                  <span className="px-2 py-0.5 bg-g-red/10 text-g-red/70 rounded text-[13px]">물 사용 구역</span>
                  <span className="text-g-muted">→</span>
                  <span className="px-2 py-0.5 bg-g-red/8 text-g-red/50 rounded text-[13px]">고위험 구역</span>
                </div>
                <p className="text-[13px] text-g-muted leading-relaxed">
                  욕실에서 사건이 발생하면, 시스템은 자동으로 "물 사용 구역"과 "고위험 구역"의 규칙까지 함께 적용합니다.
                </p>
                <pre className="text-[12px] text-g-blue/60 leading-relaxed whitespace-pre-wrap mt-3 px-3 py-2 bg-g-surface rounded-lg">
{`kind_of(X, Y) :- is_a(X, Y).
kind_of(X, Y) :-
    is_a(X, Z), kind_of(Z, Y).`}
                </pre>
              </div>
            </div>

            <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-g-surface/50 border-b border-g-border">
                <h3 className="text-[15px] font-semibold text-g-text">심각도 판정</h3>
                <p className="text-[12px] text-g-muted mt-0.5">발동된 규칙 중 가장 높은 등급이 최종 결과</p>
              </div>
              <div className="p-4">
                <div className="flex items-center gap-3 mb-3">
                  {[
                    { label: "위험", color: "bg-g-sev-high", desc: "즉시 대응" },
                    { label: "주의", color: "bg-g-sev-med", desc: "알림 전송" },
                    { label: "낮음", color: "bg-g-surface", desc: "기록만" },
                  ].map((s, i) => (
                    <div key={s.label} className="flex items-center gap-2">
                      {i > 0 && <span className="text-g-muted text-[12px]">&gt;</span>}
                      <span className={`text-[13px] font-semibold px-2 py-0.5 rounded text-white ${s.color}`}>{s.label}</span>
                    </div>
                  ))}
                </div>
                <p className="text-[13px] text-g-muted leading-relaxed">
                  13개 규칙 중 하나라도 "위험"에 해당하면 최종 결과는 위험입니다. 위험이 없으면 "주의"를 확인하고, 둘 다 없으면 "낮음"으로 판정합니다.
                </p>
                <pre className="text-[12px] text-g-blue/60 leading-relaxed whitespace-pre-wrap mt-3 px-3 py-2 bg-g-surface rounded-lg">
{`severity(I, high) :- fired(I, _, high), !.
severity(I, medium) :- fired(I, _, medium), !.
severity(I, low).`}
                </pre>
              </div>
            </div>

            <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-g-surface/50 border-b border-g-border">
                <h3 className="text-[15px] font-semibold text-g-text">추론 흐름</h3>
                <p className="text-[12px] text-g-muted mt-0.5">사건 발생부터 대응까지 4단계</p>
              </div>
              <div className="p-4 flex flex-col gap-2.5">
                {[
                  { n: "1", title: "사실 생성", desc: "카메라가 감지한 정보를 온톨로지 개념으로 변환", color: C.orange },
                  { n: "2", title: "규칙 로드", desc: "13개 판단 규칙을 Prolog 엔진에 로드", color: C.purple },
                  { n: "3", title: "추론 실행", desc: "조건에 맞는 규칙을 자동으로 찾아 발동", color: C.blue },
                  { n: "4", title: "대응 결정", desc: "최종 심각도에 따라 알림/호출 등 조치 실행", color: C.green },
                ].map((step) => (
                  <div key={step.n} className="flex items-start gap-3">
                    <span className="w-7 h-7 rounded-lg flex items-center justify-center text-[13px] font-bold shrink-0" style={{
                      background: `color-mix(in srgb, ${step.color} 15%, transparent)`,
                      color: step.color,
                    }}>{step.n}</span>
                    <div>
                      <span className="text-[14px] font-semibold text-g-text">{step.title}</span>
                      <p className="text-[12px] text-g-muted mt-0.5">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ── Simulator — Bento Grid ── */
        <div className="flex-1 min-h-0 overflow-y-auto space-y-3">
          {/* Scenario Quick Start */}
          <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-2.5 bg-g-surface/50 border-b border-g-border">
              <div className="w-2 h-2 rounded-full bg-g-orange" />
              <span className="text-[15px] font-semibold text-g-text">시나리오 바로가기</span>
              <span className="text-[12px] text-g-muted ml-auto">클릭하면 아래 조건이 자동으로 설정됩니다</span>
            </div>
            <div className="flex gap-2 p-3">
              {PRESETS.map((p, i) => {
                const isActive = zoneIdx === p.zone && personIdx === p.person && postureIdx === p.posture && audioIdx === p.audio && duration === p.duration && priorIncident === p.prior;
                return (
                  <button key={i} onClick={() => applyPreset(p)}
                    className={`flex-1 px-3 py-2.5 text-[14px] font-medium transition-all rounded-lg border ${
                      isActive
                        ? "bg-g-orange/15 border-g-orange/30 text-g-orange"
                        : "bg-g-surface border-g-border text-g-muted hover:text-g-text hover:bg-g-surface/80"
                    }`}>
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Bento Grid: Inputs + Result */}
          <div className="grid grid-cols-[1fr_1fr_1.6fr] gap-3 min-h-0">
            {/* ── Column 1: 구역 + 자세 + 무동작 ── */}
            <div className="flex flex-col gap-3">
              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-blue" />
                  <span className="text-[13px] font-semibold text-g-text">구역</span>
                  <span className="text-[11px] text-g-muted ml-auto">{zone.label}</span>
                </div>
                <div className="p-3">
                  <div className="flex flex-wrap gap-1.5">
                    {ZONES.map((z, i) => (
                      <OptionButton key={z.id} selected={zoneIdx === i} onClick={() => setZoneIdx(i)} color={RISK_COLORS[z.risk]}>{z.label}</OptionButton>
                    ))}
                  </div>
                  <p className="text-[11px] text-g-muted/50 mt-2">{zone.parent}</p>
                </div>
              </div>

              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-purple" />
                  <span className="text-[13px] font-semibold text-g-text">자세</span>
                  <span className="text-[11px] text-g-muted ml-auto">{posture.label}</span>
                </div>
                <div className="p-3 flex gap-1.5">
                  {POSTURES.map((p, i) => (
                    <OptionButton key={p.id} selected={postureIdx === i} onClick={() => setPostureIdx(i)} color={p.color}>{p.label}</OptionButton>
                  ))}
                </div>
              </div>

              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-teal" />
                  <span className="text-[13px] font-semibold text-g-text">무동작</span>
                  <span className="text-[11px] font-semibold text-g-text ml-auto tabular-nums">{duration}초</span>
                </div>
                <div className="p-3">
                  <input type="range" min={0} max={120} value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    className="w-full accent-g-teal h-1.5 cursor-pointer" />
                  <div className="flex justify-between text-[10px] text-g-muted/40 mt-1">
                    <span>0</span><span>30</span><span>60</span><span>120</span>
                  </div>
                </div>
              </div>
            </div>

            {/* ── Column 2: 인물 + 소리 + 이력 ── */}
            <div className="flex flex-col gap-3">
              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-pink" />
                  <span className="text-[13px] font-semibold text-g-text">인물</span>
                  <span className="text-[11px] text-g-muted ml-auto">{person.label}</span>
                </div>
                <div className="p-3">
                  <div className="flex flex-wrap gap-1.5">
                    {PERSONS.map((p, i) => (
                      <OptionButton key={p.id} selected={personIdx === i} onClick={() => setPersonIdx(i)} color={p.vulnerable ? C.pink : C.green}>{p.label}</OptionButton>
                    ))}
                  </div>
                  <p className="text-[11px] text-g-muted/50 mt-2">{person.parent}{person.vulnerable ? " — 취약 계층" : ""}</p>
                </div>
              </div>

              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-orange" />
                  <span className="text-[13px] font-semibold text-g-text">소리</span>
                  <span className="text-[11px] text-g-muted ml-auto">{audio.label}</span>
                </div>
                <div className="p-3 flex flex-wrap gap-1.5">
                  {AUDIO_EVENTS.map((a, i) => (
                    <OptionButton key={a.id} selected={audioIdx === i} onClick={() => setAudioIdx(i)} color={a.color}>{a.label}</OptionButton>
                  ))}
                </div>
              </div>

              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-yellow" />
                  <span className="text-[13px] font-semibold text-g-text">이력</span>
                </div>
                <div className="p-3">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" checked={priorIncident} onChange={(e) => setPriorIncident(e.target.checked)} className="accent-g-orange w-4 h-4 cursor-pointer rounded" />
                    <div>
                      <span className="text-[14px] text-g-text font-medium">이전 사건 있음</span>
                      <span className="text-[11px] text-g-muted block">5분 이내 동일 장소 낙상</span>
                    </div>
                  </label>
                </div>
              </div>

              {/* Prolog facts */}
              <div className="bg-g-card border border-g-border rounded-xl overflow-hidden flex-1">
                <div className="flex items-center gap-2 px-3 py-2 bg-g-surface/50 border-b border-g-border">
                  <span className="w-1.5 h-1.5 rounded-full bg-g-blue" />
                  <span className="text-[13px] font-semibold text-g-text">생성된 사실</span>
                </div>
                <div className="p-3 flex flex-wrap gap-1.5">
                  {[
                    `in_zone(I, ${zone.id})`,
                    `has_posture(I, ${posture.id})`,
                    ...(person.vulnerable ? ["is_vulnerable(I)"] : []),
                    ...(audio.id !== "none" ? [`has_audio_event(I, ${audio.id})`] : []),
                    ...(duration > 0 ? [`no_movement_duration(I, ${duration})`] : []),
                    ...(priorIncident ? ["prior_incident(_, _, M)"] : []),
                  ].map((f) => (
                    <span key={f} className="text-[11px] px-2 py-0.5 bg-g-surface text-g-blue rounded-md">{f}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* ── Column 3: 판정 결과 (full height) ── */}
            <div className="bg-g-card border border-g-border rounded-xl overflow-hidden flex flex-col">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-g-surface/50 border-b border-g-border">
                <div className="w-2 h-2 rounded-full" style={{ background: finalSeverity === "HIGH" ? C.red : finalSeverity === "MEDIUM" ? C.orange : finalSeverity === "LOW" ? C.green : "var(--color-g-border)" }} />
                <span className="text-[15px] font-semibold text-g-text">판정 결과</span>
                <span className="text-[12px] text-g-muted ml-1">{firedRules.length}개 규칙 발동</span>
              </div>

              <div className="flex-1 overflow-y-auto">
                {/* Severity Hero */}
                <div className="px-4 py-4 border-b border-g-border">
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl flex flex-col items-center justify-center transition-all duration-500" style={{
                      background: finalSeverity === "NONE" ? "var(--color-g-surface)" : `color-mix(in srgb, ${finalSeverity === "HIGH" ? C.red : finalSeverity === "MEDIUM" ? C.orange : C.green} 12%, transparent)`,
                      boxShadow: finalSeverity !== "NONE" ? `inset 0 0 0 1px color-mix(in srgb, ${finalSeverity === "HIGH" ? C.red : finalSeverity === "MEDIUM" ? C.orange : C.green} 20%, transparent)` : "none",
                    }}>
                      <span className="text-[22px] font-bold transition-colors duration-500" style={{
                        color: finalSeverity === "HIGH" ? C.red : finalSeverity === "MEDIUM" ? C.orange : finalSeverity === "LOW" ? C.green : "var(--color-g-border2)",
                      }}>
                        {finalSeverity === "HIGH" ? "위험" : finalSeverity === "MEDIUM" ? "주의" : finalSeverity === "LOW" ? "낮음" : "—"}
                      </span>
                      {finalSeverity !== "NONE" && (
                        <span className="text-[11px] text-g-muted mt-0.5">{finalSeverity}</span>
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="text-[14px] text-g-text-secondary leading-relaxed">
                        {finalSeverity === "HIGH" && "위험 등급 규칙이 발동되었습니다. 즉시 긴급 대응이 시작됩니다."}
                        {finalSeverity === "MEDIUM" && "주의 등급 규칙이 발동되었습니다. 보안실에 알림이 전송됩니다."}
                        {finalSeverity === "LOW" && "발동 규칙은 없지만 낙상 징후가 감지되었습니다."}
                        {finalSeverity === "NONE" && "낙상 관련 신호가 감지되지 않았습니다. 왼쪽에서 조건을 변경해 보세요."}
                      </p>
                      {/* Current input summary */}
                      <div className="flex flex-wrap gap-1.5 mt-2">
                        {[zone.label, person.label, posture.label, audio.id !== "none" ? audio.label : null, duration > 0 ? `${duration}초` : null, priorIncident ? "재낙상" : null].filter(Boolean).map((tag) => (
                          <span key={tag} className="text-[11px] px-2 py-0.5 bg-g-surface text-g-muted rounded-md">{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Fired Rules */}
                <div className="px-4 py-3 border-b border-g-border">
                  <span className="text-[12px] text-g-muted uppercase tracking-wider font-medium block mb-2">발동 규칙</span>
                  {firedRules.length > 0 ? (
                    <div className="space-y-1.5">
                      {firedRules.map((r) => (
                        <div key={r.id} className="flex items-start gap-2 px-3 py-2 bg-g-surface rounded-lg">
                          <span className="text-[12px] text-g-muted w-7 shrink-0 pt-0.5">{r.id}</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 text-white rounded ${r.severity === "HIGH" ? "bg-g-sev-high" : "bg-g-sev-med"}`}>{r.severity}</span>
                              <span className="text-[13px] text-g-text">{r.desc}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-6 bg-g-surface rounded-lg">
                      <span className="text-[14px] text-g-muted">발동된 규칙 없음</span>
                    </div>
                  )}
                  {firedRules.length > 0 && RULES.filter((r) => !firedRules.includes(r)).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-[12px] text-g-muted/40 cursor-pointer hover:text-g-muted/60">{RULES.length - firedRules.length}개 규칙 미발동</summary>
                      <div className="mt-1.5 space-y-0.5">
                        {RULES.filter((r) => !firedRules.includes(r)).map((r) => (
                          <div key={r.id} className="flex items-center gap-2 px-3 py-1 text-g-muted/30">
                            <span className="text-[11px] w-7">{r.id}</span>
                            <span className="text-[12px]">{r.desc}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>

                {/* Response Actions */}
                <div className="px-4 py-3">
                  <span className="text-[12px] text-g-muted uppercase tracking-wider font-medium block mb-2">대응 조치</span>
                  <div className="flex flex-wrap gap-2">
                    {responseAction.actions.map((a) => (
                      <span key={a} className="px-3 py-1.5 text-[13px] font-medium bg-g-surface rounded-lg transition-all duration-300" style={{
                        color: finalSeverity === "HIGH" ? C.red : finalSeverity === "MEDIUM" ? C.orange : finalSeverity === "NONE" ? "var(--color-g-border2)" : C.green,
                      }}>{a}</span>
                    ))}
                  </div>
                  {finalSeverity === "HIGH" && (
                    <div className="mt-3 px-3 py-2 bg-g-red/8 border border-g-red/15 rounded-lg flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-g-red animate-pulse shrink-0" />
                      <span className="text-[12px] text-g-red/80">비동기 에스컬레이션 에이전트 자동 실행 — 최대 4회 반복 검증</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
