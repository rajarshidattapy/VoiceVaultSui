import { BACKEND_CONFIG } from "./api";

const BASE = () => BACKEND_CONFIG.BASE_URL;

export interface AgentConfig {
  id: string;
  owner: string;
  status: "idle" | "live" | "paused";
  room_name: string;
  agent_name: string;
  template_id: string;
  system_prompt: string;
  agent_description?: string;
  skills?: string[];
  language?: string;
  endpoint?: string;
  llm_provider: string;
  price_per_call: number;
  voice_name: string;
  voice_uri: string;
  voice_id: string;
  calls_count: number;
  total_earned_sui: number;
  created_at: number;
}

export interface DeployResult {
  success: boolean;
  roomName: string;
  joinUrl: string;
  userToken: string;
  startCmd: string;
  liveKitConfigured: boolean;
  workerRunning?: boolean;
  agentDispatched?: boolean;
  workerError?: string | null;
  dispatchError?: string | null;
}

async function post(path: string, body?: object) {
  const res = await fetch(`${BASE()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || res.statusText);
  }
  return res.json();
}

async function del(path: string) {
  const res = await fetch(`${BASE()}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(res.statusText);
  return res.json();
}

export const agentApi = {
  create: (owner: string, cfg: Partial<AgentConfig>): Promise<{ success: boolean; agent: AgentConfig }> =>
    post("/api/agent/create", { owner, ...cfg }),

  list: async (owner: string): Promise<AgentConfig[]> => {
    const res = await fetch(`${BASE()}/api/agent/list?owner=${encodeURIComponent(owner)}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.agents || [];
  },

  deploy: (agentId: string): Promise<DeployResult> =>
    post(`/api/agent/deploy/${agentId}`),

  pause: (agentId: string) => post(`/api/agent/pause/${agentId}`),

  resume: (agentId: string) => post(`/api/agent/resume/${agentId}`),

  delete: (agentId: string) => del(`/api/agent/${agentId}`),

  join: (agentId: string, participantName: string): Promise<{ roomName: string; token: string; joinUrl: string; liveKitConfigured: boolean; workerRunning?: boolean; agentDispatched?: boolean }> =>
    post(`/api/agent/join/${agentId}`, { participantName }),

  talk: (agentId: string, identity: string): Promise<{ success: boolean; roomName: string; token: string; joinUrl: string; liveKitConfigured: boolean; workerRunning?: boolean; agentDispatched?: boolean }> =>
    post(`/api/agent/talk/${agentId}`, { identity }),
};
