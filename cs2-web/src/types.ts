export interface SessionUser {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface MapSummary {
  id: number;
  name: string;
  slug: string;
  overview: string;
  cover_url: string;
  layout_url: string;
  callout_color: string;
  order: number;
  status: string;
  active_pool: boolean;
  tactic_count: number;
}

export interface MapPoint {
  id: number;
  map_id: number;
  name: string;
  key: string;
  x: number;
  y: number;
  side: 'T' | 'CT' | 'BOTH';
  point_type: string;
  tags: string[];
  description?: string;
  aim_image_url?: string;
  effect_image_url?: string;
  video_url?: string;
}

export interface UtilityLineupDetail {
  id: number;
  map_id: number;
  title: string;
  slug: string;
  side: 'T' | 'CT';
  utility_type: string;
  start_point_id: number;
  aim_point_id: number;
  land_point_id: number;
  purpose: string;
  difficulty: string;
  summary: string;
  steps: string[];
  media: string[];
  status: string;
  start_point: MapPoint;
  aim_point: MapPoint;
  land_point: MapPoint;
}

export interface TacticCard {
  id: number;
  slug: string;
  title: string;
  summary: string;
  goal: string;
  phase: string;
  side: 'T' | 'CT';
  difficulty: string;
  players: number;
  tags: string[];
  cover_url: string;
  utility_types: string[];
  created_at: string;
  status: string;
  featured: boolean;
  lineup_ids?: number[];
  map: {
    id: number;
    name: string;
    slug: string;
  };
}

export interface TacticStep {
  order: number;
  role: string;
  type: string;
  instruction: string;
  lineup_id?: number | null;
  lineup?: UtilityLineupDetail | null;
}

export interface RoutePoint {
  x: number;
  y: number;
}

export interface RouteData {
  player: number;
  color: string;
  label: string;
  points: RoutePoint[];
}

export interface ScreenshotItem {
  url: string;
  description: string;
  type: 'route' | 'spot';
}

export interface TacticDetail extends TacticCard {
  video_url?: string;
  note: string;
  map_layout_url: string;
  map_radar_url: string;
  map_points: MapPoint[];
  steps: TacticStep[];
  lineups: UtilityLineupDetail[];
  routes: RouteData[];
  screenshots: ScreenshotItem[];
  related: TacticCard[];
  is_favorite: boolean;
}

export interface MapDetail extends MapSummary {
  points: MapPoint[];
  lineups: UtilityLineupDetail[];
  filters: {
    sides: string[];
    utility_types: string[];
    goals: string[];
    phases: string[];
    difficulties: string[];
    tags: string[];
  };
  tactics: TacticCard[];
}

export interface FavoriteBundle {
  favorites: TacticDetail[];
  recent: TacticDetail[];
  collections: CollectionSummary[];
}

export interface CollectionSummary {
  id: number;
  title: string;
  slug: string;
  description: string;
  cover_url: string;
  tactic_count: number;
}

export interface CollectionDetail {
  id: number;
  title: string;
  slug: string;
  description: string;
  cover_url: string;
  tactics: TacticCard[];
}
