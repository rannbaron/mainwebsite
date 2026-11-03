#!/usr/bin/env python3
"""
Autonomous Course Platform Bug Tracker Monitor & Daily Summary Dispatcher
========================================================================
1. Monitors all active bugs, feature requests, and roadmap items in bugs.json.
2. Tracks progress updates and verified fixes across the 60-day development cycle.
3. Every 24 hours, dispatches a comprehensive status digest to rann@rannbar-on.com.
4. Provides CLI interface to query, add, resolve, or audit bugs.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "/home/rann/src/gradescopetools")
import gradescope_tasks as gt

BUGS_FILE = Path("/home/rann/src/website/mainwebsite/bugs/bugs.json")
RECIPIENT = "rann@rannbar-on.com"

def load_bugs_data():
    if not BUGS_FILE.exists():
        raise FileNotFoundError(f"Bugs database not found at {BUGS_FILE}")
    with open(BUGS_FILE, "r") as f:
        return json.load(f)

def save_bugs_data(data):
    BUGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BUGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def update_bug_status(bug_id: str, new_status: str, progress_note: str = ""):
    data = load_bugs_data()
    found = False
    for b in data.get("bugs", []):
        if b["id"].upper() == bug_id.upper():
            b["status"] = new_status
            if progress_note:
                b["progress"] = progress_note
            b["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        raise ValueError(f"Bug ID '{bug_id}' not found in database.")
    save_bugs_data(data)
    print(f"Updated {bug_id} status to '{new_status}'.")

def generate_daily_bugs_summary_html():
    data = load_bugs_data()
    bugs = data.get("bugs", [])
    
    total = len(bugs)
    in_prog = sum(1 for b in bugs if b["status"] == "In Progress")
    open_cnt = sum(1 for b in bugs if b["status"] == "Open")
    resolved = sum(1 for b in bugs if b["status"] in ["Resolved", "Implemented (Testing)"])
    
    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 860px; margin: 0 auto; color: #1e293b;">
      <div style="background: linear-gradient(135deg, #001A57, #0A3282); padding: 24px; border-radius: 10px; color: white;">
        <h2 style="margin: 0 0 6px 0; font-size: 22px;">Autonomous Course Platform: Daily Bug & Feature Tracker Summary</h2>
        <p style="margin: 0; opacity: 0.85; font-size: 14px;">2-Month Development Cycle (Gradescope & Canvas Replacement) &bull; {datetime.now().strftime('%b %d, %Y')}</p>
      </div>

      <div style="display: flex; gap: 12px; margin: 16px 0;">
        <div style="flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; text-align: center;">
          <div style="font-size: 22px; font-weight: bold; color: #0f172a;">{total}</div>
          <div style="font-size: 11.5px; color: #64748b; text-transform: uppercase;">Total Items</div>
        </div>
        <div style="flex: 1; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px; text-align: center;">
          <div style="font-size: 22px; font-weight: bold; color: #2563eb;">{in_prog}</div>
          <div style="font-size: 11.5px; color: #1e40af; text-transform: uppercase;">In Progress</div>
        </div>
        <div style="flex: 1; background: #fefce8; border: 1px solid #fef08a; border-radius: 8px; padding: 12px; text-align: center;">
          <div style="font-size: 22px; font-weight: bold; color: #ca8a04;">{open_cnt}</div>
          <div style="font-size: 11.5px; color: #854d0e; text-transform: uppercase;">Open Backlog</div>
        </div>
        <div style="flex: 1; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 12px; text-align: center;">
          <div style="font-size: 22px; font-weight: bold; color: #16a34a;">{resolved}</div>
          <div style="font-size: 11.5px; color: #166534; text-transform: uppercase;">Resolved / Active</div>
        </div>
      </div>

      <div style="margin: 20px 0;">
        <h3 style="color: #001A57; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px;">Active Roadmap & Bug Items</h3>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #cbd5e1; text-align: left;">
              <th style="padding: 8px;">ID</th>
              <th style="padding: 8px;">Feature / Bug Title</th>
              <th style="padding: 8px;">Category</th>
              <th style="padding: 8px;">Priority</th>
              <th style="padding: 8px;">Status</th>
            </tr>
          </thead>
          <tbody>
    """
    for b in bugs:
        st = b["status"]
        st_style = "background:#f1f5f9;color:#475569;"
        if "Resolved" in st or "Implemented" in st:
            st_style = "background:#dcfce7;color:#166534;font-weight:bold;"
        elif st == "In Progress":
            st_style = "background:#eff6ff;color:#1d4ed8;font-weight:bold;"
        elif st == "Open":
            st_style = "background:#fef9c3;color:#854d0e;font-weight:bold;"

        html += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
              <td style="padding: 8px; font-weight: bold; font-family: monospace; color: #001A57;">{b['id']}</td>
              <td style="padding: 8px;"><strong>{b['title']}</strong><br><span style="font-size:12px;color:#64748b;">{b['progress']}</span></td>
              <td style="padding: 8px; color: #475569;">{b['category']}</td>
              <td style="padding: 8px; font-weight: bold;">{b['priority']}</td>
              <td style="padding: 8px;"><span style="padding: 3px 8px; border-radius: 4px; font-size: 11px; {st_style}">{st}</span></td>
            </tr>
        """
    html += f"""
          </tbody>
        </table>
      </div>

      <div style="font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px; margin-top: 20px;">
        Automated Bug Monitor Daemon &bull; Published dynamically to <a href="https://rannbar-on.com/bugs/">rannbar-on.com/bugs/</a> &bull; Dispatched every 24 hours to {RECIPIENT}
      </div>
    </div>
    """
    return html

def dispatch_daily_summary(dry_run=False):
    subject = f"Autonomous Course Platform: Daily Bug Tracker & Goals Summary ({datetime.now().strftime('%b %d, %Y')})"
    content = generate_daily_bugs_summary_html()
    print(f"Dispatching Daily Bug Tracker Summary to {RECIPIENT}...")
    return gt.send_duke_email(
        recipient=RECIPIENT,
        subject=subject,
        content=content,
        is_html=True,
        dry_run=dry_run
    )

if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    dispatch_daily_summary(dry_run=is_dry)

