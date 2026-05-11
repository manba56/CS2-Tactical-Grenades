r"""
Step 1 — Extract grenade throw/detonate ticks and metadata from a CS2 demo.

Usage:
    cd E:\test
    .venv\Scripts\activate
    python extract_ticks.py <demo_path> [--output tick_list.json]

Output JSON per tick:
    {
      "tick": 12345,
      "tickrate": 128,
      "seconds": 96.445,
      "event": "grenade_thrown",
      "weapon": "smokegrenade",
      "player_name": "s1mple",
      "player_steamid": "STEAM_1:0:12345",
      "is_throw": true,
      "is_detonate": false
    }
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from demoparser2 import DemoParser

# ----- event names to probe -----
THROW_EVENTS = [
    "grenade_thrown",
    "grenade_throw",
    "weapon_fire",
]

DETONATE_EVENTS = [
    "flashbang_detonate",
    "smokegrenade_detonate",
    "hegrenade_detonate",
    "molotov_detonate",
    "incendiarygrenade_detonate",
    "decoy_detonate",
    "decoy_started",
]

# ----- weapon name → utility_type mapping -----
WEAPON_MAP = {
    "smokegrenade": "smoke",
    "flashbang": "flash",
    "hegrenade": "he",
    "molotov": "molotov",
    "incgrenade": "molotov",
    "incendiarygrenade": "molotov",
    "decoy": "decoy",
    "decoy_projectile": "decoy",
}


def classify_weapon(name: str) -> str | None:
    lower = name.strip().lower()
    for key, utype in WEAPON_MAP.items():
        if key in lower:
            return utype
    return None


def _float_or_none(rec: dict, key: str) -> float | None:
    """demoparser2 prefixes player fields with user_."""
    val = rec.get(f"user_{key}")
    if val is None:
        val = rec.get(key)
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


def _str_or(rec: dict, key: str, default: str = "") -> str:
    val = rec.get(f"user_{key}")
    if val is None:
        val = rec.get(key)
    return str(val) if val is not None else default


def read_tickrate(parser: DemoParser) -> int:
    """Try to read tickrate from demo header; fall back to 128."""
    try:
        header = parser.parse_header()
        tr = header.get("tickrate") or header.get("tick_rate")
        if tr:
            return int(tr)
    except Exception:
        pass
    # Default to 128 — player can override
    return 128


def extract(demo_path: str) -> tuple[list[dict], int]:
    parser = DemoParser(demo_path)
    tickrate = read_tickrate(parser)
    all_events: list[dict] = []

    # ---- throws ----
    for event_name in THROW_EVENTS:
        try:
            df = parser.parse_event(
                event_name,
                player=["X", "Y", "Z", "pitch", "yaw", "player_name", "player_steamid"],
            )
            if df.empty:
                continue
            for rec in df.to_dict(orient="records"):
                weapon = str(rec.get("weapon", "")).lower()
                utype = classify_weapon(weapon)
                if utype is None:
                    continue
                tick = rec.get("tick")
                if tick is None:
                    continue
                all_events.append(
                    {
                        "tick": int(tick),
                        "tickrate": tickrate,
                        "seconds": round(int(tick) / tickrate, 3),
                        "event": event_name,
                        "weapon": weapon,
                        "utility_type": utype,
                        "player_name": _str_or(rec, "player_name") or _str_or(rec, "name"),
                        "player_steamid": _str_or(rec, "player_steamid") or _str_or(rec, "steamid"),
                        "player_x": _float_or_none(rec, "X"),
                        "player_y": _float_or_none(rec, "Y"),
                        "player_z": _float_or_none(rec, "Z"),
                        "eye_pitch": _float_or_none(rec, "pitch"),
                        "eye_yaw": _float_or_none(rec, "yaw"),
                        "is_throw": True,
                        "is_detonate": False,
                    }
                )
        except Exception:
            continue

    # ---- detonates ----
    for event_name in DETONATE_EVENTS:
        try:
            df = parser.parse_event(event_name)
            if df.empty:
                continue
            for rec in df.to_dict(orient="records"):
                weapon = str(rec.get("weapon", "")).lower()
                utype = classify_weapon(weapon)
                if utype is None:
                    # infer from event name
                    if "flashbang" in event_name:
                        utype = "flash"
                    elif "smokegrenade" in event_name:
                        utype = "smoke"
                    elif "hegrenade" in event_name:
                        utype = "he"
                    elif "molotov" in event_name or "incendiary" in event_name:
                        utype = "molotov"
                    elif "decoy" in event_name:
                        utype = "decoy"
                    else:
                        continue
                tick = rec.get("tick")
                if tick is None:
                    continue
                all_events.append(
                    {
                        "tick": int(tick),
                        "tickrate": tickrate,
                        "seconds": round(int(tick) / tickrate, 3),
                        "event": event_name,
                        "weapon": weapon,
                        "utility_type": utype,
                        "player_name": str(rec.get("player_name", rec.get("user_name", ""))),
                        "player_steamid": str(rec.get("player_steamid", rec.get("user_steamid", ""))),
                        "is_throw": False,
                        "is_detonate": True,
                    }
                )
        except Exception:
            continue

    # deduplicate by (tick, event) and sort
    seen: set[tuple[int, str]] = set()
    unique: list[dict] = []
    for e in sorted(all_events, key=lambda x: x["tick"]):
        key = (e["tick"], "throw" if e["is_throw"] else "detonate")
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique, tickrate


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract grenade ticks from CS2 demo")
    parser.add_argument("demo_path", help="Path to .dem file")
    parser.add_argument("--output", default="tick_list.json", help="Output JSON path")
    parser.add_argument("--tickrate", type=int, default=0, help="Override auto-detected tickrate")
    args = parser.parse_args()

    print(f"Parsing demo: {args.demo_path}")
    events, detected_tr = extract(args.demo_path)

    if args.tickrate > 0:
        for e in events:
            e["tickrate"] = args.tickrate
            e["seconds"] = round(e["tick"] / args.tickrate, 3)
    else:
        print(f"Detected tickrate: {detected_tr}")

    out_path = Path(args.output)
    out_path.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")

    throws = [e for e in events if e["is_throw"]]
    detonates = [e for e in events if e["is_detonate"]]
    print(f"Done. {len(throws)} throws + {len(detonates)} detonates → {out_path}")


if __name__ == "__main__":
    main()
