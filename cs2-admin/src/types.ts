export interface AdminSessionUser {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface DashboardSummary {
  maps: number;
  points: number;
  lineups: number;
  tactics: number;
  users: number;
  favorites: number;
}

export interface AdminMap {
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

export interface AdminPoint {
  id: number;
  map_id: number;
  name: string;
  key: string;
  x: number;
  y: number;
  side: string;
  point_type: string;
  tags: string[];
}

export interface AdminLineup {
  id: number;
  map_id: number;
  title: string;
  slug: string;
  side: string;
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
}

export interface AdminTacticStep {
  order: number;
  role: string;
  type: string;
  instruction: string;
  lineup_id: number | null;
}

export interface AdminTactic {
  id: number;
  map_id: number;
  title: string;
  slug: string;
  side: string;
  goal: string;
  phase: string;
  difficulty: string;
  players: number;
  summary: string;
  note: string;
  tags: string[];
  cover_url: string;
  featured: boolean;
  status: string;
  created_at: string;
  step_items: AdminTacticStep[];
}
