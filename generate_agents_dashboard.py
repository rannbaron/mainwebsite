#!/usr/bin/env python3
"""
Agent Command Center & Task Dependency Graph Generator: rannbar-on.com/agents
=============================================================================
Generates a fully private dashboard with:
1. Interactive Visual Task Dependency Graph (DAG) with Bernstein hazard analysis
2. Complete Agent Registry with default summaries and click-to-expand details
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/rann/src/website/mainwebsite")
AGENTS_DIR = BASE_DIR / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = AGENTS_DIR / "index.html"
ROOT_PATH = BASE_DIR / "agents.html"
DATA_PATH = AGENTS_DIR / "agents_data.json"

TASK_DAG_REGISTRY = [
    {
        "id": "T1_TURNOUT",
        "title": "Ingest County Turnout",
        "agent": "Agent-21ce25 (Worker)",
        "agent_type": "Parallel Worker",
        "tier": 1,
        "priority": 8,
        "status": "SUCCEEDED",
        "status_color": "#10b981",
        "deps": [],
        "inputs": ["NCSBE S3 absentee_county_20261103.zip"],
        "outputs": ["/tmp/county_turnout.json"],
        "hazard": "Root Independent (Spawned in Parallel)"
    },
    {
        "id": "T2_POLLS",
        "title": "Synthesize Statewide Polls",
        "agent": "Agent-0b5013 (Worker)",
        "agent_type": "Parallel Worker",
        "tier": 1,
        "priority": 8,
        "status": "SUCCEEDED",
        "status_color": "#10b981",
        "deps": [],
        "inputs": ["ECU Poll", "High Point / YouGov", "Elon Poll"],
        "outputs": ["/tmp/poll_synth.json"],
        "hazard": "Root Independent (Spawned in Parallel)"
    },
    {
        "id": "T3_BASELINES",
        "title": "Compute County Swing Baselines",
        "agent": "Agent-84da88 (Affinity)",
        "agent_type": "Affinity Chained",
        "tier": 2,
        "priority": 7,
        "status": "SUCCEEDED",
        "status_color": "#10b981",
        "deps": ["T1_TURNOUT"],
        "inputs": ["/tmp/county_turnout.json", "2022/2018 baselines"],
        "outputs": ["/tmp/baselines.json"],
        "hazard": "RAW (Read-After-Write) on /tmp/county_turnout.json -> Affinity Forwarded"
    },
    {
        "id": "T4_NEEDLE",
        "title": "Run Bayesian Needle Aggregator",
        "agent": "Agent-6c81b3 (Synchronized)",
        "agent_type": "Synchronized Frontier",
        "tier": 2,
        "priority": 9,
        "status": "SUCCEEDED",
        "status_color": "#10b981",
        "deps": ["T2_POLLS", "T3_BASELINES"],
        "inputs": ["/tmp/poll_synth.json", "/tmp/baselines.json"],
        "outputs": ["needle/needle_data.json"],
        "hazard": "Multi-parent barrier synchronization across parallel pipelines"
    },
    {
        "id": "T5_CALLER",
        "title": "Election Night Race Caller",
        "agent": "election-specialist",
        "agent_type": "Domain Specialist",
        "tier": 3,
        "priority": 9,
        "status": "ACTIVE",
        "status_color": "#10b981",
        "deps": ["T4_NEEDLE"],
        "inputs": ["needle/needle_data.json"],
        "outputs": ["needle/called_races.json"],
        "hazard": "RAW on needle_data.json -> 95% Bayesian Confidence trigger"
    },
    {
        "id": "T6_FEED",
        "title": "Continuous Feed Live Streamer",
        "agent": "continuous-feed-streamer",
        "agent_type": "Web Engine",
        "tier": 3,
        "priority": 8,
        "status": "ACTIVE",
        "status_color": "#10b981",
        "deps": ["T4_NEEDLE", "T5_CALLER"],
        "inputs": ["needle/called_races.json", "nc_map_base.json"],
        "outputs": ["ncpoliticssocials/feed.json"],
        "hazard": "Real-time auto-publish to rannbar-on.com/ncpoliticssocials"
    },
    {
        "id": "T7_SOCIALS",
        "title": "30-Min Social Pulse Daemon",
        "agent": "social-pulse-agent",
        "agent_type": "Autonomous Daemon",
        "tier": 4,
        "priority": 8,
        "status": "ACTIVE",
        "status_color": "#10b981",
        "deps": ["T6_FEED"],
        "inputs": ["ncpoliticssocials/feed.json"],
        "outputs": ["private_social/staged_social_drafts.json"],
        "hazard": "Bio link priority + 1-click approval emails to Rann every 30m"
    },
    {
        "id": "T8_STUDENTS",
        "title": "Student Morning Briefing Queue",
        "agent": "student-ta-comms-specialist",
        "agent_type": "Domain Specialist",
        "tier": 4,
        "priority": 7,
        "status": "QUEUED",
        "status_color": "#f59e0b",
        "deps": ["T5_CALLER"],
        "inputs": ["needle/called_races.json", "rosters/*.csv"],
        "outputs": ["sample_student_email.html (Awaiting Approval)"],
        "hazard": "Guarded by Duke Election Firewall; scheduled for tomorrow 10:10 AM"
    }
]

AGENTS_REGISTRY = [
    {
        "id": "election_specialist",
        "name": "Election Specialist Agent",
        "category": "Domain Specialist",
        "category_color": "#3b82f6",
        "status": "RUNNING",
        "status_color": "#10b981",
        "status_label": "ACTIVE / PROCESSING",
        "priority": 9,
        "priority_label": "P9 (High Urgency)",
        "summary": "Real-time ballot ingestion across all 100 NC counties, Bayesian 3-mode needle models, and decision desk race caller.",
        "details": {
            "current_task": "Monitoring late precinct reporting, suburban independent crossover, and Senate/House margin shifts.",
            "target_scripts": [
                "/home/rann/src/website/mainwebsite/update_server.py",
                "/home/rann/src/website/mainwebsite/election_night_race_caller.py",
                "/home/rann/src/website/mainwebsite/generate_needle_page.py",
                "/home/rann/src/website/mainwebsite/vote_forecast.py"
            ],
            "active_resources": [
                "nc_map_base.json (2.83M+ voter records)",
                "needle/needle_data.json (Bayesian margin parameters)",
                "needle/called_races.json (Certified decision desk calls)"
            ],
            "key_metrics": {
                "Processed Ballots": "2,828,131",
                "US Senate Margin": "Cooper +9.46% (99.5% win prob)",
                "NC House Supermajority": "96.2% Broken (54.2 D seats)",
                "Flipped Counties": "13 Projected Flips"
            },
            "guardrails": "Protected against non-current assignments. Enforces Duke Election Firewall across all outbound notifications.",
            "execution_context": "Multiprocessing pipeline coordinated by AgentDAG with SQLite WAL state synchronization."
        }
    },
    {
        "id": "social_pulse_scheduler",
        "name": "Social Pulse Broadcast Daemon",
        "category": "Autonomous Daemon",
        "category_color": "#8b5cf6",
        "status": "RUNNING",
        "status_color": "#10b981",
        "status_label": "ACTIVE / 30-MIN LOOP",
        "priority": 8,
        "priority_label": "P8 (High Priority)",
        "summary": "Generates 30-minute social media broadcast cycles for X/Twitter, Threads, Instagram, and Bluesky linking directly to rannbar-on.com/ncpoliticssocials.",
        "details": {
            "current_task": "Maintains bio links pointing to rannbar-on.com/ncpoliticssocials; auto-publishes to public continuous feed; stages external drafts and dispatches 1-click approval emails to Rann.",
            "target_scripts": [
                "/home/rann/src/website/mainwebsite/social_pulse_scheduler.py",
                "/home/rann/src/website/mainwebsite/social_media_dispatcher.py"
            ],
            "active_resources": [
                "private_social/staged_social_drafts.json",
                "private_social/index.html",
                "ncpoliticssocials/feed.json"
            ],
            "key_metrics": {
                "Cycle Interval": "30 Minutes",
                "Bio Link Target": "https://rannbar-on.com/ncpoliticssocials",
                "Approval Mechanism": "1-Click Email Action to Rann",
                "Supported Channels": "Twitter, Threads, Instagram, Bluesky"
            },
            "guardrails": "Never publishes to external social APIs without Rann's manual 1-click approval. Public feed updates immediately without approval.",
            "execution_context": "Stand-alone background daemon with automated timer and Microsoft Graph email dispatcher."
        }
    },
    {
        "id": "continuous_feed_streamer",
        "name": "Continuous Feed Streamer",
        "category": "Web Engine",
        "category_color": "#0284c7",
        "status": "RUNNING",
        "status_color": "#10b981",
        "status_label": "ONLINE / AUTO-SYNC",
        "priority": 8,
        "priority_label": "P8 (Operational)",
        "summary": "Maintains the phone-oriented continuous feed at rannbar-on.com/ncpoliticssocials with sub-25s auto-polling and audio alert chimes.",
        "details": {
            "current_task": "Ingesting Decision Desk post drafts, live needle movements, county turnout alerts, and curated NC news into a phone-optimized stream.",
            "target_scripts": [
                "/home/rann/src/website/mainwebsite/ncpoliticssocials_updater.py"
            ],
            "active_resources": [
                "ncpoliticssocials/feed.json",
                "ncpoliticssocials/index.html",
                "ncpoliticssocials.html"
            ],
            "key_metrics": {
                "Active Feed Items": "12 Rich Timeline Cards",
                "Polling Frequency": "25 Seconds (Client-side JSON poll)",
                "Layout Format": "Mobile Phone Shell (480px, Safe-Area Inset)",
                "Actions": "1-Tap Copy, Native Web Share, Gauge Mini-Dials"
            },
            "guardrails": "Public page; bypasses approval requirements per user directive. Static initial state embedded in HTML for zero-latency load.",
            "execution_context": "Integrated API callable by any script via ncpoliticssocials_updater.post_to_feed()."
        }
    },
    {
        "id": "agent_dag_orchestrator",
        "name": "Agent DAG Parallel Orchestrator",
        "category": "Core Infrastructure",
        "category_color": "#10b981",
        "status": "RUNNING",
        "status_color": "#10b981",
        "status_label": "ACTIVE / DISPATCHER ONLINE",
        "priority": 10,
        "priority_label": "P10 (Max / Architecture)",
        "summary": "Preemptive parallel multi-agent scheduler that infers Bernstein dependencies, spawns worker agents, and affinity-routes dependent jobs.",
        "details": {
            "current_task": "Evaluating task dependency graph; managing parallel worker allocations and local pipeline forwarding.",
            "target_scripts": [
                "/home/rann/src/agent_orchestrator/agent_dag.py",
                "/home/rann/src/agent_orchestrator/resource_analyzer.py",
                "/home/rann/src/agent_orchestrator/dag_models.py"
            ],
            "active_resources": [
                "/home/rann/src/agent_orchestrator/dag_state.db (SQLite WAL Mode)",
                "/home/rann/bin/agent-dag (Global CLI executable)"
            ],
            "key_metrics": {
                "DAG Resolution Latency": "Sub-100ms Scheduler Tick",
                "Verification Speed": "0.32s (4-Job Parallel Chained Suite)",
                "Hazard Inferences": "RAW (Read-After-Write), WAR, WAW",
                "Affinity Invariant": "J_dep forwarded directly to Agent(J_anc)"
            },
            "guardrails": "Tarjan / Kahn cycle detection prevents recursive execution loops. Process isolation for worker threads.",
            "execution_context": "Native Linux daemon with Python 3.14 multithreading and subprocess isolation."
        }
    },
    {
        "id": "student_ta_comms_specialist",
        "name": "Student & TA Communications Specialist",
        "category": "Domain Specialist",
        "category_color": "#f59e0b",
        "status": "QUEUED",
        "status_color": "#f59e0b",
        "status_label": "QUEUED / AWAITING APPROVAL",
        "priority": 7,
        "priority_label": "P7 (Elevated Priority)",
        "summary": "Prepares student morning election briefings, TA meeting notices, bug tracker guides, and courseware correspondence.",
        "details": {
            "current_task": "Awaiting Rann's 1-click email authorization for the tomorrow 10:10 AM Math 105L student election briefing and rannbar-on.com/ncpoliticssocials announcement.",
            "target_scripts": [
                "/home/rann/src/generate_student_election_sample_email.py",
                "/home/rann/src/send_feed_announcement_approval_email.py",
                "/home/rann/src/gradescopetools/stage_stakeholder_dispatch.py"
            ],
            "active_resources": [
                "Math 105L Section 001 & 002 rosters",
                "Math 105L TA Staff List (8 teaching assistants)"
            ],
            "key_metrics": {
                "Enrolled Students": "~120 active students",
                "Teaching Assistants": "8 graduate & undergraduate TAs",
                "Scheduled Delivery": "Tomorrow 10:10 AM EST (10m pre-class)",
                "Approval State": "Pending Rann's 1-Click Action"
            },
            "guardrails": "Strict Duke Election Firewall suppresses partisan messages to @duke.edu. Enforces dropped students policy (Nwoko, Payne, Kumi).",
            "execution_context": "Microsoft Graph OAuth2 integration via cached Duke credentials."
        }
    },
    {
        "id": "gradescope_tools_specialist",
        "name": "Gradescope Tools Specialist",
        "category": "Domain Specialist",
        "category_color": "#065f46",
        "status": "STANDBY",
        "status_color": "#64748b",
        "status_label": "IDLE / STANDBY",
        "priority": 7,
        "priority_label": "P7 (Standard)",
        "summary": "Maintains Math 105L/106L assignment rubrics, submission windows, quiz/lab retake management, and deadline extension enforcement.",
        "details": {
            "current_task": "Standby mode. All non-current extensions locked. Ready for next scheduled quiz/lab download cycle.",
            "target_scripts": [
                "/home/rann/src/gradescopetools/gradescope_tasks.py",
                "/home/rann/src/gradescopetools/manage_nwoko_quiz_windows.py",
                "/home/rann/src/gradescopetools/incapacitation_manager.py"
            ],
            "active_resources": [
                ".gradescope_auth.json (Session authentication)",
                "coursepack105L106L/ grading databases"
            ],
            "key_metrics": {
                "Excessive NP Limits": "Worksheets >8, Quizzes >4, Labs >2",
                "Quiz Retake Download Guard": "1 week + 1 hour delay enforced",
                "Late Retake Policy": "Dec 4, 2027 1-year offset for re-retakes"
            },
            "guardrails": "NEVER modify old assignments or grant unapproved extensions. Rann email notification mandatory on any assignment creation/update.",
            "execution_context": "Automated headless Python requests & BS4 parser with persistent auth cookie store."
        }
    },
    {
        "id": "travel_research_specialist",
        "name": "Travel & Flight Research Specialist",
        "category": "Subagent",
        "category_color": "#ec4899",
        "status": "COMPLETED",
        "status_color": "#60a5fa",
        "status_label": "COMPLETED / REPORT DELIVERED",
        "priority": 5,
        "priority_label": "P5 (Task Complete)",
        "summary": "Evaluated holiday 2026 family business class routes (4 passengers) across South America & Central America; report delivered to Rann's email.",
        "details": {
            "current_task": "Subagent task execution complete. Full 12-day itineraries and hard-product comparisons dispatched.",
            "target_scripts": [
                "/home/rann/src/send_south_america_travel_report.py"
            ],
            "active_resources": [
                "Conversation 1ce39757-f5ff-410f-8ab9-3d0682aea016 transcript",
                "Comprehensive HTML Guide delivered to rann@rannbar-on.com"
            ],
            "key_metrics": {
                "Rank #1 Destination": "Festive Colombia (Medellin lights, Coffee Triangle, Cartagena)",
                "Top RDU Routing": "Copa Airlines non-stop RDU-PTY (eliminates domestic layovers)",
                "Lie-Flat Pick": "Delta One ATL-GIG / Copa Dreams MAX 9 to Brazil (Iguazu Falls)",
                "Booking Window": "Mid-January to early February 2026 (330 days out)"
            },
            "guardrails": "Completed within requested 1-hour window. Sent directly to Rann with zero external broadcast.",
            "execution_context": "Isolated subagent process running in read-only analysis sandbox with web retrieval."
        }
    },
    {
        "id": "system_housekeeping_agent",
        "name": "System Housekeeping & Infrastructure Agent",
        "category": "System Daemon",
        "category_color": "#475569",
        "status": "MONITORING",
        "status_color": "#64748b",
        "status_label": "IDLE / MONITORING",
        "priority": 3,
        "priority_label": "P3 (Routine Background)",
        "summary": "Monitors laptop lid-close behavior, printer pipelines (Cauchy CUPS suite), workspace sync, and nightly model performance audits.",
        "details": {
            "current_task": "Periodic telemetry inspection; ensures codebase knowledge database integrity and git remote synchronization.",
            "target_scripts": [
                "/home/rann/bin/cauchy_print.sh",
                "/home/rann/src/task_priority_scheduler.py",
                "/home/rann/src/code_learner.py"
            ],
            "active_resources": [
                "/home/rann/src/codebase_knowledge.json",
                "/home/rann/src/model_comparison_24h_log.json"
            ],
            "key_metrics": {
                "Codebase Knowledge Records": "23 verified architectural topics",
                "Model Comparative Trials": "16 logged benchmark trials",
                "System Battery / Lid Status": "Continuous inhibitor active"
            },
            "guardrails": "Auto-approval recording rule active across GEMINI.md, SKILL.md, and codebase_knowledge.json.",
            "execution_context": "Standard Linux background daemons and systemd service scripts."
        }
    }
]

def generate_dashboard():
    # 1. Write agents_data.json with full DAG topology
    full_payload = {
        "agents": AGENTS_REGISTRY,
        "dag_nodes": TASK_DAG_REGISTRY,
        "generated_at": datetime.now().isoformat()
    }
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(full_payload, f, indent=2)
    print(f"[Agents] Wrote data with DAG to {DATA_PATH}")

    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p EST")

    # Build DAG HTML representation
    tiers = {1: [], 2: [], 3: [], 4: []}
    for t in TASK_DAG_REGISTRY:
        tiers[t["tier"]].append(t)

    dag_tiers_html = ""
    tier_labels = {
        1: "Tier 1: Parallel Data Ingestion (Roots)",
        2: "Tier 2: Baseline Modeling & Synthesis",
        3: "Tier 3: Race Calls & Live Stream Ingestion",
        4: "Tier 4: Automated Dispatches & Stakeholder Queues"
    }

    for tier_num, tasks in tiers.items():
        cards_in_tier = ""
        for t in tasks:
            deps_str = ", ".join(t["deps"]) if t["deps"] else "None (Independent)"
            outs_str = ", ".join([Path(o).name for o in t["outputs"]])
            inps_str = ", ".join([Path(i).name for i in t["inputs"]])

            cards_in_tier += f"""
            <div class="dag-node-card" id="node_{t['id']}" onclick="highlightNode('{t['id']}')">
              <div class="dag-node-top">
                <span class="status-indicator" style="background-color: {t['status_color']}; box-shadow: 0 0 8px {t['status_color']};"></span>
                <span class="dag-node-title">{t['title']}</span>
                <span class="badge-priority">P{t['priority']}</span>
              </div>
              <div class="dag-node-agent">Allocated: <strong>{t['agent']}</strong></div>
              <div class="dag-node-deps">Pre-reqs: <code>{deps_str}</code></div>
              <div class="dag-node-hazard">{t['hazard']}</div>
              <div class="dag-node-io">
                <span>In: {inps_str}</span> &bull; <span>Out: {outs_str}</span>
              </div>
            </div>
            """

        dag_tiers_html += f"""
        <div class="dag-tier-column">
          <div class="dag-tier-header">{tier_labels[tier_num]}</div>
          <div class="dag-tier-cards">
            {cards_in_tier}
          </div>
        </div>
        """

    # Generate HTML cards for Agents
    cards_html = ""
    for a in AGENTS_REGISTRY:
        d = a["details"]
        scripts_li = "".join([f"<li><code>{s}</code></li>" for s in d.get("target_scripts", [])])
        resources_li = "".join([f"<li>{r}</li>" for r in d.get("active_resources", [])])
        
        metrics_cells = ""
        for k, v in d.get("key_metrics", {}).items():
            metrics_cells += f"""
            <div class="metric-box">
              <span class="m-lbl">{k}</span>
              <span class="m-val">{v}</span>
            </div>
            """

        cards_html += f"""
        <div class="agent-card" id="{a['id']}">
          <!-- DEFAULT SUMMARY VIEW -->
          <div class="card-summary" onclick="toggleDetails('{a['id']}')">
            <div class="summary-top">
              <div class="name-group">
                <span class="status-indicator" style="background-color: {a['status_color']}; box-shadow: 0 0 10px {a['status_color']};"></span>
                <span class="agent-name">{a['name']}</span>
                <span class="badge" style="background: rgba(255,255,255,0.08); color: {a['category_color']}; border: 1px solid {a['category_color']}40;">{a['category']}</span>
              </div>
              <div class="summary-right">
                <span class="badge-priority">{a['priority_label']}</span>
                <span class="badge-status" style="color: {a['status_color']};">{a['status_label']}</span>
                <button class="expand-btn" id="btn_{a['id']}">Details ▼</button>
              </div>
            </div>
            <p class="summary-text">{a['summary']}</p>
          </div>

          <!-- EXPANDED DETAILS (ACCORDION) -->
          <div class="card-details" id="details_{a['id']}">
            <div class="details-inner">
              <div class="detail-row">
                <strong>Current Execution Focus:</strong>
                <p>{d.get('current_task')}</p>
              </div>

              <div class="metrics-grid">
                {metrics_cells}
              </div>

              <div class="detail-columns">
                <div class="col">
                  <strong>Target Scripts & Commands:</strong>
                  <ul>{scripts_li}</ul>
                </div>
                <div class="col">
                  <strong>Active State & Data Resources:</strong>
                  <ul>{resources_li}</ul>
                </div>
              </div>

              <div class="detail-row" style="margin-top: 14px;">
                <strong>Safety Guardrails & Compliance Policy:</strong>
                <p style="color: #cbd5e1; font-size: 13px;">{d.get('guardrails')}</p>
              </div>

              <div class="detail-row" style="margin-top: 8px;">
                <strong>Runtime Execution Context:</strong>
                <p style="color: #94a3b8; font-size: 12px; font-family: monospace;">{d.get('execution_context')}</p>
              </div>
            </div>
          </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <script id="internalGateScript" src="/internal_gate.js"></script>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet">
  <title>Agent Command Center & Task DAG | Fully Private Operational Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --card-hover: #172133;
      --border: #1f2937;
      --text: #f9fafb;
      --muted: #9ca3af;
      --blue: #3b82f6;
      --green: #10b981;
      --red: #ef4444;
      --amber: #f59e0b;
      --purple: #8b5cf6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }}

    /* Top Lock Banner */
    .privacy-banner {{
      background: linear-gradient(90deg, #450a0a 0%, #1e1b4b 100%);
      border-bottom: 1px solid #991b1b;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 13px;
      font-weight: 700;
    }}
    .privacy-left {{
      display: flex;
      align-items: center;
      gap: 10px;
      color: #fca5a5;
    }}
    .badge-lock {{
      background: #dc2626;
      color: #ffffff;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    /* Header */
    header.dash-header {{
      background: #0f172a;
      border-bottom: 1px solid #1e293b;
      padding: 28px 24px;
    }}
    .header-inner {{
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .dash-title h1 {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.4px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .dash-title p {{
      font-size: 13px;
      color: var(--muted);
      margin-top: 4px;
    }}
    .stats-summary-bar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .stat-pill {{
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 12px;
      text-align: center;
    }}
    .stat-pill strong {{
      display: block;
      font-size: 16px;
      color: #fff;
    }}

    /* Main Container */
    .container {{
      max-width: 1200px;
      margin: 28px auto 0 auto;
      padding: 0 20px;
    }}

    .section-title {{
      font-size: 18px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.3px;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    /* TASK DEPENDENCY GRAPH (DAG) STYLES */
    .dag-section {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 32px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    }}
    .dag-container {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 18px;
      margin-top: 16px;
      overflow-x: auto;
    }}
    .dag-tier-column {{
      background: #090e1a;
      border: 1px solid #1e293b;
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .dag-tier-header {{
      font-size: 11.5px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: #94a3b8;
      border-bottom: 1px solid #1e293b;
      padding-bottom: 8px;
      margin-bottom: 4px;
    }}
    .dag-tier-cards {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .dag-node-card {{
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 8px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }}
    .dag-node-card:hover {{
      border-color: var(--blue);
      transform: translateY(-2px);
      box-shadow: 0 4px 14px rgba(59, 130, 246, 0.25);
    }}
    .dag-node-card.highlighted {{
      border-color: #10b981;
      background: #06231b;
      box-shadow: 0 0 16px rgba(16, 185, 129, 0.4);
    }}
    .dag-node-top {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
    }}
    .dag-node-title {{
      font-size: 13.5px;
      font-weight: 800;
      color: #ffffff;
      flex: 1;
    }}
    .dag-node-agent {{
      font-size: 11px;
      color: #60a5fa;
      margin-bottom: 4px;
    }}
    .dag-node-deps {{
      font-size: 11px;
      color: #94a3b8;
      margin-bottom: 6px;
    }}
    .dag-node-deps code {{
      font-size: 10.5px;
      color: #cbd5e1;
    }}
    .dag-node-hazard {{
      font-size: 10.5px;
      color: #f59e0b;
      background: rgba(245, 158, 11, 0.1);
      padding: 3px 6px;
      border-radius: 4px;
      margin-bottom: 6px;
      line-height: 1.3;
    }}
    .dag-node-io {{
      font-size: 10px;
      color: #64748b;
      border-top: 1px dashed rgba(255, 255, 255, 0.05);
      padding-top: 4px;
    }}

    /* Controls Bar */
    .controls-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .btn-action {{
      background: #1e293b;
      border: 1px solid #334155;
      color: #e2e8f0;
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .btn-action:hover {{
      background: #2563eb;
      color: #fff;
      border-color: #3b82f6;
    }}

    /* Agent Card Styles */
    .agents-list {{
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .agent-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      transition: border-color 0.2s;
    }}
    .agent-card:hover {{
      border-color: #374151;
    }}
    
    /* Summary View (Default) */
    .card-summary {{
      padding: 18px 22px;
      cursor: pointer;
      user-select: none;
      transition: background 0.15s;
    }}
    .card-summary:hover {{
      background: var(--card-hover);
    }}
    .summary-top {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 8px;
    }}
    .name-group {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .status-indicator {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .agent-name {{
      font-size: 17px;
      font-weight: 800;
      color: #ffffff;
      letter-spacing: -0.2px;
    }}
    .badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
    }}
    .summary-right {{
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .badge-priority {{
      font-size: 11px;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
    }}
    .badge-status {{
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.5px;
    }}
    .expand-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #cbd5e1;
      border-radius: 6px;
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .expand-btn:hover {{
      background: var(--blue);
      color: #fff;
    }}
    .summary-text {{
      font-size: 14px;
      color: #cbd5e1;
      line-height: 1.45;
    }}

    /* Details View (Expanded on Click) */
    .card-details {{
      display: none;
      border-top: 1px solid #1e293b;
      background: #090e1a;
      animation: fadeIn 0.2s ease-out;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(-4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .details-inner {{
      padding: 20px 24px;
    }}
    .detail-row {{
      margin-bottom: 14px;
    }}
    .detail-row strong {{
      font-size: 12px;
      text-transform: uppercase;
      color: #94a3b8;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 4px;
    }}
    .detail-row p {{
      font-size: 13.5px;
      color: #f1f5f9;
    }}

    /* Metrics Grid */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin: 14px 0;
    }}
    .metric-box {{
      background: #111827;
      border: 1px solid #1f2937;
      border-radius: 8px;
      padding: 10px 14px;
    }}
    .m-lbl {{
      font-size: 10px;
      color: #64748b;
      text-transform: uppercase;
      font-weight: 700;
      display: block;
    }}
    .m-val {{
      font-size: 13.5px;
      font-weight: 800;
      color: #60a5fa;
      display: block;
      margin-top: 2px;
    }}

    /* Detail Columns */
    .detail-columns {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-top: 12px;
    }}
    @media (max-width: 768px) {{
      .detail-columns {{ grid-template-columns: 1fr; }}
      .dag-container {{ grid-template-columns: 1fr; }}
    }}
    .col strong {{
      font-size: 11px;
      text-transform: uppercase;
      color: #94a3b8;
      letter-spacing: 0.5px;
      display: block;
      margin-bottom: 6px;
    }}
    .col ul {{
      list-style: none;
      padding-left: 0;
    }}
    .col li {{
      font-size: 12.5px;
      color: #cbd5e1;
      padding: 4px 0;
      border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
    }}
    code {{
      font-family: 'JetBrains Mono', monospace;
      color: #60a5fa;
      font-size: 12px;
    }}

    .footer {{
      text-align: center;
      padding: 40px 20px 0 20px;
      font-size: 12px;
      color: #64748b;
    }}
  </style>
</head>
<body>

  <!-- Top Confidential Lock Banner -->
  <div class="privacy-banner">
    <div class="privacy-left">
      <span class="badge-lock">RESTRICTED</span>
      <span>INTERNAL USE ONLY &bull; RANN BAR-ON PRIVATE SYSTEM TELEMETRY</span>
    </div>
    <div style="color: #cbd5e1; font-size: 12px;">
      Last sync: {now_str}
    </div>
  </div>

  <!-- Header -->
  <header class="dash-header">
    <div class="header-inner">
      <div class="dash-title">
        <h1>⚡ Agent Command Center & Task DAG</h1>
        <p>Real-time operational topology, active workloads, and execution contracts across all 8 agent domains</p>
      </div>
      <div class="stats-summary-bar">
        <div class="stat-pill">
          <strong>8</strong>
          <span>Total Tasks</span>
        </div>
        <div class="stat-pill">
          <strong style="color: #10b981;">4</strong>
          <span>Active Agents</span>
        </div>
        <div class="stat-pill">
          <strong style="color: #60a5fa;">2</strong>
          <span>Parallel Roots</span>
        </div>
        <div class="stat-pill">
          <strong style="color: #f59e0b;">1</strong>
          <span>Queued Task</span>
        </div>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="container">

    <!-- TASK DEPENDENCY GRAPH (DAG) SECTION -->
    <div class="dag-section">
      <div class="section-title">
        <span>📊 Live Task Dependency Graph (DAG Architecture)</span>
        <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">Bernstein Hazard Invariant: J_dep &rarr; Agent(J_anc)</span>
      </div>
      <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 12px;">
        Visual topological frontier computed by <code>AgentDAG</code>. Independent tasks spawn parallel worker agents; dependent tasks are affinity-forwarded directly to the agent executing prerequisite commands:
      </p>

      <div class="dag-container">
        {dag_tiers_html}
      </div>
    </div>

    <!-- AGENTS DIRECTORY SECTION -->
    <div class="section-title">
      <span>🤖 Agent Directory & Workload Telemetry</span>
      <span style="font-size: 12px; color: #94a3b8; font-weight: 600;">8 Registered Agents</span>
    </div>

    <div class="controls-bar">
      <div>
        <span style="font-size: 13px; color: #94a3b8;">Click any agent card to expand full execution details, commands, and guardrails.</span>
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn-action" onclick="expandAll()">Expand All</button>
        <button class="btn-action" onclick="collapseAll()">Collapse All</button>
      </div>
    </div>

    <!-- Agents List -->
    <div class="agents-list">
      {cards_html}
    </div>

    <div class="footer">
      Private Agent Telemetry Dashboard &bull; rannbar-on.com/agents &bull; Protected under Duke Department of Mathematics internal guidelines
    </div>
  </main>

  <script>
    function toggleDetails(id) {{
      const d = document.getElementById('details_' + id);
      const b = document.getElementById('btn_' + id);
      if (d.style.display === 'block') {{
        d.style.display = 'none';
        b.innerText = 'Details ▼';
      }} else {{
        d.style.display = 'block';
        b.innerText = 'Close ▲';
      }}
    }}

    function expandAll() {{
      document.querySelectorAll('.card-details').forEach(d => d.style.display = 'block');
      document.querySelectorAll('.expand-btn').forEach(b => b.innerText = 'Close ▲');
    }}

    function collapseAll() {{
      document.querySelectorAll('.card-details').forEach(d => d.style.display = 'none');
      document.querySelectorAll('.expand-btn').forEach(b => b.innerText = 'Details ▼');
    }}

    function highlightNode(id) {{
      const card = document.getElementById('node_' + id);
      const isHigh = card.classList.contains('highlighted');
      document.querySelectorAll('.dag-node-card').forEach(c => c.classList.remove('highlighted'));
      if (!isHigh) {{
        card.classList.add('highlighted');
      }}
    }}
  </script>
</body>
</html>
"""

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Agents] Wrote index.html to {INDEX_PATH}")

    with open(ROOT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Agents] Wrote root router page to {ROOT_PATH}")

if __name__ == "__main__":
    generate_dashboard()
