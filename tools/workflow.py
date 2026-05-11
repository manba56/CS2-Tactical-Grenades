"""
CS2 grenade tactics workflow.

Usage:
    # Step 1 — extract throw data from demo
    python tools/workflow.py prepare <demo_path>

    # Step 2 — import screenshots into the web app
    python tools/workflow.py import <demo_path> --map mirage
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VENV = Path("E:/test/.venv")
DEFAULT_WORKDIR_BASE = Path("E:/test/workdir")
DEFAULT_API_URL = "http://127.0.0.1:8008"


def find_venv_python() -> str | None:
    for candidate in [
        DEFAULT_VENV / "Scripts" / "python.exe",
        Path("E:/test/.venv/Scripts/python.exe"),
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def cmd_prepare(args: argparse.Namespace) -> None:
    """Extract ticks from demo with position and view angle data."""
    demo_path = Path(args.demo_path)
    if not demo_path.exists():
        print(f"ERROR: demo not found: {demo_path}")
        sys.exit(1)

    workdir = DEFAULT_WORKDIR_BASE / demo_path.stem
    workdir.mkdir(parents=True, exist_ok=True)
    tick_json = workdir / "tick_list.json"
    tools_dir = PROJECT_ROOT / "tools"

    python_exe = find_venv_python()
    if not python_exe:
        print("ERROR: E:\\test\\.venv not found. Install demoparser2 there first.")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Extracting ticks from demo")
    print(f"{'='*60}")
    run([
        python_exe,
        str(tools_dir / "extract_ticks.py"),
        str(demo_path),
        "--output", str(tick_json),
    ])

    events = json.loads(tick_json.read_text(encoding="utf-8"))
    throws = [e for e in events if e["is_throw"]]
    detonates = [e for e in events if e["is_detonate"]]
    has_pos = sum(1 for e in throws if e.get("player_x") is not None)

    print(f"\nDone. {len(throws)} throws + {len(detonates)} detonates")
    print(f"  {has_pos}/{len(throws)} throws have position + view angle data")
    print(f"  Output: {tick_json}")
    print()
    print(f"To import screenshots:")
    map_hint = f"--map {args.map_slug}" if args.map_slug else "--map <mirage|inferno|nuke>"
    print(f"  python tools/workflow.py import {args.demo_path} {map_hint}")


def cmd_import(args: argparse.Namespace) -> None:
    """Import screenshots into cs2-tactics-suite."""
    demo_path = Path(args.demo_path)
    workdir = DEFAULT_WORKDIR_BASE / demo_path.stem
    tick_json = workdir / "tick_list.json"
    images_dir = workdir / "screenshots"
    tools_dir = PROJECT_ROOT / "tools"

    if not images_dir.is_dir() or not list(images_dir.glob("*.png")):
        print(f"ERROR: No screenshots found in {images_dir}")
        print(f"Place your renamed screenshots there first.")
        print(f"Naming: tick_XXXXXX_UTYPE_NNN.png")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Importing screenshots to cs2-tactics-suite")
    print(f"{'='*60}")

    import_args = [
        sys.executable,
        str(tools_dir / "import_to_suite.py"),
        "--api-url", args.api_url,
        "--admin-username", args.admin_user,
        "--admin-password", args.admin_pass,
        "--images-dir", str(images_dir),
        "--tick-json", str(tick_json),
        "--map-slug", args.map_slug,
        "--mode", args.mode,
    ]
    if args.dry_run:
        import_args.append("--dry-run")

    run(import_args)
    print(f"\nDone. Check: http://127.0.0.1:5175/admin")


def main() -> None:
    parser = argparse.ArgumentParser(description="CS2 grenade tactics workflow")
    sub = parser.add_subparsers(dest="command")

    prep = sub.add_parser("prepare", help="Extract throw ticks from demo")
    prep.add_argument("demo_path", help="Path to CS2 .dem file")
    prep.add_argument("--map", dest="map_slug", default="", help="Map slug (for hint only)")
    prep.set_defaults(func=cmd_prepare)

    imp = sub.add_parser("import", help="Import screenshots into web app")
    imp.add_argument("demo_path", help="Same demo path used in prepare")
    imp.add_argument("--map", dest="map_slug", required=True, help="Map slug: mirage, inferno, nuke")
    imp.add_argument("--mode", choices=["interactive", "auto"], default="interactive")
    imp.add_argument("--api-url", default=DEFAULT_API_URL)
    imp.add_argument("--admin-user", default="admin")
    imp.add_argument("--admin-pass", default="admin123")
    imp.add_argument("--dry-run", action="store_true")
    imp.set_defaults(func=cmd_import)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
