/**
 * Typed API client for the Order Supervisor backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────────────────────

export interface Supervisor {
  id: string;
  name: string;
  base_instruction: string;
  available_actions: string[];
  default_wake_behavior: Record<string, unknown> | null;
  model_config_data: Record<string, unknown> | null;
  wake_guidance: string | null;
  created_at: string;
  updated_at: string;
}

export interface Run {
  id: string;
  supervisor_id: string;
  order_id: string;
  status: 'running' | 'sleeping' | 'paused' | 'completed' | 'terminated';
  state: Record<string, unknown>;
  wake_guidance: string | null;
  additional_instructions: string[];
  next_wake_at: string | null;
  max_end_at: string | null;
  final_summary: RunSummary | null;
  created_at: string;
  updated_at: string;
  supervisor?: Supervisor;
}

export interface RunSummary {
  summary: string;
  actions_taken: string[];
  key_learnings: string[];
  recommendations: string[];
}

export interface RunListItem {
  id: string;
  supervisor_id: string;
  order_id: string;
  status: string;
  next_wake_at: string | null;
  created_at: string;
  updated_at: string;
  supervisor_name: string | null;
}

export interface Activity {
  id: string;
  run_id: string;
  type: string;
  subtype: string | null;
  content: Record<string, unknown>;
  created_at: string;
}

export interface DashboardStats {
  total_runs: number;
  active_runs: number;
  completed_runs: number;
  total_events: number;
  total_actions: number;
}

export interface StatusResponse {
  status: string;
  message: string;
}

// ── Fetch helper ───────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API Error ${res.status}: ${errorBody}`);
  }

  return res.json();
}

// ── Supervisor API ─────────────────────────────────────────────────────────

export const supervisorApi = {
  list: () => apiFetch<Supervisor[]>('/api/supervisors'),

  get: (id: string) => apiFetch<Supervisor>(`/api/supervisors/${id}`),

  create: (data: {
    name: string;
    base_instruction: string;
    available_actions?: string[];
    default_wake_behavior?: Record<string, unknown>;
    model_config_data?: Record<string, unknown>;
    wake_guidance?: string;
  }) =>
    apiFetch<Supervisor>('/api/supervisors', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<Supervisor>) =>
    apiFetch<Supervisor>(`/api/supervisors/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};

// ── Run API ────────────────────────────────────────────────────────────────

export const runApi = {
  list: (status?: string) => {
    const params = status ? `?status=${status}` : '';
    return apiFetch<RunListItem[]>(`/api/runs${params}`);
  },

  get: (id: string) => apiFetch<Run>(`/api/runs/${id}`),

  create: (data: { supervisor_id: string; order_id: string; initial_context?: Record<string, unknown> }) =>
    apiFetch<Run>('/api/runs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getActivities: (id: string, limit = 100, offset = 0) =>
    apiFetch<Activity[]>(`/api/runs/${id}/activities?limit=${limit}&offset=${offset}`),

  getStats: () => apiFetch<DashboardStats>('/api/runs/stats'),

  injectEvent: (id: string, eventType: string, payload: Record<string, unknown> = {}) =>
    apiFetch<StatusResponse>(`/api/runs/${id}/events`, {
      method: 'POST',
      body: JSON.stringify({ event_type: eventType, payload }),
    }),

  addInstruction: (id: string, instruction: string) =>
    apiFetch<StatusResponse>(`/api/runs/${id}/instructions`, {
      method: 'POST',
      body: JSON.stringify({ instruction }),
    }),

  pause: (id: string) =>
    apiFetch<StatusResponse>(`/api/runs/${id}/pause`, { method: 'POST' }),

  resume: (id: string) =>
    apiFetch<StatusResponse>(`/api/runs/${id}/resume`, { method: 'POST' }),

  terminate: (id: string) =>
    apiFetch<StatusResponse>(`/api/runs/${id}/terminate`, { method: 'POST' }),
};

// ── Simulator API ──────────────────────────────────────────────────────────

export const simulatorApi = {
  fireScenario: (runId: string, scenario: string) =>
    apiFetch<StatusResponse>(`/api/simulator/scenario?run_id=${runId}`, {
      method: 'POST',
      body: JSON.stringify({ scenario }),
    }),
};
