import type { Language } from '../composables/useI18n';

export const UTILITY_LABELS: Record<string, string> = {
  smoke: '烟雾弹',
  flash: '闪光弹',
  molotov: '燃烧弹',
  he: '手雷',
  decoy: '诱饵弹',
};

export const DIFFICULTY_LABELS: Record<string, string> = {
  easy: '简单',
  medium: '中等',
  hard: '困难',
};

export const PHASE_LABELS: Record<string, string> = {
  pistol: '手枪局',
  default: '默认',
  'mid-round': '中局',
  exec: '执行',
  retake: '回防',
  'late-round': '残局',
};

export const SIDE_LABELS: Record<string, string> = {
  T: '进攻方',
  CT: '防守方',
};

export const UTILITY_LABELS_EN: Record<string, string> = {
  smoke: 'Smoke',
  flash: 'Flash',
  molotov: 'Molotov',
  he: 'HE Grenade',
  decoy: 'Decoy',
};

export const DIFFICULTY_LABELS_EN: Record<string, string> = {
  easy: 'Easy',
  medium: 'Medium',
  hard: 'Hard',
};

export const PHASE_LABELS_EN: Record<string, string> = {
  pistol: 'Pistol',
  default: 'Default',
  'mid-round': 'Mid-round',
  exec: 'Execute',
  retake: 'Retake',
  'late-round': 'Late round',
};

export const SIDE_LABELS_EN: Record<string, string> = {
  T: 'Attack',
  CT: 'Defense',
};

export function label(term: string, dict: Record<string, string>): string {
  return dict[term] || term;
}

export function labelByLanguage(
  term: string,
  zhDict: Record<string, string>,
  enDict: Record<string, string>,
  language: Language,
): string {
  return (language === 'en' ? enDict[term] : zhDict[term]) || term;
}
