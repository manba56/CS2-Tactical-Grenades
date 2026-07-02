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
  video_url: string;
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
  description: string;
  aim_image_url: string;
  aim_image_description: string;
  effect_image_url: string;
  effect_image_description: string;
  video_url: string;
}

export interface AdminLineup {
  id: number;
  map_id: number;
  map?: { id: number; name: string; slug: string };
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
  video_url: string;
  status: string;
  start_point?: AdminPoint;
  aim_point?: AdminPoint;
  land_point?: AdminPoint;
}

export interface AdminTacticStep {
  order: number;
  role: string;
  type: string;
  instruction: string;
  lineup_id: number | null;
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
  video_url: string;
  featured: boolean;
  status: string;
  created_at: string;
  step_items: AdminTacticStep[];
  routes: RouteData[];
  screenshots: ScreenshotItem[];
}

export interface AdminCollection {
  id: number;
  title: string;
  slug: string;
  description: string;
  cover_url: string;
  tactic_ids: number[];
  status: string;
  created_at: string;
}

export interface AdminAsset {
  id: number;
  filename: string;
  original_name: string;
  url: string;
  width: number | null;
  height: number | null;
  type: string;
  used?: boolean;
}

export interface ClipSegment {
  title: string;
  note: string;
  start_seconds: number;
  end_seconds: number;
  focus_mode?: 'auto_center' | 'none';
  slow_motion?: boolean;
  focus_point_seconds?: number | null;
  focus_pause_seconds?: number;
  focus_start_seconds?: number | null;
  focus_end_seconds?: number | null;
  focus_x?: number;
  focus_y?: number;
  focus_width?: number;
  focus_height?: number;
  focus_scale?: number;
  focus_position?: 'top_right' | 'top_left' | 'bottom_right' | 'bottom_left' | 'center';
}

export interface ClipSourceUploadResponse {
  filename: string;
  original_name: string;
  url: string;
  size: number;
  type: string;
}

export interface AdminClipJob {
  id: number;
  title: string;
  lineup_id: number | null;
  lineup?: AdminLineup | null;
  source_url: string;
  source_filename: string;
  segments: ClipSegment[];
  template_type: 'lineup_tutorial';
  status: 'draft' | 'rendering' | 'ready' | 'failed';
  output_url: string;
  output_filename: string;
  error: string;
  created_at: string;
  updated_at: string;
}
