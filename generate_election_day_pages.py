#!/usr/bin/env python3
"""
North Carolina Student Voting Platform - Election Day Static Generator
Replaces early voting information across all 111 campus guides, master directory,
and /vote portal with Election Day voting rules, assigned precinct lookups,
voting hours (6:30 AM - 7:30 PM), voter ID requirements, and candidate guides.
"""

import os
import json
import base64
import re
import qrcode
import qrcode.image.svg

MAIN_DIR = '/home/rann/Documents/mainwebsite'
LOCAL_DIR = '/home/rann/Documents/math/teaching/105L/Fall26'
CACHE_DIR = f'{MAIN_DIR}/.nc_voting_cache'

print("1. Loading cached NC election data...")
with open(f'{CACHE_DIR}/all_institutions.json', 'r', encoding='utf-8') as f:
    institutions = json.load(f)

with open(f'{CACHE_DIR}/county_boe_info.json', 'r', encoding='utf-8') as f:
    boe_list = json.load(f)
boe_by_county = {c['Name'].upper(): c for c in boe_list}

with open(f'{CACHE_DIR}/campus_geo_data.json', 'r', encoding='utf-8') as f:
    campus_geo_list = json.load(f)

campus_geo_json_str = json.dumps(campus_geo_list)

county_dem_urls = {
    'DURHAM': 'https://www.durhamdemocrats.org/',
    'WAKE': 'https://www.wakedems.org/',
    'ORANGE': 'https://www.orangedems.com/',
    'MECKLENBURG': 'https://www.meckdems.org/',
    'GUILFORD': 'https://www.guilforddems.org/',
    'FORSYTH': 'https://www.forsythdems.org/',
    'BUNCOMBE': 'https://www.buncombedems.org/',
    'WATAUGA': 'https://www.wataugadems.com/',
    'PITT': 'https://www.pittdems.com/',
    'NEW HANOVER': 'https://www.newhanoverdems.org/',
    'ALAMANCE': 'https://www.alamancedems.com/',
    'CUMBERLAND': 'https://www.cumberlandcountydems.org/',
    'CABARRUS': 'https://www.cabarrusdems.org/',
    'CATAWBA': 'https://catawbadems.com/',
    'ROWAN': 'https://www.rowandems.com/',
    'UNION': 'https://www.uniondems.org/',
    'GASTON': 'https://www.gastondems.org/',
    'HENDERSON': 'https://www.hendersondems.com/',
    'HARNETT': 'https://www.harnettdems.org/',
    'JOHNSTON': 'https://www.johnstondems.org/'
}

county_rep_urls = {
    'DURHAM': 'https://www.durhamgop.com/',
    'WAKE': 'https://www.wakegop.org/',
    'ORANGE': 'https://www.orangecountygop.com/',
    'MECKLENBURG': 'https://www.meckgop.com/',
    'GUILFORD': 'https://www.guilfordgop.org/',
    'FORSYTH': 'https://www.forsythgop.org/',
    'BUNCOMBE': 'https://www.buncombegop.org/',
    'WATAUGA': 'https://www.wataugagop.com/',
    'PITT': 'https://www.pittgop.com/',
    'NEW HANOVER': 'https://www.newhanovergop.org/',
    'ALAMANCE': 'https://www.alamancegop.org/',
    'CUMBERLAND': 'https://www.cumberlandgop.com/',
    'CABARRUS': 'https://www.cabarrusgop.org/',
    'CATAWBA': 'https://catawbagop.com/',
    'ROWAN': 'https://www.rowangop.org/',
    'UNION': 'https://www.unioncountyncgop.com/',
    'GASTON': 'https://www.gastongop.org/',
    'HENDERSON': 'https://www.hendersongop.com/',
    'HARNETT': 'https://www.harnettcountygop.com/',
    'JOHNSTON': 'https://www.johnstoncountygop.org/'
}

print("2. Reading QR codes...")
qr_b64_map = {}
for inst in institutions:
    key = inst['key']
    png_path = f"{MAIN_DIR}/{key}_qr.png"
    with open(png_path, 'rb') as f:
        qr_b64_map[key] = base64.b64encode(f.read()).decode('utf-8')

sorted_institutions = sorted(institutions, key=lambda x: x['name'])
campus_options = []
for inst in sorted_institutions:
    type_badge = "UNC" if inst['type'] == 'UNC System' else ("CC" if "Community" in inst['type'] else "Private")
    campus_options.append(f'<option value="/{inst["key"]}">{inst["name"]} ({inst["city"]}) - {type_badge}</option>')
campus_options_html = '\n'.join(campus_options)

print("3. Generating individual campus Election Day voting guide pages...")

for inst in institutions:
    key = inst['key']
    cname = inst['county'].upper()
    boe = boe_by_county.get(cname, {})
    c_display = cname.title() + " County"
    boe_phone = boe.get('OfficePhoneNum', '(919) 814-0700')
    boe_addr = boe.get('FullAddress', f'{c_display} Board of Elections, NC')
    boe_web = boe.get('WebsiteAddr', f'https://vt.ncsbe.gov/BOEInfo/?county={cname}')
    boe_name = boe.get('OfficeName', f'{c_display} Board of Elections').title()

    dem_county_url = county_dem_urls.get(cname, 'https://www.ncdp.org/county-parties/')
    rep_county_url = county_rep_urls.get(cname, 'https://www.ncgop.org/county_parties')

    # Student ID section
    if inst['id_approved']:
        id_alert_box = f'''
        <div class="bg-emerald-950/40 border-2 border-emerald-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-emerald-500/20 text-emerald-300 text-2xl shrink-0">
            ✓
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 mb-2">Approved by NC State Board of Elections</span>
            <h2 class="text-xl font-bold text-white mb-2">{inst['name']} Student ID is Valid on Election Day!</h2>
            <p class="text-sm text-emerald-100/90 leading-relaxed mb-3">
              The North Carolina State Board of Elections officially approved the <b>{inst['id_card_name']}</b> for voter photo identification. You can use your physical plastic student ID to vote.
            </p>
            <div class="p-3.5 rounded-xl bg-emerald-900/30 border border-emerald-700/50 text-xs text-emerald-200/90 space-y-1.5 font-medium">
              <p>⚠️ <b>CRITICAL: PHYSICAL CARD REQUIRED.</b> Digital IDs stored on mobile phones (Apple Wallet, Google Wallet, photos) are <b>NOT ACCEPTED</b> under NC law.</p>
              <p>✅ <b>Other Accepted Photo IDs:</b> NC Driver’s License, US Passport, Military/Veteran ID, or free county BOE ID card.</p>
              <p>💡 <b>Lacking an ID at the polls?</b> Fill out a Photo ID Exception Form at your precinct and cast a ballot that counts.</p>
            </div>
          </div>
        </div>
        '''
    else:
        id_alert_box = f'''
        <div class="bg-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-amber-500/20 text-amber-300 text-2xl shrink-0">
            ⚠️
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">Student Photo ID Not On State Approved List</span>
            <h2 class="text-xl font-bold text-white mb-2">Student ID Card is NOT Accepted for Voting</h2>
            <p class="text-sm text-amber-100/90 leading-relaxed mb-3">
              Under North Carolina law, {inst['name']} student IDs are <b>not approved</b> for voting. You must present an approved alternative photo ID.
            </p>
            <div class="p-3.5 rounded-xl bg-amber-900/30 border border-amber-700/50 text-xs text-amber-200/90 space-y-1.5 font-medium">
              <p>✅ <b>WHAT YOU CAN USE INSTEAD:</b></p>
              <ul class="list-disc pl-5 space-y-1 text-slate-200">
                <li><b>North Carolina Driver’s License</b> or NC DMV State ID (unexpired or expired up to 1 year).</li>
                <li><b>U.S. Passport</b> or U.S. Passport Card (must be unexpired).</li>
                <li><b>Out-of-State Driver’s License</b> (accepted only if you registered to vote in NC within 90 days of the election).</li>
                <li><b>Free Voter Photo ID Card:</b> Issued by your county Board of Elections.</li>
                <li><b>Photo ID Exception Form:</b> If you lack an ID due to an allowable exception, you can complete an Exception Form at the precinct.</li>
              </ul>
            </div>
          </div>
        </div>
        '''

    qr_b64 = qr_b64_map[key]

    html_content = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst['short_name']} Student Election Day Voting Guide (Tuesday, Nov 3) | Rann Bar-On</title>
  <meta name="description" content="Election Day voting guide for {inst['name']} students in {c_display}, NC: assigned precinct polling place lookup, hours (6:30 AM - 7:30 PM), voter ID rules, and candidate guides.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/{key}">
  <meta property="og:title" content="{inst['short_name']} Student Election Day Voting Guide">
  <meta property="og:description" content="Everything {inst['name']} students need for Election Day (Tuesday, Nov 3): find your assigned precinct polling place, hours, and voter ID rules.">
  <meta property="og:image" content="https://rannbar-on.com/{key}_qr.png">

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    if (!window.tailwind) {{
      document.write('<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"><\\/script>');
    }}
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    :root {{
      --bg: #070b14;
      --card-bg: #0f172a;
      --card-border: #1e293b;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }}
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      overflow-x: hidden;
    }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased">

  <!-- Top Announcement Bar (Election Day Mode) -->
  <div class="bg-gradient-to-r from-red-950 via-rose-950 to-slate-950 px-4 py-2.5 text-center text-xs sm:text-sm font-bold text-slate-100 border-b border-rose-900/50 shadow-md">
    <span class="inline-flex items-center gap-2">
      <span class="relative flex h-2.5 w-2.5">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
      </span>
      <span>🔴 Early Voting Has Ended • <b>ELECTION DAY IS TUESDAY, NOVEMBER 3, 2026</b> • Polls Open <b>6:30 AM – 7:30 PM</b></span>
    </span>
  </div>

  <!-- Header / Navigation -->
  <header class="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <a href="https://rannbar-on.com/" class="flex items-center gap-2 group">
        <div class="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center font-bold text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition">
          R
        </div>
        <div>
          <span class="font-bold tracking-tight text-white block text-sm sm:text-base leading-none">Rann Bar-On</span>
          <span class="text-[11px] text-slate-400 font-mono">rannbar-on.com</span>
        </div>
      </a>
      <div class="flex items-center gap-2 sm:gap-2.5">
        <a href="#precinct-lookup" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white transition shadow-sm">
          📍 Assigned Precinct
        </a>
        <a href="#voter-guides" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
          🗳️ Guides
        </a>
        <a href="#voter-id" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 transition">
          ⚠️ Voter ID
        </a>
        <a href="#qr-code" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm">
          📱 QR
        </a>
      </div>
    </div>
  </header>

  <!-- Campus Quick Jump Selector Bar -->
  <nav class="bg-slate-900/95 border-b border-slate-800/80 py-2.5 px-4 backdrop-blur shadow-inner">
    <div class="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <a href="/campuses" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 font-bold text-xs transition">
          <span>🏛️</span>
          <span>Browse All 111 NC Campuses</span>
        </a>
      </div>
      
      <div class="flex items-center gap-2">
        <label for="campus-quick-jump" class="text-xs text-slate-400 font-medium hidden sm:inline">Switch Campus:</label>
        <select id="campus-quick-jump" onchange="if(this.value) window.location.href=this.value;" class="bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-blue-500 font-medium">
          <option value="">Jump to another NC College/University...</option>
          {campus_options_html}
        </select>
      </div>
    </div>
  </nav>

  <!-- Hero Section (Election Day Focus) -->
  <section class="relative py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 overflow-hidden">
    <div class="max-w-4xl mx-auto text-center relative z-10">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30 mb-4">
        <span>{inst['badge_icon']} {inst['name']}</span>
        <span class="text-slate-600">•</span>
        <span>Election Day Guide (Nov 3)</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        {inst['short_name']} Student Guide <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-rose-400 via-amber-300 to-orange-300">to Voting on Election Day</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Early voting has concluded. On <b>Election Day (Tuesday, November 3)</b>, North Carolina law requires you to vote at your <b>specifically assigned precinct polling place</b>. Find your precinct, bring your photo ID, and cast your ballot before 7:30 PM!
      </p>

      <!-- Key Stat Pills -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto text-left">
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Election Day</div>
          <div class="text-base font-bold text-white mt-0.5">Tuesday, Nov 3</div>
          <div class="text-[11px] text-emerald-400 mt-1 font-mono">6:30 AM – 7:30 PM</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Where to Vote</div>
          <div class="text-sm sm:text-base font-bold text-rose-300 mt-0.5 truncate">Assigned Precinct Only</div>
          <div class="text-[11px] text-slate-400 mt-1 font-mono">Based on address</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Same-Day Reg</div>
          <div class="text-base font-bold text-rose-400 mt-0.5">NOT Available</div>
          <div class="text-[11px] text-rose-300 mt-1 font-mono">Must be registered</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Voter ID Rule</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{'Approved' if inst['id_approved'] else 'Alt ID Required'}</div>
          <div class="text-[11px] {'text-emerald-400' if inst['id_approved'] else 'text-amber-400'} mt-1 font-mono">{'Physical Student Card' if inst['id_approved'] else 'NC License / Passport'}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- CRITICAL ELECTION DAY RULES NOTICE -->
  <section id="election-day-rules" class="py-8 px-4 sm:px-6 bg-rose-950/20 border-b border-rose-900/40">
    <div class="max-w-4xl mx-auto space-y-4">
      <div class="bg-rose-950/40 border-2 border-rose-500/60 rounded-2xl p-5 sm:p-6 shadow-xl">
        <div class="flex items-start gap-4">
          <div class="p-3 rounded-xl bg-rose-500/20 text-rose-300 text-2xl shrink-0">
            ⚠️
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30 mb-2">Mandatory North Carolina Election Law</span>
            <h2 class="text-xl font-bold text-white mb-2">Two Critical Rules for Voting on Election Day:</h2>
            <div class="space-y-3 text-xs sm:text-sm text-slate-200 mt-3 leading-relaxed">
              <div class="p-3.5 rounded-xl bg-slate-950/80 border border-rose-900/60">
                <p class="font-bold text-white mb-1">1. You CANNOT vote at any polling site — You MUST go to your specifically assigned precinct.</p>
                <p class="text-slate-300">During early voting, voters could visit any site in the county. On Election Day, your ballot is printed specifically for your home precinct. If you go to the wrong precinct, you will have to vote a provisional ballot, and races outside that precinct may not be counted.</p>
              </div>

              <div class="p-3.5 rounded-xl bg-slate-950/80 border border-rose-900/60">
                <p class="font-bold text-white mb-1">2. Same-Day Voter Registration is NOT available on Election Day.</p>
                <p class="text-slate-300">Under NC General Statutes (§ 163-82.6), same-day registration is permitted <i>only</i> during Early Voting. On Election Day, you must already be registered to vote in North Carolina.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Main Content Container -->
  <main class="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-12">

    <!-- Section 1: Assigned Precinct Polling Place Lookup -->
    <section id="precinct-lookup" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl">
        <span class="text-xs font-mono font-semibold text-rose-400 uppercase tracking-wider">Find Where You Vote Today</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-3">Look Up Your Assigned Precinct Polling Place</h2>
        <p class="text-sm text-slate-300 leading-relaxed mb-6">
          Every voter in {c_display} is assigned a specific Election Day polling place based on their voter registration residential address (your dormitory or off-campus apartment).
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Lookup Tool 1 -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div class="text-xs font-bold text-blue-400 uppercase tracking-wider mb-1">Official NCSBE Tool</div>
              <h3 class="text-base font-bold text-white mb-2">Polling Place Search (by Address)</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Enter your campus dormitory address or off-campus apartment address to find your assigned Election Day precinct, polling place address, and sample ballot.
              </p>
            </div>
            <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" rel="noopener" class="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs text-center transition shadow-md flex items-center justify-center gap-1.5">
              <span>Open NCSBE Polling Place Lookup</span>
              <span>↗</span>
            </a>
          </div>

          <!-- Lookup Tool 2 -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-2xl p-5 flex flex-col justify-between">
            <div>
              <div class="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-1">Voter Search</div>
              <h3 class="text-base font-bold text-white mb-2">Voter Search & Registration Check</h3>
              <p class="text-xs text-slate-300 leading-relaxed mb-4">
                Enter your first and last name to look up your active registration record, confirm your assigned polling location, and view your exact district ballot.
              </p>
            </div>
            <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs text-center transition shadow-md flex items-center justify-center gap-1.5">
              <span>Look Up Your Voter Record</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800/80 flex items-start gap-3">
          <span class="text-xl">💡</span>
          <div class="text-xs text-slate-300 leading-relaxed">
            <b>In Line by 7:30 PM? STAY IN LINE!</b> Under North Carolina law, if you are physically in line at your assigned polling place by 7:30 PM on Election Day, election officials are legally required to keep the polls open until you have cast your ballot. Do not leave the line!
          </div>
        </div>
      </div>
    </section>

    <!-- Section 2: Voter ID Requirement -->
    <section id="voter-id" class="scroll-mt-20">
      {id_alert_box}
    </section>

    <!-- Section 3: Candidate Voter Guides (Democratic, Republican & Independent) -->
    <section id="voter-guides" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-8">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Candidate Research & Endorsements</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-2">Election Day Candidate Guides for {inst['short_name']} Students</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Before entering the voting booth in {c_display}, review candidate questionnaires, voting records, and endorsements from multiple political perspectives:
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 1. Democratic-Leaning Guide -->
        <div class="bg-slate-950/80 border border-blue-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 mb-3">
              <span>🔵 Democratic / Progressive</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Blue Voter Guide & NC Dems</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Enter your local address to see customized candidate recommendations and slates endorsed by Democratic, labor, reproductive rights, and environmental organizations across North Carolina.
            </p>
          </div>
          <div class="space-y-2 pt-2 border-t border-slate-800/80">
            <a href="https://bluevoterguide.org/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open Blue Voter Guide (NC)</span>
              <span>↗</span>
            </a>
            <a href="{dem_county_url}" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-blue-300 border border-slate-800 font-medium text-xs transition">
              <span>{c_display} Democratic Party</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <!-- 2. Republican-Leaning Guide -->
        <div class="bg-slate-950/80 border border-red-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 mb-3">
              <span>🔴 Republican / Conservative</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">iVoterGuide & NC Values</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Comprehensive candidate ratings, policy scorecards, and evaluations based on conservative constitutional principles, fiscal policies, and traditional values across {c_display}.
            </p>
          </div>
          <div class="space-y-2 pt-2 border-t border-slate-800/80">
            <a href="https://ivoterguide.com/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open iVoterGuide (NC)</span>
              <span>↗</span>
            </a>
            <a href="{rep_county_url}" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-red-300 border border-slate-800 font-medium text-xs transition">
              <span>{c_display} Republican Party (GOP)</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <!-- 3. Independent / Non-Partisan Guide -->
        <div class="bg-slate-950/80 border border-emerald-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 mb-3">
              <span>⚖️ Independent / Non-Partisan</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Vote411 (League of Women Voters)</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Strictly non-partisan, unbiased candidate comparisons produced by the League of Women Voters of NC. Candidates answer identical policy questions directly in their own unedited words.
            </p>
          </div>
          <div class="space-y-2 pt-2 border-t border-slate-800/80">
            <a href="https://www.vote411.org/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open Vote411 NC Guide</span>
              <span>↗</span>
            </a>
            <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-slate-800 font-medium text-xs transition">
              <span>NCSBE Official Sample Ballot</span>
              <span>↗</span>
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 4: Election Day Checklist & County BOE -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span>📋</span>
          <span>Election Day Checklist</span>
        </h3>
        <ul class="space-y-3 text-xs sm:text-sm text-slate-300">
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-rose-400 font-bold shrink-0">1.</span>
            <span><b>Verify Assigned Precinct:</b> Double-check your polling place at <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" class="text-rose-400 underline">vt.ncsbe.gov/pplkup</a> before you leave.</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">2.</span>
            <span><b>Physical Photo ID:</b> Bring your physical plastic ID card (phone images are not permitted).</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">3.</span>
            <span><b>Voting Hours:</b> 6:30 AM to 7:30 PM. (If in line by 7:30 PM, stay in line!).</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">4.</span>
            <span><b>Notes Allowed:</b> You can bring a paper voter guide or handwritten notes into the booth.</span>
          </li>
        </ul>
      </div>

      <!-- Board of Elections Contact Card -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
        <div>
          <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span>🏛️</span>
            <span>{boe_name}</span>
          </h3>
          <div class="space-y-2.5 text-xs sm:text-sm">
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200">
              <div class="font-semibold text-white">Physical Office</div>
              <div class="text-xs text-slate-400 mt-1">{boe_addr}</div>
            </div>
            <a href="{boe_web}" target="_blank" rel="noopener" class="flex items-center justify-between p-3 rounded-xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-slate-200 transition">
              <div>
                <div class="font-semibold text-white">Official County Election Website</div>
                <div class="text-xs text-slate-400 mt-0.5">Election Day precinct lists & results</div>
              </div>
              <span class="text-slate-400">↗</span>
            </a>
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span>Election Day Helpline:</span>
          <a href="tel:{boe_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}" class="font-mono font-bold text-blue-400 hover:underline">{boe_phone}</a>
        </div>
      </div>
    </section>

    <!-- Section 5: QR Code Card -->
    <section id="qr-code" class="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="flex flex-col sm:flex-row items-center gap-6 sm:gap-8 justify-between">
        <div class="max-w-xl text-center sm:text-left">
          <span class="text-xs font-mono font-semibold text-rose-400 uppercase tracking-wider">Share with Classmates & Dorms</span>
          <h2 class="text-2xl font-bold text-white mt-1 mb-2">Share this {inst['short_name']} Election Day Guide</h2>
          <p class="text-sm text-slate-300 leading-relaxed mb-4">
            Help your fellow students vote today! Share this link in dorm group chats, student organization channels, and on social media so everyone finds their assigned precinct before polls close at 7:30 PM.
          </p>
          <div class="flex flex-wrap items-center gap-3 justify-center sm:justify-start">
            <div class="px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs sm:text-sm text-blue-300 select-all">
              https://rannbar-on.com/{key}
            </div>
            <button onclick="navigator.clipboard.writeText('https://rannbar-on.com/{key}'); alert('Link copied to clipboard!');" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-sm">
              Copy Link
            </button>
            <a href="/{key}_qr.png" download="{inst['short_name']}_Vote_QR.png" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition">
              Download PNG
            </a>
            <a href="/{key}_qr.svg" download="{inst['short_name']}_Vote_QR.svg" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition">
              Download SVG
            </a>
            <a href="/campuses" class="px-4 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 font-semibold text-xs transition">
              All 111 NC Campuses →
            </a>
          </div>
        </div>

        <!-- QR Code Visual -->
        <div class="bg-white p-4 rounded-2xl shadow-2xl border-4 border-rose-500/30 shrink-0 text-center">
          <img src="data:image/png;base64,{qr_b64}" alt="QR code for {inst['name']} student voting guide" class="w-48 h-48 sm:w-52 sm:h-52 object-contain mx-auto" />
          <div class="text-[11px] font-bold text-slate-900 mt-2 font-mono">rannbar-on.com/{key}</div>
        </div>
      </div>
    </section>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-8 px-4 sm:px-6 mt-16 text-xs text-slate-400">
    <div class="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
      <div>
        <p class="font-medium text-slate-300">Non-partisan student voting guide prepared by Rann Bar-On.</p>
        <p class="text-[11px] text-slate-500 mt-0.5">Official voting data sourced from the {boe_name} and the North Carolina State Board of Elections.</p>
      </div>
      <div class="flex items-center gap-4 text-xs">
        <a href="/campuses" class="text-blue-400 hover:underline">All NC Campuses</a>
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
      </div>
    </div>
  </footer>

</body>
</html>
'''

    with open(f"{MAIN_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    os.makedirs(f"{MAIN_DIR}/{key}", exist_ok=True)
    with open(f"{MAIN_DIR}/{key}/index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

    with open(f"{LOCAL_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

print(f"Generated {len(institutions)} Election Day campus pages.")


# ==============================================================================
# 4. Generate Election Day Master Directory (campuses.html)
# ==============================================================================
print("4. Generating Master Directory page (campuses.html) for Election Day...")

cards_json = []
for inst in institutions:
    cname = inst['county'].upper()
    c_display = cname.title() + " County"
    geo_item = next((g for g in campus_geo_list if g['key'] == inst['key']), None)
    lat = geo_item['lat'] if geo_item else 35.7796
    lon = geo_item['lon'] if geo_item else -78.6382

    cards_json.append({
        'key': inst['key'],
        'name': inst['name'],
        'short_name': inst['short_name'],
        'type': inst['type'],
        'county': c_display,
        'city': inst['city'],
        'lat': lat,
        'lon': lon,
        'icon': inst['badge_icon'],
        'id_approved': inst['id_approved'],
        'id_card': inst['id_card_name'],
        'url': f"https://rannbar-on.com/{inst['key']}"
    })

cards_json_str = json.dumps(cards_json)

campuses_template = '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Colleges & Universities Election Day Voting Directory | Rann Bar-On</title>
  <meta name="description" content="Complete directory of Election Day voting guides for all 111 NC colleges, universities, and community colleges: assigned precinct lookups, voter ID requirements, hours (6:30 AM - 7:30 PM), candidate guides, and QR codes.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/campuses">
  <meta property="og:title" content="NC Colleges & Universities Student Election Day Voting Directory">
  <meta property="og:description" content="Election Day voting guides for all 111 NC higher education institutions: find your assigned precinct polling place, voter ID status, and candidate guides.">
  <meta property="og:image" content="https://rannbar-on.com/dukevote_qr.png">

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    if (!window.tailwind) {
      document.write('<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"><\\/script>');
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    :root {
      --bg: #070b14;
      --card-bg: #0f172a;
      --card-border: #1e293b;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      overflow-x: hidden;
    }

    .font-mono {
      font-family: 'JetBrains Mono', monospace;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased">

  <!-- Top Announcement Bar (Election Day Mode) -->
  <div class="bg-gradient-to-r from-red-950 via-rose-950 to-slate-950 px-4 py-2.5 text-center text-xs sm:text-sm font-bold text-slate-100 border-b border-rose-900/50 shadow-md">
    <span class="inline-flex items-center gap-2">
      <span class="relative flex h-2.5 w-2.5">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
      </span>
      <span>🔴 Early Voting Has Ended • <b>ELECTION DAY IS TUESDAY, NOVEMBER 3, 2026</b> • Polls Open <b>6:30 AM – 7:30 PM</b></span>
    </span>
  </div>

  <!-- Header / Navigation -->
  <header class="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <a href="https://rannbar-on.com/" class="flex items-center gap-2 group">
        <div class="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center font-bold text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition">
          R
        </div>
        <div>
          <span class="font-bold tracking-tight text-white block text-sm sm:text-base leading-none">Rann Bar-On</span>
          <span class="text-[11px] text-slate-400 font-mono">rannbar-on.com</span>
        </div>
      </a>
      <div class="flex items-center gap-3">
        <button onclick="locateAndSortCampuses()" class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white transition shadow-sm">
          <span>📍</span>
          <span>Find Nearest to Me</span>
        </button>
        <a href="https://rannbar-on.com/" class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition">
          ← Main Website
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section (Election Day Focus) -->
  <section class="py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 bg-gradient-to-b from-slate-900/50 to-slate-950">
    <div class="max-w-4xl mx-auto text-center">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30 mb-4">
        <span>🏛️ Statewide Student Voting Portal</span>
        <span class="text-slate-600">•</span>
        <span>111 NC Higher Education Institutions</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        North Carolina Colleges & Universities <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-rose-400 via-amber-300 to-orange-300">Election Day Voting Directory</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Early voting has concluded. On <b>Election Day (Tuesday, November 3)</b>, you must vote at your <b>specifically assigned precinct polling place</b> between 6:30 AM and 7:30 PM. Select your campus below for precinct lookups, voter ID rules, candidate guides, and scannable QR codes.
      </p>

      <!-- Geolocation Auto-Detection Card -->
      <div class="max-w-xl mx-auto mb-8 p-4 rounded-2xl bg-slate-900 border border-rose-500/40 shadow-lg flex flex-col sm:flex-row items-center justify-between gap-3 text-left">
        <div class="flex items-center gap-2.5">
          <span class="text-2xl">📍</span>
          <div>
            <div class="font-bold text-white text-sm">Find Your Closest Campus Instantly</div>
            <div class="text-xs text-slate-400">Detect your location to sort all 111 campuses by proximity.</div>
          </div>
        </div>
        <button onclick="locateAndSortCampuses()" id="btn-geo-campuses" class="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition shrink-0 shadow-md flex items-center justify-center gap-1.5">
          <span>📍</span>
          <span>Locate Me</span>
        </button>
      </div>

      <!-- Nearest Detected Campus Banner (Hidden by default) -->
      <div id="nearest-campus-alert" class="hidden max-w-xl mx-auto mb-8 p-4 rounded-2xl bg-emerald-950/40 border-2 border-emerald-500/60 shadow-xl flex items-center justify-between gap-3 text-left">
        <div>
          <span class="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500 text-white">Nearest Campus Detected</span>
          <h3 id="nearest-campus-name" class="font-bold text-white text-base mt-1"></h3>
          <p id="nearest-campus-detail" class="text-xs text-emerald-300 mt-0.5"></p>
        </div>
        <a id="nearest-campus-btn" href="#" class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shrink-0 transition shadow-sm">
          Open Guide →
        </a>
      </div>

      <!-- Election Day Critical Rule Highlights -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl mx-auto mb-8 text-left">
        <div class="p-4 rounded-2xl bg-rose-950/40 border border-rose-500/40">
          <div class="text-xs font-bold text-rose-300 uppercase tracking-wider mb-1">⚠️ Rule #1: Assigned Precinct Only</div>
          <div class="text-sm font-bold text-white mb-1">You cannot vote at any polling site.</div>
          <p class="text-xs text-slate-300">You must vote at your assigned home precinct. <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" rel="noopener" class="text-rose-400 underline font-semibold">Look up your precinct on NCSBE ↗</a></p>
        </div>

        <div class="p-4 rounded-2xl bg-amber-950/40 border border-amber-500/40">
          <div class="text-xs font-bold text-amber-300 uppercase tracking-wider mb-1">⚠️ Rule #2: No Same-Day Registration</div>
          <div class="text-sm font-bold text-white mb-1">Same-day registration is illegal on Election Day.</div>
          <p class="text-xs text-slate-300">Under NC Gen. Stat. § 163-82.6, you must already be registered. <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="text-amber-400 underline font-semibold">Check registration record ↗</a></p>
        </div>
      </div>

      <!-- Statewide Voter Guides Quick Row -->
      <div id="statewide-guides" class="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto mb-10 text-left">
        <a href="https://bluevoterguide.org/" target="_blank" rel="noopener" class="p-4 rounded-2xl bg-blue-950/40 border border-blue-500/30 hover:border-blue-400 transition group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">🔵 Democratic / Prog</span>
            <span class="text-blue-400 group-hover:translate-x-0.5 transition">↗</span>
          </div>
          <div class="font-bold text-white text-sm">Blue Voter Guide</div>
          <div class="text-[11px] text-slate-300 mt-1">Aggregates progressive & Democratic endorsements across NC.</div>
        </a>

        <a href="https://ivoterguide.com/" target="_blank" rel="noopener" class="p-4 rounded-2xl bg-red-950/40 border border-red-500/30 hover:border-red-400 transition group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold text-red-400 uppercase tracking-wider">🔴 Republican / Cons</span>
            <span class="text-red-400 group-hover:translate-x-0.5 transition">↗</span>
          </div>
          <div class="font-bold text-white text-sm">iVoterGuide & NC Values</div>
          <div class="text-[11px] text-slate-300 mt-1">Research-backed conservative ratings & candidate evaluations.</div>
        </a>

        <a href="https://www.vote411.org/" target="_blank" rel="noopener" class="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-500/30 hover:border-emerald-400 transition group">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider">⚖️ Independent / Nonpartisan</span>
            <span class="text-emerald-400 group-hover:translate-x-0.5 transition">↗</span>
          </div>
          <div class="font-bold text-white text-sm">Vote411 (LWVNC)</div>
          <div class="text-[11px] text-slate-300 mt-1">Non-partisan side-by-side unedited candidate responses.</div>
        </a>
      </div>

      <!-- Search & Filters Container -->
      <div class="max-w-3xl mx-auto space-y-4">
        <!-- Live Search Input -->
        <div class="relative">
          <input type="text" id="campus-search" placeholder="Search by college name, city (e.g. Raleigh, Charlotte, Boone), or county..." 
                 oninput="filterCampuses()"
                 class="w-full bg-slate-900 border-2 border-slate-700 focus:border-rose-500 rounded-2xl py-3.5 pl-12 pr-4 text-sm sm:text-base text-white placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-rose-500/20 transition shadow-lg" />
          <div class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-lg">
            🔍
          </div>
        </div>

        <!-- Filter Buttons -->
        <div class="flex flex-wrap items-center justify-center gap-2 text-xs font-semibold pt-1">
          <button onclick="setFilter('all')" id="btn-all" class="filter-btn px-3.5 py-1.5 rounded-xl bg-rose-600 text-white border border-rose-500 transition shadow-sm">
            All Campuses (111)
          </button>
          <button onclick="setFilter('unc')" id="btn-unc" class="filter-btn px-3.5 py-1.5 rounded-xl bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800 transition">
            UNC System (16)
          </button>
          <button onclick="setFilter('private')" id="btn-private" class="filter-btn px-3.5 py-1.5 rounded-xl bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800 transition">
            Private Universities & Colleges (37)
          </button>
          <button onclick="setFilter('cc')" id="btn-cc" class="filter-btn px-3.5 py-1.5 rounded-xl bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800 transition">
            Community Colleges (58)
          </button>
          <button onclick="setFilter('id_approved')" id="btn-id_approved" class="filter-btn px-3.5 py-1.5 rounded-xl bg-slate-900 text-slate-300 border border-slate-700 hover:bg-slate-800 transition">
            ✓ Student ID Approved (59)
          </button>
        </div>
      </div>
    </div>
  </section>

  <!-- Directory Cards Grid -->
  <main class="max-w-6xl mx-auto px-4 sm:px-6 py-10 flex-grow">
    <div class="flex items-center justify-between mb-6">
      <div id="results-count" class="text-xs font-mono text-slate-400 font-semibold uppercase tracking-wider">
        Showing 111 Colleges & Universities
      </div>
    </div>

    <div id="campuses-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <!-- Populated via JavaScript -->
    </div>
  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-8 px-4 sm:px-6 mt-16 text-xs text-slate-400">
    <div class="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
      <div>
        <p class="font-medium text-slate-300">Non-partisan student voting guide directory prepared by Rann Bar-On.</p>
        <p class="text-[11px] text-slate-500 mt-0.5">Official voting data sourced from the North Carolina State Board of Elections and all 100 County Boards of Elections.</p>
      </div>
      <div class="flex items-center gap-4 text-xs">
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
      </div>
    </div>
  </footer>

  <script>
    const rawCampuses = %%CARDS_JSON%%;
    let campusesData = [...rawCampuses];
    let currentFilter = 'all';

    function haversine(lat1, lon1, lat2, lon2) {
      const R = 3958.8;
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return Math.round(R * c * 10) / 10;
    }

    function locateAndSortCampuses() {
      if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
      }

      const btn = document.getElementById('btn-geo-campuses');
      if (btn) btn.innerHTML = '<span class="animate-spin">⏳</span> Detecting...';

      navigator.geolocation.getCurrentPosition(
        position => {
          const uLat = position.coords.latitude;
          const uLon = position.coords.longitude;
          sessionStorage.setItem('nc_user_lat', uLat);
          sessionStorage.setItem('nc_user_lon', uLon);

          if (btn) btn.innerHTML = '✓ Proximity Active';

          campusesData = rawCampuses.map(c => ({
            ...c,
            distance: haversine(uLat, uLon, c.lat, c.lon)
          })).sort((a, b) => a.distance - b.distance);

          const nearest = campusesData[0];
          if (nearest) {
            const alertBox = document.getElementById('nearest-campus-alert');
            const alertName = document.getElementById('nearest-campus-name');
            const alertDetail = document.getElementById('nearest-campus-detail');
            const alertBtn = document.getElementById('nearest-campus-btn');

            alertName.innerText = `${nearest.name}`;
            alertDetail.innerText = `Located in ${nearest.city}, NC • ${nearest.distance} miles from your current GPS location`;
            alertBtn.href = `/${nearest.key}?autoloc=1`;
            alertBox.classList.remove('hidden');
          }

          filterCampuses();
        },
        error => {
          if (btn) btn.innerHTML = '📍 Locate Me';
          alert("Location permission was denied. You can still search by college or city name!");
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
      );
    }

    function renderCampuses(list) {
      const grid = document.getElementById('campuses-grid');
      const countEl = document.getElementById('results-count');
      countEl.innerText = `Showing ${list.length} Colleges & Universities`;

      if (list.length === 0) {
        grid.innerHTML = `
          <div class="col-span-full text-center py-12 bg-slate-900 border border-slate-800 rounded-2xl p-8">
            <div class="text-3xl mb-2">🔍</div>
            <h3 class="text-lg font-bold text-white">No campuses matched your search</h3>
            <p class="text-xs text-slate-400 mt-1">Try searching for a different college name, municipality, or county.</p>
            <button onclick="document.getElementById('campus-search').value = ''; setFilter('all');" class="mt-4 px-4 py-2 rounded-xl bg-rose-600 text-white font-semibold text-xs">Reset Search</button>
          </div>
        `;
        return;
      }

      grid.innerHTML = list.map((c, index) => {
        const idBadge = c.id_approved 
          ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✓ Approved Student ID</span>`
          : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">⚠️ Alternative Photo ID</span>`;

        const typeColor = c.type === 'UNC System' 
          ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
          : (c.type.includes('Community') ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-purple-500/10 text-purple-400 border-purple-500/20');

        const distBadge = c.distance !== undefined
          ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold ${index === 0 ? 'bg-emerald-500 text-white' : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'}">📍 ${c.distance} mi away</span>`
          : '';

        return `
        <div class="bg-slate-900 border ${index === 0 && c.distance !== undefined ? 'border-2 border-emerald-500 ring-2 ring-emerald-500/20' : 'border-slate-800 hover:border-slate-700'} rounded-2xl p-5 shadow-sm flex flex-col justify-between transition hover:-translate-y-0.5">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-lg">${c.icon}</span>
              <div class="flex items-center gap-1.5">
                ${distBadge}
                <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${typeColor}">${c.type}</span>
              </div>
            </div>
            <h3 class="font-bold text-white text-base leading-snug">${c.name}</h3>
            <p class="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
              <span>📍 ${c.city}, NC</span>
              <span>•</span>
              <span class="font-medium text-slate-300">${c.county}</span>
            </p>
            <div class="mt-3">
              ${idBadge}
            </div>
          </div>

          <div class="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
            <a href="/${c.key}?autoloc=1" class="flex-grow py-2 px-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs text-center transition shadow-sm">
              View Election Day Guide →
            </a>
            <a href="/${c.key}_qr.png" download="${c.short_name}_Vote_QR.png" class="py-2 px-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition" title="Download QR PNG">
              📥 QR
            </a>
          </div>
        </div>
        `;
      }).join('');
    }

    function filterCampuses() {
      const query = document.getElementById('campus-search').value.toLowerCase().trim();
      
      const filtered = campusesData.filter(c => {
        const matchesQuery = !query || 
          c.name.toLowerCase().includes(query) || 
          c.short_name.toLowerCase().includes(query) || 
          c.city.toLowerCase().includes(query) || 
          c.county.toLowerCase().includes(query);

        if (!matchesQuery) return false;

        if (currentFilter === 'unc') return c.type === 'UNC System';
        if (currentFilter === 'private') return c.type.includes('Independent');
        if (currentFilter === 'cc') return c.type.includes('Community');
        if (currentFilter === 'id_approved') return c.id_approved === true;

        return true;
      });

      renderCampuses(filtered);
    }

    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('bg-rose-600', 'text-white', 'border-rose-500');
        btn.classList.add('bg-slate-900', 'text-slate-300', 'border-slate-700');
      });
      const activeBtn = document.getElementById(`btn-${filter}`);
      if (activeBtn) {
        activeBtn.classList.remove('bg-slate-900', 'text-slate-300', 'border-slate-700');
        activeBtn.classList.add('bg-rose-600', 'text-white', 'border-rose-500');
      }
      filterCampuses();
    }

    window.addEventListener('DOMContentLoaded', () => {
      const savedLat = sessionStorage.getItem('nc_user_lat');
      const savedLon = sessionStorage.getItem('nc_user_lon');
      if (savedLat && savedLon) {
        campusesData = rawCampuses.map(c => ({
          ...c,
          distance: haversine(parseFloat(savedLat), parseFloat(savedLon), c.lat, c.lon)
        })).sort((a, b) => a.distance - b.distance);

        const btn = document.getElementById('btn-geo-campuses');
        if (btn) btn.innerHTML = '✓ Proximity Active';
      }
      renderCampuses(campusesData);
    });
  </script>

</body>
</html>
'''

campuses_html = campuses_template.replace('%%CARDS_JSON%%', cards_json_str)

with open(f"{MAIN_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
os.makedirs(f"{MAIN_DIR}/campuses", exist_ok=True)
with open(f"{MAIN_DIR}/campuses/index.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
with open(f"{LOCAL_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)

print("Master campuses.html updated for Election Day!")

# ==============================================================================
# 5. Generate Election Day Dynamic QR Portal (vote.html)
# ==============================================================================
print("5. Generating dynamic Main QR Code Portal (vote.html) for Election Day...")

with open(f"{CACHE_DIR}/county_early_voting_sites.json", 'r', encoding='utf-8') as f:
    sites_by_county = json.load(f)

# Build zip map from voting sites
zip_map = {}
for county, sites in sites_by_county.items():
    for s in sites:
        csz = s.get('SiteAddressCSZ', '') + ' ' + s.get('SiteAddressComplete', '')
        zips = re.findall(r'\b(2[78]\d{3})\b', csz)
        lat = s.get('SiteCoordLat')
        lon = s.get('SiteCoordLong')
        if zips and lat and lon:
            for z in zips:
                if z not in zip_map:
                    zip_map[z] = [round(lat, 4), round(lon, 4)]

local_zip_map_json_str = json.dumps(zip_map)
qr_b64_map_json_str = json.dumps(qr_b64_map)
duke_qr_b64 = qr_b64_map.get('dukevote', '')

vote_template = '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Campus Election Day Voting Portal & QR Code | Rann Bar-On</title>
  <meta name="description" content="Dynamic NC student Election Day voting portal. Automatically generates the QR code and Election Day voting guide for your college or university using geolocation or zip code.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/vote">
  <meta property="og:title" content="North Carolina Campus Election Day Voting Portal">
  <meta property="og:description" content="Dynamic QR code and Election Day voting guide for every college and university in North Carolina.">
  <meta property="og:image" content="https://rannbar-on.com/dukevote_qr.png">

  <!-- Tailwind CSS -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    if (!window.tailwind) {
      document.write('<script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"><\\/script>');
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    
    :root {
      --bg: #070b14;
      --card-bg: #0f172a;
      --card-border: #1e293b;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      overflow-x: hidden;
    }

    .font-mono {
      font-family: 'JetBrains Mono', monospace;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col justify-between bg-slate-950 text-slate-100 antialiased">

  <!-- Top Announcement Bar (Election Day Mode) -->
  <div class="bg-gradient-to-r from-red-950 via-rose-950 to-slate-950 px-4 py-2 text-center text-xs sm:text-sm font-bold text-slate-100 border-b border-rose-900/50 shadow-md">
    <span class="inline-flex items-center gap-2">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
      </span>
      <span>🔴 Early Voting Has Ended • <b>ELECTION DAY IS TUESDAY, NOVEMBER 3, 2026</b> • Polls Open <b>6:30 AM – 7:30 PM</b></span>
    </span>
  </div>

  <!-- Header / Navigation -->
  <header class="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur sticky top-0 z-40">
    <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <a href="https://rannbar-on.com/" class="flex items-center gap-2 group">
        <div class="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center font-bold text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition">
          R
        </div>
        <div>
          <span class="font-bold tracking-tight text-white block text-sm sm:text-base leading-none">Rann Bar-On</span>
          <span class="text-[11px] text-slate-400 font-mono">rannbar-on.com</span>
        </div>
      </a>
      <div class="flex items-center gap-3">
        <a href="/campuses" class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition">
          Browse All 111 NC Campuses →
        </a>
      </div>
    </div>
  </header>

  <!-- Main Container -->
  <main class="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12 flex-grow flex flex-col items-center justify-center">

    <div class="text-center max-w-2xl mx-auto mb-8">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30 mb-3">
        <span>📍 Smart QR Code Portal</span>
        <span class="text-slate-600">•</span>
        <span>Election Day Edition</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
        Scan Your Campus Election Day Guide
      </h1>
      <p class="text-xs sm:text-sm text-slate-300 mt-2 leading-relaxed">
        Early voting has ended. This QR code automatically updates to point to your college or university's Election Day voting guide (assigned precinct lookup, voter ID status, and candidate guides). Use your device location or enter a zip code below to customize it instantly.
      </p>
    </div>

    <!-- The Main Dynamic QR Card -->
    <div class="w-full max-w-md bg-gradient-to-b from-slate-900 to-slate-950 border-2 border-rose-500/40 rounded-3xl p-6 sm:p-8 shadow-2xl text-center relative overflow-hidden mb-8">
      
      <!-- Dynamic School Header -->
      <div class="mb-4">
        <div id="qr-status-badge" class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-rose-950/80 text-rose-300 border border-rose-700/60 mb-2">
          <span>🔴 Election Day Mode</span>
        </div>
        <h2 id="qr-school-name" class="text-xl sm:text-2xl font-black text-white tracking-tight">
          Duke University
        </h2>
        <p id="qr-school-loc" class="text-xs text-slate-400 mt-0.5 font-medium">
          Durham, NC • Durham County
        </p>
      </div>

      <!-- High-Resolution QR Box -->
      <div class="bg-white p-4 sm:p-5 rounded-2xl shadow-xl border-4 border-rose-500/30 inline-block my-2 transition duration-300">
        <img id="main-qr-img" src="data:image/png;base64,%%DUKE_QR_B64%%" alt="NC Campus Election Day Voting QR Code" class="w-52 h-52 sm:w-56 sm:h-56 object-contain mx-auto" />
      </div>

      <!-- URL Pill -->
      <div id="qr-guide-url" class="mt-3 inline-block font-mono text-xs font-semibold text-rose-300 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 select-all">
        rannbar-on.com/dukevote
      </div>

      <!-- Quick Action Buttons -->
      <div class="mt-5 space-y-2">
        <a id="qr-guide-btn" href="/dukevote?autoloc=1" class="w-full py-3 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs sm:text-sm transition shadow-lg flex items-center justify-center gap-2">
          <span>Open Duke Election Day Guide</span>
          <span>→</span>
        </a>

        <div class="grid grid-cols-3 gap-2 text-xs">
          <button onclick="copyCurrentLink()" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition flex items-center justify-center gap-1">
            <span>📋</span><span>Copy</span>
          </button>
          <a id="qr-dl-png" href="/dukevote_qr.png" download="Duke_Vote_QR.png" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition flex items-center justify-center gap-1">
            <span>📥</span><span>PNG</span>
          </a>
          <a id="qr-dl-svg" href="/dukevote_qr.svg" download="Duke_Vote_QR.svg" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition flex items-center justify-center gap-1">
            <span>📥</span><span>SVG</span>
          </a>
        </div>
      </div>
    </div>

    <!-- Dynamic Location / Zip Controls Container -->
    <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-5">
      
      <!-- Option 1: Geolocation -->
      <div>
        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Option 1: Device Location (Fastest)</label>
        <button onclick="triggerGeolocation()" id="btn-geo" class="w-full py-2.5 px-4 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-rose-300 font-bold text-xs transition flex items-center justify-center gap-2">
          <span>📍</span>
          <span>Use My Current Location to Update QR</span>
        </button>
        <div id="geo-status-text" class="text-[11px] text-slate-400 mt-1.5 min-h-[16px] text-center"></div>
      </div>

      <div class="relative flex py-1 items-center">
        <div class="flex-grow border-t border-slate-800"></div>
        <span class="flex-shrink mx-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">or</span>
        <div class="flex-grow border-t border-slate-800"></div>
      </div>

      <!-- Option 2: NC Zip Code Lookup -->
      <div>
        <label for="zip-input" class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Option 2: Enter NC Zip Code</label>
        <form onsubmit="handleZipSubmit(event)" class="flex gap-2">
          <input type="text" id="zip-input" maxlength="5" pattern="[0-9]{5}" placeholder="e.g. 27708, 27514, 28608..." 
                 class="w-full bg-slate-950 border border-slate-700 focus:border-rose-500 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none" />
          <button type="submit" id="btn-zip-submit" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-bold text-xs transition shrink-0">
            Update QR
          </button>
        </form>
        <div id="zip-status-text" class="text-[11px] text-slate-400 mt-1.5 min-h-[16px] text-center"></div>
      </div>

      <div class="relative flex py-1 items-center">
        <div class="flex-grow border-t border-slate-800"></div>
        <span class="flex-shrink mx-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">or</span>
        <div class="flex-grow border-t border-slate-800"></div>
      </div>

      <!-- Option 3: Manual Campus Selection -->
      <div>
        <label for="campus-select" class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Option 3: Select College / University</label>
        <select id="campus-select" onchange="handleSelectCampus(this.value)" class="w-full bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-rose-500 font-medium">
          <option value="">Choose an NC College/University...</option>
          %%CAMPUS_OPTIONS%%
        </select>
      </div>

    </div>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-6 px-4 text-center text-xs text-slate-500">
    <div class="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
      <span>Non-partisan student voting guide portal prepared by Rann Bar-On.</span>
      <div class="flex items-center gap-4">
        <a href="/campuses" class="text-blue-400 hover:underline">All 111 NC Campuses</a>
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
      </div>
    </div>
  </footer>

  <script>
    const qrB64Map = %%QR_B64_MAP%%;
    const allCampuses = %%CAMPUS_GEO%%;
    const localZips = %%LOCAL_ZIPS%%;
    let currentCampus = allCampuses.find(c => c.key === 'dukevote') || allCampuses[0];

    function haversine(lat1, lon1, lat2, lon2) {
      const R = 3958.8;
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return Math.round(R * c * 10) / 10;
    }

    function findClosestCampus(uLat, uLon) {
      let closest = allCampuses[0];
      let minDistance = Infinity;

      allCampuses.forEach(campus => {
        const dist = haversine(uLat, uLon, campus.lat, campus.lon);
        if (dist < minDistance) {
          minDistance = dist;
          closest = campus;
        }
      });

      return { campus: closest, distance: minDistance };
    }

    function updateCardDisplay(campus, methodLabel, distanceStr) {
      currentCampus = campus;

      // School info
      document.getElementById('qr-school-name').innerText = campus.name;
      document.getElementById('qr-school-loc').innerText = `${campus.city}, NC • ${campus.county}`;

      // Status badge
      const badge = document.getElementById('qr-status-badge');
      if (distanceStr) {
        badge.innerHTML = `<span>📍 ${methodLabel}: ${distanceStr} mi away</span>`;
        badge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 mb-2';
      } else {
        badge.innerHTML = `<span>🔴 ${methodLabel}</span>`;
        badge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-rose-950/80 text-rose-300 border border-rose-700/60 mb-2';
      }

      // QR Image
      const b64 = qrB64Map[campus.key];
      const imgEl = document.getElementById('main-qr-img');
      if (b64) {
        imgEl.src = `data:image/png;base64,${b64}`;
      } else {
        imgEl.src = `/${campus.key}_qr.png`;
      }

      // URL Pill
      document.getElementById('qr-guide-url').innerText = `rannbar-on.com/${campus.key}`;

      // Button
      const btn = document.getElementById('qr-guide-btn');
      btn.href = `/${campus.key}?autoloc=1`;
      btn.innerHTML = `<span>Open ${campus.short_name} Election Day Guide</span><span>→</span>`;

      // Downloads
      const dlPng = document.getElementById('qr-dl-png');
      dlPng.href = `/${campus.key}_qr.png`;
      dlPng.download = `${campus.short_name}_Vote_QR.png`;

      const dlSvg = document.getElementById('qr-dl-svg');
      dlSvg.href = `/${campus.key}_qr.svg`;
      dlSvg.download = `${campus.short_name}_Vote_QR.svg`;
    }

    function triggerGeolocation() {
      const statusText = document.getElementById('geo-status-text');
      const btn = document.getElementById('btn-geo');
      
      if (!navigator.geolocation) {
        statusText.innerText = "Geolocation not supported by your browser.";
        return;
      }

      btn.innerHTML = '<span class="animate-spin">⏳</span> Detecting GPS Location...';
      statusText.innerText = "Requesting permission...";

      navigator.geolocation.getCurrentPosition(
        position => {
          const uLat = position.coords.latitude;
          const uLon = position.coords.longitude;
          sessionStorage.setItem('nc_user_lat', uLat);
          sessionStorage.setItem('nc_user_lon', uLon);

          const result = findClosestCampus(uLat, uLon);
          btn.innerHTML = '<span>✓</span> <span>Location Matched!</span>';
          statusText.innerText = `Detected nearest: ${result.campus.name} (${result.distance} miles)`;
          updateCardDisplay(result.campus, 'Nearest Detected', result.distance);
        },
        error => {
          btn.innerHTML = '<span>📍</span> <span>Use My Current Location to Update QR</span>';
          statusText.innerText = "Location permission denied. Please enter your zip code below.";
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
      );
    }

    function handleZipSubmit(e) {
      e.preventDefault();
      const zip = document.getElementById('zip-input').value.trim();
      const statusText = document.getElementById('zip-status-text');

      if (!/^[0-9]{5}$/.test(zip)) {
        statusText.innerText = "Please enter a valid 5-digit zip code.";
        return;
      }

      // Check zip coordinates
      const coords = localZips[zip];
      if (coords) {
        const result = findClosestCampus(coords[0], coords[1]);
        statusText.innerText = `Matched zip ${zip} → Nearest: ${result.campus.name} (~${result.distance} miles)`;
        updateCardDisplay(result.campus, `Zip ${zip} Matched`, result.distance);
        return;
      }

      // Fallback: check city of campuses
      const cityMatch = allCampuses.find(c => c.city.toLowerCase() === zip.toLowerCase());
      if (cityMatch) {
        updateCardDisplay(cityMatch, `Zip Match`, null);
        return;
      }

      // Fallback NC approximate centroid search
      const result = findClosestCampus(35.7796, -78.6382);
      statusText.innerText = `Zip ${zip} mapped to closest NC university: ${result.campus.name}`;
      updateCardDisplay(result.campus, `Zip ${zip} Matched`, null);
    }

    function handleSelectCampus(key) {
      if (!key) return;
      const cleanKey = key.replace('/', '');
      const campus = allCampuses.find(c => c.key === cleanKey);
      if (campus) {
        updateCardDisplay(campus, 'Manually Selected', null);
      }
    }

    function copyCurrentLink() {
      navigator.clipboard.writeText(`https://rannbar-on.com/${currentCampus.key}`);
      alert(`Copied link to ${currentCampus.name} voting guide!`);
    }

    // Auto-detect if session coords already exist
    window.addEventListener('DOMContentLoaded', () => {
      const savedLat = sessionStorage.getItem('nc_user_lat');
      const savedLon = sessionStorage.getItem('nc_user_lon');
      if (savedLat && savedLon) {
        const result = findClosestCampus(parseFloat(savedLat), parseFloat(savedLon));
        updateCardDisplay(result.campus, 'Saved Location', result.distance);
        document.getElementById('geo-status-text').innerText = `Using previous location: ${result.campus.name} (${result.distance} miles)`;
      }
    });
  </script>

</body>
</html>
'''

vote_html = vote_template.replace('%%DUKE_QR_B64%%', duke_qr_b64)
vote_html = vote_html.replace('%%CAMPUS_OPTIONS%%', campus_options_html)
vote_html = vote_html.replace('%%QR_B64_MAP%%', qr_b64_map_json_str)
vote_html = vote_html.replace('%%CAMPUS_GEO%%', campus_geo_json_str)
vote_html = vote_html.replace('%%LOCAL_ZIPS%%', local_zip_map_json_str)

with open(f"{MAIN_DIR}/vote.html", 'w', encoding='utf-8') as f:
    f.write(vote_html)
os.makedirs(f"{MAIN_DIR}/vote", exist_ok=True)
with open(f"{MAIN_DIR}/vote/index.html", 'w', encoding='utf-8') as f:
    f.write(vote_html)
with open(f"{LOCAL_DIR}/vote.html", 'w', encoding='utf-8') as f:
    f.write(vote_html)

print("Dynamic vote.html updated for Election Day!")
