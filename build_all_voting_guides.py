#!/usr/bin/env python3
import os
import base64

MAIN_DIR = '/home/rann/src/website/mainwebsite'
LOCAL_DIR = '/home/rann/src/website/voting-info'

def get_b64(path):
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

universities = [
    {
        'key': 'dukevote',
        'url': 'https://rannbar-on.com/dukevote',
        'school_name': 'Duke University',
        'short_name': 'Duke',
        'mascot': 'Blue Devils',
        'badge_icon': '🔵',
        'county': 'Durham County',
        'primary_site_name': 'Karsh Alumni and Visitors Center',
        'primary_site_address': '2080 Duke University Road<br/>Durham, NC 27708',
        'primary_site_desc': 'Located at the corner of Duke University Rd & Chapel Dr. Just a 5-minute walk from West Campus (Bryan Center / Abele Quad).',
        'primary_site_transit': '<b>Free Voter Parking:</b> Available in designated lot<br/><b>Duke Transit:</b> Accessible via C1 & campus shuttles',
        'map_query': 'Karsh+Alumni+and+Visitors+Center+Duke',
        'student_id_name': 'Physical DukeCard',
        'id_warning_details': 'Under North Carolina law, voters must present an approved photo identification. <b>Duke University\'s physical plastic DukeCard and Duke Student Voter ID Card are officially approved.</b> Mobile DukeCards in Apple Wallet or Google Wallet are NOT ACCEPTED under NC law. Free physical voter IDs are available from the DukeCard office.',
        'hours_weekday': '8:00 AM – 7:30 PM',
        'hours_saturday': '8:00 AM – 3:00 PM',
        'hours_sunday': '2:00 PM – 6:00 PM',
        'hours_final_sat': '8:00 AM – 3:00 PM',
        'on_campus_reg_note': 'Duke Housing provides an official on-campus student residential roster directly to Durham County election officials. Your physical DukeCard serves as both photo ID and proof of residence.',
        'support_org': 'Duke Votes (Student Initiative)',
        'support_contact': 'Non-partisan student voter support: <a href="mailto:dukevotes@duke.edu" class="text-blue-400 underline">dukevotes@duke.edu</a> | <a href="https://sites.duke.edu/dukevotes/" target="_blank" class="text-blue-400 underline">sites.duke.edu/dukevotes</a>',
        'boe_name': 'Durham County Board of Elections',
        'boe_url': 'https://www.dcovotes.com',
        'boe_phone': '(919) 560-0700',
        'accent_border': 'border-blue-500',
        'btn_color': 'bg-blue-600 hover:bg-blue-500',
        'tag_color': 'text-blue-400 bg-blue-500/10 border-blue-500/20',
        'hero_gradient': 'from-blue-900 via-indigo-950 to-slate-950',
        'all_sites': [
            ('Karsh Alumni Center (Duke Campus)', '2080 Duke University Rd, Durham 27708', 'Closest to West Campus & Bryan Ctr', True),
            ('Durham County Main Library', '300 N. Roxboro St, Durham 27701', 'Downtown Durham (Near East Campus)', False),
            ('NCCU - Turner Law Building', '640 Nelson St, Durham 27707', 'NCCU Campus', False),
            ('Durham County Board of Elections', '3825 S. Roxboro St, Durham 27713', 'Free voter IDs printed on-site', False),
            ('South Regional Library', '4505 S. Alston Ave, Durham 27713', 'South Durham / RTP', False),
            ('North Regional Library', '221 Milton Rd, Durham 27712', 'North Durham', False),
            ('East Regional Library', '211 Lick Creek Ln, Durham 27703', 'East Durham', False),
            ('Eno River UU Fellowship', '4907 Garrett Rd, Durham 27707', 'Southwest Durham', False),
            ('Southern High School', '800 Clayton Rd, Durham 27703', 'Southeast Durham', False),
            ('Little River Community Complex', '8307 N. Roxboro St, Bahama 27503', 'Northern Durham County', False)
        ]
    },
    {
        'key': 'uncvote',
        'url': 'https://rannbar-on.com/uncvote',
        'school_name': 'UNC-Chapel Hill',
        'short_name': 'UNC-CH',
        'mascot': 'Tar Heels',
        'badge_icon': '🩵',
        'county': 'Orange County',
        'primary_site_name': 'Chapel of the Cross (Franklin St)',
        'primary_site_address': '304 E. Franklin St<br/>Chapel Hill, NC 27514',
        'primary_site_desc': 'Located directly adjacent to Morehead Planetarium & Science Center on Franklin St. Just steps away from McCorkle Place, Spencer, Cobb, and North Campus residence halls.',
        'primary_site_transit': '<b>Free Chapel Hill Transit:</b> All local buses are fare-free! (Routes CW, CL, D, F, G, S, U, V)<br/><b>Walkable:</b> Central location right on the north edge of campus',
        'map_query': 'Chapel+of+the+Cross+Chapel+Hill+NC',
        'student_id_name': 'Physical UNC One Card',
        'id_warning_details': '<b>CRITICAL COURT RULING:</b> The NC Court of Appeals issued an injunction prohibiting the use of mobile/digital UNC One Cards for voting. <b>You MUST bring a PHYSICAL, plastic photo ID</b> (physical UNC One Card, NC driver\'s license, or US passport). If you only have a mobile card, visit the UNC One Card Office in the Student Union to obtain a physical card.',
        'hours_weekday': '8:00 AM – 7:30 PM',
        'hours_saturday': '8:00 AM – 3:00 PM',
        'hours_sunday': '12:00 PM – 4:00 PM',
        'hours_final_sat': '8:00 AM – 3:00 PM',
        'on_campus_reg_note': 'On-campus UNC students can use their physical UNC One Card and campus housing proof (viewable on the ConnectCarolina portal or housing assignment letter).',
        'support_org': 'UNC Votes & Carolina Center for Public Service',
        'support_contact': 'Student voting support: <a href="mailto:uncvotes@unc.edu" class="text-sky-400 underline">uncvotes@unc.edu</a> | <a href="https://ccps.unc.edu/" target="_blank" class="text-sky-400 underline">ccps.unc.edu</a>',
        'boe_name': 'Orange County Board of Elections',
        'boe_url': 'https://www.orangecountync.gov/elections',
        'boe_phone': '(919) 245-2350',
        'accent_border': 'border-sky-400',
        'btn_color': 'bg-sky-600 hover:bg-sky-500',
        'tag_color': 'text-sky-400 bg-sky-500/10 border-sky-500/20',
        'hero_gradient': 'from-sky-950 via-slate-900 to-slate-950',
        'all_sites': [
            ('Chapel of the Cross (Campus Site)', '304 E. Franklin St, Chapel Hill 27514', 'Adjacent to Morehead Planetarium', True),
            ('Seymour Center', '2551 Homestead Rd, Chapel Hill 27516', 'North Chapel Hill', False),
            ('Carrboro Town Hall Complex', '108 Bim St, Carrboro 27510', 'Downtown Carrboro', False),
            ('Orange County Board of Elections', '208 S. Cameron St, Hillsborough 27278', 'Hillsborough Main Office', False),
            ('Efland Ruritan Club', '3009 Forrest Ave, Efland 27243', 'Western Orange County', False)
        ]
    },
    {
        'key': 'nccuvote',
        'url': 'https://rannbar-on.com/nccuvote',
        'school_name': 'North Carolina Central University',
        'short_name': 'NCCU',
        'mascot': 'Eagles',
        'badge_icon': '🦅',
        'county': 'Durham County',
        'primary_site_name': 'NCCU School of Law (Turner Law Bldg)',
        'primary_site_address': '640 Nelson Street<br/>Durham, NC 27707',
        'primary_site_desc': 'Located directly on NCCU\'s campus at the Albert L. Turner Law Building. Centrally located and within easy walking distance from all NCCU residence halls, Greek housing, and student centers.',
        'primary_site_transit': '<b>Campus Access:</b> Walking distance from anywhere on campus<br/><b>Transit:</b> GoDurham bus lines serve Fayetteville St & Nelson St',
        'map_query': 'Albert+L+Turner+Law+Building+NCCU',
        'student_id_name': 'Physical NCCU Eagle Card',
        'id_warning_details': '<b>PHOTO ID MANDATORY:</b> Under North Carolina law, all voters must show an approved photo ID. The <b>NCCU Eagle Card is officially approved</b> by the NC State Board of Elections. You must present your physical plastic ID card (phone/mobile images are not accepted). NC Driver\'s License and US Passport are also accepted.',
        'hours_weekday': '8:00 AM – 7:30 PM',
        'hours_saturday': '8:00 AM – 3:00 PM',
        'hours_sunday': '2:00 PM – 6:00 PM',
        'hours_final_sat': '8:00 AM – 3:00 PM',
        'on_campus_reg_note': 'NCCU Residential Life provides residential verification to the Durham County Board of Elections. Your physical Eagle Card acts as valid photo ID and proof of enrollment.',
        'support_org': 'NCCU Civic Engagement & SGA',
        'support_contact': 'Campus voting initiatives: <a href="mailto:civicengagement@nccu.edu" class="text-rose-400 underline">civicengagement@nccu.edu</a> | <a href="https://www.nccu.edu/" target="_blank" class="text-rose-400 underline">nccu.edu</a>',
        'boe_name': 'Durham County Board of Elections',
        'boe_url': 'https://www.dcovotes.com',
        'boe_phone': '(919) 560-0700',
        'accent_border': 'border-rose-600',
        'btn_color': 'bg-rose-700 hover:bg-rose-600',
        'tag_color': 'text-rose-400 bg-rose-500/10 border-rose-500/20',
        'hero_gradient': 'from-rose-950 via-slate-900 to-slate-950',
        'all_sites': [
            ('NCCU - Turner Law Building', '640 Nelson St, Durham 27707', 'Directly on NCCU Campus', True),
            ('Karsh Alumni Center (Duke Campus)', '2080 Duke University Rd, Durham 27708', 'Duke West Campus', False),
            ('Durham County Main Library', '300 N. Roxboro St, Durham 27701', 'Downtown Durham', False),
            ('Durham County Board of Elections', '3825 S. Roxboro St, Durham 27713', 'Free voter IDs printed on-site', False),
            ('South Regional Library', '4505 S. Alston Ave, Durham 27713', 'South Durham / RTP', False),
            ('North Regional Library', '221 Milton Rd, Durham 27712', 'North Durham', False),
            ('East Regional Library', '211 Lick Creek Ln, Durham 27703', 'East Durham', False),
            ('Eno River UU Fellowship', '4907 Garrett Rd, Durham 27707', 'Southwest Durham', False),
            ('Southern High School', '800 Clayton Rd, Durham 27703', 'Southeast Durham', False),
            ('Little River Community Complex', '8307 N. Roxboro St, Bahama 27503', 'Northern Durham County', False)
        ]
    },
    {
        'key': 'ncsuvote',
        'url': 'https://rannbar-on.com/ncsuvote',
        'school_name': 'NC State University',
        'short_name': 'NC State',
        'mascot': 'Wolfpack',
        'badge_icon': '🐺',
        'county': 'Wake County',
        'primary_site_name': '1220 Varsity Drive (Campus Polling Site)',
        'primary_site_address': 'Western Boulevard Business Services<br/>1220 Varsity Dr, Raleigh, NC 27606',
        'primary_site_desc': 'Official NC State campus early voting site for Wake County. Located near the corner of Western Blvd & Varsity Dr.',
        'primary_site_transit': '<b>FREE Pack the Polls Shuttles:</b> Free continuous shuttles run between Talley Student Union (Reynolds Coliseum loop), Centennial Campus, and 1220 Varsity Drive!<br/><b>Voter Parking:</b> Free designated parking available on-site',
        'map_query': '1220+Varsity+Dr+Raleigh+NC',
        'student_id_name': 'Physical Wolfpack One Card',
        'id_warning_details': '<b>PHYSICAL PHOTO ID REQUIRED:</b> Under NC voting law, all voters must show an acceptable photo ID. The <b>NC State Wolfpack One Card is officially approved</b> by the State Board of Elections. You must present your physical plastic card (mobile/phone IDs are not accepted under NC law). NC Driver\'s License, state ID, or US Passport are also accepted.',
        'hours_weekday': '8:00 AM – 7:30 PM',
        'hours_saturday': '8:00 AM – 3:00 PM',
        'hours_sunday': '1:00 PM – 6:00 PM',
        'hours_final_sat': '8:00 AM – 3:00 PM',
        'on_campus_reg_note': 'On-campus NC State students can use their physical Wolfpack One Card along with NC State housing verification (accessible via MyPack Portal or housing agreement).',
        'support_org': 'Pack the Polls (NC State Civic Engagement)',
        'support_contact': 'Free shuttle info & student voter support: <a href="mailto:packthepolls@ncsu.edu" class="text-red-400 underline">packthepolls@ncsu.edu</a> | <a href="https://dasa.ncsu.edu/pack-the-polls/" target="_blank" class="text-red-400 underline">dasa.ncsu.edu/pack-the-polls</a>',
        'boe_name': 'Wake County Board of Elections',
        'boe_url': 'https://www.wake.gov/elections',
        'boe_phone': '(919) 404-4040',
        'accent_border': 'border-red-600',
        'btn_color': 'bg-red-700 hover:bg-red-600',
        'tag_color': 'text-red-400 bg-red-500/10 border-red-500/20',
        'hero_gradient': 'from-red-950 via-slate-900 to-slate-950',
        'all_sites': [
            ('1220 Varsity Dr (NC State Campus Site)', '1220 Varsity Dr, Raleigh 27606', 'Free shuttles from Talley / Reynolds', True),
            ('Chavis Community Center', '505 Martin Luther King Jr Blvd, Raleigh 27601', 'Near Downtown Raleigh', False),
            ('Wake BOE Operations Center', '1200 N. New Hope Rd, Raleigh 27610', 'East Raleigh', False),
            ('Optimist Park Community Center', '5900 Whittier Dr, Raleigh 27609', 'North Raleigh', False),
            ('Cary Senior Center', '120 Maury O\'Dell Pl, Cary 27519', 'Bond Park, Cary', False),
            ('Green Road Community Center', '4201 Green Rd, Raleigh 27604', 'Northeast Raleigh', False),
            ('Herbert C. Young Community Center', '101 Wilkinson Ave, Cary 27513', 'Downtown Cary', False),
            ('Garner Senior Center', '205 E. Garner Rd, Garner 27529', 'Garner', False),
            ('Wake Forest Town Hall', '301 S. Brooks St, Wake Forest 27587', 'Wake Forest', False)
        ]
    }
]

# Preload all QR codes in Base64
qr_b64_map = {u['key']: get_b64(f'{MAIN_DIR}/{u["key"]}_qr.png') for u in universities}

def render_switcher(active_key):
    items = []
    for u in universities:
        is_active = (u['key'] == active_key)
        cls = 'px-3 py-1.5 rounded-lg border font-semibold text-xs transition shadow-sm flex items-center gap-1.5 shrink-0 '
        if is_active:
            cls += 'bg-white text-slate-950 border-white font-bold'
        else:
            cls += 'bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-700 hover:text-white'
        items.append(f'<a href="/{u["key"]}" class="{cls}"><span>{u["badge_icon"]}</span><span>{u["short_name"]}</span></a>')
    return '\n'.join(items)

def render_all_sites_html(sites):
    cards = []
    for title, addr, note, is_highlight in sites:
        border_cls = 'border-2 border-blue-500/60' if is_highlight else 'border border-slate-800'
        badge = '<span class="absolute top-2 right-2 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-500 text-white">Campus Site</span>' if is_highlight else ''
        cards.append(f'''
        <div class="bg-slate-900 {border_cls} rounded-xl p-4 shadow-sm relative overflow-hidden">
          {badge}
          <h4 class="font-bold text-white text-base pr-20">{title}</h4>
          <p class="text-xs text-slate-300 mt-1">{addr}</p>
          <div class="text-[11px] text-emerald-400 mt-2 font-mono">{note}</div>
        </div>
        ''')
    return '\n'.join(cards)

def render_all_qr_cards(current_key):
    cards = []
    for u in universities:
        is_current = (u['key'] == current_key)
        b64_img = qr_b64_map[u['key']]
        
        if is_current:
            card_border = f"border-2 {u['accent_border']} ring-2 ring-blue-500/20 bg-slate-900 shadow-xl"
            badge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-white text-slate-950 shadow-sm">Current Page</span>'
        else:
            card_border = "border border-slate-800 bg-slate-900/70 hover:border-slate-700 hover:bg-slate-900/90"
            badge = f'<a href="/{u["key"]}" class="px-2 py-0.5 rounded text-[10px] font-semibold text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white transition">Visit Guide →</a>'

        cards.append(f'''
        <div class="rounded-2xl p-4 flex flex-col justify-between {card_border} transition">
          <div>
            <div class="flex items-center justify-between gap-1.5 mb-1.5">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="text-lg">{u['badge_icon']}</span>
                <span class="font-bold text-white text-sm truncate">{u['short_name']}</span>
              </div>
              {badge}
            </div>
            <div class="text-[11px] text-slate-400 mb-3 font-medium truncate">{u['county']}</div>

            <div class="bg-white p-3 rounded-xl shadow-md border border-slate-200/10 mb-3 flex items-center justify-center">
              <img src="data:image/png;base64,{b64_img}" alt="QR code for {u['school_name']} early voting guide" class="w-36 h-36 sm:w-40 sm:h-40 object-contain mx-auto" />
            </div>

            <div class="text-center font-mono text-[11px] text-slate-300 font-medium py-1.5 px-2 rounded-lg bg-slate-950/80 border border-slate-800/80 mb-3 select-all truncate">
              rannbar-on.com/{u['key']}
            </div>
          </div>

          <div class="space-y-1.5 pt-1">
            <button onclick="navigator.clipboard.writeText('{u['url']}'); alert('Copied {u['short_name']} voting guide link to clipboard!');" class="w-full py-2 px-3 rounded-xl {u['btn_color']} text-white font-semibold text-xs transition shadow-sm flex items-center justify-center gap-1.5">
              <span>📋</span>
              <span>Copy Link</span>
            </button>
            <div class="grid grid-cols-2 gap-1.5">
              <a href="/{u['key']}_qr.png" download="{u['short_name']}_Vote_QR.png" class="py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-[11px] text-center transition flex items-center justify-center gap-1">
                <span>📥</span><span>PNG</span>
              </a>
              <a href="/{u['key']}_qr.svg" download="{u['short_name']}_Vote_QR.svg" class="py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-[11px] text-center transition flex items-center justify-center gap-1">
                <span>📥</span><span>SVG</span>
              </a>
            </div>
          </div>
        </div>
        ''')
    return '\n'.join(cards)

for u in universities:
    key = u['key']
    switcher_html = render_switcher(key)
    sites_html = render_all_sites_html(u['all_sites'])
    all_qr_cards_html = render_all_qr_cards(key)

    html = f'''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{u['short_name']} Student Guide to Early Voting in {u['county']} | Rann Bar-On</title>
  <meta name="description" content="Complete early voting guide for {u['school_name']} students in {u['county']}, NC: on-campus site, voter ID rules, same-day registration, hours, and polling locations.">
  
  <!-- Open Graph -->
  <meta property="og:type" content="website">
  <meta property="og:url" content="{u['url']}">
  <meta property="og:title" content="{u['short_name']} Student Guide to Early Voting in {u['county']}">
  <meta property="og:description" content="Everything {u['school_name']} students need to vote early: on-campus voting site, physical student ID requirements, same-day registration, and hours.">
  <meta property="og:image" content="{u['url']}_qr.png">

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
  <div class="bg-gradient-to-r {u['hero_gradient']} px-4 py-2.5 text-center text-xs sm:text-sm font-medium text-slate-100 border-b border-slate-800 shadow-sm">
    <span class="inline-flex items-center gap-1.5">
      <span class="relative flex h-2 w-2">
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
      </span>
      <span>Early Voting in {u['county']} is <b>OPEN NOW</b> through <b>Saturday, October 31, 2026</b></span>
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
        <a href="#polling-site" class="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full {u['tag_color']} hover:opacity-80 transition">
          📍 Campus Site
        </a>
        <a href="#voter-id" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20 transition">
          ⚠️ Voter ID Rules
        </a>
        <a href="#qr-code" class="text-xs font-semibold px-3 py-1.5 rounded-full bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700 transition">
          📱 QR Codes
        </a>
      </div>
    </div>
  </header>

  <!-- University Switcher Nav -->
  <nav class="bg-slate-900/90 border-b border-slate-800/80 py-2.5 px-4 overflow-x-auto shadow-inner">
    <div class="max-w-6xl mx-auto flex items-center justify-between gap-3">
      <span class="text-xs font-bold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1.5">
        <span>🏛️</span>
        <span class="hidden sm:inline">Triangle Campus Guides:</span>
        <span class="sm:hidden">Campuses:</span>
      </span>
      <div class="flex items-center gap-2 overflow-x-auto text-xs font-semibold py-0.5">
        {switcher_html}
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="relative py-12 sm:py-16 px-4 sm:px-6 border-b border-slate-800/80 overflow-hidden">
    <div class="max-w-4xl mx-auto text-center relative z-10">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold {u['tag_color']} mb-4">
        <span>{u['badge_icon']} {u['school_name']} Voter Guide</span>
        <span class="text-slate-600">•</span>
        <span>{u['county']}, NC</span>
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight text-white mb-4 leading-tight">
        {u['short_name']} Student Guide <br class="hidden sm:inline"/>
        <span class="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-300 to-cyan-300">to Early Voting in {u['county']}</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-2xl mx-auto mb-8 leading-relaxed">
        Everything {u['school_name']} undergraduate and graduate students need to cast their ballot early. Vote on campus, register on the spot, and make sure your vote counts!
      </p>

      <!-- Key Stat Pills -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto text-left">
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Early Voting Window</div>
          <div class="text-base font-bold text-white mt-0.5">Oct 15 – Oct 31</div>
          <div class="text-[11px] text-emerald-400 mt-1 font-mono">Open 7 days/wk</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Campus Polling Site</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{u['primary_site_name'].split('(')[0].strip()}</div>
          <div class="text-[11px] text-blue-400 mt-1 font-mono">Walk or Free Shuttle</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Missed Registration?</div>
          <div class="text-base font-bold text-white mt-0.5">Same-Day Reg</div>
          <div class="text-[11px] text-purple-400 mt-1 font-mono">Register & vote at once</div>
        </div>
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 shadow-sm">
          <div class="text-xs text-slate-400 font-medium">Approved Student ID</div>
          <div class="text-sm sm:text-base font-bold text-white mt-0.5 truncate">{u['student_id_name']}</div>
          <div class="text-[11px] text-amber-300 mt-1 font-mono">Physical card only!</div>
        </div>
      </div>
    </div>
  </section>

  <!-- CRITICAL ALERT: PHYSICAL CARD ONLY -->
  <section id="voter-id" class="py-8 px-4 sm:px-6 bg-amber-950/20 border-b border-amber-900/40">
    <div class="max-w-4xl mx-auto">
      <div class="bg-amber-950/40 border-2 border-amber-500/60 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col sm:flex-row items-start gap-4">
        <div class="p-3 rounded-xl bg-amber-500/20 text-amber-400 text-2xl shrink-0">
          ⚠️
        </div>
        <div>
          <span class="inline-block px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30 mb-2">Mandatory NC State Law Requirement</span>
          <h2 class="text-xl font-bold text-white mb-2">You MUST Bring a PHYSICAL Photo ID (No Phone/Digital Cards!)</h2>
          <p class="text-sm text-amber-100/90 leading-relaxed mb-3">
            {u['id_warning_details']}
          </p>
          <div class="p-3.5 rounded-xl bg-amber-900/30 border border-amber-700/50 text-xs text-amber-200/90 space-y-1.5 font-medium">
            <p>🚫 <b>Mobile digital IDs on your phone are NOT ACCEPTED</b> at polling sites under North Carolina law.</p>
            <p>✅ <b>ACCEPTED:</b> {u['student_id_name']}, NC Driver's License, US Passport, Military/Veteran ID.</p>
            <p>💡 <b>Need an ID on the spot?</b> You can still vote! Fill out a Photo ID Exception Form at the polling place or obtain a free voter photo ID from the {u['boe_name']}.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Main Content Container -->
  <main class="max-w-5xl mx-auto px-4 sm:px-6 py-10 space-y-12">

    <!-- Section 1: Campus Polling Site -->
    <section id="polling-site" class="scroll-mt-20">
      <div class="flex items-center justify-between mb-4">
        <div>
          <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Campus Early Voting Site</span>
          <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1">{u['primary_site_name']}</h2>
        </div>
        <span class="hidden sm:inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Open to all {u['county']} Voters
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
              {u['primary_site_address']}
            </p>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">
              {u['primary_site_desc']}
            </p>

            <div class="mt-4 pt-4 border-t border-slate-800/80 space-y-2 text-xs text-slate-300 leading-relaxed">
              {u['primary_site_transit']}
            </div>
          </div>

          <div class="mt-6 pt-4">
            <a href="https://maps.google.com/?q={u['map_query']}" target="_blank" rel="noopener" class="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl {u['btn_color']} text-white font-semibold text-xs transition shadow-sm">
              <span>Open in Google Maps</span>
              <span>↗</span>
            </a>
          </div>
        </div>

        <!-- Right: Early Voting Hours Schedule -->
        <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 md:col-span-2">
          <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">{u['county']} Early Voting Hours Schedule</h3>
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
                  <td class="py-3 font-mono text-emerald-400 font-semibold">{u['hours_weekday']}</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Extended</span></td>
                </tr>
                <tr>
                  <td class="py-3 font-medium text-white">Saturdays</td>
                  <td class="py-3 text-slate-400 text-xs">Oct 17 & Oct 24</td>
                  <td class="py-3 font-mono text-blue-300 font-semibold">{u['hours_saturday']}</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Weekend</span></td>
                </tr>
                <tr>
                  <td class="py-3 font-medium text-white">Sundays</td>
                  <td class="py-3 text-slate-400 text-xs">Oct 18 & Oct 25</td>
                  <td class="py-3 font-mono text-blue-300 font-semibold">{u['hours_sunday']}</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-300">Afternoon</span></td>
                </tr>
                <tr class="bg-amber-500/5 font-semibold">
                  <td class="py-3 text-amber-300">Final Saturday (Last Day!)</td>
                  <td class="py-3 text-amber-200 text-xs">Saturday, Oct 31</td>
                  <td class="py-3 font-mono text-amber-300 font-bold">{u['hours_final_sat']}</td>
                  <td class="py-3 text-right"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Closes 3 PM</span></td>
                </tr>
              </tbody>
            </table>
          </div>
          <p class="text-xs text-slate-400 mt-4 leading-relaxed">
            💡 <i>During early voting, you can vote at <b>any</b> early voting location in {u['county']}, regardless of your assigned voting precinct!</i>
          </p>
        </div>
      </div>
    </section>

    <!-- Section 2: Same-Day Registration -->
    <section id="registration" class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 scroll-mt-20">
      <div class="max-w-3xl">
        <span class="text-xs font-mono font-semibold text-purple-400 uppercase tracking-wider">Missed the Voter Registration Deadline?</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-3">Same-Day Voter Registration is Available!</h2>
        <p class="text-sm text-slate-300 leading-relaxed mb-6">
          In North Carolina, if you are not yet registered to vote in {u['county']}, or if you moved to a new local address, you can <b>register and vote on the same visit</b> exclusively during Early Voting. (Same-day registration is <i>not</i> allowed on Election Day).
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
                <span><b>{u['student_id_name']}</b> (physical card).</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span>{u['on_campus_reg_note']}</span>
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
                <span><b>Approved Photo ID:</b> {u['student_id_name']}, NC Driver’s License, or US Passport.</span>
              </li>
              <li class="flex items-start gap-2">
                <span class="text-emerald-400 font-bold">✓</span>
                <span><b>Proof of Residence:</b> Document showing your name and current local {u['county']} address (university official portal/letter, utility bill, bank statement, paycheck, or lease; can be electronic on your phone).</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-400 leading-relaxed">
          ⚖️ <b>Student Voting Rights:</b> College students have the established legal right to choose whether to register and vote at their college address or their permanent home address. You must choose one and vote only once per election.
        </div>
      </div>
    </section>

    <!-- Section 3: All Early Voting Sites in County -->
    <section id="sites" class="scroll-mt-20">
      <div class="mb-6">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Countywide Flexibility</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1">All {len(u['all_sites'])} {u['county']} Early Voting Sites</h2>
        <p class="text-sm text-slate-400 mt-1">Any registered {u['county']} voter can cast a ballot at any of these sites during early voting hours.</p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {sites_html}
      </div>
    </section>

    <!-- Section 4: Checklist & Resources -->
    <section class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Checklist -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6">
        <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span>📋</span>
          <span>Pre-Voting Checklist</span>
        </h3>
        <ul class="space-y-3 text-xs sm:text-sm text-slate-300">
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">1.</span>
            <span><b>Physical Photo ID:</b> {u['student_id_name']}, NC Driver’s License, or US Passport. <i>Double-check you have the plastic card, not your phone!</i></span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">2.</span>
            <span><b>Proof of Residence (If Registering):</b> Physical campus ID (on campus) or local address document (off campus).</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">3.</span>
            <span><b>Check Sample Ballot:</b> Look up your sample ballot on <a href="{u['boe_url']}" target="_blank" class="text-blue-400 underline">{u['boe_name']}</a> to preview candidates before you vote.</span>
          </li>
          <li class="flex items-start gap-2.5 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80">
            <span class="text-blue-400 font-bold shrink-0">4.</span>
            <span><b>You Can Bring Notes:</b> You are legally permitted to bring a written list or notes into the voting booth (just do not take photos while voting).</span>
          </li>
        </ul>
      </div>

      <!-- Quick Helpful Links -->
      <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
        <div>
          <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span>🔗</span>
            <span>Official Resources & Support</span>
          </h3>
          <div class="space-y-2.5 text-xs sm:text-sm">
            <a href="{u['boe_url']}" target="_blank" rel="noopener" class="flex items-center justify-between p-3 rounded-xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-slate-200 transition">
              <div>
                <div class="font-semibold text-white">{u['boe_name']}</div>
                <div class="text-xs text-slate-400 mt-0.5">Live site wait times & sample ballots</div>
              </div>
              <span class="text-slate-400">↗</span>
            </a>
            <a href="https://vt.ncsbe.gov/RegLkup/" target="_blank" rel="noopener" class="flex items-center justify-between p-3 rounded-xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 text-slate-200 transition">
              <div>
                <div class="font-semibold text-white">NC Voter Search (NCSBE)</div>
                <div class="text-xs text-slate-400 mt-0.5">Verify registration status & view district ballot</div>
              </div>
              <span class="text-slate-400">↗</span>
            </a>
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200">
              <div class="font-semibold text-white">{u['support_org']}</div>
              <div class="text-xs text-slate-400 mt-1">{u['support_contact']}</div>
            </div>
          </div>
        </div>

        <div class="mt-4 pt-4 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
          <span>Need help? Call {u['county']} BOE:</span>
          <a href="tel:{u['boe_phone'].replace(' ', '').replace('(', '').replace(')', '').replace('-', '')}" class="font-mono font-bold text-blue-400 hover:underline">{u['boe_phone']}</a>
        </div>
      </div>
    </section>

    <!-- Section 5: QR Codes for All Schools -->
    <section id="qr-code" class="bg-gradient-to-br from-slate-900 via-slate-900 to-slate-950 border border-slate-800 rounded-3xl p-6 sm:p-8 scroll-mt-20 shadow-xl">
      <div class="max-w-3xl mb-8">
        <span class="text-xs font-mono font-semibold text-blue-400 uppercase tracking-wider">Campus Early Voting QR Codes</span>
        <h2 class="text-2xl sm:text-3xl font-extrabold text-white mt-1 mb-2">QR Codes for All Triangle Campuses</h2>
        <p class="text-sm text-slate-300 leading-relaxed">
          Spread the word across the Triangle! Scan any campus QR code directly with your phone camera, copy links for dorm group chats and student orgs, or download high-resolution PNG & vector SVG graphics for printing flyers and posters.
        </p>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {all_qr_cards_html}
      </div>
    </section>

  </main>

  <!-- Footer -->
  <footer class="border-t border-slate-800/80 bg-slate-950 py-8 px-4 sm:px-6 mt-16 text-xs text-slate-400">
    <div class="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
      <div>
        <p class="font-medium text-slate-300">Non-partisan student voting guide prepared by Rann Bar-On.</p>
        <p class="text-[11px] text-slate-500 mt-0.5">Official voting data sourced from the {u['boe_name']} and the NC State Board of Elections.</p>
      </div>
      <div class="flex items-center gap-4 text-xs">
        <a href="https://rannbar-on.com/" class="text-blue-400 hover:underline">rannbar-on.com Home</a>
      </div>
    </div>
  </footer>

</body>
</html>
'''

    # Save to mainwebsite (both root .html and directory /index.html)
    with open(f'{MAIN_DIR}/{key}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    os.makedirs(f'{MAIN_DIR}/{key}', exist_ok=True)
    with open(f'{MAIN_DIR}/{key}/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Also save to local Fall26 workspace
    with open(f'{LOCAL_DIR}/{key}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'Successfully generated {key}.html and {key}/index.html')

# Generate redirect for /vote and /vote/index.html to /dukevote
redirect_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url=https://rannbar-on.com/dukevote">
  <link rel="canonical" href="https://rannbar-on.com/dukevote">
  <title>Redirecting to Duke Early Voting Guide...</title>
  <script>
    window.location.replace("https://rannbar-on.com/dukevote");
  </script>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #070b14; color: #f8fafc; text-align: center; padding-top: 50px;">
  <p>Redirecting to <a href="https://rannbar-on.com/dukevote" style="color: #60a5fa;">Duke Early Voting Guide</a>...</p>
</body>
</html>
'''

with open(f'{MAIN_DIR}/vote.html', 'w', encoding='utf-8') as f:
    f.write(redirect_html)
os.makedirs(f'{MAIN_DIR}/vote', exist_ok=True)
with open(f'{MAIN_DIR}/vote/index.html', 'w', encoding='utf-8') as f:
    f.write(redirect_html)

print('Successfully configured redirect from /vote to /dukevote!')
