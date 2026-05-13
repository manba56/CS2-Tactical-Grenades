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


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=64)


class MapPayload(BaseModel):
    name: str
    slug: str
    overview: str
    cover_url: str
    layout_url: str
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
    status: Literal["draft", "published", "archived"] = "draft"
    featured: bool = False


def dump_model(model: BaseModel) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
