"""
Step 3 — Import grenade screenshots into cs2-tactics-suite.

Workflow:
  1. Uploads each screenshot as an asset via the admin API
  2. Associates screenshots with lineups (interactive or auto mode)

Interactive mode (default):
  For each screenshot, shows available lineups filtered by map + utility_type,
  and lets you pick which one to associate.

Auto mode:
  Auto-matches by map + utility_type. If exactly one lineup matches, pairs them.
  If multiple or none, skips (reported at end).

Usage:
    python import_to_suite.py                          \\
        --api-url http://127.0.0.1:8008               \\
        --admin-username admin --admin-password admin123 \\
        --images-dir E:/test/grenade_images           \\
        --tick-json tick_list.json                    \\
        --map-slug mirage                             \\
        --mode interactive
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests


def login(url: str, username: str, password: str) -> str:
    r = requests.post(
        f"{url}/api/admin/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["token"]
    print(f"Logged in as admin (token={token[:12]}...)")
    return token


def upload_asset(url: str, token: str, file_path: Path) -> dict[str, Any]:
    with file_path.open("rb") as fh:
        r = requests.post(
            f"{url}/api/admin/assets",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (file_path.name, fh)},
            timeout=30,
        )
    r.raise_for_status()
    return r.json()


def fetch_lineups(url: str, token: str, map_id: int | None = None) -> list[dict]:
    params = {}
    if map_id is not None:
        params["map_id"] = map_id
    r = requests.get(
        f"{url}/api/admin/lineups",
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def fetch_map_by_slug(url: str, slug: str) -> dict | None:
    try:
        r = requests.get(f"{url}/api/public/maps/{slug}", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None



def run_interactive(
    url: str,
    token: str,
    events: list[dict],
    images_dir: Path,
    lineups: list[dict],
    dry_run: bool,
) -> dict[str, list[str]]:
    """Upload and interactively assign screenshots to lineups."""
    results: dict[str, list[str]] = {"uploaded": [], "assigned": [], "skipped": []}

    image_files = sorted(images_dir.glob("*"))
    # map tick → image path
    tick_to_image: dict[int, Path] = {}
    for img in image_files:
        if img.suffix.lower() in (".jpg", ".jpeg", ".png"):
            # Try to extract tick from filename like tick_012345_smoke_001.jpg
            name = img.stem
            parts = name.split("_")
            if len(parts) >= 2 and parts[0] == "tick":
                try:
                    tick_to_image[int(parts[1])] = img
                except ValueError:
                    continue

    throw_events = [e for e in events if e["is_throw"]]

    for i, event in enumerate(throw_events):
        tick = event["tick"]
        utype = event["utility_type"]
        img_path = tick_to_image.get(tick)

        if not img_path:
            results["skipped"].append(f"tick {tick}: no image file found")
            continue

        # Upload asset
        if not dry_run:
            try:
                asset = upload_asset(url, token, img_path)
                asset_url = asset["url"]
                print(f"\n[{i+1}/{len(throw_events)}] Uploaded: {img_path.name} → {asset_url}")
            except Exception as exc:
                results["skipped"].append(f"tick {tick}: upload failed ({exc})")
                continue
        else:
            asset_url = f"DRY_RUN:{img_path.name}"
            print(f"\n[{i+1}/{len(throw_events)}] Would upload: {img_path.name}")

        results["uploaded"].append(asset_url)

        # Filter matching lineups
        matching = [
            l for l in lineups
            if l["utility_type"] == utype and l["status"] == "published"
        ]

        if not matching:
            print(f"  No published {utype} lineups found. Skipping association.")
            results["skipped"].append(f"tick {tick}: no matching lineup for {utype}")
            continue

        if len(matching) == 1:
            lineup = matching[0]
            print(f"  Auto-matched → {lineup['title']} (id={lineup['id']})")
            choice = "1"  # auto-pick the only option
        else:
            print(f"  Matching {utype} lineups:")
            for j, lineup in enumerate(matching, 1):
                print(f"    [{j}] {lineup['title']} (id={lineup['id']})")
            print(f"    [s] Skip")
            choice = input("  Select > ").strip()

        if choice.lower() == "s" or not choice:
            results["skipped"].append(f"tick {tick}: user skipped")
            continue

        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(matching):
                raise ValueError()
            chosen = matching[idx]
        except (ValueError, IndexError):
            results["skipped"].append(f"tick {tick}: invalid selection")
            continue

        if not dry_run:
            try:
                requests.put(
                    f"{url}/api/admin/lineups/{chosen['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                    json={**chosen, "media": chosen.get("media", []) + [asset_url]},
                    timeout=10,
                ).raise_for_status()
                print(f"  Added to {chosen['title']} media")
            except Exception as e:
                print(f"  Failed to update {chosen['title']}: {e}")
        else:
            print(f"  Would associate with {chosen['title']}")

        results["assigned"].append(f"tick {tick}: → {chosen['title']}")

    return results


def run_auto(
    url: str,
    token: str,
    events: list[dict],
    images_dir: Path,
    lineups: list[dict],
    dry_run: bool,
) -> dict[str, list[str]]:
    """Upload and auto-assign screenshots to lineups (exact match only)."""
    results: dict[str, list[str]] = {"uploaded": [], "assigned": [], "skipped": []}

    image_files = sorted(images_dir.glob("*"))
    tick_to_image: dict[int, Path] = {}
    for img in image_files:
        if img.suffix.lower() in (".jpg", ".jpeg", ".png"):
            name = img.stem
            parts = name.split("_")
            if len(parts) >= 2 and parts[0] == "tick":
                try:
                    tick_to_image[int(parts[1])] = img
                except ValueError:
                    continue

    # Pre-group lineups by utility_type
    lineup_by_type: dict[str, list[dict]] = {}
    for l in lineups:
        if l["status"] == "published":
            lineup_by_type.setdefault(l["utility_type"], []).append(l)

    throw_events = [e for e in events if e["is_throw"]]

    for i, event in enumerate(throw_events):
        tick = event["tick"]
        utype = event["utility_type"]
        img_path = tick_to_image.get(tick)

        if not img_path:
            results["skipped"].append(f"tick {tick}: no image file")
            continue

        # Upload
        if not dry_run:
            try:
                asset = upload_asset(url, token, img_path)
                asset_url = asset["url"]
                print(f"[{i+1}/{len(throw_events)}] Uploaded: {img_path.name}")
            except Exception as exc:
                results["skipped"].append(f"tick {tick}: upload failed ({exc})")
                continue
        else:
            asset_url = f"DRY_RUN:{img_path.name}"
            print(f"[{i+1}/{len(throw_events)}] Would upload: {img_path.name}")

        results["uploaded"].append(asset_url)

        matching = lineup_by_type.get(utype, [])
        if len(matching) == 1:
            chosen = matching[0]
            if not dry_run:
                try:
                    requests.put(
                        f"{url}/api/admin/lineups/{chosen['id']}",
                        headers={"Authorization": f"Bearer {token}"},
                        json={**chosen, "media": chosen.get("media", []) + [asset_url]},
                        timeout=10,
                    ).raise_for_status()
                except Exception as e:
                    print(f"  Failed to update {chosen['title']}: {e}")
            results["assigned"].append(f"tick {tick}: → {chosen['title']}")
            print(f"  Auto → {chosen['title']}")
        else:
            results["skipped"].append(f"tick {tick}: {len(matching)} {utype} lineups (need exactly 1)")
            print(f"  Skipped: {len(matching)} candidates for {utype}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Import screenshots into cs2-tactics-suite")
    parser.add_argument("--api-url", default="http://127.0.0.1:8008")
    parser.add_argument("--admin-username", default="admin")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--images-dir", required=True, help="Folder with tick-named screenshots")
    parser.add_argument("--tick-json", required=True, help="Path to tick_list.json")
    parser.add_argument("--map-slug", required=True, help="Map slug (e.g. mirage, inferno, nuke)")
    parser.add_argument(
        "--mode", choices=["interactive", "auto"], default="interactive",
        help="interactive = pick lineup per screenshot | auto = exact utility_type match"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without uploading")
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    if not images_dir.is_dir():
        print(f"ERROR: images directory not found: {images_dir}")
        sys.exit(1)

    events = json.loads(Path(args.tick_json).read_text(encoding="utf-8"))
    throw_count = len([e for e in events if e["is_throw"]])
    print(f"Loaded {throw_count} throw events from {args.tick_json}")

    # Login
    token = login(args.api_url, args.admin_username, args.admin_password)

    # Resolve map
    map_data = fetch_map_by_slug(args.api_url, args.map_slug)
    if not map_data:
        print(f"ERROR: map '{args.map_slug}' not found in API")
        sys.exit(1)
    map_id = map_data["id"]
    print(f"Map: {map_data['name']} (id={map_id})")

    # Fetch lineups for this map
    lineups = fetch_lineups(args.api_url, token, map_id=map_id)
    print(f"Found {len(lineups)} lineups for {map_data['name']}")

    if args.mode == "auto":
        results = run_auto(args.api_url, token, events, images_dir, lineups, args.dry_run)
    else:
        results = run_interactive(args.api_url, token, events, images_dir, lineups, args.dry_run)

    # Summary
    print()
    print("=" * 50)
    print(f"Uploaded:   {len(results['uploaded'])}")
    print(f"Assigned:   {len(results['assigned'])}")
    print(f"Skipped:    {len(results['skipped'])}")
    if args.dry_run:
        print("[DRY RUN — no changes made]")


if __name__ == "__main__":
    main()
