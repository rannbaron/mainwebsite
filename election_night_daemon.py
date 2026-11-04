#!/usr/bin/env python3
"""
Election Night Continuous Supervisor Daemon
===========================================
- Runs continuously overnight ("do not suspend tonight at all")
- Refreshes all live pages and feeds every 30 seconds
- Staged social post linking to socials feed every 30 minutes
"""

import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/rann/src/website/mainwebsite")
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, "/home/rann/src/gradescopetools")

import ncpoliticssocials_updater as updater
import generate_agents_dashboard as agents_gen

def tick_30s():
    """Runs high-frequency 30-second tasks."""
    try:
        # 1. Update socials continuous feed
        updater.save_feed_and_pages()
    except Exception as e:
        print(f"[Daemon 30s] Error in updater: {e}", file=sys.stderr)

    try:
        # 2. Update agents DAG dashboard
        agents_gen.generate_dashboard()
    except Exception as e:
        print(f"[Daemon 30s] Error in agents gen: {e}", file=sys.stderr)

def tick_30m():
    """Runs 30-minute social post staging task."""
    now_str = datetime.now().strftime("%I:%M %p EST")
    print(f"[Daemon 30m] Triggering 30-min social pulse at {now_str}...")
    try:
        updater.post_to_feed(
            title=f"🚨 DECISION DESK PULSE: Real-Time Dials & Supermajority Watch ({now_str})",
            content=(
                f"⚡ LIVE AT {now_str}:\n"
                f"• US Senate: Roy Cooper (D) maintains projected +9.5% margin advantage [Safe D].\n"
                f"• NC House Supermajority: Modeled at 96.2% confidence BROKEN (54.2 Exp D seats).\n"
                f"• NC Senate Supermajority: 65.7% probability broken (21.1 Exp D seats).\n\n"
                f"Explore full interactive 3-mode Bayesian needles and precinct swings:\n"
                f"🎯 Needle: https://rannbar-on.com/needle\n"
                f"📱 Feed: https://rannbar-on.com/ncpoliticssocials\n"
                f"⚡ Dual View: https://rannbar-on.com/both\n\n"
                f"#NCpol #NCSen #Elections2026 #DecisionDesk #SwingState"
            ),
            category="📢 Our Posts",
            metrics=[
                {"label": "Senate Proj", "val": "Cooper +9.5%", "color": "#3b82f6"},
                {"label": "NC House", "val": "54.2 D (Broken)", "color": "#10b981"},
                {"label": "NC Senate", "val": "21.1 D (Lean Brk)", "color": "#f59e0b"}
            ],
            action_link="https://rannbar-on.com/needle",
            action_text="Live Needle Dials ➡️"
        )
    except Exception as e:
        print(f"[Daemon 30m] Error posting 30m social update: {e}", file=sys.stderr)

def main():
    print(f"[Daemon] Election Night Daemon started at {datetime.now().isoformat()} - running continuously overnight.")
    last_30m_time = time.time()

    while True:
        tick_30s()
        now = time.time()
        if now - last_30m_time >= 1800: # 30 minutes
            tick_30m()
            last_30m_time = now
        time.sleep(30)

if __name__ == "__main__":
    main()
