#!/usr/bin/env python3
"""
Real-Time Live Meeting Monitor, Audio ASR Processor & Auto-Archiver
for Durham Politics Tracker.

Capabilities:
1. Continuously polls Durham City Council (@CityofDurhamNC), DPS Board
   (@durhampublicschoolsboardof2290), and Durham BOCC (@DCoWebmaster) for
   ongoing live broadcasts (`live_status == "is_live"`).
2. When a live meeting is in progress:
   - Activates `/durhampolitics/live_status.json` (`is_live: true`) so the
     'Live Meeting in Progress' tab appears on rannbar-on.com/durhampolitics.
   - Captures real-time audio directly from the live video stream via
     `yt-dlp` + `ffmpeg` (16kHz PCM) — NEVER relies on captions.
   - Transcribes rolling 20-second audio chunks locally via `faster-whisper`,
     normalizes Durham official names, and updates the running transcript.
   - Every 60 seconds, recomputes a dynamic executive summary, chronological
     topics so far, and observed motions/votes, writing `live_status.json`
     and pushing to GitHub Pages.
3. Upon meeting completion (and on periodic archive checks for any newly
   ended meeting):
   - Clears `is_live: false` in `live_status.json`.
   - Uses `dual_transcriber.py` (audio ASR + captions reliability comparison,
     preserving the full audio transcript) to archive the meeting into
     `durham_politics.db`, generate its Executive Summary PDF, rebuild the
     static site, and push to `origin/main`.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BASE_DIR.parent))
if "/home/rann/src" not in sys.path and Path("/home/rann/src").exists():
    sys.path.insert(0, "/home/rann/src")

from durham_politics_tracker.config import BODIES, OUTPUT_DIR
from durham_politics_tracker.database import DurhamPoliticsDB
from durham_politics_tracker.dual_transcriber import transcribe_dual_pick_best
from durham_politics_tracker.scripts.build_pdfs_and_update_db import (
    SUMMARIES_DIR,
    build_meeting_pdf,
    format_seconds,
)
from durham_politics_tracker.site_generator import generate_durhampolitics_page
try:
    from durham_politics_tracker.durham_officials import correct_transcript_names
except ImportError:
    from video_topic_summarizer.durham_officials import correct_transcript_names

YT_DLP = shutil.which("yt-dlp") or "/home/rann/.local/bin/yt-dlp"
WEBSITE_REPO = OUTPUT_DIR.parent
LIVE_STATUS_PATH = OUTPUT_DIR / "live_status.json"
CACHE_DIR = BASE_DIR / "transcripts_cache"

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

CATEGORY_RULES = [
    ("Budget & Taxes", ["budget", "tax", "appropriation", "audit", "fiscal", "finance", "bond", "million"]),
    ("Staff Compensation & Labor", ["salary", "pay", "supplement", "dae", "union", "wage", "worker", "classified"]),
    ("Zoning & Development (SCAD)", ["scad", "zoning", "rezoning", "annexation", "subdivision", "udo", "development"]),
    ("Affordable Housing", ["housing", "affordable", "tenant", "eviction", "homeless", "encampment"]),
    ("Community Safety & HEART", ["heart", "police", "sheriff", "safety", "crime", "axon", "surveillance", "911"]),
    ("School Facilities & Closures", ["consolidation", "closure", "facility", "school", "campus", "mgt", "construction"]),
    ("Transit & Public Works", ["transit", "bus", "godurham", "sidewalk", "water", "sewer", "paving", "road"]),
]


def classify_category(text: str) -> str:
    tl = text.lower()
    for cat, kws in CATEGORY_RULES:
        if any(k in tl for k in kws):
            return cat
    return "Governance & Transparency"


def git_publish(paths: List[str], message: str) -> bool:
    try:
        subprocess.run(["git", "-C", str(WEBSITE_REPO), "add", *paths], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        diff = subprocess.run(["git", "-C", str(WEBSITE_REPO), "diff", "--cached", "--quiet"])
        if diff.returncode == 0:
            return True
        subprocess.run(["git", "-C", str(WEBSITE_REPO), "commit", "-m", message], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(WEBSITE_REPO), "push"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        print(f"[GitPublish] Pushed: {message}", flush=True)
        # On GitHub Actions, GITHUB_TOKEN pushes don't trigger downstream push workflows,
        # so explicitly dispatch deploy_pages.yml to publish updated live_status.json / pages.
        if os.environ.get("GITHUB_ACTIONS") == "true" and shutil.which("gh"):
            subprocess.run(
                ["gh", "workflow", "run", "deploy_pages.yml"],
                cwd=str(WEBSITE_REPO),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        return True
    except Exception as e:
        print(f"[GitPublish] Warning: {e}", flush=True)
        return False


def detect_live_meetings() -> List[Dict[str, Any]]:
    """Checks all 3 official YouTube channels for active live broadcasts."""
    live_found = []
    for body_id, url in CHANNEL_STREAMS.items():
        cmd = [YT_DLP, "--flat-playlist", "--dump-json", "--playlist-end", "8", url]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("live_status") == "is_live":
                    title = data.get("title", "")
                    if any(k in title.lower() for k in MEETING_KEYWORDS[body_id]):
                        vid = data["id"]
                        live_found.append({
                            "body_id": body_id,
                            "body_name": BODIES[body_id]["name"],
                            "video_id": vid,
                            "video_url": f"https://www.youtube.com/watch?v={vid}",
                            "title": title,
                        })
        except Exception as e:
            print(f"[LiveDetect] Warning for {body_id}: {e}", flush=True)
    return live_found


def resolve_live_audio_url(video_url: str) -> Optional[str]:
    cmd = [
        YT_DLP,
        "--remote-components", "ejs:github",
        "-g",
        "-f", "bestaudio/best",
        "--no-warnings",
        video_url,
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
    if res.returncode != 0:
        return None
    urls = [u.strip() for u in res.stdout.splitlines() if u.strip().startswith("http")]
    return urls[-1] if urls else None


def synthesize_live_summary(
    body_name: str,
    title: str,
    transcript_lines: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Dynamically synthesizes an executive summary, chronological topics so far,
    and observed motions/votes from the live running audio transcript.
    """
    if not transcript_lines:
        return {
            "executive_summary": f"Live real-time audio processing active for {title}. Waiting for opening remarks...",
            "topics_so_far": [],
            "votes_so_far": [],
        }

    # Group lines into ~3-minute topical blocks or explicit agenda item transitions
    topic_triggers = re.compile(
        r"\b(item\s+(?:number\s+)?\d+|next\s+item|public\s+hearing|consent\s+agenda|"
        r"general\s+business\s+agenda|presentation\s+on|moving\s+on\s+to|budget\s+update|"
        r"rezoning|annexation|closed\s+session|public\s+comment)\b",
        re.IGNORECASE,
    )
    vote_triggers = re.compile(
        r"\b(motion\s+(?:passes|carries|fails|approved|adopted)|passes\s+unanimously|"
        r"carries\s+\d+\s*(?:to|-)\s*\d+|passes\s+\d+\s*(?:to|-)\s*\d+|"
        r"all\s+(?:those\s+)?in\s+favor|so\s+moved|seconded\s+by)\b",
        re.IGNORECASE,
    )

    topics: List[Dict[str, Any]] = []
    votes: List[Dict[str, Any]] = []

    current_block: List[Dict[str, Any]] = []
    block_start = transcript_lines[0]["seconds"]
    block_title = "Opening Remarks & Call to Order"

    def flush_block(blk, start_s, blk_title):
        if not blk:
            return
        combined = " ".join(x["text"] for x in blk).strip()
        if len(combined) < 40:
            return
        # Take first 2-3 informative sentences as running summary
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", combined) if len(s.strip()) > 20]
        summary = " ".join(sents[:3])[:420]
        if len(summary) == 420:
            summary = summary.rsplit(" ", 1)[0] + "..."
        vote_note = ""
        for x in blk:
            if vote_triggers.search(x["text"]):
                vote_note = x["text"][:180]
                break
        topics.append({
            "title": blk_title,
            "category": classify_category(combined),
            "start_seconds": start_s,
            "timestamp_label": format_seconds(start_s),
            "discussion_summary": summary,
            "vote_summary": vote_note or "Ongoing discussion / no formal vote detected in segment",
        })

    for line in transcript_lines:
        txt = line["text"]
        sec = line["seconds"]
        m_top = topic_triggers.search(txt)
        if m_top and (sec - block_start >= 60 or len(current_block) >= 6):
            flush_block(current_block, block_start, block_title)
            current_block = [line]
            block_start = sec
            snippet = txt[m_top.start():m_top.start() + 70].strip(" ,.;:-")
            block_title = snippet[0].upper() + snippet[1:] if snippet else "Agenda Discussion"
        else:
            current_block.append(line)
            if sec - block_start >= 300 and len(current_block) >= 12:
                flush_block(current_block, block_start, block_title)
                current_block = []
                block_start = sec
                block_title = f"Continued Deliberation ({format_seconds(sec)})"

        if vote_triggers.search(txt):
            # Avoid duplicate votes within 30 seconds
            if not votes or (sec - votes[-1]["timestamp_seconds"]) >= 30:
                tally_m = re.search(r"\b(\d+)\s*(?:to|-)\s*(\d+)\b", txt, re.IGNORECASE)
                is_unam = "unanimous" in txt.lower()
                outcome = "Failed" if "fail" in txt.lower() else "Passed"
                tally = f"{tally_m.group(1)}-{tally_m.group(2)}" if tally_m else ("Unanimous" if is_unam else "Voice / Roll Call")
                # Gather surrounding ~4 lines of discussion context leading up to this vote
                ctx_lines = [x["text"] for x in current_block[-5:]]
                disc_ctx = " ".join(ctx_lines).strip()[:650]
                votes.append({
                    "item_title": block_title,
                    "outcome": outcome,
                    "tally": tally,
                    "timestamp_seconds": sec,
                    "timestamp_label": format_seconds(sec),
                    "discussion_detail": disc_ctx,
                    "notes": txt[:200],
                })

    flush_block(current_block, block_start, block_title)

    elapsed_min = max(1, int((transcript_lines[-1]["seconds"] - transcript_lines[0]["seconds"]) // 60))
    cat_counts: Dict[str, int] = {}
    for t in topics:
        cat_counts[t["category"]] = cat_counts.get(t["category"], 0) + 1
    top_cats = ", ".join(sorted(cat_counts, key=cat_counts.get, reverse=True)[:3]) or "General Governance"

    exec_summary = (
        f"Live real-time audio analysis of {body_name} — {title} ({elapsed_min} min transcribed so far, "
        f"{len(transcript_lines)} speech segments). Primary areas covered: {top_cats}. "
        f"Identified {len(topics)} discussion segment(s) and {len(votes)} motion/vote cue(s) so far."
    )

    return {
        "executive_summary": exec_summary,
        "topics_so_far": topics,
        "votes_so_far": votes,
    }


def write_live_status(payload: Dict[str, Any], push: bool = True):
    LIVE_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIVE_STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if push:
        git_publish(["durhampolitics/live_status.json"], f"Live meeting update: {payload.get('title') or 'offline'}")


def process_live_meeting(live_info: Dict[str, Any], model_size: str = "tiny.en", max_seconds: Optional[int] = None):
    """
    Captures live video audio in real time (no captions), runs faster-whisper ASR
    chunk-by-chunk, updates executive summary every 60 seconds, and archives the
    completed meeting with a PDF upon stream end.
    """
    from faster_whisper import WhisperModel

    body_id = live_info["body_id"]
    vid = live_info["video_id"]
    video_url = live_info["video_url"]
    title = live_info["title"]
    started_at = datetime.now(timezone.utc).isoformat()

    print(f"[LiveDaemon] Starting real-time audio processing for {body_id.upper()}: {title} ({vid})", flush=True)
    model = WhisperModel(model_size, device="auto", compute_type="int8")

    transcript_lines: List[Dict[str, Any]] = []
    status_payload = {
        "is_live": True,
        "body_id": body_id,
        "body_name": BODIES[body_id]["name"],
        "video_id": vid,
        "video_url": video_url,
        "title": title,
        "started_at": started_at,
        "summary_updated_at": started_at,
        "transcript_updated_at": started_at,
        "executive_summary": f"Connected to live {BODIES[body_id]['name']} stream. Real-time audio ASR initializing...",
        "topics_so_far": [],
        "votes_so_far": [],
        "debates_so_far": [],
        "transcript_lines": [],
        "source_mode": "realtime_audio_asr",
    }
    write_live_status(status_payload, push=True)

    stream_url = resolve_live_audio_url(video_url)
    if not stream_url:
        print(f"[LiveDaemon] Could not resolve live audio stream URL for {video_url}", flush=True)
        status_payload["is_live"] = False
        write_live_status(status_payload, push=True)
        return

    # Stream continuous 16kHz mono PCM directly from live HLS video via ffmpeg
    ff_cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error",
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-i", stream_url,
        "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", "16000", "-",
    ]
    proc = subprocess.Popen(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    chunk_seconds = 20
    bytes_per_chunk = 16000 * 2 * chunk_seconds
    elapsed_audio_sec = 0
    last_summary_push = time.time()
    start_wall = time.time()

    try:
        while True:
            if max_seconds and (time.time() - start_wall) >= max_seconds:
                break
            raw = proc.stdout.read(bytes_per_chunk)
            if not raw or len(raw) < 16000 * 2:
                break

            audio_np = np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0
            segments, _ = model.transcribe(audio_np, vad_filter=True)
            for seg in segments:
                txt = correct_transcript_names(seg.text.strip())
                if txt:
                    ts_sec = int(elapsed_audio_sec + seg.start)
                    transcript_lines.append({
                        "seconds": ts_sec,
                        "timestamp": format_seconds(ts_sec),
                        "text": txt,
                    })

            elapsed_audio_sec += chunk_seconds
            now_iso = datetime.now(timezone.utc).isoformat()
            status_payload["transcript_lines"] = transcript_lines[-400:]
            status_payload["transcript_updated_at"] = now_iso

            # Update executive summary & publish every 60 seconds
            if (time.time() - last_summary_push) >= 60.0:
                synth = synthesize_live_summary(BODIES[body_id]["name"], title, transcript_lines)
                status_payload.update(synth)
                status_payload["summary_updated_at"] = now_iso
                write_live_status(status_payload, push=True)
                last_summary_push = time.time()
            else:
                write_live_status(status_payload, push=False)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    # Save full real-time audio transcript to cache
    out_dir = CACHE_DIR / body_id
    out_dir.mkdir(parents=True, exist_ok=True)
    full_txt = "\n".join(f"[{l['timestamp']}] {l['text']}" for l in transcript_lines)
    if full_txt:
        (out_dir / f"{vid}.audio.txt").write_text(full_txt, encoding="utf-8")
        (out_dir / f"{vid}.txt").write_text(full_txt, encoding="utf-8")

    # Mark offline and archive into DB + Executive Summary PDF + static site
    status_payload["is_live"] = False
    write_live_status(status_payload, push=False)
    archive_completed_meeting(body_id, vid, title, video_url, transcript_lines)


def archive_completed_meeting(
    body_id: str,
    vid: str,
    title: str,
    video_url: str,
    transcript_lines: List[Dict[str, Any]],
    date_str: Optional[str] = None,
):
    """Archives a completed meeting into durham_politics.db, builds its PDF, and pushes."""
    date_str = date_str or datetime.now().strftime("%Y-%m-%d")
    meeting_id = f"{body_id}_{date_str.replace('-', '_')}_{vid}"
    synth = synthesize_live_summary(BODIES[body_id]["name"], title, transcript_lines)
    dur_sec = transcript_lines[-1]["seconds"] if transcript_lines else 0
    dur_str = f"{dur_sec // 3600}h {(dur_sec % 3600) // 60:02d}m" if dur_sec >= 3600 else f"{max(1, dur_sec // 60)}m"

    db = DurhamPoliticsDB()
    db.insert_meeting({
        "id": meeting_id,
        "body_id": body_id,
        "title": title,
        "meeting_type": "Work Session" if "work session" in title.lower() else "Regular Meeting",
        "date": date_str,
        "video_url": video_url,
        "duration": dur_str,
        "executive_summary": synth["executive_summary"],
        "tags": list({t["category"] for t in synth["topics_so_far"]})[:3] or ["Governance & Transparency"],
    })
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE meetings SET summary_pdf_url = ? WHERE id = ?",
            (f"/durhampolitics/summaries/{meeting_id}.pdf", meeting_id),
        )
        conn.execute("DELETE FROM agenda_items WHERE meeting_id = ?", (meeting_id,))
        for idx, t in enumerate(synth["topics_so_far"], 1):
            conn.execute("""
                INSERT OR REPLACE INTO agenda_items (
                    id, meeting_id, item_number, title, category,
                    description, discussion_summary, start_seconds, timestamp_label, vote_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"ag_{meeting_id}_{idx:02d}", meeting_id, f"Topic {idx}",
                t["title"], t["category"], "", t["discussion_summary"],
                t["start_seconds"], t["timestamp_label"], t["vote_summary"],
            ))
        for idx, v in enumerate(synth["votes_so_far"], 1):
            db.insert_vote({
                "id": f"v_{meeting_id}_{idx:02d}",
                "meeting_id": meeting_id,
                "item_title": v["item_title"],
                "outcome": v["outcome"],
                "tally": v["tally"],
                "ayes": ["All present members"] if v["outcome"] == "Passed" else [],
                "nays": [],
                "notes": v.get("notes", ""),
                "category": classify_category(v["item_title"]),
            })
            conn.execute(
                "UPDATE votes SET timestamp_seconds = ?, timestamp_label = ?, discussion_detail = ? WHERE id = ?",
                (v["timestamp_seconds"], v["timestamp_label"], v.get("discussion_detail", ""), f"v_{meeting_id}_{idx:02d}"),
            )

    dataset = db.export_full_dataset()
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    for mtg in dataset["meetings"]:
        if mtg["id"] == meeting_id:
            build_meeting_pdf(mtg, SUMMARIES_DIR / f"{meeting_id}.pdf")
            break

    generate_durhampolitics_page()
    publish_paths = [
        "durhampolitics.html",
        "durhampolitics/index.html",
        "durhampolitics/live.html",
        "durhampolitics/live_status.json",
        "durhampolitics/durham_politics_data.json",
        f"durhampolitics/summaries/{meeting_id}.pdf",
    ]
    if (WEBSITE_REPO / "durham_politics_tracker" / "durham_politics.db").exists():
        publish_paths.append("durham_politics_tracker/durham_politics.db")
    git_publish(
        publish_paths,
        f"Archive completed meeting: {title}",
    )


def scan_and_archive_newly_finished_meetings():
    """Checks all 3 channels for recently ended meetings not yet in DB and runs dual_transcriber."""
    db = DurhamPoliticsDB()
    with db.get_connection() as conn:
        existing_urls = {r[0] for r in conn.execute("SELECT video_url FROM meetings").fetchall() if r[0]}

    for body_id, url in CHANNEL_STREAMS.items():
        cmd = [YT_DLP, "--flat-playlist", "--dump-json", "--playlist-end", "10", url]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=45)
            for line in res.stdout.splitlines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("live_status") in ("is_live", "is_upcoming") or not data.get("duration"):
                    continue
                vid = data.get("id")
                title = data.get("title", "")
                if not vid or not any(k in title.lower() for k in MEETING_KEYWORDS[body_id]):
                    continue
                vurl = f"https://www.youtube.com/watch?v={vid}"
                if vurl in existing_urls:
                    continue
                print(f"[AutoArchive] Newly completed meeting detected: {body_id.upper()} | {title} ({vid})", flush=True)
                best_text, meta = transcribe_dual_pick_best(body_id, vid, vurl, duration_sec=data.get("duration") or 0)
                if not best_text:
                    continue
                lines = []
                for ln in best_text.splitlines():
                    m = re.match(r"\[(\d{2}:\d{2}:\d{2})\]\s*(.*)", ln)
                    if m:
                        h, mi, s = map(int, m.group(1).split(":"))
                        lines.append({"seconds": h * 3600 + mi * 60 + s, "timestamp": m.group(1), "text": m.group(2)})
                archive_completed_meeting(body_id, vid, title, vurl, lines)
                existing_urls.add(vurl)
        except Exception as e:
            print(f"[AutoArchive] Warning for {body_id}: {e}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Durham Politics Tracker Real-Time Live Meeting Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single live + archive check cycle")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in the background")
    parser.add_argument("--poll-seconds", type=int, default=60, help="Seconds between live checks (default: 60)")
    args = parser.parse_args()

    if args.once or not args.daemon:
        live_list = detect_live_meetings()
        if live_list:
            process_live_meeting(live_list[0])
        else:
            print("[LiveDaemon] No meeting currently live.", flush=True)
            scan_and_archive_newly_finished_meetings()
        return

    print(f"[LiveDaemon] Continuous monitor started (polling every {args.poll_seconds}s)...", flush=True)
    last_archive_scan = 0.0
    while True:
        live_list = detect_live_meetings()
        if live_list:
            process_live_meeting(live_list[0])
            last_archive_scan = time.time()
        elif (time.time() - last_archive_scan) >= 900:
            scan_and_archive_newly_finished_meetings()
            last_archive_scan = time.time()
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    main()
