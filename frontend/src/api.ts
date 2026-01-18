export type PlayerStatus = {
  gif_dir: string;
  gif_count: number;
  index: number;
  current_name: string | null;
  playing: boolean;
  last_error: string | null;
};

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export function apiUrl(path: string): string {
  if (!path.startsWith("/")) return path;
  return API_BASE ? `${API_BASE}${path}` : path;
}

export async function getStatus(signal?: AbortSignal): Promise<PlayerStatus> {
  const res = await fetch(apiUrl("/api/status"), { signal });
  if (!res.ok) throw new Error(`GET /api/status failed: ${res.status}`);
  return (await res.json()) as PlayerStatus;
}

