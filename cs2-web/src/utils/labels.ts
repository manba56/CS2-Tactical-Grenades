/** Chinese labels for utility types, difficulty, phase, side */
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

export function label(term: string, dict: Record<string, string>): string {
  return dict[term] || term;
}
