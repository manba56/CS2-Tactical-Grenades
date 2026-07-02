from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=24)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=64)


class LoginRequest(BaseModel):
    username_or_email: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=64)


TrainingStatus = Literal["practicing", "mastered", "match_ready"]


class ProgressPayload(BaseModel):
    status: TrainingStatus | None = None


class LocalSyncPayload(BaseModel):
    favorite_lineup_ids: list[int] = Field(default_factory=list)
    lineup_progress: dict[str, TrainingStatus] = Field(default_factory=dict)
    tactic_progress: dict[str, TrainingStatus] = Field(default_factory=dict)


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=64)


class MapPayload(BaseModel):
    name: str
    slug: str
    overview: str
    cover_url: str
    layout_url: str
    video_url: str = ""
    callout_color: str = "#ff7a18"
    order: int = 0
    status: Literal["draft", "published", "archived"] = "draft"
    active_pool: bool = True


class PointPayload(BaseModel):
    map_id: int
    name: str
    key: str
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    side: Literal["T", "CT", "BOTH"] = "BOTH"
    point_type: Literal["site", "staging", "aim", "utility", "anchor"] = "site"
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    aim_image_url: str = ""
    aim_image_description: str = ""
    effect_image_url: str = ""
    effect_image_description: str = ""
    video_url: str = ""


class LineupPayload(BaseModel):
    map_id: int
    title: str
    slug: str
    side: Literal["T", "CT"]
    utility_type: Literal["smoke", "flash", "molotov", "he", "decoy"]
    start_point_id: int
    aim_point_id: int
    land_point_id: int
    purpose: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    summary: str
    steps: list[str] = Field(default_factory=list)
    media: list[str] = Field(default_factory=list)
    video_url: str = ""
    status: Literal["draft", "published", "archived"] = "draft"


class TacticStepPayload(BaseModel):
    order: int
    role: str
    type: Literal["utility", "move", "hold", "trade"]
    instruction: str
    lineup_id: int | None = None


class RoutePoint(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class RouteData(BaseModel):
    player: int = Field(ge=1, le=5)
    color: str = "#ff7a18"
    label: str = ""
    points: list[RoutePoint] = Field(default_factory=list)


class BoardMarkerPayload(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    label: str = Field(min_length=1, max_length=40)
    role: Literal["player", "smoke", "flash", "molotov", "he", "note"] = "player"
    side: Literal["T", "CT", "BOTH"] = "BOTH"


class PersonalBoardPayload(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    map_id: int
    side: Literal["T", "CT"] = "T"
    plan_type: Literal["exec", "default", "retake", "anti-rush", "practice"] = "exec"
    summary: str = Field(default="", max_length=500)
    markers: list[BoardMarkerPayload] = Field(default_factory=list)
    routes: list[RouteData] = Field(default_factory=list)


class ClipSegmentPayload(BaseModel):
    title: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=300)
    start_seconds: float = Field(ge=0)
    end_seconds: float = Field(gt=0)
    focus_mode: Literal["auto_center", "none"] = "auto_center"
    slow_motion: bool = True
    focus_point_seconds: float | None = Field(default=None, ge=0)
    focus_pause_seconds: float = Field(default=1.0, ge=0.2, le=5)
    focus_start_seconds: float | None = Field(default=None, ge=0)
    focus_end_seconds: float | None = Field(default=None, ge=0)
    focus_x: float = Field(default=0.38, ge=0, le=0.95)
    focus_y: float = Field(default=0.38, ge=0, le=0.95)
    focus_width: float = Field(default=0.24, ge=0.08, le=1)
    focus_height: float = Field(default=0.24, ge=0.08, le=1)
    focus_scale: float = Field(default=1.2, ge=0.8, le=2.4)
    focus_position: Literal["top_right", "top_left", "bottom_right", "bottom_left", "center"] = "center"


class ClipJobPayload(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    lineup_id: int | None = None
    source_url: str
    source_filename: str = ""
    segments: list[ClipSegmentPayload] = Field(default_factory=list)
    template_type: Literal["lineup_tutorial"] = "lineup_tutorial"


class ScreenshotItem(BaseModel):
    url: str
    description: str = ""
    type: Literal["route", "spot"] = "spot"


class TacticPayload(BaseModel):
    map_id: int
    title: str
    slug: str
    side: Literal["T", "CT"]
    goal: str
    phase: Literal["pistol", "default", "mid-round", "exec", "retake", "late-round"]
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    players: int = Field(ge=1, le=5)
    summary: str
    note: str
    tags: list[str] = Field(default_factory=list)
    cover_url: str
    step_items: list[TacticStepPayload] = Field(default_factory=list)
    routes: list[RouteData] = Field(default_factory=list)
    screenshots: list[ScreenshotItem] = Field(default_factory=list)
    video_url: str = ""
    status: Literal["draft", "published", "archived"] = "draft"
    featured: bool = False


def dump_model(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
