"""
Static Site Generator for Durham Politics Tracker.
Produces the interactive single-page application at:
/home/rann/src/website/mainwebsite/durhampolitics/index.html
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from .config import (
    HTML_OUTPUT_PATH, DATA_EXPORT_PATH, PAGE_PASSWORD, MASTER_PASSWORD,
    BODIES, ISSUE_CATEGORIES
)
from .database import DurhamPoliticsDB

def generate_durhampolitics_page(db: Optional[DurhamPoliticsDB] = None) -> str:
    """
    Extracts the full database state and renders the standalone interactive
    password-protected HTML application.
    """
    if db is None:
        db = DurhamPoliticsDB(read_only=True)

    dataset = db.export_full_dataset()
    data_json = json.dumps(dataset, ensure_ascii=False)

    # Ensure output directory exists
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Save data export JSON
    with open(DATA_EXPORT_PATH, "w", encoding="utf-8") as f:
        f.write(data_json)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Durham Politics Tracker | Confidential Deliberation & Voting Intelligence</title>
  
  <!-- Strict Privacy & Anti-Search Indexing Control -->
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet">
  <meta name="bingbot" content="noindex, nofollow, noarchive, nosnippet">

  <style>
    :root {{
      --bg-dark: #090d16;
      --bg-sidebar: #0f172a;
      --card-bg: #111827;
      --card-inner: #1a2234;
      --card-border: #1f2937;
      --border-focus: #3b82f6;
      --text-main: #f9fafb;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-blue: #3b82f6;
      --accent-green: #10b981;
      --accent-amber: #f59e0b;
      --accent-red: #ef4444;
      --accent-purple: #8b5cf6;
      --accent-cyan: #06b6d4;
      --dps-color: #3b82f6;
      --city-color: #10b981;
      --bocc-color: #f59e0b;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg-dark);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      overflow-x: hidden;
    }}

    /* Password Protection Screen Overlay */
    #authOverlay {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: radial-gradient(circle at center, #1e1b4b 0%, #090d16 100%);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}

    .auth-card {{
      background: var(--card-bg);
      border: 1px solid #312e81;
      border-radius: 12px;
      max-width: 440px;
      width: 100%;
      padding: 32px;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.7);
      text-align: center;
    }}

    .auth-badge {{
      display: inline-block;
      background: rgba(239, 68, 68, 0.2);
      border: 1px solid #ef4444;
      color: #fca5a5;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 1px;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 9999px;
      margin-bottom: 16px;
    }}

    .auth-title {{
      font-size: 22px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 8px;
    }}

    .auth-desc {{
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 24px;
    }}

    .auth-form {{
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}

    .auth-input {{
      background: var(--card-inner);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px 16px;
      color: #fff;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }}

    .auth-input:focus {{
      border-color: var(--accent-blue);
    }}

    .auth-btn {{
      background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
      color: #fff;
      font-weight: 600;
      border: none;
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: transform 0.1s, opacity 0.2s;
    }}

    .auth-btn:hover {{
      opacity: 0.95;
    }}

    .auth-btn:active {{
      transform: scale(0.98);
    }}

    .auth-error {{
      color: #f87171;
      font-size: 12px;
      margin-top: 6px;
      display: none;
    }}

    /* Main App Layout */
    #appWrapper {{
      display: none;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Header */
    header {{
      background: rgba(15, 23, 42, 0.95);
      backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--card-border);
      position: sticky;
      top: 0;
      z-index: 100;
    }}

    .header-inner {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }}

    .brand-group {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .brand-logo {{
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #2563eb, #7c3aed);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 900;
      font-size: 18px;
      color: #fff;
    }}

    .brand-text h1 {{
      font-size: 17px;
      font-weight: 800;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .brand-text p {{
      font-size: 11px;
      color: var(--text-muted);
    }}

    .badge-confidential {{
      background: rgba(239, 68, 68, 0.15);
      border: 1px solid rgba(239, 68, 68, 0.4);
      color: #fca5a5;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}

    .search-box {{
      position: relative;
      width: 280px;
    }}

    .search-input {{
      width: 100%;
      background: var(--card-inner);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 8px 12px 8px 32px;
      color: #fff;
      font-size: 13px;
      outline: none;
    }}

    .search-icon {{
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 14px;
    }}

    .btn-lock {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      border-radius: 8px;
      padding: 8px 14px;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: background 0.2s;
    }}

    .btn-lock:hover {{
      background: #334155;
      color: #fff;
    }}

    /* Navigation Bar */
    nav.nav-tabs {{
      background: #0b1120;
      border-bottom: 1px solid var(--card-border);
    }}

    .nav-inner {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      gap: 4px;
      overflow-x: auto;
      scrollbar-width: none;
    }}

    .tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      padding: 12px 16px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      border-bottom: 2px solid transparent;
      white-space: nowrap;
      transition: color 0.2s, border-color 0.2s;
    }}

    .tab-btn:hover {{
      color: #fff;
    }}

    .tab-btn.active {{
      color: #fff;
      border-bottom-color: var(--accent-blue);
    }}

    .tab-pill {{
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 9999px;
      background: #1e293b;
      color: var(--text-muted);
    }}

    .tab-btn.active .tab-pill {{
      background: rgba(59, 130, 246, 0.2);
      color: #93c5fd;
    }}

    /* Main Container */
    main.container {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 24px;
      flex: 1;
      width: 100%;
    }}

    /* Tab Content Panes */
    .tab-pane {{
      display: none;
    }}

    .tab-pane.active {{
      display: block;
      animation: fadeIn 0.2s ease-in-out;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(4px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* KPI Summary Cards */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}

    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 18px;
      position: relative;
      overflow: hidden;
    }}

    .kpi-card::before {{
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 3px;
      background: var(--accent-blue);
    }}

    .kpi-card.kpi-dps::before {{ background: var(--dps-color); }}
    .kpi-card.kpi-city::before {{ background: var(--city-color); }}
    .kpi-card.kpi-bocc::before {{ background: var(--bocc-color); }}

    .kpi-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      margin-bottom: 6px;
    }}

    .kpi-value {{
      font-size: 28px;
      font-weight: 800;
      color: #fff;
      line-height: 1;
      margin-bottom: 6px;
    }}

    .kpi-subtext {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    /* Cards & Section Containers */
    .section-title {{
      font-size: 18px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 20px;
    }}

    /* Body Badge */
    .badge-body {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .badge-body.dps {{
      background: rgba(59, 130, 246, 0.15);
      border: 1px solid rgba(59, 130, 246, 0.3);
      color: #93c5fd;
    }}

    .badge-body.city {{
      background: rgba(16, 185, 129, 0.15);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: #6ee7b7;
    }}

    .badge-body.bocc {{
      background: rgba(245, 158, 11, 0.15);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #fcd34d;
    }}

    /* Member Cards Grid */
    .members-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
      margin-top: 16px;
    }}

    .member-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s, border-color 0.15s;
    }}

    .member-card:hover {{
      transform: translateY(-2px);
      border-color: #334155;
    }}

    .member-header {{
      display: flex;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 12px;
    }}

    .member-avatar {{
      width: 48px;
      height: 48px;
      border-radius: 10px;
      background: #1e293b;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 16px;
      color: #fff;
      flex-shrink: 0;
    }}

    .member-info h3 {{
      font-size: 16px;
      font-weight: 700;
      color: #fff;
    }}

    .member-info p {{
      font-size: 12px;
      color: var(--text-muted);
    }}

    .member-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 8px;
      background: var(--card-inner);
      border-radius: 8px;
      padding: 10px;
      margin: 12px 0;
      text-align: center;
    }}

    .stat-box-num {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
    }}

    .stat-box-lbl {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-dim);
    }}

    .tag-container {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }}

    .tag {{
      background: #1e293b;
      color: #cbd5e1;
      font-size: 11px;
      padding: 2px 8px;
      border-radius: 4px;
    }}

    .tag-ideology {{
      background: rgba(139, 92, 246, 0.15);
      border: 1px solid rgba(139, 92, 246, 0.3);
      color: #c4b5fd;
    }}

    .btn-view-record {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #fff;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      padding: 8px;
      width: 100%;
      margin-top: 14px;
      cursor: pointer;
      transition: background 0.2s;
    }}

    .btn-view-record:hover {{
      background: #334155;
    }}

    /* Meeting Timeline Feed */
    .timeline {{
      display: flex;
      flex-direction: column;
      gap: 16px;
      margin-top: 16px;
    }}

    .meeting-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 20px;
      transition: border-color 0.2s;
    }}

    .meeting-card:hover {{
      border-color: #334155;
    }}

    .meeting-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 12px;
    }}

    .meeting-meta {{
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: var(--text-dim);
    }}

    .meeting-title {{
      font-size: 16px;
      font-weight: 800;
      color: #fff;
      margin-bottom: 6px;
    }}

    .meeting-summary {{
      font-size: 13px;
      color: var(--text-muted);
      line-height: 1.6;
      margin-bottom: 14px;
    }}

    /* Collapsible Sections inside Meeting */
    .meeting-details-toggle {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 10px;
      padding-top: 12px;
      border-top: 1px solid var(--card-inner);
    }}

    .btn-toggle-details {{
      background: #1e293b;
      border: 1px solid var(--card-border);
      color: #cbd5e1;
      font-size: 12px;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}

    .btn-toggle-details:hover {{
      background: #334155;
      color: #fff;
    }}

    .details-pane {{
      display: none;
      margin-top: 14px;
      background: var(--card-inner);
      border-radius: 8px;
      padding: 16px;
      border: 1px solid #232d42;
    }}

    /* Votes list */
    .vote-item {{
      border-bottom: 1px solid #2a374f;
      padding-bottom: 12px;
      margin-bottom: 12px;
    }}

    .vote-item:last-child {{
      border-bottom: none;
      padding-bottom: 0;
      margin-bottom: 0;
    }}

    .vote-title {{
      font-size: 14px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 4px;
    }}

    .vote-badge-passed {{
      background: rgba(16, 185, 129, 0.2);
      color: #6ee7b7;
      border: 1px solid rgba(16, 185, 129, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }}

    .vote-badge-failed {{
      background: rgba(239, 68, 68, 0.2);
      color: #fca5a5;
      border: 1px solid rgba(239, 68, 68, 0.4);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
    }}

    .vote-breakdown {{
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 6px;
    }}

    .disagreement-box {{
      background: #131b2e;
      border-left: 3px solid var(--accent-amber);
      border-radius: 0 8px 8px 0;
      padding: 14px;
      margin-bottom: 12px;
    }}

    .disagreement-box:last-child {{
      margin-bottom: 0;
    }}

    .dis-title {{
      font-size: 14px;
      font-weight: 700;
      color: #fcd34d;
      margin-bottom: 6px;
    }}

    .dis-side {{
      font-size: 12px;
      color: #e2e8f0;
      margin: 6px 0;
    }}

    /* Pairwise Heatmap Grid */
    .heatmap-wrapper {{
      overflow-x: auto;
      margin-top: 16px;
    }}

    .heatmap-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: center;
    }}

    .heatmap-table th, .heatmap-table td {{
      padding: 8px;
      border: 1px solid #1e293b;
    }}

    .heatmap-table th {{
      background: #0f172a;
      color: var(--text-muted);
      font-weight: 600;
      max-width: 110px;
      word-wrap: break-word;
    }}

    .heat-high {{ background: rgba(16, 185, 129, 0.25); color: #6ee7b7; font-weight: 700; }}
    .heat-med {{ background: rgba(245, 158, 11, 0.25); color: #fcd34d; }}
    .heat-low {{ background: rgba(239, 68, 68, 0.25); color: #fca5a5; font-weight: 700; }}
    .heat-self {{ background: #1e293b; color: var(--text-dim); }}

    /* Modal for Voting Record */
    #recordModal {{
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.75);
      backdrop-filter: blur(4px);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }}

    .modal-content {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      max-width: 720px;
      width: 100%;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}

    .modal-header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    .modal-body {{
      padding: 24px;
      overflow-y: auto;
      flex: 1;
    }}

    .btn-close-modal {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 20px;
      cursor: pointer;
    }}

    /* Filter Controls Bar */
    .filter-bar {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-bottom: 20px;
      align-items: center;
    }}

    .filter-select {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: #fff;
      font-size: 13px;
      border-radius: 8px;
      padding: 8px 12px;
      outline: none;
    }}

    /* Toast Notification */
    #toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      border: 1px solid var(--accent-blue);
      color: #fff;
      font-size: 13px;
      padding: 12px 20px;
      border-radius: 8px;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5);
      z-index: 999999;
      display: none;
    }}
  </style>
</head>
<body>

  <!-- ======================================================== -->
  <!-- PASSWORD PROTECTION GATEWAY                             -->
  <!-- ======================================================== -->
  <div id="authOverlay">
    <div class="auth-card">
      <div class="auth-badge">Confidential Document</div>
      <div class="auth-title">Durham Politics Tracker</div>
      <div class="auth-desc">Private research command center tracking DPS Board of Education, Durham City Council, and County Commissioners. Password protected.</div>
      
      <form class="auth-form" onsubmit="handleAuth(event)">
        <div style="text-align: left;">
          <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">Username</label>
          <input type="text" id="authUsernameInput" class="auth-input" placeholder="e.g. rann" autofocus required autocomplete="username" style="width: 100%;">
        </div>
        <div style="text-align: left;">
          <label style="font-size: 11px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">Password</label>
          <input type="password" id="authPasswordInput" class="auth-input" placeholder="Enter Password" required autocomplete="current-password" style="width: 100%;">
        </div>
        <label style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); cursor: pointer; text-align: left;">
          <input type="checkbox" id="rememberAuthCheckbox" checked> Remember access on this browser
        </label>
        <button type="submit" class="auth-btn">Unlock Command Center &rarr;</button>
        <div id="authErrorMsg" class="auth-error">Invalid username or password. Please verify and retry.</div>
        <div style="margin-top: 12px; font-size: 12.5px; color: var(--text-muted); text-align: center;">
          Need an account? <a href="/durhampolitics/signup.html" style="color: #60a5fa; text-decoration: none; font-weight: 600;">Request Access &rarr;</a>
          &nbsp;&bull;&nbsp;
          <a href="/durhampolitics/docs.html" style="color: var(--text-muted); text-decoration: none;">Documentation</a>
        </div>
      </form>
    </div>
  </div>

  <!-- ======================================================== -->
  <!-- MAIN APPLICATION SHELL                                  -->
  <!-- ======================================================== -->
  <div id="appWrapper">
    <!-- Header -->
    <header>
      <div class="header-inner">
        <div class="brand-group">
          <div class="brand-logo">DP</div>
          <div class="brand-text">
            <h1>Durham Politics Tracker <span class="badge-confidential">Private Access</span></h1>
            <p>Nov 2024 – Nov 2026 Deliberation & Voting Intelligence | DPS, City Council & BOCC</p>
          </div>
        </div>

        <div class="header-actions">
          <label style="display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);cursor:pointer;background:rgba(15,23,42,0.65);border:1px solid var(--card-border);padding:6px 10px;border-radius:8px;white-space:nowrap;" title="Toggle blanket consent agenda votes in counts and lists (pulled items are always included)">
            <input type="checkbox" id="includeConsentAgendaToggle" onchange="toggleConsentAgenda(this.checked)" style="accent-color:#3b82f6;cursor:pointer;" />
            <span>Include Consent Agenda</span>
          </label>
          <div class="search-box">
            <span class="search-icon">&#128269;</span>
            <input type="text" id="globalSearchInput" class="search-input" placeholder="Search votes, topics, officials..." oninput="handleGlobalSearch(this.value)">
          </div>
          <a href="/durhampolitics/docs.html" style="display:inline-flex;align-items:center;gap:5px;padding:7px 12px;border-radius:8px;border:1px solid var(--card-border);background:rgba(15,23,42,0.65);color:var(--text-main);text-decoration:none;font-size:12px;font-weight:600;white-space:nowrap;" title="Site Documentation & Guide">
            <span>&#128214;</span> Docs
          </a>
        </div>
      </div>
    </header>

    <!-- Navigation Tabs -->
    <nav class="nav-tabs">
      <div class="nav-inner">
        <button class="tab-btn active" onclick="switchTab('overview')">
          <span>Overview & Macro Trends</span>
        </button>
        <button class="tab-btn" onclick="switchTab('dps')">
          <span>DPS School Board</span>
          <span class="tab-pill" id="pill_dps">7 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('city')">
          <span>City Council</span>
          <span class="tab-pill" id="pill_city">7 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('bocc')">
          <span>County Commissioners</span>
          <span class="tab-pill" id="pill_bocc">5 Seats</span>
        </button>
        <button class="tab-btn" onclick="switchTab('members')">
          <span>Member Directory</span>
          <span class="tab-pill" id="pill_members">22 Officials</span>
        </button>
        <button class="tab-btn" onclick="switchTab('alignments')">
          <span>Voting Alignments & Heatmaps</span>
        </button>
        <button class="tab-btn" onclick="switchTab('timeline')">
          <span>Meeting Archives & Video</span>
          <span class="tab-pill" id="pill_meetings">Timeline</span>
        </button>
        <button class="tab-btn" id="liveMeetingTabBtn" style="display:none; color:#fca5a5; border-bottom-color: transparent;" onclick="window.location.href='/durhampolitics/live.html'">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#ef4444;box-shadow:0 0 8px #ef4444;margin-right:4px;"></span>
          <span>Live Meeting in Progress</span>
          <span class="tab-pill" id="liveMeetingPill" style="background:rgba(239,68,68,0.25);color:#fca5a5;">LIVE</span>
        </button>
      </div>
    </nav>

    <!-- Main Content Container -->
    <main class="container">
      
      <!-- ================= TAB 1: OVERVIEW ================= -->
      <div id="tab_overview" class="tab-pane active">
        <!-- KPI Cards -->
        <div class="kpi-grid">
          <div class="kpi-card">
            <div class="kpi-label">Tracked Meetings</div>
            <div class="kpi-value" id="kpiTotalMeetings">0</div>
            <div class="kpi-subtext">Nov 2024 – Nov 2026 public sessions</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Recorded Formal Votes</div>
            <div class="kpi-value" id="kpiTotalVotes">0</div>
            <div class="kpi-subtext" id="kpiUnanimousPct">0% Unanimous Consensual</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Contested Roll Calls</div>
            <div class="kpi-value" id="kpiContestedVotes">0</div>
            <div class="kpi-subtext">Divided roll calls & dissents</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Deliberation Issues</div>
            <div class="kpi-value" id="kpiTotalDisagreements">0</div>
            <div class="kpi-subtext">Sources of substantive debate</div>
          </div>
        </div>

        <!-- Cross-Body Summary Cards -->
        <div class="section-title">Major Governance Fault Lines & Running Alignments</div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px;">
          <!-- DPS Summary -->
          <div class="card" style="border-top: 3px solid var(--dps-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body dps">Durham Public Schools</span>
              <span style="font-size: 12px; color: var(--text-dim);">Chaired by Joy Harrell-Goff</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Labor Stability, Fiscal Oversight & Facility Preservation</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Key tensions center on classified staff salary schedules and meet-and-confer frameworks with the Durham Association of Educators (DAE). Under Policy 8600, strict quarterly budget reporting was instituted. Board resisted outside consultant recommendations to consolidate/close elementary schools.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> Labor-allied progressives (Bir, Rogers, Rivero, Chávez) partnering with collaborative leadership (Harrell-Goff, Cason) to prioritize workforce retention.
            </div>
          </div>

          <!-- City Council Summary -->
          <div class="card" style="border-top: 3px solid var(--city-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body city">Durham City Council</span>
              <span style="font-size: 12px; color: var(--text-dim);">Mayor Leonardo Williams</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Density Urbanism (SCAD) vs Neighborhood Preservation</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Persistent 4-3 and 5-2 ideological split on development rezonings and the SCAD housing code. Williams, Caballero, and Kopac advocate market supply abundance; Baker and Cook dissent frequently demanding deep binding affordability and environmental buffers. Universal support for HEART non-police crisis expansion.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> Pro-growth urbanists (Williams, Caballero, Kopac, Rist) vs Planning integrity/tenant defense progressives (Baker, Cook, Burris).
            </div>
          </div>

          <!-- BOCC Summary -->
          <div class="card" style="border-top: 3px solid var(--bocc-color);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <span class="badge-body bocc">County Commissioners</span>
              <span style="font-size: 12px; color: var(--text-dim);">Chaired by Dr. Mike Lee</span>
            </div>
            <h3 style="font-size: 15px; margin-bottom: 8px;">Education Funding, Property Revaluation & Regional Transit</h3>
            <p style="font-size: 13px; color: var(--text-muted); line-height: 1.6; margin-bottom: 12px;">
              Steered major supplemental funding ($27M) to stabilize DPS classified salaries. Unanimous on dedicating county-owned downtown parcels (300 E. Main) to 100% affordable housing. High cohesion with isolated dissents on suburban property tax rate adjustments. Smooth leadership rotation from Allam to Lee in Dec 2025.
            </p>
            <div style="font-size: 12px; background: var(--card-inner); padding: 10px; border-radius: 6px;">
              <strong>Key Faction Dynamic:</strong> High consensus body (Lee, Allam, Burton, Jacobs, Valentine) prioritizing countywide human services, public health, and transit right-of-way.
            </div>
          </div>
        </div>

        <!-- Latest High-Impact Motions -->
        <div class="section-title" style="margin-top: 24px;">Recent Landmark Votes</div>
        <div id="overviewLandmarkVotes" class="timeline"></div>
      </div>

      <!-- ================= TAB 2: DPS ================= -->
      <div id="tab_dps" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham Public Schools Board of Education</h2>
            <span class="badge-body dps">7 Total Seats</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            Oversees Durham County's K-12 public school system, serving over 32,000 students across 56 schools. Responsibilities include superintendent supervision (Dr. Anthony S. Lewis), operational budget adoption, state class-size compliance, facility construction (2022 bond projects), and staff compensation supplements.
          </p>
        </div>
        <div class="section-title">DPS Board Members</div>
        <div id="dpsMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;">DPS Meeting Chronology & Roll Calls</div>
        <div id="dpsMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 3: CITY COUNCIL ================= -->
      <div id="tab_city" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham City Council</h2>
            <span class="badge-body city">7 Total Seats (Mayor + 6 Council Members)</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            The legislative and policy-making body of the City of Durham. Enacts municipal ordinances, sets city ad valorem property tax rates, adopts the annual capital and operating budget ($640M+), oversees development zoning and annexation requests, and guides public safety investments including the DPD and HEART non-police crisis program.
          </p>
        </div>
        <div class="section-title">City Council Members</div>
        <div id="cityMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;">City Council Meeting Chronology & Roll Calls</div>
        <div id="cityMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 4: BOCC ================= -->
      <div id="tab_bocc" class="tab-pane">
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h2 style="font-size: 20px; font-weight: 800; color: #fff;">Durham Board of County Commissioners (BOCC)</h2>
            <span class="badge-body bocc">5 County-wide Seats</span>
          </div>
          <p style="font-size: 14px; color: var(--text-muted); line-height: 1.6;">
            The governing body of Durham County, managing public health, social services, property appraisals, county court administration, and local funding supplements for Durham Public Schools and Durham Technical Community College. Chaired by Dr. Mike Lee (elected Dec 2025; Vice Chair Nida Allam).
          </p>
        </div>
        <div class="section-title">County Commissioners</div>
        <div id="boccMembersGrid" class="members-grid"></div>

        <div class="section-title" style="margin-top: 32px;">BOCC Meeting Chronology & Roll Calls</div>
        <div id="boccMeetingsTimeline" class="timeline"></div>
      </div>

      <!-- ================= TAB 5: MEMBERS ================= -->
      <div id="tab_members" class="tab-pane">
        <div class="filter-bar">
          <select id="memberFilterBody" class="filter-select" onchange="renderMembers()">
            <option value="all">All Governing Bodies</option>
            <option value="dps">DPS School Board</option>
            <option value="city">Durham City Council</option>
            <option value="bocc">County Commissioners (BOCC)</option>
          </select>
          <select id="memberFilterStatus" class="filter-select" onchange="renderMembers()">
            <option value="current">Current Serving Officials</option>
            <option value="all">All (Including Preceding Members)</option>
            <option value="former">Preceding / Former Members Only</option>
          </select>
        </div>
        <div id="allMembersGrid" class="members-grid"></div>
      </div>

      <!-- ================= TAB 6: ALIGNMENTS ================= -->
      <div id="tab_alignments" class="tab-pane">
        <div class="card">
          <h2 style="font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 8px;">Pairwise Voting Agreement Heatmap</h2>
          <p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-bottom: 16px;">
            Calculates the percentage of recorded votes where two members voted identically when both were present. Green cells indicate voting agreement &ge; 95%; yellow indicates 90&ndash;94.9%; red indicates &lt; 90%.
          </p>
          <div class="filter-bar">
            <select id="alignmentBodySelect" class="filter-select" onchange="renderPairwiseHeatmap(this.value)">
              <option value="city">Durham City Council Agreement Grid</option>
              <option value="dps">DPS Board of Education Agreement Grid</option>
              <option value="bocc">Durham County Commissioners (BOCC) Grid</option>
            </select>
          </div>
          <div id="heatmapContainer" class="heatmap-wrapper"></div>
        </div>

        <div class="card" style="margin-top: 20px;">
          <h3 id="dissentLeaderboardTitle" style="font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 8px;">Dissent Frequency Leaderboard</h3>
          <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 14px;">
            Officials on the selected board who cast the highest proportion of dissenting votes (NAY against a carried majority motion) out of all recorded votes:
          </p>
          <div id="dissentLeaderboard"></div>
        </div>
      </div>

      <!-- ================= TAB 7: TIMELINE ================= -->
      <div id="tab_timeline" class="tab-pane">
        <div class="filter-bar">
          <select id="timelineFilterBody" class="filter-select" onchange="renderTimeline()">
            <option value="all">All Bodies</option>
            <option value="dps">DPS School Board</option>
            <option value="city">City Council</option>
            <option value="bocc">County Commissioners</option>
          </select>
          <select id="timelineFilterYear" class="filter-select" onchange="renderTimeline()">
            <option value="all">All Years (2024–2026)</option>
            <option value="2026">2026 Meetings</option>
            <option value="2025">2025 Meetings</option>
            <option value="2024">2024 Meetings</option>
          </select>
          <select id="timelineFilterContested" class="filter-select" onchange="renderTimeline()">
            <option value="all">All Recorded Sessions</option>
            <option value="contested">Contested Roll Calls Only</option>
          </select>
        </div>
        <div id="masterTimelineList" class="timeline"></div>
      </div>

    </main>
  </div>

  <!-- ======================================================== -->
  <!-- VOTING RECORD MODAL                                     -->
  <!-- ======================================================== -->
  <div id="recordModal">
    <div class="modal-content">
      <div class="modal-header">
        <div id="modalMemberTitle" style="font-weight: 800; font-size: 18px; color: #fff;"></div>
        <button class="btn-close-modal" onclick="closeRecordModal()">&times;</button>
      </div>
      <div id="modalMemberBody" class="modal-body"></div>
    </div>
  </div>

  <!-- Toast notification -->
  <div id="toast"></div>

  <!-- ======================================================== -->
  <!-- CLIENT DATA & APPLICATION LOGIC                          -->
  <!-- ======================================================== -->
  <script>
    const APP_DATA = {data_json};
    const VALID_PASSWORDS = ["{PAGE_PASSWORD}", "{MASTER_PASSWORD}"];

    // ----------------------------------------------------
    // Authentication & Privacy Control
    // ----------------------------------------------------
    const SHARED_ACTIVE_KEY = "rann_auth_last_active";
    const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000; // 1 hour idle timeout
    let lastActiveMem = Date.now();

    function touchActivity() {{
      lastActiveMem = Date.now();
      try {{ localStorage.setItem(SHARED_ACTIVE_KEY, lastActiveMem.toString()); }} catch(e) {{}}
    }}

    function getLastActive() {{
      try {{
        const stored = parseInt(localStorage.getItem(SHARED_ACTIVE_KEY) || "0", 10);
        return Math.max(stored || 0, lastActiveMem);
      }} catch(e) {{
        return lastActiveMem;
      }}
    }}

    let lastThrottle = 0;
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(ev => {{
      window.addEventListener(ev, () => {{
        const now = Date.now();
        if (now - lastThrottle > 2000) {{
          lastThrottle = now;
          touchActivity();
        }}
      }}, {{ passive: true }});
    }});

    setInterval(() => {{
      const now = Date.now();
      const isAuthed = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (isAuthed && (now - getLastActive() > INACTIVITY_TIMEOUT_MS)) {{
        lockApp("Session timed out after 1 hour of idle time.");
      }}
    }}, 5000);

    function checkAuth() {{
      const sessionAuth = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      const lastActive = getLastActive();
      const now = Date.now();
      
      if (sessionAuth && (now - lastActive <= INACTIVITY_TIMEOUT_MS)) {{
        touchActivity();
        unlockApp();
      }} else {{
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.removeItem("durham_pol_auth");
        document.getElementById("authOverlay").style.display = "flex";
        document.getElementById("appWrapper").style.display = "none";
      }}
    }}

    async function sha256Hex(str) {{
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
      return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}

    async function verifyApprovedDurhamUser(identifier, password) {{
      try {{
        const res = await fetch("/durhampolitics/approved_users.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) return null;
        const data = await res.json();
        const users = (data && data.users) || [];
        const idLow = identifier.toLowerCase();
        const match = users.find(u =>
          u.status === "APPROVED" &&
          (u.allowed_pages || []).includes("/durhampolitics") &&
          ((u.username || "").toLowerCase() === idLow || (u.email || "").toLowerCase() === idLow)
        );
        if (!match || !match.salt || !match.password_hash) return null;
        const computed = await sha256Hex(match.salt + ":" + password);
        return computed === match.password_hash ? match : null;
      }} catch (e) {{
        return null;
      }}
    }}

    async function handleAuth(e) {{
      e.preventDefault();
      const user = (document.getElementById("authUsernameInput") ? document.getElementById("authUsernameInput").value.trim().toLowerCase() : "");
      const pwd = document.getElementById("authPasswordInput").value.trim();

      if (user === "rann" && pwd === "{MASTER_PASSWORD}") {{
        sessionStorage.setItem("rann_session_active", "valid");
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockApp();
        return;
      }}
      if (user === "durhampol" && pwd === "{PAGE_PASSWORD}") {{
        sessionStorage.setItem("durham_pol_auth", "granted");
        try {{
          localStorage.setItem("rann_auth_user", JSON.stringify({{
            username: "durhampol", fullName: "Durham Politics Guest",
            privilegeLevel: 2, privilegeName: "Standard Member", allowedPages: ["/durhampolitics"]
          }}));
        }} catch(ex) {{}}
        touchActivity();
        unlockApp();
        return;
      }}

      const approved = await verifyApprovedDurhamUser(user, pwd);
      if (approved) {{
        // Strictly scope approved users to /durhampolitics/ ONLY (never grant master session)
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.setItem("durham_pol_auth", "granted");
        try {{
          localStorage.setItem("rann_auth_user", JSON.stringify({{
            username: approved.username,
            fullName: approved.full_name || approved.username,
            email: approved.email || "",
            privilegeLevel: 2,
            privilegeName: "Standard Member",
            allowedPages: ["/durhampolitics"]
          }}));
        }} catch(ex) {{}}
        touchActivity();
        unlockApp();
      }} else {{
        const err = document.getElementById("authErrorMsg");
        err.style.display = "block";
        err.innerText = "Invalid username/password, or account is still pending approval.";
        document.getElementById("authPasswordInput").focus();
      }}
    }}

    function unlockApp() {{
      document.getElementById("authOverlay").style.display = "none";
      document.getElementById("appWrapper").style.display = "flex";
      initApplication();
    }}

    function lockApp(reason) {{
      sessionStorage.removeItem("rann_session_active");
      sessionStorage.removeItem("durham_pol_auth");
      try {{ localStorage.removeItem("durham_pol_auth"); }} catch(e) {{}}
      document.getElementById("appWrapper").style.display = "none";
      document.getElementById("authOverlay").style.display = "flex";
      document.getElementById("authPasswordInput").value = "";
      document.getElementById("authErrorMsg").style.display = "none";
      showToast(reason || "🔒 Session timed out after 1 hour of idle time.");
    }}

    function showToast(msg) {{
      const t = document.getElementById("toast");
      t.innerText = msg;
      t.style.display = "block";
      setTimeout(() => {{ t.style.display = "none"; }}, 3000);
    }}

    // ----------------------------------------------------
    // Tab Navigation
    // ----------------------------------------------------
    function switchTab(tabId) {{
      const panes = document.querySelectorAll(".tab-pane");
      panes.forEach(p => p.classList.remove("active"));
      
      const btns = document.querySelectorAll(".tab-btn");
      btns.forEach(b => b.classList.remove("active"));

      const targetPane = document.getElementById(`tab_${{tabId}}`);
      if (targetPane) targetPane.classList.add("active");

      // Set active button
      event.currentTarget.classList.add("active");

      if (tabId === "alignments") {{
        const bodySelect = document.getElementById("alignmentBodySelect").value;
        renderPairwiseHeatmap(bodySelect);
      }}
    }}

    // ----------------------------------------------------
    // Consent Agenda Filtering & Dynamic Stat Recomputation
    // ----------------------------------------------------
    let includeConsentAgenda = false;

    function isBlanketConsentAgendaVote(v) {{
      const title = (v.item_title || "").toLowerCase();
      const mtype = (v.motion_type || "").toLowerCase();
      const notes = (v.notes || "").toLowerCase();
      const combined = title + " " + mtype + " " + notes;
      const isPulled = (
        /pulled\\s+(consent\\s+)?item/i.test(title) ||
        /pulled\\s+and\\s+approved/i.test(notes) ||
        /pulled\\s+for\\s+(separate|discussion)/i.test(notes) ||
        /^approval of pulled/i.test(title) ||
        /^approve pulled/i.test(title)
      );
      if (isPulled) return false;
      return (
        combined.includes("consent agenda") ||
        combined.includes("settle the agenda") ||
        combined.includes("settle agenda") ||
        combined.includes("settlement of the agenda") ||
        combined.includes("settle and adopt meeting agenda")
      );
    }}

    function getVisibleVotes(votes) {{
      const arr = votes || [];
      return includeConsentAgenda ? arr : arr.filter(v => !isBlanketConsentAgendaVote(v));
    }}

    const MEMBER_ALIASES = {{
      "matt_kopac": ["kopac", "kopack", "kopacek", "kopec", "kobec", "kubic", "copac", "copack", "copak", "copek", "corbett"],
      "shanetta_burris": ["burris", "burrus", "burries", "burus", "barris", "barriss", "burgess", "boris"],
      "carl_rist": ["rist", "rrist", "ris", "ree", "reese", "wrist", "rynkiewicz"],
      "javiera_caballero": ["caballero", "cababiero", "cabayro", "cabayo", "cayetano", "cavayto", "cáviero", "clavijo", "fayto", "javier", "javiera", "mayor pro tem"],
      "nate_baker": ["baker", "bigger"],
      "chelsea_cook": ["cook"],
      "leonardo_williams": ["williams", "leonardo"],
      "nida_allam": ["allam", "alam", "alum", "alom", "lom", "long", "nida"],
      "stephen_valentine": ["valentine"],
      "mike_lee": ["mike lee", "chair lee", "dr. lee", "dr lee"],
      "michelle_burton": ["burton"],
      "wendy_jacobs": ["jacobs"],
      "joy_harrell_goff": ["harrell-goff", "harrell goff", "herald goff", "goff"],
      "xavier_cason": ["cason", "xavier"],
      "natalie_bent_kitaif": ["kitaif", "bent kitaif"],
      "nadeen_bir": ["nadeen bir", "nadine bir", "ms bir", "ms. bir", "bir"],
      "gabby_rivero": ["rivero", "gabby"],
      "wendell_tabb": ["tabb", "wendell"],
      "millicent_rogers": ["rogers", "millicent"]
    }};

    function realVoteNames(arr) {{
      return (arr || []).filter(x => x && !/^(none|n\\/a|na|0|null|-)$/i.test(String(x).trim()));
    }}

    function isGenericUnanimousAyes(v) {{
      const nays = realVoteNames(v.nays);
      const abst = realVoteNames(v.abstentions);
      if (nays.length > 0 || abst.length > 0) return false;
      const ayes = realVoteNames(v.ayes);
      if (ayes.length === 0) return true;
      if (/unanimous|7-0|6-0-0|5-0-0|5-0/i.test(v.tally || "")) return true;
      return ayes.some(x => /all\\s+(present|members|commissioners|council|board)|board\\s+members|unanimous|supporting|and\\s+others|^\\d+\\s+commissioners|^council\\s+members$/i.test(x.trim()));
    }}

    function memberMatchesVoteList(nameList, member) {{
      const cleanName = member.name.replace(/^Dr\\.?\\s+/i, "").replace(/\\([^)]*\\)/g, "").replace(/\\s+/g, " ").trim().toLowerCase();
      const parts = cleanName.split(" ").filter(Boolean);
      const last = parts[parts.length - 1] || "";
      const aliases = MEMBER_ALIASES[member.id] || [];
      return realVoteNames(nameList).some(n => {{
        const nl = n.toLowerCase();
        if (nl.includes(cleanName)) return true;
        if (last.length >= 4 && nl.includes(last)) return true;
        return aliases.some(a => a.length >= 4 ? nl.includes(a) : new RegExp(`\\\\b${{a}}\\\\b`, "i").test(nl));
      }});
    }}

    function recomputeVoteStats() {{
      let totalVotes = 0;
      let contestedVotes = 0;

      // Reset member counters
      const memberMap = {{}};
      APP_DATA.stats.members.forEach(mem => {{
        mem.ayes = 0;
        mem.nays = 0;
        mem.abstains = 0;
        mem.votes_cast = 0;
        mem.dissents_count = 0;
        memberMap[mem.id] = mem;
      }});

      // Pairwise counters per body
      const pairwiseAgree = {{}};
      const pairwiseTotal = {{}};
      Object.keys(APP_DATA.stats.pairwise || {{}}).forEach(b => {{
        pairwiseAgree[b] = {{}};
        pairwiseTotal[b] = {{}};
      }});

      APP_DATA.meetings.forEach(m => {{
        const visVotes = getVisibleVotes(m.votes);
        totalVotes += visVotes.length;
        contestedVotes += visVotes.filter(v => v.is_contested).length;

        const bodyMembers = APP_DATA.stats.members.filter(mem => mem.body_id === m.body_id);
        const currentBodyMembers = bodyMembers.filter(mem => mem.is_current);
        visVotes.forEach(v => {{
          const outcomePassed = (v.outcome || "").toLowerCase().includes("pass");
          const genericAyes = outcomePassed && isGenericUnanimousAyes(v);
          const castById = {{}};
          bodyMembers.forEach(mem => {{
            if (memberMatchesVoteList(v.nays, mem)) {{
              mem.nays += 1;
              mem.votes_cast += 1;
              if (outcomePassed) mem.dissents_count += 1;
              castById[mem.id] = "NAY";
            }} else if (memberMatchesVoteList(v.abstentions, mem)) {{
              mem.abstains += 1;
              mem.votes_cast += 1;
              castById[mem.id] = "ABSTAIN";
            }} else if (memberMatchesVoteList(v.ayes, mem) || (genericAyes && mem.is_current)) {{
              mem.ayes += 1;
              mem.votes_cast += 1;
              castById[mem.id] = "AYE";
            }}
          }});

          const ids = Object.keys(castById);
          for (let i = 0; i < ids.length; i++) {{
            for (let j = i + 1; j < ids.length; j++) {{
              const id1 = ids[i], id2 = ids[j];
              pairwiseTotal[m.body_id][id1] = pairwiseTotal[m.body_id][id1] || {{}};
              pairwiseTotal[m.body_id][id2] = pairwiseTotal[m.body_id][id2] || {{}};
              pairwiseAgree[m.body_id][id1] = pairwiseAgree[m.body_id][id1] || {{}};
              pairwiseAgree[m.body_id][id2] = pairwiseAgree[m.body_id][id2] || {{}};

              pairwiseTotal[m.body_id][id1][id2] = (pairwiseTotal[m.body_id][id1][id2] || 0) + 1;
              pairwiseTotal[m.body_id][id2][id1] = (pairwiseTotal[m.body_id][id2][id1] || 0) + 1;
              if (castById[id1] === castById[id2]) {{
                pairwiseAgree[m.body_id][id1][id2] = (pairwiseAgree[m.body_id][id1][id2] || 0) + 1;
                pairwiseAgree[m.body_id][id2][id1] = (pairwiseAgree[m.body_id][id2][id1] || 0) + 1;
              }}
            }}
          }}
        }});
      }});

      const unanimousVotes = totalVotes - contestedVotes;
      APP_DATA.stats.overall.total_votes = totalVotes;
      APP_DATA.stats.overall.contested_votes = contestedVotes;
      APP_DATA.stats.overall.unanimous_votes = unanimousVotes;
      APP_DATA.stats.overall.unanimous_pct = totalVotes > 0 ? Math.round((unanimousVotes / totalVotes) * 1000) / 10 : 0.0;

      APP_DATA.stats.members.forEach(mem => {{
        mem.aye_pct = mem.votes_cast > 0 ? Math.round((mem.ayes / mem.votes_cast) * 1000) / 10 : 0.0;
        mem.nay_pct = mem.votes_cast > 0 ? Math.round((mem.nays / mem.votes_cast) * 1000) / 10 : 0.0;
        mem.dissent_rate = mem.votes_cast > 0 ? Math.round((mem.dissents_count / mem.votes_cast) * 1000) / 10 : 0.0;
      }});

      Object.keys(APP_DATA.stats.pairwise || {{}}).forEach(b => {{
        const bMems = APP_DATA.stats.members.filter(mem => mem.body_id === b);
        bMems.forEach(m1 => {{
          APP_DATA.stats.pairwise[b][m1.id] = APP_DATA.stats.pairwise[b][m1.id] || {{}};
          bMems.forEach(m2 => {{
            if (m1.id === m2.id) {{
              APP_DATA.stats.pairwise[b][m1.id][m2.id] = 100.0;
            }} else {{
              const tot = (pairwiseTotal[b][m1.id] && pairwiseTotal[b][m1.id][m2.id]) || 0;
              if (tot === 0) {{
                APP_DATA.stats.pairwise[b][m1.id][m2.id] = null;
              }} else {{
                const agr = (pairwiseAgree[b][m1.id] && pairwiseAgree[b][m1.id][m2.id]) || 0;
                APP_DATA.stats.pairwise[b][m1.id][m2.id] = Math.round((agr / tot) * 1000) / 10;
              }}
            }}
          }});
        }});
      }});
    }}

    function toggleConsentAgenda(checked) {{
      includeConsentAgenda = !!checked;
      recomputeVoteStats();
      applyStatsKPIs();
      renderOverviewLandmarks();
      renderMembers();
      renderBodyTabs();
      const bodySelect = document.getElementById("alignmentBodySelect") ? document.getElementById("alignmentBodySelect").value : "city";
      renderPairwiseHeatmap(bodySelect);
      renderDissentLeaderboard();
      renderTimeline();
    }}

    // ----------------------------------------------------
    // App Initialization
    // ----------------------------------------------------
    function initApplication() {{
      recomputeVoteStats();
      applyStatsKPIs();
      renderOverviewLandmarks();
      renderMembers();
      renderBodyTabs();
      renderPairwiseHeatmap("city");
      renderDissentLeaderboard();
      renderTimeline();
      pollLiveMeetingStatus();
      setInterval(pollLiveMeetingStatus, 15000);
    }}

    async function pollLiveMeetingStatus() {{
      const btn = document.getElementById("liveMeetingTabBtn");
      const pill = document.getElementById("liveMeetingPill");
      if (!btn) return;
      try {{
        const res = await fetch("/durhampolitics/live_status.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) {{
          btn.style.display = "none";
          return;
        }}
        const data = await res.json();
        if (data && data.is_live) {{
          btn.style.display = "inline-flex";
          const bAcronym = data.body_id === "dps" ? "DPS" : data.body_id === "city" ? "CITY" : data.body_id === "bocc" ? "BOCC" : "LIVE";
          if (pill) pill.innerText = "LIVE • " + bAcronym;
          btn.title = data.title || "Live Meeting in Progress";
        }} else {{
          btn.style.display = "none";
        }}
      }} catch (e) {{
        btn.style.display = "none";
      }}
    }}

    function applyStatsKPIs() {{
      const s = APP_DATA.stats.overall;
      document.getElementById("kpiTotalMeetings").innerText = s.total_meetings;
      document.getElementById("kpiTotalVotes").innerText = s.total_votes;
      document.getElementById("kpiContestedVotes").innerText = s.contested_votes;
      document.getElementById("kpiUnanimousPct").innerText = `${{s.unanimous_pct}}% Unanimous Consensus`;
      document.getElementById("kpiTotalDisagreements").innerText = s.total_disagreements;
    }}

    function renderOverviewLandmarks() {{
      const container = document.getElementById("overviewLandmarkVotes");
      container.innerHTML = "";

      // Gather contested or key landmark votes
      const landmarkMeetings = APP_DATA.meetings.filter(m => m.votes.some(v => v.is_contested || v.item_title.includes("Budget")));
      landmarkMeetings.slice(0, 5).forEach(m => {{
        container.appendChild(createMeetingElement(m));
      }});
    }}

    function renderBodyTabs() {{
      // DPS (Current Seated Members)
      const dpsMembers = APP_DATA.stats.members.filter(m => m.body_id === "dps" && m.is_current);
      document.getElementById("dpsMembersGrid").innerHTML = dpsMembers.map(createMemberCardHTML).join("");
      const dpsMeetings = APP_DATA.meetings.filter(m => m.body_id === "dps");
      const dpsTimeline = document.getElementById("dpsMeetingsTimeline");
      dpsTimeline.innerHTML = "";
      dpsMeetings.forEach(m => dpsTimeline.appendChild(createMeetingElement(m)));

      // City Council (Current Seated Members)
      const cityMembers = APP_DATA.stats.members.filter(m => m.body_id === "city" && m.is_current);
      document.getElementById("cityMembersGrid").innerHTML = cityMembers.map(createMemberCardHTML).join("");
      const cityMeetings = APP_DATA.meetings.filter(m => m.body_id === "city");
      const cityTimeline = document.getElementById("cityMeetingsTimeline");
      cityTimeline.innerHTML = "";
      cityMeetings.forEach(m => cityTimeline.appendChild(createMeetingElement(m)));

      // BOCC (Current Seated Members)
      const boccMembers = APP_DATA.stats.members.filter(m => m.body_id === "bocc" && m.is_current);
      document.getElementById("boccMembersGrid").innerHTML = boccMembers.map(createMemberCardHTML).join("");
      const boccMeetings = APP_DATA.meetings.filter(m => m.body_id === "bocc");
      const boccTimeline = document.getElementById("boccMeetingsTimeline");
      boccTimeline.innerHTML = "";
      boccMeetings.forEach(m => boccTimeline.appendChild(createMeetingElement(m)));
    }}

    function renderMembers() {{
      const bodyFilter = document.getElementById("memberFilterBody").value;
      const statusFilter = document.getElementById("memberFilterStatus").value;

      let list = APP_DATA.stats.members;
      if (bodyFilter !== "all") {{
        list = list.filter(m => m.body_id === bodyFilter);
      }}
      if (statusFilter === "current") {{
        list = list.filter(m => m.is_current);
      }} else if (statusFilter === "former") {{
        list = list.filter(m => !m.is_current);
      }}

      document.getElementById("allMembersGrid").innerHTML = list.map(createMemberCardHTML).join("");
    }}

    function createMemberCardHTML(m) {{
      const bColor = m.body_id === "dps" ? "var(--dps-color)" : m.body_id === "city" ? "var(--city-color)" : "var(--bocc-color)";
      const bName = m.body_id === "dps" ? "DPS Board" : m.body_id === "city" ? "City Council" : "BOCC";

      const termStr = m.active_terms ? m.active_terms.join(", ") : "";

      const tagsHTML = (m.ideology_tags || []).map(t => `<span class="tag tag-ideology">${{t}}</span>`).join("");
      const priorityHTML = (m.key_priorities || []).map(p => `<span class="tag">${{p}}</span>`).join("");

      return `
        <div class="member-card">
          <div>
            <div class="member-header">
              <div class="member-avatar" style="border: 2px solid ${{bColor}};">${{m.avatar_initials}}</div>
              <div class="member-info">
                <h3>${{m.name}}</h3>
                <p style="color: ${{bColor}}; font-weight: 600;">${{m.title}} &bull; ${{m.district}}</p>
                <p style="font-size: 11px;">${{termStr}}</p>
              </div>
            </div>

            <div class="member-stats">
              <div>
                <div class="stat-box-num">${{m.votes_cast}}</div>
                <div class="stat-box-lbl">Votes Cast</div>
              </div>
              <div>
                <div class="stat-box-num" style="color: #6ee7b7;">${{m.aye_pct}}%</div>
                <div class="stat-box-lbl">Aye Rate</div>
              </div>
              <div>
                <div class="stat-box-num" style="color: #fca5a5;">${{m.dissent_rate}}%</div>
                <div class="stat-box-lbl">Dissent Rate</div>
              </div>
            </div>

            <p style="font-size: 12px; color: var(--text-muted); line-height: 1.5; margin-bottom: 8px;">${{m.bio || ""}}</p>

            <div class="tag-container">${{tagsHTML}}</div>
            <div class="tag-container" style="margin-top: 4px;">${{priorityHTML}}</div>
          </div>

          <button class="btn-view-record" onclick="openMemberRecord('${{m.id}}')">
            Inspect Full Voting Record &rarr;
          </button>
        </div>
      `;
    }}

    function openMemberRecord(memberId) {{
      const member = APP_DATA.stats.members.find(m => m.id === memberId);
      if (!member) return;

      document.getElementById("modalMemberTitle").innerText = `${{member.name}} — Complete Voting History`;

      // Find all votes where this member cast a vote
      let votesHTML = "";
      APP_DATA.meetings.forEach(m => {{
        getVisibleVotes(m.votes).forEach(v => {{
          const outcomePassed = (v.outcome || "").toLowerCase().includes("pass");
          const genericAyes = m.body_id === member.body_id && member.is_current && outcomePassed && isGenericUnanimousAyes(v);
          const isNay = memberMatchesVoteList(v.nays, member);
          const isAbstain = !isNay && memberMatchesVoteList(v.abstentions, member);
          const isAye = !isNay && !isAbstain && (memberMatchesVoteList(v.ayes, member) || genericAyes);

          if (isAye || isNay || isAbstain) {{
            const badgeClass = isAye ? "vote-badge-passed" : isNay ? "vote-badge-failed" : "tag";
            const castText = isAye ? "AYE (IN FAVOR)" : isNay ? "NAY (DISSENT)" : "ABSTAIN";

            const tsLink = v.video_timestamp_url && v.timestamp_label
              ? `<a href="${{v.video_timestamp_url}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;margin-left:8px;white-space:nowrap;">&#9658; ${{v.timestamp_label}}</a>`
              : (m.video_url ? `<a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;margin-left:8px;white-space:nowrap;">&#9658; Video</a>` : "");

            votesHTML += `
              <div class="vote-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span style="font-size: 11px; color: var(--text-dim);">${{m.date}} &bull; ${{m.title}}${{tsLink}}</span>
                  <span class="${{badgeClass}}">${{castText}}</span>
                </div>
                <div class="vote-title">${{v.item_title}}</div>
                <div class="vote-breakdown">
                  Outcome: <strong>${{v.outcome}}</strong> (${{v.tally}}) | Mover: ${{v.mover || 'N/A'}} | Seconder: ${{v.seconder || 'N/A'}}
                </div>
                ${{v.notes ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">${{v.notes}}</div>` : ''}}
              </div>
            `;
          }}
        }});
      }});

      if (!votesHTML) {{
        votesHTML = `<div style="color: var(--text-muted); font-size: 13px;">No recorded roll call votes on file for this session window.</div>`;
      }}

      document.getElementById("modalMemberBody").innerHTML = votesHTML;
      document.getElementById("recordModal").style.display = "flex";
    }}

    function closeRecordModal() {{
      document.getElementById("recordModal").style.display = "none";
    }}

    // Close modal on click outside
    window.onclick = function(e) {{
      const m = document.getElementById("recordModal");
      if (e.target === m) {{
        m.style.display = "none";
      }}
    }};

    // ----------------------------------------------------
    // Meeting Elements & Timeline
    // ----------------------------------------------------
    function createMeetingElement(m) {{
      const el = document.createElement("div");
      el.className = "meeting-card";

      const bColor = m.body_id === "dps" ? "dps" : m.body_id === "city" ? "city" : "bocc";
      const bLabel = m.body_id === "dps" ? "DPS Board" : m.body_id === "city" ? "City Council" : "BOCC";

      const visibleVotes = getVisibleVotes(m.votes);
      const contestedCount = visibleVotes.filter(v => v.is_contested).length;

      const agendaItems = m.agenda_items || [];
      let agendaListHTML = agendaItems.map(ag => {{
        const tsUrl = ag.video_timestamp_url || m.video_url || "";
        const tsBadge = tsUrl
          ? `<a href="${{tsUrl}}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:4px;background:rgba(37,99,235,0.2);color:#93c5fd;border:1px solid rgba(96,165,250,0.35);padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;text-decoration:none;white-space:nowrap;">&#9658; ${{ag.timestamp_label || 'Watch'}}</a>`
          : "";
        const titleLink = tsUrl
          ? `<a href="${{tsUrl}}" target="_blank" rel="noopener noreferrer" style="color:#f8fafc;text-decoration:none;">${{ag.item_number ? ag.item_number + ': ' : ''}}${{ag.title}}</a>`
          : `${{ag.item_number ? ag.item_number + ': ' : ''}}${{ag.title}}`;
        return `
          <div class="vote-item">
            <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 4px; flex-wrap: wrap;">
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                ${{tsBadge}}
                <span style="font-size: 11px; color: var(--text-dim);">${{ag.category || 'General'}}</span>
              </div>
            </div>
            <div class="vote-title">${{titleLink}}</div>
            ${{ag.discussion_summary ? `<div class="vote-breakdown" style="margin-top:4px;color:var(--text-muted);">${{ag.discussion_summary}}</div>` : ''}}
            ${{ag.vote_summary ? `<div class="vote-breakdown" style="margin-top:4px;color:#a7f3d0;"><strong>Action / Vote:</strong> ${{ag.vote_summary}}</div>` : ''}}
          </div>
        `;
      }}).join("");

      let votesListHTML = visibleVotes.map(v => {{
        const vUrl = v.video_timestamp_url || m.video_url || "";
        const vTsLink = vUrl && v.timestamp_label
          ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; ${{v.timestamp_label}}</a>`
          : (vUrl ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; Video</a>` : "");
        return `
        <div class="vote-item">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; flex-wrap: wrap; gap: 6px;">
            <div>
              <span class="${{v.outcome.toLowerCase().includes('pass') ? 'vote-badge-passed' : 'vote-badge-failed'}}">
                ${{v.outcome}} (${{v.tally}})
              </span>
              ${{vTsLink}}
            </div>
            <span style="font-size: 11px; color: var(--text-dim);">${{v.category || 'General'}}</span>
          </div>
          <div class="vote-title">${{vUrl ? `<a href="${{vUrl}}" target="_blank" rel="noopener noreferrer" style="color:#f8fafc;text-decoration:none;">${{v.item_title}}</a>` : v.item_title}}</div>
          ${{v.discussion_detail ? `<div class="vote-breakdown" style="margin-top:6px;margin-bottom:6px;color:#cbd5e1;line-height:1.5;"><strong>Discussion:</strong> ${{v.discussion_detail}}</div>` : ''}}
          <div class="vote-breakdown">
            <strong>Mover:</strong> ${{v.mover || 'N/A'}} | <strong>Seconder:</strong> ${{v.seconder || 'N/A'}} | <strong>Format:</strong> ${{v.vote_format}}
          </div>
          <div class="vote-breakdown">
            <strong>Ayes:</strong> ${{v.ayes.join(', ') || 'None'}}
          </div>
          ${{v.nays && v.nays.length ? `<div class="vote-breakdown" style="color: #fca5a5;"><strong>Nays:</strong> ${{v.nays.join(', ')}}</div>` : ''}}
          ${{v.amendments && v.amendments.length ? `<div class="vote-breakdown" style="color: #93c5fd;"><strong>Amendments:</strong> ${{v.amendments.join('; ')}}</div>` : ''}}
          ${{v.notes ? `<div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">${{v.notes}}</div>` : ''}}
        </div>
      `;
      }}).join("");

      let disagreementsListHTML = (m.disagreements || []).map(d => {{
        const dUrl = d.video_timestamp_url || m.video_url || "";
        const dTsLink = dUrl && d.timestamp_label
          ? ` <a href="${{dUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; ${{d.timestamp_label}}</a>`
          : (dUrl ? ` <a href="${{dUrl}}" target="_blank" rel="noopener noreferrer" style="color:#60a5fa;text-decoration:none;font-size:11px;font-weight:600;margin-left:8px;">&#9658; Watch</a>` : "");
        return `
        <div class="disagreement-box">
          <div class="dis-title">&#9888; Deliberation Contention: ${{d.issue}}${{dTsLink}}</div>
          <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">${{d.summary}}</p>
          <div class="dis-side">
            <strong style="color: #93c5fd;">Side A (${{d.side_a.position}}):</strong>
            ${{(d.side_a.arguments || []).join(' &bull; ')}}
            <div style="font-size: 11px; color: var(--text-dim);">Members: ${{d.side_a.members.join(', ')}}</div>
          </div>
          <div class="dis-side" style="margin-top: 6px;">
            <strong style="color: #fca5a5;">Side B (${{d.side_b.position}}):</strong>
            ${{(d.side_b.arguments || []).join(' &bull; ')}}
            <div style="font-size: 11px; color: var(--text-dim);">Members: ${{d.side_b.members.join(', ')}}</div>
          </div>
          <div style="font-size: 11px; color: #a7f3d0; margin-top: 6px;">
            <strong>Resolution:</strong> ${{d.resolution}}
          </div>
        </div>
      `;
      }}).join("");

      const meetingTitleHTML = m.video_url
        ? `<a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" style="color:inherit;text-decoration:none;">${{m.title}}</a>`
        : m.title;

      el.innerHTML = `
        <div class="meeting-header">
          <div>
            <span class="badge-body ${{bColor}}">${{bLabel}}</span>
            <span style="font-size: 12px; color: var(--text-muted); margin-left: 8px;">${{m.date}}</span>
            <span style="font-size: 12px; color: var(--text-dim); margin-left: 8px;">&bull; Duration: ${{m.duration || '2h+'}}</span>
            ${{m.presiding_chair ? `<span style="font-size: 12px; color: var(--text-dim); margin-left: 8px;">&bull; Presided by ${{m.presiding_chair}}</span>` : ''}}
          </div>
          <div>
            ${{contestedCount > 0 ? `<span class="vote-badge-failed">${{contestedCount}} Contested Roll Calls</span>` : `<span class="vote-badge-passed">Consensual</span>`}}
          </div>
        </div>

        <div class="meeting-title">${{meetingTitleHTML}}</div>
        <div class="meeting-summary">${{m.executive_summary || ''}}</div>

        <div class="meeting-details-toggle">
          ${{agendaItems.length ? `
            <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_agenda', this)">
              <span>&#128203;</span> Agenda Topics &amp; Timestamps (${{agendaItems.length}})
            </button>
          ` : ''}}
          <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_votes', this)">
            <span>&#9745;</span> Roll Call Votes (${{visibleVotes.length}})
          </button>
          ${{m.disagreements && m.disagreements.length ? `
            <button class="btn-toggle-details" onclick="toggleDetailsPane('${{m.id}}_dis', this)">
              <span>&#9878;</span> Debates & Disagreements (${{m.disagreements.length}})
            </button>
          ` : ''}}
          ${{m.video_url ? `
            <a href="${{m.video_url}}" target="_blank" rel="noopener noreferrer" class="btn-toggle-details" style="text-decoration: none;">
              <span>&#9658;</span> Watch Video Recording
            </a>
          ` : ''}}
          ${{m.summary_pdf_url ? `
            <a href="${{m.summary_pdf_url}}" target="_blank" rel="noopener noreferrer" class="btn-toggle-details" style="text-decoration: none; border-color: rgba(16,185,129,0.45); color: #6ee7b7;">
              <span>&#128196;</span> Executive Summary PDF
            </a>
          ` : ''}}
        </div>

        <div id="${{m.id}}_agenda" class="details-pane">
          ${{agendaListHTML || '<div style="font-size: 12px; color: var(--text-muted);">No timestamped agenda breakdown available.</div>'}}
        </div>

        <div id="${{m.id}}_votes" class="details-pane">
          ${{votesListHTML || '<div style="font-size: 12px; color: var(--text-muted);">No formal roll-call votes recorded.</div>'}}
        </div>

        <div id="${{m.id}}_dis" class="details-pane">
          ${{disagreementsListHTML}}
        </div>
      `;

      return el;
    }}

    function toggleDetailsPane(paneId, btn) {{
      const pane = document.getElementById(paneId);
      if (!pane) return;
      if (pane.style.display === "block") {{
        pane.style.display = "none";
        btn.style.background = "#1e293b";
      }} else {{
        pane.style.display = "block";
        btn.style.background = "#334155";
      }}
    }}

    function renderTimeline() {{
      const bodyFilter = document.getElementById("timelineFilterBody").value;
      const yearFilter = document.getElementById("timelineFilterYear").value;
      const contestedFilter = document.getElementById("timelineFilterContested").value;

      let list = APP_DATA.meetings;
      if (bodyFilter !== "all") {{
        list = list.filter(m => m.body_id === bodyFilter);
      }}
      if (yearFilter !== "all") {{
        list = list.filter(m => m.date.startsWith(yearFilter));
      }}
      if (contestedFilter === "contested") {{
        list = list.filter(m => m.votes.some(v => v.is_contested));
      }}

      const container = document.getElementById("masterTimelineList");
      container.innerHTML = "";
      list.forEach(m => container.appendChild(createMeetingElement(m)));
    }}

    // ----------------------------------------------------
    // Heatmaps & Alignment Grids
    // ----------------------------------------------------
    function renderPairwiseHeatmap(bodyId) {{
      const matrix = APP_DATA.stats.pairwise[bodyId];
      if (!matrix) return;

      const members = APP_DATA.stats.members.filter(m => m.body_id === bodyId && m.is_current);
      const memberIds = members.map(m => m.id);

      let html = `<table class="heatmap-table"><thead><tr><th>Official</th>`;
      members.forEach(m => {{
        const colLabel = /^Dr\\.?\\s+/i.test(m.name) ? m.name : m.name.split(" ")[0];
        html += `<th>${{colLabel}}</th>`;
      }});
      html += `</tr></thead><tbody>`;

      members.forEach((m1, i) => {{
        html += `<tr><th>${{m1.name}}</th>`;
        members.forEach((m2, j) => {{
          if (j < i) {{
            html += `<td class="heat-self" style="background: transparent; border-color: transparent;"></td>`;
          }} else if (i === j) {{
            html += `<td class="heat-self">100%</td>`;
          }} else {{
            const score = (matrix[m1.id] && matrix[m1.id][m2.id] !== undefined) ? matrix[m1.id][m2.id] : null;
            if (score === null) {{
              html += `<td class="heat-self">&mdash;</td>`;
            }} else {{
              const cls = score >= 95 ? "heat-high" : score >= 90 ? "heat-med" : "heat-low";
              html += `<td class="${{cls}}">${{score}}%</td>`;
            }}
          }}
        }});
        html += `</tr>`;
      }});

      html += `</tbody></table>`;
      document.getElementById("heatmapContainer").innerHTML = html;
      renderDissentLeaderboard(bodyId);
    }}

    function renderDissentLeaderboard(bodyId) {{
      const selectedBody = bodyId || (document.getElementById("alignmentBodySelect") ? document.getElementById("alignmentBodySelect").value : "city");
      const boardNames = {{
        dps: "DPS Board of Education",
        city: "Durham City Council",
        bocc: "Durham County Commissioners (BOCC)"
      }};
      const titleEl = document.getElementById("dissentLeaderboardTitle");
      if (titleEl) {{
        titleEl.innerText = `Dissent Frequency Leaderboard — ${{boardNames[selectedBody] || selectedBody.toUpperCase()}}`;
      }}

      const sorted = APP_DATA.stats.members
        .filter(m => m.body_id === selectedBody && m.is_current && m.votes_cast > 0)
        .sort((a, b) => (b.dissent_rate - a.dissent_rate) || (b.dissents_count - a.dissents_count) || a.name.localeCompare(b.name));

      let html = `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;">`;
      sorted.forEach(m => {{
        const bLabel = m.body_id === "dps" ? "DPS Board" : m.body_id === "city" ? "City Council" : "BOCC";
        html += `
          <div style="background: var(--card-inner); padding: 12px 16px; border-radius: 8px; border: 1px solid #232d42;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div>
                <strong style="color: #fff; font-size: 14px;">${{m.name}}</strong>
                <div style="font-size: 11px; color: var(--text-dim);">${{bLabel}} &bull; ${{m.title}}</div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 18px; font-weight: 800; color: #fca5a5;">${{m.dissent_rate}}%</div>
                <div style="font-size: 10px; color: var(--text-dim); text-transform: uppercase;">${{m.dissents_count}}/${{m.votes_cast}} Dissent</div>
              </div>
            </div>
            <div style="font-size: 11px; color: var(--text-muted); margin-top: 8px;">
              Primary areas of dissent: ${{m.key_priorities.slice(0, 2).join(', ')}}
            </div>
          </div>
        `;
      }});
      html += `</div>`;
      document.getElementById("dissentLeaderboard").innerHTML = html;
    }}

    // Global Search Function
    function handleGlobalSearch(query) {{
      const q = query.toLowerCase().trim();
      if (!q) {{
        renderTimeline();
        renderMembers();
        return;
      }}

      // Switch to timeline tab automatically if search entered
      const matchingMeetings = APP_DATA.meetings.filter(m => 
        m.title.toLowerCase().includes(q) ||
        m.executive_summary.toLowerCase().includes(q) ||
        m.votes.some(v => v.item_title.toLowerCase().includes(q) || v.notes.toLowerCase().includes(q)) ||
        (m.disagreements || []).some(d => d.issue.toLowerCase().includes(q) || d.summary.toLowerCase().includes(q))
      );

      const container = document.getElementById("masterTimelineList");
      container.innerHTML = `<div style="font-size: 13px; color: var(--accent-blue); margin-bottom: 12px;">Found ${{matchingMeetings.length}} matching meeting records for "${{query}}":</div>`;
      matchingMeetings.forEach(m => container.appendChild(createMeetingElement(m)));

      // Switch to timeline tab
      const panes = document.querySelectorAll(".tab-pane");
      panes.forEach(p => p.classList.remove("active"));
      document.getElementById("tab_timeline").classList.add("active");
    }}

    // Check auth on load
    window.addEventListener("DOMContentLoaded", checkAuth);
  </script>
</body>
</html>
"""

    with open(HTML_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    # Also keep /durhampolitics.html in sync for extensionless URLs without trailing slash
    flat_html_path = HTML_OUTPUT_PATH.parent.parent / "durhampolitics.html"
    if flat_html_path.parent.exists():
        with open(flat_html_path, "w", encoding="utf-8") as f:
            f.write(html)

    # Generate dedicated Live Meeting split-pane page & default status JSON
    generate_live_meeting_page()

    print(f"✓ Standalone private web app generated at: {HTML_OUTPUT_PATH}")
    print(f"  - Password protected with 'durhampol' & master password")
    print(f"  - Anti-crawler robots meta tags included")
    print(f"  - Exported dataset cached at: {DATA_EXPORT_PATH}")
    return str(HTML_OUTPUT_PATH)


def generate_live_meeting_page() -> str:
    """
    Generates /durhampolitics/live.html:
      - Left pane: Dynamically updating Executive Summary (updates every 60s)
      - Top-right pane: Embedded live video of the ongoing meeting
      - Bottom-right pane: Real-time running audio transcript (non-caption ASR)
    Also ensures /durhampolitics/live_status.json exists.
    """
    live_html_path = HTML_OUTPUT_PATH.parent / "live.html"
    live_status_path = HTML_OUTPUT_PATH.parent / "live_status.json"
    HTML_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not live_status_path.exists():
        live_status_path.write_text(json.dumps({
            "is_live": False,
            "body_id": None,
            "body_name": None,
            "video_id": None,
            "video_url": None,
            "title": None,
            "started_at": None,
            "summary_updated_at": None,
            "transcript_updated_at": None,
            "executive_summary": "",
            "topics_so_far": [],
            "votes_so_far": [],
            "debates_so_far": [],
            "transcript_lines": [],
            "source_mode": "realtime_audio_asr"
        }, indent=2), encoding="utf-8")

    live_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet">
  <title>Live Meeting in Progress | Durham Politics Tracker</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #070b14;
      --bg-surface: #0f1623;
      --bg-card: #151e30;
      --bg-elevated: #1c2841;
      --border: #23304c;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent: #3b82f6;
      --danger: #ef4444;
      --success: #10b981;
      --warn: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    #authOverlay {{
      position: fixed; inset: 0; z-index: 9999;
      background: radial-gradient(circle at top, #13203d 0%, #070b14 70%);
      display: flex; align-items: center; justify-content: center;
    }}
    .auth-card {{
      width: 100%; max-width: 400px; background: var(--bg-surface);
      border: 1px solid var(--border); border-radius: 14px; padding: 28px;
      box-shadow: 0 24px 60px rgba(0,0,0,0.6);
    }}
    .auth-card h2 {{ font-size: 18px; margin-bottom: 6px; }}
    .auth-card p {{ font-size: 13px; color: var(--text-muted); margin-bottom: 18px; }}
    .auth-input {{
      width: 100%; padding: 10px 12px; margin-bottom: 12px; border-radius: 8px;
      border: 1px solid var(--border); background: var(--bg-card); color: var(--text-main);
      font-size: 14px;
    }}
    .auth-btn {{
      width: 100%; padding: 10px 14px; border-radius: 8px; border: none;
      background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff;
      font-weight: 700; font-size: 14px; cursor: pointer;
    }}
    #liveApp {{
      display: none;
      flex-direction: column;
      height: 100vh;
      width: 100%;
    }}
    header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 20px; background: var(--bg-surface); border-bottom: 1px solid var(--border);
      gap: 12px; flex-shrink: 0; flex-wrap: wrap;
    }}
    .hdr-left {{ display: flex; align-items: center; gap: 12px; min-width: 0; }}
    .live-pill {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 800;
      background: rgba(239,68,68,0.2); color: #fca5a5; border: 1px solid rgba(239,68,68,0.45);
      text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
    }}
    .live-dot {{
      width: 8px; height: 8px; border-radius: 50%; background: #ef4444;
      box-shadow: 0 0 8px #ef4444; animation: pulse 1.4s infinite;
    }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
    .hdr-title {{ font-size: 15px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .hdr-right {{ display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--text-muted); }}
    .btn-back {{
      padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border);
      background: var(--bg-card); color: var(--text-main); text-decoration: none;
      font-size: 12px; font-weight: 600;
    }}
    .btn-back:hover {{ background: var(--bg-elevated); }}

    /* Split Layout: Left = Exec Summary, Top-Right = Video, Bottom-Right = Running Transcript */
    .split-grid {{
      flex: 1;
      display: grid;
      grid-template-columns: minmax(420px, 1.15fr) minmax(380px, 0.85fr);
      grid-template-rows: 1fr 1fr;
      gap: 12px;
      padding: 12px;
      min-height: 0;
    }}
    .pane {{
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      min-height: 0;
      overflow: hidden;
    }}
    .pane-left {{ grid-column: 1; grid-row: 1 / span 2; }}
    .pane-top-right {{ grid-column: 2; grid-row: 1; }}
    .pane-bottom-right {{ grid-column: 2; grid-row: 2; }}
    .pane-header {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 14px; background: var(--bg-card); border-bottom: 1px solid var(--border);
      font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
      color: #cbd5e1; flex-shrink: 0; gap: 8px;
    }}
    .pane-body {{ flex: 1; overflow-y: auto; padding: 16px; min-height: 0; }}
    .video-wrap {{ flex: 1; background: #000; position: relative; min-height: 0; }}
    .video-wrap iframe {{ position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }}
    .section-hdr {{
      font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;
      color: #60a5fa; margin: 16px 0 8px 0;
    }}
    .section-hdr:first-child {{ margin-top: 0; }}
    .exec-box {{
      background: var(--bg-card); border: 1px solid var(--border); border-left: 3px solid var(--accent);
      border-radius: 8px; padding: 14px; font-size: 13.5px; line-height: 1.6; color: #e2e8f0;
    }}
    .topic-card, .vote-card {{
      background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px;
      padding: 12px; margin-bottom: 10px;
    }}
    .topic-head {{
      display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 4px;
    }}
    .ts-chip {{
      display: inline-flex; align-items: center; gap: 4px; font-family: 'JetBrains Mono', monospace;
      font-size: 11px; font-weight: 600; color: #93c5fd; background: rgba(37,99,235,0.2);
      border: 1px solid rgba(96,165,250,0.35); border-radius: 999px; padding: 2px 8px;
      text-decoration: none;
    }}
    .transcript-line {{
      font-size: 12.5px; line-height: 1.5; padding: 5px 8px; border-radius: 6px;
      border-bottom: 1px solid rgba(35,48,76,0.45);
    }}
    .transcript-line:hover {{ background: rgba(59,130,246,0.08); }}
    .t-ts {{
      font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #60a5fa;
      margin-right: 8px; text-decoration: none;
    }}
    .empty-state {{
      height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center;
      text-align: center; color: var(--text-muted); gap: 10px; padding: 24px;
    }}
    @media (max-width: 960px) {{
      body {{ height: auto; overflow: auto; }}
      #liveApp {{ height: auto; }}
      .split-grid {{ grid-template-columns: 1fr; grid-template-rows: auto; }}
      .pane-left, .pane-top-right, .pane-bottom-right {{ grid-column: 1; grid-row: auto; min-height: 360px; }}
      .video-wrap {{ min-height: 280px; }}
    }}
  </style>
</head>
<body>
  <div id="authOverlay">
    <form class="auth-card" onsubmit="handleAuth(event)">
      <h2>Durham Politics Tracker — Live Feed</h2>
      <p>Enter credentials to access the real-time meeting dashboard.</p>
      <input id="authUser" class="auth-input" type="text" placeholder="Username" required>
      <input id="authPass" class="auth-input" type="password" placeholder="Password" required>
      <div id="authErr" style="color:#fca5a5;font-size:12px;margin-bottom:10px;display:none;">Invalid credentials or pending approval.</div>
      <button class="auth-btn" type="submit">Unlock Live Meeting</button>
      <div style="margin-top:12px;text-align:center;font-size:12px;color:var(--text-muted);">
        Need an account? <a href="/durhampolitics/signup.html" style="color:#60a5fa;text-decoration:none;font-weight:600;">Request Access &rarr;</a>
        &nbsp;&bull;&nbsp;
        <a href="/durhampolitics/docs.html" style="color:var(--text-muted);text-decoration:none;">Documentation</a>
      </div>
    </form>
  </div>

  <div id="liveApp">
    <header>
      <div class="hdr-left">
        <span class="live-pill" id="liveBadge"><span class="live-dot"></span> <span id="liveBadgeText">Checking...</span></span>
        <div class="hdr-title" id="liveTitle">Durham Local Government Live Meeting Monitor</div>
      </div>
      <div class="hdr-right">
        <span id="summaryStatus">Summary updates every 60s (Real-time Audio ASR)</span>
        <a href="/durhampolitics/docs.html" class="btn-back">&#128214; Docs</a>
        <a href="/durhampolitics/" class="btn-back">&larr; Back to Archive</a>
      </div>
    </header>

    <div class="split-grid">
      <!-- LEFT: Dynamically Updating Executive Summary -->
      <section class="pane pane-left">
        <div class="pane-header">
          <span>Executive Summary of Discussion So Far</span>
          <span id="summaryTimer" style="font-family:'JetBrains Mono',monospace;color:#6ee7b7;">Next update: 60s</span>
        </div>
        <div class="pane-body" id="summaryPane">
          <div class="empty-state">Waiting for live stream audio analysis...</div>
        </div>
      </section>

      <!-- TOP RIGHT: Live Video -->
      <section class="pane pane-top-right">
        <div class="pane-header">
          <span>Live Meeting Video</span>
          <a id="openYtLink" href="#" target="_blank" rel="noopener noreferrer" style="color:#93c5fd;text-decoration:none;display:none;">Open on YouTube &#8599;</a>
        </div>
        <div class="video-wrap" id="videoWrap">
          <div class="empty-state">No live video stream active right now.</div>
        </div>
      </section>

      <!-- BOTTOM RIGHT: Running Transcript -->
      <section class="pane pane-bottom-right">
        <div class="pane-header">
          <span>Running Transcript (Real-Time Video Audio ASR)</span>
          <div style="display:flex;align-items:center;gap:8px;">
            <input id="transcriptFilter" type="text" placeholder="Filter..." oninput="renderTranscript()" style="background:var(--bg-surface);border:1px solid var(--border);color:#fff;padding:3px 8px;border-radius:6px;font-size:11px;width:110px;">
            <label style="display:inline-flex;align-items:center;gap:4px;font-size:11px;text-transform:none;cursor:pointer;">
              <input id="autoScrollToggle" type="checkbox" checked> Auto-scroll
            </label>
          </div>
        </div>
        <div class="pane-body" id="transcriptPane" style="padding:10px;">
          <div class="empty-state">Real-time audio transcript will appear here once a meeting begins.</div>
        </div>
      </section>
    </div>
  </div>

  <script>
    const SHARED_ACTIVE_KEY = "rann_auth_last_active";
    const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
    let lastActiveMem = Date.now();
    let currentVideoId = null;
    let latestData = null;
    let secondsToSummaryRefresh = 60;

    function touchActivity() {{
      lastActiveMem = Date.now();
      try {{ localStorage.setItem(SHARED_ACTIVE_KEY, lastActiveMem.toString()); }} catch(e) {{}}
    }}
    function getLastActive() {{
      try {{
        const s = parseInt(localStorage.getItem(SHARED_ACTIVE_KEY) || "0", 10);
        return Math.max(s || 0, lastActiveMem);
      }} catch(e) {{ return lastActiveMem; }}
    }}
    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(ev => {{
      window.addEventListener(ev, () => touchActivity(), {{ passive: true }});
    }});
    setInterval(() => {{
      const isAuthed = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (isAuthed && (Date.now() - getLastActive() > INACTIVITY_TIMEOUT_MS)) {{
        sessionStorage.removeItem("rann_session_active");
        sessionStorage.removeItem("durham_pol_auth");
        document.getElementById("liveApp").style.display = "none";
        document.getElementById("authOverlay").style.display = "flex";
      }}
    }}, 5000);

    async function sha256Hex(str) {{
      const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
      return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
    }}

    async function handleAuth(e) {{
      e.preventDefault();
      const u = document.getElementById("authUser").value.trim().toLowerCase();
      const p = document.getElementById("authPass").value.trim();
      if (u === "rann" && p === "{MASTER_PASSWORD}") {{
        sessionStorage.setItem("rann_session_active", "valid");
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockLive();
        return;
      }}
      if (u === "durhampol" && p === "{PAGE_PASSWORD}") {{
        sessionStorage.setItem("durham_pol_auth", "granted");
        touchActivity();
        unlockLive();
        return;
      }}
      try {{
        const res = await fetch("/durhampolitics/approved_users.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (res.ok) {{
          const data = await res.json();
          const match = ((data && data.users) || []).find(x =>
            x.status === "APPROVED" &&
            (x.allowed_pages || []).includes("/durhampolitics") &&
            ((x.username || "").toLowerCase() === u || (x.email || "").toLowerCase() === u)
          );
          if (match && match.salt && match.password_hash) {{
            const h = await sha256Hex(match.salt + ":" + p);
            if (h === match.password_hash) {{
              sessionStorage.removeItem("rann_session_active");
              sessionStorage.setItem("durham_pol_auth", "granted");
              touchActivity();
              unlockLive();
              return;
            }}
          }}
        }}
      }} catch (err) {{}}
      document.getElementById("authErr").style.display = "block";
    }}

    function unlockLive() {{
      document.getElementById("authOverlay").style.display = "none";
      document.getElementById("liveApp").style.display = "flex";
      fetchLiveStatus(true);
      setInterval(() => fetchLiveStatus(false), 10000);
      setInterval(() => {{
        secondsToSummaryRefresh = secondsToSummaryRefresh <= 1 ? 60 : secondsToSummaryRefresh - 1;
        const el = document.getElementById("summaryTimer");
        if (el) el.innerText = "Next summary sync: " + secondsToSummaryRefresh + "s";
        if (secondsToSummaryRefresh === 60) fetchLiveStatus(true);
      }}, 1000);
    }}

    function esc(s) {{
      return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
    }}

    async function fetchLiveStatus(forceSummary) {{
      try {{
        const res = await fetch("/durhampolitics/live_status.json?t=" + Date.now(), {{ cache: "no-store" }});
        if (!res.ok) return;
        const data = await res.json();
        const prevSummaryTs = latestData ? latestData.summary_updated_at : null;
        latestData = data;

        const badge = document.getElementById("liveBadgeText");
        const titleEl = document.getElementById("liveTitle");
        const ytLink = document.getElementById("openYtLink");

        if (!data || !data.is_live) {{
          badge.innerText = "OFFLINE";
          titleEl.innerText = "No Meeting Currently in Progress";
          ytLink.style.display = "none";
          currentVideoId = null;
          document.getElementById("videoWrap").innerHTML = '<div class="empty-state"><strong>No Durham meeting is currently live.</strong><span>When City Council, DPS Board, or BOCC goes live, this page activates automatically with real-time audio transcription and 60-second executive summaries.</span><a href="/durhampolitics/" class="btn-back">Return to Meeting Archives</a></div>';
          document.getElementById("summaryPane").innerHTML = '<div class="empty-state">No live session in progress. Past meetings and Executive Summary PDFs are available in the main archive.</div>';
          document.getElementById("transcriptPane").innerHTML = '<div class="empty-state">Standing by for next live broadcast...</div>';
          return;
        }}

        const bName = data.body_name || (data.body_id || "").toUpperCase();
        badge.innerText = "LIVE • " + (data.body_id || "").toUpperCase();
        titleEl.innerText = data.title || (bName + " — Live Meeting");
        if (data.video_url) {{
          ytLink.href = data.video_url;
          ytLink.style.display = "inline";
        }}

        if (data.video_id && data.video_id !== currentVideoId) {{
          currentVideoId = data.video_id;
          document.getElementById("videoWrap").innerHTML = `<iframe src="https://www.youtube.com/embed/${{encodeURIComponent(data.video_id)}}?autoplay=1&rel=0" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>`;
        }}

        if (forceSummary || data.summary_updated_at !== prevSummaryTs) {{
          renderSummary(data);
        }}
        renderTranscript();
      }} catch (e) {{
        console.error("Live status poll failed:", e);
      }}
    }}

    function renderSummary(data) {{
      const pane = document.getElementById("summaryPane");
      const updatedStr = data.summary_updated_at ? new Date(data.summary_updated_at).toLocaleTimeString() : "Updating...";
      document.getElementById("summaryStatus").innerText = "Last summary: " + updatedStr + " • Real-time Audio ASR";

      let html = `
        <div class="section-hdr">Executive Overview So Far</div>
        <div class="exec-box">${{esc(data.executive_summary || "Listening to live meeting audio and synthesizing initial summary...")}}</div>
      `;

      const topics = data.topics_so_far || [];
      html += `<div class="section-hdr">Agenda Topics Discussed So Far (${{topics.length}})</div>`;
      if (!topics.length) {{
        html += `<div style="font-size:12.5px;color:var(--text-dim);">Topics will populate automatically as agenda items are discussed.</div>`;
      }} else {{
        topics.forEach(t => {{
          const tsUrl = (data.video_url && t.start_seconds !== undefined) ? `${{data.video_url}}&t=${{t.start_seconds}}s` : (data.video_url || "#");
          html += `
            <div class="topic-card">
              <div class="topic-head">
                <strong style="font-size:13px;color:#fff;">${{esc(t.title)}}</strong>
                <a class="ts-chip" href="${{tsUrl}}" target="_blank" rel="noopener noreferrer">&#9658; ${{esc(t.timestamp_label || "Live")}}</a>
              </div>
              <div style="font-size:12.5px;color:var(--text-muted);line-height:1.5;">${{esc(t.discussion_summary || "")}}</div>
              ${{t.vote_summary ? `<div style="font-size:12px;color:#6ee7b7;margin-top:6px;"><strong>Vote / Action:</strong> ${{esc(t.vote_summary)}}</div>` : ""}}
            </div>
          `;
        }});
      }}

      const votes = data.votes_so_far || [];
      html += `<div class="section-hdr">Motions &amp; Votes Observed So Far (${{votes.length}})</div>`;
      if (!votes.length) {{
        html += `<div style="font-size:12.5px;color:var(--text-dim);">No formal votes detected yet in the live audio.</div>`;
      }} else {{
        votes.forEach(v => {{
          const tsUrl = (data.video_url && v.timestamp_seconds !== undefined) ? `${{data.video_url}}&t=${{v.timestamp_seconds}}s` : (data.video_url || "#");
          html += `
            <div class="vote-card">
              <div class="topic-head">
                <strong style="font-size:13px;color:#fff;">${{esc(v.item_title)}}</strong>
                <a class="ts-chip" href="${{tsUrl}}" target="_blank" rel="noopener noreferrer">&#9658; ${{esc(v.timestamp_label || "")}}</a>
              </div>
              <div style="font-size:12px;color:#93c5fd;">Outcome: <strong>${{esc(v.outcome || "Recorded")}}</strong> ${{v.tally ? "(" + esc(v.tally) + ")" : ""}}</div>
              ${{v.notes ? `<div style="font-size:12px;color:var(--text-muted);margin-top:4px;">${{esc(v.notes)}}</div>` : ""}}
            </div>
          `;
        }});
      }}

      pane.innerHTML = html;
    }}

    function renderTranscript() {{
      const pane = document.getElementById("transcriptPane");
      if (!latestData || !latestData.is_live) return;
      const filter = (document.getElementById("transcriptFilter").value || "").trim().toLowerCase();
      const lines = (latestData.transcript_lines || []).filter(l => !filter || (l.text || "").toLowerCase().includes(filter));
      if (!lines.length) {{
        pane.innerHTML = '<div class="empty-state">Transcribing live audio stream via local ASR...</div>';
        return;
      }}
      const baseUrl = latestData.video_url || "";
      pane.innerHTML = lines.map(l => {{
        const href = baseUrl && l.seconds !== undefined ? `${{baseUrl}}&t=${{l.seconds}}s` : baseUrl;
        return `<div class="transcript-line"><a class="t-ts" href="${{href}}" target="_blank" rel="noopener noreferrer">[${{esc(l.timestamp)}}]</a><span>${{esc(l.text)}}</span></div>`;
      }}).join("");

      if (document.getElementById("autoScrollToggle").checked) {{
        pane.scrollTop = pane.scrollHeight;
      }}
    }}

    (function() {{
      const sessionAuth = sessionStorage.getItem("rann_session_active") || sessionStorage.getItem("durham_pol_auth");
      if (sessionAuth && (Date.now() - getLastActive() <= INACTIVITY_TIMEOUT_MS)) {{
        touchActivity();
        unlockLive();
      }}
    }})();
  </script>
</body>
</html>
"""
    live_html_path.write_text(live_html, encoding="utf-8")
    print(f"✓ Live Meeting split-pane page generated at: {live_html_path}")
    return str(live_html_path)

if __name__ == "__main__":
    generate_durhampolitics_page()
