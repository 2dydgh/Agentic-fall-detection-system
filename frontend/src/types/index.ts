export type AttentionWeights = {
  pose: number;
  audio: number;
  vlm: number;
};

export type Incident = {
  id: string;
  camera_id: string;
  timestamp: string;
  severity: string;
  score: number;
  audio_scream: boolean;
  audio_impact: boolean;
  audio_confidence: number;
  attention_weights: AttentionWeights | null;
  decision_mode: string;
};

export type Stats = {
  total: number;
  high: number;
  medium: number;
  logs: Incident[];
};

export type AgentAction = {
  tool: string;
  args: Record<string, unknown>;
  result: Record<string, unknown>;
};

export type AgentResult = {
  id: number;
  incident_id: string;
  timestamp: string;
  escalation_needed: boolean;
  final_assessment: string;
  actions_taken: AgentAction[];
};

export const CAMERAS = [
  { id: "01", label: "Corridor", video: "input/corridor.mp4", audio: "data/fall_audio_sample.wav" },
  { id: "02", label: "Hospital", video: "input/hospital1.mp4", audio: "data/fall_audio_sample.wav" },
  { id: "03", label: "Outdoor",  video: "input/outdoor.mp4",   audio: "data/fall_audio_sample.wav" },
  { id: "04", label: "Toilet",   video: "input/toilet.mp4",    audio: "data/fall_audio_sample.wav" },
] as const;
