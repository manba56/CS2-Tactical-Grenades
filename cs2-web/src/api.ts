import type {
  FavoriteBundle,
  MapDetail,
  MapSummary,
  SessionUser,
  TacticCard,
  TacticDetail,
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8008';

export function resolveAssetUrl(path: string): string {
  if (!path) {
    return '';
  }
  if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('data:')) {
    return path;
  }
  return `${API_BASE}${path}`;
}

export type TacticQuery = Record<string, string | number | undefined | null>;

interface AuthResponse {
  token: string;
  user: SessionUser;
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(init.headers || {});
  headers.set('Content-Type', 'application/json');
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

function toQueryString(query: TacticQuery): string {
  const params = new URLSearchParams();
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      params.set(key, String(value));
    }
  });
  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
}

export const api = {
  getHome() {
    return request<{
      featured_maps: MapSummary[];
      featured_tactics: TacticCard[];
      latest_tactics: TacticCard[];
      utility_quick_links: { type: string; count: number }[];
    }>('/api/public/home');
  },
  getMaps() {
    return request<MapSummary[]>('/api/public/maps');
  },
  getMapDetail(slug: string) {
    return request<MapDetail>(`/api/public/maps/${slug}`);
  },
  getTactics(query: TacticQuery) {
    return request<{ items: TacticCard[]; total: number; page: number; page_size: number }>(
      `/api/public/tactics${toQueryString(query)}`,
    );
  },
  getTacticDetail(slug: string, token?: string) {
    return request<TacticDetail>(`/api/public/tactics/${slug}`, {}, token);
  },
  login(usernameOrEmail: string, password: string) {
    return request<AuthResponse>('/api/public/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
    });
  },
  register(username: string, email: string, password: string) {
    return request<AuthResponse>('/api/public/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, email, password }),
    });
  },
  getFavorites(token: string) {
    return request<FavoriteBundle>('/api/public/me/favorites', {}, token);
  },
  addFavorite(tacticId: number, token: string) {
    return request('/api/public/me/favorites/' + tacticId, { method: 'POST' }, token);
  },
  removeFavorite(tacticId: number, token: string) {
    return request('/api/public/me/favorites/' + tacticId, { method: 'DELETE' }, token);
  },
  trackRecent(tacticId: number, token: string) {
    return request('/api/public/me/recent/' + tacticId, { method: 'POST' }, token);
  },
};
