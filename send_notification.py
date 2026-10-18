#!/usr/bin/env python3
"""
Email Notification Dispatcher for NC Early Voting Daily Updates.
Sends execution status and detailed logs to baronrann@gmail.com.
"""

import os
import sys
import argparse
import subprocess
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from email.utils import formatdate, make_msgid, formataddr

DEFAULT_RECIPIENT = "baronrann@gmail.com"

def load_env_file():
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_file):
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        os.environ[k.strip().replace('export ', '')] = v.strip().strip('"').strip("'")
        except Exception as e:
            print(f"Warning: Failed to load .env: {e}")

def send_email(subject, body, recipient=DEFAULT_RECIPIENT):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to send email notification to {recipient}...")
    load_env_file()

    smtp_server = os.getenv("SMTP_SERVER")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", 587 if (smtp_pass or (smtp_server and "gmail" in smtp_server)) else 25))

    # Priority 1: External or Campus SMTP (if configured in .env or environment)
    if smtp_server:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Using configured SMTP server: {smtp_server}:{smtp_port}...")
        try:
            msg = MIMEMultipart()
            sender_email = smtp_user if smtp_user else f"rann@{os.uname().nodename}"
            msg['From'] = formataddr(("NC Early Voting Updates", sender_email))
            msg['To'] = recipient
            msg['Subject'] = subject
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain="elections.map")
            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                if smtp_port == 587 or smtp_pass:
                    server.starttls()

            with server:
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.sendmail(sender_email, [recipient], msg.as_string())

            print(f"[{datetime.now().strftime('%H:%M:%S')}] Notification successfully sent via SMTP ({smtp_server}:{smtp_port}) to {recipient}!")
            return True
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] SMTP delivery failed ({smtp_server}:{smtp_port}): {e}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Falling back to local mail tools...")

    # Priority 2: Try /usr/sbin/sendmail or /usr/lib/sendmail
    sendmail_bins = ["/usr/sbin/sendmail", "/usr/lib/sendmail"]
    for s_bin in sendmail_bins:
        if os.path.exists(s_bin) and os.access(s_bin, os.X_OK):
            try:
                msg = MIMEMultipart()
                msg['From'] = formataddr(("NC Early Voting Robot", f"rann@{os.uname().nodename}"))
                msg['To'] = recipient
                msg['Subject'] = subject
                msg['Date'] = formatdate(localtime=True)
                msg['Message-ID'] = make_msgid(domain=os.uname().nodename)
                msg.attach(MIMEText(body, 'plain', 'utf-8'))

                p = subprocess.Popen([s_bin, "-t", "-oi"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate(input=msg.as_bytes(), timeout=4)
                if p.returncode == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Notification submitted to local spool via {s_bin}")
                    return True
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {s_bin} returned code {p.returncode}: {stderr.decode(errors='ignore')}")
            except subprocess.TimeoutExpired:
                p.kill()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {s_bin} timed out after 4s.")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {s_bin} error: {e}")

    # Priority 3: Try /usr/bin/mail or mailx
    mail_bins = ["/usr/bin/mail", "/usr/bin/mailx"]
    for m_bin in mail_bins:
        if os.path.exists(m_bin) and os.access(m_bin, os.X_OK):
            try:
                p = subprocess.Popen([m_bin, "-s", subject, recipient], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = p.communicate(input=body.encode('utf-8'), timeout=4)
                if p.returncode == 0:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Notification submitted via {m_bin}")
                    return True
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {m_bin} returned code {p.returncode}: {stderr.decode(errors='ignore')}")
            except subprocess.TimeoutExpired:
                p.kill()
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {m_bin} timed out after 4s.")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {m_bin} error: {e}")

    # Priority 4: Try local SMTP on localhost:25
    try:
        msg = MIMEMultipart()
        msg['From'] = f"rann@{os.uname().nodename}"
        msg['To'] = recipient
        msg['Subject'] = subject
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=os.uname().nodename)
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        with smtplib.SMTP('localhost', 25, timeout=5) as server:
            server.sendmail(msg['From'], [recipient], msg.as_string())
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Notification sent via local SMTP (localhost:25)")
            return True
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Localhost SMTP port 25 error: {e}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Could not dispatch email via any method. Ensure .env has valid SMTP credentials.")
    return False

def main():
    parser = argparse.ArgumentParser(description="Send Daily Update Notification Email")
    parser.add_argument("--status", choices=["SUCCESS", "FAILURE", "NO_CHANGE"], default="SUCCESS")
    parser.add_argument("--recipient", default=DEFAULT_RECIPIENT)
    parser.add_argument("--log-file", help="Path to log file to attach/include")
    parser.add_argument("--summary", default="", help="Summary text")
    parser.add_argument("--ev-day", type=str, default="", help="EV Day number")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S EDT")
    today_date = datetime.now().strftime("%Y-%m-%d")

    if args.status == "SUCCESS":
        subject = f"[SUCCESS] NC Early Voting Map Updated: Day {args.ev_day or 'Latest'} ({today_date})"
    elif args.status == "NO_CHANGE":
        subject = f"[INFO] NC Early Voting Check: S3 Unchanged ({today_date})"
    else:
        subject = f"[ALERT] NC Early Voting Map Update FAILED ({today_date})"

    # Read log content if provided
    log_content = ""
    if args.log_file and os.path.exists(args.log_file):
        try:
            with open(args.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()
        except Exception as e:
            log_content = f"(Could not read log file: {e})"

    # Compose body
    body_lines = [
        f"NC Early Voting Automatic Daily Update Notification",
        f"=" * 60,
        f"Status:       {args.status}",
        f"Timestamp:    {date_str}",
        f"Host:         {os.uname().nodename}",
        f"Recipient:    {args.recipient}",
        f"Target Path:  /home/grad/rann/public_html/interactive_map.html",
        f"=" * 60,
    ]

    if args.summary:
        body_lines.append("")
        body_lines.append("SUMMARY:")
        body_lines.append(args.summary)
        body_lines.append("")

    if log_content:
        body_lines.append("DETAILED EXECUTION LOG:")
        body_lines.append("-" * 60)
        body_lines.append(log_content)
        body_lines.append("-" * 60)

    full_body = "\n".join(body_lines)
    send_email(subject, full_body, args.recipient)

if __name__ == "__main__":
    main()

