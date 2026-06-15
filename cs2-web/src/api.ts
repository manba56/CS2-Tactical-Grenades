import type {
  CollectionDetail,
  CollectionSummary,
  FavoriteBundle,
  MapDetail,
  MapSummary,
  SessionUser,
  TacticCard,
  TacticDetail,
} from './types';

export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8008';

function fallbackErrorMessage(type: 'network' | 'request' = 'request'): string {
  const isEnglish = typeof localStorage !== 'undefined' && localStorage.getItem('cs2-language') === 'en';
  if (type === 'network') {
    return isEnglish ? 'Network error. Please try again later.' : '网络异常，请稍后重试';
  }
  return isEnglish ? 'Request failed' : '请求失败';
}

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

// ── Simple in-memory cache for GET requests ──
const cache = new Map<string, { data: unknown; ts: number }>();
const CACHE_TTL = 30_000; // 30 seconds
const inflight = new Map<string, Promise<unknown>>();

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const isGet = !init.method || init.method === 'GET';
  const cacheKey = isGet ? `GET:${path}:${token || ''}` : '';

  // Return cached value if fresh
  if (cacheKey) {
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.ts < CACHE_TTL) {
      return cached.data as T;
    }
    // Dedup in-flight requests
    const flying = inflight.get(cacheKey) as Promise<T> | undefined;
    if (flying) return flying;
  }

  const headers = new Headers(init.headers || {});
  if (!(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const promise = (async () => {
    const MAX_RETRIES = 2;
    const TIMEOUT_MS = 15_000;
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      try {
        const ctrl = new AbortController();
        const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
        const response = await fetch(`${API_BASE}${path}`, {
          ...init, headers, signal: ctrl.signal,
        });
        clearTimeout(timer);

        if (!response.ok) {
          const data = await response.json().catch(() => ({ detail: fallbackErrorMessage('request') }));
          throw new Error(data.detail || fallbackErrorMessage('request'));
        }
        return response.json() as Promise<T>;
      } catch (err: any) {
        lastError = err;
        if (attempt < MAX_RETRIES && (err.name === 'AbortError' || err.message?.includes('fetch') || err.message?.includes('network'))) {
          await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
          continue;
        }
        throw new Error(lastError?.message || fallbackErrorMessage('network'));
      }
    }
    throw lastError || new Error(fallbackErrorMessage('request'));
  })();

  if (cacheKey) {
    inflight.set(cacheKey, promise);
    const result = await promise;
    cache.set(cacheKey, { data: result, ts: Date.now() });
    inflight.delete(cacheKey);
    return result as T;
  }

  return promise;
}

// Clean stale cache every 60s
if (typeof setInterval !== 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, val] of cache) {
      if (now - val.ts > CACHE_TTL) cache.delete(key);
    }
  }, 60_000);
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
  getCollections() {
    return request<CollectionSummary[]>('/api/public/collections');
  },
  getCollection(slug: string) {
    return request<CollectionDetail>(`/api/public/collections/${slug}`);
  },
};
