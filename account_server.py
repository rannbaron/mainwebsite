#!/usr/bin/env python3
"""
RannBar-On.com User Account Management & 2FA Authentication Server
================================================================
Named Privilege Levels & Page-by-Page Granular Access Control System.

Role Tiers:
- Level 1: Guest (Public access only)
- Level 2: Standard Member
- Level 3: Verified Member
- Level 4: Research Associate
- Level 5: Community Contributor
- Level 6: Policy Analyst
- Level 7: Senior Reviewer
- Level 8: Operations Lead
- Level 9: System Administrator
- Level 10: Master Administrator (Rann)

Catalog of Private Pages:
- /durhampolitics (Durham Politics Tracker)
- /agents (Agent Command Center)
- /taskpriority (Decision Desk Approvals)
- /internal/vibes.html (Real-Time Vibes Monitor)
- /voice (Voice Dictation Bridge)
- /dashboard/accounts (User Administration Console)
"""

import os
import sys
import re
import json
import time
import sqlite3
import hashlib
import secrets
import argparse
from datetime import datetime, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "accounts.db"
JSON_CACHE_PATH = BASE_DIR / "accounts.json"
MASTER_PASSWORD = "AS2cYGy9GD7qRt@XV&gf$yUX!pD@"
DEFAULT_PORT = 8086
DEFAULT_TEST_EMAIL = "outputtest@rannbar-on.com"

# Prevent sending to non-existent / dummy addresses or third parties during testing
DISALLOWED_TEST_PATTERNS = [
    r"@example\.(com|org|net)",
    r"@test\.(com|org|net)",
    r"@fake\.(com|org|net)",
    r"@nonexistent\.(com|org|net)",
    r"^test@",
    r"nida\.allam@",
    r"nallam@",
    r"nidaallam@"
]

def resolve_email_recipient(email: str, is_test: bool = False) -> str:
    """Enforce user rule: Never send emails to fake or non-existent addresses.
    Always route test emails or dummy domains to outputtest@rannbar-on.com."""
    if is_test or not email:
        return DEFAULT_TEST_EMAIL
    email_clean = email.strip()
    for pattern in DISALLOWED_TEST_PATTERNS:
        if re.search(pattern, email_clean, re.IGNORECASE):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Rerouting non-existent/test address '{email_clean}' to '{DEFAULT_TEST_EMAIL}'")
            return DEFAULT_TEST_EMAIL
    return email_clean

ROLE_TIERS = {
    1: "Guest",
    2: "Standard Member",
    3: "Verified Member",
    4: "Research Associate",
    5: "Community Contributor",
    6: "Policy Analyst",
    7: "Senior Reviewer",
    8: "Operations Lead",
    9: "System Administrator",
    10: "Master Administrator"
}
ROLE_TO_LEVEL = {v.lower(): k for k, v in ROLE_TIERS.items()}

PRIVATE_PAGES_CATALOG = [
    {"route": "/durhampolitics", "title": "Durham Politics Tracker"},
    {"route": "/agents", "title": "Agent Command Center"},
    {"route": "/taskpriority", "title": "Decision Desk Approvals"},
    {"route": "/internal/vibes.html", "title": "Real-Time Vibes Monitor"},
    {"route": "/internal/test_inbox.html", "title": "Test Mailbox (outputtest@rannbar-on.com)"},
    {"route": "/voice", "title": "Voice Dictation Bridge"},
    {"route": "/dashboard/accounts", "title": "User Administration Console"}
]

ACTIVE_2FA_CHALLENGES = {}

# Try importing send_duke_email from gradescope_tasks
sys.path.insert(0, "/home/rann/src/gradescopetools")
try:
    from gradescope_tasks import send_duke_email
except ImportError:
    send_duke_email = None

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    hashed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100000).hex()
    return hashed, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    computed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100000).hex()
    return secrets.compare_digest(computed, stored_hash)

def is_nida_allam(full_name: str, email: str, username: str) -> bool:
    """Detects if user is Commissioner Nida Allam."""
    fn = (full_name or "").lower().strip()
    em = (email or "").lower().strip()
    un = (username or "").lower().strip()
    if "nida" in fn and "allam" in fn:
        return True
    if un in ["nida", "nidaallam", "nallam"]:
        return True
    if em.startswith("nida.allam") or em.startswith("nallam") or em.startswith("nidaallam") or "nida" in em and "allam" in em:
        return True
    return False

def notify_rann_nida_onboarding(full_name: str, email: str, username: str):
    """Sends immediate notice to Rann when Commissioner Nida Allam registers."""
    subject = "[Account Provisioned] Commissioner Nida Allam Onboarded to Durham Politics Tracker"
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 580px; margin: 0 auto; color: #1e293b; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;">
      <div style="background: linear-gradient(135deg, #001A57, #0A3282); padding: 20px; color: #ffffff;">
        <h2 style="margin: 0; font-size: 19px;">Commissioner Nida Allam Onboarded</h2>
        <p style="margin: 4px 0 0 0; opacity: 0.85; font-size: 13px;">Automatic Access Provisioning &bull; Durham Politics Tracker</p>
      </div>
      <div style="padding: 22px;">
        <p style="font-size: 14px; margin-top: 0;">Notice: Commissioner Nida Allam has registered and was automatically provisioned with access and redirected to the Durham Politics Tracker.</p>
        <ul style="font-size: 13.5px; line-height: 1.8; color: #334155;">
          <li><strong>Full Name:</strong> {full_name}</li>
          <li><strong>Email Address:</strong> {email}</li>
          <li><strong>Username:</strong> {username}</li>
          <li><strong>Role Tier:</strong> Policy Analyst (Level 6)</li>
          <li><strong>Allowed Pages:</strong> /durhampolitics</li>
          <li><strong>Status:</strong> APPROVED (Instant Active)</li>
        </ul>
      </div>
    </div>
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching Nida Allam onboarding notification strictly to rann@rannbar-on.com...")
    if send_duke_email:
        try:
            send_duke_email(
                recipient="rann@rannbar-on.com",
                cc_recipients=None,
                subject=subject,
                content=html,
                is_html=True,
                allow_dropped=True
            )
        except Exception as ex:
            print(f"Warning: send_duke_email failed: {ex}")

def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                privilege_level INTEGER NOT NULL DEFAULT 1,
                privilege_name TEXT NOT NULL DEFAULT 'Guest',
                allowed_pages TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
                created_at TEXT NOT NULL,
                last_login TEXT,
                notes TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                ip_address TEXT,
                success INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT
            )
        """)

        # Migration: Ensure privilege_name and allowed_pages exist if table was previously created
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "privilege_name" not in columns:
            cursor.execute("ALTER TABLE accounts ADD COLUMN privilege_name TEXT NOT NULL DEFAULT 'Guest'")
        if "allowed_pages" not in columns:
            cursor.execute("ALTER TABLE accounts ADD COLUMN allowed_pages TEXT NOT NULL DEFAULT '[]'")

        # Ensure 'rann' admin account exists with Master Administrator role and full page access
        cursor.execute("SELECT id FROM accounts WHERE username = 'rann'")
        row = cursor.fetchone()
        now_iso = datetime.now(timezone.utc).isoformat()
        if not row:
            hashed, salt = hash_password(MASTER_PASSWORD)
            cursor.execute("""
                INSERT INTO accounts (username, full_name, email, password_hash, salt, privilege_level, privilege_name, allowed_pages, status, created_at, notes)
                VALUES (?, ?, ?, ?, ?, 10, 'Master Administrator', '[\"*\"]', 'APPROVED', ?, 'Master Administrator Account')
            """, ("rann", "Rann Bar-On", "rann@rannbar-on.com", hashed, salt, now_iso))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Seeded Master Administrator 'rann'.")
        else:
            cursor.execute("""
                UPDATE accounts 
                SET privilege_level = 10, privilege_name = 'Master Administrator', allowed_pages = '[\"*\"]', status = 'APPROVED'
                WHERE username = 'rann'
            """)
        conn.commit()
    export_sanitized_accounts_json()

def export_sanitized_accounts_json():
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, email, privilege_level, privilege_name, allowed_pages, status, created_at, last_login
                FROM accounts ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            accounts = []
            for r in rows:
                d = dict(r)
                try:
                    d["allowed_pages"] = json.loads(d.get("allowed_pages") or "[]")
                except Exception:
                    d["allowed_pages"] = []
                accounts.append(d)
        
        with open(JSON_CACHE_PATH, "w") as f:
            json.dump({
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total": len(accounts),
                "accounts": accounts,
                "role_tiers": ROLE_TIERS,
                "catalog": PRIVATE_PAGES_CATALOG
            }, f, indent=2)
    except Exception as e:
        print(f"Error exporting sanitized JSON: {e}")

def dispatch_2fa_email(email: str, code: str, purpose: str = "Authentication", user_name: str = "") -> bool:
    subject = f"[Security 2FA] Your Verification Passcode: {code}"
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 540px; margin: 0 auto; color: #1e293b; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="background: linear-gradient(135deg, #001A57, #0A3282); padding: 24px; color: #ffffff; text-align: center;">
        <h2 style="margin: 0 0 6px 0; font-size: 22px;">Security Verification Code</h2>
        <p style="margin: 0; opacity: 0.85; font-size: 13.5px;">RannBar-On.com &bull; Two-Factor {purpose}</p>
      </div>

      <div style="padding: 28px 24px; text-align: center;">
        <p style="font-size: 14px; color: #475569; margin-bottom: 20px;">
          {f"Hello <strong>{user_name}</strong>," if user_name else "Hello,"}<br>
          Please enter the following one-time security passcode to complete your {purpose.lower()}:
        </p>

        <div style="background: #f1f5f9; border: 2px dashed #00539b; border-radius: 8px; padding: 18px 24px; margin: 0 auto 24px auto; display: inline-block;">
          <span style="font-size: 34px; font-weight: 800; letter-spacing: 8px; font-family: monospace; color: #00539b; margin-left: 8px;">{code}</span>
        </div>

        <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 12px 16px; font-size: 12.5px; color: #92400e; margin-bottom: 20px; text-align: left;">
          <i style="font-style: normal; font-weight: 700;">Important Expiration Rules:</i>
          <ul style="margin: 6px 0 0 18px; padding: 0;">
            <li>This passcode expires in <strong>5 minutes</strong>.</li>
            <li>If an incorrect code is entered, a <strong>30-second countdown</strong> will begin.</li>
            <li>Entering an incorrect code twice or letting the timer expire will cancel the session.</li>
          </ul>
        </div>

        <p style="font-size: 12px; color: #94a3b8; margin: 0;">
          If you did not initiate this request, you can safely ignore this email.
        </p>
      </div>

      <div style="background: #f8fafc; padding: 12px 20px; border-top: 1px solid #e2e8f0; font-size: 11.5px; color: #94a3b8; text-align: center;">
        Automated Security Dispatch &bull; RannBar-On.com Authentication Gateway
      </div>
    </div>
    """

    target_email = resolve_email_recipient(email)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching 2FA passcode {code} to {target_email}...")
    sent = False
    if send_duke_email:
        try:
            sent = send_duke_email(
                recipient=target_email,
                cc_recipients=None,
                subject=subject,
                content=html,
                is_html=True,
                allow_dropped=True
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 2FA email dispatched via send_duke_email to {target_email}.")
        except Exception as ex:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: 2FA send_duke_email failed: {ex}")
    
    if not sent:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fallback logged 2FA code {code} for {target_email}.")
    return sent

def notify_rann_new_signup(full_name: str, email: str, username: str, timestamp: str, role_name: str = "Guest"):
    subject = f"[Account Request] New User Registration: {full_name} ({username})"
    review_url = "https://rannbar-on.com/dashboard/accounts"
    
    html_content = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 620px; margin: 0 auto; color: #1e293b; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="background: linear-gradient(135deg, #001A57, #0A3282); padding: 24px; color: #ffffff;">
        <h2 style="margin: 0 0 6px 0; font-size: 20px;">RannBar-On.com &bull; New User Signup Alert</h2>
        <p style="margin: 0; opacity: 0.85; font-size: 13.5px;">A new account registration has been submitted and verified via 2FA.</p>
      </div>

      <div style="padding: 24px;">
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 14px;">
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 0; font-weight: 600; color: #64748b; width: 140px;">Full Name</td>
            <td style="padding: 10px 0; font-weight: 700; color: #0f172a;">{full_name}</td>
          </tr>
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Email Address</td>
            <td style="padding: 10px 0; color: #0f172a;"><a href="mailto:{email}" style="color: #2563eb; text-decoration: none;">{email}</a></td>
          </tr>
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Username</td>
            <td style="padding: 10px 0; font-family: monospace; color: #0f172a;">{username}</td>
          </tr>
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Signup Timestamp</td>
            <td style="padding: 10px 0; color: #0f172a;">{timestamp}</td>
          </tr>
          <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Default Role Tier</td>
            <td style="padding: 10px 0; color: #0f172a;"><span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;">{role_name} (Public Only)</span></td>
          </tr>
          <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Status</td>
            <td style="padding: 10px 0; color: #d97706; font-weight: 700;"><span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 4px; font-size: 12px;">PENDING_APPROVAL</span></td>
          </tr>
        </table>

        <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 6px; margin-bottom: 24px;">
          <p style="margin: 0; font-size: 13.5px; color: #334155;">
            <strong>Action Required:</strong> Review role tiers and configure granular page permissions in the Admin Console.
          </p>
        </div>

        <div style="text-align: center; margin-bottom: 8px;">
          <a href="{review_url}" style="background: #00539b; color: #ffffff; padding: 12px 26px; border-radius: 6px; font-weight: 700; font-size: 14px; text-decoration: none; display: inline-block;">
            Open Accounts Management Dashboard &rarr;
          </a>
        </div>
      </div>
    </div>
    """

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching new signup alert for {email} strictly to rann@rannbar-on.com...")
    if send_duke_email:
        try:
            send_duke_email(
                recipient="rann@rannbar-on.com",
                cc_recipients=None,
                subject=subject,
                content=html_content,
                is_html=True,
                allow_dropped=True
            )
        except Exception as ex:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: send_duke_email failed: {ex}")

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class AccountHTTPHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Admin-Password, X-Requested-With")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, status_code: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_admin_authenticated(self) -> bool:
        admin_pwd = self.headers.get("X-Admin-Password")
        if admin_pwd == MASTER_PASSWORD:
            return True
        
        auth_header = self.headers.get("Authorization", "")
        if auth_header:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
                if token == MASTER_PASSWORD:
                    return True
            import base64
            if auth_header.startswith("Basic "):
                try:
                    decoded = base64.b64decode(auth_header[6:]).decode("utf-8")
                    u, p = decoded.split(":", 1)
                    if (u == "rann" and p == MASTER_PASSWORD) or p == MASTER_PASSWORD:
                        return True
                except Exception:
                    pass
        return False

    def do_GET(self):
        url_path = self.path.split("?")[0]
        
        if url_path == "/api/accounts":
            if not self._is_admin_authenticated():
                self._send_json(401, {"success": False, "error": "Unauthorized: Administrator access required."})
                return
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, full_name, email, privilege_level, privilege_name, allowed_pages, status, created_at, last_login, notes
                    FROM accounts ORDER BY id ASC
                """)
                rows = cursor.fetchall()
                accounts = []
                for r in rows:
                    item = dict(r)
                    try:
                        item["allowed_pages"] = json.loads(item.get("allowed_pages") or "[]")
                    except Exception:
                        item["allowed_pages"] = []
                    accounts.append(item)
            
            self._send_json(200, {
                "success": True,
                "accounts": accounts,
                "count": len(accounts),
                "role_tiers": ROLE_TIERS,
                "catalog": PRIVATE_PAGES_CATALOG
            })
            return

        elif url_path == "/api/catalog":
            self._send_json(200, {
                "success": True,
                "catalog": PRIVATE_PAGES_CATALOG,
                "role_tiers": ROLE_TIERS
            })
            return
            
        elif url_path == "/api/health":
            self._send_json(200, {"status": "ok", "service": "accounts-api", "timestamp": datetime.now(timezone.utc).isoformat()})
            return

        elif url_path == "/api/test/2fa_code":
            # Strictly for outputtest@rannbar-on.com automated verification tests
            import urllib.parse
            parsed_query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            cid = parsed_query.get("challenge_id", [""])[0]
            challenge = ACTIVE_2FA_CHALLENGES.get(cid)
            if challenge and challenge.get("email") == DEFAULT_TEST_EMAIL:
                self._send_json(200, {"success": True, "code": challenge["code"]})
                return
            self._send_json(404, {"success": False, "error": "Challenge not found or not a test account."})
            return

        elif url_path == "/api/test_inbox":
            # Test inbox endpoint - returns captured messages from /home/rann/src/test_inbox/messages.json
            try:
                sys.path.insert(0, "/home/rann/src/test_inbox")
                import inbox
                messages = inbox.get_messages(limit=100)
                self._send_json(200, {
                    "success": True,
                    "inbox": "outputtest@rannbar-on.com",
                    "total": len(messages),
                    "messages": messages
                })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
            return

        self._send_json(404, {"success": False, "error": "Endpoint not found"})

    def do_POST(self):
        url_path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""
        
        try:
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except json.JSONDecodeError:
            self._send_json(400, {"success": False, "error": "Invalid JSON body"})
            return

        now_ts = time.time()

        # ----------------------------------------------------
        # 1. POST /api/register (Signup step 1)
        # ----------------------------------------------------
        if url_path == "/api/register":
            full_name = payload.get("fullName", "").strip()
            email = payload.get("email", "").strip().lower()
            username = payload.get("username", "").strip().lower()
            password = payload.get("password", "")

            if not full_name:
                self._send_json(400, {"success": False, "error": "Full name is required"})
                return
            if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                self._send_json(400, {"success": False, "error": "A valid email address is required"})
                return
            # Enforce 20+ chars and mix of letters, numbers, and symbols
            if not password or len(password) < 20:
                self._send_json(400, {"success": False, "error": "Password must be at least 20 characters in length."})
                return
            if not re.search(r"[A-Za-z]", password):
                self._send_json(400, {"success": False, "error": "Password must include letters (A-Z, a-z)."})
                return
            if not re.search(r"[0-9]", password):
                self._send_json(400, {"success": False, "error": "Password must include numbers (0-9)."})
                return
            if not re.search(r"[^A-Za-z0-9]", password):
                self._send_json(400, {"success": False, "error": "Password must include special symbols (!@#$%^&*...)."})
                return
            
            if not username:
                username = email.split("@")[0]
                username = re.sub(r"[^a-z0-9_]", "", username)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM accounts WHERE username = ?", (username,))
                if cursor.fetchone():
                    self._send_json(409, {"success": False, "error": f"Username '{username}' is already taken. Please choose another."})
                    return
                cursor.execute("SELECT id FROM accounts WHERE email = ?", (email,))
                if cursor.fetchone():
                    self._send_json(409, {"success": False, "error": f"An account with email '{email}' already exists."})
                    return

            code = f"{secrets.randbelow(900000) + 100000}"
            challenge_id = secrets.token_hex(16)
            hashed, salt = hash_password(password)

            is_nida = is_nida_allam(full_name, email, username)
            default_role = "Policy Analyst" if is_nida else "Guest"
            default_level = 6 if is_nida else 1
            default_pages = json.dumps(["/durhampolitics"]) if is_nida else json.dumps([])
            default_status = "APPROVED" if is_nida else "PENDING_APPROVAL"

            ACTIVE_2FA_CHALLENGES[challenge_id] = {
                "type": "signup",
                "code": code,
                "email": email,
                "is_nida": is_nida,
                "created_at": now_ts,
                "expires_at": now_ts + 300.0,
                "attempts": 0,
                "grace_expires_at": None,
                "payload": {
                    "username": username,
                    "full_name": full_name,
                    "email": email,
                    "password_hash": hashed,
                    "salt": salt,
                    "privilege_level": default_level,
                    "privilege_name": default_role,
                    "allowed_pages": default_pages,
                    "status": default_status,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            }

            dispatch_2fa_email(email=email, code=code, purpose="Account Registration", user_name=full_name)

            self._send_json(200, {
                "success": True,
                "two_factor_required": True,
                "challenge_id": challenge_id,
                "email_masked": mask_email(email),
                "expires_in": 300,
                "message": f"Verification passcode dispatched to {mask_email(email)}. Valid for 5 minutes."
            })
            return

        # ----------------------------------------------------
        # 2. POST /api/accounts/login (Login step 1)
        # ----------------------------------------------------
        elif url_path == "/api/accounts/login":
            username = payload.get("username", "").strip().lower()
            password = payload.get("password", "")

            if not username or not password:
                self._send_json(400, {"success": False, "error": "Username and password are required"})
                return

            user_record = None

            if (username == "rann" and password == MASTER_PASSWORD) or password == MASTER_PASSWORD:
                user_record = {
                    "username": "rann",
                    "fullName": "Rann Bar-On",
                    "email": "rann@rannbar-on.com",
                    "privilegeLevel": 10,
                    "privilegeName": "Master Administrator",
                    "allowedPages": ["*"],
                    "status": "APPROVED"
                }
            elif username == "durhampol" and password == "durhampol":
                user_record = {
                    "username": "durhampol",
                    "fullName": "Durham Politics Guest",
                    "email": "rann@rannbar-on.com",
                    "privilegeLevel": 2,
                    "privilegeName": "Standard Member",
                    "allowedPages": ["/durhampolitics"],
                    "status": "APPROVED"
                }
            else:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, username, full_name, email, password_hash, salt, privilege_level, privilege_name, allowed_pages, status
                        FROM accounts WHERE username = ? OR email = ?
                    """, (username, username))
                    row = cursor.fetchone()

                    if not row or not verify_password(password, row["password_hash"], row["salt"]):
                        self._send_json(401, {"success": False, "error": "Invalid username or password"})
                        return

                    if row["status"] == "PENDING_APPROVAL":
                        self._send_json(403, {"success": False, "error": "Account is pending administrator approval."})
                        return
                    elif row["status"] in ["REJECTED", "DEACTIVATED"]:
                        self._send_json(403, {"success": False, "error": "Account has been deactivated or rejected."})
                        return

                    try:
                        pages = json.loads(row["allowed_pages"] or "[]")
                    except Exception:
                        pages = []

                    user_record = {
                        "id": row["id"],
                        "username": row["username"],
                        "fullName": row["full_name"],
                        "email": row["email"],
                        "privilegeLevel": row["privilege_level"],
                        "privilegeName": row["privilege_name"] or ROLE_TIERS.get(row["privilege_level"], "Guest"),
                        "allowedPages": pages,
                        "status": row["status"]
                    }

            code = f"{secrets.randbelow(900000) + 100000}"
            challenge_id = secrets.token_hex(16)
            dest_email = user_record["email"]

            ACTIVE_2FA_CHALLENGES[challenge_id] = {
                "type": "login",
                "code": code,
                "email": dest_email,
                "created_at": now_ts,
                "expires_at": now_ts + 300.0,
                "attempts": 0,
                "grace_expires_at": None,
                "user_data": user_record
            }

            dispatch_2fa_email(email=dest_email, code=code, purpose="Login Authorization", user_name=user_record.get("fullName", ""))

            self._send_json(200, {
                "success": True,
                "two_factor_required": True,
                "challenge_id": challenge_id,
                "email_masked": mask_email(dest_email),
                "expires_in": 300,
                "message": f"Security passcode dispatched to {mask_email(dest_email)}. Valid for 5:00 minutes."
            })
            return

        # ----------------------------------------------------
        # 3. POST /api/auth/verify_2fa (Step 2: 2FA verification)
        # ----------------------------------------------------
        elif url_path == "/api/auth/verify_2fa":
            challenge_id = payload.get("challenge_id", "").strip()
            submitted_code = payload.get("code", "").strip()

            if not challenge_id or not submitted_code:
                self._send_json(400, {"success": False, "error": "challenge_id and code are required"})
                return

            challenge = ACTIVE_2FA_CHALLENGES.get(challenge_id)
            if not challenge:
                self._send_json(400, {"success": False, "error": "Session expired or invalid. Please sign in again.", "kicked": True})
                return

            if now_ts > challenge["expires_at"]:
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                self._send_json(400, {"success": False, "error": "Passcode expired (5-minute limit exceeded). Session terminated.", "kicked": True})
                return

            if challenge["grace_expires_at"] and now_ts > challenge["grace_expires_at"]:
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                self._send_json(400, {"success": False, "error": "30-second error correction timer expired. Session terminated.", "kicked": True})
                return

            if submitted_code != challenge["code"]:
                challenge["attempts"] += 1
                if challenge["attempts"] >= 2:
                    ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                    self._send_json(403, {"success": False, "error": "Incorrect code on second attempt. Session terminated for security.", "kicked": True})
                    return
                else:
                    challenge["grace_expires_at"] = now_ts + 30.0
                    self._send_json(400, {
                        "success": False,
                        "error": "Incorrect verification code. You have 30 seconds to correct and re-enter it.",
                        "grace_period_seconds": 30,
                        "attempt": 1,
                        "kicked": False
                    })
                    return

            c_type = challenge["type"]
            if c_type == "login":
                user = challenge["user_data"]
                now_iso = datetime.now(timezone.utc).isoformat()
                if "id" in user:
                    with get_db() as conn:
                        conn.execute("UPDATE accounts SET last_login = ? WHERE id = ?", (now_iso, user["id"]))
                        conn.commit()
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                export_sanitized_accounts_json()
                self._send_json(200, {
                    "success": True,
                    "user": user,
                    "token": MASTER_PASSWORD if (user.get("privilegeLevel") == 10) else user.get("username")
                })
                return

            elif c_type == "signup":
                p = challenge["payload"]
                try:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO accounts (username, full_name, email, password_hash, salt, privilege_level, privilege_name, allowed_pages, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (p["username"], p["full_name"], p["email"], p["password_hash"], p["salt"], p["privilege_level"], p["privilege_name"], p["allowed_pages"], p["status"], p["created_at"]))
                        conn.commit()
                except sqlite3.IntegrityError:
                    ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                    self._send_json(409, {"success": False, "error": "Account already exists.", "kicked": True})
                    return

                is_nida = challenge.get("is_nida", False) or is_nida_allam(p["full_name"], p["email"], p["username"])
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                export_sanitized_accounts_json()

                if is_nida:
                    notify_rann_nida_onboarding(
                        full_name=p["full_name"],
                        email=p["email"],
                        username=p["username"]
                    )
                    self._send_json(201, {
                        "success": True,
                        "redirect": "/durhampolitics",
                        "message": "Welcome Commissioner Nida Allam! Your account is active and you are being redirected to the Durham Politics Tracker.",
                        "user": {
                            "username": p["username"],
                            "fullName": p["full_name"],
                            "email": p["email"],
                            "privilegeLevel": p["privilege_level"],
                            "privilegeName": p["privilege_name"],
                            "allowedPages": json.loads(p["allowed_pages"]),
                            "status": "APPROVED"
                        }
                    })
                    return
                else:
                    notify_rann_new_signup(
                        full_name=p["full_name"],
                        email=p["email"],
                        username=p["username"],
                        timestamp=p["created_at"],
                        role_name=p["privilege_name"]
                    )
                    self._send_json(201, {
                        "success": True,
                        "message": "Registration verified! Account is pending administrator approval.",
                        "user": {
                            "username": p["username"],
                            "fullName": p["full_name"],
                            "email": p["email"],
                            "privilegeLevel": p["privilege_level"],
                            "privilegeName": p["privilege_name"],
                            "allowedPages": json.loads(p["allowed_pages"]),
                            "status": p["status"]
                        }
                    })
                    return

        # ----------------------------------------------------
        # Authenticated Admin Action Endpoints
        # ----------------------------------------------------
        if not self._is_admin_authenticated():
            self._send_json(401, {"success": False, "error": "Unauthorized: Administrator access required."})
            return

        # ----------------------------------------------------
        # 4. POST /api/accounts/update_permissions (Granular role + pages update)
        # ----------------------------------------------------
        if url_path == "/api/accounts/update_permissions":
            user_id = payload.get("id") or payload.get("user_id")
            username = payload.get("username")
            privilege_name = payload.get("privilege_name")
            privilege_level = payload.get("privilege_level")
            allowed_pages = payload.get("allowed_pages")

            if not user_id and not username:
                self._send_json(400, {"success": False, "error": "User ID or username is required"})
                return

            if privilege_name and not privilege_level:
                privilege_level = ROLE_TO_LEVEL.get(privilege_name.lower().strip(), 1)
            elif privilege_level and not privilege_name:
                try:
                    privilege_level = int(privilege_level)
                    privilege_name = ROLE_TIERS.get(privilege_level, "Guest")
                except ValueError:
                    privilege_level = 1
                    privilege_name = "Guest"

            if allowed_pages is not None:
                if isinstance(allowed_pages, list):
                    pages_json = json.dumps(allowed_pages)
                else:
                    pages_json = json.dumps([str(allowed_pages)])
            else:
                pages_json = None

            with get_db() as conn:
                cursor = conn.cursor()
                # Protect Master Admin 'rann'
                if user_id:
                    cursor.execute("SELECT username FROM accounts WHERE id = ?", (user_id,))
                    u_row = cursor.fetchone()
                    if u_row and u_row["username"] == "rann":
                        privilege_level = 10
                        privilege_name = "Master Administrator"
                        pages_json = json.dumps(["*"])

                    if pages_json is not None:
                        cursor.execute("""
                            UPDATE accounts 
                            SET privilege_level = ?, privilege_name = ?, allowed_pages = ?
                            WHERE id = ?
                        """, (privilege_level, privilege_name, pages_json, user_id))
                    else:
                        cursor.execute("""
                            UPDATE accounts 
                            SET privilege_level = ?, privilege_name = ?
                            WHERE id = ?
                        """, (privilege_level, privilege_name, user_id))
                else:
                    if username == "rann":
                        privilege_level = 10
                        privilege_name = "Master Administrator"
                        pages_json = json.dumps(["*"])

                    if pages_json is not None:
                        cursor.execute("""
                            UPDATE accounts 
                            SET privilege_level = ?, privilege_name = ?, allowed_pages = ?
                            WHERE username = ?
                        """, (privilege_level, privilege_name, pages_json, username))
                    else:
                        cursor.execute("""
                            UPDATE accounts 
                            SET privilege_level = ?, privilege_name = ?
                            WHERE username = ?
                        """, (privilege_level, privilege_name, username))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {
                "success": True,
                "message": f"Permissions updated: Role set to '{privilege_name}', allowed pages saved.",
                "privilege_name": privilege_name,
                "privilege_level": privilege_level
            })
            return

        elif url_path == "/api/accounts/approve":
            user_id = payload.get("id")
            email = payload.get("email")
            role_name = payload.get("privilege_name")
            new_level = payload.get("privilege_level")
            allowed_pages = payload.get("allowed_pages")

            if new_level and not role_name:
                role_name = ROLE_TIERS.get(int(new_level), "Guest")
            elif role_name and not new_level:
                new_level = ROLE_TO_LEVEL.get(role_name.lower().strip(), 2)
            elif not new_level and not role_name:
                new_level = 2
                role_name = "Standard Member"

            pages_json = json.dumps(allowed_pages) if allowed_pages is not None else None

            with get_db() as conn:
                cursor = conn.cursor()
                if user_id:
                    if pages_json is not None:
                        cursor.execute("""
                            UPDATE accounts 
                            SET status = 'APPROVED', privilege_level = ?, privilege_name = ?, allowed_pages = ?
                            WHERE id = ?
                        """, (new_level, role_name, pages_json, user_id))
                    else:
                        cursor.execute("""
                            UPDATE accounts 
                            SET status = 'APPROVED', privilege_level = ?, privilege_name = ?
                            WHERE id = ?
                        """, (new_level, role_name, user_id))
                else:
                    if pages_json is not None:
                        cursor.execute("""
                            UPDATE accounts 
                            SET status = 'APPROVED', privilege_level = ?, privilege_name = ?, allowed_pages = ?
                            WHERE email = ?
                        """, (new_level, role_name, pages_json, email))
                    else:
                        cursor.execute("""
                            UPDATE accounts 
                            SET status = 'APPROVED', privilege_level = ?, privilege_name = ?
                            WHERE email = ?
                        """, (new_level, role_name, email))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": f"User account approved with role '{role_name}'."})
            return

        elif url_path == "/api/accounts/reject":
            user_id = payload.get("id")
            email = payload.get("email")

            if not user_id and not email:
                self._send_json(400, {"success": False, "error": "User ID or email is required"})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("UPDATE accounts SET status = 'REJECTED' WHERE id = ? AND username != 'rann'", (user_id,))
                else:
                    cursor.execute("UPDATE accounts SET status = 'REJECTED' WHERE email = ? AND username != 'rann'", (email,))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": "User account status set to REJECTED."})
            return

        elif url_path == "/api/accounts/update_level":
            user_id = payload.get("id")
            new_level = payload.get("privilege_level")
            role_name = payload.get("privilege_name")

            if not user_id or (new_level is None and role_name is None):
                self._send_json(400, {"success": False, "error": "User ID and privilege_level or privilege_name are required"})
                return

            if new_level is not None:
                new_level = int(new_level)
                role_name = ROLE_TIERS.get(new_level, "Guest")
            else:
                role_name = str(role_name).strip()
                new_level = ROLE_TO_LEVEL.get(role_name.lower(), 1)

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE accounts 
                    SET privilege_level = ?, privilege_name = ? 
                    WHERE id = ? AND username != 'rann'
                """, (new_level, role_name, user_id))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": f"Role tier updated to '{role_name}' (Level {new_level})."})
            return

        elif url_path == "/api/accounts/delete":
            user_id = payload.get("id")
            if not user_id:
                self._send_json(400, {"success": False, "error": "User ID is required"})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM accounts WHERE id = ? AND username != 'rann'", (user_id,))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": "User deleted successfully."})
            return

        self._send_json(404, {"success": False, "error": "Endpoint not found"})

def send_test_email(email=DEFAULT_TEST_EMAIL):
    code = f"{secrets.randbelow(900000) + 100000}"
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending test 2FA verification email to {email}...")
    sent = dispatch_2fa_email(email=email, code=code, purpose="Test Verification", user_name="Test Operator")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Test email dispatched: success={sent}")
    return sent

def run_self_tests(port=DEFAULT_PORT) -> bool:
    import urllib.request
    import urllib.error
    print(f"[{datetime.now().strftime('%H:%M:%S')}] === RUNNING ACCOUNT SERVER SELF-TESTS ===")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Safe test recipient configured: {DEFAULT_TEST_EMAIL}")
    
    # 1. Test Email Sanitization & Guardrails
    print("Test 1: Testing email recipient resolution & safeguards...")
    assert resolve_email_recipient("test@example.com") == DEFAULT_TEST_EMAIL
    assert resolve_email_recipient("nida.allam@dconc.gov") == DEFAULT_TEST_EMAIL
    assert resolve_email_recipient("fakeuser@test.org") == DEFAULT_TEST_EMAIL
    assert resolve_email_recipient("outputtest@rannbar-on.com") == DEFAULT_TEST_EMAIL
    assert resolve_email_recipient("rann@rannbar-on.com") == "rann@rannbar-on.com"
    print("  -> PASSED: All synthetic/dummy/third-party emails correctly rerouted to outputtest@rannbar-on.com")

    # 2. Test Password Policy Rejections via API
    base_url = f"http://127.0.0.1:{port}"
    print("Test 2: Testing password strength requirements...")
    
    def post_json(path, data):
        req = urllib.request.Request(
            f"{base_url}{path}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    # Password too short (<20 chars)
    status, res = post_json("/api/register", {
        "fullName": "Test User",
        "email": DEFAULT_TEST_EMAIL,
        "password": "Short!1"
    })
    assert status == 400 and "20 characters" in res.get("error", "")
    print("  -> PASSED: Short password (<20 chars) rejected.")

    # Password missing numbers
    status, res = post_json("/api/register", {
        "fullName": "Test User",
        "email": DEFAULT_TEST_EMAIL,
        "password": "ThisPasswordHasNoNumbersAtAll!"
    })
    assert status == 400 and "numbers" in res.get("error", "")
    print("  -> PASSED: Password missing numbers rejected.")

    # Password missing symbols
    status, res = post_json("/api/register", {
        "fullName": "Test User",
        "email": DEFAULT_TEST_EMAIL,
        "password": "ThisPasswordHasNoSymbols12345678"
    })
    assert status == 400 and "symbols" in res.get("error", "")
    print("  -> PASSED: Password missing symbols rejected.")

    # 3. Test Full Registration & 2FA Flow with outputtest@rannbar-on.com
    print(f"Test 3: Testing registration and 2FA flow strictly using {DEFAULT_TEST_EMAIL}...")
    valid_test_password = "SecureVerificationTestPass!2026@"
    test_uname = f"testuser_{int(time.time())}"
    
    status, res = post_json("/api/register", {
        "fullName": "Synthetic Test User",
        "username": test_uname,
        "email": DEFAULT_TEST_EMAIL,
        "password": valid_test_password
    })
    assert status == 200 and res.get("two_factor_required") is True, f"Registration failed: {res}"
    challenge_id = res.get("challenge_id")
    print(f"  -> PASSED: 2FA challenge generated: {challenge_id}")

    # Retrieve test code via /api/test/2fa_code (available only for outputtest@rannbar-on.com)
    code_req = urllib.request.urlopen(f"{base_url}/api/test/2fa_code?challenge_id={challenge_id}")
    code_data = json.loads(code_req.read().decode("utf-8"))
    code = code_data.get("code")
    assert code is not None, "Failed to retrieve test 2FA code"
    print(f"  -> Challenge code verified for {DEFAULT_TEST_EMAIL}: {code}")

    # Verify 2FA
    status, res = post_json("/api/auth/verify_2fa", {
        "challenge_id": challenge_id,
        "code": code
    })
    assert status == 201, f"2FA verification failed: {res}"
    print("  -> PASSED: 2FA verification succeeded.")

    # Verify user created in DB
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, privilege_name, status FROM accounts WHERE username = ?", (test_uname,))
        row = cursor.fetchone()
        assert row is not None, "User not found in accounts DB"
        assert row["email"] == DEFAULT_TEST_EMAIL
        user_id = row["id"]
        print(f"  -> PASSED: User '{test_uname}' found in DB (ID: {user_id}, Status: {row['status']}).")

        # Clean up test user
        cursor.execute("DELETE FROM accounts WHERE id = ?", (user_id,))
        conn.commit()
    export_sanitized_accounts_json()
    print(f"  -> Cleaned up test user '{test_uname}' from accounts DB.")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] === ALL SELF-TESTS PASSED SUCCESSFULLY ===")
    return True

def run_server(port=DEFAULT_PORT):
    init_db()
    server_address = ("0.0.0.0", port)
    httpd = ThreadedHTTPServer(server_address, AccountHTTPHandler)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Account & 2FA Server running at http://0.0.0.0:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Account Management & 2FA Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    parser.add_argument("--init-only", action="store_true", help="Initialize database and exit")
    parser.add_argument("--test-email", action="store_true", help=f"Send a test verification email to {DEFAULT_TEST_EMAIL}")
    parser.add_argument("--run-tests", action="store_true", help=f"Run automated registration and 2FA self-tests using {DEFAULT_TEST_EMAIL}")
    args = parser.parse_args()

    if args.init_only:
        init_db()
        print("Database initialized successfully.")
    elif args.test_email:
        send_test_email()
    elif args.run_tests:
        run_self_tests(args.port)
    else:
        run_server(args.port)
