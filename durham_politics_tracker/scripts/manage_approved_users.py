#!/usr/bin/env python3
"""
Approve or revoke Durham Politics Tracker user accounts.

Approved users are strictly scoped to ONLY https://rannbar-on.com/durhampolitics/
(allowed_pages = ["/durhampolitics"], privilege_level = 2).
Updates both durhampolitics/approved_users.json and accounts.json, and optionally
sends an approval confirmation email via SMTP if configured.
"""

import argparse
import hashlib
import json
import os
import secrets
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent if (BASE_DIR.parent / "durhampolitics").exists() else Path("/home/rann/src/website/mainwebsite")
APPROVED_USERS_PATH = REPO_ROOT / "durhampolitics" / "approved_users.json"
ACCOUNTS_JSON_PATH = REPO_ROOT / "accounts.json"


def hash_password_sha256(password: str, salt: str = "") -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return salt, digest


def send_approval_email(to_email: str, full_name: str, username: str):
    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    if not smtp_user or not smtp_pass or not to_email:
        print("[Email] SMTP secrets not configured; skipping user confirmation email.")
        return

    msg = EmailMessage()
    msg["Subject"] = "Your Durham Politics Tracker Account Has Been Approved"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content(
        f"Hello {full_name},\n\n"
        f"Your account ({username}) for the Durham Politics Tracker has been approved!\n\n"
        f"You can now sign in at:\n"
        f"https://rannbar-on.com/durhampolitics/\n\n"
        f"Best,\nRann Bar-On\n"
    )
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        print(f"[Email] Sent approval notification to {to_email}")
    except Exception as e:
        print(f"[Email] Warning: failed to send approval email: {e}")


def main():
    parser = argparse.ArgumentParser(description="Approve or revoke Durham Politics Tracker user account.")
    parser.add_argument("--action", choices=["approve", "revoke"], default="approve")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--salt", default="")
    parser.add_argument("--password-hash", default="")
    parser.add_argument("--temporary-password", default="")
    args = parser.parse_args()

    username = args.username.strip().lower()
    email = args.email.strip().lower()
    full_name = args.full_name.strip() or username
    now_iso = datetime.now(timezone.utc).isoformat()

    if APPROVED_USERS_PATH.exists():
        data = json.loads(APPROVED_USERS_PATH.read_text(encoding="utf-8"))
    else:
        data = {"updated_at": now_iso, "allowed_route": "/durhampolitics", "users": []}

    users = [u for u in data.get("users", []) if u.get("username", "").lower() != username]

    if args.action == "approve":
        salt = args.salt.strip()
        pwd_hash = args.password_hash.strip()
        if args.temporary_password:
            salt, pwd_hash = hash_password_sha256(args.temporary_password, salt)
        if not salt or not pwd_hash:
            raise SystemExit("ERROR: Provide either (--salt and --password-hash) or --temporary-password.")

        users.append({
            "username": username,
            "full_name": full_name,
            "email": email,
            "salt": salt,
            "password_hash": pwd_hash,
            "status": "APPROVED",
            "allowed_pages": ["/durhampolitics"],
            "approved_at": now_iso,
        })
        print(f"✓ Approved '{username}' ({full_name}) with access strictly limited to /durhampolitics/")
    else:
        print(f"✓ Revoked access for '{username}'")

    data["updated_at"] = now_iso
    data["allowed_route"] = "/durhampolitics"
    data["users"] = sorted(users, key=lambda u: u["username"])
    APPROVED_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APPROVED_USERS_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # Also keep sanitized accounts.json synchronized with strict /durhampolitics-only permissions
    if ACCOUNTS_JSON_PATH.exists():
        acc = json.loads(ACCOUNTS_JSON_PATH.read_text(encoding="utf-8"))
        existing = [a for a in acc.get("accounts", []) if a.get("username", "").lower() != username]
        if args.action == "approve":
            next_id = max((a.get("id", 0) for a in existing), default=0) + 1
            existing.append({
                "id": next_id,
                "username": username,
                "full_name": full_name,
                "email": email,
                "privilege_level": 2,
                "privilege_name": "Standard Member",
                "allowed_pages": ["/durhampolitics"],
                "status": "APPROVED",
                "created_at": now_iso,
                "last_login": None,
            })
        acc["accounts"] = existing
        acc["total"] = len(existing)
        acc["updated_at"] = now_iso
        ACCOUNTS_JSON_PATH.write_text(json.dumps(acc, indent=2) + "\n", encoding="utf-8")

    if args.action == "approve" and email:
        send_approval_email(email, full_name, username)


if __name__ == "__main__":
    main()
