import type {
  AdminCollection,
  AdminLineup,
  AdminMap,
  AdminPoint,
  AdminSessionUser,
  AdminTactic,
  DashboardSummary,
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8008';

export function resolveAssetUrl(path: string): string {
  if (!path) {
    return '';
  }
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  return `${API_BASE}${path}`;
}

interface AuthResponse {
  token: string;
  user: AdminSessionUser;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: '请求失败' }));
    throw new Error(data.detail || '请求失败');
  }
  return response.json() as Promise<T>;
}

export const api = {
  login(username: string, password: string) {
    return request<AuthResponse>('/api/admin/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },
  dashboard(token: string) {
    return request<DashboardSummary>('/api/admin/dashboard', {}, token);
  },
  maps(token: string) {
    return request<AdminMap[]>('/api/admin/maps', {}, token);
  },
  createMap(payload: Omit<AdminMap, 'id' | 'tactic_count'>, token: string) {
    return request<AdminMap>('/api/admin/maps', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updateMap(id: number, payload: Omit<AdminMap, 'id' | 'tactic_count'>, token: string) {
    return request<AdminMap>(`/api/admin/maps/${id}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  points(token: string) {
    return request<AdminPoint[]>('/api/admin/points', {}, token);
  },
  createPoint(payload: Omit<AdminPoint, 'id'>, token: string) {
    return request<AdminPoint>('/api/admin/points', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updatePoint(id: number, payload: Omit<AdminPoint, 'id'>, token: string) {
    return request<AdminPoint>(`/api/admin/points/${id}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  lineups(token: string) {
    return request<AdminLineup[]>('/api/admin/lineups', {}, token);
  },
  createLineup(payload: Omit<AdminLineup, 'id'>, token: string) {
    return request<AdminLineup>('/api/admin/lineups', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updateLineup(id: number, payload: Omit<AdminLineup, 'id'>, token: string) {
    return request<AdminLineup>(`/api/admin/lineups/${id}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  archiveLineup(id: number, token: string) {
    return request<{ status: string }>(`/api/admin/lineups/${id}/archive`, { method: 'POST' }, token);
  },
  deleteLineup(id: number, token: string) {
    return request<{ status: string }>(`/api/admin/lineups/${id}`, { method: 'DELETE' }, token);
  },
  tactics(token: string) {
    return request<AdminTactic[]>('/api/admin/tactics', {}, token);
  },
  createTactic(payload: Omit<AdminTactic, 'id' | 'created_at'>, token: string) {
    return request<AdminTactic>('/api/admin/tactics', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updateTactic(id: number, payload: Omit<AdminTactic, 'id' | 'created_at'>, token: string) {
    return request<AdminTactic>(`/api/admin/tactics/${id}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  publishTactic(id: number, token: string) {
    return request<{ status: string }>(`/api/admin/tactics/${id}/publish`, { method: 'POST' }, token);
  },
  archiveTactic(id: number, token: string) {
    return request<{ status: string }>(`/api/admin/tactics/${id}/archive`, { method: 'POST' }, token);
  },
  users(token: string) {
    return request<Array<{ id: number; username: string; email: string; favorites: number; recent: number }>>(
      '/api/admin/users',
      {},
      token,
    );
  },
  aiGenerate(form: Record<string, any>, token: string) {
    return request<{ summary: string; steps: string; note: string }>('/api/admin/ai/generate', {
      method: 'POST', body: JSON.stringify(form),
    }, token);
  },
  uploadAsset(file: File, token: string) {
    const formData = new FormData();
    formData.append('file', file);
    return request<{ id: number; url: string; original_name: string; type: string }>('/api/admin/assets', {
      method: 'POST',
      body: formData,
    }, token);
  },
  collections(token: string) {
    return request<AdminCollection[]>('/api/admin/collections', {}, token);
  },
  createCollection(payload: Omit<AdminCollection, 'id' | 'created_at'>, token: string) {
    return request<AdminCollection>('/api/admin/collections', { method: 'POST', body: JSON.stringify(payload) }, token);
  },
  updateCollection(id: number, payload: Omit<AdminCollection, 'id' | 'created_at'>, token: string) {
    return request<AdminCollection>(`/api/admin/collections/${id}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
  },
  deleteCollection(id: number, token: string) {
    return request<{ status: string }>(`/api/admin/collections/${id}`, { method: 'DELETE' }, token);
  },
};
