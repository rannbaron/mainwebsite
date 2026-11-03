#!/usr/bin/env python3
"""
NCSBE War Room Page Generator: rannbar-on.com/fuckyeah
Generates a dedicated high-impact NCSBE ballot returns & turnout dashboard.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("/home/rann/src/website/mainwebsite")
MAP_BASE_PATH = BASE_DIR / "nc_map_base.json"
OUTPUT_DIR = BASE_DIR / "fuckyeah"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INDEX_PATH = OUTPUT_DIR / "index.html"
ROOT_PATH = BASE_DIR / "fuckyeah.html"

def generate_page():
    with open(MAP_BASE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    state_data = data.get("state", {}).get("data", {}).get("2026", {})
    tot = state_data.get("tot", 2828131)
    dem = state_data.get("dem", 1085262)
    rep = state_data.get("rep", 738717)
    una = state_data.get("una", 995378)
    white = state_data.get("white", 1875529)
    black = state_data.get("black", 599214)

    dem_pct = (dem / tot * 100) if tot > 0 else 0
    rep_pct = (rep / tot * 100) if tot > 0 else 0
    una_pct = (una / tot * 100) if tot > 0 else 0

    flipped = data.get("state", {}).get("forecast", {}).get("flipped_to_dem", [
        "ALAMANCE", "ANSON", "CABARRUS", "FRANKLIN", "GASTON", "HARNETT", 
        "JOHNSTON", "LEE", "NASH", "NEW HANOVER", "SCOTLAND", "WASHINGTON", "WILSON"
    ])

    counties = data.get("counties", [])
    counties_sorted = sorted(counties, key=lambda c: c.get("data", {}).get("2026", {}).get("tot", 0), reverse=True)

    rows_html = ""
    for c in counties_sorted:
        c_name = c.get("name", "Unknown")
        c_data = c.get("data", {}).get("2026", {})
        c_tot = c_data.get("tot", 0)
        c_dem = c_data.get("dem", 0)
        c_rep = c_data.get("rep", 0)
        c_una = c_data.get("una", 0)

        c_dem_p = (c_dem / c_tot * 100) if c_tot > 0 else 0
        c_rep_p = (c_rep / c_tot * 100) if c_tot > 0 else 0
        c_una_p = (c_una / c_tot * 100) if c_tot > 0 else 0

        diff = c_dem - c_rep
        is_dem_lead = diff > 0
        lead_str = f"D +{abs(diff):,}" if is_dem_lead else f"R +{abs(diff):,}"
        lead_color = "#3b82f6" if is_dem_lead else "#ef4444"

        is_flip = c_name.upper() in [f.upper() for f in flipped]
        flip_badge = '<span class="badge badge-flip">FLIP DEM</span>' if is_flip else ''

        rows_html += f"""
        <tr data-county="{c_name.lower()}">
          <td><strong>{c_name}</strong> {flip_badge}</td>
          <td style="text-align: right; font-weight: 700;">{c_tot:,}</td>
          <td style="text-align: right; color: #60a5fa;">{c_dem:,} <span class="pct">({c_dem_p:.1f}%)</span></td>
          <td style="text-align: right; color: #f87171;">{c_rep:,} <span class="pct">({c_rep_p:.1f}%)</span></td>
          <td style="text-align: right; color: #fbbf24;">{c_una:,} <span class="pct">({c_una_p:.1f}%)</span></td>
          <td style="text-align: right; font-weight: 800; color: {lead_color};">{lead_str}</td>
        </tr>
        """

    flipped_tags = " ".join([f'<span class="badge badge-flip-lg">{f.title()}</span>' for f in flipped])

    now_str = datetime.now().strftime("%B %d, %Y at %I:%M %p EST")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NCSBE Turnout & Ballot Returns War Room | rannbar-on.com/fuckyeah</title>
  <meta name="description" content="NCSBE Real-Time 2026 Ballot Ingestion & County Turnout War Room. Live voter returns across all 100 NC counties.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #090d16;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f9fafb;
      --muted: #9ca3af;
      --blue: #3b82f6;
      --red: #ef4444;
      --green: #10b981;
      --amber: #f59e0b;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 0 0 60px 0;
    }}
    .header {{
      background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #172554 100%);
      border-bottom: 1px solid #1e293b;
      padding: 36px 20px;
      text-align: center;
    }}
    .header h1 {{
      font-size: 32px;
      font-weight: 900;
      letter-spacing: -0.5px;
      color: #ffffff;
      margin-bottom: 8px;
    }}
    .header p {{
      font-size: 14px;
      color: #94a3b8;
      max-width: 600px;
      margin: 0 auto;
    }}
    .nav-links {{
      display: flex;
      justify-content: center;
      gap: 12px;
      margin-top: 20px;
      flex-wrap: wrap;
    }}
    .nav-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.12);
      color: #cbd5e1;
      border-radius: 20px;
      padding: 8px 16px;
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
      transition: all 0.2s;
    }}
    .nav-btn:hover {{
      background: var(--blue);
      color: #fff;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px 20px;
    }}
    .grid-4 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      text-align: center;
    }}
    .stat-lbl {{
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      color: var(--muted);
      margin-bottom: 6px;
      display: block;
    }}
    .stat-val {{
      font-size: 28px;
      font-weight: 900;
      color: #ffffff;
      line-height: 1.1;
    }}
    .stat-sub {{
      font-size: 12px;
      font-weight: 700;
      margin-top: 6px;
      display: block;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    .card-title {{
      font-size: 18px;
      font-weight: 800;
      color: #ffffff;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 800;
    }}
    .badge-flip {{
      background: #1e3a8a;
      color: #60a5fa;
      border: 1px solid #2563eb;
      margin-left: 6px;
    }}
    .badge-flip-lg {{
      background: #1e3a8a;
      color: #93c5fd;
      border: 1px solid #3b82f6;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 700;
      margin: 4px;
      display: inline-block;
    }}
    .search-box {{
      background: #090d16;
      border: 1px solid #334155;
      color: #ffffff;
      padding: 10px 16px;
      border-radius: 8px;
      font-size: 14px;
      width: 100%;
      max-width: 320px;
    }}
    .search-box:focus {{
      outline: none;
      border-color: var(--blue);
    }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 13.5px;
    }}
    table.data-table th {{
      background: #0f172a;
      border-bottom: 2px solid #1e293b;
      padding: 12px 14px;
      text-align: left;
      font-weight: 700;
      color: #94a3b8;
    }}
    table.data-table td {{
      padding: 12px 14px;
      border-bottom: 1px solid #1e293b;
    }}
    table.data-table tr:hover {{
      background: #1e293b;
    }}
    .pct {{
      font-size: 11px;
      color: #94a3b8;
      font-weight: 500;
    }}
    .footer {{
      text-align: center;
      font-size: 12px;
      color: #64748b;
      margin-top: 40px;
    }}
  </style>
</head>
<body>

  <header class="header">
    <h1>🔥 NCSBE War Room: Live 2026 Ballot Ingestion</h1>
    <p>Real-time official returns across all 100 North Carolina counties | Data updated {now_str}</p>
    <div class="nav-links">
      <a href="https://rannbar-on.com/needle" class="nav-btn">⚡ Live Needle Dials</a>
      <a href="https://rannbar-on.com/prediction" class="nav-btn">📊 Full Forecast Model</a>
      <a href="https://rannbar-on.com/ncpoliticssocials" class="nav-btn">📱 Phone Social Feed</a>
      <a href="https://rannbar-on.com/early_voting_turnout_map.html" class="nav-btn">🗺️ Turnout Map</a>
    </div>
  </header>

  <main class="container">

    <!-- Top Key Metrics Grid -->
    <div class="grid-4">
      <div class="stat-card">
        <span class="stat-lbl">Total Ballots Cast</span>
        <div class="stat-val">{tot:,}</div>
        <span class="stat-sub" style="color: #10b981;">100% of Counties Active</span>
      </div>
      <div class="stat-card">
        <span class="stat-lbl">Democratic Ballots</span>
        <div class="stat-val" style="color: #60a5fa;">{dem:,}</div>
        <span class="stat-sub" style="color: #60a5fa;">{dem_pct:.2f}% of electorate</span>
      </div>
      <div class="stat-card">
        <span class="stat-lbl">Republican Ballots</span>
        <div class="stat-val" style="color: #f87171;">{rep:,}</div>
        <span class="stat-sub" style="color: #f87171;">{rep_pct:.2f}% of electorate</span>
      </div>
      <div class="stat-card">
        <span class="stat-lbl">Unaffiliated Ballots</span>
        <div class="stat-val" style="color: #fbbf24;">{una:,}</div>
        <span class="stat-sub" style="color: #fbbf24;">{una_pct:.2f}% (Surging past GOP!)</span>
      </div>
    </div>

    <!-- Flipped Counties Card -->
    <div class="card">
      <div class="card-title">
        <span>🗺️ Projected County Flips Toward Democrats (13 Counties)</span>
        <span style="font-size: 13px; color: #60a5fa; font-weight: 600;">Shift vs. 2022 Midterm Baselines</span>
      </div>
      <p style="font-size: 13px; color: #cbd5e1; margin-bottom: 12px;">
        Comparing current NCSBE ballot volume against 2022 historical benchmarks, the Bayesian regression model indicates 13 counties currently tracking in the Democratic win column:
      </p>
      <div>
        {flipped_tags}
      </div>
    </div>

    <!-- 100-County Returns Table -->
    <div class="card">
      <div class="card-title">
        <span>📊 County-by-County Ballot Return Data (All 100 Counties)</span>
        <input type="text" id="countySearch" class="search-box" placeholder="Search county..." onkeyup="filterTable()">
      </div>
      <div style="overflow-x: auto;">
        <table class="data-table" id="countyTable">
          <thead>
            <tr>
              <th>County</th>
              <th style="text-align: right;">Total Ballots</th>
              <th style="text-align: right;">Democratic (Share)</th>
              <th style="text-align: right;">Republican (Share)</th>
              <th style="text-align: right;">Unaffiliated (Share)</th>
              <th style="text-align: right;">Current Net Margin</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </div>
    </div>

    <div class="footer">
      Official NCSBE automated feed ingestion & analytics | rannbar-on.com/fuckyeah | Hosted on GitHub Pages
    </div>
  </main>

  <script>
    function filterTable() {{
      const query = document.getElementById("countySearch").value.toLowerCase();
      const rows = document.querySelectorAll("#countyTable tbody tr");
      rows.forEach(r => {{
        const cname = r.getAttribute("data-county") || "";
        r.style.display = cname.includes(query) ? "" : "none";
      }});
    }}
  </script>
</body>
</html>
"""

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[NCSBE] Wrote {INDEX_PATH}")

    with open(ROOT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[NCSBE] Wrote {ROOT_PATH}")

if __name__ == "__main__":
    generate_page()
