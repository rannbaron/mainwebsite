#!/usr/bin/env python3
"""
RannBar-On.com User Account Management & 2FA Authentication Server
================================================================
Handles user registration, two-factor email authentication (2FA),
privilege authorization, and admin review workflows for rannbar-on.com.

Features:
- SQLite persistent storage in /home/rann/src/website/mainwebsite/accounts.db
- Secure salted PBKDF2/SHA-256 password hashing (100,000 iterations)
- Immediate notification emails to rann@rannbar-on.com
- 2FA One-Time Passcodes (6 digits, valid 5 minutes)
- Live 5:00 countdown timer & strict 30-second error correction timer
- Automatic invalidation on second failed attempt, 30s timer expiry, or 5m timer expiry
- Privilege levels 1-10 (Level 1: Public only, Level 10: Full Admin Control)
- Seeded admin account for 'rann' (Level 10, APPROVED)
- REST API with full CORS support and fallback sync
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

# In-memory store for active 2FA challenges
# Format: { challenge_id: { "type": "login"|"signup", "code": "123456", "expires_at": float, "attempts": int, "grace_expires_at": float|None, "user_data": dict, "payload": dict } }
ACTIVE_2FA_CHALLENGES = {}

# Try importing send_duke_email from gradescope_tasks
sys.path.insert(0, "/home/rann/src/gradescopetools")
try:
    from gradescope_tasks import send_duke_email
except ImportError:
    send_duke_email = None

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Generates a salt and hashes password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    hashed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100000).hex()
    return hashed, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a password against the stored PBKDF2 hash."""
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    computed = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100000).hex()
    return secrets.compare_digest(computed, stored_hash)

def mask_email(email: str) -> str:
    """Masks an email for safe client display, e.g. j***e@domain.com."""
    if "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "***" + local[-1]
    return f"{masked_local}@{domain}"

def get_db():
    """Returns a SQLite database connection with row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds the administrator account."""
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
        
        # Check if 'rann' admin account exists
        cursor.execute("SELECT id FROM accounts WHERE username = 'rann'")
        row = cursor.fetchone()
        if not row:
            hashed, salt = hash_password(MASTER_PASSWORD)
            now_iso = datetime.now(timezone.utc).isoformat()
            cursor.execute("""
                INSERT INTO accounts (username, full_name, email, password_hash, salt, privilege_level, status, created_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "rann",
                "Rann Bar-On",
                "rann@rannbar-on.com",
                hashed,
                salt,
                10,
                "APPROVED",
                now_iso,
                "Seeded Master Administrator"
            ))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Seeded administrator account 'rann' (Level 10, APPROVED).")
        conn.commit()
    export_sanitized_accounts_json()

def export_sanitized_accounts_json():
    """Exports sanitized user accounts (excluding password hashes and salts) for static fallback."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, full_name, email, privilege_level, status, created_at, last_login
                FROM accounts ORDER BY id ASC
            """)
            rows = cursor.fetchall()
            accounts = [dict(r) for r in rows]
        
        with open(JSON_CACHE_PATH, "w") as f:
            json.dump({
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "total": len(accounts),
                "accounts": accounts
            }, f, indent=2)
    except Exception as e:
        print(f"Error exporting sanitized JSON: {e}")

def dispatch_2fa_email(email: str, code: str, purpose: str = "Authentication", user_name: str = "") -> bool:
    """Dispatches a 6-digit 2FA passcode to the user's registered email address."""
    subject = f"[Security 2FA] Your Verification Passcode: {code}"
    is_rann = (email.lower() == "rann@rannbar-on.com")
    
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

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching 2FA passcode {code} to {email}...")
    sent = False
    if send_duke_email:
        try:
            cc = None
            sent = send_duke_email(
                recipient=email,
                cc_recipients=cc,
                subject=subject,
                content=html,
                is_html=True,
                allow_dropped=True
            )
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 2FA email dispatched via send_duke_email.")
        except Exception as ex:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: 2FA send_duke_email failed: {ex}")
    
    if not sent:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fallback logged 2FA code {code} for {email}.")
    return sent

def notify_rann_new_signup(full_name: str, email: str, username: str, timestamp: str, level: int = 1):
    """Sends notification email to Rann Bar-On about a new user account registration."""
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
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Default Privilege</td>
            <td style="padding: 10px 0; color: #0f172a;"><span style="background: #e2e8f0; color: #334155; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px;">Level {level} (Public Only)</span></td>
          </tr>
          <tr>
            <td style="padding: 10px 0; font-weight: 600; color: #64748b;">Status</td>
            <td style="padding: 10px 0; color: #d97706; font-weight: 700;"><span style="background: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 4px; font-size: 12px;">PENDING_APPROVAL</span></td>
          </tr>
        </table>

        <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 14px 18px; border-radius: 6px; margin-bottom: 24px;">
          <p style="margin: 0; font-size: 13.5px; color: #334155;">
            <strong>Action Required:</strong> Please review and approve or adjust privilege levels (1–10) in the Admin Accounts Management Dashboard.
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

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dispatching new signup notification for {email} to rann@rannbar-on.com...")
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
        """Verifies if request contains the admin master credentials."""
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
                    SELECT id, username, full_name, email, privilege_level, status, created_at, last_login, notes
                    FROM accounts ORDER BY id ASC
                """)
                rows = cursor.fetchall()
                accounts = [dict(r) for r in rows]
            
            self._send_json(200, {
                "success": True,
                "accounts": accounts,
                "count": len(accounts)
            })
            return
            
        elif url_path == "/api/health":
            self._send_json(200, {"status": "ok", "service": "accounts-api", "timestamp": datetime.now(timezone.utc).isoformat()})
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
        # 1. POST /api/register (Step 1 of Signup: Validates & initiates 2FA)
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
            if not password or len(password) < 8:
                self._send_json(400, {"success": False, "error": "Password must be at least 8 characters"})
                return
            
            if not username:
                username = email.split("@")[0]
                username = re.sub(r"[^a-z0-9_]", "", username)

            # Check for existing email/username
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

            # Generate 6-digit 2FA code (valid 5 minutes = 300 seconds)
            code = f"{secrets.randbelow(900000) + 100000}"
            challenge_id = secrets.token_hex(16)
            hashed, salt = hash_password(password)

            ACTIVE_2FA_CHALLENGES[challenge_id] = {
                "type": "signup",
                "code": code,
                "email": email,
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
                    "privilege_level": 1,
                    "status": "PENDING_APPROVAL",
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
        # 2. POST /api/accounts/login (Step 1 of Login: Checks creds & dispatches 2FA)
        # ----------------------------------------------------
        elif url_path == "/api/accounts/login":
            username = payload.get("username", "").strip().lower()
            password = payload.get("password", "")

            if not username or not password:
                self._send_json(400, {"success": False, "error": "Username and password are required"})
                return

            user_record = None

            # Check master admin credential
            if (username == "rann" and password == MASTER_PASSWORD) or password == MASTER_PASSWORD:
                user_record = {
                    "username": "rann",
                    "fullName": "Rann Bar-On",
                    "email": "rann@rannbar-on.com",
                    "privilegeLevel": 10,
                    "status": "APPROVED"
                }
            elif username == "durhampol" and password == "durhampol":
                user_record = {
                    "username": "durhampol",
                    "fullName": "Durham Politics Guest",
                    "email": "rann@rannbar-on.com",
                    "privilegeLevel": 2,
                    "status": "APPROVED"
                }
            else:
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, username, full_name, email, password_hash, salt, privilege_level, status
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

                    user_record = {
                        "id": row["id"],
                        "username": row["username"],
                        "fullName": row["full_name"],
                        "email": row["email"],
                        "privilegeLevel": row["privilege_level"],
                        "status": row["status"]
                    }

            # Generate 6-digit 2FA passcode
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
        # 3. POST /api/auth/verify_2fa (Step 2: Validates Passcode with strict timers)
        # ----------------------------------------------------
        elif url_path == "/api/auth/verify_2fa":
            challenge_id = payload.get("challenge_id", "").strip()
            submitted_code = payload.get("code", "").strip()

            if not challenge_id or not submitted_code:
                self._send_json(400, {"success": False, "error": "challenge_id and code are required"})
                return

            challenge = ACTIVE_2FA_CHALLENGES.get(challenge_id)
            if not challenge:
                self._send_json(400, {
                    "success": False,
                    "error": "Session expired or invalid. Please sign in again.",
                    "kicked": True
                })
                return

            # Check Main 5-Minute Timer Expiry
            if now_ts > challenge["expires_at"]:
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                self._send_json(400, {
                    "success": False,
                    "error": "Passcode expired (5-minute limit exceeded). Session terminated.",
                    "kicked": True
                })
                return

            # Check 30-Second Grace Correction Timer Expiry (if active)
            if challenge["grace_expires_at"] and now_ts > challenge["grace_expires_at"]:
                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                self._send_json(400, {
                    "success": False,
                    "error": "30-second error correction timer expired. Session terminated.",
                    "kicked": True
                })
                return

            # Validate Code
            if submitted_code != challenge["code"]:
                challenge["attempts"] += 1
                if challenge["attempts"] >= 2:
                    ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                    self._send_json(403, {
                        "success": False,
                        "error": "Incorrect code on second attempt. Session terminated for security.",
                        "kicked": True
                    })
                    return
                else:
                    # First wrong attempt: start 30-second timer
                    challenge["grace_expires_at"] = now_ts + 30.0
                    self._send_json(400, {
                        "success": False,
                        "error": "Incorrect verification code. You have 30 seconds to correct and re-enter it.",
                        "grace_period_seconds": 30,
                        "attempt": 1,
                        "kicked": False
                    })
                    return

            # CODE IS CORRECT!
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
                            INSERT INTO accounts (username, full_name, email, password_hash, salt, privilege_level, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (p["username"], p["full_name"], p["email"], p["password_hash"], p["salt"], p["privilege_level"], p["status"], p["created_at"]))
                        conn.commit()
                except sqlite3.IntegrityError:
                    ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                    self._send_json(409, {"success": False, "error": "Account already exists.", "kicked": True})
                    return

                ACTIVE_2FA_CHALLENGES.pop(challenge_id, None)
                export_sanitized_accounts_json()

                # Dispatch administrator notification to Rann
                notify_rann_new_signup(
                    full_name=p["full_name"],
                    email=p["email"],
                    username=p["username"],
                    timestamp=p["created_at"],
                    level=1
                )

                self._send_json(201, {
                    "success": True,
                    "message": "Registration verified! Account is pending administrator approval.",
                    "user": {
                        "username": p["username"],
                        "fullName": p["full_name"],
                        "email": p["email"],
                        "privilegeLevel": 1,
                        "status": "PENDING_APPROVAL"
                    }
                })
                return

        # ----------------------------------------------------
        # Authenticated Admin Action Endpoints below
        # ----------------------------------------------------
        if not self._is_admin_authenticated():
            self._send_json(401, {"success": False, "error": "Unauthorized: Administrator access required."})
            return

        if url_path == "/api/accounts/approve":
            user_id = payload.get("id")
            email = payload.get("email")
            new_level = payload.get("privilege_level")

            if not user_id and not email:
                self._send_json(400, {"success": False, "error": "User ID or email is required"})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                if user_id:
                    if new_level is not None:
                        cursor.execute("UPDATE accounts SET status = 'APPROVED', privilege_level = ? WHERE id = ?", (int(new_level), user_id))
                    else:
                        cursor.execute("UPDATE accounts SET status = 'APPROVED' WHERE id = ?", (user_id,))
                else:
                    if new_level is not None:
                        cursor.execute("UPDATE accounts SET status = 'APPROVED', privilege_level = ? WHERE email = ?", (int(new_level), email))
                    else:
                        cursor.execute("UPDATE accounts SET status = 'APPROVED' WHERE email = ?", (email,))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": "User account approved successfully."})
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

            if not user_id or new_level is None:
                self._send_json(400, {"success": False, "error": "User ID and privilege_level are required"})
                return

            try:
                new_level = int(new_level)
                if not (1 <= new_level <= 10):
                    raise ValueError()
            except ValueError:
                self._send_json(400, {"success": False, "error": "privilege_level must be between 1 and 10"})
                return

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE accounts SET privilege_level = ? WHERE id = ?", (new_level, user_id))
                conn.commit()

            export_sanitized_accounts_json()
            self._send_json(200, {"success": True, "message": f"Privilege level updated to {new_level}."})
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
    args = parser.parse_args()

    if args.init_only:
        init_db()
        print("Database initialized successfully.")
    else:
        run_server(args.port)
