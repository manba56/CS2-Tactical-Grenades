import type { MapPoint, UtilityLineupDetail } from '../types';
import type { Language } from '../composables/useI18n';

export type LandingGroup = {
  point: MapPoint;
  lineups: UtilityLineupDetail[];
};

export type LineupMediaCard = {
  title: string;
  description: string;
  url: string;
};

export function groupLineupsByLandingPoint(
  points: MapPoint[],
  lineups: UtilityLineupDetail[],
): LandingGroup[];

export function buildLineupMediaCards(
  lineup: UtilityLineupDetail | null,
  language?: Language,
): LineupMediaCard[];
