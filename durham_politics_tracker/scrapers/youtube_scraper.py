"""
YouTube Scraper for Durham Local Government Meeting Channels.
Monitors:
  - Durham Public Schools: @DurhamPublicSchoolsNC
  - City of Durham: @CityofDurhamNC
  - Durham County Government: @DurhamCountyNC
Extracts meeting video IDs, live streams, descriptions, dates, and durations.
"""

import re
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..config import BODIES

DEFAULT_YT_DLP_BIN = "/home/rann/.local/bin/yt-dlp"

class DurhamYouTubeScraper:
    CHANNEL_URLS = {
        "dps": [
            "https://www.youtube.com/@durhampublicschoolsboardof2290/streams",
            "https://www.youtube.com/@durhampublicschoolsboardof2290/videos",
        ],
        "city": [
            "https://www.youtube.com/@CityofDurhamNC/streams",
            "https://www.youtube.com/@CityofDurhamNC/videos",
        ],
        "bocc": [
            "https://www.youtube.com/@DCoWebmaster/streams",
            "https://www.youtube.com/@DCoWebmaster/videos",
        ],
    }

    MEETING_KEYWORDS = [
        "board of education", "school board", "work session", "monthly action",
        "city council", "council meeting", "bocc", "county commissioners",
        "budget hearing", "regular meeting", "special meeting"
    ]

    def __init__(self, yt_dlp_bin: str = "/home/rann/.local/bin/yt-dlp"):
        self.yt_dlp_bin = yt_dlp_bin

    def fetch_channel_videos(self, body_id: str, limit: int = 15) -> List[Dict[str, Any]]:
        """
        Queries recent channel uploads using yt-dlp flat-playlist extraction.
        Returns parsed meeting records.
        """
        if body_id not in self.CHANNEL_URLS:
            raise ValueError(f"Unknown body_id: {body_id}")

        urls = self.CHANNEL_URLS[body_id]
        if isinstance(urls, str):
            urls = [urls]

        videos = []
        seen_ids = set()
        for channel_url in urls:
            cmd = [
                self.yt_dlp_bin,
                "--flat-playlist",
                "--dump-json",
                "--playlist-end", str(limit),
                channel_url
            ]

            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
                if res.returncode != 0:
                    print(f"[YouTubeScraper] yt-dlp warning for {body_id} ({channel_url}): {res.stderr[:200]}")
                    continue

                for line in res.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                        vid = data.get("id", "")
                        if not vid or vid in seen_ids or data.get("duration") is None:
                            continue
                        title = data.get("title", "")
                        if self._is_meeting_video(title, body_id):
                            seen_ids.add(vid)
                            meeting_record = self._parse_video_metadata(data, body_id)
                            videos.append(meeting_record)
                    except Exception:
                        continue
            except Exception as err:
                print(f"[YouTubeScraper] Execution failed for {channel_url}: {err}")
        return videos

    def _is_meeting_video(self, title: str, body_id: str) -> bool:
        t_low = title.lower()
        return any(k in t_low for k in self.MEETING_KEYWORDS)

    def _parse_video_metadata(self, data: Dict[str, Any], body_id: str) -> Dict[str, Any]:
        title = data.get("title", "")
        vid_id = data.get("id", "")
        upload_date = data.get("upload_date")  # YYYYMMDD
        
        parsed_date = None
        if upload_date and len(upload_date) == 8:
            parsed_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
        else:
            # Try to extract date from title e.g. 'November 21, 2024' or '11/21/24'
            match = re.search(r"(\w+\s+\d{1,2},?\s+\d{4})", title)
            if match:
                try:
                    dt = datetime.strptime(match.group(1).replace(",", ""), "%B %d %Y")
                    parsed_date = dt.strftime("%Y-%m-%d")
                except Exception:
                    pass
        
        if not parsed_date:
            parsed_date = datetime.now().strftime("%Y-%m-%d")

        # Determine meeting type
        meeting_type = "Regular Meeting"
        t_low = title.lower()
        if "work session" in t_low:
            meeting_type = "Work Session"
        elif "budget" in t_low:
            meeting_type = "Budget Session"
        elif "special" in t_low or "emergency" in t_low:
            meeting_type = "Special Meeting"

        duration_sec = data.get("duration") or 7200
        hrs = int(duration_sec // 3600)
        mins = int((duration_sec % 3600) // 60)
        duration_str = f"{hrs}h {mins:02d}m" if hrs > 0 else f"{mins}m"

        return {
            "id": f"{body_id}_{parsed_date.replace('-', '_')}",
            "body_id": body_id,
            "title": title,
            "meeting_type": meeting_type,
            "date": parsed_date,
            "video_url": f"https://www.youtube.com/watch?v={vid_id}",
            "duration": duration_str,
            "source": "youtube"
        }
