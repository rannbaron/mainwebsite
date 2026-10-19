#!/usr/bin/env python3
"""
Subscription Management Database for NC Early Voting Daily Intelligence Reports.
Maintains a database of subscriber emails, handles web signups, remote sync,
and provides subscriber lists for daily morning dispatches.
"""

import os
import re
import sys
import json
import sqlite3
import argparse
import urllib.request
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "subscribers.db")
DEFAULT_SUBSCRIBER = "baronrann@gmail.com"

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def get_db_connection(db_path=DB_PATH):
    """Returns a SQLite connection and initializes the schema if needed."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'web',
                last_sent_at TIMESTAMP,
                notes TEXT
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_status ON subscribers(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sub_email ON subscribers(email);")
        
        # Seed default subscriber if table is empty
        cur = conn.execute("SELECT COUNT(*) FROM subscribers")
        if cur.fetchone()[0] == 0 and DEFAULT_SUBSCRIBER:
            conn.execute(
                "INSERT INTO subscribers (email, status, source, notes) VALUES (?, 'active', 'admin', 'Default recipient')",
                (DEFAULT_SUBSCRIBER.lower().strip(),)
            )
    return conn

def validate_email(email):
    """Validates email format and normalizes to lowercase."""
    if not email or not isinstance(email, str):
        return None
    email_clean = email.strip().lower()
    if EMAIL_REGEX.match(email_clean):
        return email_clean
    return None

def add_subscriber(email, source="web", notes=None, db_path=DB_PATH):
    """
    Adds or reactivates a subscriber in the database.
    Returns (success: bool, message: str, is_new: bool).
    """
    clean_email = validate_email(email)
    if not clean_email:
        return False, "Invalid email address format.", False

    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute("SELECT id, status FROM subscribers WHERE email = ?", (clean_email,))
        row = cur.fetchone()
        if row:
            if row["status"] == "active":
                return True, f"{clean_email} is already actively subscribed.", False
            else:
                conn.execute(
                    "UPDATE subscribers SET status = 'active', subscribed_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (row["id"],)
                )
                return True, f"Subscription for {clean_email} reactivated!", False
        else:
            conn.execute(
                "INSERT INTO subscribers (email, status, source, notes) VALUES (?, 'active', ?, ?)",
                (clean_email, source, notes)
            )
            return True, f"Successfully subscribed {clean_email} to daily updates!", True

def unsubscribe(email, db_path=DB_PATH):
    """Marks a subscriber as unsubscribed."""
    clean_email = validate_email(email)
    if not clean_email:
        return False, "Invalid email address."

    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute("UPDATE subscribers SET status = 'unsubscribed' WHERE email = ?", (clean_email,))
        if cur.rowcount > 0:
            return True, f"{clean_email} has been unsubscribed."
        return False, f"{clean_email} was not found in the subscriber list."

def get_active_subscribers(db_path=DB_PATH, sync_remote_first=True):
    """
    Returns a sorted list of unique active subscriber email addresses.
    Optionally syncs from remote webhook/sheet endpoint before querying.
    """
    if sync_remote_first:
        try:
            sync_from_remote(db_path=db_path)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Note: Remote subscription sync skipped: {e}")

    conn = get_db_connection(db_path)
    with conn:
        cur = conn.execute("SELECT email FROM subscribers WHERE status = 'active' ORDER BY email")
        emails = [row["email"] for row in cur.fetchall()]

    # Ensure DEFAULT_SUBSCRIBER is always included
    if DEFAULT_SUBSCRIBER and DEFAULT_SUBSCRIBER.lower() not in emails:
        emails.insert(0, DEFAULT_SUBSCRIBER.lower())

    return emails

def mark_sent(emails, timestamp=None, db_path=DB_PATH):
    """Records the timestamp when an update email was successfully dispatched."""
    if not emails:
        return
    if timestamp is None:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    conn = get_db_connection(db_path)
    with conn:
        for em in emails:
            clean = validate_email(em)
            if clean:
                conn.execute("UPDATE subscribers SET last_sent_at = ? WHERE email = ?", (timestamp, clean))

def sync_from_remote(remote_url=None, db_path=DB_PATH):
    """
    Syncs new subscriptions from a remote endpoint (e.g. Google Apps Script / Sheet or webhook).
    Expects remote endpoint to return either JSON:
      {"subscribers": ["user1@email.com", "user2@email.com"]}
    or a CSV containing emails.
    """
    url = remote_url or os.getenv("SUBSCRIBERS_REMOTE_URL")
    if not url:
        return 0

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Syncing subscribers from remote source: {url[:45]}...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NCEarlyVoteBot/1.0", "Accept": "application/json, text/csv, text/plain"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        content = resp.read().decode("utf-8", errors="ignore")

    new_count = 0
    # Try parsing as JSON first
    try:
        data = json.loads(content)
        emails = []
        if isinstance(data, list):
            emails = data
        elif isinstance(data, dict):
            emails = data.get("subscribers") or data.get("emails") or []
        for item in emails:
            e = item.get("email") if isinstance(item, dict) else str(item)
            success, _, is_new = add_subscriber(e, source="remote_sync", db_path=db_path)
            if is_new:
                new_count += 1
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Remote sync completed: {new_count} new subscriber(s) added.")
        return new_count
    except json.JSONDecodeError:
        pass

    # Fallback to plain CSV / lines
    for line in content.splitlines():
        line = line.strip().strip('"').strip("'")
        if ',' in line:
            parts = [p.strip().strip('"') for p in line.split(',')]
            for p in parts:
                if '@' in p:
                    success, _, is_new = add_subscriber(p, source="remote_csv", db_path=db_path)
                    if is_new:
                        new_count += 1
        elif '@' in line:
            success, _, is_new = add_subscriber(line, source="remote_txt", db_path=db_path)
            if is_new:
                new_count += 1

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Remote sync completed: {new_count} new subscriber(s) added.")
    return new_count

def list_all_subscribers(status=None, db_path=DB_PATH):
    """Returns a list of dicts for all subscribers."""
    conn = get_db_connection(db_path)
    with conn:
        if status:
            cur = conn.execute("SELECT * FROM subscribers WHERE status = ? ORDER BY id", (status,))
        else:
            cur = conn.execute("SELECT * FROM subscribers ORDER BY id")
        return [dict(row) for row in cur.fetchall()]

def main():
    parser = argparse.ArgumentParser(description="NC Early Voting Subscription Manager")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list
    list_p = subparsers.add_parser("list", help="List subscribers")
    list_p.add_argument("--status", choices=["active", "unsubscribed", "all"], default="active")

    # add
    add_p = subparsers.add_parser("add", help="Add a subscriber")
    add_p.add_argument("email", help="Subscriber email address")
    add_p.add_argument("--source", default="cli", help="Source tag")
    add_p.add_argument("--notes", default=None, help="Optional notes")

    # remove
    rem_p = subparsers.add_parser("remove", help="Unsubscribe an email")
    rem_p.add_argument("email", help="Subscriber email address")

    # sync
    sync_p = subparsers.add_parser("sync", help="Sync from remote endpoint/sheet")
    sync_p.add_argument("--url", default=None, help="Remote endpoint URL")

    args = parser.parse_args()

    if args.command == "add":
        ok, msg, _ = add_subscriber(args.email, source=args.source, notes=args.notes)
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
    elif args.command == "remove":
        ok, msg = unsubscribe(args.email)
        print(f"[{'OK' if ok else 'ERROR'}] {msg}")
    elif args.command == "sync":
        count = sync_from_remote(remote_url=args.url)
        print(f"Synced {count} new subscribers.")
    else: # default list
        status_filter = None if getattr(args, "status", "active") == "all" else getattr(args, "status", "active")
        subs = list_all_subscribers(status=status_filter)
        print(f"\nSubscribers ({len(subs)} total):")
        print(f"{'ID':<4} {'Status':<12} {'Email':<32} {'Subscribed At':<20} {'Source':<10}")
        print("-" * 80)
        for s in subs:
            print(f"{s['id']:<4} {s['status']:<12} {s['email']:<32} {str(s['subscribed_at'])[:19]:<20} {s['source'] or 'web':<10}")
        print("")

if __name__ == "__main__":
    main()
