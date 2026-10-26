#!/usr/bin/env python3
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

with open(f'{CACHE_DIR}/county_early_voting_sites.json', 'r', encoding='utf-8') as f:
    sites_by_county = json.load(f)

print(f"Loaded {len(institutions)} institutions, {len(boe_by_county)} counties.")

# 2. Local County Party URL Mappings
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
    'CATAWBA': 'https://www.catawbagop.com/',
    'ROWAN': 'https://www.rowangop.org/',
    'UNION': 'https://www.unioncountyncgop.com/',
    'GASTON': 'https://www.gastongop.org/',
    'HENDERSON': 'https://www.hendersongop.com/',
    'HARNETT': 'https://www.harnettcountygop.com/',
    'JOHNSTON': 'https://www.johnstoncountygop.org/'
}

# 3. Cache QR codes in Base64
print("2. Reading QR codes...")
qr_b64_map = {}
for inst in institutions:
    key = inst['key']
    png_path = f"{MAIN_DIR}/{key}_qr.png"
    if not os.path.exists(png_path):
        url = f"https://rannbar-on.com/{key}"
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(png_path)
        img.save(f"{LOCAL_DIR}/{key}_qr.png")
    with open(png_path, 'rb') as f:
        qr_b64_map[key] = base64.b64encode(f.read()).decode('utf-8')

# 4. Build Select Dropdown HTML for campus switching
sorted_institutions = sorted(institutions, key=lambda x: x['name'])
campus_options = []
for inst in sorted_institutions:
    type_badge = "UNC" if inst['type'] == 'UNC System' else ("CC" if "Community" in inst['type'] else "Private")
    campus_options.append(f'<option value="/{inst["key"]}">{inst["name"]} ({inst["city"]}) - {type_badge}</option>')
campus_options_html = '\n'.join(campus_options)

def get_best_site(inst, county_sites):
    if not county_sites:
        return None
    keyword = inst.get('site_keyword', '').upper()
    name_words = [w for w in re.split(r'[\s\-]+', inst['name'].upper()) if len(w) > 3 and w not in ['UNIVERSITY', 'COLLEGE', 'COMMUNITY', 'NORTH', 'CAROLINA', 'TECHNICAL', 'SYSTEM']]
    
    if keyword:
        for s in county_sites:
            s_name = s['Name'].upper()
            s_addr = s['SiteAddressStreet'].upper()
            if keyword in s_name or keyword in s_addr:
                return s
    
    for w in name_words:
        for s in county_sites:
            if w in s['Name'].upper() or w in s['SiteAddressStreet'].upper():
                return s
    
    return county_sites[0]

# 5. Generate individual voting guide pages
print("3. Generating individual campus voting guide pages with 3 balanced voter guides...")

for inst in institutions:
    key = inst['key']
    cname = inst['county'].upper()
    boe = boe_by_county.get(cname, {})
    county_sites = sites_by_county.get(cname, [])
    primary_site = get_best_site(inst, county_sites)

    c_display = cname.title() + " County"
    boe_phone = boe.get('OfficePhoneNum', '(919) 814-0700')
    boe_addr = boe.get('FullAddress', f'{c_display} Board of Elections, NC')
    boe_web = boe.get('WebsiteAddr', f'https://vt.ncsbe.gov/BOEInfo/?county={cname}')
    boe_name = boe.get('OfficeName', f'{c_display} Board of Elections').title()

    dem_county_url = county_dem_urls.get(cname, 'https://www.ncdp.org/county-parties/')
    rep_county_url = county_rep_urls.get(cname, 'https://www.ncgop.org/county_parties')

    if primary_site:
        p_name = primary_site['Name'].title()
        p_addr = primary_site['SiteAddressComplete'].title()
        p_maps = primary_site.get('DirectionURL', f"https://maps.google.com/?q={p_addr.replace(' ', '+')}")
    else:
        p_name = f"{c_display} Early Voting Center"
        p_addr = boe_addr
        p_maps = f"https://maps.google.com/?q={boe_addr.replace(' ', '+')}"

    # Student ID section
    if inst['id_approved']:
        id_badge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ NCSBE Approved Student ID</span>'
        id_alert_border = "border-emerald-500/40 bg-emerald-950/20"
        id_alert_box = f'''
        <div class="bg-emerald-950/40 border-2 border-emerald-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-emerald-500/20 text-emerald-300 text-2xl shrink-0">
            ✓
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 mb-2">Approved by NC State Board of Elections</span>
            <h2 class="text-xl font-bold text-white mb-2">{inst['name']} Student ID is Valid for Voting!</h2>
            <p class="text-sm text-emerald-100/90 leading-relaxed mb-3">
              The North Carolina State Board of Elections officially approved the <b>{inst['id_card_name']}</b> for voter photo identification. You can use your physical student ID to cast your ballot.
            </p>
            <div class="p-3.5 rounded-xl bg-emerald-900/30 border border-emerald-700/50 text-xs text-emerald-200/90 space-y-1.5 font-medium">
              <p>⚠️ <b>CRITICAL: PHYSICAL CARD REQUIRED.</b> Digital IDs stored on mobile phones (Apple Wallet, Google Wallet, photos) are <b>NOT ACCEPTED</b> at polling sites under NC law.</p>
              <p>✅ <b>Other Accepted Photo IDs:</b> NC Driver’s License, US Passport, Military/Veteran ID, or free county BOE ID card.</p>
              <p>💡 <b>Need an ID on voting day?</b> You can still vote! Fill out a Photo ID Exception Form at the polling place or get a free voter photo ID at the {c_display} Board of Elections office.</p>
            </div>
          </div>
        </div>
        '''
    else:
        id_badge = '<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">⚠️ Alternative Photo ID Required</span>'
        id_alert_border = "border-amber-500/40 bg-amber-950/20"
        id_alert_box = f'''
        <div class="bg-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-amber-500/20 text-amber-300 text-2xl shrink-0">
            ⚠️
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">Student Photo ID Not On State Approved List</span>
            <h2 class="text-xl font-bold text-white mb-2">Student ID Card is NOT Accepted for Voting</h2>
            <p class="text-sm text-amber-100/90 leading-relaxed mb-3">
              Under North Carolina law, student IDs cannot be used for voting unless the institution applied for and received approval from the State Board of Elections. {inst['name']} student IDs are <b>not approved</b> for voting purposes.
            </p>
            <div class="p-3.5 rounded-xl bg-amber-900/30 border border-amber-700/50 text-xs text-amber-200/90 space-y-1.5 font-medium">
              <p>✅ <b>WHAT YOU CAN USE INSTEAD:</b></p>
              <ul class="list-disc pl-5 space-y-1 text-slate-200">
                <li><b>North Carolina Driver’s License</b> or NC DMV State ID (can be expired up to 1 year, or unexpired).</li>
                <li><b>U.S. Passport</b> or U.S. Passport Card (must be unexpired).</li>
                <li><b>Out-of-State Driver’s License</b> (accepted only if you registered to vote in NC within 90 days of the election).</li>
                <li><b>Free Voter Photo ID Card:</b> Issued on the spot for free at the {c_display} Board of Elections office!</li>
                <li><b>Photo ID Exception Form:</b> If you lack an approved ID due to a reasonable impediment, you can complete an Exception Form at the polling site and cast a ballot that counts.</li>
              </ul>
            </div>
          </div>
        </div>
        '''

    # Build All Sites Cards for this county
    site_cards = []
    for s in county_sites:
        s_title = s['Name'].title()
        s_address = s['SiteAddressComplete'].title()
        is_highlight = (primary_site and s['Name'] == primary_site['Name'])
        border_cls = 'border-2 border-blue-500/70 bg-slate-900 shadow-md' if is_highlight else 'border border-slate-800 bg-slate-900/70'
        badge_html = '<span class="absolute top-2 right-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-600 text-white">Campus / Nearest Site</span>' if is_highlight else ''
        dir_url = s.get('DirectionURL', f"https://maps.google.com/?q={s_address.replace(' ', '+')}")
        site_cards.append(f'''
        <div class="rounded-xl p-4 {border_cls} relative overflow-hidden flex flex-col justify-between">
          <div>
            {badge_html}
            <h4 class="font-bold text-white text-sm pr-16">{s_title}</h4>
            <p class="text-xs text-slate-300 mt-1">{s_address}</p>
          </div>
          <div class="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
            <span class="text-[11px] text-emerald-400 font-mono">Open Early Voting</span>
            <a href="{dir_url}" target="_blank" rel="noopener" class="text-xs text-blue-400 hover:underline font-semibold flex items-center gap-1">Map ↗</a>
          </div>
        </div>
        ''')
    sites_grid_html = '\n'.join(site_cards) if site_cards else f'<div class="p-4 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 text-sm">See {c_display} Board of Elections for full list.</div>'

    qr_b64 = qr_b64_map[key]

    html_content = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst['short_name']} Student Guide to Early Voting in {c_display} | Rann Bar-On</title>
  <meta name="description" content="Complete early voting guide for {inst['name']} students in {c_display}, NC: voting sites, voter ID rules, local voter guides (Democratic, Republican, Independent), same-day registration, and hours.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/{key}">
  <meta property="og:title" content="{inst['short_name']} Student Guide to Early Voting in {c_display}">
  <meta property="og:description" content="Everything {inst['name']} students need to cast their ballot early in {c_display}: polling locations, voter ID rules, candidate guides, and same-day registration.">
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

    .font-mono {{
      font-family: 'JetBrains Mono', monospace;
    }}

    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-track {{
      background: #0b1120;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #334155;
      border-radius: 3px;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased">

  <!-- Top Announcement Bar -->
  <div class="bg-gradient-to-r from-blue-950 via-indigo-950 to-slate-950 px-4 py-2.5 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-1.5">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span>Early Voting in {c_display} is <b>OPEN NOW</b> through <b>Saturday, October 31, 2026</b></span>
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
        <a href="#voter-guides" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
          🗳️ Voter Guides
        </a>
        <a href="#voter-id" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 transition">
          ⚠️ Voter ID
        </a>
        <a href="#qr-code" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm">
          📱 QR Code
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
      
      <!-- Quick Jump Campus Selector -->
      <div class="flex items-center gap-2">
        <label for="campus-quick-jump" class="text-xs text-slate-400 font-medium hidden sm:inline">Switch Campus:</label>
        <select id="campus-quick-jump" onchange="if(this.value) window.location.href=this.value;" class="bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-blue-500 font-medium">
          <option value="">Jump to another NC College/University...</option>
          {campus_options_html}
        </select>
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="relative py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 overflow-hidden">
    <div class="max-w-4xl mx-auto text-center relative z-10">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-4">
        <span>{inst['badge_icon']} {inst['name']}</span>
        <span class="text-slate-600">•</span>
        <span>{c_display}, NC</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        {inst['short_name']} Student Guide <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-300">to Early Voting in {c_display}</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Everything {inst['name']} undergraduate and graduate students need to cast their ballot early. Vote on campus or nearby, compare candidate guides from all perspectives, and make sure your voice is heard!
      </p>

      <!-- Key Stat Pills -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto text-left">
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Early Voting Window</div>
          <div class="text-base font-bold text-white mt-0.5">Oct 15 – Oct 31</div>
          <div class="text-[11px] text-emerald-400 mt-1 font-mono">Open 7 days/wk</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Primary Voting Site</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{p_name}</div>
          <div class="text-[11px] text-blue-400 mt-1 font-mono">{inst['city']}, NC</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Missed Registration?</div>
          <div class="text-base font-bold text-white mt-0.5">Same-Day Reg</div>
          <div class="text-[11px] text-purple-400 mt-1 font-mono">Register & vote at once</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Voter ID Rule</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{'Approved' if inst['id_approved'] else 'Alt ID Required'}</div>
          <div class="text-[11px] {'text-emerald-400' if inst['id_approved'] else 'text-amber-400'} mt-1 font-mono">{'Physical Student Card' if inst['id_approved'] else 'NC License / Passport'}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- CRITICAL VOTER ID RULE SECTION -->
  <section id="voter-id" class="py-8 px-4 sm:px-6 {id_alert_border} border-b">
    <div class="max-w-4xl mx-auto">
      {id_alert_box}
    </div>
  </section>

  <!-- Main Content Container -->
  <main class="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-12">

    <!-- Section 1: Campus Polling Site -->
    <section id="polling-site" class="scroll-mt-20">
      <div class="flex items-center justify-between mb-4">
        <div>
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Campus / Nearest Early Voting Site</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1">{p_name}</h2>
        </div>
        <span class="hidden sm:inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Open to all {c_display} Voters
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Left: Address & Directions -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:col-span-1 flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2 text-sm font-semibold text-slate-300 mb-2">
              <span>📍 Address & Getting There</span>
            </div>
            <p class="text-base font-bold text-white leading-snug">
              {p_addr}
            </p>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              Official Early Voting location serving {inst['name']} students, faculty, staff, and all residents of {c_display}.
            </p>

            <div class="mt-4 pt-4 border-t border-slate-800/80 space-y-2 text-xs text-slate-300 leading-relaxed">
              <p><b>Free Voter Parking:</b> Available at or near the facility during voting hours.</p>
              <p><b>Flexibility:</b> You can cast your early ballot at <b>any</b> early voting site in {c_display}.</p>
            </div>
          </div>

          <div class="mt-6 pt-4">
            <a href="{p_maps}" target="_blank" rel="noopener" class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-sm">
              <span>Open in Google Maps</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <!-- Right: Early Voting Hours Schedule -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:col-span-2">
          <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">{c_display} Early Voting Hours Schedule</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead>
                <tr class="border-b border-slate-800 text-xs text-slate-400 font-mono">
                  <th class="py-2.5 font-semibold">Days</th>
                  <th class="py-2.5 font-semibold">Dates</th>
                  <th class="py-2.5 font-semibold">Hours</th>
                  <th class="py-2.5 font-semibold text-right">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-800/60">
                <tr>
                  <td class="py-3 font-medium text-white">Mondays – Fridays</td>
                  <td class="py-3 text-slate-400 text-xs">Oct 15 – Oct 30</td>
                  <td class="py-3 font-mono text-emerald-400 font-semibold">8:00 AM – 7:30 PM</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Extended</span></td>
                </tr>
                <tr>
                  <td class="py-3 font-medium text-white">Saturdays</td>
                  <td class="py-3 text-slate-400 text-xs">Oct 17 & Oct 24</td>
                  <td class="py-3 font-mono text-blue-300 font-semibold">8:00 AM – 3:00 PM</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Weekend</span></td>
                </tr>
                <tr>
                  <td class="py-3 font-medium text-white">Sundays</td>
                  <td class="py-3 text-slate-400 text-xs">Oct 18 & Oct 25</td>
                  <td class="py-3 font-mono text-blue-300 font-semibold">1:00 PM – 5:00 PM</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Afternoon</span></td>
                </tr>
                <tr class="bg-amber-500/5 font-semibold">
                  <td class="py-3 text-amber-300">Final Saturday (Last Day!)</td>
                  <td class="py-3 text-amber-200 text-xs">Saturday, Oct 31</td>
                  <td class="py-3 font-mono text-amber-300 font-bold">8:00 AM – 3:00 PM</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Closes 3 PM</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="text-xs text-slate-400 mt-4 leading-relaxed">
            💡 <i>During early voting, you can vote at <b>any</b> early voting location in {c_display}, regardless of your precinct!</i>
          </p>
        </div>
      </div>
    </section>

    <!-- Section 2: Local Candidate Voter Guides (Democratic, Republican & Independent) -->
    <section id="voter-guides" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-8">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Candidate Research & Endorsements</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-2">Local Candidate Guides for {inst['short_name']} Students</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Before casting your ballot in {c_display}, review candidate questionnaires, voting records, and endorsements from multiple political perspectives. Compare trusted Democratic, Republican, and non-partisan sources below:
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
              Enter your local {c_display} address to see customized candidate recommendations and slates endorsed by Democratic, labor, reproductive rights, and environmental organizations across North Carolina.
            </p>
            <ul class="text-xs text-slate-400 space-y-1.5 mb-4">
              <li class="flex items-center gap-2">
                <span class="text-blue-400 font-bold">✓</span>
                <span>Endorsements from 40+ progressive orgs</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-blue-400 font-bold">✓</span>
                <span>Local legislative, judicial & county races</span>
              </li>
            </ul>
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
            <ul class="text-xs text-slate-400 space-y-1.5 mb-4">
              <li class="flex items-center gap-2">
                <span class="text-red-400 font-bold">✓</span>
                <span>Detailed candidate ratings & questionnaires</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-red-400 font-bold">✓</span>
                <span>Covers statewide, judicial & local offices</span>
              </li>
            </ul>
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
            <ul class="text-xs text-slate-400 space-y-1.5 mb-4">
              <li class="flex items-center gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span>Side-by-side unedited candidate responses</span>
              </li>
              <li class="flex items-center gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span>Zero party bias or endorsements</span>
              </li>
            </ul>
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

    <!-- Section 3: Same-Day Registration -->
    <section id="registration" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 scroll-mt-20">
      <div class="max-w-3xl">
        <span class="text-xs font-mono font-semibold text-purple-400 uppercase tracking-wider">Missed the Voter Registration Deadline?</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-3">Same-Day Voter Registration is Available!</h2>
        <p class="text-sm text-slate-300 leading-relaxed mb-6">
          In North Carolina, if you are not yet registered to vote in {c_display}, or if you moved to a new address, you can <b>register and vote on the same visit</b> exclusively during Early Voting. (Same-day registration is <i>not</i> allowed on Election Day).
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- On Campus Students -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-500/10 text-blue-400 font-bold text-xs mb-3">
              <span>🏠 On-Campus Residents</span>
            </div>
            <h4 class="text-sm font-bold text-white mb-1.5">What to Bring:</h4>
            <ul class="text-xs text-slate-300 space-y-2">
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span><b>Photo ID:</b> An approved photo ID (or {inst['id_card_name']} if approved, NC Driver's License, or US Passport).</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span><b>Proof of Residence:</b> Campus housing verification (residential roster provided to election officials, or housing contract on student portal).</span>
              </li>
            </ul>
          </div>

          <!-- Off Campus Students -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
            <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-purple-500/10 text-purple-400 font-bold text-xs mb-3">
              <span>🏢 Off-Campus Residents</span>
            </div>
            <h4 class="text-sm font-bold text-white mb-1.5">What to Bring:</h4>
            <ul class="text-xs text-slate-300 space-y-2">
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span><b>Photo ID:</b> Approved photo identification.</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span><b>Proof of Residence:</b> Document showing your name and current local {c_display} address (utility bill, bank statement, paycheck, lease, or university official letter; can be digital on your phone).</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-400 leading-relaxed">
          ⚖️ <b>Student Voting Rights:</b> College students have the established legal right to choose whether to register and vote at their college address or their permanent home address. You must choose one and vote only once per election.
        </div>
      </div>
    </section>

    <!-- Section 4: All Early Voting Sites in County -->
    <section id="sites" class="scroll-mt-20">
      <div class="mb-6">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Countywide Flexibility</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1">All {len(county_sites)} {c_display} Early Voting Sites</h2>
        <p class="text-sm text-slate-400 mt-1">Any registered {c_display} voter can cast a ballot at any of these sites during early voting hours.</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {sites_grid_html}
      </div>
    </section>

    <!-- Section 5: Official Resources & County BOE -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span>📋</span>
          <span>Pre-Voting Checklist</span>
        </h3>
        <ul class="space-y-3 text-xs sm:text-sm text-slate-300">
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">1.</span>
            <span><b>Physical Photo ID:</b> Bring a physical acceptable photo ID. Remember: digital phone images are not permitted.</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">2.</span>
            <span><b>Proof of Residence (If Registering):</b> Proof of your current address in {c_display}.</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">3.</span>
            <span><b>Check Sample Ballot:</b> Look up your sample ballot on the <a href="{boe_web}" target="_blank" class="text-blue-400 underline">{boe_name}</a> portal.</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">4.</span>
            <span><b>Notes Allowed:</b> You can bring a printed voter guide or written notes into the voting booth.</span>
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
                <div class="text-xs text-slate-400 mt-0.5">Sample ballots, wait times & office info</div>
              </div>
              <span class="text-slate-400">↗</span>
            </a>
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span>Need help? Call Election Office:</span>
          <a href="tel:{boe_phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}" class="font-mono font-bold text-blue-400 hover:underline">{boe_phone}</a>
        </div>
      </div>
    </section>

    <!-- Section 6: QR Code Card -->
    <section id="qr-code" class="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="flex flex-col sm:flex-row items-center gap-6 sm:gap-8 justify-between">
        <div class="max-w-xl text-center sm:text-left">
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Share with Classmates & Dorms</span>
          <h2 class="text-2xl font-bold text-white mt-1 mb-2">Scan or Share this {inst['short_name']} Voting Guide</h2>
          <p class="text-sm text-slate-300 leading-relaxed mb-4">
            Scan with your phone or copy the direct link for dorm group chats, social media, dining hall flyers, and student organizations across {inst['name']}!
          </p>
          <div class="flex flex-wrap items-center gap-3 justify-center sm:justify-start">
            <div class="px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs sm:text-sm text-blue-300 select-all">
              https://rannbar-on.com/{key}
            </div>
            <button onclick="navigator.clipboard.writeText('https://rannbar-on.com/{key}'); alert('Link copied to clipboard!');" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition shadow-sm">
              Copy Link
            </button>
            <a href="/{key}_qr.png" download="{inst['short_name']}_Vote_Early_QR.png" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition">
              Download PNG
            </a>
            <a href="/{key}_qr.svg" download="{inst['short_name']}_Vote_Early_QR.svg" class="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-xs transition">
              Download SVG
            </a>
            <a href="/campuses" class="px-4 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 font-semibold text-xs transition">
              All 111 NC Campuses →
            </a>
          </div>
        </div>

        <!-- QR Code Visual -->
        <div class="bg-white p-4 rounded-2xl shadow-2xl border-4 border-blue-500/30 shrink-0 text-center">
          <img src="data:image/png;base64,{qr_b64}" alt="QR code for {inst['name']} student early voting guide" class="w-48 h-48 sm:w-52 sm:h-52 object-contain mx-auto" />
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

    # Save to mainwebsite (both key.html and key/index.html)
    with open(f"{MAIN_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    os.makedirs(f"{MAIN_DIR}/{key}", exist_ok=True)
    with open(f"{MAIN_DIR}/{key}/index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Mirror to local Fall26 workspace
    with open(f"{LOCAL_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)

print(f"Generated {len(institutions)} individual campus pages with voter guides.")

# 6. Master Directory page (campuses.html) with voter guide hub
print("4. Updating Master Directory page (campuses.html)...")

cards_json = []
for inst in institutions:
    cname = inst['county'].upper()
    c_display = cname.title() + " County"
    cards_json.append({
        'key': inst['key'],
        'name': inst['name'],
        'short_name': inst['short_name'],
        'type': inst['type'],
        'county': c_display,
        'city': inst['city'],
        'icon': inst['badge_icon'],
        'id_approved': inst['id_approved'],
        'id_card': inst['id_card_name'],
        'url': f"https://rannbar-on.com/{inst['key']}"
    })

cards_json_str = json.dumps(cards_json)

campuses_html = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Colleges & Universities Student Voting Directory | Rann Bar-On</title>
  <meta name="description" content="Complete directory of early voting guides for all 111 colleges, universities, and community colleges across North Carolina. Voter ID rules, candidate guides (Dem, Rep, Ind), polling sites, and QR codes.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/campuses">
  <meta property="og:title" content="NC Colleges & Universities Student Early Voting Directory">
  <meta property="og:description" content="Find your campus early voting guide, candidate guides (Democratic, Republican, Independent), approved voter ID rules, and scannable QR codes for all 111 NC colleges and universities.">

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

    .font-mono {{
      font-family: 'JetBrains Mono', monospace;
    }}
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased">

  <!-- Top Announcement Bar -->
  <div class="bg-gradient-to-r from-blue-950 via-indigo-950 to-slate-950 px-4 py-2.5 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-1.5">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span>North Carolina Early Voting is <b>OPEN STATEWIDE</b> through <b>Saturday, October 31, 2026</b></span>
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
        <a href="#statewide-guides" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
          🗳️ Voter Guides
        </a>
        <a href="https://rannbar-on.com/" class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition">
          ← Main Website
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 bg-gradient-to-b from-slate-900/50 to-slate-950">
    <div class="max-w-4xl mx-auto text-center">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-4">
        <span>🏛️ Statewide Student Voting Portal</span>
        <span class="text-slate-600">•</span>
        <span>111 NC Higher Education Institutions</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        North Carolina Colleges & Universities <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-300">Early Voting Guides & QR Directory</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Select your campus below to view your local polling site, candidate guides from Democratic, Republican, and Independent sources, official voter ID rules, and download scannable QR codes.
      </p>

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
                 class="w-full bg-slate-900 border-2 border-slate-700 focus:border-blue-500 rounded-2xl py-3.5 pl-12 pr-4 text-sm sm:text-base text-white placeholder-slate-400 focus:outline-none focus:ring-4 focus:ring-blue-500/20 transition shadow-lg" />
          <div class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 text-lg">
            🔍
          </div>
        </div>

        <!-- Filter Buttons -->
        <div class="flex flex-wrap items-center justify-center gap-2 text-xs font-semibold pt-1">
          <button onclick="setFilter('all')" id="btn-all" class="filter-btn px-3.5 py-1.5 rounded-xl bg-blue-600 text-white border border-blue-500 transition shadow-sm">
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
      <!-- Populated via JavaScript for instantaneous search -->
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

  <!-- Instant Search & Filter Logic -->
  <script>
    const campusesData = {cards_json_str};
    let currentFilter = 'all';

    function renderCampuses(list) {{
      const grid = document.getElementById('campuses-grid');
      const countEl = document.getElementById('results-count');
      countEl.innerText = `Showing ${{list.length}} Colleges & Universities`;

      if (list.length === 0) {{
        grid.innerHTML = `
          <div class="col-span-full text-center py-12 bg-slate-900 border border-slate-800 rounded-2xl p-8">
            <div class="text-3xl mb-2">🔍</div>
            <h3 class="text-lg font-bold text-white">No campuses matched your search</h3>
            <p class="text-xs text-slate-400 mt-1">Try searching for a different college name, municipality, or county.</p>
            <button onclick="document.getElementById('campus-search').value = ''; setFilter('all');" class="mt-4 px-4 py-2 rounded-xl bg-blue-600 text-white font-semibold text-xs">Reset Search</button>
          </div>
        `;
        return;
      }}

      grid.innerHTML = list.map(c => {{
        const idBadge = c.id_approved 
          ? `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✓ Approved Student ID</span>`
          : `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20">⚠️ Alternative Photo ID</span>`;

        const typeColor = c.type === 'UNC System' 
          ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' 
          : (c.type.includes('Community') ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-purple-500/10 text-purple-400 border-purple-500/20');

        return `
        <div class="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-sm flex flex-col justify-between transition hover:-translate-y-0.5">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-lg">${{c.icon}}</span>
              <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${{typeColor}}">${{c.type}}</span>
            </div>
            <h3 class="font-bold text-white text-base leading-snug">${{c.name}}</h3>
            <p class="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
              <span>📍 ${{c.city}}, NC</span>
              <span>•</span>
              <span class="font-medium text-slate-300">${{c.county}}</span>
            </p>
            <div class="mt-3">
              ${{idBadge}}
            </div>
          </div>

          <div class="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
            <a href="/${{c.key}}" class="flex-grow py-2 px-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs text-center transition shadow-sm">
              View Guide →
            </a>
            <a href="/${{c.key}}_qr.png" download="${{c.short_name}}_Vote_QR.png" class="py-2 px-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition" title="Download QR PNG">
              📥 QR
            </a>
          </div>
        </div>
        `;
      }}).join('');
    }}

    function filterCampuses() {{
      const query = document.getElementById('campus-search').value.toLowerCase().trim();
      
      const filtered = campusesData.filter(c => {{
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
      }});

      renderCampuses(filtered);
    }}

    function setFilter(filter) {{
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(btn => {{
        btn.classList.remove('bg-blue-600', 'text-white', 'border-blue-500');
        btn.classList.add('bg-slate-900', 'text-slate-300', 'border-slate-700');
      }});
      const activeBtn = document.getElementById(`btn-${{filter}}`);
      if (activeBtn) {{
        activeBtn.classList.remove('bg-slate-900', 'text-slate-300', 'border-slate-700');
        activeBtn.classList.add('bg-blue-600', 'text-white', 'border-blue-500');
      }}
      filterCampuses();
    }}

    // Initial render
    renderCampuses(campusesData);
  </script>

</body>
</html>
'''

with open(f"{MAIN_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
os.makedirs(f"{MAIN_DIR}/campuses", exist_ok=True)
with open(f"{MAIN_DIR}/campuses/index.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)

with open(f"{LOCAL_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)

print("Master campuses.html updated successfully!")
print("ALL DONE!")
