import { api } from '../api';
import type { ProgressMap, TrainingStatus } from '../types';

export const FAVORITE_LINEUPS_KEY = 'cs2-favorite-lineups';
export const LINEUP_PROGRESS_KEY = 'cs2-lineup-progress';
export const TACTIC_PROGRESS_KEY = 'cs2-tactic-progress';

export const TRAINING_STATUSES: Array<{ value: TrainingStatus; zh: string; en: string }> = [
  { value: 'practicing', zh: '练习中', en: 'Practicing' },
  { value: 'mastered', zh: '已掌握', en: 'Mastered' },
  { value: 'match_ready', zh: '比赛常用', en: 'Match ready' },
];

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function readLocalFavoriteLineups(): number[] {
  return readJson<number[]>(FAVORITE_LINEUPS_KEY, []);
}

export function writeLocalFavoriteLineups(ids: number[]) {
  writeJson(FAVORITE_LINEUPS_KEY, Array.from(new Set(ids)));
}

export function readLocalLineupProgress(): ProgressMap {
  return readJson<ProgressMap>(LINEUP_PROGRESS_KEY, {});
}

export function writeLocalLineupProgress(progress: ProgressMap) {
  writeJson(LINEUP_PROGRESS_KEY, progress);
}

export function readLocalTacticProgress(): ProgressMap {
  return readJson<ProgressMap>(TACTIC_PROGRESS_KEY, {});
}

export function writeLocalTacticProgress(progress: ProgressMap) {
  writeJson(TACTIC_PROGRESS_KEY, progress);
}

export function setProgressValue(progress: ProgressMap, id: number, status: TrainingStatus | null): ProgressMap {
  const next = { ...progress };
  if (status) {
    next[String(id)] = status;
  } else {
    delete next[String(id)];
  }
  return next;
}

export function clearLocalPersonalData() {
  localStorage.removeItem(FAVORITE_LINEUPS_KEY);
  localStorage.removeItem(LINEUP_PROGRESS_KEY);
  localStorage.removeItem(TACTIC_PROGRESS_KEY);
}

export function progressLabel(status: TrainingStatus | undefined, language: 'zh' | 'en') {
  if (!status) return language === 'en' ? 'Not practiced' : '未练习';
  const option = TRAINING_STATUSES.find((item) => item.value === status);
  if (!option) return status;
  return language === 'en' ? option.en : option.zh;
}

export async function syncLocalPersonalData(token: string) {
  const payload = {
    favorite_lineup_ids: readLocalFavoriteLineups(),
    lineup_progress: readLocalLineupProgress(),
    tactic_progress: readLocalTacticProgress(),
  };
  const hasLocalData =
    payload.favorite_lineup_ids.length > 0
    || Object.keys(payload.lineup_progress).length > 0
    || Object.keys(payload.tactic_progress).length > 0;
  if (!hasLocalData) return;
  await api.syncLocalPersonalData(payload, token);
  clearLocalPersonalData();
}
