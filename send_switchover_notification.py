#!/usr/bin/env python3
"""
NC Student Voting Platform - Switchover Email Notification Dispatcher
Sends detailed email alerts to rann@rannbar-on.com upon successful completion
or failure of the automated Election Day switchover workflow.
"""

import os
import sys
import argparse
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid, formataddr

DEFAULT_PRIMARY_RECIPIENT = "rann@rannbar-on.com"
DEFAULT_CC_RECIPIENT = "baronrann@gmail.com"

def send_notification(status, recipient, error_text="", commit_sha="", run_id="", cc_recipient=None):
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    if smtp_pass:
        smtp_pass = smtp_pass.replace(" ", "").strip()

    if not smtp_user or not smtp_pass:
        print(f"Warning: SMTP_USER or SMTP_PASSWORD not set. Cannot send email notification to {recipient}.")
        return False

    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p EDT")
    repo = os.getenv("GITHUB_REPOSITORY", "rannbaron/mainwebsite")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else f"https://github.com/{repo}/actions"
    commit_url = f"https://github.com/{repo}/commit/{commit_sha}" if commit_sha else f"https://github.com/{repo}/commits/main"

    is_success = (status.lower() == "success")

    if is_success:
        subject = "✅ [SUCCESS] NC Student Voting Platform Switched to Election Day Mode"
        plain_body = f"""NC Student Voting Platform - Election Day Switchover Complete
====================================================================
Timestamp: {now_str}
Status: SUCCESS

Early Voting has concluded across North Carolina. The student voting platform has successfully transitioned to Election Day mode.

Key Updates Applied:
• All 110 NC higher-ed institution guides have been updated with Election Day polling places and precinct lookups.
• The Master Directory (/campuses) now displays Election Day information and precinct finders.
• The dynamic QR portal (/vote) has been updated with GPS-based nearest Election Day precinct detection.
• Accepted student photo ID compliance and nonpartisan local candidate guides remain active.

GitHub Actions Run: {run_url}
Commit: {commit_url}

Live Verification Links:
• Master Portal: https://rannbar-on.com/vote
• 110 Campus Directory: https://rannbar-on.com/campuses
• Duke Campus Guide: https://rannbar-on.com/dukevote
• UNC Campus Guide: https://rannbar-on.com/uncvote
• NC State Campus Guide: https://rannbar-on.com/ncsuvote
• NCCU Campus Guide: https://rannbar-on.com/nccuvote
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b; padding: 24px; margin: 0; }}
    .container {{ max-width: 650px; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .badge-success {{ background-color: #dcfce7; color: #15803d; }}
    h1 {{ font-size: 22px; font-weight: 800; color: #0f172a; margin-top: 16px; margin-bottom: 8px; }}
    p {{ font-size: 15px; line-height: 1.6; color: #334155; margin: 8px 0; }}
    .card {{ background-color: #f1f5f9; border-left: 4px solid #10b981; padding: 16px; border-radius: 6px; margin: 20px 0; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: #ffffff !important; padding: 10px 20px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 14px; margin-top: 12px; }}
    .btn:hover {{ background-color: #1d4ed8; }}
    ul {{ padding-left: 20px; font-size: 14px; color: #334155; line-height: 1.6; }}
    .footer {{ margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <span class="badge badge-success">✓ Switchover Complete</span>
    <h1>NC Student Voting Platform is Live for Election Day</h1>
    <p>Early Voting has officially concluded across North Carolina. The platform has automatically transitioned all campus guides to <b>Election Day polling locations and assigned precincts</b>.</p>
    
    <div class="card">
      <b>Execution Details:</b><br>
      • <b>Completed:</b> {now_str}<br>
      • <b>Institution Guides:</b> 110 active NC colleges & universities regenerated<br>
      • <b>Features Deployed:</b> Assigned precinct lookups, GPS nearest-precinct routing, Student ID memo verification
    </div>

    <h3>Verified Live Links:</h3>
    <ul>
      <li><a href="https://rannbar-on.com/vote" style="color: #2563eb; font-weight: 600;">Main QR Code Portal (/vote)</a></li>
      <li><a href="https://rannbar-on.com/campuses" style="color: #2563eb; font-weight: 600;">110 Campuses Master Directory (/campuses)</a></li>
      <li><a href="https://rannbar-on.com/dukevote" style="color: #2563eb;">Duke University Guide (/dukevote)</a></li>
      <li><a href="https://rannbar-on.com/uncvote" style="color: #2563eb;">UNC Chapel Hill Guide (/uncvote)</a></li>
      <li><a href="https://rannbar-on.com/ncsuvote" style="color: #2563eb;">NC State Guide (/ncsuvote)</a></li>
      <li><a href="https://rannbar-on.com/nccuvote" style="color: #2563eb;">NCCU Guide (/nccuvote)</a></li>
    </ul>

    <p style="margin-top: 20px;">
      <a href="{run_url}" class="btn">View GitHub Actions Run &rarr;</a>
    </p>

    <div class="footer">
      Automated dispatch from GitHub Actions • Repository: <a href="https://github.com/{repo}">{repo}</a>
    </div>
  </div>
</body>
</html>
"""
    else:
        subject = "🚨 [ALERT] NC Student Voting Platform: Election Day Switchover Failed"
        plain_body = f"""CRITICAL ALERT: NC Student Voting Platform Switchover Encountered Errors
====================================================================
Timestamp: {now_str}
Status: FAILED

The automated switchover from Early Voting to Election Day mode encountered an error.

Error Summary / Trace:
--------------------------------------------------------------------
{error_text or 'No specific error text captured. Check GitHub Action run logs.'}
--------------------------------------------------------------------

GitHub Actions Run: {run_url}

Recommended Action:
1. Inspect the GitHub Actions logs at: {run_url}
2. Run manual switchover locally if needed:
   cd /home/rann/src/website/mainwebsite
   python3 generate_election_day_pages.py
   git add -A && git commit -m "Manual switch to Election Day" && git push origin main
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #fef2f2; color: #1e293b; padding: 24px; margin: 0; }}
    .container {{ max-width: 650px; background: #ffffff; border-radius: 12px; border: 1px solid #fecaca; padding: 32px; margin: 0 auto; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .badge-error {{ background-color: #fee2e2; color: #b91c1c; }}
    h1 {{ font-size: 22px; font-weight: 800; color: #991b1b; margin-top: 16px; margin-bottom: 8px; }}
    p {{ font-size: 15px; line-height: 1.6; color: #334155; margin: 8px 0; }}
    pre {{ background-color: #0f172a; color: #f8fafc; padding: 16px; border-radius: 8px; font-size: 12px; overflow-x: auto; white-space: pre-wrap; }}
    .btn {{ display: inline-block; background-color: #dc2626; color: #ffffff !important; padding: 10px 20px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 14px; margin-top: 12px; }}
    .footer {{ margin-top: 28px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b; }}
  </style>
</head>
<body>
  <div class="container">
    <span class="badge badge-error">✕ Switchover Failed</span>
    <h1>Switchover Encountered an Error</h1>
    <p>The automated switchover to Election Day voting info failed at <b>{now_str}</b>.</p>
    
    <h3>Error Trace:</h3>
    <pre>{error_text or 'No specific stderr captured. Check run details in GitHub Actions.'}</pre>

    <p style="margin-top: 20px;">
      <a href="{run_url}" class="btn">Inspect GitHub Action Run &rarr;</a>
    </p>

    <h3>Manual Fallback:</h3>
    <pre>cd ~/src/website/mainwebsite
python3 generate_election_day_pages.py
git add -A && git commit -m "Manual switch to Election Day" && git push origin main</pre>

    <div class="footer">
      Automated alert from GitHub Actions • Repository: <a href="https://github.com/{repo}">{repo}</a>
    </div>
  </div>
</body>
</html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr(("NC Student Voting Platform", smtp_user))
    msg["To"] = recipient
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=smtp_user.split('@')[-1] if '@' in smtp_user else "rannbar-on.com")

    all_recipients = [recipient]
    if cc_recipient and cc_recipient.lower() != recipient.lower():
        msg["Cc"] = cc_recipient
        all_recipients.append(cc_recipient)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        print(f"Connecting to {smtp_server}:{smtp_port} via STARTTLS...")
        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, all_recipients, msg.as_string())
        print(f"Notification email successfully sent to {', '.join(all_recipients)}!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Send Election Day switchover email notification")
    parser.add_argument("--status", choices=["success", "failure"], default="success", help="Switchover status")
    parser.add_argument("--recipient", default=DEFAULT_PRIMARY_RECIPIENT, help="Primary recipient email")
    parser.add_argument("--cc", default=DEFAULT_CC_RECIPIENT, help="CC recipient email")
    parser.add_argument("--error-log", default=None, help="Path to error log file if failure")
    parser.add_argument("--commit", default="", help="Git commit SHA")
    parser.add_argument("--run-id", default="", help="GitHub Actions run ID")

    args = parser.parse_args()

    error_text = ""
    if args.error_log and os.path.exists(args.error_log):
        try:
            with open(args.error_log, "r", encoding="utf-8", errors="ignore") as f:
                error_text = f.read()
        except Exception:
            pass

    success = send_notification(
        status=args.status,
        recipient=args.recipient,
        error_text=error_text,
        commit_sha=args.commit,
        run_id=args.run_id,
        cc_recipient=args.cc
    )

    if not success and args.status == "success":
        # Don't fail the whole workflow just because notification had an issue, but log it
        print("Notice: Notification email could not be delivered.")

if __name__ == "__main__":
    main()
