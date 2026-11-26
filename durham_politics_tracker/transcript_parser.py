"""
Transcript Parser & Cleaner for WebVTT and SRT captions.
Handles YouTube auto-generated rolling captions, deduplication, timestamp normalization,
and cue segmentation.
"""

import re
import os
from typing import List, Dict, Any, Optional

def parse_timestamp(ts_str: str) -> float:
    """
    Parse a timestamp string like '01:48:33.840', '48:33.840', or '01:48:33,840' to seconds (float).
    """
    ts_str = ts_str.strip().replace(',', '.')
    parts = ts_str.split(':')
    try:
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            s = float(parts[2])
            return h * 3600.0 + m * 60.0 + s
        elif len(parts) == 2:
            m = float(parts[0])
            s = float(parts[1])
            return m * 60.0 + s
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        pass
    return 0.0

def format_timestamp(seconds: float, include_millis: bool = False) -> str:
    """
    Format seconds (float) into HH:MM:SS or HH:MM:SS.mmm string.
    """
    if seconds < 0:
        seconds = 0.0
    total_seconds = int(seconds)
    millis = int(round((seconds - total_seconds) * 1000))
    if millis >= 1000:
        total_seconds += 1
        millis = 0
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    if include_millis:
        return f"{h:02d}:{m:02d}:{s:02d}.{millis:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"

def dedup_text_repeats(text: str) -> str:
    """
    Remove repeated phrases, duplicated clauses, and stutter artifacts common in YouTube captions.
    """
    if not text:
        return ""
    words = text.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        half = len(words) // 2
        if words[:half] == words[half:]:
            return " ".join(words[:half])
            
    pattern = re.compile(r'\b(.+?)\s+\1\b', re.IGNORECASE)
    cleaned = pattern.sub(r'\1', text)
    
    for n in range(8, 1, -1):
        w_list = cleaned.split()
        out = []
        i = 0
        while i < len(w_list):
            chunk = w_list[i:i+n]
            if len(chunk) == n and i + 2*n <= len(w_list) and w_list[i+n:i+2*n] == chunk:
                out.extend(chunk)
                i += 2*n
            else:
                out.append(w_list[i])
                i += 1
        cleaned = " ".join(out)
    return cleaned

def clean_caption_text(raw_text: str) -> str:
    """
    Remove WebVTT inline formatting, HTML tags, karaoke timing tags (<00:00:00.000>),
    and normalizes whitespace and repeats.
    """
    if not raw_text:
        return ""
    # Remove karaoke timestamp tags like <01:48:34.480>
    text = re.sub(r'<\d{1,2}:\d{2}:\d{2}\.\d{3}>', '', raw_text)
    text = re.sub(r'<\d{1,2}:\d{2}\.\d{3}>', '', text)
    # Remove HTML/XML tags like <c>, </c>, <v Speaker>, etc.
    text = re.sub(r'</?[a-zA-Z0-9_\-\.\:\s]+>', '', text)
    # Decode HTML entities if any
    text = text.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return dedup_text_repeats(text)

def parse_vtt(vtt_content: str) -> List[Dict[str, Any]]:
    """
    Parse WebVTT content into cleaned, deduplicated cue list:
    [{'start': float, 'end': float, 'text': str, 'start_str': str, 'end_str': str}]
    """
    lines = vtt_content.splitlines()
    raw_cues = []
    
    # Regular expression for WebVTT timestamp line:
    # 00:00:00.000 --> 00:00:04.000 align:start position:0%
    ts_pattern = re.compile(
        r'^\s*(\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{3}\s*-->\s*(\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{3}'
    )
    
    idx = 0
    total_lines = len(lines)
    while idx < total_lines:
        line = lines[idx].strip()
        match = ts_pattern.match(line)
        if match:
            arrow_idx = line.find('-->')
            start_str = line[:arrow_idx].strip()
            rest = line[arrow_idx + 3:].strip()
            end_tokens = rest.split()
            end_str = end_tokens[0] if end_tokens else ""
            
            start_sec = parse_timestamp(start_str)
            end_sec = parse_timestamp(end_str)
            
            # Read text lines until empty line or next timestamp
            cue_text_lines = []
            idx += 1
            while idx < total_lines:
                text_line = lines[idx]
                if not text_line.strip():
                    break
                if ts_pattern.match(text_line):
                    idx -= 1
                    break
                cleaned_line = clean_caption_text(text_line)
                if cleaned_line:
                    cue_text_lines.append(cleaned_line)
                idx += 1
            
            full_text = " ".join(cue_text_lines).strip()
            if full_text and end_sec >= start_sec:
                raw_cues.append({
                    "start": start_sec,
                    "end": end_sec,
                    "text": full_text
                })
        idx += 1

    return deduplicate_cues(raw_cues)

def parse_srt(srt_content: str) -> List[Dict[str, Any]]:
    """
    Parse SubRip (.srt) caption content into cue list.
    """
    raw_cues = []
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    ts_pattern = re.compile(
        r'(\d{1,2}:\d{2}:\d{2}[\.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[\.,]\d{3})'
    )
    
    for block in blocks:
        lines = [b.strip() for b in block.splitlines() if b.strip()]
        if not lines:
            continue
        ts_match = None
        text_lines = []
        for line in lines:
            m = ts_pattern.search(line)
            if m:
                ts_match = m
            elif ts_match:
                cleaned = clean_caption_text(line)
                if cleaned:
                    text_lines.append(cleaned)
        
        if ts_match and text_lines:
            start_sec = parse_timestamp(ts_match.group(1))
            end_sec = parse_timestamp(ts_match.group(2))
            full_text = " ".join(text_lines).strip()
            if full_text:
                raw_cues.append({
                    "start": start_sec,
                    "end": end_sec,
                    "text": full_text
                })

    return deduplicate_cues(raw_cues)

def deduplicate_cues(raw_cues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate YouTube auto-generated rolling captions where cues repeat previous text
    or overlap heavily.
    """
    if not raw_cues:
        return []

    # Sort by start time, then end time
    sorted_cues = sorted(raw_cues, key=lambda c: (c["start"], c["end"]))
    
    deduped = []
    last_text = ""
    last_cue = None

    for cue in sorted_cues:
        text = cue["text"].strip()
        if not text:
            continue

        # If identical to last cue, extend the duration of the last cue
        if text == last_text and last_cue is not None:
            last_cue["end"] = max(last_cue["end"], cue["end"])
            continue

        # If last text is a prefix of this cue and timestamps are adjacent/overlapping
        if last_cue is not None and last_cue["end"] >= cue["start"] - 0.5:
            if text.startswith(last_text) and len(text) > len(last_text):
                # Update text to the more complete version and extend end
                last_cue["text"] = text
                last_cue["end"] = max(last_cue["end"], cue["end"])
                last_text = text
                continue
            elif last_text.endswith(text) and len(last_text) >= len(text):
                # Subsumed
                last_cue["end"] = max(last_cue["end"], cue["end"])
                continue

        # Add new cue
        new_cue = {
            "start": round(cue["start"], 3),
            "end": round(cue["end"], 3),
            "text": text,
            "start_str": format_timestamp(cue["start"]),
            "end_str": format_timestamp(cue["end"])
        }
        deduped.append(new_cue)
        last_cue = new_cue
        last_text = text

    # Merge very short adjacent cues (e.g. 1-2 words within 0.8s) into natural conversational sentences
    merged_cues = []
    current = None
    for cue in deduped:
        if current is None:
            current = dict(cue)
            continue
        
        time_gap = cue["start"] - current["end"]
        # If words are consecutive and close in time (less than 1.5s gap), join them
        # Stop merging if punctuation indicates end of sentence (. ? !) or gap is larger
        ends_with_terminal = bool(re.search(r'[\.\?!]\s*$', current["text"]))
        word_count = len(current["text"].split())
        
        if time_gap < 1.5 and not ends_with_terminal and word_count < 35:
            current["end"] = cue["end"]
            current["end_str"] = cue["end_str"]
            current["text"] = current["text"] + " " + cue["text"]
        else:
            merged_cues.append(current)
            current = dict(cue)

    if current is not None:
        merged_cues.append(current)

    return merged_cues

def parse_transcript_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse a subtitle file (VTT or SRT) into a list of cues.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Transcript file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if file_path.lower().endswith(".vtt") or "WEBVTT" in content[:100]:
        return parse_vtt(content)
    else:
        return parse_srt(content)

def cues_to_full_text(cues: List[Dict[str, Any]], with_timestamps: bool = True) -> str:
    """
    Convert a list of cues into a formatted readable transcript string.
    """
    lines = []
    for cue in cues:
        if with_timestamps:
            lines.append(f"[{cue['start_str']} -> {cue['end_str']}] {cue['text']}")
        else:
            lines.append(cue["text"])
    return "\n".join(lines)
