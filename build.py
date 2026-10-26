#!/usr/bin/env python3
"""
North Carolina Student Voting Platform - Unified Static Site Generator
Builds clean, lightweight, accessible voting guides for all 110 NC higher education institutions,
the master directory (/campuses), the QR landing page (/vote), and telemetry stats (/stats).
Supports both Early Voting mode and Election Day mode.
"""

import os
import sys
import re
import json
import urllib.parse
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOCAL_DIR = '/home/rann/Documents/math/teaching/105L/Fall26' if os.path.exists('/home/rann/Documents/math/teaching/105L/Fall26') else None

GITHUB_REPO_URL = "https://github.com/rannbaron/mainwebsite"
GITHUB_ISSUES_URL = "https://github.com/rannbaron/mainwebsite/issues"
CHECKED_DATE = "October 26, 2026"

# Check mode: Early Voting vs Election Day
is_eday = '--eday' in sys.argv or '--mode=eday' in sys.argv or '--mode=election_day' in sys.argv
if not is_eday:
    now = datetime.datetime.now()
    # Early voting for 2026 general election concludes Saturday, Oct 31, 2026 at 3:00 PM
    if now >= datetime.datetime(2026, 10, 31, 15, 0, 0):
        is_eday = True

mode_name = "Election Day" if is_eday else "Early Voting"
print(f"1. Loading campus and county voting data from data/ (Mode: {mode_name})...")

with open(os.path.join(DATA_DIR, 'campuses.json'), 'r', encoding='utf-8') as f:
    campuses = json.load(f)

with open(os.path.join(DATA_DIR, 'county_sites.json'), 'r', encoding='utf-8') as f:
    county_sites = json.load(f)

with open(os.path.join(DATA_DIR, 'county_boe.json'), 'r', encoding='utf-8') as f:
    boe_list = json.load(f)
boe_by_county = {c['Name'].upper(): c for c in boe_list}

with open(os.path.join(DATA_DIR, 'county_precincts.json'), 'r', encoding='utf-8') as f:
    county_precincts_map = json.load(f)

def format_title(text):
    if not text:
        return ""
    s = str(text).strip()
    if "NCCU" in s.upper():
        return "NCCU - Turner Law Building"
    if "LITTLE RIVER" in s.upper():
        return "Little River Community Complex"
    if s.upper() == "WESTERN CAROLINA UNIVERSITY" or "WESTERN CAROLINA UNIVERSITY" in s.upper():
        return "WCU - Health and Human Sciences Building (HHS)"
    
    minor = {'of', 'and', 'at', 'the', 'for', 'in', 'on', 'by', 'to'}
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
    res = re.sub(r'\bBoard Of Elections\b', 'Board of Elections', res, flags=re.I)
    res = re.sub(r'\bDurham,\s*Nc\b', 'Durham, NC', res, flags=re.I)
    res = re.sub(r'\bNc\b', 'NC', res)
    return res

def format_address(addr):
    if not addr:
        return ""
    addr = str(addr).strip()
    words = addr.split()
    out = []
    for w in words:
        w_clean = w.rstrip(',')
        has_comma = w.endswith(',')
        comma = ',' if has_comma else ''
        w_upper = w_clean.upper()
        if w_upper in {'NC', 'USA', 'US'}:
            out.append(w_upper + comma)
        elif re.match(r'^\d', w):
            out.append(w)
        elif w_upper in {'RD', 'ST', 'AVE', 'BLVD', 'DR', 'LN', 'HWY', 'PKWY', 'WAY', 'CT'}:
            out.append(w_upper.capitalize() + comma)
        else:
            out.append(w_upper.capitalize() + comma)
    return ' '.join(out)

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
    'NEW HANOVER': 'https://www.newhanoverdems.org/'
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
    'NEW HANOVER': 'https://www.newhanovergop.org/'
}

def parse_hours_table(hours_raw):
    if not hours_raw:
        return "<p>Hours not specified. Contact the county Board of Elections for details.</p>"
    
    rows = re.findall(r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', hours_raw, re.DOTALL | re.IGNORECASE)
    if not rows:
        return "<p>Hours not specified. Contact the county Board of Elections for details.</p>"
    
    html = "<table>\n  <thead>\n    <tr>\n      <th>Date</th>\n      <th>Hours</th>\n    </tr>\n  </thead>\n  <tbody>\n"
    for day, hrs in rows:
        d_clean = re.sub(r'<[^>]+>', '', day).strip()
        h_clean = re.sub(r'<[^>]+>', '', hrs).strip()
        html += f"    <tr>\n      <td>{d_clean}</td>\n      <td>{h_clean}</td>\n    </tr>\n"
    html += "  </tbody>\n</table>"
    return html

support_dialog_html = '''<dialog id="support-dialog">
  <h2 style="margin-top: 0; font-size: 18px;">Help maintain this site</h2>
  <p style="font-size: 14px;">This platform is maintained independently by Rann Bar-On as a free, open-source public service for North Carolina students. Contributions help cover hosting, domain renewal, and ongoing election verification.</p>
  <div class="support-qr-grid">
    <div class="support-qr-card">
      <img src="/venmo_qr.png" alt="Venmo QR Code">
      <div style="font-weight: 600; font-size: 14px;">Venmo</div>
      <div style="font-size: 13px;"><a href="https://venmo.com/Ran-Baron" target="_blank" rel="noopener">@Ran-Baron</a></div>
    </div>
    <div class="support-qr-card">
      <img src="/cashapp_qr.png" alt="Cash App QR Code">
      <div style="font-weight: 600; font-size: 14px;">Cash App</div>
      <div style="font-size: 13px;"><a href="https://cash.app/$RanBaron" target="_blank" rel="noopener">$RanBaron</a></div>
    </div>
  </div>
  <div style="text-align: right; margin-top: 16px;">
    <button type="button" class="btn btn-secondary" id="support-dialog-close">Close</button>
  </div>
</dialog>'''

footer_template = f'''    <footer>
      <div>Maintained by Rann Bar-On as an open-source public service under the <a href="{GITHUB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener">MIT License</a>.</div>
      <div class="footer-links">
        <a href="{GITHUB_REPO_URL}" target="_blank" rel="noopener">Source code on GitHub</a>
        <a href="{GITHUB_ISSUES_URL}" target="_blank" rel="noopener">Report an issue</a>
        <a href="{GITHUB_REPO_URL}/blob/main/LICENSE" target="_blank" rel="noopener">MIT License</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="#support-modal" id="support-link">Help maintain this site</a>
        <a href="/stats">Usage tracker</a>
      </div>
    </footer>
  </div>

{support_dialog_html}'''

sorted_campuses = sorted(campuses, key=lambda x: x['name'])
campus_options = []
for c in sorted_campuses:
    campus_options.append(f'<option value="/{c["key"]}">{c["name"]} ({c["city"]})</option>')
campus_options_html = '\n          '.join(campus_options)

print(f"2. Generating individual campus pages (Mode: {mode_name})...")

for inst in campuses:
    key = inst['key']
    cname = inst['county'].upper()
    c_display = format_title(cname) + " County"
    boe = boe_by_county.get(cname, {})
    boe_phone = boe.get('OfficePhoneNum', '(919) 814-0700')
    boe_addr = format_address(boe.get('FullAddress', f'{c_display} Board of Elections, NC'))
    boe_web = boe.get('WebsiteAddr', f'https://vt.ncsbe.gov/BOEInfo/?county={cname}')
    boe_name = format_title(boe.get('OfficeName', f'{c_display} Board of Elections'))

    dem_url = county_dem_urls.get(cname, 'https://www.ncdp.org/county-parties/')
    rep_url = county_rep_urls.get(cname, 'https://www.ncgop.org/county_parties')

    is_residential = inst.get('is_residential', True)
    is_private = inst.get('private_school_rule', False)
    clean_card = inst.get('clean_id_card_name', 'Student ID')

    # Candidate guides section (identical across modes)
    candidate_guides_html = f'''      <h2>Candidate guides</h2>
      <p>Candidate information from non-partisan and party sources:</p>
      <div class="guide-links">
        <div><strong>Non-partisan:</strong> <a href="https://www.vote411.org/north-carolina" target="_blank" rel="noopener">Vote411 (League of Women Voters)</a></div>
        <div><strong>Democratic:</strong> <a href="https://bluevoterguide.org/" target="_blank" rel="noopener">Blue Voter Guide (NC)</a> | <a href="{dem_url}" target="_blank" rel="noopener">{c_display} Democratic Party</a></div>
      </div>'''

    boe_section_html = f'''      <h2>{c_display} Board of Elections</h2>
      <p>
        Address: {boe_addr}<br>
        Phone: <a href="tel:{boe_phone}">{boe_phone}</a><br>
        Website: <a href="{boe_web}" target="_blank" rel="noopener">{boe_web}</a>
      </p>

      <div class="verification-note">
        Hours checked against the {c_display} Board of Elections on {CHECKED_DATE}. <a href="{boe_web}" target="_blank" rel="noopener">Source: {c_display} Board of Elections</a>.
      </div>'''

    if not is_eday:
        # =========================================================
        # EARLY VOTING MODE
        # =========================================================
        sites_in_county = county_sites.get(cname, [])
        hours_html = "<p>Hours not provided.</p>"
        if sites_in_county:
            hours_html = parse_hours_table(sites_in_county[0].get('CompleteHoursHTML', ''))

        has_on_campus = inst.get('has_on_campus_site', False)
        if has_on_campus:
            site_title_h2 = "On-campus early voting location"
            site_name = format_title(inst.get('site_name', ''))
            site_address = format_address(inst.get('site_address', ''))
            site_intro = ""
        else:
            site_title_h2 = "Nearest early voting location"
            site_name = format_title(inst.get('nearest_site_name', 'County Early Voting Site'))
            site_address = format_address(inst.get('nearest_site_address', ''))
            site_intro = f"<p>{inst['name']} does not host an on-campus early voting site. The closest early voting location in {c_display} is:</p>"

        site_entrance = inst.get('site_entrance', '')
        transit_shuttle = inst.get('transit_shuttle', '')

        entrance_html = f"<p style='margin: 6px 0 0; font-size: 14px;'><strong>Entrance:</strong> {site_entrance}</p>" if site_entrance else ""
        transit_html = f"<p style='margin: 4px 0 0; font-size: 14px;'><strong>Transit and shuttles:</strong> {transit_shuttle}</p>" if transit_shuttle else ""
        gmap_url = f"https://maps.google.com/?q={urllib.parse.quote(site_name + ' ' + site_address)}"

        # JSON representation for client-side nearest site distance calculation
        sites_json_list = []
        for s in sites_in_county:
            sites_json_list.append({
                'name': format_title(s.get('Name', '')),
                'address': format_address(s.get('SiteAddressComplete', '')),
                'lat': s.get('SiteCoordLat'),
                'lon': s.get('SiteCoordLong')
            })
        sites_json_str = json.dumps(sites_json_list)

        # Format sites list
        sites_list_parts = []
        for s in sites_in_county:
            s_title = format_title(s.get('Name', ''))
            s_addr = format_address(s.get('SiteAddressComplete', ''))
            s_map = f"https://maps.google.com/?q={urllib.parse.quote(s_title + ' ' + s_addr)}"
            sites_list_parts.append(f'''<div class="site-item">
  <div class="site-name">{s_title}</div>
  <div class="site-meta">{s_addr}</div>
  <p style="margin: 4px 0 0; font-size: 13px;"><a href="{s_map}" target="_blank" rel="noopener">Directions on Google Maps</a></p>
</div>''')
        county_sites_list_html = '\n'.join(sites_list_parts)

        # Voter ID section & single callout
        if inst['id_approved']:
            id_section_html = f'''<p>{inst['name']} student IDs are approved for voting. You can present your physical {clean_card}.</p>
<div class="callout callout-warning">
  <p><strong>Physical card required:</strong> Digital IDs on phones (Apple Wallet, Google Wallet, or photos) are not accepted under North Carolina law. You must present the physical plastic card.</p>
</div>
<p>Other acceptable photo IDs include: NC driver's license (unexpired or expired up to one year), U.S. passport, military or veteran ID, or a free voter photo ID card issued by your county board of elections.</p>'''
        else:
            id_section_html = f'''<div class="callout callout-warning">
  <p><strong>Photo ID required:</strong> {inst['name']} student IDs are not approved for voting under North Carolina law. You must present an approved alternative photo ID, such as an NC driver's license, U.S. passport, or free county voter photo ID card.</p>
</div>
<p>Acceptable photo IDs include: NC driver's license (unexpired or expired up to one year), U.S. passport, military or veteran ID, or a free voter photo ID card issued by {c_display} Board of Elections.</p>'''

        # Same-day registration section
        if is_residential and is_private:
            reg_section_html = f'''<p>If you missed the voter registration deadline, you can register and vote on the same day during early voting. Same-day registration is not available on Election Day.</p>
<p>To register during early voting, you must show proof of your residential address in {c_display}.</p>
<p><strong>On-campus students:</strong> {inst['name']} provides a student housing roster to the {c_display} Board of Elections. Under NCSBE Numbered Memo 2023-05, because this is a private institution, students relying on the campus housing roster as proof of residence <strong>must present their physical {clean_card}</strong>. An out-of-state driver's license or passport cannot be paired with a private-school housing roster. Under state rules, the housing roster is only valid if it lists residents separated by individual residential facility or dormitory.</p>
<p><strong>Off-campus students:</strong> You can show an NC driver's license, utility bill, bank statement, paycheck, or government document showing your name and current address in {c_display}.</p>'''
        elif is_residential and not is_private:
            reg_section_html = f'''<p>If you missed the voter registration deadline, you can register and vote on the same day during early voting. Same-day registration is not available on Election Day.</p>
<p>To register during early voting, you must show proof of your residential address in {c_display}.</p>
<p><strong>On-campus students:</strong> {inst['name']} provides an official student housing roster to the {c_display} Board of Elections. You can verify your on-campus residential address with the campus roster paired with your student ID or any approved photo ID.</p>
<p><strong>Off-campus students:</strong> You can show an NC driver's license, utility bill, bank statement, paycheck, or government document showing your name and current address in {c_display}.</p>'''
        else:
            reg_section_html = f'''<p>If you missed the voter registration deadline, you can register and vote on the same day during early voting. Same-day registration is not available on Election Day.</p>
<p>To register during early voting, you must provide proof of your residential address in {c_display}: an NC driver's license, utility bill, bank statement, paycheck, or government document showing your current address.</p>'''

        page_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst['name']} Student Voting Guide | Rann Bar-On</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body data-campus="{inst['name']}" data-key="{key}">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>{inst['name']} student early voting guide</h1>
      <p>{inst['city']}, NC | {c_display}</p>

      <div class="campus-select-wrapper">
        <label for="campus-select">Switch campus:</label><br>
        <select id="campus-select">
          <option value="">Select a North Carolina college or university...</option>
          {campus_options_html}
        </select>
      </div>

      <h2>Early voting hours</h2>
      <p>Early voting runs from Thursday, October 15 through Saturday, October 31, 2026. Any registered voter in {c_display} can vote at any early voting site in the county.</p>
      {hours_html}

      <h2>{site_title_h2}</h2>
      {site_intro}
      <div class="site-item">
        <div class="site-name">{site_name}</div>
        <div class="site-meta">{site_address}</div>
        {entrance_html}
        {transit_html}
        <p style="margin: 8px 0 0; font-size: 14px;"><a href="{gmap_url}" target="_blank" rel="noopener">Get directions on Google Maps</a></p>
      </div>

      <h2>Voter ID</h2>
      {id_section_html}

      <h2>Same-day registration</h2>
      {reg_section_html}

      <h2>Voting locations in {c_display}</h2>
      <p>You can vote at any of these early voting locations in {c_display}:</p>
      <button type="button" class="btn btn-secondary" id="find-nearest-btn" style="margin-bottom: 12px;">Find nearest voting site</button>
      <div id="nearest-result" style="font-size: 14px; margin-bottom: 16px;"></div>
      {county_sites_list_html}

{candidate_guides_html}

{boe_section_html}
    </main>

{footer_template}

  <script>
    window.NC_SITES_DATA = {sites_json_str};
  </script>
  <script src="/voting.js"></script>
  <script src="/tracker.js"></script>
</body>
</html>'''

    else:
        # =========================================================
        # ELECTION DAY MODE
        # =========================================================
        precinct_info = inst.get('primary_precinct_name', 'Campus Precinct')
        precinct_id = inst.get('primary_precinct', '')
        precinct_dist = inst.get('dist_to_precinct', 0.5)
        precinct_lat = inst.get('primary_precinct_lat')
        precinct_lon = inst.get('primary_precinct_lon')

        county_precincts = county_precincts_map.get(cname, [])
        precincts_json_list = []
        precincts_list_parts = []

        for p in county_precincts:
            p_name = format_title(p.get('name', 'Precinct Polling Place'))
            p_addr = format_address(p.get('address', ''))
            p_code = p.get('code', '')
            p_lat = p.get('lat')
            p_lon = p.get('lon')
            gmap = f"https://maps.google.com/?q={urllib.parse.quote(p_name + ' ' + p_addr)}"

            precincts_json_list.append({
                'name': p_name,
                'address': p_addr,
                'code': p_code,
                'lat': p_lat,
                'lon': p_lon
            })

            precincts_list_parts.append(f'''<div class="site-item">
  <div class="site-name">Precinct {p_code}: {p_name}</div>
  <div class="site-meta">{p_addr}</div>
  <p style="margin: 4px 0 0; font-size: 13px;"><a href="{gmap}" target="_blank" rel="noopener">Directions on Google Maps</a></p>
</div>''')

        precincts_json_str = json.dumps(precincts_json_list)
        county_precincts_list_html = '\n'.join(precincts_list_parts) if precincts_list_parts else f"<p>Precinct polling locations are provided by the {c_display} Board of Elections.</p>"

        primary_map_url = f"https://maps.google.com/?q={urllib.parse.quote(precinct_info + ' ' + c_display + ' NC')}"

        if inst['id_approved']:
            id_section_html = f'''<p>{inst['name']} student IDs are approved for voting. You can present your physical {clean_card}.</p>
<div class="callout callout-warning">
  <p><strong>Physical card required:</strong> Digital IDs on phones (Apple Wallet, Google Wallet, or photos) are not accepted under North Carolina law. You must present the physical plastic card.</p>
</div>
<p>Other acceptable photo IDs include: NC driver's license (unexpired or expired up to one year), U.S. passport, military or veteran ID, or a free voter photo ID card issued by your county board of elections.</p>'''
        else:
            id_section_html = f'''<div class="callout callout-warning">
  <p><strong>Photo ID required:</strong> {inst['name']} student IDs are not approved for voting under North Carolina law. You must present an approved alternative photo ID, such as an NC driver's license, U.S. passport, or free county voter photo ID card.</p>
</div>
<p>Acceptable photo IDs include: NC driver's license (unexpired or expired up to one year), U.S. passport, military or veteran ID, or a free voter photo ID card issued by {c_display} Board of Elections.</p>'''

        page_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{inst['name']} Student Election Day Guide | Rann Bar-On</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body data-campus="{inst['name']}" data-key="{key}">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>{inst['name']} student Election Day voting guide</h1>
      <p>{inst['city']}, NC | {c_display}</p>

      <div class="campus-select-wrapper">
        <label for="campus-select">Switch campus:</label><br>
        <select id="campus-select">
          <option value="">Select a North Carolina college or university...</option>
          {campus_options_html}
        </select>
      </div>

      <h2>Election Day hours and voting location</h2>
      <p>Election Day is Tuesday, November 3, 2026. Polling places across North Carolina are open from 6:30 a.m. to 7:30 p.m. Anyone in line by 7:30 p.m. has the legal right to vote.</p>
      <p>On Election Day, you must vote at your assigned precinct polling place based on your registered address.</p>

      <div class="site-item">
        <div class="site-name">Assigned polling place near campus: Precinct {precinct_id} &ndash; {format_title(precinct_info)}</div>
        <p style="margin: 4px 0 0; font-size: 14px;">Located approximately {precinct_dist} miles from campus.</p>
        <p style="margin: 6px 0 0; font-size: 14px;"><a href="{primary_map_url}" target="_blank" rel="noopener">Directions on Google Maps</a></p>
      </div>

      <div style="margin: 16px 0; display: flex; flex-wrap: wrap; gap: 10px;">
        <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="btn">Find my assigned polling place on NCSBE</a>
        <button type="button" class="btn btn-secondary" id="find-nearest-btn">Find nearest precinct to my location</button>
      </div>
      <div id="nearest-result" style="font-size: 14px; margin-bottom: 16px;"></div>

      <h2>Voter ID</h2>
      {id_section_html}

      <h2>Voter registration</h2>
      <p><strong>Registration deadline passed:</strong> Same-day voter registration is not permitted on Election Day under North Carolina law. You must already be registered to vote today.</p>
      <p>If you believe you are registered or if your eligibility is in question, you have the right to request and cast a provisional ballot at the polling place.</p>

      <h2>All Election Day precincts in {c_display}</h2>
      <p>Search or browse all voting precincts in {c_display}:</p>
      {county_precincts_list_html}

{candidate_guides_html}

{boe_section_html}
    </main>

{footer_template}

  <script>
    window.NC_SITES_DATA = {precincts_json_str};
  </script>
  <script src="/voting.js"></script>
  <script src="/tracker.js"></script>
</body>
</html>'''

    file_path = os.path.join(BASE_DIR, f"{key}.html")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(page_content)
    sub_dir = os.path.join(BASE_DIR, key)
    if os.path.isdir(sub_dir):
        with open(os.path.join(sub_dir, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page_content)
    if LOCAL_DIR:
        with open(os.path.join(LOCAL_DIR, f"{key}.html"), 'w', encoding='utf-8') as f:
            f.write(page_content)
        local_sub = os.path.join(LOCAL_DIR, key)
        if os.path.isdir(local_sub):
            with open(os.path.join(local_sub, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(page_content)

print(f"Generated 110 campus guides (Mode: {mode_name}).")

# =========================================================
# MASTER DIRECTORY: campuses.html
# =========================================================
print("3. Generating master directory (campuses.html)...")

directory_cards = []
for inst in sorted_campuses:
    c_display = format_title(inst['county']) + " County"
    type_badge = inst['type']
    id_note = "Student ID approved" if inst['id_approved'] else "Alternative ID required"
    directory_cards.append(f'''<a href="/{inst['key']}" class="directory-item">
  <div class="directory-name">{inst['name']}</div>
  <div class="directory-meta">{inst['city']}, NC | {c_display}</div>
  <div class="directory-meta">{type_badge} | {id_note}</div>
</a>''')
directory_cards_html = '\n'.join(directory_cards)

campuses_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina College & University Voting Directory | Rann Bar-On</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body data-campus="Statewide Directory" data-key="campuses">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>North Carolina student voting directory</h1>
      <p>Select your college or university to access campus-specific early voting sites, polling hours, student photo ID validity, and Board of Elections details across all 110 institutions in North Carolina.</p>

      <div style="margin: 20px 0;">
        <label for="directory-search" style="font-weight: 600;">Search institutions:</label><br>
        <input type="text" id="directory-search" placeholder="Type campus name, city, or county..." style="width: 100%; max-width: 420px; margin-top: 6px;">
        <div id="directory-count" style="font-size: 13px; color: var(--text-muted); margin-top: 6px;">Showing 110 of 110 institutions</div>
      </div>

      <div class="card-grid">
        {directory_cards_html}
      </div>

      <div class="verification-note">
        Institutional status, county jurisdictions, and photo ID rules verified against North Carolina State Board of Elections records on {CHECKED_DATE}.
      </div>
    </main>

{footer_template}

  <script src="/voting.js"></script>
  <script src="/tracker.js"></script>
</body>
</html>'''

with open(os.path.join(BASE_DIR, 'campuses.html'), 'w', encoding='utf-8') as f:
    f.write(campuses_html)
if os.path.isdir(os.path.join(BASE_DIR, 'campuses')):
    with open(os.path.join(BASE_DIR, 'campuses', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(campuses_html)
if LOCAL_DIR:
    with open(os.path.join(LOCAL_DIR, 'campuses.html'), 'w', encoding='utf-8') as f:
        f.write(campuses_html)
    if os.path.isdir(os.path.join(LOCAL_DIR, 'campuses')):
        with open(os.path.join(LOCAL_DIR, 'campuses', 'index.html'), 'w', encoding='utf-8') as f:
            f.write(campuses_html)
print("Generated campuses.html successfully.")

# =========================================================
# QR PORTAL: vote.html
# =========================================================
print("4. Generating QR portal (/vote)...")

vote_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>North Carolina Student Voting Portal | rannbar-on.com/vote</title>
  <link rel="stylesheet" href="/style.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
</head>
<body data-campus="Main Portal" data-key="vote">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>Student voting portal</h1>
      <p>Scan or select your college or university to access your campus voting guide, polling hours, acceptable photo IDs, and voting locations.</p>

      <div style="margin: 24px 0; text-align: left;">
        <div style="background: #ffffff; padding: 16px; border: 1px solid var(--border); border-radius: 4px; display: inline-block;">
          <div id="qrcode-box"></div>
        </div>
        <p id="qr-target-text" style="font-size: 13px; font-family: var(--font-mono); color: var(--text-muted); margin-top: 8px;">Target: https://rannbar-on.com/dukevote</p>
      </div>

      <h2>Select your campus</h2>
      <div class="campus-select-wrapper">
        <label for="campus-picker">Choose from 110 North Carolina institutions:</label><br>
        <select id="campus-picker" style="margin-top: 6px;">
          <option value="">Select your college or university...</option>
          {campus_options_html}
        </select>
      </div>

      <div style="margin: 20px 0;">
        <button type="button" class="btn btn-secondary" id="portal-geolocate-btn">Use my location to find closest campus</button>
        <div id="portal-geo-status" style="font-size: 14px; margin-top: 8px;"></div>
      </div>

      <div style="margin: 20px 0;">
        <label for="zip-input" style="font-weight: 600;">Or enter your NC ZIP code:</label><br>
        <div style="margin-top: 6px; display: flex; gap: 8px; max-width: 300px;">
          <input type="text" id="zip-input" placeholder="e.g. 27708" maxlength="5" pattern="[0-9]{5}" style="flex: 1;">
          <button type="button" class="btn btn-secondary" id="zip-btn">Lookup</button>
        </div>
        <div id="zip-status" style="font-size: 14px; margin-top: 6px;"></div>
      </div>

      <h2>Browse the full directory</h2>
      <p><a href="/campuses">View all 110 North Carolina college and university guides</a></p>

      <div class="verification-note">
        Official voting dates, hours, and photo ID rules checked against North Carolina State Board of Elections records on {CHECKED_DATE}.
      </div>
    </main>

{footer_template}

  <script>
    window.CAMPUS_LIST = {json.dumps(campuses)};
  </script>
  <script src="/voting.js"></script>
  <script src="/tracker.js"></script>
</body>
</html>'''

with open(os.path.join(BASE_DIR, 'vote.html'), 'w', encoding='utf-8') as f:
    f.write(vote_html)
if os.path.isdir(os.path.join(BASE_DIR, 'vote')):
    with open(os.path.join(BASE_DIR, 'vote', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(vote_html)
if LOCAL_DIR:
    with open(os.path.join(LOCAL_DIR, 'vote.html'), 'w', encoding='utf-8') as f:
        f.write(vote_html)
    if os.path.isdir(os.path.join(LOCAL_DIR, 'vote')):
        with open(os.path.join(LOCAL_DIR, 'vote', 'index.html'), 'w', encoding='utf-8') as f:
            f.write(vote_html)
print("Generated vote.html successfully.")

# =========================================================
# TELEMETRY: stats.html
# =========================================================
print("5. Generating clean stats page (stats.html)...")

table_rows = []
for inst in sorted_campuses:
    c_display = format_title(inst['county']) + " County"
    table_rows.append(f'''    <tr>
      <td><a href="/{inst['key']}">{inst['name']}</a></td>
      <td>/{inst['key']}</td>
      <td>{inst['city']}, NC</td>
      <td>{c_display}</td>
    </tr>''')
table_rows_html = '\n'.join(table_rows)

stats_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Usage Analytics | North Carolina Student Voting</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body data-campus="Usage Analytics" data-key="stats">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>Visitor analytics and telemetry</h1>
      <p>Usage across all 110 North Carolina higher education campus voting guides is tracked using privacy-preserving, cookie-free telemetry hosted via GoatCounter.</p>

      <h2>Live analytics dashboard</h2>
      <p>Aggregated visitor counts, daily trends, referring domains, and per-campus breakdown can be viewed directly on the public GoatCounter dashboard:</p>
      <p><a href="https://rannbaron.goatcounter.com" target="_blank" rel="noopener" class="btn">View GoatCounter analytics dashboard</a></p>

      <h2>Tracked institutions</h2>
      <p>Every campus voting guide includes lightweight logging tracking visitor engagement by path:</p>

      <table>
        <thead>
          <tr>
            <th>Institution</th>
            <th>Path</th>
            <th>City</th>
            <th>County</th>
          </tr>
        </thead>
        <tbody>
{table_rows_html}
        </tbody>
      </table>

      <div class="verification-note">
        GoatCounter telemetry does not store personal data, track users across sites, or set tracking cookies.
      </div>
    </main>

{footer_template}

  <script src="/voting.js"></script>
</body>
</html>'''

with open(os.path.join(BASE_DIR, 'stats.html'), 'w', encoding='utf-8') as f:
    f.write(stats_html)
if os.path.isdir(os.path.join(BASE_DIR, 'stats')):
    with open(os.path.join(BASE_DIR, 'stats', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(stats_html)
if LOCAL_DIR:
    with open(os.path.join(LOCAL_DIR, 'stats.html'), 'w', encoding='utf-8') as f:
        f.write(stats_html)
    if os.path.isdir(os.path.join(LOCAL_DIR, 'stats')):
        with open(os.path.join(LOCAL_DIR, 'stats', 'index.html'), 'w', encoding='utf-8') as f:
            f.write(stats_html)
print("Generated stats.html successfully.")

# =========================================================
# STANDREWS REDIRECT PAGE
# =========================================================
standrews_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="5; url=/campuses">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>St. Andrews University Voting Information | Rann Bar-On</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body data-campus="St. Andrews University" data-key="standrewsvote">
  <div class="container">
    <header>
      <div class="nav-links">
        <a href="/campuses" class="site-title">North Carolina Student Voting</a>
        <a href="/campuses">All 110 campuses</a>
        <a href="/vote">Main QR portal</a>
        <a href="/stats">Usage stats</a>
      </div>
    </header>

    <main>
      <h1>St. Andrews University</h1>
      <p>Laurinburg, NC | Scotland County</p>

      <div class="callout callout-warning">
        <p><strong>Campus closed:</strong> St. Andrews University ceased academic operations on May 5, 2025 following revocation of accreditation by SACSCOC. It is not an active polling precinct or higher education institution for the 2026 election cycle.</p>
      </div>

      <p>If you are a resident of Scotland County, you can find your voter registration details, voting precinct, and photo ID requirements through the Scotland County Board of Elections:</p>
      <p>
        Scotland County Board of Elections<br>
        231 E. Cronly Street, Suite L, Laurinburg, NC 28352<br>
        Phone: <a href="tel:910-277-2595">910-277-2595</a><br>
        Website: <a href="https://www.scotlandcounty.org/218/Board-of-Elections" target="_blank" rel="noopener">https://www.scotlandcounty.org/218/Board-of-Elections</a>
      </p>

      <p><a href="/campuses">Go to the active 110 North Carolina campus voting directory</a></p>
    </main>

{footer_template}

  <script src="/voting.js"></script>
  <script src="/tracker.js"></script>
</body>
</html>'''

with open(os.path.join(BASE_DIR, 'standrewsvote.html'), 'w', encoding='utf-8') as f:
    f.write(standrews_html)
if os.path.isdir(os.path.join(BASE_DIR, 'standrewsvote')):
    with open(os.path.join(BASE_DIR, 'standrewsvote', 'index.html'), 'w', encoding='utf-8') as f:
        f.write(standrews_html)
if LOCAL_DIR:
    with open(os.path.join(LOCAL_DIR, 'standrewsvote.html'), 'w', encoding='utf-8') as f:
        f.write(standrews_html)
    if os.path.isdir(os.path.join(LOCAL_DIR, 'standrewsvote')):
        with open(os.path.join(LOCAL_DIR, 'standrewsvote', 'index.html'), 'w', encoding='utf-8') as f:
            f.write(standrews_html)
print("Generated standrewsvote.html redirect.")

print("ALL DONE! Clean build completed successfully.")
