#!/usr/bin/env python3
"""
North Carolina Student Voting Platform - Statewide Generator
Builds voting guides for all 110 NC higher education institutions,
the master directory (/campuses), and dynamic QR portal (/vote).
"""

import os
import json
import base64
import re
import urllib.parse

MAIN_DIR = os.environ.get('CI_PROJECT_DIR') or os.environ.get('GITHUB_WORKSPACE') or os.path.dirname(os.path.abspath(__file__))
LOCAL_DIR = '/home/rann/Documents/math/teaching/105L/Fall26' if os.path.exists('/home/rann/Documents/math/teaching/105L/Fall26') else None
CACHE_DIR = f'{MAIN_DIR}/.nc_voting_cache'
GITLAB_REPO_URL = os.environ.get('CI_PROJECT_URL') or 'https://github.com/rannbaron/mainwebsite'
GITLAB_ISSUES_URL = os.environ.get('GITLAB_ISSUES_URL') or 'https://github.com/rannbaron/mainwebsite/issues'
VERIFIED_UPDATE_TIME = "October 26, 2026 at 1:45 PM EDT"

print("1. Loading cached NC election data...")
with open(f'{CACHE_DIR}/all_institutions.json', 'r', encoding='utf-8') as f:
    institutions = json.load(f)

# Ensure St. Andrews is excluded
institutions = [i for i in institutions if i['key'] != 'standrewsvote']

with open(f'{CACHE_DIR}/county_boe_info.json', 'r', encoding='utf-8') as f:
    boe_list = json.load(f)
boe_by_county = {c['Name'].upper(): c for c in boe_list}

with open(f'{CACHE_DIR}/county_early_voting_sites.json', 'r', encoding='utf-8') as f:
    sites_by_county = json.load(f)

with open(f'{CACHE_DIR}/campus_geo_data.json', 'r', encoding='utf-8') as f:
    campus_geo_list = json.load(f)
campus_geo_list = [g for g in campus_geo_list if g['key'] != 'standrewsvote']
campus_geo_json_str = json.dumps(campus_geo_list)

with open(f'{CACHE_DIR}/county_precincts_map.json', 'r', encoding='utf-8') as f:
    precincts_by_county = json.load(f)

with open(f'{CACHE_DIR}/campus_primary_precincts.json', 'r', encoding='utf-8') as f:
    campus_primary_precincts = json.load(f)
if 'standrewsvote' in campus_primary_precincts:
    del campus_primary_precincts['standrewsvote']
campus_primary_precincts_json_str = json.dumps(campus_primary_precincts)

print(f"Loaded {len(institutions)} institutions across North Carolina.")

def clean_site_name(name):
    if not name:
        return ""
    s = str(name).strip()
    if "NCCU" in s.upper():
        return "NCCU - Turner Law Building"
    if "LITTLE RIVER" in s.upper():
        return "Little River Community Complex"
    if "WESTERN CAROLINA" in s.upper() or "LITTLE SAVANNAH" in s.upper() or "HEALTH AND HUMAN" in s.upper():
        return "WCU Health and Human Sciences Building (HHS)"
    
    minor = {'of', 'and', 'at', 'the', 'for', 'in', 'on', 'by'}
    acronyms = {'NCCU', 'NC', 'UNC', 'NCSU', 'WCU', 'HHS', 'GOP', 'BOE', 'USA', 'US', 'DPS', 'STEM', 'W.I.', 'E.K.', 'W.J.', 'C.C.', 'KIPP'}
    words = s.split()
    out = []
    for i, w in enumerate(words):
        m = re.match(r'^([^\w]*)(.*?)([^\w]*)$', w)
        if m:
            prefix, core, suffix = m.groups()
        else:
            prefix, core, suffix = '', w, ''
        core_up = core.upper()
        if core_up in acronyms:
            out.append(prefix + core_up + suffix)
        elif i > 0 and core.lower() in minor:
            out.append(prefix + core.lower() + suffix)
        else:
            out.append(prefix + core.capitalize() + suffix)
    res = " ".join(out)
    res = re.sub(r'\bBoard Of Elections\b', 'Board of Elections', res)
    res = re.sub(r'\bDurham, Nc\b', 'Durham, NC', res)
    return res

def clean_address(addr):
    if not addr:
        return ""
    if "4121 LITTLE SAVANNAH" in str(addr).upper():
        return "4121 Little Savannah Rd, Cullowhee, NC 28723"
    res = str(addr).title()
    res = re.sub(r',\s*Nc\b', ', NC', res, flags=re.I)
    res = re.sub(r'\bNc\b', 'NC', res)
    return re.sub(r'\s+', ' ', res).strip()

def clean_boe_name(name, c_display):
    if not name:
        return f"{c_display} Board of Elections"
    res = str(name).title()
    res = re.sub(r'\bBoard Of Elections\b', 'Board of Elections', res)
    res = re.sub(r'\bOf\b', 'of', res)
    return res

def generate_county_hours_table_html(complete_html, c_display):
    if not complete_html:
        return f'<p class="text-xs text-slate-300">Contact the {c_display} Board of Elections for official daily operating hours.</p>'
    pairs = re.findall(r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>', complete_html, re.DOTALL)
    if not pairs:
        return f'<p class="text-xs text-slate-300">Contact the {c_display} Board of Elections for official daily operating hours.</p>'
    rows = []
    for d, h in pairs:
        d_clean = re.sub(r'<[^>]+>', '', d).strip()
        h_clean = re.sub(r'<[^>]+>', '', h).strip()
        h_clean = re.sub(r'a\.m\.', 'AM', h_clean, flags=re.I)
        h_clean = re.sub(r'p\.m\.', 'PM', h_clean, flags=re.I)
        h_clean = h_clean.replace('-', '–')
        is_sunday = 'sunday' in d_clean.lower()
        is_saturday = 'saturday' in d_clean.lower()
        is_final = 'october 31' in d_clean.lower()
        
        if is_final:
            r_cls = 'bg-amber-500/10 font-bold border-t border-amber-500/30'
            t_cls = 'text-amber-300 font-bold'
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Closes 3 PM</span>'
        elif is_sunday:
            r_cls = 'bg-slate-900/40'
            t_cls = 'text-blue-300 font-semibold'
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/20">Sunday</span>'
        elif is_saturday:
            r_cls = 'bg-slate-900/20'
            t_cls = 'text-blue-300 font-semibold'
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Saturday</span>'
        else:
            r_cls = ''
            t_cls = 'text-slate-200 font-mono'
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-800/60 text-slate-400">Weekday</span>'
            
        rows.append(f'''
        <tr class="{r_cls} border-b border-slate-800/60">
          <td class="py-2.5 px-3 text-slate-200 text-xs font-medium">{d_clean}</td>
          <td class="py-2.5 px-3 font-mono {t_cls} text-xs">{h_clean}</td>
          <td class="py-2.5 px-3 text-right">{badge}</td>
        </tr>
        ''')
    return f'''
    <div class="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
      <table class="w-full text-left text-xs">
        <thead class="bg-slate-900/90 text-slate-400 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-800">
          <tr>
            <th class="py-2.5 px-3">Date / Window</th>
            <th class="py-2.5 px-3">Voting Hours</th>
            <th class="py-2.5 px-3 text-right">Schedule Type</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-800/40">
          {''.join(rows)}
        </tbody>
      </table>
    </div>
    '''

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
    if os.path.exists(png_path):
        with open(png_path, 'rb') as f:
            qr_b64_map[key] = base64.b64encode(f.read()).decode('utf-8')

sorted_institutions = sorted(institutions, key=lambda x: x['name'])
campus_options = []
for inst in sorted_institutions:
    type_badge = "UNC" if inst['type'] == 'UNC System' else ("CC" if "Community" in inst['type'] else "Private")
    campus_options.append(f'<option value="/{inst["key"]}">{inst["name"]} ({inst["city"]}) - {type_badge}</option>')
campus_options_html = '\n'.join(campus_options)

print("3. Generating individual campus voting guide pages with Geolocation...")

for inst in institutions:
    key = inst['key']
    cname = inst['county'].upper()
    boe = boe_by_county.get(cname, {})
    c_display = cname.title() + " County"
    boe_phone = boe.get('OfficePhoneNum', '(919) 814-0700')
    boe_addr = clean_address(boe.get('FullAddress', f'{c_display} Board of Elections, NC'))
    boe_web = boe.get('WebsiteAddr', f'https://vt.ncsbe.gov/BOEInfo/?county={cname}')
    boe_name = clean_boe_name(boe.get('OfficeName'), c_display)

    county_sites_raw = sites_by_county.get(cname, [])
    primary_site = None
    kw = inst.get('site_keyword', '').upper()
    for s in county_sites_raw:
        if kw and kw in s['Name'].upper():
            primary_site = s
            break
    if not primary_site and county_sites_raw:
        primary_site = county_sites_raw[0]

    if primary_site:
        p_name = clean_site_name(primary_site['Name'])
        p_addr = clean_address(primary_site['SiteAddressComplete'])
        p_hours = primary_site.get('CurrentHours', '8:00 AM – 7:30 PM')
        p_maps = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(primary_site['SiteAddressComplete'])}"
        p_complete_html = primary_site.get('CompleteHoursHTML', '')
    else:
        p_name = f"{c_display} Early Voting Site"
        p_addr = boe_addr
        p_hours = "8:00 AM – 7:30 PM"
        p_maps = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(boe_addr)}"
        p_complete_html = ""

    county_sites_data = []
    for idx, s in enumerate(county_sites_raw):
        s_title = clean_site_name(s['Name'])
        s_address = clean_address(s['SiteAddressComplete'])
        s_maps = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(s['SiteAddressComplete'])}"
        county_sites_data.append({
            'name': s_title,
            'addr': s_address,
            'lat': s['SiteCoordLat'],
            'lon': s['SiteCoordLong'],
            'maps': s_maps
        })

    county_sites_json_str = json.dumps(county_sites_data)

    c_precincts = precincts_by_county.get(cname, [])
    county_precincts_json_str = json.dumps(c_precincts)
    campus_precinct_info = campus_primary_precincts.get(key, {})
    campus_precinct_json_str = json.dumps(campus_precinct_info)

    hours_table_html = generate_county_hours_table_html(p_complete_html, c_display)

    local_transit = {
        'dukevote': 'Accessible via Duke Transit C1 (East-West shuttle, stopping at Chapel Drive), Bull City Connector, and Duke Vans (free for students after 5:00 PM via TransLoc or 919-684-2020).',
        'wcuvote': 'Free WCU Cat-Tran shuttle (All-Campus / HHS route) connects central campus (University Center, residence halls) across NC-107 directly to the Health and Human Sciences Building.',
        'nccuvote': 'Located directly on the NCCU campus at Turner Law Building on Nelson Street; walkable from residence halls and served by GoDurham Route 5.',
        'uncvote': 'Free service via Chapel Hill Transit bus routes (CL, D, and F routes connect main campus to Chapel Hill Public Library).',
        'ncsuvote': 'Central campus location served by Wolfline bus routes 1, 2, 3, and 7.',
        'appstatevote': 'Free AppalCART transit routes connect all residence halls to the student union.',
        'unccvote': 'Served by UNC Charlotte Niner Transit (Silver and Green routes) and Lynx Blue Line light rail.',
        'wfuvote': 'Wake Forest provides shuttle service from Benson University Center during early voting.'
    }
    transit_info_html = ''
    if key in local_transit:
        transit_info_html = f'''<p class="text-xs text-blue-300 mt-2.5 bg-blue-950/40 p-2.5 rounded-xl border border-blue-900/40 font-medium"><b>Transit &amp; Shuttle:</b> {local_transit[key]}</p>'''

    dem_county_url = county_dem_urls.get(cname, 'https://www.ncdp.org/county-parties/')
    rep_county_url = county_rep_urls.get(cname, 'https://www.ncgop.org/county_parties')

    is_private_school = (inst['type'] != 'UNC System' and 'Community' not in inst['type'])

    # Student ID Alert Box
    if inst['id_approved']:
        id_alert_box = f'''
        <div class="bg-emerald-950/40 border-2 border-emerald-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-emerald-500/20 text-emerald-300 font-bold shrink-0">
            [Approved]
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 mb-2">Approved by NC State Board of Elections</span>
            <h2 class="text-xl font-bold text-white mb-2">{inst['name']} Student ID is Valid for Voting!</h2>
            <p class="text-sm text-emerald-100/90 leading-relaxed mb-3">
              The North Carolina State Board of Elections officially approved the <b>{inst['id_card_name']}</b> for voter photo identification. You can use your physical plastic student ID to vote.
            </p>
            <div class="p-3.5 rounded-xl bg-emerald-900/30 border border-emerald-700/50 text-xs text-emerald-200/90 space-y-1.5 font-medium">
              <p><b>CRITICAL: PHYSICAL CARD REQUIRED.</b> Digital IDs stored on mobile phones (Apple Wallet, Google Wallet, photos) are <b>NOT ACCEPTED</b> under NC law.</p>
              <p><b>Other Accepted Photo IDs:</b> NC Driver’s License, US Passport, Military/Veteran ID, or free county Board of Elections ID card.</p>
              <p><b>Lacking an ID at the polls?</b> Fill out a Photo ID Exception Form at the check-in desk and cast a ballot that counts.</p>
            </div>
          </div>
        </div>
        '''
    else:
        id_alert_box = f'''
        <div class="bg-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
          <div class="p-3 rounded-xl bg-amber-500/20 text-amber-300 font-bold shrink-0">
            [Notice]
          </div>
          <div>
            <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">Student Photo ID Not On State Approved List</span>
            <h2 class="text-xl font-bold text-white mb-2">Student ID Card is NOT Accepted for Voting</h2>
            <p class="text-sm text-amber-100/90 leading-relaxed mb-3">
              Under North Carolina law, {inst['name']} student IDs are <b>not approved</b> for voting. You must present an approved alternative photo ID.
            </p>
            <div class="p-3.5 rounded-xl bg-amber-900/30 border border-amber-700/50 text-xs text-amber-200/90 space-y-1.5 font-medium">
              <p><b>WHAT YOU CAN USE INSTEAD:</b></p>
              <ul class="list-disc pl-5 space-y-1 text-slate-200">
                <li><b>North Carolina Driver’s License</b> or NC DMV State ID (unexpired or expired up to 1 year).</li>
                <li><b>U.S. Passport</b> or U.S. Passport Card (must be unexpired).</li>
                <li><b>Out-of-State Driver’s License</b> (accepted only if you registered to vote in NC within 90 days of the election).</li>
                <li><b>Free Voter Photo ID Card:</b> Issued by your county Board of Elections.</li>
                <li><b>Photo ID Exception Form:</b> If you lack an ID due to an allowable exception, you can complete an Exception Form at the check-in desk.</li>
              </ul>
            </div>
          </div>
        </div>
        '''

    # Same-Day Registration info with NCSBE Numbered Memo 2023-05
    if is_private_school:
        same_day_photo_id_note = f"""Under NCSBE Numbered Memo 2023-05, because {inst['name']} is a private university, on-campus students relying on the university housing roster MUST present their physical <b>{inst['id_card_name']}</b>. Alternative photo IDs (such as an out-of-state driver's license or passport) cannot be paired with a private university housing roster. (Confirmed with {c_display} Board of Elections)."""
    else:
        same_day_photo_id_note = f"""Present your approved physical <b>{inst['id_card_name']}</b>, NC Driver's License, or US Passport."""

    # County sites cards HTML
    sites_cards_html = []
    for idx, s in enumerate(county_sites_raw):
        s_title = clean_site_name(s['Name'])
        s_address = clean_address(s['SiteAddressComplete'])
        s_maps = f"https://www.google.com/maps/dir/?api=1&destination={urllib.parse.quote(s['SiteAddressComplete'])}"
        is_p = (s_title == p_name)
        border_cls = "border-2 border-blue-500/80 shadow-lg" if is_p else "border border-slate-800"
        tag_html = f'<span class="distance-tag"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">Primary Campus Site</span></span>' if is_p else '<span class="distance-tag"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400">Early Voting Site</span></span>'

        sites_cards_html.append(f'''
        <div id="site-card-{idx}" class="site-card bg-slate-900 {border_cls} rounded-2xl p-5 flex flex-col justify-between transition hover:border-slate-700">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-mono font-bold text-slate-400">Site #{idx+1}</span>
              {tag_html}
            </div>
            <h3 class="text-base font-bold text-white mb-1.5 leading-snug">{s_title}</h3>
            <p class="text-xs text-slate-300 mb-4">{s_address}</p>
          </div>
          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
            <a href="{s_maps}" target="_blank" rel="noopener" class="flex-1 py-2 px-3 rounded-xl bg-blue-600/20 hover:bg-blue-600 text-blue-300 hover:text-white border border-blue-500/30 text-xs font-semibold text-center transition flex items-center justify-center gap-1">
              <span>Directions</span>
              <span>↗</span>
            </a>
            <a href="{boe_web}" target="_blank" rel="noopener" class="py-2 px-3 rounded-xl bg-slate-950 hover:bg-slate-800 text-slate-400 text-xs font-medium text-center border border-slate-800 transition">
              <span>County BOE ↗</span>
            </a>
          </div>
        </div>
        ''')
    all_sites_cards_str = '\n'.join(sites_cards_html)

    qr_b64 = qr_b64_map.get(key, '')

    html_content = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst['short_name']} Student Voting Guide | Rann Bar-On</title>
  <meta name="description" content="Complete voting guide for {inst['name']} students in {c_display}, NC: voting sites, dynamic geolocation, voter ID rules, candidate guides, and hours.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/{key}">
  <meta property="og:title" content="{inst['short_name']} Student Voting Guide">
  <meta property="og:description" content="Everything {inst['name']} students need to vote in {c_display}: dynamic nearest site detection, voter ID rules, and candidate guides.">
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
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased" data-campus="{inst['name']}" data-key="{key}" data-county="{inst['county']}">

  <!-- Top Announcement Bar -->
  <div id="top-announcement-bar" class="bg-gradient-to-r from-blue-950 via-indigo-950 to-slate-950 px-4 py-2 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-2">
      <span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
      <span>Early Voting is <b>OPEN STATEWIDE</b> through <b>Saturday, October 31, 2026</b></span>
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
        <a href="#polling-site" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm">
          Voting Sites
        </a>
        <a href="#voter-guides" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 hover:bg-indigo-500/20 transition">
          Guides
        </a>
        <a href="#voter-id" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 transition">
          Voter ID
        </a>
        <a href="#qr-code" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
          QR
        </a>
      </div>
    </div>
  </header>

  <!-- Campus Quick Jump Selector Bar -->
  <nav class="bg-slate-900/95 border-b border-slate-800/80 py-2.5 px-4 backdrop-blur shadow-inner">
    <div class="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <a href="/campuses" class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 font-bold text-xs transition">
          <span>Browse All 110 NC Campuses</span>
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

  <!-- Hero Section -->
  <section class="relative py-10 sm:py-14 px-4 sm:px-6 border-b border-slate-800/80 overflow-hidden">
    <div class="max-w-4xl mx-auto text-center relative z-10">
      
      <!-- Verified Source & Verification Status Banner -->
      <div class="mb-6 p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-left shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div class="flex items-center gap-2.5">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Verified Source
          </span>
          <span class="text-slate-200">
            Official NC State Board of Elections (NCSBE) &amp; {c_display} Board of Elections
          </span>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-slate-400 text-[11px]">
          <span>Last Verified Update: <b class="text-slate-200 font-mono">{VERIFIED_UPDATE_TIME}</b></span>
          <span>•</span>
          <a href="{boe_web}" target="_blank" rel="noopener" class="text-blue-400 hover:underline">Information Sources &amp; BOE Portal ↗</a>
          <span>•</span>
          <a href="{GITLAB_REPO_URL}" target="_blank" rel="noopener" class="text-indigo-400 hover:underline">GitHub Source ↗</a>
        </div>
      </div>

      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/30 mb-4">
        <span>{inst['name']}</span>
        <span class="text-slate-600">•</span>
        <span>Student Voting Guide</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        {inst['short_name']} Student Guide <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-sky-300">to Early Voting in {c_display}</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Everything you need to cast your ballot in North Carolina: campus early voting locations, dynamic GPS nearest site detection, student voter ID rules, and non-partisan voting info.
      </p>

      <!-- Key Stat Pills -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto text-left">
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Early Voting Window</div>
          <div class="text-base font-bold text-white mt-0.5">Oct 15 – Oct 31</div>
          <div class="text-[11px] text-emerald-400 mt-1 font-mono">Open through 3 PM Sat</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Primary Site</div>
          <div id="stat-primary-site" class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{p_name}</div>
          <div id="stat-primary-dist" class="text-[11px] text-blue-400 mt-1 font-mono">{inst['city']}, NC</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Missed Registration?</div>
          <div class="text-base font-bold text-white mt-0.5">Same-Day Reg</div>
          <div class="text-[11px] text-purple-400 mt-1 font-mono">Register &amp; vote at once</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Voter ID Rule</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{'Approved' if inst['id_approved'] else 'Alt ID Required'}</div>
          <div class="text-[11px] {'text-emerald-400' if inst['id_approved'] else 'text-amber-400'} mt-1 font-mono">{'Physical Student Card' if inst['id_approved'] else 'NC License / Passport'}</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Cross-Campus Proximity Alert Banner -->
  <div id="cross-campus-banner" class="hidden bg-indigo-950 border-b border-indigo-500/40 px-4 py-3 text-center text-xs sm:text-sm font-medium text-indigo-200">
    <div class="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
      <span id="cross-campus-text"></span>
      <div class="flex items-center gap-2">
        <a id="cross-campus-link" href="#" class="px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition">
          Switch Guide →
        </a>
        <button onclick="cancelRedirect()" class="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs">
          Stay on this page
        </button>
      </div>
    </div>
  </div>

  <!-- CRITICAL VOTER ID RULE SECTION -->
  <section id="voter-id" class="py-8 px-4 sm:px-6 bg-slate-950 border-b border-slate-800/80">
    <div class="max-w-4xl mx-auto">
      {id_alert_box}
    </div>
  </section>

  <!-- Main Content Container -->
  <main class="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-12">

    <!-- Section 1: Campus Polling Site with Geolocation Finder -->
    <section id="polling-site" class="scroll-mt-20">
      
      <!-- Interactive Geolocation Discovery Card -->
      <div class="bg-gradient-to-r from-blue-950/40 via-indigo-950/30 to-slate-900 border border-blue-500/30 rounded-2xl p-4 sm:p-5 mb-6 shadow-md">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 class="text-sm font-bold text-white">Find Your Nearest Polling Location Dynamically</h3>
            <p class="text-xs text-slate-300 mt-1">
              Allow location access to update this page with exact distances to all {c_display} early voting sites and find your closest voting location.
            </p>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <button onclick="detectNearestSite()" id="btn-detect-loc" class="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition shadow-sm">
              Detect My Location
            </button>
          </div>
        </div>
        <div id="geo-status-banner" class="mt-3 text-xs hidden"></div>
      </div>

      <div class="flex items-center justify-between mb-4">
        <div>
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Campus / Nearest Early Voting Site</span>
          <h2 id="main-site-title" class="text-2xl sm:text-3xl font-extrabold text-white mt-1">{p_name}</h2>
        </div>
        <span id="site-open-tag" class="hidden sm:inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Open to all {c_display} Voters
        </span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Left: Address & Directions -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:col-span-1 flex flex-col justify-between">
          <div>
            <div class="text-sm font-semibold text-slate-300 mb-2">Address &amp; Directions</div>
            <p id="main-site-addr" class="text-base font-bold text-white leading-snug">
              {p_addr}
            </p>
            <p class="text-xs text-slate-400 mt-2">
              Located in {c_display}, NC. Any registered county voter can cast their ballot here during early voting.
            </p>
            {transit_info_html}
          </div>
          <div class="mt-6 pt-4 border-t border-slate-800">
            <a id="main-site-maps" href="{p_maps}" target="_blank" rel="noopener" class="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs text-center transition shadow-md flex items-center justify-center gap-1.5">
              <span>Open in Google Maps</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <!-- Right: Official Hours Table (Accurate Sunday Hours) -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:col-span-2 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-semibold text-slate-300">Official Daily Voting Hours</span>
              <span class="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
                {c_display} Approved Schedule
              </span>
            </div>
            
            {hours_table_html}
          </div>
          <p class="text-xs text-slate-400 mt-4 leading-relaxed">
            Note: During early voting, you can vote at <b>any</b> early voting location in {c_display}, regardless of your precinct!
          </p>
        </div>
      </div>
    </section>

    <!-- Section 2: Local Candidate Voter Guides (Democratic, Republican & Independent) -->
    <section id="voter-guides" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-8">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Candidate Research &amp; Endorsements</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-2">Local Candidate Guides for {inst['short_name']} Students</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Before heading to the ballot box in {c_display}, review questionnaires, policy scorecards, and endorsements from multiple political perspectives:
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- 1. Democratic-Leaning Guide -->
        <div class="bg-slate-950/80 border border-blue-500/40 rounded-2xl p-5 sm:p-6 flex flex-col justify-between shadow-md">
          <div>
            <div class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-blue-500/20 text-blue-400 border border-blue-500/30 mb-3">
              <span>Democratic / Progressive</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Blue Voter Guide &amp; NC Dems</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Personalized candidate recommendations endorsed by labor, reproductive rights, environmental, and progressive organizations in North Carolina.
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
            <div class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 mb-3">
              <span>Republican / Conservative</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">iVoterGuide &amp; NC Values</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Research-backed candidate evaluations and ratings based on conservative constitutional principles, fiscal policies, and traditional values across {c_display}.
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
            <div class="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 mb-3">
              <span>Independent / Non-Partisan</span>
            </div>
            <h3 class="text-lg font-bold text-white mb-2">Vote411 (League of Women Voters)</h3>
            <p class="text-xs text-slate-300 leading-relaxed mb-4">
              Non-partisan candidate questionnaires and unbiased comparisons by the League of Women Voters of North Carolina.
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
            <div class="inline-flex items-center px-2.5 py-1 rounded bg-blue-500/10 text-blue-400 font-bold text-xs mb-3">
              <span>On-Campus Residents</span>
            </div>
            <h4 class="text-sm font-bold text-white mb-1.5">What to Bring:</h4>
            <ul class="text-xs text-slate-300 space-y-2.5">
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold shrink-0">[Photo ID]</span>
                <span><b>Photo ID Requirement:</b> {same_day_photo_id_note}</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold shrink-0">[Roster]</span>
                <span><b>Housing Roster Separation Rule:</b> Under NCSBE rules, an approved campus housing roster provided to the County Board of Elections serves as proof of residency <b>only if</b> it explicitly separates and identifies residents by individual campus housing facility / dormitory, and is presented alongside the student\'s photo ID.</span>
              </li>
            </ul>
          </div>

          <!-- Off Campus Students -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
            <div class="inline-flex items-center px-2.5 py-1 rounded bg-purple-500/10 text-purple-400 font-bold text-xs mb-3">
              <span>Off-Campus Residents</span>
            </div>
            <h4 class="text-sm font-bold text-white mb-1.5">What to Bring:</h4>
            <ul class="text-xs text-slate-300 space-y-2.5">
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold shrink-0">[Photo ID]</span>
                <span><b>Photo ID:</b> Any approved photo identification.</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold shrink-0">[Proof]</span>
                <span><b>Proof of Residence:</b> A document showing your name and current local {c_display} address (utility bill, bank statement, paycheck, lease, or university official letter; digital on smartphone is accepted).</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-400 leading-relaxed">
          <b>Student Voting Rights:</b> College students have the established legal right to choose whether to register and vote at their college address or their permanent home address. You must choose one and vote only once per election.
        </div>
      </div>
    </section>

    <!-- Section 4: All Early Voting Sites in County -->
    <section id="sites" class="scroll-mt-20">
      <div class="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Countywide Flexibility</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1">All {len(county_sites_raw)} {c_display} Early Voting Sites</h2>
          <p class="text-sm text-slate-400 mt-1">Any registered {c_display} voter can cast a ballot at any of these sites during early voting hours.</p>
        </div>
      </div>

      <div id="voting-sites" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {all_sites_cards_str}
      </div>
    </section>

    <!-- Section 5: QR Code Card -->
    <section id="qr-code" class="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="flex flex-col sm:flex-row items-center gap-6 sm:gap-8 justify-between">
        <div class="max-w-xl text-center sm:text-left">
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Share with Classmates &amp; Dorms</span>
          <h2 class="text-2xl font-bold text-white mt-1 mb-2">Share this {inst['short_name']} Voting Guide</h2>
          <p class="text-sm text-slate-300 leading-relaxed mb-4">
            Spread the word across your campus! Share this link in group chats, dorm channels, and student organization social media.
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
              All 110 NC Campuses →
            </a>
          </div>
        </div>

        <!-- QR Code Box -->
        <div class="bg-white p-4 rounded-2xl shadow-2xl border-4 border-blue-500/30 shrink-0 text-center">
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
        <p class="font-medium text-slate-300">Non-partisan student voting guide prepared by Rann Bar-On under the <a href="{GITLAB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener" class="text-blue-400 hover:underline">MIT License</a>.</p>
        <p class="text-[11px] text-slate-500 mt-0.5">Verified Source: Official voting data sourced from the {boe_name} and the North Carolina State Board of Elections. Last Verified Update: {VERIFIED_UPDATE_TIME}. <a href="{boe_web}" target="_blank" rel="noopener" class="text-blue-400 hover:underline ml-1">Information Sources ↗</a></p>
      </div>
      <div class="flex flex-wrap items-center justify-center sm:justify-end gap-4 text-xs">
        <a href="/campuses" class="text-blue-400 hover:underline">All 110 NC Campuses</a>
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
        <a href="{GITLAB_REPO_URL}" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Source</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Issues</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="{GITLAB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline">MIT License</a>
        <a href="/stats" class="text-slate-400 hover:text-slate-200 hover:underline">Usage Tracker</a>
        <a href="#support-site" onclick="openSupportModal(); return false;" class="text-amber-400 hover:text-amber-300 hover:underline flex items-center gap-1 font-medium">
          <span>Help Rann Bar-On maintain this site</span>
        </a>
      </div>
    </div>
  </footer>

  <!-- Geolocation & Dynamic Polling Site Script -->
  <script>
    const currentCampusKey = "{key}";
    const currentCampusName = "{inst['name']}";
    const allCampuses = {campus_geo_json_str};
    const countySites = {county_sites_json_str};
    const countyPrecincts = {county_precincts_json_str};
    const campusPrimaryPrecinct = {campus_precinct_json_str};
    let redirectTimer = null;

    function haversine(lat1, lon1, lat2, lon2) {{
      const R = 3958.8; // miles
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return Math.round(R * c * 10) / 10;
    }}

    function cancelRedirect() {{
      if (redirectTimer) {{
        clearInterval(redirectTimer);
        redirectTimer = null;
      }}
      document.getElementById('cross-campus-banner').classList.add('hidden');
    }}

    function detectNearestSite() {{
      if (!navigator.geolocation) {{
        alert("Geolocation is not supported by your browser.");
        return;
      }}

      const statusEl = document.getElementById('geo-status-banner');
      statusEl.className = 'mt-3 text-xs text-blue-400 font-medium';
      statusEl.innerText = 'Detecting your location...';
      statusEl.classList.remove('hidden');

      navigator.geolocation.getCurrentPosition(
        position => {{
          const uLat = position.coords.latitude;
          const uLon = position.coords.longitude;
          sessionStorage.setItem('nc_user_lat', uLat);
          sessionStorage.setItem('nc_user_lon', uLon);

          applyLocation(uLat, uLon);
        }},
        error => {{
          statusEl.className = 'mt-3 text-xs text-amber-400 font-medium';
          statusEl.innerText = "Location permission was denied or unavailable. You can still browse manually!";
        }},
        {{ enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }}
      );
    }}

    function applyLocation(uLat, uLon) {{
      const statusEl = document.getElementById('geo-status-banner');
      const EARLY_VOTING_DEADLINE = new Date('2026-10-31T15:00:00-04:00');
      const urlParams = new URLSearchParams(window.location.search);
      const isElectionDay = (new Date() >= EARLY_VOTING_DEADLINE) || (urlParams.get('mode') === 'election_day');

      if (isElectionDay) {{
        // Election Day: Find closest precinct
        if (countyPrecincts && countyPrecincts.length > 0) {{
          countyPrecincts.forEach((p, idx) => {{
            p.distance = haversine(uLat, uLon, p.lat, p.lon);
            p.elemIndex = idx;
          }});
          const sortedPrecincts = [...countyPrecincts].sort((a, b) => a.distance - b.distance);
          const nearestPrecinct = sortedPrecincts[0];

          const mainTitle = document.getElementById('main-site-title');
          const mainAddr = document.getElementById('main-site-addr');
          const mainMaps = document.getElementById('main-site-maps');
          const statSite = document.getElementById('stat-primary-site');
          const statDist = document.getElementById('stat-primary-dist');

          if (mainTitle && nearestPrecinct) {{
            mainTitle.innerText = `${{nearestPrecinct.name}} (${{nearestPrecinct.distance}} mi away)`;
            if (mainAddr) mainAddr.innerText = `Precinct ${{nearestPrecinct.prec_id}} • Assigned Election Day Polling Place`;
            if (mainMaps) {{
              mainMaps.href = `https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(nearestPrecinct.name + ', {c_display}, NC')}}`;
              mainMaps.innerHTML = '<span>Directions to Nearest Precinct</span><span>↗</span>';
            }}
            if (statSite) statSite.innerText = nearestPrecinct.name;
            if (statDist) statDist.innerText = `Precinct ${{nearestPrecinct.prec_id}} (${{nearestPrecinct.distance}} mi)`;
          }}

          statusEl.className = 'mt-3 text-xs text-emerald-400 font-medium';
          statusEl.innerHTML = `Located! Your closest Election Day precinct polling place is <b>${{nearestPrecinct.name}}</b> (<b>${{nearestPrecinct.distance}} miles away</b>). <a href="https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(nearestPrecinct.name + ', {c_display}, NC')}}" target="_blank" rel="noopener" class="underline font-bold text-white ml-2">Directions ↗</a>`;
        }}
      }} else {{
        // Early Voting
        if (countySites && countySites.length > 0) {{
          countySites.forEach((s, idx) => {{
            s.distance = haversine(uLat, uLon, s.lat, s.lon);
            s.elemIndex = idx;
          }});

          const sortedSites = [...countySites].sort((a, b) => a.distance - b.distance);
          const nearestSite = sortedSites[0];

          const mainTitle = document.getElementById('main-site-title');
          const mainAddr = document.getElementById('main-site-addr');
          const mainMaps = document.getElementById('main-site-maps');
          const statSite = document.getElementById('stat-primary-site');
          const statDist = document.getElementById('stat-primary-dist');

          if (mainTitle && nearestSite) {{
            mainTitle.innerText = `${{nearestSite.name}} (${{nearestSite.distance}} mi away)`;
            mainAddr.innerText = nearestSite.addr;
            mainMaps.href = nearestSite.maps;
            if (statSite) statSite.innerText = nearestSite.name;
            if (statDist) statDist.innerText = `${{nearestSite.distance}} miles away`;
          }}

          sortedSites.forEach((s, rank) => {{
            const card = document.getElementById(`site-card-${{s.elemIndex}}`);
            if (card) {{
              const tag = card.querySelector('.distance-tag');
              if (tag) {{
                tag.innerHTML = `<span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${{rank === 0 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'bg-slate-800 text-slate-300'}}">${{s.distance}} mi away</span>`;
              }}
              if (rank === 0) {{
                card.classList.remove('border-slate-800');
                card.classList.add('border-2', 'border-emerald-500', 'ring-2', 'ring-emerald-500/20');
              }}
            }}
          }});

          statusEl.className = 'mt-3 text-xs text-emerald-400 font-medium';
          statusEl.innerHTML = `Located! Your closest early voting site is <b>${{nearestSite.name}}</b> (<b>${{nearestSite.distance}} miles away</b>).`;
        }}
      }}

      // Check cross campus
      const sortedCampuses = [...allCampuses].map(c => ({{
        ...c,
        dist: haversine(uLat, uLon, c.lat, c.lon)
      }})).sort((a, b) => a.dist - b.dist);

      const closestCampus = sortedCampuses[0];
      if (closestCampus && closestCampus.key !== currentCampusKey && closestCampus.dist < 50) {{
        const banner = document.getElementById('cross-campus-banner');
        const bannerText = document.getElementById('cross-campus-text');
        const bannerLink = document.getElementById('cross-campus-link');

        let secondsLeft = 4;
        bannerText.innerHTML = `You appear closest to <b>${{closestCampus.name}}</b> in ${{closestCampus.city}} (<b>${{closestCampus.dist}} mi away</b>). Redirecting in <span id="redir-sec">${{secondsLeft}}</span>s...`;
        bannerLink.href = `/${{closestCampus.key}}?autoloc=1`;
        bannerLink.innerText = `Go to ${{closestCampus.short_name}} Guide →`;
        banner.classList.remove('hidden');

        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('autoloc') !== '1') {{
          redirectTimer = setInterval(() => {{
            secondsLeft -= 1;
            const secEl = document.getElementById('redir-sec');
            if (secEl) secEl.innerText = secondsLeft;
            if (secondsLeft <= 0) {{
              clearInterval(redirectTimer);
              window.location.href = `/${{closestCampus.key}}?autoloc=1`;
            }}
          }}, 1000);
        }}
      }}
    }}

    function checkElectionDayMode() {{
      const EARLY_VOTING_DEADLINE = new Date('2026-10-31T15:00:00-04:00');
      const urlParams = new URLSearchParams(window.location.search);
      if (new Date() >= EARLY_VOTING_DEADLINE || urlParams.get('mode') === 'election_day') {{
        const topBar = document.getElementById('top-announcement-bar');
        if (topBar) {{
          topBar.className = 'bg-gradient-to-r from-red-950 via-rose-950 to-slate-950 px-4 py-2.5 text-center text-xs sm:text-sm font-bold text-slate-100 border-b border-rose-900/50 shadow-md';
          topBar.innerHTML = '<span>Early Voting Has Ended • <b>ELECTION DAY IS TUESDAY, NOVEMBER 3, 2026</b> • Polls Open <b>6:30 AM – 7:30 PM</b></span>';
        }}
        const sitesSection = document.getElementById('voting-sites');
        if (sitesSection && !document.getElementById('election-day-alert')) {{
          const alertDiv = document.createElement('div');
          alertDiv.id = 'election-day-alert';
          alertDiv.className = 'bg-rose-950/60 border-2 border-rose-500 rounded-2xl p-5 sm:p-6 mb-8 text-white shadow-xl col-span-full';
          alertDiv.innerHTML = `
            <div class="space-y-3">
              <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30">Early Voting Concluded</span>
              <h2 class="text-lg sm:text-xl font-bold text-white">Election Day Voting Rules (Tuesday, Nov 3):</h2>
              <div class="p-3.5 rounded-xl bg-slate-950/80 border border-rose-900/60 text-xs sm:text-sm space-y-2 text-slate-200">
                <p><b>1. Assigned Precinct Only:</b> Early voting sites are closed. On Election Day, you must vote at your specifically assigned precinct polling place based on your address between <b>6:30 AM and 7:30 PM</b>.</p>
                <p><b>2. No Same-Day Registration:</b> Under NC Gen. Stat. § 163-82.6, same-day registration is not permitted on Election Day. You must already be registered.</p>
                <p><b>3. In line by 7:30 PM? Stay in line!</b> You are legally entitled to cast your ballot.</p>
              </div>
              <div class="flex flex-wrap gap-2 pt-1">
                <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" rel="noopener" class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition shadow-md">
                  Find Your Assigned Precinct (NCSBE Lookup) ↗
                </a>
                <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow-md">
                  Check Registration &amp; Sample Ballot ↗
                </a>
              </div>
            </div>
          `;
          sitesSection.insertBefore(alertDiv, sitesSection.firstChild);
        }}
      }}
    }}

    window.addEventListener('DOMContentLoaded', () => {{
      checkElectionDayMode();
      const urlParams = new URLSearchParams(window.location.search);
      const savedLat = sessionStorage.getItem('nc_user_lat');
      const savedLon = sessionStorage.getItem('nc_user_lon');

      if (urlParams.get('autoloc') === '1' && savedLat && savedLon) {{
        applyLocation(parseFloat(savedLat), parseFloat(savedLon));
      }} else if (savedLat && savedLon) {{
        applyLocation(parseFloat(savedLat), parseFloat(savedLon));
      }}
    }});
  </script>

  <!-- Support Modal -->
  <div id="support-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm transition-opacity duration-200">
    <div class="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl text-center">
      <button onclick="closeSupportModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-sm transition" aria-label="Close">
        Close [X]
      </button>
      
      <div class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30 mb-3">
        <span>Independent &amp; Community Supported</span>
      </div>
      
      <h3 class="text-xl sm:text-2xl font-bold text-white mb-2">Help Rann Bar-On maintain this site</h3>
      <p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-md mx-auto mb-6">
        This statewide student voting platform is independently built and self-funded as a free public service for students and voters across all 110 North Carolina colleges and universities. If you find this guide helpful, your contribution helps cover server hosting, domain fees, and continuous data updates!
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
        <!-- Venmo Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-blue-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#008CFF] text-white font-bold flex items-center justify-center text-xs">V</span>
            <span class="font-bold text-white text-sm">Venmo</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-blue-500/30 shadow-md my-1">
            <img src="/venmo_qr.png" alt="Venmo QR Code @Ran-Baron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-blue-400 mt-2 select-all">@Ran-Baron</div>
          <a href="https://account.venmo.com/u/Ran-Baron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#008CFF] hover:bg-blue-600 text-white font-semibold text-xs text-center transition shadow-sm">
            Pay via Venmo ↗
          </a>
        </div>

        <!-- CashApp Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-emerald-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#00D632] text-black font-extrabold flex items-center justify-center text-xs">$</span>
            <span class="font-bold text-white text-sm">Cash App</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-emerald-500/30 shadow-md my-1">
            <img src="/cashapp_qr.png" alt="Cash App QR Code $RanBaron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-emerald-400 mt-2 select-all">$RanBaron</div>
          <a href="https://cash.app/$RanBaron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#00D632] hover:bg-emerald-500 text-black font-bold text-xs text-center transition shadow-sm">
            Pay via Cash App ↗
          </a>
        </div>
      </div>

      <div class="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-500 text-center">
        Thank you for supporting non-partisan student voting access in North Carolina!
      </div>
    </div>
  </div>

  <script>
    function openSupportModal() {{
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.remove('hidden');
    }}
    function closeSupportModal() {{
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.add('hidden');
    }}
    window.addEventListener('click', (e) => {{
      const modal = document.getElementById('support-modal');
      if (e.target === modal) closeSupportModal();
    }});
    window.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeSupportModal();
    }});
  </script>

  <script src="/tracker.js"></script>
</body>
</html>
'''

    with open(f"{MAIN_DIR}/{key}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    os.makedirs(f"{MAIN_DIR}/{key}", exist_ok=True)
    with open(f"{MAIN_DIR}/{key}/index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    if LOCAL_DIR:
        with open(f"{LOCAL_DIR}/{key}.html", 'w', encoding='utf-8') as f:
            f.write(html_content)

print(f"Generated {len(institutions)} individual campus pages with geolocation.")

# Handle closed campus standrewsvote
standrews_redirect_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="3; url=/campuses">
  <title>St. Andrews University Voting Information | Rann Bar-On</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 text-center font-sans">
  <div class="max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl">
    <span class="inline-block px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 mb-4">Campus Closed</span>
    <h1 class="text-2xl font-bold text-white mb-3">St. Andrews University</h1>
    <p class="text-sm text-slate-300 mb-6 leading-relaxed">
      St. Andrews University in Laurinburg permanently closed in May 2025. You are being redirected to the active North Carolina Campus Voting Directory.
    </p>
    <a href="/campuses" class="inline-block py-2.5 px-5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition">
      Go to All 110 NC Campuses Directory →
    </a>
  </div>
</body>
</html>'''

with open(f"{MAIN_DIR}/standrewsvote.html", 'w', encoding='utf-8') as f:
    f.write(standrews_redirect_html)
if os.path.exists(f"{MAIN_DIR}/standrewsvote"):
    with open(f"{MAIN_DIR}/standrewsvote/index.html", 'w', encoding='utf-8') as f:
        f.write(standrews_redirect_html)


# 4. Generate campuses.html
print("4. Updating Master Directory page (campuses.html)...")

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
  <title>North Carolina Colleges &amp; Universities Early Voting Directory | Rann Bar-On</title>
  <meta name="description" content="Complete directory of early voting guides for all 110 NC colleges, universities, and community colleges: nearest sites, voter ID requirements, hours, and candidate guides.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/campuses">
  <meta property="og:title" content="NC Colleges &amp; Universities Student Voting Directory">
  <meta property="og:description" content="Voting guides for all 110 NC higher education institutions: find your campus voting site, voter ID status, and candidate guides.">
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
    .font-mono { font-family: 'JetBrains Mono', monospace; }
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-950 text-slate-100 antialiased font-sans" data-campus="Master Directory" data-key="campuses">

  <!-- Top Announcement Bar -->
  <div class="bg-gradient-to-r from-blue-950 via-indigo-950 to-slate-950 px-4 py-2 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-2">
      <span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
      <span>Early Voting is <b>OPEN STATEWIDE</b> through <b>Saturday, October 31, 2026</b></span>
    </span>
  </div>

  <!-- Header -->
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
        <a href="/vote" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-600 hover:bg-blue-500 text-white transition shadow-sm">
          Dynamic QR Portal
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <section class="relative py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 overflow-hidden">
    <div class="max-w-4xl mx-auto text-center relative z-10">

      <!-- Verified Source Banner -->
      <div class="mb-6 p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-left shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div class="flex items-center gap-2.5">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            Verified Source
          </span>
          <span class="text-slate-200">
            Official NC State Board of Elections (NCSBE) &amp; 100 County Boards of Elections
          </span>
        </div>
        <div class="flex flex-wrap items-center gap-3 text-slate-400 text-[11px]">
          <span>Last Verified Update: <b class="text-slate-200 font-mono">%%VERIFIED_UPDATE_TIME%%</b></span>
          <span>•</span>
          <a href="https://vt.ncsbe.gov/OSSite/" target="_blank" rel="noopener" class="text-blue-400 hover:underline">NCSBE Official Portal ↗</a>
        </div>
      </div>

      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/30 mb-4">
        <span>Statewide Student Voting Portal</span>
        <span class="text-slate-600">•</span>
        <span>110 Higher Ed Campuses</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        North Carolina Colleges &amp; Universities <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-sky-300">Student Voting Directory</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Select your college or university to view your campus early voting location, GPS directions, voter ID status, and candidate research guides.
      </p>

      <!-- Search & Geolocation Filter Controls -->
      <div class="max-w-2xl mx-auto space-y-4">
        <div class="flex flex-col sm:flex-row gap-2.5">
          <div class="relative flex-1">
            <input type="text" id="campus-search" oninput="filterCampuses()" placeholder="Search 110 campuses by school name, city, or county..." class="w-full bg-slate-900 border border-slate-700 focus:border-blue-500 rounded-xl px-4 py-3 text-xs sm:text-sm text-white placeholder-slate-500 focus:outline-none shadow-inner" />
          </div>
          <button onclick="sortCampusesByLocation()" id="btn-geo-sort" class="px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs transition shadow-md flex items-center justify-center gap-1.5 shrink-0">
            <span>Find Nearest to Me</span>
          </button>
        </div>
        <div id="geo-sort-status" class="text-xs text-slate-400 min-h-[18px]"></div>

        <!-- Filter Badges -->
        <div class="flex flex-wrap items-center justify-center gap-2 pt-2 text-xs">
          <button onclick="setFilter('ALL')" id="filter-btn-ALL" class="filter-badge px-3 py-1.5 rounded-lg bg-blue-600 text-white font-semibold border border-blue-500 transition">
            All 110 Campuses
          </button>
          <button onclick="setFilter('UNC')" id="filter-btn-UNC" class="filter-badge px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 transition">
            UNC System (16)
          </button>
          <button onclick="setFilter('CC')" id="filter-btn-CC" class="filter-badge px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 transition">
            Community Colleges (58)
          </button>
          <button onclick="setFilter('PRIVATE')" id="filter-btn-PRIVATE" class="filter-badge px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 transition">
            Independent / Private (36)
          </button>
        </div>
      </div>
    </div>
  </section>

  <!-- Directory Grid -->
  <main class="max-w-6xl mx-auto px-4 sm:px-6 py-10 flex-1">
    <div id="campus-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <!-- Populated via JavaScript -->
    </div>
  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-8 px-4 text-center text-xs text-slate-500">
    <div class="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
      <span>Non-partisan statewide student voting platform prepared by Rann Bar-On under the <a href="%%GITLAB_REPO_URL%%/blob/main/LICENSE" target="_blank" rel="noopener" class="text-blue-400 hover:underline">MIT License</a>.</span>
      <div class="flex flex-wrap items-center justify-center gap-4">
        <a href="/vote" class="text-blue-400 hover:underline">Dynamic QR Portal</a>
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
        <a href="%%GITLAB_REPO_URL%%" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Source</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="%%GITLAB_ISSUES_URL%%" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Issues</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="%%GITLAB_REPO_URL%%/blob/main/LICENSE" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline">MIT License</a>
        <a href="/stats" class="text-slate-400 hover:text-slate-200 hover:underline">Usage Tracker</a>
        <a href="#support-site" onclick="openSupportModal(); return false;" class="text-amber-400 hover:text-amber-300 hover:underline flex items-center gap-1 font-medium">
          <span>Help Rann Bar-On maintain this site</span>
        </a>
      </div>
    </div>
  </footer>

  <!-- Support Modal -->
  <div id="support-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm transition-opacity duration-200">
    <div class="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl text-center">
      <button onclick="closeSupportModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-sm transition" aria-label="Close">
        Close [X]
      </button>
      
      <div class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30 mb-3">
        <span>Independent &amp; Community Supported</span>
      </div>
      
      <h3 class="text-xl sm:text-2xl font-bold text-white mb-2">Help Rann Bar-On maintain this site</h3>
      <p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-md mx-auto mb-6">
        This statewide student voting platform is independently built and self-funded as a free public service for students and voters across all 110 North Carolina colleges and universities. If you find this guide helpful, your contribution helps cover server hosting, domain fees, and continuous data updates!
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
        <!-- Venmo Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-blue-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#008CFF] text-white font-bold flex items-center justify-center text-xs">V</span>
            <span class="font-bold text-white text-sm">Venmo</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-blue-500/30 shadow-md my-1">
            <img src="/venmo_qr.png" alt="Venmo QR Code @Ran-Baron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-blue-400 mt-2 select-all">@Ran-Baron</div>
          <a href="https://account.venmo.com/u/Ran-Baron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#008CFF] hover:bg-blue-600 text-white font-semibold text-xs text-center transition shadow-sm">
            Pay via Venmo ↗
          </a>
        </div>

        <!-- CashApp Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-emerald-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#00D632] text-black font-extrabold flex items-center justify-center text-xs">$</span>
            <span class="font-bold text-white text-sm">Cash App</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-emerald-500/30 shadow-md my-1">
            <img src="/cashapp_qr.png" alt="Cash App QR Code $RanBaron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-emerald-400 mt-2 select-all">$RanBaron</div>
          <a href="https://cash.app/$RanBaron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#00D632] hover:bg-emerald-500 text-black font-bold text-xs text-center transition shadow-sm">
            Pay via Cash App ↗
          </a>
        </div>
      </div>

      <div class="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-500 text-center">
        Thank you for supporting non-partisan student voting access in North Carolina!
      </div>
    </div>
  </div>

  <script>
    const campuses = %%CARDS_JSON%%;
    let currentFilter = 'ALL';
    let userLocation = null;

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

    function renderCampuses(list) {
      const grid = document.getElementById('campus-grid');
      grid.innerHTML = '';
      if (list.length === 0) {
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400 text-sm">No colleges or universities matched your search. Try another query or clear filters!</div>';
        return;
      }

      list.forEach(c => {
        const distHtml = c.distance !== undefined ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">${c.distance} mi away</span>` : 
          `<span class="text-[11px] text-slate-500 font-mono">${c.city}</span>`;

        const idBadge = c.id_approved ? 
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Student ID Approved</span>` :
          `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Alt ID Required</span>`;

        const card = document.createElement('a');
        card.href = c.url;
        card.className = "bg-slate-900 border border-slate-800 hover:border-blue-500/60 rounded-2xl p-5 flex flex-col justify-between transition duration-200 hover:-translate-y-0.5 shadow-md group";
        card.innerHTML = `
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">${c.type}</span>
              ${distHtml}
            </div>
            <h3 class="text-base font-bold text-white group-hover:text-blue-300 transition leading-snug mb-1">${c.name}</h3>
            <p class="text-xs text-slate-400 mb-3">${c.city}, NC • ${c.county}</p>
          </div>
          <div class="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
            ${idBadge}
            <span class="text-blue-400 font-semibold group-hover:translate-x-1 transition duration-150">View Guide →</span>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    function filterCampuses() {
      const q = document.getElementById('campus-search').value.toLowerCase().trim();
      let filtered = campuses.filter(c => {
        const matchesQuery = !q || c.name.toLowerCase().includes(q) || c.city.toLowerCase().includes(q) || c.county.toLowerCase().includes(q) || c.short_name.toLowerCase().includes(q);
        let matchesType = true;
        if (currentFilter === 'UNC') matchesType = (c.type === 'UNC System');
        else if (currentFilter === 'CC') matchesType = c.type.includes('Community');
        else if (currentFilter === 'PRIVATE') matchesType = (c.type !== 'UNC System' && !c.type.includes('Community'));
        return matchesQuery && matchesType;
      });

      if (userLocation) {
        filtered = filtered.sort((a, b) => (a.distance || 9999) - (b.distance || 9999));
      }
      renderCampuses(filtered);
    }

    function setFilter(type) {
      currentFilter = type;
      document.querySelectorAll('.filter-badge').forEach(b => {
        b.className = "filter-badge px-3 py-1.5 rounded-lg bg-slate-900 text-slate-300 hover:text-white border border-slate-800 transition";
      });
      const activeBtn = document.getElementById(`filter-btn-${type}`);
      if (activeBtn) {
        activeBtn.className = "filter-badge px-3 py-1.5 rounded-lg bg-blue-600 text-white font-semibold border border-blue-500 transition";
      }
      filterCampuses();
    }

    function sortCampusesByLocation() {
      if (!navigator.geolocation) {
        alert("Geolocation is not supported by your browser.");
        return;
      }
      const status = document.getElementById('geo-sort-status');
      status.innerText = "Detecting your location to sort closest campuses...";

      navigator.geolocation.getCurrentPosition(
        pos => {
          userLocation = { lat: pos.coords.latitude, lon: pos.coords.longitude };
          sessionStorage.setItem('nc_user_lat', userLocation.lat);
          sessionStorage.setItem('nc_user_lon', userLocation.lon);

          campuses.forEach(c => {
            c.distance = haversine(userLocation.lat, userLocation.lon, c.lat, c.lon);
          });
          campuses.sort((a, b) => a.distance - b.distance);

          status.innerHTML = `Sorted by distance from your current location! Closest: <b>${campuses[0].name}</b> (${campuses[0].distance} miles)`;
          filterCampuses();
        },
        err => {
          status.innerText = "Location access was denied. You can still search manually by name or city!";
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }
      );
    }

    function openSupportModal() {
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.remove('hidden');
    }
    function closeSupportModal() {
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.add('hidden');
    }
    window.addEventListener('click', (e) => {
      const modal = document.getElementById('support-modal');
      if (e.target === modal) closeSupportModal();
    });
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeSupportModal();
    });

    window.addEventListener('DOMContentLoaded', () => {
      const savedLat = sessionStorage.getItem('nc_user_lat');
      const savedLon = sessionStorage.getItem('nc_user_lon');
      if (savedLat && savedLon) {
        userLocation = { lat: parseFloat(savedLat), lon: parseFloat(savedLon) };
        campuses.forEach(c => {
          c.distance = haversine(userLocation.lat, userLocation.lon, c.lat, c.lon);
        });
        campuses.sort((a, b) => a.distance - b.distance);
        document.getElementById('geo-sort-status').innerHTML = `Using previous location: Closest is <b>${campuses[0].name}</b> (${campuses[0].distance} miles)`;
      }
      renderCampuses(campuses);
    });
  </script>

  <script src="/tracker.js"></script>
</body>
</html>
'''

campuses_html = campuses_template.replace('%%CARDS_JSON%%', cards_json_str).replace('%%GITLAB_REPO_URL%%', GITLAB_REPO_URL).replace('%%GITLAB_ISSUES_URL%%', GITLAB_ISSUES_URL).replace('%%VERIFIED_UPDATE_TIME%%', VERIFIED_UPDATE_TIME)
with open(f"{MAIN_DIR}/campuses.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
os.makedirs(f"{MAIN_DIR}/campuses", exist_ok=True)
with open(f"{MAIN_DIR}/campuses/index.html", 'w', encoding='utf-8') as f:
    f.write(campuses_html)
if LOCAL_DIR:
    with open(f"{LOCAL_DIR}/campuses.html", 'w', encoding='utf-8') as f:
        f.write(campuses_html)

print("Master campuses.html updated with 110 campuses!")


# 5. Generate /vote.html
print("5. Generating dynamic Main QR Code Portal for /vote...")

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

vote_html = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Campus Voting Portal &amp; Dynamic QR Code | Rann Bar-On</title>
  <meta name="description" content="Dynamic NC student voting portal. Automatically generates the QR code and voting guide for your college or university using geolocation or zip code.">
  
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://rannbar-on.com/vote">
  <meta property="og:title" content="North Carolina Campus Voting Portal">
  <meta property="og:description" content="Dynamic QR code and voting guide for every college and university in North Carolina.">
  <meta property="og:image" content="https://rannbar-on.com/dukevote_qr.png">

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
<body class="min-h-screen flex flex-col justify-between bg-slate-950 text-slate-100 antialiased font-sans" data-campus="Dynamic QR Portal" data-key="vote">

  <!-- Top Announcement Bar -->
  <div id="top-announcement-bar" class="bg-gradient-to-r from-blue-950 via-indigo-950 to-slate-950 px-4 py-2 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-2">
      <span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
      <span>Early Voting is <b>OPEN STATEWIDE</b> through <b>Saturday, October 31, 2026</b></span>
    </span>
  </div>

  <!-- Header -->
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
        <a href="/campuses" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/30 transition">
          Browse All 110 Campuses
        </a>
      </div>
    </div>
  </header>

  <!-- Hero Section -->
  <main class="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-14 flex-1 flex flex-col items-center justify-center text-center">

    <!-- Verified Source Banner -->
    <div class="w-full max-w-xl mb-6 p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-left shadow-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
      <div class="flex items-center gap-2.5">
        <span class="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
          Verified Source
        </span>
        <span class="text-slate-200">
          Official North Carolina State Board of Elections (NCSBE)
        </span>
      </div>
      <div class="flex flex-wrap items-center gap-3 text-slate-400 text-[11px]">
        <span>Last Verified Update: <b class="text-slate-200 font-mono">{VERIFIED_UPDATE_TIME}</b></span>
        <span>•</span>
        <a href="https://vt.ncsbe.gov/OSSite/" target="_blank" rel="noopener" class="text-blue-400 hover:underline">NCSBE Portal ↗</a>
      </div>
    </div>

    <div id="qr-status-badge" class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/30 mb-4">
      <span>Dynamic Student Voting Portal</span>
    </div>

    <h1 class="text-3xl sm:text-4xl font-extrabold tracking-tight text-white mb-2 leading-tight">
      Scan or Find Your Campus Voting Guide
    </h1>
    <p class="text-sm text-slate-300 max-w-lg mb-8 leading-relaxed">
      This adaptive portal connects you directly to early voting polling locations, voter ID requirements, and candidate research guides across all 110 North Carolina institutions.
    </p>

    <!-- Main Dynamic QR Card -->
    <div id="qr-display-card" class="bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl max-w-md w-full mb-8 relative transition-all duration-300">
      
      <!-- Current Target Header -->
      <div class="mb-4">
        <span id="target-mode-pill" class="inline-block px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-blue-500/10 text-blue-400 border border-blue-500/20 mb-1">
          Default Campus
        </span>
        <h2 id="target-school-name" class="text-xl sm:text-2xl font-bold text-white">Duke University</h2>
        <p id="target-school-sub" class="text-xs text-slate-400 mt-0.5">Durham, NC • Durham County</p>
      </div>

      <!-- High-Resolution QR Box -->
      <div class="bg-white p-4 sm:p-5 rounded-2xl shadow-xl border-4 border-blue-500/30 inline-block my-2 transition duration-300">
        <img id="main-qr-img" src="data:image/png;base64,{duke_qr_b64}" alt="NC Campus Voting QR Code" class="w-52 h-52 sm:w-56 sm:h-56 object-contain mx-auto" />
      </div>

      <!-- URL Pill -->
      <div id="qr-guide-url" class="mt-3 inline-block font-mono text-xs font-semibold text-blue-300 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 select-all">
        rannbar-on.com/dukevote
      </div>

      <!-- Nearest Precinct Box (Election Day) -->
      <div id="card-precinct-box" class="hidden mt-4 p-3.5 rounded-xl bg-slate-950/80 border border-rose-500/40 text-left">
        <div class="flex items-center justify-between text-[11px] font-semibold text-rose-300 mb-1">
          <span>Nearest E-Day Precinct</span>
          <span id="card-precinct-dist" class="font-mono text-slate-400"></span>
        </div>
        <div id="card-precinct-name" class="text-sm font-bold text-white truncate"></div>
        <div id="card-precinct-id" class="text-[11px] text-slate-400 mb-2"></div>
        <div class="flex gap-2">
          <a id="card-precinct-maps" href="#" target="_blank" rel="noopener" class="flex-1 py-1.5 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs text-center transition">
            Directions ↗
          </a>
          <a href="https://vt.ncsbe.gov/pplkup/" target="_blank" rel="noopener" class="py-1.5 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-blue-300 text-xs font-semibold text-center transition">
            NCSBE Lookup ↗
          </a>
        </div>
      </div>

      <!-- Quick Action Buttons -->
      <div class="mt-5 space-y-2">
        <a id="qr-guide-btn" href="/dukevote?autoloc=1" class="w-full py-3 px-4 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs sm:text-sm transition shadow-lg flex items-center justify-center gap-2">
          <span>Open Duke Early Voting Guide</span>
          <span>→</span>
        </a>

        <div class="grid grid-cols-3 gap-2 text-xs">
          <button onclick="copyCurrentLink()" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition">
            Copy
          </button>
          <a id="qr-dl-png" href="/dukevote_qr.png" download="Duke_Vote_QR.png" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition">
            PNG
          </a>
          <a id="qr-dl-svg" href="/dukevote_qr.svg" download="Duke_Vote_QR.svg" class="py-2 px-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold transition">
            SVG
          </a>
        </div>
      </div>
    </div>

    <!-- Location / Zip Controls Container -->
    <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-5">
      
      <!-- Option 1: Geolocation -->
      <div>
        <label class="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">Option 1: Device Location (Fastest)</label>
        <button onclick="triggerGeolocation()" id="btn-geo" class="w-full py-2.5 px-4 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/40 text-blue-300 font-bold text-xs transition flex items-center justify-center gap-2">
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
                 class="w-full bg-slate-950 border border-slate-700 focus:border-blue-500 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none" />
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
        <select id="campus-select" onchange="handleSelectCampus(this.value)" class="w-full bg-slate-950 border border-slate-700 text-xs text-slate-200 rounded-xl px-3 py-2 focus:ring-2 focus:ring-blue-500 font-medium">
          <option value="">Choose an NC College/University...</option>
          {campus_options_html}
        </select>
      </div>

    </div>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-6 px-4 text-center text-xs text-slate-500">
    <div class="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
      <span>Non-partisan student voting guide portal prepared by Rann Bar-On under the <a href="{GITLAB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener" class="text-blue-400 hover:underline">MIT License</a>.</span>
      <div class="flex flex-wrap items-center justify-center gap-4">
        <a href="/campuses" class="text-blue-400 hover:underline">All 110 NC Campuses</a>
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
        <a href="{GITLAB_REPO_URL}" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Source</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="{GITLAB_ISSUES_URL}" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline flex items-center gap-1">
          <span>GitHub Issues</span>
          <span class="text-[10px]">↗</span>
        </a>
        <a href="{GITLAB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener" class="text-slate-400 hover:text-slate-200 hover:underline">MIT License</a>
        <a href="/stats" class="text-slate-400 hover:text-slate-200 hover:underline">Usage Tracker</a>
        <a href="#support-site" onclick="openSupportModal(); return false;" class="text-amber-400 hover:text-amber-300 hover:underline flex items-center gap-1 font-medium">
          <span>Help Rann Bar-On maintain this site</span>
        </a>
      </div>
    </div>
  </footer>

  <!-- Support Modal -->
  <div id="support-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm transition-opacity duration-200">
    <div class="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl text-center">
      <button onclick="closeSupportModal()" class="absolute top-4 right-4 text-slate-400 hover:text-white p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-sm transition" aria-label="Close">
        Close [X]
      </button>
      
      <div class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30 mb-3">
        <span>Independent &amp; Community Supported</span>
      </div>
      
      <h3 class="text-xl sm:text-2xl font-bold text-white mb-2">Help Rann Bar-On maintain this site</h3>
      <p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-md mx-auto mb-6">
        This statewide student voting platform is independently built and self-funded as a free public service for students and voters across all 110 North Carolina colleges and universities. If you find this guide helpful, your contribution helps cover server hosting, domain fees, and continuous data updates!
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
        <!-- Venmo Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-blue-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#008CFF] text-white font-bold flex items-center justify-center text-xs">V</span>
            <span class="font-bold text-white text-sm">Venmo</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-blue-500/30 shadow-md my-1">
            <img src="/venmo_qr.png" alt="Venmo QR Code @Ran-Baron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-blue-400 mt-2 select-all">@Ran-Baron</div>
          <a href="https://account.venmo.com/u/Ran-Baron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#008CFF] hover:bg-blue-600 text-white font-semibold text-xs text-center transition shadow-sm">
            Pay via Venmo ↗
          </a>
        </div>

        <!-- CashApp Card -->
        <div class="p-4 rounded-2xl bg-slate-950 border border-emerald-500/40 flex flex-col items-center text-center">
          <div class="flex items-center gap-2 mb-2">
            <span class="w-6 h-6 rounded-md bg-[#00D632] text-black font-extrabold flex items-center justify-center text-xs">$</span>
            <span class="font-bold text-white text-sm">Cash App</span>
          </div>
          <div class="bg-white p-2.5 rounded-xl border-2 border-emerald-500/30 shadow-md my-1">
            <img src="/cashapp_qr.png" alt="Cash App QR Code $RanBaron" class="w-32 h-32 object-contain" />
          </div>
          <div class="font-mono text-xs font-bold text-emerald-400 mt-2 select-all">$RanBaron</div>
          <a href="https://cash.app/$RanBaron" target="_blank" rel="noopener" class="mt-3 w-full py-2 px-3 rounded-xl bg-[#00D632] hover:bg-emerald-500 text-black font-bold text-xs text-center transition shadow-sm">
            Pay via Cash App ↗
          </a>
        </div>
      </div>

      <div class="mt-6 pt-4 border-t border-slate-800 text-[11px] text-slate-500 text-center">
        Thank you for supporting non-partisan student voting access in North Carolina!
      </div>
    </div>
  </div>

  <script>
    const allCampuses = {campus_geo_json_str};
    const qrB64Map = {qr_b64_map_json_str};
    const localZips = {local_zip_map_json_str};
    const campusPrimaryPrecincts = {campus_primary_precincts_json_str};
    let currentCampus = allCampuses.find(c => c.key === 'dukevote') || allCampuses[0];

    function haversine(lat1, lon1, lat2, lon2) {{
      const R = 3958.8;
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2);
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
      return Math.round(R * c * 10) / 10;
    }}

    function updateMainQR(campus, modeLabel, distanceText) {{
      currentCampus = campus;
      document.getElementById('target-mode-pill').innerText = modeLabel || 'Nearest Campus';
      document.getElementById('target-school-name').innerText = campus.name;
      document.getElementById('target-school-sub').innerText = `${{campus.city}}, NC • ${{campus.county}} ${{distanceText ? '• (' + distanceText + ')' : ''}}`;

      const b64 = qrB64Map[campus.key];
      const img = document.getElementById('main-qr-img');
      if (b64) {{
        img.src = `data:image/png;base64,${{b64}}`;
      }} else {{
        img.src = `/${{campus.key}}_qr.png`;
      }}

      document.getElementById('qr-guide-url').innerText = `rannbar-on.com/${{campus.key}}`;

      const btn = document.getElementById('qr-guide-btn');
      btn.href = `/${{campus.key}}?autoloc=1`;
      btn.innerHTML = `<span>Open ${{campus.short_name || campus.name}} Guide</span><span>→</span>`;

      const dlPng = document.getElementById('qr-dl-png');
      dlPng.href = `/${{campus.key}}_qr.png`;
      dlPng.download = `${{campus.short_name || campus.name}}_Vote_QR.png`;

      const dlSvg = document.getElementById('qr-dl-svg');
      dlSvg.href = `/${{campus.key}}_qr.svg`;
      dlSvg.download = `${{campus.short_name || campus.name}}_Vote_QR.svg`;

      // Update precinct box if election day
      const EARLY_VOTING_DEADLINE = new Date('2026-10-31T15:00:00-04:00');
      const urlParams = new URLSearchParams(window.location.search);
      const isElectionDay = (new Date() >= EARLY_VOTING_DEADLINE) || (urlParams.get('mode') === 'election_day');
      const precBox = document.getElementById('card-precinct-box');

      if (isElectionDay && precBox) {{
        const prec = campusPrimaryPrecincts[campus.key];
        if (prec) {{
          document.getElementById('card-precinct-name').innerText = prec.primary_name;
          document.getElementById('card-precinct-id').innerText = `Precinct ${{prec.primary_precinct}} • ${{campus.city}}, NC`;
          document.getElementById('card-precinct-dist').innerText = `~${{prec.dist_to_campus}} mi from campus`;
          document.getElementById('card-precinct-maps').href = `https://www.google.com/maps/dir/?api=1&destination=${{encodeURIComponent(prec.primary_name + ', ' + campus.county + ', NC')}}`;
          precBox.classList.remove('hidden');
        }}
      }}

      sessionStorage.setItem('nc_user_campus', campus.key);
    }}

    function triggerGeolocation() {{
      if (!navigator.geolocation) {{
        alert("Geolocation is not supported by your browser.");
        return;
      }}

      const status = document.getElementById('geo-status-text');
      status.className = 'text-[11px] text-blue-400 mt-1.5 min-h-[16px] text-center font-medium';
      status.innerText = 'Detecting your location...';

      navigator.geolocation.getCurrentPosition(
        pos => {{
          const uLat = pos.coords.latitude;
          const uLon = pos.coords.longitude;
          sessionStorage.setItem('nc_user_lat', uLat);
          sessionStorage.setItem('nc_user_lon', uLon);

          const sorted = [...allCampuses].map(c => ({{
            ...c,
            dist: haversine(uLat, uLon, c.lat, c.lon)
          }})).sort((a, b) => a.dist - b.dist);

          const closest = sorted[0];
          updateMainQR(closest, `Located via GPS: ${{closest.name}}`, `${{closest.dist}} mi away`);
          status.className = 'text-[11px] text-emerald-400 mt-1.5 min-h-[16px] text-center font-medium';
          status.innerHTML = `Found! Closest campus: <b>${{closest.name}}</b> (${{closest.dist}} miles away)`;
        }},
        err => {{
          status.className = 'text-[11px] text-amber-400 mt-1.5 min-h-[16px] text-center font-medium';
          status.innerText = "Location permission was denied. Try entering your zip code below!";
        }},
        {{ enableHighAccuracy: true, timeout: 8000, maximumAge: 60000 }}
      );
    }}

    async function handleZipSubmit(e) {{
      e.preventDefault();
      const zipInput = document.getElementById('zip-input');
      const zip = zipInput.value.trim();
      const status = document.getElementById('zip-status-text');

      if (!/^\\d{{5}}$/.test(zip)) {{
        status.className = 'text-[11px] text-amber-400 mt-1.5 min-h-[16px] text-center font-medium';
        status.innerText = "Please enter a valid 5-digit NC zip code.";
        return;
      }}

      status.className = 'text-[11px] text-blue-400 mt-1.5 min-h-[16px] text-center font-medium';
      status.innerText = 'Looking up zip code...';

      let coords = null;
      if (localZips[zip]) {{
        coords = localZips[zip];
      }} else {{
        try {{
          const res = await fetch(`https://api.zippopotam.us/us/${{zip}}`);
          if (res.ok) {{
            const data = await res.json();
            if (data.places && data.places.length > 0) {{
              coords = [parseFloat(data.places[0].latitude), parseFloat(data.places[0].longitude)];
            }}
          }}
        }} catch (err) {{
          console.warn("Zippopotam fetch failed:", err);
        }}
      }}

      if (coords) {{
        const [zLat, zLon] = coords;
        const sorted = [...allCampuses].map(c => ({{
          ...c,
          dist: haversine(zLat, zLon, c.lat, c.lon)
        }})).sort((a, b) => a.dist - b.dist);

        const closest = sorted[0];
        updateMainQR(closest, `Zip Code ${{zip}}: ${{closest.name}}`, `${{closest.dist}} mi away`);
        status.className = 'text-[11px] text-emerald-400 mt-1.5 min-h-[16px] text-center font-medium';
        status.innerHTML = `Zip ${{zip}} matched! Closest campus: <b>${{closest.name}}</b> (${{closest.dist}} miles away)`;
      }} else {{
        status.className = 'text-[11px] text-amber-400 mt-1.5 min-h-[16px] text-center font-medium';
        status.innerText = "Could not find coordinates for that zip code. Please select your school from Option 3!";
      }}
    }}

    function handleSelectCampus(key) {{
      if (!key) return;
      const cleanKey = key.replace('/', '');
      const campus = allCampuses.find(c => c.key === cleanKey);
      if (campus) {{
        updateMainQR(campus, `Selected: ${{campus.name}}`, campus.city);
        const status = document.getElementById('zip-status-text');
        status.className = 'text-[11px] text-emerald-400 mt-1.5 min-h-[16px] text-center font-medium';
        status.innerHTML = `Updated QR Code to <b>${{campus.name}}</b>`;
      }}
    }}

    function copyCurrentLink() {{
      const url = `https://rannbar-on.com/${{currentCampus.key}}`;
      navigator.clipboard.writeText(url);
      alert(`Copied link to ${{currentCampus.short_name || currentCampus.name}} Guide!`);
    }}

    function checkElectionDayMode() {{
      const EARLY_VOTING_DEADLINE = new Date('2026-10-31T15:00:00-04:00');
      const urlParams = new URLSearchParams(window.location.search);
      if (new Date() >= EARLY_VOTING_DEADLINE || urlParams.get('mode') === 'election_day') {{
        const topBar = document.getElementById('top-announcement-bar');
        if (topBar) {{
          topBar.className = 'bg-gradient-to-r from-red-950 via-rose-950 to-slate-950 px-4 py-2 text-center text-xs sm:text-sm font-bold text-slate-100 border-b border-rose-900/50 shadow-md';
          topBar.innerHTML = '<span>Early Voting Has Ended • <b>ELECTION DAY IS TUESDAY, NOVEMBER 3, 2026</b> • Polls Open <b>6:30 AM – 7:30 PM</b></span>';
        }}
        const badge = document.getElementById('qr-status-badge');
        if (badge) {{
          badge.innerHTML = '<span>Election Day Mode</span>';
          badge.className = 'inline-flex items-center px-3 py-1 rounded-full text-[11px] font-bold bg-rose-950/80 text-rose-300 border border-rose-700/60 mb-2';
        }}
      }}
    }}

    function openSupportModal() {{
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.remove('hidden');
    }}
    function closeSupportModal() {{
      const modal = document.getElementById('support-modal');
      if (modal) modal.classList.add('hidden');
    }}
    window.addEventListener('click', (e) => {{
      const modal = document.getElementById('support-modal');
      if (e.target === modal) closeSupportModal();
    }});
    window.addEventListener('keydown', (e) => {{
      if (e.key === 'Escape') closeSupportModal();
    }});

    window.addEventListener('DOMContentLoaded', () => {{
      checkElectionDayMode();
      const savedLat = sessionStorage.getItem('nc_user_lat');
      const savedLon = sessionStorage.getItem('nc_user_lon');
      if (savedLat && savedLon) {{
        const uLat = parseFloat(savedLat);
        const uLon = parseFloat(savedLon);
        const sorted = [...allCampuses].map(c => ({{
          ...c,
          dist: haversine(uLat, uLon, c.lat, c.lon)
        }})).sort((a, b) => a.dist - b.dist);

        const closest = sorted[0];
        updateMainQR(closest, `Saved Location: ${{closest.name}}`, `${{closest.dist}} mi away`);
        document.getElementById('geo-status-text').innerText = `Using previous location: ${{closest.name}} (${{closest.dist}} miles)`;
      }} else {{
        updateMainQR(currentCampus, 'Default Campus', null);
      }}
    }});
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

print("Dynamic /vote.html updated successfully!")
print("ALL DONE!")
