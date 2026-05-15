"""
CS2 HLTV Demo Downloader.

Usage:
    python cs2_demo_downloader.py 2026-05-11
    python cs2_demo_downloader.py 2026-05-11 --event "IEM Dallas"
    python cs2_demo_downloader.py 2026-05-11 --output "D:\\steam\\...\\game\\csgo"
    python cs2_demo_downloader.py 2026-05-11 --clear-cache  # reset browser profile
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import os
import random
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

HLTV_BASE = "https://www.hltv.org"
RESULTS_URL = f"{HLTV_BASE}/results"
DEFAULT_OUTPUT = Path("D:/steam/steamapps/common/Counter-Strike Global Offensive/game/csgo")
USER_DATA_DIR = Path(__file__).parent / "hltv_browser_profile"

console = Console()


def _rand_delay(min_s: float = 1.5, max_s: float = 4.0) -> float:
    return random.uniform(min_s, max_s)


def _is_cloudflare_blocked(html: str | None) -> bool:
    if not html:
        return False
    markers = [
        "cf-browser-verification", "cf_challenge",
        "Checking your browser", "Just a moment",
        "cf-please-wait", "Attention Required!",
        "Cloudflare", "cf-error",
    ]
    return any(m.lower() in html.lower() for m in markers)


def _filter_real_matches(raw: list[dict]) -> list[dict]:
    out = []
    seen = set()
    for m in raw:
        url = m.get("matchUrl", "")
        if not url or url in seen:
            continue
        seen.add(url)
        if re.search(r"/matches/\d+/", url):
            out.append(m)
    return out


# ── RAR extraction ───────────────────────────────────────────────

def _find_unrar_tool() -> str | None:
    """Find an available RAR extraction tool on this Windows system."""
    candidates = [
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "unrar", "UnRAR.exe", "7z", "7z.exe",
    ]
    for p in candidates:
        if shutil.which(p) or Path(p).exists():
            return p
    return None


def _extract_rar(filepath: Path, output_dir: Path) -> Path | None:
    """Extract .rar archive, return path to .dem file or None."""
    # Try 1: rarfile Python library
    try:
        import rarfile
        tool = _find_unrar_tool()
        if tool:
            rarfile.UNRAR_TOOL = tool
        with rarfile.RarFile(filepath) as rf:
            rf.extractall(output_dir)
            for name in rf.namelist():
                if name.lower().endswith(".dem"):
                    extracted = output_dir / name
                    console.print(f"  [green]Extracted: {extracted.name}[/green]")
                    filepath.unlink()
                    return extracted
    except ImportError:
        pass
    except Exception as e:
        console.print(f"  [dim]rarfile: {e}[/dim]")

    # Try 2: 7-Zip
    seven_zip = None
    for p in [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z", "7z.exe"]:
        if shutil.which(p) or Path(p).exists():
            seven_zip = p
            break
    if seven_zip:
        try:
            subprocess.run(
                [seven_zip, "x", str(filepath), f"-o{output_dir}", "-y"],
                capture_output=True, check=True, timeout=300,
            )
            for root, _, files in os.walk(output_dir):
                for name in files:
                    if name.endswith(".dem"):
                        extracted = Path(root) / name
                        console.print(f"  [green]Extracted (7z): {extracted.name}[/green]")
                        filepath.unlink()
                        return extracted
        except Exception as e:
            console.print(f"  [dim]7z: {e}[/dim]")

    # Try 3: WinRAR unrar
    unrar = None
    for p in [r"C:\Program Files\WinRAR\UnRAR.exe", r"C:\Program Files (x86)\WinRAR\UnRAR.exe", "unrar", "UnRAR.exe"]:
        if shutil.which(p) or Path(p).exists():
            unrar = p
            break
    if unrar:
        try:
            subprocess.run(
                [unrar, "x", "-y", str(filepath), str(output_dir) + "\\"],
                capture_output=True, check=True, timeout=300,
            )
            for root, _, files in os.walk(output_dir):
                for name in files:
                    if name.endswith(".dem"):
                        extracted = Path(root) / name
                        console.print(f"  [green]Extracted (unrar): {extracted.name}[/green]")
                        filepath.unlink()
                        return extracted
        except Exception as e:
            console.print(f"  [dim]unrar: {e}[/dim]")

    console.print("  [red]No RAR tool found. Install WinRAR or 7-Zip.[/red]")
    return None


# ── main downloader class ─────────────────────────────────────────

class HLTVDemoDownloader:
    def __init__(
        self,
        date: str,
        event_filter: str | None = None,
        output_dir: Path | None = None,
        headless: bool = False,
        clear_cache: bool = False,
    ) -> None:
        self.date = date
        self.event_filter = event_filter.strip() if event_filter else None
        base = Path(output_dir) if output_dir else DEFAULT_OUTPUT
        # Organize by date: <base>/<MM-DD>/
        date_folder = date[5:]  # "YYYY-MM-DD" -> "MM-DD"
        self.output_dir = base / date_folder
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._headless = headless
        self._clear_cache = clear_cache
        self._playwright = None
        self._context = None
        self._page = None

    # ── browser lifecycle ────────────────────────────────────────
    async def start(self) -> None:
        if self._clear_cache and USER_DATA_DIR.exists():
            shutil.rmtree(str(USER_DATA_DIR), ignore_errors=True)
            console.print("[dim]Cleared browser profile cache[/dim]")

        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            color_scheme="dark",
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
        )
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._playwright:
            await self._playwright.stop()

    async def _human_scroll(self) -> None:
        try:
            steps = random.randint(2, 5)
            total_height = await self._page.evaluate("document.body.scrollHeight")
            for _ in range(steps):
                scroll_y = random.randint(0, max(1, total_height))
                await self._page.evaluate(f"window.scrollTo({{top: {scroll_y}, behavior: 'smooth'}})")
                await asyncio.sleep(random.uniform(0.3, 1.2))
        except Exception:
            pass

    # ── fetch match list ─────────────────────────────────────────
    async def fetch_matches(self) -> list[dict]:
        url = f"{RESULTS_URL}?startdate={self.date}&enddate={self.date}"
        console.print(f"\n[bold]Fetching:[/bold] {url}")

        for attempt in range(3):
            if attempt > 0:
                wait = 5 * (attempt + 1)
                console.print(f"  [yellow]Retry {attempt + 1}/3 (waiting {wait}s)...[/yellow]")
                await asyncio.sleep(wait)

            try:
                await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                console.print(f"  [red]Navigation error: {e}[/red]")
                continue

            await asyncio.sleep(_rand_delay(2, 4))

            page_text = await self._page.evaluate("() => document.body.innerText.substring(0, 500)")
            if _is_cloudflare_blocked(page_text):
                if not self._headless:
                    console.print(
                        "  [yellow]Cloudflare challenge! Solve in browser, then press Enter...[/yellow]"
                    )
                    input("  > ")
                    try:
                        await self._page.reload(wait_until="domcontentloaded", timeout=30000)
                    except Exception:
                        pass
                else:
                    console.print("  [yellow]Cloudflare detected, waiting...[/yellow]")
                    for wait_sec in [5, 10, 15]:
                        await asyncio.sleep(wait_sec)
                        try:
                            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
                        except Exception:
                            pass
                        await asyncio.sleep(3)
                        page_text = await self._page.evaluate("() => document.body.innerText.substring(0, 500)")
                        if not _is_cloudflare_blocked(page_text):
                            break
                    else:
                        continue

            try:
                await self._page.wait_for_selector(
                    ".results-sublist, .results-all, .result-con", timeout=15000
                )
            except Exception:
                title = await self._page.title()
                console.print(f"  [yellow]Selector not found. Page title: '{title}'[/yellow]")
                continue

            await self._human_scroll()
            await asyncio.sleep(_rand_delay(1, 2))

            raw = await self._page.evaluate("""
                () => {
                    const matchLinks = document.querySelectorAll('a[href*="/matches/"]');
                    const matches = [];
                    const seen = new Set();
                    matchLinks.forEach(a => {
                        const href = a.getAttribute('href');
                        if (!href || seen.has(href)) return;
                        seen.add(href);
                        const container = a.closest('.result-con, .result, [class*="result"]');
                        if (!container) return;
                        const t1 = container.querySelector('.team1 .team, .team1')?.textContent?.trim();
                        const t2 = container.querySelector('.team2 .team, .team2')?.textContent?.trim();
                        if (!t1 || !t2) return;
                        const scoreEl = container.querySelector('.result-score');
                        const stars = container.querySelectorAll('.fa-star').length;
                        const eventLogo = container.querySelector('.event-logo')
                            || container.closest('.results-sublist')?.querySelector('.event-logo');
                        matches.push({
                            team1: t1, team2: t2,
                            score: scoreEl?.textContent?.trim() || '',
                            event: eventLogo?.getAttribute('title') || eventLogo?.getAttribute('alt') || '',
                            matchUrl: href, stars: stars
                        });
                    });
                    return matches;
                }
            """)

            matches = _filter_real_matches(raw)
            if self.event_filter:
                kw = self.event_filter.lower()
                matches = [m for m in matches if kw in m.get("event", "").lower()]
            if matches:
                return matches
            console.print("  [yellow]Parsed 0 matches, may need retry[/yellow]")

        return []

    # ── display ──────────────────────────────────────────────────
    def display_matches(self, matches: list[dict]) -> None:
        if not matches:
            console.print("\n[yellow]No matches found for this date.[/yellow]")
            return

        table = Table(title=f"\nMatches for {self.date}", show_lines=False)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Team 1", style="bold green")
        table.add_column("Score", style="dim", width=8)
        table.add_column("Team 2", style="bold red")
        table.add_column("Event", style="yellow")
        table.add_column("Stars", style="magenta", width=6)

        for i, m in enumerate(matches, 1):
            stars = ":star:" * m.get("stars", 0) or "-"
            table.add_row(
                str(i), m["team1"], m.get("score", "-"),
                m["team2"], m.get("event", "-"), stars,
            )
        console.print(table)

    # ── check demo availability ──────────────────────────────────
    async def check_demo(self, match_url: str) -> tuple[str | None, str | None]:
        full_url = urljoin(HLTV_BASE, match_url)
        results_url = f"{RESULTS_URL}?startdate={self.date}&enddate={self.date}"
        console.print(f"  [dim]Checking {full_url}[/dim]")

        try:
            await self._page.goto(full_url, wait_until="domcontentloaded",
                                  timeout=45000, referer=results_url)
            await asyncio.sleep(2)
        except Exception as e:
            console.print(f"  [red]Navigation error: {e}[/red]")
            return None, None

        for _ in range(3):
            page_text = await self._page.evaluate("() => document.body.innerText.substring(0, 500)")
            if not _is_cloudflare_blocked(page_text):
                break

            if not self._headless:
                console.print(
                    "  [yellow]Cloudflare challenge! Solve in browser.[/yellow]\n"
                    "  [dim](Page will auto-redirect to match content after solving)[/dim]\n"
                    "  [bold]Press Enter once match page loads...[/bold]"
                )
                input("  > ")
                for _ in range(15):
                    await asyncio.sleep(1)
                    ct = await self._page.evaluate("() => document.body.innerText.substring(0, 300)")
                    if not _is_cloudflare_blocked(ct):
                        console.print("  [green]Loaded![/green]")
                        break
            else:
                await asyncio.sleep(10)
                try:
                    await self._page.reload(wait_until="domcontentloaded", timeout=30000)
                except Exception:
                    pass
                await asyncio.sleep(3)

        page_text = await self._page.evaluate("() => document.body.innerText.substring(0, 500)")
        if _is_cloudflare_blocked(page_text):
            console.print("  [red]Still blocked by Cloudflare[/red]")
            return None, None

        demo_link = await self._page.evaluate("""
            () => {
                const sb = document.querySelector('.stream-box[data-demo-link]');
                if (sb) return sb.getAttribute('data-demo-link');
                const hl = document.querySelector('a[href*="/download/demo/"]');
                if (hl) return hl.getAttribute('href');
                return null;
            }
        """)

        if not demo_link:
            return None, None

        demo_id = demo_link.rstrip("/").split("/")[-1]
        demo_url = urljoin(HLTV_BASE, demo_link)
        return demo_id, demo_url

    # ── download + extract ───────────────────────────────────────
    async def download_demo(self, match: dict, demo_url: str) -> Path | None:
        safe_name = re.sub(r"[^\w\-]", "_", match.get("matchUrl", "demo").split("/")[-1] or "demo")
        existing = list(self.output_dir.glob(f"{safe_name}*"))
        if existing:
            console.print(f"  [yellow]File already exists: {existing[0].name}[/yellow]")
            resp = input("  Overwrite? [y/N]: ").strip().lower()
            if resp != "y":
                console.print("  [dim]Skipped[/dim]")
                return None
            for f in existing:
                f.unlink()

        console.print("  [bold]Downloading demo...[/bold]")

        try:
            async with self._page.expect_download(timeout=120000) as download_info:
                try:
                    await self._page.goto(demo_url, wait_until="commit", timeout=30000)
                except Exception:
                    pass
            download = await download_info.value
            suggested = download.suggested_filename
            ext = Path(suggested).suffix
            tmp_path = self.output_dir / f"_tmp_{safe_name}{ext}"
            await download.save_as(str(tmp_path))
            size_mb = tmp_path.stat().st_size / 1024 / 1024
            console.print(f"  [green]Downloaded: {tmp_path.name} ({size_mb:.1f} MB)[/green]")

            ext_lower = ext.lower()
            if ext_lower == ".gz":
                console.print("  [dim]Extracting .gz...[/dim]")
                out_path = self.output_dir / f"{safe_name}.dem"
                with gzip.open(tmp_path, "rb") as fin, open(out_path, "wb") as fout:
                    shutil.copyfileobj(fin, fout)
                tmp_path.unlink()
                console.print(f"  [green]Extracted: {out_path.name}[/green]")
                return out_path

            elif ext_lower == ".rar":
                console.print("  [dim]Extracting .rar...[/dim]")
                result = _extract_rar(tmp_path, self.output_dir)
                if result:
                    return result
                # If extraction fails, keep .rar file
                console.print("  [yellow]Could not extract RAR. File saved as .rar[/yellow]")
                return tmp_path

            elif ext_lower == ".zip":
                console.print("  [dim]Extracting .zip...[/dim]")
                with zipfile.ZipFile(tmp_path, "r") as zf:
                    for name in zf.namelist():
                        if name.endswith(".dem"):
                            zf.extract(name, self.output_dir)
                            extracted = self.output_dir / name
                            console.print(f"  [green]Extracted: {extracted.name}[/green]")
                            tmp_path.unlink()
                            return extracted
                console.print("  [yellow]No .dem in ZIP[/yellow]")
                return tmp_path

            else:
                # Already .dem or unknown — just rename
                if not ext_lower:
                    new_path = tmp_path.with_suffix(".dem")
                    tmp_path.rename(new_path)
                    return new_path
                return tmp_path

        except Exception as e:
            console.print(f"  [red]Download failed: {e}[/red]")
            return None


# ── main ─────────────────────────────────────────────────────────
async def main_async(args: argparse.Namespace) -> None:
    d = HLTVDemoDownloader(
        date=args.date,
        event_filter=args.event,
        output_dir=Path(args.output) if args.output else None,
        headless=args.headless,
        clear_cache=args.clear_cache,
    )
    await d.start()
    try:
        matches = await d.fetch_matches()
        d.display_matches(matches)
        if not matches:
            return

        console.print("\n[bold]Enter match numbers[/bold] (e.g. 1 or 1,3,5)")
        choice = input("> ").strip().replace("，", ",")
        indices = []
        for part in choice.split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(matches):
                    indices.append(idx)
                else:
                    console.print(f"  [yellow]#{part} out of range, skipped[/yellow]")
        if not indices:
            console.print("[red]No valid selections.[/red]")
            return

        for idx in indices:
            match = matches[idx]
            console.print(f"\n[bold]--- #{idx + 1}: {match['team1']} vs {match['team2']} ---[/bold]")
            demo_id, demo_url = await d.check_demo(match["matchUrl"])
            if not demo_url:
                console.print("  [red]No demo available[/red]")
                continue
            console.print(f"  Demo ID: {demo_id}")
            result = await d.download_demo(match, demo_url)
            if result:
                console.print(f"  [bold green]Done: {result}[/bold green]")
    finally:
        await d.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="CS2 HLTV Demo Downloader")
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument("--event", "-e", default=None, help="Filter by event name")
    parser.add_argument("--output", "-o", default=None, help="Output directory")
    parser.add_argument("--headless", action="store_true", help="Run headless")
    parser.add_argument("--clear-cache", action="store_true", help="Clear browser profile")
    args = parser.parse_args()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.date):
        console.print("[red]Date must be YYYY-MM-DD format[/red]")
        sys.exit(1)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
