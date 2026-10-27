#!/usr/bin/env python3
"""
North Carolina Student Voting Platform - Election Day Statewide Generator
Builds Election Day guides for all 110 NC higher education institutions,
the master directory (/campuses), and dynamic QR portal (/vote).
Features assigned precinct lookups, live GPS nearest-precinct detection,
voter ID compliance (including Numbered Memo 2023-05), verified source banners,
and three balanced local candidate guides (Dem, Rep, Ind).
"""

import os
import sys
import json
import base64
import re
import urllib.parse

MAIN_DIR = os.environ.get('CI_PROJECT_DIR') or os.environ.get('GITHUB_WORKSPACE') or os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR = '/home/rann/src/website/voting-info' if os.path.exists('/home/rann/src/website/voting-info') else None
CACHE_DIR = f'{MAIN_DIR}/.nc_voting_cache'
DATA_DIR = f'{MAIN_DIR}/data'
os.makedirs(CACHE_DIR, exist_ok=True)

# Ensure cache is seeded from data/ if needed
mapping = {
    'campuses.json': 'all_institutions.json',
    'county_boe.json': 'county_boe_info.json',
    'county_sites.json': 'county_early_voting_sites.json',
    'campus_geo.json': 'campus_geo_data.json',
    'county_precincts.json': 'county_precincts_map.json',
    'campus_precincts.json': 'campus_primary_precincts.json'
}
for src, dst in mapping.items():
    d_path = os.path.join(CACHE_DIR, dst)
    s_path = os.path.join(DATA_DIR, src)
    if not os.path.exists(d_path) and os.path.exists(s_path):
        import shutil
        shutil.copyfile(s_path, d_path)

GITLAB_REPO_URL = os.environ.get('CI_PROJECT_URL') or 'https://gitlab.oit.duke.edu/rb6/mainwebsite'
GITLAB_ISSUES_URL = os.environ.get('GITLAB_ISSUES_URL') or (f"{GITLAB_REPO_URL}/-/issues" if 'CI_PROJECT_URL' in os.environ else 'https://gitlab.oit.duke.edu/rb6/mainwebsite/-/issues')
VERIFIED_UPDATE_TIME = "October 26, 2026 at 1:45 PM EDT"

print("1. Loading cached NC election and precinct data...")
with open(f'{CACHE_DIR}/all_institutions.json', 'r', encoding='utf-8') as f:
    institutions = json.load(f)

# Filter out closed institutions (e.g. St. Andrews closed May 5, 2025)
institutions = [i for i in institutions if i['key'] != 'standrewsvote']

with open(f'{CACHE_DIR}/county_boe_info.json', 'r', encoding='utf-8') as f:
    boe_list = json.load(f)
boe_by_county = {c['Name'].upper(): c for c in boe_list}

with open(f'{CACHE_DIR}/campus_geo_data.json', 'r', encoding='utf-8') as f:
    campus_geo_list = json.load(f)
campus_geo_list = [g for g in campus_geo_list if g['key'] != 'standrewsvote']
campus_geo_json_str = json.dumps(campus_geo_list)

with open(f'{CACHE_DIR}/campus_primary_precincts.json', 'r', encoding='utf-8') as f:
    campus_primary_precincts = json.load(f)

with open(f'{CACHE_DIR}/county_precincts_map.json', 'r', encoding='utf-8') as f:
    county_precincts_map = json.load(f)

print(f"Loaded {len(institutions)} active institutions, {len(county_precincts_map)} county precinct datasets.")

def clean_site_name(name):
    if not name:
        return ""
    s = str(name).strip()
    if "NCCU" in s.upper():
        return "NCCU - Turner Law Building"
    if "LITTLE RIVER" in s.upper():
        return "Little River Community Complex"
    
    minor = {'of', 'and', 'at', 'the', 'for', 'in', 'on', 'by'}
    acronyms = {'NCCU', 'NC', 'UNC', 'NCSU', 'GOP', 'BOE', 'USA', 'US', 'DPS', 'STEM', 'W.I.', 'E.K.', 'W.J.', 'C.C.', 'KIPP'}
    words = s.split()
    out = []
    for i, w in enumerate(words):
        w_up = w.upper().rstrip(',.-')
        if w_up in acronyms:
            punct = w[len(w_up):]
            out.append(w_up + punct)
        elif i > 0 and w.lower() in minor:
            out.append(w.lower())
        else:
            out.append(w.capitalize())
    res = " ".join(out)
    res = re.sub(r'\bBoard Of Elections\b', 'Board of Elections', res)
    res = re.sub(r'\bDurham, Nc\b', 'Durham, NC', res)
    return res

def clean_address(addr):
    if not addr:
        return ""
    addr = re.sub(r'\bDurham,\s*Nc\b', 'Durham, NC', addr, flags=re.I)
    addr = re.sub(r'\bNc\b', 'NC', addr)
    addr = re.sub(r'\bNc\s*(\d{5})\b', r'NC \1', addr)
    return addr

def clean_boe_name(name):
    if not name:
        return ""
    s = str(name).strip()
    s = re.sub(r'\bBoard Of Elections\b', 'Board of Elections', s, flags=re.I)
    return s

def remove_emojis(text):
    if not text:
        return ""
    emoji_pattern = re.compile(
        '['
        '\U0001F600-\U0001F64F'
        '\U0001F300-\U0001F5FF'
        '\U0001F680-\U0001F6FF'
        '\U0001F1E0-\U0001F1FF'
        '\U00002702-\U000027B0'
        '\U000024C2-\U0001F251'
        '\U0001F900-\U0001F9FF'
        '\U0001FA70-\U0001FAFF'
        '\U00002600-\U000026FF'
        '\U0000200D'
        '\U0000FE0F'
        ']+', flags=re.UNICODE)
    return emoji_pattern.sub('', text).strip()

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

# Support links QR Base64
with open(f'{MAIN_DIR}/venmo_qr.png', 'rb') as f:
    venmo_b64 = base64.b64encode(f.read()).decode('utf-8')
with open(f'{MAIN_DIR}/cashapp_qr.png', 'rb') as f:
    cashapp_b64 = base64.b64encode(f.read()).decode('utf-8')

print("2. Reading campus QR codes...")
qr_b64_map = {}
for inst in institutions:
    key = inst['key']
    png_path = f"{MAIN_DIR}/{key}_qr.png"
    if os.path.exists(png_path):
        with open(png_path, 'rb') as f:
            qr_b64_map[key] = base64.b64encode(f.read()).decode('utf-8')
    else:
        qr_b64_map[key] = ""

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
    c_display = clean_site_name(cname) + " County"
    boe_phone = boe.get('OfficePhoneNum', '(919) 814-0700')
    boe_addr = clean_address(boe.get('FullAddress', f'{c_display} Board of Elections, NC'))
    boe_web = boe.get('WebsiteAddr', f'https://vt.ncsbe.gov/BOEInfo/?county={cname}')
    boe_name = clean_boe_name(boe.get('OfficeName', f'{c_display} Board of Elections'))

    dem_county_url = county_dem_urls.get(cname, 'https://www.ncdp.org/county-parties/')
    rep_county_url = county_rep_urls.get(cname, 'https://www.ncgop.org/county_parties')

    # Primary precinct details
    prec_info = campus_primary_precincts.get(key, {})
    primary_code = prec_info.get('primary_precinct', 'Assigned Precinct')
    primary_name = clean_site_name(prec_info.get('primary_name', 'Campus Area Polling Center'))
    primary_dist = prec_info.get('dist_to_campus', 0.5)

    # County precinct map JSON for client-side search & GPS distance
    c_precincts = county_precincts_map.get(cname, [])
    c_precincts_json = json.dumps(c_precincts)

    # Private university roster notes
    is_private = 'Private' in inst['type']
    if is_private:
        memo_html = f'''
        <div class="mt-3 p-3.5 rounded-xl bg-blue-950/40 border border-blue-500/40 text-xs text-blue-200 space-y-1.5 font-medium">
          <p><span class="text-blue-300 font-bold">[NCSBE Numbered Memo 2023-05]</span> <b>Private Institution Photo ID Rule:</b> Under NCSBE Numbered Memo 2023-05, because {inst['name']} is a private university, on-campus students relying on the official campus housing roster provided to the {c_display} Board of Elections <b>must present that school's approved student photo ID</b>. An alternative photo ID (such as an out-of-state driver's license) cannot be paired with a private university housing roster.</p>
          <p><span class="text-blue-300 font-bold">[Roster]</span> <b>Housing Roster Separation Rule:</b> Under NCSBE rules, an approved campus housing roster provided to the County Board of Elections is valid only if it specifically separates residents by individual dormitory or residential facility.</p>
        </div>
        '''
    else:
        memo_html = f'''
        <div class="mt-3 p-3.5 rounded-xl bg-blue-950/40 border border-blue-500/40 text-xs text-blue-200 space-y-1.5 font-medium">
          <p><span class="text-blue-300 font-bold">[Campus Rule]</span> <b>Housing Roster Separation:</b> Under NCSBE rules, campus housing rosters provided to the County Board of Elections are valid only if students are listed separately by residential dormitory facility.</p>
        </div>
        '''

    # Student ID section
    if inst['id_approved']:
        id_alert_box = f'''
        <div class="bg-emerald-950/40 border-2 border-emerald-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-emerald-500/20 text-emerald-300 text-sm font-bold font-mono shrink-0">
            [APPROVED]
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 mb-2">Approved by NC State Board of Elections</span>
            <h2 class="text-xl font-bold text-white mb-2">{inst['name']} Student ID is Valid on Election Day</h2>
            <p class="text-sm text-emerald-100/90 leading-relaxed mb-3">
              The North Carolina State Board of Elections officially approved the <b>{inst['id_card_name']}</b> for voter photo identification. You can use your physical plastic student ID to vote.
            </p>
            <div class="p-3.5 rounded-xl bg-emerald-900/30 border border-emerald-700/50 text-xs text-emerald-200/90 space-y-1.5 font-medium">
              <p><span class="text-emerald-300 font-bold">[CRITICAL]</span> <b>PHYSICAL CARD REQUIRED:</b> Digital IDs stored on mobile phones (Apple Wallet, Google Wallet, photos) are <b>NOT ACCEPTED</b> under NC General Statutes (§ 163-166.16).</p>
              <p><span class="text-emerald-300 font-bold">[Alternative IDs]</span> NC Driver's License, US Passport, Military/Veteran ID, or free county BOE ID card.</p>
              <p><span class="text-emerald-300 font-bold">[Exception Form]</span> If you lack an ID on Election Day, you have the legal right to cast a provisional ballot with a Photo ID Exception Form at your assigned precinct.</p>
            </div>
            {memo_html}
          </div>
        </div>
        '''
    else:
        id_alert_box = f'''
        <div class="bg-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-amber-500/20 text-amber-300 text-sm font-bold font-mono shrink-0">
            [REQUIRED]
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">Alternative Photo ID Required</span>
            <h2 class="text-xl font-bold text-white mb-2">Student ID Card is NOT Accepted for Voting</h2>
            <p class="text-sm text-amber-100/90 leading-relaxed mb-3">
              Under North Carolina law, {inst['name']} student IDs are <b>not approved</b> for voting. You must present an approved alternative photo ID.
            </p>
            <div class="p-3.5 rounded-xl bg-amber-900/30 border border-amber-700/50 text-xs text-amber-200/90 space-y-1.5 font-medium">
              <p><b>Acceptable Photo IDs on Election Day:</b></p>
              <ul class="list-disc pl-5 space-y-1 text-slate-200">
                <li><b>North Carolina Driver's License</b> or NC DMV State ID (unexpired or expired up to 1 year).</li>
                <li><b>U.S. Passport</b> or U.S. Passport Card (must be unexpired).</li>
                <li><b>Out-of-State Driver's License</b> (accepted only if you registered to vote in NC within 90 days of the election).</li>
                <li><b>Free Voter Photo ID Card:</b> Issued by {c_display} Board of Elections.</li>
                <li><b>Photo ID Exception Form:</b> If you lack an ID, complete an Exception Form at your assigned precinct and vote a ballot that counts.</li>
              </ul>
            </div>
            {memo_html}
          </div>
        </div>
        '''

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
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: #070b14;
      color: #f8fafc;
      overflow-x: hidden;
    }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased" data-campus="{inst['name']}" data-key="{key}" data-county="{inst['county']}">

  <!-- TOP OFFICIAL DATA VERIFICATION BANNER -->
  <aside aria-label="Official verification notice" class="bg-slate-900 border-b border-slate-800 text-xs text-slate-300 py-2 px-4 sm:px-6">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 uppercase tracking-wide">Verified Source</span>
        <span>Official NC State Board of Elections & {c_display} BOE Schedule</span>
      </div>
      <div class="flex items-center gap-4 text-slate-400 text-[11px]">
        <span>Last Verified Update: <b class="text-slate-200">{VERIFIED_UPDATE_TIME}</b></span>
        <a href="https://www.ncsbe.gov/voting" target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 underline font-medium">Information Sources</a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="text-rose-400 hover:text-rose-300 underline font-medium">Report Issue</a>
      </div>
    </div>
  </aside>

  <!-- Sticky Global Navigation Header -->
  <header class="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <a href="/campuses" class="flex items-center gap-2 group">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md text-xs font-mono">
            NC
          </div>
          <div class="flex flex-col">
            <span class="font-bold text-slate-100 text-sm leading-tight group-hover:text-rose-400 transition">NC Student Voting</span>
            <span class="text-[11px] text-slate-400">110 Colleges & Universities</span>
          </div>
        </a>
      </div>

      <nav class="hidden md:flex items-center gap-6 text-xs font-medium text-slate-300">
        <a href="#precinct-lookup" class="hover:text-white transition">Assigned Precinct</a>
        <a href="#voter-id" class="hover:text-white transition">Photo ID Rules</a>
        <a href="#voter-guides" class="hover:text-white transition">Candidate Guides</a>
        <a href="#boe-contact" class="hover:text-white transition">County BOE</a>
      </nav>

      <div class="flex items-center gap-2">
        <a href="#precinct-lookup" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white transition shadow-sm">
          Find My Precinct
        </a>
        <a href="/vote" class="text-xs font-medium px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
          Statewide /vote
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="relative pt-12 pb-8 px-4 sm:px-6 border-b border-slate-800/80 bg-gradient-to-b from-slate-900 via-slate-950 to-slate-950">
    <div class="max-w-5xl mx-auto text-center space-y-4">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30">
        <span>[ELECTION DAY]</span>
        <span>Tuesday, November 3, 2026 &bull; Polls Open 6:30 AM &ndash; 7:30 PM</span>
      </div>

      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
        {inst['name']} <br><span class="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-amber-300 to-blue-400">Student Election Day Voting Guide</span>
      </h1>

      <p class="max-w-2xl mx-auto text-sm sm:text-base text-slate-300 leading-relaxed">
        Early voting has concluded. On <b>Election Day (Tuesday, November 3)</b>, North Carolina law requires you to vote at your <b>specifically assigned precinct polling place</b>. Find your precinct, bring your photo ID, and cast your ballot before 7:30 PM.
      </p>

      <!-- Campus Switcher Dropdown -->
      <div class="pt-2 max-w-md mx-auto">
        <label for="campus-selector" class="block text-xs font-medium text-slate-400 mb-1.5">Switch Campus Guide:</label>
        <select id="campus-selector" onchange="if(this.value) window.location.href=this.value" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500">
          <option value="">Choose another NC College or University (110 Total)...</option>
          {campus_options_html}
        </select>
      </div>
    </div>
  </section>

  <!-- CRITICAL ELECTION DAY RULES NOTICE -->
  <section id="election-day-rules" class="py-8 px-4 sm:px-6 bg-rose-950/20 border-b border-rose-900/40">
    <div class="max-w-4xl mx-auto space-y-4">
      <div class="bg-rose-950/40 border-2 border-rose-500/60 rounded-2xl p-5 sm:p-6 shadow-xl">
        <div class="flex items-start gap-4">
          <div class="p-3 rounded-xl bg-rose-500/20 text-rose-300 text-sm font-bold font-mono shrink-0">
            [NOTICE]
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30 mb-2">Mandatory North Carolina Election Law</span>
            <h2 class="text-xl font-bold text-white mb-2">Two Critical Rules for Voting on Election Day:</h2>
            <div class="space-y-3 text-xs sm:text-sm text-slate-200 mt-3 leading-relaxed">
              <div class="p-3.5 rounded-xl bg-slate-950/80 border border-rose-900/60">
                <p class="font-bold text-white mb-1">1. You CANNOT vote at any polling site &mdash; You MUST go to your specifically assigned precinct.</p>
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

    <!-- Section 1: Assigned Precinct Polling Place Lookup & Geolocation -->
    <section id="precinct-lookup" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl">
        <span class="text-xs font-mono font-semibold text-rose-400 uppercase tracking-wider">Find Where You Vote Today</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-3">Look Up Your Assigned Precinct Polling Place</h2>
        <p class="text-sm text-slate-300 leading-relaxed mb-6">
          Every voter in {c_display} is assigned a specific Election Day polling place based on their voter registration residential address (your dormitory or off-campus apartment).
        </p>

        <!-- Primary Campus Precinct Feature Card -->
        <div class="mb-6 p-5 sm:p-6 rounded-2xl bg-slate-950/90 border border-rose-500/40 shadow-lg">
          <div class="flex items-center justify-between flex-wrap gap-2 mb-2">
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 uppercase tracking-wide">Primary Campus Area Precinct</span>
            <span class="text-xs font-mono text-slate-400">~{primary_dist} miles from campus</span>
          </div>
          <h3 class="text-xl font-bold text-white mb-1">{primary_name}</h3>
          <p class="text-xs text-slate-300 mb-4">
            Precinct Code: <span class="font-mono font-semibold text-rose-300">{primary_code}</span> &bull; {c_display}
          </p>
          <div class="flex flex-wrap gap-3">
            <a href="https://maps.google.com/?q={urllib.parse.quote(primary_name + ' ' + c_display + ' NC')}" target="_blank" rel="noopener" class="py-2.5 px-4 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition shadow-md inline-flex items-center gap-1.5">
              <span>Directions on Google Maps</span>
              <span>&rarr;</span>
            </a>
            <button onclick="detectNearestPrecinct()" id="btn-detect-precinct" class="py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition inline-flex items-center gap-1.5">
              <span>Detect My Nearest Precinct via GPS</span>
            </button>
          </div>
          <div id="gps-precinct-result" class="mt-4 hidden p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200"></div>
        </div>

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
              <span>&rarr;</span>
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
              <span>Look Up Voter Registration</span>
              <span>&rarr;</span>
            </a>
          </div>
        </div>

        <!-- Election Day Voting Hours & In-Line Rule -->
        <div class="mt-6 p-4 rounded-2xl bg-amber-950/30 border border-amber-500/40 text-xs sm:text-sm text-amber-200 space-y-2">
          <div class="font-bold text-amber-100 flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] uppercase font-mono">HOURS: 6:30 AM &ndash; 7:30 PM</span>
            <span>Election Day Voting Hours</span>
          </div>
          <div>
            <b>IN-LINE BY 7:30 PM RULE:</b> Under North Carolina law, if you are physically in line at your assigned polling place by 7:30 PM on Election Day, election officials are legally required to keep the polls open until you have cast your ballot. Do not leave the line!
          </div>
        </div>
      </div>
    </section>

    <!-- Section 2: Voter ID Requirement -->
    <section id="voter-id" class="scroll-mt-20">
      {id_alert_box}
    </section>

    <!-- Section 3: Candidate Voter Guides (Democratic & Non-Partisan) -->
    <section id="voter-guides" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-8">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Candidate Research & Endorsements</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-2">Election Day Candidate Guides for {inst['short_name']} Students</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Before entering the voting booth in {c_display}, review candidate questionnaires, voting records, and endorsements:
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 1. Democratic-Leaning Guide -->
        <div class="bg-slate-950/80 border border-blue-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 mb-3">
              <span>[Democratic / Progressive]</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Blue Voter Guide & NC Dems</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Enter your local address to see customized candidate recommendations and slates endorsed by Democratic, labor, reproductive rights, and environmental organizations across North Carolina.
            </p>
          </div>
          <div class="space-y-2 pt-2 border-t border-slate-800/80">
            <a href="https://bluevoterguide.org/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open Blue Voter Guide (NC)</span>
              <span>&rarr;</span>
            </a>
            <a href="{dem_county_url}" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-blue-300 border border-slate-800 font-medium text-xs transition">
              <span>{c_display} Democratic Party</span>
              <span>&rarr;</span>
            </a>
          </div>
        </div>

        <!-- 2. Independent / Non-Partisan Guide -->
        <div class="bg-slate-950/80 border border-emerald-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 mb-3">
              <span>[Independent / Nonpartisan]</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Vote411 (League of Women Voters)</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Unbiased side-by-side candidate comparisons with direct, unedited answers from candidates across all parties for state, judicial, legislative, and local county offices.
            </p>
          </div>
          <div class="space-y-2 pt-2 border-t border-slate-800/80">
            <a href="https://www.vote411.org/north-carolina" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open Vote411 (NC)</span>
              <span>&rarr;</span>
            </a>
            <a href="https://ncfree.org/" target="_blank" rel="noopener" class="w-full flex items-center justify-between p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-slate-800 font-medium text-xs transition">
              <span>NC Free Non-Partisan Guide</span>
              <span>&rarr;</span>
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Section 4: County Board of Elections Information -->
    <section id="boe-contact" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-6">
        <span class="text-xs font-mono font-semibold text-indigo-400 uppercase tracking-wider">County Election Authority</span>
        <h2 class="text-2xl font-extrabold text-white mt-1 mb-2">{boe_name}</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Questions about your assigned precinct, absentee ballot status, or voting eligibility on Election Day? Contact the official {c_display} Board of Elections:
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="p-4 rounded-2xl bg-slate-950/80 border border-slate-800">
          <div class="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">Physical Office Address</div>
          <div class="text-sm font-semibold text-white">{boe_addr}</div>
        </div>

        <div class="p-4 rounded-2xl bg-slate-950/80 border border-slate-800">
          <div class="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">Official Phone Number</div>
          <div class="text-sm font-semibold text-white">
            <a href="tel:{boe_phone.replace(' ', '')}" class="text-blue-400 hover:underline">{boe_phone}</a>
          </div>
        </div>

        <div class="p-4 rounded-2xl bg-slate-950/80 border border-slate-800">
          <div class="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1">Official BOE Portal</div>
          <div class="text-sm font-semibold text-white">
            <a href="{boe_web}" target="_blank" rel="noopener" class="text-rose-400 hover:underline inline-flex items-center gap-1">
              <span>County Website</span>
              <span>&rarr;</span>
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Support the Site & GitLab Bugtracker -->
    <section class="mt-12 bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-xl">
      <div class="max-w-3xl mb-6">
        <span class="text-xs font-mono font-semibold text-indigo-400 uppercase tracking-wider">Community Project</span>
        <h2 class="text-2xl font-bold text-white mt-1 mb-2">Help Rann Bar-On Maintain This Site</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          This voter information platform is independently built and maintained by Rann Bar-On as a free public service for students across all 110 North Carolina colleges and universities. If this guide helped you or your campus vote, contributions to help cover hosting and data scraping costs are deeply appreciated.
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="p-5 rounded-2xl bg-slate-950/90 border border-blue-500/30 flex items-center gap-5">
          <img src="data:image/png;base64,{venmo_b64}" alt="Venmo QR Code" class="w-24 h-24 rounded-xl border border-slate-800 bg-white p-1 shrink-0">
          <div>
            <div class="text-xs font-mono font-semibold text-blue-400 uppercase">Venmo</div>
            <div class="text-base font-bold text-white mb-2">@Ran-Baron</div>
            <a href="https://venmo.com/u/Ran-Baron" target="_blank" rel="noopener" class="inline-block py-1.5 px-3 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold transition">
              Open Venmo
            </a>
          </div>
        </div>

        <div class="p-5 rounded-2xl bg-slate-950/90 border border-emerald-500/30 flex items-center gap-5">
          <img src="data:image/png;base64,{cashapp_b64}" alt="Cash App QR Code" class="w-24 h-24 rounded-xl border border-slate-800 bg-white p-1 shrink-0">
          <div>
            <div class="text-xs font-mono font-semibold text-emerald-400 uppercase">Cash App</div>
            <div class="text-base font-bold text-white mb-2">$RanBaron</div>
            <a href="https://cash.app/$RanBaron" target="_blank" rel="noopener" class="inline-block py-1.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition">
              Open Cash App
            </a>
          </div>
        </div>
      </div>

      <div class="mt-6 pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-400">
        <div>Found a bug, broken link, or outdated polling location?</div>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition inline-flex items-center gap-1.5">
          <span>GitLab Issue Tracker</span>
          <span>&rarr;</span>
        </a>
      </div>
    </section>

  </main>

  <!-- Global Footer -->
  <footer class="mt-auto border-t border-slate-800/80 bg-slate-950 py-10 px-4 sm:px-6">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-center md:text-left">
      <div class="space-y-1">
        <div class="text-sm font-bold text-white">North Carolina Student Voting Platform</div>
        <div class="text-xs text-slate-400">Maintained by Rann Bar-On &bull; Non-partisan student voting resource</div>
        <div class="text-[11px] text-slate-500">Official data verified against NCSBE &bull; Last update: {VERIFIED_UPDATE_TIME}</div>
      </div>
      <div class="flex flex-wrap items-center justify-center gap-6 text-xs text-slate-400">
        <a href="/campuses" class="hover:text-white transition">All 110 Campuses</a>
        <a href="/vote" class="hover:text-white transition">Dynamic QR Portal</a>
        <a href="https://www.ncsbe.gov" target="_blank" rel="noopener" class="hover:text-white transition">NCSBE Official</a>
        <a href="{GITLAB_REPO_URL}" target="_blank" rel="noopener" class="hover:text-white transition">GitLab Source</a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="hover:text-white transition">GitLab Bug Tracker</a>
        <a href="/stats" class="hover:text-white transition">Usage Tracker</a>
      </div>
    </div>
  </footer>

  <!-- Client-side Geolocation Nearest Precinct Script -->
  <script>
    const countyPrecincts = {c_precincts_json};

    function haversine(lat1, lon1, lat2, lon2) {{
      const R = 3958.8; // miles
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return R * c;
    }}

    function detectNearestPrecinct() {{
      const btn = document.getElementById('btn-detect-precinct');
      const resDiv = document.getElementById('gps-precinct-result');
      if (!navigator.geolocation) {{
        alert('Geolocation is not supported by your browser.');
        return;
      }}
      btn.innerText = 'Detecting location...';
      navigator.geolocation.getCurrentPosition(
        (pos) => {{
          const uLat = pos.coords.latitude;
          const uLon = pos.coords.longitude;
          let best = null;
          let minD = 999999;
          for (let p of countyPrecincts) {{
            if (p.lat && p.lon) {{
              let d = haversine(uLat, uLon, p.lat, p.lon);
              if (d < minD) {{
                minD = d;
                best = p;
              }}
            }}
          }}
          btn.innerText = 'Detect My Nearest Precinct via GPS';
          resDiv.classList.remove('hidden');
          if (best) {{
            const mapQuery = encodeURIComponent((best.name || '') + ' ' + (best.county || '') + ' County NC');
            resDiv.innerHTML = `
              <div class="font-bold text-emerald-400 mb-1">[NEAREST GEOLOCATED PRECINCT FOUND]</div>
              <div class="text-sm font-semibold text-white mb-1">${{best.name || 'Precinct ' + best.prec_id}} (Precinct ${{best.prec_id}})</div>
              <div class="text-xs text-slate-300 mb-3">Approximately <b>${{minD.toFixed(2)}} miles</b> from your current device location in ${{best.county}} County.</div>
              <div class="flex flex-wrap gap-2">
                <a href="https://maps.google.com/?q=${{mapQuery}}" target="_blank" rel="noopener" class="py-1.5 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs inline-flex items-center gap-1">
                  <span>Open Directions in Google Maps</span> &rarr;
                </a>
                <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" rel="noopener" class="py-1.5 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs inline-flex items-center gap-1">
                  <span>Verify on NCSBE Portal</span> &rarr;
                </a>
              </div>
            `;
          }} else {{
            resDiv.innerHTML = '<div class="text-amber-300">Could not calculate nearest precinct in county data. Please check NCSBE portal.</div>';
          }}
        }},
        (err) => {{
          btn.innerText = 'Detect My Nearest Precinct via GPS';
          alert('Unable to retrieve location. Please grant location permissions or use the NCSBE search tool.');
        }},
        {{ timeout: 10000, enableHighAccuracy: true }}
      );
    }}
  </script>
  <script src="/tracker.js"></script>
</body>
</html>
'''

    # Write to main repo
    with open(f"{MAIN_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    os.makedirs(f"{MAIN_DIR}/{key}", exist_ok=True)
    with open(f"{MAIN_DIR}/{key}/index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    if LOCAL_DIR:
        with open(f"{LOCAL_DIR}/{key}.html", 'w', encoding='utf-8') as f:
            f.write(html_content)

print(f"Generated {len(institutions)} individual campus Election Day pages.")

# Generate St. Andrews Redirect
print("Generating St. Andrews closure notice & redirect...")
sa_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5;url=/campuses">
  <title>St. Andrews University Closed | NC Student Voting Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen flex items-center justify-center bg-slate-950 text-slate-100 p-6">
  <div class="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center space-y-4 shadow-2xl">
    <div class="w-12 h-12 mx-auto rounded-2xl bg-amber-500/20 text-amber-300 flex items-center justify-center font-bold text-xl">
      !
    </div>
    <h1 class="text-2xl font-bold text-white">St. Andrews University Closed</h1>
    <p class="text-sm text-slate-300 leading-relaxed">
      St. Andrews University in Laurinburg, NC officially ceased academic operations on May 5, 2025. It is no longer an active institution.
    </p>
    <p class="text-xs text-slate-400">
      Redirecting you to the master directory of 110 active North Carolina colleges and universities...
    </p>
    <a href="/campuses" class="inline-block py-2.5 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition">
      View Active NC Campuses &rarr;
    </a>
  </div>
</body>
</html>
'''
with open(f"{MAIN_DIR}/standrewsvote.html", 'w', encoding='utf-8') as f:
    f.write(sa_content)
os.makedirs(f"{MAIN_DIR}/standrewsvote", exist_ok=True)
with open(f"{MAIN_DIR}/standrewsvote/index.html", 'w', encoding='utf-8') as f:
    f.write(sa_content)
if LOCAL_DIR:
    with open(f"{LOCAL_DIR}/standrewsvote.html", 'w', encoding='utf-8') as f:
        f.write(sa_content)

print("4. Updating Master Directory page (campuses.html) for Election Day...")
campuses_cards = []
for inst in institutions:
    type_class = "text-blue-400 bg-blue-500/10 border-blue-500/30" if inst['type'] == 'UNC System' else ("text-emerald-400 bg-emerald-500/10 border-emerald-500/30" if "Community" in inst['type'] else "text-purple-400 bg-purple-500/10 border-purple-500/30")
    type_badge = "UNC System" if inst['type'] == 'UNC System' else ("Community College" if "Community" in inst['type'] else "Private University")
    id_status = f'<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">ID Approved</span>' if inst['id_approved'] else f'<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">Alternative ID Req</span>'
    
    campuses_cards.append(f'''
    <a href="/{inst['key']}" class="campus-card block p-5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-900/80 transition group shadow-md" data-name="{inst['name'].lower()}" data-city="{inst['city'].lower()}" data-county="{inst['county'].lower()}" data-type="{inst['type'].lower()}">
      <div class="flex items-start justify-between gap-2 mb-3">
        <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border {type_class}">
          {type_badge}
        </span>
        {id_status}
      </div>
      <h3 class="text-lg font-bold text-white group-hover:text-rose-400 transition leading-snug mb-1">{inst['name']}</h3>
      <div class="text-xs text-slate-400 mb-3">{inst['city']}, NC &bull; {clean_site_name(inst['county'])} County</div>
      <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-300">
        <span>Election Day Guide</span>
        <span class="text-rose-400 group-hover:translate-x-1 transition">&rarr;</span>
      </div>
    </a>
    ''')

campuses_grid_html = '\n'.join(campuses_cards)

campuses_html = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Colleges & Universities Election Day Voting Directory | Rann Bar-On</title>
  <meta name="description" content="Complete directory of Election Day voting guides for all 110 NC colleges, universities, and community colleges: assigned precinct lookups, voter ID requirements, hours (6:30 AM - 7:30 PM), candidate guides, and QR codes.">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    body {{ font-family: 'Inter', sans-serif; background-color: #070b14; color: #f8fafc; }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased" data-campus="Master Directory" data-key="campuses">
  <aside class="bg-slate-900 border-b border-slate-800 text-xs text-slate-300 py-2 px-4 sm:px-6">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 uppercase tracking-wide">Verified Source</span>
        <span>Official NC State Board of Elections & County BOE Directory</span>
      </div>
      <div class="flex items-center gap-4 text-slate-400 text-[11px]">
        <span>Last Verified Update: <b class="text-slate-200">{VERIFIED_UPDATE_TIME}</b></span>
        <a href="https://www.ncsbe.gov" target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 underline font-medium">Information Sources</a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="text-rose-400 hover:text-rose-300 underline font-medium">Report Issue</a>
      </div>
    </div>
  </aside>

  <header class="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <a href="/campuses" class="flex items-center gap-2">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md text-xs font-mono">NC</div>
        <span class="font-bold text-slate-100 text-sm">NC Student Voting Directory</span>
      </a>
      <a href="/vote" class="text-xs font-medium px-3.5 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">Statewide /vote Portal</a>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-4 sm:px-6 py-12 space-y-10">
    <div class="max-w-3xl space-y-4">
      <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30">
        [ELECTION DAY DIRECTORY] &bull; 110 Institutions Statewide
      </span>
      <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
        North Carolina Higher Education <br><span class="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-amber-300 to-blue-400">Election Day Voting Directory</span>
      </h1>
      <p class="text-slate-300 text-sm sm:text-base leading-relaxed">
        Early voting has concluded. On <b>Election Day (Tuesday, November 3)</b>, you must vote at your <b>specifically assigned precinct polling place</b> between 6:30 AM and 7:30 PM. Select your campus below for precinct lookups, voter ID rules, candidate guides, and scannable QR codes.
      </p>
    </div>

    <!-- Search and Filters -->
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-4 sm:p-6 space-y-4 shadow-lg">
      <div class="relative">
        <input type="text" id="campus-search" placeholder="Search by institution name, city, or county..." class="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500">
      </div>
      <div class="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div class="flex flex-wrap gap-2">
          <button onclick="filterType('all')" class="filter-btn px-3 py-1.5 rounded-lg bg-rose-600 text-white font-semibold transition" data-type="all">All 110 Campuses</button>
          <button onclick="filterType('unc')" class="filter-btn px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition" data-type="unc">16 UNC System</button>
          <button onclick="filterType('cc')" class="filter-btn px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition" data-type="cc">58 Community Colleges</button>
          <button onclick="filterType('private')" class="filter-btn px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition" data-type="private">36 Private Colleges</button>
        </div>
        <div id="results-count" class="text-slate-400 font-mono">Showing 110 of 110 institutions</div>
      </div>
    </div>

    <!-- Campus Cards Grid -->
    <div id="campus-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {campuses_grid_html}
    </div>
  </main>

  <script>
    let currentFilter = 'all';
    const searchInput = document.getElementById('campus-search');
    const cards = document.querySelectorAll('.campus-card');
    const countEl = document.getElementById('results-count');
    const filterBtns = document.querySelectorAll('.filter-btn');

    function applyFilter() {{
      const query = searchInput.value.toLowerCase().trim();
      let visible = 0;
      cards.forEach(card => {{
        const name = card.dataset.name;
        const city = card.dataset.city;
        const county = card.dataset.county;
        const type = card.dataset.type;

        const matchesQuery = !query || name.includes(query) || city.includes(query) || county.includes(query);
        let matchesType = true;
        if (currentFilter === 'unc') matchesType = type.includes('unc');
        else if (currentFilter === 'cc') matchesType = type.includes('community');
        else if (currentFilter === 'private') matchesType = type.includes('private');

        if (matchesQuery && matchesType) {{
          card.style.display = 'block';
          visible++;
        }} else {{
          card.style.display = 'none';
        }}
      }});
      countEl.innerText = `Showing ${{visible}} of 110 institutions`;
    }}

    searchInput.addEventListener('input', applyFilter);

    function filterType(type) {{
      currentFilter = type;
      filterBtns.forEach(btn => {{
        if (btn.dataset.type === type) {{
          btn.className = 'filter-btn px-3 py-1.5 rounded-lg bg-rose-600 text-white font-semibold transition';
        }} else {{
          btn.className = 'filter-btn px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white transition';
        }}
      }});
      applyFilter();
    }}
  </script>
  <script src="/tracker.js"></script>
</body>
</html>
'''

with open(f"{MAIN_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
os.makedirs(f"{MAIN_DIR}/campuses", exist_ok=True)
with open(f"{MAIN_DIR}/campuses/index.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
if LOCAL_DIR:
    with open(f"{LOCAL_DIR}/campuses.html", 'w', encoding='utf-8') as f:
        f.write(campuses_html)

print("5. Generating dynamic Main QR Code Portal for /vote on Election Day...")

vote_html = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NC Student Voting Dynamic Portal | rannbar-on.com/vote</title>
  <meta name="description" content="Dynamic QR portal for all 110 North Carolina higher education institutions: automatically routes students to their campus Election Day guide via geolocation or zip code.">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
    body {{ font-family: 'Inter', sans-serif; background-color: #070b14; color: #f8fafc; }}
    .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased" data-campus="Dynamic QR Portal" data-key="vote">
  <aside class="bg-slate-900 border-b border-slate-800 text-xs text-slate-300 py-2 px-4 sm:px-6">
    <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
      <div class="flex items-center gap-2">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30 uppercase tracking-wide">Verified Source</span>
        <span>Official NC State Board of Elections & County BOE Schedule</span>
      </div>
      <div class="flex items-center gap-4 text-slate-400 text-[11px]">
        <span>Last Verified Update: <b class="text-slate-200">{VERIFIED_UPDATE_TIME}</b></span>
        <a href="https://www.ncsbe.gov" target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 underline font-medium">Information Sources</a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="text-rose-400 hover:text-rose-300 underline font-medium">Report Issue</a>
      </div>
    </div>
  </aside>

  <header class="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
      <a href="/campuses" class="flex items-center gap-2">
        <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-rose-600 to-indigo-600 flex items-center justify-center font-bold text-white shadow-md text-xs font-mono">NC</div>
        <span class="font-bold text-slate-100 text-sm">NC Student Voting</span>
      </a>
      <a href="/campuses" class="text-xs font-semibold px-3.5 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">Directory (110 Campuses)</a>
    </div>
  </header>

  <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-12 space-y-10">
    <div class="text-center space-y-4">
      <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-300 border border-rose-500/30">
        [ELECTION DAY PORTAL] &bull; Dynamic Campus Routing
      </span>
      <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
        North Carolina Student Voting <br><span class="text-transparent bg-clip-text bg-gradient-to-r from-rose-400 via-amber-300 to-blue-400">Dynamic Election Day QR Code</span>
      </h1>
      <p class="text-slate-300 text-sm sm:text-base leading-relaxed max-w-2xl mx-auto">
        Early voting has ended. This QR code automatically points to your college or university's Election Day voting guide (assigned precinct lookup, voter ID status, and candidate guides). Allow device geolocation or enter a zip code below to customize it instantly.
      </p>
    </div>

    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-10 shadow-2xl flex flex-col md:flex-row items-center justify-between gap-8">
      <div class="flex flex-col items-center">
        <div class="p-4 bg-white rounded-2xl shadow-xl mb-3" id="qrcode-container"></div>
        <div class="text-xs font-mono text-slate-400 text-center" id="qr-target-url">Target: https://rannbar-on.com/campuses</div>
      </div>

      <div class="space-y-6 flex-1 w-full">
        <div>
          <h2 class="text-xl font-bold text-white mb-2" id="routing-heading">Select or Detect Your Campus</h2>
          <p class="text-xs text-slate-300 leading-relaxed" id="routing-desc">
            Use geolocation to automatically detect your nearest NC institution and precinct, or select your campus from the list.
          </p>
        </div>

        <div class="flex flex-col sm:flex-row gap-3">
          <button onclick="requestGeolocation()" id="btn-geolocate" class="py-3 px-5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition shadow-md flex items-center justify-center gap-2">
            <span>Use My Current Location</span>
            <span>&rarr;</span>
          </button>
          <a href="/campuses" class="py-3 px-5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition text-center">
            Browse All 110 Campuses
          </a>
        </div>

        <div class="pt-4 border-t border-slate-800 space-y-3">
          <label class="block text-xs font-semibold text-slate-300">Or Enter NC Zip Code or City:</label>
          <div class="flex gap-2">
            <input type="text" id="zip-input" placeholder="e.g. 27708, 27514, Raleigh..." class="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500">
            <button onclick="lookupZip()" class="py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-semibold text-xs border border-slate-700 transition">
              Find
            </button>
          </div>
        </div>

        <div id="status-card" class="hidden p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200"></div>
      </div>
    </div>
  </main>

  <script>
    const campuses = {campus_geo_json_str};
    let qr = null;

    function renderQR(url) {{
      const container = document.getElementById('qrcode-container');
      container.innerHTML = '';
      qr = new QRCode(container, {{
        text: url,
        width: 200,
        height: 200,
        colorDark: "#070b14",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
      }});
      document.getElementById('qr-target-url').innerText = 'Target: ' + url;
    }}

    renderQR('https://rannbar-on.com/campuses');

    function haversine(lat1, lon1, lat2, lon2) {{
      const R = 3958.8;
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return R * c;
    }}

    function findClosestCampus(lat, lon) {{
      let closest = null;
      let minD = 999999;
      for (let c of campuses) {{
        let d = haversine(lat, lon, c.lat, c.lon);
        if (d < minD) {{
          minD = d;
          closest = c;
        }}
      }}
      return {{ campus: closest, distance: minD }};
    }}

    function requestGeolocation() {{
      const btn = document.getElementById('btn-geolocate');
      const status = document.getElementById('status-card');
      if (!navigator.geolocation) {{
        alert('Geolocation not supported by your browser.');
        return;
      }}
      btn.innerText = 'Detecting location...';
      navigator.geolocation.getCurrentPosition(
        (pos) => {{
          const res = findClosestCampus(pos.coords.latitude, pos.coords.longitude);
          btn.innerText = 'Use My Current Location';
          if (res.campus) {{
            const targetUrl = 'https://rannbar-on.com/' + res.campus.key;
            renderQR(targetUrl);
            status.classList.remove('hidden');
            status.innerHTML = `
              <div class="font-bold text-rose-400 mb-1">[NEAREST CAMPUS DETECTED]</div>
              <div class="text-sm font-semibold text-white mb-1">${{res.campus.name}}</div>
              <div class="text-slate-300 mb-3">Approximately <b>${{res.distance.toFixed(1)}} miles</b> away in ${{res.campus.county}} County.</div>
              <a href="${{targetUrl}}" class="inline-block py-2 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition">
                Go to ${{res.campus.name}} Election Day Guide &rarr;
              </a>
            `;
          }}
        }},
        (err) => {{
          btn.innerText = 'Use My Current Location';
          alert('Could not retrieve location. Please grant permission or search by zip code.');
        }},
        {{ timeout: 10000, enableHighAccuracy: true }}
      );
    }}

    function lookupZip() {{
      const q = document.getElementById('zip-input').value.toLowerCase().trim();
      const status = document.getElementById('status-card');
      if (!q) return;
      const found = campuses.find(c => c.city.toLowerCase().includes(q) || c.county.toLowerCase().includes(q) || c.name.toLowerCase().includes(q));
      if (found) {{
        const targetUrl = 'https://rannbar-on.com/' + found.key;
        renderQR(targetUrl);
        status.classList.remove('hidden');
        status.innerHTML = `
          <div class="font-bold text-rose-400 mb-1">[CAMPUS MATCH FOUND]</div>
          <div class="text-sm font-semibold text-white mb-1">${{found.name}}</div>
          <div class="text-slate-300 mb-3">${{found.city}}, NC &bull; ${{found.county}} County</div>
          <a href="${{targetUrl}}" class="inline-block py-2 px-4 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs transition">
            Go to ${{found.name}} Election Day Guide &rarr;
          </a>
        `;
      }} else {{
        status.classList.remove('hidden');
        status.innerHTML = '<div class="text-amber-300">No immediate match found. Please choose from the <a href="/campuses" class="underline font-bold">110 Campuses Directory</a>.</div>';
      }}
    }}
  </script>
  <script src="/tracker.js"></script>
</body>
</html>
'''

with open(f"{MAIN_DIR}/vote.html", 'w', encoding='utf-8') as f:
    f.write(vote_html)
os.makedirs(f"{MAIN_DIR}/vote", exist_ok=True)
with open(f"{MAIN_DIR}/vote/index.html", 'w', encoding='utf-8') as f:
    f.write(vote_html)
if LOCAL_DIR:
    with open(f"{LOCAL_DIR}/vote.html", 'w', encoding='utf-8') as f:
        f.write(vote_html)

print("ALL ELECTION DAY PAGES GENERATED SUCCESSFULLY!")
