"""
Database engine and query models for Durham Politics Tracker.
Uses SQLite for robust local querying and JSON caching for fast static site builds.
"""

import os
import re
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from .config import DB_PATH, BODIES

class DurhamPoliticsDB:
    def __init__(self, db_path: Optional[Path] = None, read_only: bool = False):
        self.db_path = Path(db_path or DB_PATH)
        self.read_only = read_only
        self._alias_cache: Optional[Dict[str, Dict[str, str]]] = None
        if not read_only:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.init_schema()

    @contextmanager
    def get_connection(self):
        if self.read_only or not os.access(self.db_path.parent, os.W_OK):
            conn = sqlite3.connect(f"file:{self.db_path.resolve()}?mode=ro&immutable=1", uri=True)
        else:
            conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_schema(self):
        """Initializes tables for bodies, members, meetings, votes, and deliberation issues."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            cur.executescript("""
            CREATE TABLE IF NOT EXISTS bodies (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                short_name TEXT NOT NULL,
                acronym TEXT NOT NULL,
                portal_url TEXT,
                youtube_channel TEXT,
                description TEXT,
                total_seats INTEGER DEFAULT 7
            );

            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                body_id TEXT NOT NULL,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                district TEXT,
                active_terms TEXT,
                is_current INTEGER DEFAULT 1,
                start_year INTEGER DEFAULT 2024,
                end_year INTEGER,
                avatar_initials TEXT,
                bio TEXT,
                key_priorities TEXT, -- JSON array
                ideology_tags TEXT,   -- JSON array
                FOREIGN KEY (body_id) REFERENCES bodies(id)
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                body_id TEXT NOT NULL,
                title TEXT NOT NULL,
                meeting_type TEXT NOT NULL, -- Regular, Work Session, Special, Budget
                date TEXT NOT NULL,         -- YYYY-MM-DD
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                presiding_chair TEXT,
                video_url TEXT,
                video_topic_slug TEXT,
                agenda_url TEXT,
                minutes_url TEXT,
                duration TEXT,
                executive_summary TEXT,
                tags TEXT,                  -- JSON array
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (body_id) REFERENCES bodies(id)
            );

            CREATE TABLE IF NOT EXISTS agenda_items (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                item_number TEXT,
                title TEXT NOT NULL,
                category TEXT,
                description TEXT,
                discussion_summary TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS votes (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                agenda_item_id TEXT,
                item_title TEXT NOT NULL,
                motion_type TEXT,
                mover TEXT,
                seconder TEXT,
                vote_format TEXT DEFAULT 'Roll Call',
                outcome TEXT NOT NULL, -- Passed, Failed, Tabled, Amended
                tally TEXT NOT NULL,   -- e.g. '7-0', '4-3'
                is_contested INTEGER DEFAULT 0,
                ayes TEXT,             -- JSON array of member names/ids
                nays TEXT,             -- JSON array of member names/ids
                abstentions TEXT,      -- JSON array of member names/ids
                amendments TEXT,       -- JSON array
                notes TEXT,
                category TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS member_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vote_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                member_name TEXT NOT NULL,
                body_id TEXT NOT NULL,
                vote_cast TEXT NOT NULL, -- AYE, NAY, ABSTAIN, ABSENT
                FOREIGN KEY (vote_id) REFERENCES votes(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE TABLE IF NOT EXISTS sources_of_disagreement (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                category TEXT,
                summary TEXT NOT NULL,
                side_a_position TEXT NOT NULL,
                side_a_arguments TEXT, -- JSON array
                side_a_members TEXT,   -- JSON array
                side_b_position TEXT NOT NULL,
                side_b_arguments TEXT, -- JSON array
                side_b_members TEXT,   -- JSON array
                resolution TEXT NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS board_cohorts (
                id TEXT PRIMARY KEY,
                body_id TEXT NOT NULL,
                label TEXT NOT NULL,
                short_label TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                is_current INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                transition_reason TEXT,
                FOREIGN KEY (body_id) REFERENCES bodies(id)
            );

            CREATE TABLE IF NOT EXISTS cohort_members (
                cohort_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                body_id TEXT NOT NULL,
                role TEXT NOT NULL,
                district TEXT,
                PRIMARY KEY (cohort_id, member_id),
                FOREIGN KEY (cohort_id) REFERENCES board_cohorts(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id)
            );

            CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(date);
            CREATE INDEX IF NOT EXISTS idx_meetings_body ON meetings(body_id);
            CREATE INDEX IF NOT EXISTS idx_votes_meeting ON votes(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_member_votes_member ON member_votes(member_id);
            CREATE INDEX IF NOT EXISTS idx_member_votes_vote ON member_votes(vote_id);
            CREATE INDEX IF NOT EXISTS idx_agenda_items_meeting ON agenda_items(meeting_id);
            CREATE INDEX IF NOT EXISTS idx_cohort_members_cohort ON cohort_members(cohort_id);
            """)

            # Safe incremental migrations for timestamped topics, summary PDFs, and historical cohorts
            migrations = [
                ("meetings", "summary_pdf_url", "TEXT"),
                ("meetings", "cohort_id", "TEXT"),
                ("members", "aliases", "TEXT"),
                ("agenda_items", "start_seconds", "INTEGER"),
                ("agenda_items", "timestamp_label", "TEXT"),
                ("agenda_items", "vote_summary", "TEXT"),
                ("votes", "timestamp_seconds", "INTEGER"),
                ("votes", "timestamp_label", "TEXT"),
                ("votes", "discussion_detail", "TEXT"),
                ("sources_of_disagreement", "timestamp_seconds", "INTEGER"),
                ("sources_of_disagreement", "timestamp_label", "TEXT"),
            ]
            for table, col, col_type in migrations:
                existing_cols = {r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_meetings_cohort ON meetings(cohort_id)")

    def insert_body(self, body_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO bodies (id, name, short_name, acronym, portal_url, youtube_channel, description, total_seats)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                body_data["id"], body_data["name"], body_data["short_name"], body_data["acronym"],
                body_data.get("portal_url"), body_data.get("youtube_channel"),
                body_data.get("description"), body_data.get("total_seats", 7)
            ))

    def insert_member(self, member_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO members (
                id, body_id, name, title, district, active_terms, is_current,
                start_year, end_year, avatar_initials, bio, key_priorities, ideology_tags, aliases
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                member_data["id"],
                member_data["body_id"],
                member_data["name"],
                member_data["title"],
                member_data.get("district", "At-Large"),
                json.dumps(member_data.get("active_terms", [])),
                1 if member_data.get("is_current", True) else 0,
                member_data.get("start_year", 2024),
                member_data.get("end_year"),
                member_data.get("avatar_initials", "".join([part[0] for part in re.sub(r"\([^)]*\)", "", member_data["name"]).split() if part][:2]).upper()),
                member_data.get("bio", ""),
                json.dumps(member_data.get("key_priorities", [])),
                json.dumps(member_data.get("ideology_tags", [])),
                json.dumps(member_data.get("aliases", [])),
            ))
        self._alias_cache = None

    def insert_cohort(self, cohort_data: Dict[str, Any]):
        """Inserts/updates a board seating cohort and its seated voting members."""
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO board_cohorts (
                id, body_id, label, short_label, start_date, end_date,
                is_current, sort_order, transition_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cohort_data["id"],
                cohort_data["body_id"],
                cohort_data["label"],
                cohort_data.get("short_label", cohort_data["label"]),
                cohort_data["start_date"],
                cohort_data.get("end_date"),
                1 if cohort_data.get("is_current", False) else 0,
                int(cohort_data.get("sort_order", 0)),
                cohort_data.get("transition_reason", ""),
            ))
            cur.execute("DELETE FROM cohort_members WHERE cohort_id = ?", (cohort_data["id"],))
            for cm in cohort_data.get("members", []):
                cur.execute("""
                INSERT OR REPLACE INTO cohort_members (cohort_id, member_id, body_id, role, district)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    cohort_data["id"],
                    cm["member_id"],
                    cohort_data["body_id"],
                    cm.get("role", "Member"),
                    cm.get("district", ""),
                ))

    def find_cohort_for_date(self, body_id: str, date_str: str) -> Optional[str]:
        """Returns the cohort_id for (body_id, YYYY-MM-DD)."""
        if not body_id or not date_str:
            return None
        with self.get_connection() as conn:
            cur = conn.cursor()
            row = cur.execute("""
                SELECT id FROM board_cohorts
                WHERE body_id = ?
                  AND start_date <= ?
                  AND (end_date IS NULL OR end_date >= ?)
                ORDER BY start_date DESC LIMIT 1
            """, (body_id, date_str, date_str)).fetchone()
            if row:
                return row["id"]
            # Fallback: if earlier than earliest cohort start_date, use earliest; else current
            earliest = cur.execute(
                "SELECT id, start_date FROM board_cohorts WHERE body_id = ? ORDER BY start_date ASC LIMIT 1",
                (body_id,),
            ).fetchone()
            if earliest and date_str < earliest["start_date"]:
                return earliest["id"]
            latest = cur.execute(
                "SELECT id FROM board_cohorts WHERE body_id = ? ORDER BY is_current DESC, start_date DESC LIMIT 1",
                (body_id,),
            ).fetchone()
            return latest["id"] if latest else None

    def assign_meeting_cohorts(self) -> int:
        """Assigns cohort_id to every meeting in the meetings table based on (body_id, date)."""
        updated = 0
        with self.get_connection() as conn:
            cur = conn.cursor()
            cohorts_by_body: Dict[str, List[Tuple[str, str, str]]] = {}
            for r in cur.execute(
                "SELECT id, body_id, start_date, COALESCE(end_date, '9999-12-31') AS end_d FROM board_cohorts ORDER BY start_date ASC"
            ).fetchall():
                cohorts_by_body.setdefault(r["body_id"], []).append((r["id"], r["start_date"], r["end_d"]))

            meetings = cur.execute("SELECT id, body_id, date FROM meetings").fetchall()
            for m in meetings:
                cands = cohorts_by_body.get(m["body_id"], [])
                if not cands:
                    continue
                chosen = None
                for cid, sd, ed in cands:
                    if sd <= m["date"] <= ed:
                        chosen = cid
                if not chosen:
                    chosen = cands[0][0] if m["date"] < cands[0][1] else cands[-1][0]
                cur.execute("UPDATE meetings SET cohort_id = ? WHERE id = ?", (chosen, m["id"]))
                updated += 1
        return updated

    def insert_meeting(self, meeting_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            dt = datetime.strptime(meeting_data["date"], "%Y-%m-%d")
            cohort_id = meeting_data.get("cohort_id") or self.find_cohort_for_date(
                meeting_data["body_id"], meeting_data["date"]
            )
            pdf_url = meeting_data.get("summary_pdf_url") or f"/durhampolitics/summaries/{meeting_data['id']}.pdf"
            cur.execute("""
            INSERT OR REPLACE INTO meetings (
                id, body_id, title, meeting_type, date, year, month,
                presiding_chair, video_url, video_topic_slug, agenda_url, minutes_url,
                duration, executive_summary, tags, summary_pdf_url, cohort_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                meeting_data["id"],
                meeting_data["body_id"],
                meeting_data["title"],
                meeting_data.get("meeting_type", "Regular Meeting"),
                meeting_data["date"],
                dt.year,
                dt.month,
                meeting_data.get("presiding_chair", ""),
                meeting_data.get("video_url", ""),
                meeting_data.get("video_topic_slug", ""),
                meeting_data.get("agenda_url", ""),
                meeting_data.get("minutes_url", ""),
                meeting_data.get("duration", "2h 30m"),
                meeting_data.get("executive_summary", ""),
                json.dumps(meeting_data.get("tags", [])),
                pdf_url,
                cohort_id,
            ))

    def insert_vote(self, vote_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            ayes = vote_data.get("ayes", [])
            nays = vote_data.get("nays", [])
            abstentions = vote_data.get("abstentions", [])
            is_contested = 1 if len(nays) > 0 or len(abstentions) > 0 else 0

            cur.execute("""
            INSERT OR REPLACE INTO votes (
                id, meeting_id, agenda_item_id, item_title, motion_type,
                mover, seconder, vote_format, outcome, tally, is_contested,
                ayes, nays, abstentions, amendments, notes, category,
                timestamp_seconds, timestamp_label, discussion_detail
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vote_data["id"],
                vote_data["meeting_id"],
                vote_data.get("agenda_item_id"),
                vote_data["item_title"],
                vote_data.get("motion_type", "Main Motion"),
                vote_data.get("mover", ""),
                vote_data.get("seconder", ""),
                vote_data.get("vote_format", "Roll Call"),
                vote_data.get("outcome", "Passed"),
                vote_data.get("tally", f"{len(ayes)}-{len(nays)}"),
                is_contested,
                json.dumps(ayes),
                json.dumps(nays),
                json.dumps(abstentions),
                json.dumps(vote_data.get("amendments", [])),
                vote_data.get("notes", ""),
                vote_data.get("category", "General"),
                vote_data.get("timestamp_seconds"),
                vote_data.get("timestamp_label", ""),
                vote_data.get("discussion_detail", ""),
            ))

            # Record individual member votes scoped strictly by body_id
            meeting_body = cur.execute("SELECT body_id FROM meetings WHERE id = ?", (vote_data["meeting_id"],)).fetchone()
            body_id = meeting_body["body_id"] if meeting_body else vote_data.get("body_id", "dps")

            cur.execute("DELETE FROM member_votes WHERE vote_id = ?", (vote_data["id"],))

            seen_mids = set()
            for m in ayes:
                m_id = self._canonical_member_id(m, body_id=body_id)
                if m_id and m_id not in seen_mids:
                    seen_mids.add(m_id)
                    cur.execute("INSERT INTO member_votes (vote_id, member_id, member_name, body_id, vote_cast) VALUES (?, ?, ?, ?, 'AYE')",
                                (vote_data["id"], m_id, m, body_id))
            for m in nays:
                m_id = self._canonical_member_id(m, body_id=body_id)
                if m_id and m_id not in seen_mids:
                    seen_mids.add(m_id)
                    cur.execute("INSERT INTO member_votes (vote_id, member_id, member_name, body_id, vote_cast) VALUES (?, ?, ?, ?, 'NAY')",
                                (vote_data["id"], m_id, m, body_id))
            for m in abstentions:
                m_id = self._canonical_member_id(m, body_id=body_id)
                if m_id and m_id not in seen_mids:
                    seen_mids.add(m_id)
                    cur.execute("INSERT INTO member_votes (vote_id, member_id, member_name, body_id, vote_cast) VALUES (?, ?, ?, ?, 'ABSTAIN')",
                                (vote_data["id"], m_id, m, body_id))

    def insert_agenda_item(self, item_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO agenda_items (
                id, meeting_id, item_number, title, category,
                description, discussion_summary, start_seconds, timestamp_label, vote_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_data["id"],
                item_data["meeting_id"],
                item_data.get("item_number", ""),
                item_data["title"],
                item_data.get("category", "Governance & Transparency"),
                item_data.get("description", ""),
                item_data.get("discussion_summary", ""),
                item_data.get("start_seconds"),
                item_data.get("timestamp_label", ""),
                item_data.get("vote_summary", ""),
            ))

    def insert_disagreement(self, dis_data: Dict[str, Any]):
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT OR REPLACE INTO sources_of_disagreement (
                id, meeting_id, issue, category, summary,
                side_a_position, side_a_arguments, side_a_members,
                side_b_position, side_b_arguments, side_b_members,
                resolution, timestamp_seconds, timestamp_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dis_data["id"],
                dis_data["meeting_id"],
                dis_data["issue"],
                dis_data.get("category", "Governance"),
                dis_data["summary"],
                dis_data["side_a_position"],
                json.dumps(dis_data.get("side_a_arguments", [])),
                json.dumps(dis_data.get("side_a_members", [])),
                dis_data["side_b_position"],
                json.dumps(dis_data.get("side_b_arguments", [])),
                json.dumps(dis_data.get("side_b_members", [])),
                dis_data.get("resolution", ""),
                dis_data.get("timestamp_seconds"),
                dis_data.get("timestamp_label", ""),
            ))

    def _build_alias_cache(self) -> Dict[str, Dict[str, str]]:
        """Builds per-body alias lookup tables from the members table + core ASR aliases."""
        if self._alias_cache is not None:
            return self._alias_cache
        cache: Dict[str, Dict[str, str]] = {"city": {}, "bocc": {}, "dps": {}, "all": {}}
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id, body_id, name, aliases FROM members").fetchall()
            for r in rows:
                mid = r["id"]
                bid = r["body_id"]
                nm = (r["name"] or "").strip()
                clean_nm = re.sub(r"^(?:dr\.?|mayor|chair|vice chair|commissioner|council\s*member)\s+", "", nm, flags=re.I)
                clean_nm = re.sub(r"\([^)]*\)", "", clean_nm).strip().lower()
                cands = [clean_nm, nm.lower(), mid.lower()]
                parts = clean_nm.split()
                if len(parts) >= 2 and len(parts[-1]) >= 4:
                    cands.append(parts[-1])
                try:
                    al = json.loads(r["aliases"] or "[]") if "aliases" in r.keys() else []
                    if isinstance(al, list):
                        cands.extend(str(a).lower().strip() for a in al if a)
                except Exception:
                    pass
                for c in cands:
                    if not c or len(c) < 3:
                        continue
                    cache.setdefault(bid, {})[c] = mid
                    cache["all"].setdefault(c, mid)
        self._alias_cache = cache
        return cache

    def _canonical_member_id(self, name: str, body_id: Optional[str] = None) -> Optional[str]:
        """Normalizes an official's name into a unique member ID, scoped by body_id."""
        if not name or not str(name).strip():
            return None
        clean = str(name).lower()
        for prefix in ["vice chair", "mayor pro tem", "mayor pro tempore", "council member", "councilmember", "commissioner", "board member", "chair", "mayor", "dr.", "dr ", "mr.", "ms.", "mrs."]:
            clean = clean.replace(prefix, " ")
        clean = re.sub(r"\s+", " ", clean).strip()
        if not clean or clean in ("none", "n/a", "na", "0", "all", "unanimous", "unknown"):
            return None

        # 1. Dynamic DB-backed aliases (strictly body-scoped first!)
        cache = self._build_alias_cache()
        if body_id and body_id in cache:
            body_map = cache[body_id]
            if clean in body_map:
                return body_map[clean]
            # Longest-alias-first match within body
            for k in sorted(body_map.keys(), key=len, reverse=True):
                if len(k) >= 4 and k in clean:
                    return body_map[k]
                if len(k) == 3 and re.search(r"\b" + re.escape(k) + r"\b", clean):
                    return body_map[k]

        # 2. Core ASR fallback lookup
        lookup = {
            "joy harrell-goff": ("dps", "joy_harrell_goff"),
            "joy harrell goff": ("dps", "joy_harrell_goff"),
            "harrell-goff": ("dps", "joy_harrell_goff"),
            "xavier cason": ("dps", "xavier_cason"),
            "natalie bent kitaif": ("dps", "natalie_bent_kitaif"),
            "natalie kitaif": ("dps", "natalie_bent_kitaif"),
            "nadeen bir": ("dps", "nadeen_bir"),
            "gabrielle (gabby) rivero": ("dps", "gabby_rivero"),
            "gabrielle rivero": ("dps", "gabby_rivero"),
            "gabby rivero": ("dps", "gabby_rivero"),
            "wendell tabb": ("dps", "wendell_tabb"),
            "millicent rogers": ("dps", "millicent_rogers"),
            "bettina umstead": ("dps", "bettina_umstead"),
            "emily chávez": ("dps", "emily_chavez"),
            "emily chavez": ("dps", "emily_chavez"),
            "natalie beyer": ("dps", "natalie_beyer"),
            "alexandra valladares": ("dps", "alexandra_valladares"),
            "jovonia lewis": ("dps", "jovonia_lewis"),
            "leonardo williams": ("city", "leonardo_williams"),
            "leo williams": ("city", "leonardo_williams"),
            "javiera caballero": ("city", "javiera_caballero"),
            "cabayro": ("city", "javiera_caballero"),
            "cababiero": ("city", "javiera_caballero"),
            "cabayo": ("city", "javiera_caballero"),
            "cayetano": ("city", "javiera_caballero"),
            "cavayto": ("city", "javiera_caballero"),
            "cáviero": ("city", "javiera_caballero"),
            "clavijo": ("city", "javiera_caballero"),
            "fayto": ("city", "javiera_caballero"),
            "nate baker": ("city", "nate_baker"),
            "baker": ("city", "nate_baker"),
            "bigger": ("city", "nate_baker"),
            "carl rist": ("city", "carl_rist"),
            "rist": ("city", "carl_rist"),
            "rrist": ("city", "carl_rist"),
            "matt kopac": ("city", "matt_kopac"),
            "kopac": ("city", "matt_kopac"),
            "kopack": ("city", "matt_kopac"),
            "kopacek": ("city", "matt_kopac"),
            "kopec": ("city", "matt_kopac"),
            "kobec": ("city", "matt_kopac"),
            "kubic": ("city", "matt_kopac"),
            "copac": ("city", "matt_kopac"),
            "copack": ("city", "matt_kopac"),
            "copak": ("city", "matt_kopac"),
            "copek": ("city", "matt_kopac"),
            "corbett": ("city", "matt_kopac"),
            "shanetta burris": ("city", "shanetta_burris"),
            "burris": ("city", "shanetta_burris"),
            "burrus": ("city", "shanetta_burris"),
            "burries": ("city", "shanetta_burris"),
            "burus": ("city", "shanetta_burris"),
            "barris": ("city", "shanetta_burris"),
            "barriss": ("city", "shanetta_burris"),
            "burgess": ("city", "shanetta_burris"),
            "chelsea cook": ("city", "chelsea_cook"),
            "cook": ("city", "chelsea_cook"),
            "mike lee": ("bocc", "mike_lee"),
            "nida allam": ("bocc", "nida_allam"),
            "nida alam": ("bocc", "nida_allam"),
            "allam": ("bocc", "nida_allam"),
            "alam": ("bocc", "nida_allam"),
            "alum": ("bocc", "nida_allam"),
            "alom": ("bocc", "nida_allam"),
            "michelle burton": ("bocc", "michelle_burton"),
            "burton": ("bocc", "michelle_burton"),
            "stephen valentine": ("bocc", "stephen_valentine"),
            "steven valentine": ("bocc", "stephen_valentine"),
            "steve valentine": ("bocc", "stephen_valentine"),
            "valentine": ("bocc", "stephen_valentine"),
            "wendy jacobs": ("bocc", "wendy_jacobs"),
            "jacobs": ("bocc", "wendy_jacobs"),
        }

        if clean in lookup:
            l_bid, l_mid = lookup[clean]
            if not body_id or l_bid == body_id:
                return l_mid

        for k, (l_bid, l_mid) in lookup.items():
            if (not body_id or l_bid == body_id) and len(k) >= 4 and k in clean:
                return l_mid

        with self.get_connection() as conn:
            if body_id:
                m = conn.execute(
                    "SELECT id FROM members WHERE body_id = ? AND (LOWER(name) LIKE ? OR id = ?)",
                    (body_id, f"%{clean}%", clean),
                ).fetchone()
            else:
                m = conn.execute(
                    "SELECT id FROM members WHERE LOWER(name) LIKE ? OR id = ?",
                    (f"%{clean}%", clean),
                ).fetchone()
            if m:
                return m["id"]
        return None

    def compute_stats(self) -> Dict[str, Any]:
        """Calculates rich metrics, member stats, pairwise agreements, and dissent scores."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            # Global counts
            total_meetings = cur.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
            total_votes = cur.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
            contested_votes = cur.execute("SELECT COUNT(*) FROM votes WHERE is_contested = 1").fetchone()[0]
            unanimous_votes = total_votes - contested_votes
            total_disagreements = cur.execute("SELECT COUNT(*) FROM sources_of_disagreement").fetchone()[0]

            # Per body metrics
            body_stats = {}
            for body_id in BODIES.keys():
                b_meetings = cur.execute("SELECT COUNT(*) FROM meetings WHERE body_id = ?", (body_id,)).fetchone()[0]
                b_votes = cur.execute("""
                    SELECT COUNT(*) FROM votes v JOIN meetings m ON v.meeting_id = m.id WHERE m.body_id = ?
                """, (body_id,)).fetchone()[0]
                b_contested = cur.execute("""
                    SELECT COUNT(*) FROM votes v JOIN meetings m ON v.meeting_id = m.id WHERE m.body_id = ? AND v.is_contested = 1
                """, (body_id,)).fetchone()[0]
                body_stats[body_id] = {
                    "meetings_count": b_meetings,
                    "votes_count": b_votes,
                    "contested_votes": b_contested,
                    "unanimous_rate": round(((b_votes - b_contested) / max(b_votes, 1)) * 100, 1)
                }

            # Member statistics
            members_raw = cur.execute("SELECT * FROM members ORDER BY body_id, name").fetchall()
            member_stats = []

            for m in members_raw:
                m_id = m["id"]
                # Count total cast votes
                ayes = cur.execute("SELECT COUNT(*) FROM member_votes WHERE member_id = ? AND vote_cast = 'AYE'", (m_id,)).fetchone()[0]
                nays = cur.execute("SELECT COUNT(*) FROM member_votes WHERE member_id = ? AND vote_cast = 'NAY'", (m_id,)).fetchone()[0]
                abstains = cur.execute("SELECT COUNT(*) FROM member_votes WHERE member_id = ? AND vote_cast = 'ABSTAIN'", (m_id,)).fetchone()[0]
                total_cast = ayes + nays + abstains

                # Contested vote dissents
                dissents = cur.execute("""
                    SELECT COUNT(*) FROM member_votes mv
                    JOIN votes v ON mv.vote_id = v.id
                    WHERE mv.member_id = ? AND mv.vote_cast = 'NAY' AND v.outcome LIKE '%Passed%'
                """, (m_id,)).fetchone()[0]

                contested_participated = cur.execute("""
                    SELECT COUNT(*) FROM member_votes mv
                    JOIN votes v ON mv.vote_id = v.id
                    WHERE mv.member_id = ? AND v.is_contested = 1
                """, (m_id,)).fetchone()[0]

                dissent_rate = round((dissents / total_cast) * 100, 1) if total_cast > 0 else 0.0

                m_keys = m.keys()
                aliases_list = []
                if "aliases" in m_keys and m["aliases"]:
                    try:
                        aliases_list = json.loads(m["aliases"])
                    except Exception:
                        aliases_list = []

                member_stats.append({
                    "id": m["id"],
                    "body_id": m["body_id"],
                    "name": m["name"],
                    "title": m["title"],
                    "district": m["district"],
                    "active_terms": json.loads(m["active_terms"] or "[]"),
                    "is_current": bool(m["is_current"]),
                    "start_year": m["start_year"],
                    "end_year": m["end_year"],
                    "avatar_initials": m["avatar_initials"],
                    "bio": m["bio"],
                    "key_priorities": json.loads(m["key_priorities"] or "[]"),
                    "ideology_tags": json.loads(m["ideology_tags"] or "[]"),
                    "aliases": aliases_list,
                    "votes_cast": total_cast,
                    "ayes": ayes,
                    "nays": nays,
                    "abstains": abstains,
                    "aye_pct": round((ayes / max(total_cast, 1)) * 100, 1),
                    "nay_pct": round((nays / max(total_cast, 1)) * 100, 1),
                    "dissent_rate": dissent_rate,
                    "dissents_count": dissents
                })

            # Pairwise Agreement Heatmap per Body
            pairwise_agreements = {}
            for body_id in BODIES.keys():
                body_mems = [m["id"] for m in member_stats if m["body_id"] == body_id]
                matrix = {}
                for m1 in body_mems:
                    matrix[m1] = {}
                    for m2 in body_mems:
                        if m1 == m2:
                            matrix[m1][m2] = 100.0
                            continue
                        # Find votes where both participated
                        both_votes = cur.execute("""
                            SELECT v1.vote_cast AS c1, v2.vote_cast AS c2
                            FROM member_votes v1
                            JOIN member_votes v2 ON v1.vote_id = v2.vote_id
                            WHERE v1.member_id = ? AND v2.member_id = ?
                        """, (m1, m2)).fetchall()

                        if not both_votes:
                            matrix[m1][m2] = None
                        else:
                            agree = sum(1 for row in both_votes if row["c1"] == row["c2"])
                            matrix[m1][m2] = round((agree / len(both_votes)) * 100, 1)
                pairwise_agreements[body_id] = matrix

            return {
                "overall": {
                    "total_meetings": total_meetings,
                    "total_votes": total_votes,
                    "contested_votes": contested_votes,
                    "unanimous_votes": unanimous_votes,
                    "unanimous_pct": round((unanimous_votes / max(total_votes, 1)) * 100, 1),
                    "total_disagreements": total_disagreements,
                    "last_updated": datetime.now().strftime("%B %d, %Y")
                },
                "bodies": body_stats,
                "members": member_stats,
                "pairwise": pairwise_agreements
            }

    def export_full_dataset(self) -> Dict[str, Any]:
        """Assembles the complete hierarchical dataset for frontend rendering."""
        with self.get_connection() as conn:
            cur = conn.cursor()

            stats = self.compute_stats()

            # All meetings with votes and disagreements
            meetings_rows = cur.execute("""
                SELECT * FROM meetings ORDER BY date DESC
            """).fetchall()

            meetings_list = []
            for m in meetings_rows:
                m_id = m["id"]
                base_video_url = m["video_url"] or ""

                def make_ts_url(secs):
                    if not base_video_url:
                        return ""
                    if secs is None:
                        return base_video_url
                    sep = "&" if "?" in base_video_url else "?"
                    return f"{base_video_url}{sep}t={int(secs)}s"

                # get agenda items
                agenda_rows = cur.execute(
                    "SELECT * FROM agenda_items WHERE meeting_id = ? ORDER BY COALESCE(start_seconds, 999999) ASC, id ASC",
                    (m_id,),
                ).fetchall()
                agenda_items = []
                for ag in agenda_rows:
                    ag_keys = ag.keys()
                    start_s = ag["start_seconds"] if "start_seconds" in ag_keys else None
                    ts_lbl = ag["timestamp_label"] if "timestamp_label" in ag_keys else ""
                    v_sum = ag["vote_summary"] if "vote_summary" in ag_keys else ""
                    agenda_items.append({
                        "id": ag["id"],
                        "item_number": ag["item_number"] or "",
                        "title": ag["title"],
                        "category": ag["category"] or "Governance & Transparency",
                        "discussion_summary": ag["discussion_summary"] or "",
                        "vote_summary": v_sum or "",
                        "start_seconds": start_s,
                        "timestamp_label": ts_lbl or "",
                        "video_timestamp_url": make_ts_url(start_s),
                    })

                # get votes
                votes_rows = cur.execute("SELECT * FROM votes WHERE meeting_id = ?", (m_id,)).fetchall()
                votes = []
                for v in votes_rows:
                    v_keys = v.keys()
                    v_ts = v["timestamp_seconds"] if "timestamp_seconds" in v_keys else None
                    v_ts_lbl = v["timestamp_label"] if "timestamp_label" in v_keys else ""
                    v_disc = v["discussion_detail"] if "discussion_detail" in v_keys else ""
                    votes.append({
                        "id": v["id"],
                        "item_title": v["item_title"],
                        "motion_type": v["motion_type"],
                        "mover": v["mover"],
                        "seconder": v["seconder"],
                        "vote_format": v["vote_format"],
                        "outcome": v["outcome"],
                        "tally": v["tally"],
                        "is_contested": bool(v["is_contested"]),
                        "ayes": json.loads(v["ayes"] or "[]"),
                        "nays": json.loads(v["nays"] or "[]"),
                        "abstentions": json.loads(v["abstentions"] or "[]"),
                        "amendments": json.loads(v["amendments"] or "[]"),
                        "notes": v["notes"],
                        "discussion_detail": v_disc or "",
                        "category": v["category"],
                        "timestamp_seconds": v_ts,
                        "timestamp_label": v_ts_lbl or "",
                        "video_timestamp_url": make_ts_url(v_ts),
                    })

                # get disagreements
                dis_rows = cur.execute("SELECT * FROM sources_of_disagreement WHERE meeting_id = ?", (m_id,)).fetchall()
                disagreements = []
                for d in dis_rows:
                    d_keys = d.keys()
                    d_ts = d["timestamp_seconds"] if "timestamp_seconds" in d_keys else None
                    d_ts_lbl = d["timestamp_label"] if "timestamp_label" in d_keys else ""
                    disagreements.append({
                        "id": d["id"],
                        "issue": d["issue"],
                        "category": d["category"],
                        "summary": d["summary"],
                        "side_a": {
                            "position": d["side_a_position"],
                            "arguments": json.loads(d["side_a_arguments"] or "[]"),
                            "members": json.loads(d["side_a_members"] or "[]")
                        },
                        "side_b": {
                            "position": d["side_b_position"],
                            "arguments": json.loads(d["side_b_arguments"] or "[]"),
                            "members": json.loads(d["side_b_members"] or "[]")
                        },
                        "resolution": d["resolution"],
                        "timestamp_seconds": d_ts,
                        "timestamp_label": d_ts_lbl or "",
                        "video_timestamp_url": make_ts_url(d_ts),
                    })

                m_keys = m.keys()
                pdf_url = (m["summary_pdf_url"] if "summary_pdf_url" in m_keys else "") or f"/durhampolitics/summaries/{m_id}.pdf"
                cohort_id = m["cohort_id"] if "cohort_id" in m_keys else None

                meetings_list.append({
                    "id": m["id"],
                    "body_id": m["body_id"],
                    "cohort_id": cohort_id,
                    "title": m["title"],
                    "meeting_type": m["meeting_type"],
                    "date": m["date"],
                    "year": m["year"],
                    "month": m["month"],
                    "presiding_chair": m["presiding_chair"],
                    "video_url": m["video_url"],
                    "video_topic_slug": m["video_topic_slug"],
                    "agenda_url": m["agenda_url"],
                    "minutes_url": m["minutes_url"],
                    "summary_pdf_url": pdf_url,
                    "duration": m["duration"],
                    "executive_summary": m["executive_summary"],
                    "tags": json.loads(m["tags"] or "[]"),
                    "agenda_items": agenda_items,
                    "votes": votes,
                    "disagreements": disagreements
                })

            # Export board cohorts (sorted newest-first per body)
            cohorts_by_body: Dict[str, List[Dict[str, Any]]] = {b: [] for b in BODIES.keys()}
            tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            if "board_cohorts" in tables:
                c_rows = cur.execute(
                    "SELECT * FROM board_cohorts ORDER BY body_id ASC, is_current DESC, start_date DESC"
                ).fetchall()
                cm_by_cohort: Dict[str, List[Dict[str, Any]]] = {}
                for cm in cur.execute("SELECT * FROM cohort_members").fetchall():
                    cm_by_cohort.setdefault(cm["cohort_id"], []).append({
                        "member_id": cm["member_id"],
                        "role": cm["role"],
                        "district": cm["district"],
                    })
                m_counts = {
                    r["cohort_id"]: r["cnt"]
                    for r in cur.execute(
                        "SELECT cohort_id, COUNT(*) AS cnt FROM meetings WHERE cohort_id IS NOT NULL GROUP BY cohort_id"
                    ).fetchall()
                }
                for c in c_rows:
                    cmems = cm_by_cohort.get(c["id"], [])
                    cohorts_by_body.setdefault(c["body_id"], []).append({
                        "id": c["id"],
                        "body_id": c["body_id"],
                        "label": c["label"],
                        "short_label": c["short_label"],
                        "start_date": c["start_date"],
                        "end_date": c["end_date"],
                        "is_current": bool(c["is_current"]),
                        "sort_order": c["sort_order"],
                        "transition_reason": c["transition_reason"] or "",
                        "meeting_count": m_counts.get(c["id"], 0),
                        "member_ids": [x["member_id"] for x in cmems],
                        "members": cmems,
                    })

            dates_all = [m["date"] for m in meetings_list if m.get("date")]
            if dates_all:
                min_yr = min(dates_all)[:4]
                max_dt = datetime.strptime(max(dates_all), "%Y-%m-%d").strftime("%B %Y")
                coverage_str = f"{min_yr} – {max_dt} & Ongoing"
            else:
                coverage_str = "2012 – November 2026 & Ongoing"

            return {
                "metadata": {
                    "app_title": "Durham Politics Tracker",
                    "coverage": coverage_str,
                    "bodies": BODIES,
                    "generated_at": datetime.now().isoformat()
                },
                "cohorts": cohorts_by_body,
                "stats": stats,
                "meetings": meetings_list
            }
