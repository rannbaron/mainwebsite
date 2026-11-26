#!/usr/bin/env python3
"""
Lightweight Schedule Fetcher & Live Meeting Pre-Checker (Python stdlib only).

Designed to run in ~5 seconds on GitHub Actions `ubuntu-slim` ($0.002/min)
with ZERO `apt-get` or `pip install` dependencies:
  1. Fetches upcoming meeting schedules & agenda links from official Durham portals:
     - BOCC: Legistar OData REST API (webapi.legistar.com/v1/durhamcounty/events)
     - City Council: durhamnc.gov/AgendaCenter & @CityofDurhamNC/streams
     - DPS Board: dpsnc.net & @durhampublicschoolsboardof2290/streams
  2. Performs a fast HTTP check on all 3 official YouTube `/streams` pages to
     detect if a meeting is currently LIVE right now, or if we are inside a
     scheduled meeting start window, or (when --check-archive is set) if a
     newly finished meeting video isn't yet in `durham_politics.db`.
  3. Writes `should_run=true/false` and `reason=...` to `$GITHUB_OUTPUT` so
     the heavy `ubuntu-latest` (`ffmpeg` + `faster-whisper`) job ONLY boots
     when there is actually a live or newly finished meeting to process.
"""

import argparse
import json
import os
import re
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "durham_politics.db"
_REPO_SITE_DIR = BASE_DIR.parent / "durhampolitics"
_LOCAL_SITE_DIR = Path("/home/rann/src/website/mainwebsite/durhampolitics")
OUTPUT_DIR = Path(
    os.environ.get(
        "DURHAM_OUTPUT_DIR",
        str(_REPO_SITE_DIR if (_REPO_SITE_DIR.exists() or (BASE_DIR.parent / ".github").exists()) else _LOCAL_SITE_DIR),
    )
)
UPCOMING_PATH = OUTPUT_DIR / "upcoming_meetings.json"
ET = ZoneInfo("America/New_York")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

CHANNEL_STREAMS = {
    "city": "https://www.youtube.com/@CityofDurhamNC/streams",
    "dps": "https://www.youtube.com/@durhampublicschoolsboardof2290/streams",
    "bocc": "https://www.youtube.com/@DCoWebmaster/streams",
}

MEETING_KEYWORDS = {
    "city": ["city council", "council meeting", "work session", "budget"],
    "dps": ["board of education", "school board", "work session", "monthly", "special", "meeting"],
    "bocc": ["bocc", "county commissioners", "board of commissioners", "work session", "regular session", "budget"],
}


def http_get(url: str, timeout: int = 15, accept: str = "*/*") -> Optional[str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Precheck] HTTP warning for {url}: {e}")
        return None


def fetch_bocc_legistar_schedule() -> List[Dict[str, Any]]:
    """Queries Durham County's public Legistar OData API for upcoming BOCC meetings."""
    today = datetime.now(ET).strftime("%Y-%m-%d")
    q = urllib.parse.quote(f"EventDate ge datetime'{today}'")
    url = f"https://webapi.legistar.com/v1/durhamcounty/events?$filter={q}&$orderby=EventDate%20asc&$top=20"
    raw = http_get(url, accept="application/json")
    if not raw:
        return []
    events = []
    try:
        data = json.loads(raw)
        for ev in data:
            body = (ev.get("EventBodyName") or "").strip()
            if not any(k in body.lower() for k in ("commissioner", "bocc", "board of county")):
                continue
            date_part = (ev.get("EventDate") or "")[:10]
            time_part = (ev.get("EventTime") or "7:00 PM").strip()
            events.append({
                "body_id": "bocc",
                "title": body,
                "date": date_part,
                "time_et": time_part,
                "agenda_url": ev.get("EventAgendaFile") or ev.get("EventInSiteURL") or "https://durhamcounty.legistar.com/Calendar.aspx",
                "source": "legistar_api",
            })
    except Exception as e:
        print(f"[Precheck] Legistar parse warning: {e}")
    return events


def parse_youtube_streams_page(body_id: str, html: str) -> Dict[str, Any]:
    """
    Parses YouTube /streams page HTML (ytInitialData JSON) using stdlib only
    to detect:
      - live_videos: currently broadcasting live streams
      - upcoming_videos: scheduled upcoming streams with start timestamps
      - recent_completed: recent ended meeting video IDs
    """
    result = {"live": [], "upcoming": [], "recent_completed": []}
    if not html:
        return result

    m = re.search(r"var\s+ytInitialData\s*=\s*(\{.*?\});\s*</script>", html, re.S)
    if not m:
        m = re.search(r"ytInitialData\"\s*:\s*(\{.*?\})\s*,\s*\"ytInitialPlayerResponse", html, re.S)
    if not m:
        return result

    try:
        data = json.loads(m.group(1))
    except Exception:
        return result

    # Recursively walk for videoRenderer objects
    stack = [data]
    seen = set()
    kws = MEETING_KEYWORDS[body_id]

    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if "videoRenderer" in node and isinstance(node["videoRenderer"], dict):
                vr = node["videoRenderer"]
                vid = vr.get("videoId")
                if vid and vid not in seen:
                    seen.add(vid)
                    title_runs = vr.get("title", {}).get("runs", [])
                    title = "".join(r.get("text", "") for r in title_runs) or vr.get("title", {}).get("simpleText", "")
                    if not any(k in title.lower() for k in kws):
                        continue

                    # Detect LIVE / UPCOMING via thumbnailOverlays or badges or upcomingEventData
                    vr_str = json.dumps(vr)
                    is_upcoming = "upcomingEventData" in vr
                    is_live = (
                        '"style":"LIVE"' in vr_str
                        or '"iconType":"LIVE"' in vr_str
                        or '"label":"LIVE"' in vr_str
                    ) and not is_upcoming

                    if is_live:
                        result["live"].append({
                            "body_id": body_id,
                            "video_id": vid,
                            "title": title,
                            "video_url": f"https://www.youtube.com/watch?v={vid}",
                        })
                    elif is_upcoming:
                        start_ts = vr.get("upcomingEventData", {}).get("startTime")
                        date_str, time_str = "", ""
                        if start_ts and str(start_ts).isdigit():
                            dt_et = datetime.fromtimestamp(int(start_ts), tz=ET)
                            date_str = dt_et.strftime("%Y-%m-%d")
                            time_str = dt_et.strftime("%-I:%M %p")
                        result["upcoming"].append({
                            "body_id": body_id,
                            "video_id": vid,
                            "title": title,
                            "date": date_str,
                            "time_et": time_str,
                            "start_epoch": int(start_ts) if (start_ts and str(start_ts).isdigit()) else None,
                            "video_url": f"https://www.youtube.com/watch?v={vid}",
                            "source": "youtube_upcoming",
                        })
                    else:
                        if len(result["recent_completed"]) < 6:
                            result["recent_completed"].append({
                                "body_id": body_id,
                                "video_id": vid,
                                "title": title,
                                "video_url": f"https://www.youtube.com/watch?v={vid}",
                            })
            else:
                for v in node.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
        elif isinstance(node, list):
            for item in node:
                if isinstance(item, (dict, list)):
                    stack.append(item)
    return result


def parse_et_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    t_clean = (time_str or "7:00 PM").strip().upper()
    for fmt in ("%Y-%m-%d %I:%M %p", "%Y-%m-%d %I:%M%p", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(f"{date_str} {t_clean}", fmt).replace(tzinfo=ET)
        except ValueError:
            continue
    return None


def is_within_scheduled_window(upcoming: List[Dict[str, Any]], now_et: datetime) -> Optional[Dict[str, Any]]:
    """Returns a scheduled meeting if now is within [start - 10m, start + 45m]."""
    for ev in upcoming:
        dt = None
        if ev.get("start_epoch"):
            dt = datetime.fromtimestamp(ev["start_epoch"], tz=ET)
        else:
            dt = parse_et_datetime(ev.get("date", ""), ev.get("time_et", ""))
        if dt:
            delta_min = (now_et - dt).total_seconds() / 60.0
            if -10.0 <= delta_min <= 45.0:
                return ev
    return None


def load_existing_video_urls() -> set:
    if not DB_PATH.exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro&immutable=1", uri=True)
        urls = {r[0] for r in conn.execute("SELECT video_url FROM meetings").fetchall() if r[0]}
        conn.close()
        return urls
    except Exception:
        return set()


def write_github_output(kv: Dict[str, str]):
    out_file = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"[Output] {k}={v}")
    if out_file:
        with open(out_file, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def main():
    parser = argparse.ArgumentParser(description="Lightweight schedule sync & live pre-checker for ubuntu-slim")
    parser.add_argument("--sync-schedule", action="store_true", help="Refresh upcoming_meetings.json from official portals")
    parser.add_argument("--check-archive", action="store_true", help="Also trigger if a newly finished meeting isn't in DB")
    args = parser.parse_args()

    now_et = datetime.now(ET)
    live_hits = []
    upcoming_all = []
    recent_completed = []

    # 1. Fast check all 3 YouTube /streams pages via pure stdlib HTTP
    for body_id, url in CHANNEL_STREAMS.items():
        html = http_get(url)
        parsed = parse_youtube_streams_page(body_id, html or "")
        live_hits.extend(parsed["live"])
        upcoming_all.extend(parsed["upcoming"])
        recent_completed.extend(parsed["recent_completed"])

    # 2. Refresh official portal schedule when --sync-schedule or if cache missing/stale (>12h)
    cached_upcoming = []
    cache_stale = True
    if UPCOMING_PATH.exists():
        try:
            cached = json.loads(UPCOMING_PATH.read_text(encoding="utf-8"))
            cached_upcoming = cached.get("meetings", [])
            gen = cached.get("updated_at")
            if gen:
                age_hr = (datetime.now(timezone.utc) - datetime.fromisoformat(gen)).total_seconds() / 3600.0
                cache_stale = age_hr >= 12.0
        except Exception:
            pass

    if args.sync_schedule or cache_stale:
        bocc_sched = fetch_bocc_legistar_schedule()
        # Merge deduplicated upcoming meetings
        merged = []
        seen_keys = set()
        for ev in upcoming_all + bocc_sched:
            key = (ev.get("body_id"), ev.get("date"), ev.get("title", "")[:40].lower())
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(ev)
        merged.sort(key=lambda x: (x.get("date") or "9999-99-99", x.get("time_et") or ""))
        UPCOMING_PATH.parent.mkdir(parents=True, exist_ok=True)
        UPCOMING_PATH.write_text(json.dumps({
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "portals": {
                "bocc": "https://durhamcounty.legistar.com/Calendar.aspx",
                "city": "https://cityordinances.durhamnc.gov/OnBaseAgendaOnline",
                "city_calendar": "https://www.durhamnc.gov/AgendaCenter",
                "dps": "https://www.dpsnc.net/page/board-of-education",
            },
            "meetings": merged,
        }, indent=2), encoding="utf-8")
        print(f"[Precheck] Updated {UPCOMING_PATH} with {len(merged)} upcoming meetings.")
        active_upcoming = merged
    else:
        active_upcoming = upcoming_all + cached_upcoming

    # 3. Decide whether to wake up the heavy ubuntu-latest job
    should_run = False
    reason = "idle"
    live_body = ""

    if live_hits:
        should_run = True
        live_body = live_hits[0]["body_id"]
        reason = f"live_stream_detected:{live_body}:{live_hits[0]['video_id']}"
    else:
        sched_hit = is_within_scheduled_window(active_upcoming, now_et)
        if sched_hit:
            should_run = True
            live_body = sched_hit.get("body_id", "")
            reason = f"scheduled_meeting_window:{live_body}:{sched_hit.get('date')}"
        elif args.check_archive:
            existing = load_existing_video_urls()
            unarchived = [v for v in recent_completed if v["video_url"] not in existing]
            if unarchived:
                should_run = True
                live_body = unarchived[0]["body_id"]
                reason = f"unarchived_completed_meeting:{live_body}:{unarchived[0]['video_id']}"

    write_github_output({
        "should_run": "true" if should_run else "false",
        "reason": reason,
        "live_body": live_body,
    })


if __name__ == "__main__":
    main()
