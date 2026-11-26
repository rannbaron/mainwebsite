#!/usr/bin/env python3
"""
Dual Audio + Caption Transcriber for Durham Politics Tracker.

In all future ingestion runs:
1. Extracts YouTube captions (VTT) when available.
2. Downloads audio and runs local ASR (faster-whisper / whisper) when available.
3. Scores both transcripts for reliability (completeness vs video duration,
   official-name recognition density, low repetition/garble ratio) and picks
   the more reliable transcript.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR.parent) not in sys.path:
    sys.path.insert(0, str(BASE_DIR.parent))
if "/home/rann/src" not in sys.path and Path("/home/rann/src").exists():
    sys.path.insert(0, "/home/rann/src")

try:
    from .transcript_parser import parse_vtt
    from .durham_officials import correct_transcript_names, ALL_OFFICIALS
except ImportError:
    from video_topic_summarizer.transcript_parser import parse_vtt
    from video_topic_summarizer.durham_officials import correct_transcript_names, ALL_OFFICIALS

YT_DLP = shutil.which("yt-dlp") or "/home/rann/.local/bin/yt-dlp"
CACHE_DIR = BASE_DIR / "transcripts_cache"


def score_transcript_reliability(text: str, duration_sec: float = 0.0) -> Dict[str, Any]:
    """Scores a transcript's reliability using length, official-name hits, and repetition."""
    if not text or not text.strip():
        return {"score": 0.0, "words": 0, "official_hits": 0, "repeat_ratio": 1.0}

    words = re.findall(r"\b\w+\b", text.lower())
    word_count = len(words)
    if word_count == 0:
        return {"score": 0.0, "words": 0, "official_hits": 0, "repeat_ratio": 1.0}

    # Check density of recognized Durham official names
    t_low = text.lower()
    official_hits = sum(
        t_low.count(info["canonical_name"].lower().split()[-1])
        for info in ALL_OFFICIALS.values()
    )

    # Check consecutive bigram repetition (common in broken auto-captions)
    bigrams = [tuple(words[i:i + 2]) for i in range(len(words) - 1)]
    repeat_count = sum(1 for i in range(1, len(bigrams)) if bigrams[i] == bigrams[i - 1])
    repeat_ratio = repeat_count / max(len(bigrams), 1)

    # Expected ~100-150 spoken words per minute
    expected_words = max((duration_sec / 60.0) * 110.0, 500.0) if duration_sec else 3000.0
    coverage = min(word_count / expected_words, 1.2)

    score = (coverage * 60.0) + min(official_hits * 0.5, 30.0) + max(0.0, (1.0 - repeat_ratio * 5.0) * 10.0)
    return {
        "score": round(score, 2),
        "words": word_count,
        "official_hits": official_hits,
        "repeat_ratio": round(repeat_ratio, 4),
    }


def fetch_captions_transcript(url: str, out_dir: Path, vid: str) -> Optional[str]:
    """Downloads English VTT captions and returns cleaned timestamped text."""
    out_tmpl = str(out_dir / f"{vid}.%(ext)s")
    cmd = [
        YT_DLP,
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang", "en,en-US",
        "--sub-format", "vtt",
        "--skip-download",
        "--ignore-errors",
        "--no-warnings",
        "-o", out_tmpl,
        url,
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
    vtt_files = list(out_dir.glob(f"{vid}*.vtt"))
    if not vtt_files:
        return None
    cues = parse_vtt(vtt_files[0].read_text(encoding="utf-8", errors="ignore"))
    lines = []
    for c in cues:
        ts = int(c["start"])
        h, m, s = ts // 3600, (ts % 3600) // 60, ts % 60
        txt = correct_transcript_names(c["text"])
        if txt:
            lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {txt}")
    return "\n".join(lines) if lines else None


def transcribe_audio_asr(url: str, out_dir: Path, vid: str, model_size: str = "tiny.en") -> Optional[str]:
    """Downloads audio via yt-dlp and transcribes via faster-whisper or openai-whisper."""
    audio_path = out_dir / f"{vid}.m4a"
    if not audio_path.exists():
        cmd = [
            YT_DLP,
            "--remote-components", "ejs:github",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "--no-warnings",
            "-o", str(audio_path),
            url,
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if res.returncode != 0 or not audio_path.exists():
            return None

    lines = []
    try:
        import numpy as np
        from faster_whisper import WhisperModel
        # Decode audio via ffmpeg to 16kHz mono float32 PCM to avoid PyAV metadata_errors incompatibility
        ff_cmd = [
            "ffmpeg", "-nostdin", "-threads", "0", "-i", str(audio_path),
            "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le", "-ar", "16000", "-"
        ]
        ff_res = subprocess.run(ff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if ff_res.returncode != 0 or not ff_res.stdout:
            return None
        audio_np = np.frombuffer(ff_res.stdout, np.int16).astype(np.float32) / 32768.0
        total_dur = len(audio_np) / 16000.0
        model = WhisperModel(model_size, device="auto", compute_type="int8")
        segments, info = model.transcribe(audio_np, vad_filter=True)
        dur = getattr(info, "duration", 0.0) or total_dur
        last_pct = -1
        for seg in segments:
            ts = int(seg.start)
            h, m, s = ts // 3600, (ts % 3600) // 60, ts % 60
            txt = correct_transcript_names(seg.text.strip())
            if txt:
                lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {txt}")
            if dur > 0:
                pct = min(100, int((seg.end / dur) * 100))
                if pct >= last_pct + 2 or pct == 100:
                    last_pct = pct
                    filled = pct // 5
                    bar = "█" * filled + "░" * (20 - filled)
                    eh, em, es = int(seg.end) // 3600, (int(seg.end) % 3600) // 60, int(seg.end) % 60
                    dh, dm, ds = int(dur) // 3600, (int(dur) % 3600) // 60, int(dur) % 60
                    end_char = "\n" if pct == 100 else "\r"
                    print(
                        f"  [{vid}] [{bar}] {pct:3d}% ({eh:02d}:{em:02d}:{es:02d} / {dh:02d}:{dm:02d}:{ds:02d})",
                        end=end_char,
                        flush=True,
                    )
    except ImportError:
        try:
            import whisper
            model = whisper.load_model(model_size)
            result = model.transcribe(str(audio_path))
            for seg in result.get("segments", []):
                ts = int(seg["start"])
                h, m, s = ts // 3600, (ts % 3600) // 60, ts % 60
                txt = correct_transcript_names(seg["text"].strip())
                if txt:
                    lines.append(f"[{h:02d}:{m:02d}:{s:02d}] {txt}")
        except ImportError:
            print("[DualTranscriber] Neither faster_whisper nor whisper is installed; audio ASR skipped.")
            return None

    return "\n".join(lines) if lines else None


def transcribe_dual_pick_best(
    body_id: str,
    vid: str,
    url: str,
    duration_sec: float = 0.0,
) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Runs both audio ASR and caption extraction, scores both for reliability,
    writes `{vid}.txt` with the winning transcript, and saves `{vid}.meta.json`.
    """
    out_dir = CACHE_DIR / body_id
    out_dir.mkdir(parents=True, exist_ok=True)

    cap_text = fetch_captions_transcript(url, out_dir, vid)
    cap_stats = score_transcript_reliability(cap_text or "", duration_sec)
    if cap_text:
        (out_dir / f"{vid}.captions.txt").write_text(cap_text, encoding="utf-8")

    audio_text = transcribe_audio_asr(url, out_dir, vid)
    audio_stats = score_transcript_reliability(audio_text or "", duration_sec)
    if audio_text:
        (out_dir / f"{vid}.audio.txt").write_text(audio_text, encoding="utf-8")

    # Pick the more reliable source (slight preference for audio ASR on ties)
    if audio_text and (audio_stats["score"] >= cap_stats["score"] or not cap_text):
        winner = "audio"
        best_text = audio_text
    elif cap_text:
        winner = "captions"
        best_text = cap_text
    else:
        winner = "none"
        best_text = None

    meta = {
        "vid": vid,
        "body_id": body_id,
        "winner": winner,
        "audio_stats": audio_stats,
        "captions_stats": cap_stats,
    }
    (out_dir / f"{vid}.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if best_text:
        (out_dir / f"{vid}.txt").write_text(best_text, encoding="utf-8")
    return best_text, meta
