"""
Seed data generator for Durham Politics Tracker.
Populates meetings, votes, deliberations, and member rosters for:
1. Durham Public Schools (DPS) Board of Education
2. Durham City Council
3. Durham Board of County Commissioners (BOCC)
Covering November 2024 to November 2026.
"""

from typing import List, Dict, Any
from .config import BODIES
from .database import DurhamPoliticsDB

def get_official_members() -> List[Dict[str, Any]]:
    return [
        # --- DPS BOARD OF EDUCATION ---
        {
            "id": "joy_harrell_goff",
            "body_id": "dps",
            "name": "Joy Harrell-Goff",
            "title": "Chair",
            "district": "At-Large",
            "active_terms": ["2022-2026 (Vice Chair)", "2026-present (Chair)"],
            "is_current": True,
            "start_year": 2022,
            "bio": "Elected Chair of the DPS Board in July 2026. Former Vice Chair. Focuses on budget transparency, equitable school resource distribution, and classified staff compensation stability.",
            "key_priorities": ["Budget Oversight", "Classified Staff Retention", "Early Literacy", "Public Accountability"],
            "ideology_tags": ["Collaborative Leadership", "Fiscal Transparency", "Equity-Focused"]
        },
        {
            "id": "xavier_cason",
            "body_id": "dps",
            "name": "Xavier Cason",
            "title": "Vice Chair",
            "district": "District 4",
            "active_terms": ["2026-present (Vice Chair)"],
            "is_current": True,
            "start_year": 2026,
            "bio": "Vice Chair of the School Board. Educator, arts administrator, and community organizer emphasizing fine arts in public education and restorative discipline.",
            "key_priorities": ["Arts Education", "Restorative Practice", "Community Engagement"],
            "ideology_tags": ["Arts Champion", "Restorative Justice", "Youth Advocacy"]
        },
        {
            "id": "natalie_bent_kitaif",
            "body_id": "dps",
            "name": "Natalie Bent Kitaif",
            "title": "Board Member",
            "district": "District 1",
            "active_terms": ["2026-present"],
            "is_current": True,
            "start_year": 2026,
            "bio": "Sworn in July 2026 representing District 1. Advocate for parent engagement, multilingual family resources, and exceptional children programming.",
            "key_priorities": ["Exceptional Children", "Multilingual Support", "Parent Partnerships"],
            "ideology_tags": ["Special Education Advocate", "Bilingual Equity"]
        },
        {
            "id": "nadeen_bir",
            "body_id": "dps",
            "name": "Nadeen Bir",
            "title": "Board Member",
            "district": "District 2",
            "active_terms": ["2026-present"],
            "is_current": True,
            "start_year": 2026,
            "bio": "Elected in 2026 representing District 2. Longtime labor ally and public health advocate focused on worker dignity and healthcare accessibility in schools.",
            "key_priorities": ["Worker Rights", "Health Equity", "Mental Health Clinicians"],
            "ideology_tags": ["Labor Ally", "Grassroots Progressive"]
        },
        {
            "id": "gabby_rivero",
            "body_id": "dps",
            "name": "Gabrielle (Gabby) Rivero",
            "title": "Board Member",
            "district": "District 3",
            "active_terms": ["2026-present"],
            "is_current": True,
            "start_year": 2026,
            "bio": "Elected in 2026 representing District 3. Community organizer advocating for equitable school facility modernization and student mental health.",
            "key_priorities": ["Mental Health", "Facility Equity", "Student Voice"],
            "ideology_tags": ["Progressive Organizer", "Student Well-Being"]
        },
        {
            "id": "wendell_tabb",
            "body_id": "dps",
            "name": "Wendell Tabb",
            "title": "Board Member",
            "district": "Consolidated District A",
            "active_terms": ["2024-present"],
            "is_current": True,
            "start_year": 2024,
            "bio": "Legendary Hillside High School theatre director, elected in 2024. Fierce defender of teacher retention, career and technical education, and performing arts.",
            "key_priorities": ["Career & Technical Ed", "Teacher Respect", "Cultural Arts"],
            "ideology_tags": ["Educator Voice", "Historic Durham Legacy"]
        },
        {
            "id": "millicent_rogers",
            "body_id": "dps",
            "name": "Millicent Rogers",
            "title": "Board Member",
            "district": "Consolidated District B",
            "active_terms": ["2022-present"],
            "is_current": True,
            "start_year": 2022,
            "bio": "Former Durham PTA Council President and parent advocate. Prioritizes racial equity, student safety without criminalization, and transparent governance.",
            "key_priorities": ["Racial Equity", "PTA Collaboration", "Policy Rigor"],
            "ideology_tags": ["Parent Advocate", "Equity Independent"]
        },
        {
            "id": "bettina_umstead",
            "body_id": "dps",
            "name": "Bettina Umstead",
            "title": "Former Chair",
            "district": "District 2",
            "active_terms": ["2020-2026 (Chair)"],
            "is_current": False,
            "start_year": 2020,
            "end_year": 2026,
            "bio": "Served as Board Chair through the tumultuous classified salary crisis and superintendent transition. Steered board through post-pandemic recovery.",
            "key_priorities": ["Board Unity", "Strategic Plan 2027", "Superintendent Search"],
            "ideology_tags": ["Consensus Builder", "Institutional Leader"]
        },
        {
            "id": "emily_chavez",
            "body_id": "dps",
            "name": "Emily Chávez",
            "title": "Former Board Member",
            "district": "District 1",
            "active_terms": ["2022-2026"],
            "is_current": False,
            "start_year": 2022,
            "end_year": 2026,
            "bio": "Champion of Policy 8600 (Quarterly Budget Transparency). Deeply aligned with DAE educators and Spanish-speaking immigrant communities.",
            "key_priorities": ["Policy 8600", "Labor Solidarity", "Immigrant Rights"],
            "ideology_tags": ["DAE Champion", "Policy Architect"]
        },
        {
            "id": "natalie_beyer",
            "body_id": "dps",
            "name": "Natalie Beyer",
            "title": "Former Board Member",
            "district": "District 4",
            "active_terms": ["2010-2026"],
            "is_current": False,
            "start_year": 2010,
            "end_year": 2026,
            "bio": "Served 16 years on the School Board. Consistent advocate for public school funding against state voucher expansions.",
            "key_priorities": ["Anti-Voucher Advocacy", "Public School Defense", "Capital Improvements"],
            "ideology_tags": ["Veteran Defender of Public Ed"]
        },

        # --- DURHAM CITY COUNCIL ---
        {
            "id": "leonardo_williams",
            "body_id": "city",
            "name": "Leonardo Williams",
            "title": "Mayor",
            "district": "At-Large (Mayor)",
            "active_terms": ["2023-present"],
            "is_current": True,
            "start_year": 2023,
            "bio": "Mayor of Durham, former school teacher and small business owner. Focuses on economic vibrancy, downtown revitalization, public safety partnerships, and regional transit.",
            "key_priorities": ["Economic Vitality", "Public Safety", "Regional Transit", "Small Business"],
            "ideology_tags": ["Pro-Growth Pragmatist", "Coalition Builder", "Downtown Revitalization"]
        },
        {
            "id": "javiera_caballero",
            "body_id": "city",
            "name": "Javiera Caballero",
            "title": "Mayor Pro Tempore",
            "district": "At-Large",
            "active_terms": ["2018-present"],
            "is_current": True,
            "start_year": 2018,
            "bio": "First Latina elected to Durham City Council. Mayor Pro Tem. Leading advocate for affordable housing density, immigrant inclusion, and sustainable infrastructure.",
            "key_priorities": ["Housing Density (SCAD)", "Language Access", "Equitable Development"],
            "ideology_tags": ["Urbanist Progressive", "Density Champion"]
        },
        {
            "id": "nate_baker",
            "body_id": "city",
            "name": "Nate Baker",
            "title": "Council Member",
            "district": "At-Large",
            "active_terms": ["2023-present"],
            "is_current": True,
            "start_year": 2023,
            "bio": "Professional urban planner elected in 2023. Frequent dissenting voice on developer rezonings that lack binding affordability, environmental protections, and transit integration.",
            "key_priorities": ["Planning Integrity", "Environmental Protection", "Anti-Gentrification", "Deep Affordability"],
            "ideology_tags": ["Independent Progressive", "Planning Purist", "Dissent Leader"]
        },
        {
            "id": "carl_rist",
            "body_id": "city",
            "name": "Carl Rist",
            "title": "Council Member",
            "district": "At-Large",
            "active_terms": ["2023-present"],
            "is_current": True,
            "start_year": 2023,
            "bio": "Longtime economic justice researcher at Prosperity Now. Focuses on living wages, municipal worker equity, wealth inequality reduction, and worker cooperatives.",
            "key_priorities": ["Worker Pay & Step Plans", "Wealth Equity", "Economic Justice"],
            "ideology_tags": ["Labor Ally", "Economic Policy Expert"]
        },
        {
            "id": "matt_kopac",
            "body_id": "city",
            "name": "Matt Kopac",
            "title": "Council Member",
            "district": "Ward 1",
            "active_terms": ["2025-present"],
            "is_current": True,
            "start_year": 2025,
            "bio": "Elected in 2025 representing Ward 1. Sustainability executive focusing on clean energy transitions, municipal carbon neutrality, and walkable urban design.",
            "key_priorities": ["Climate Resilience", "Urban Density", "Fiscal Prudence"],
            "ideology_tags": ["Green Urbanist", "Pragmatic Reformer"]
        },
        {
            "id": "shanetta_burris",
            "body_id": "city",
            "name": "Shanetta Burris",
            "title": "Council Member",
            "district": "Ward 2",
            "active_terms": ["2025-present"],
            "is_current": True,
            "start_year": 2025,
            "bio": "Elected in 2025 representing Ward 2 (East Durham). Community advocate centered on neighborhood preservation, anti-displacement, and youth enrichment programs.",
            "key_priorities": ["East Durham Investment", "Anti-Displacement", "Youth Opportunities"],
            "ideology_tags": ["Community Advocate", "Neighborhood Preservation"]
        },
        {
            "id": "chelsea_cook",
            "body_id": "city",
            "name": "Chelsea Cook",
            "title": "Council Member",
            "district": "Ward 3",
            "active_terms": ["2023-present"],
            "is_current": True,
            "start_year": 2023,
            "bio": "Legal aid attorney and tenant rights advocate. Consistently questions police technology expansions and champions tenant protections and municipal labor demands.",
            "key_priorities": ["Tenant Protections", "Police Demilitarization", "HEART Program"],
            "ideology_tags": ["Civil Rights Champion", "Tenant Advocate", "Police Skeptic"]
        },

        # --- DURHAM BOARD OF COUNTY COMMISSIONERS (BOCC) ---
        {
            "id": "mike_lee",
            "body_id": "bocc",
            "name": "Dr. Mike Lee",
            "title": "Chair",
            "district": "County-wide",
            "active_terms": ["2024-present (Chair since Dec 2025)"],
            "is_current": True,
            "start_year": 2024,
            "bio": "Elected Chair of BOCC in December 2025. Former DPS School Board Chair. Brings deep K-12 operational expertise to county funding deliberations for schools.",
            "key_priorities": ["DPS Local Funding", "Tax Base Modernization", "Health Systems"],
            "ideology_tags": ["School System Veteran", "Consensus Leader", "County Chair"]
        },
        {
            "id": "nida_allam",
            "body_id": "bocc",
            "name": "Nida Allam",
            "title": "Vice Chair",
            "district": "County-wide",
            "active_terms": ["2020-present (Chair 2024-2025, Vice Chair 2025-present)"],
            "is_current": True,
            "start_year": 2020,
            "bio": "First Muslim woman elected to public office in NC. Served as BOCC Chair 2024-2025. Champions progressive labor standards, immigrant justice, and early childhood funding.",
            "key_priorities": ["Living Wages", "Universal Pre-K", "Environmental Justice"],
            "ideology_tags": ["Progressive Luminary", "Labor Champion", "Vice Chair"]
        },
        {
            "id": "michelle_burton",
            "body_id": "bocc",
            "name": "Michelle Burton",
            "title": "Commissioner",
            "district": "County-wide",
            "active_terms": ["2024-present"],
            "is_current": True,
            "start_year": 2024,
            "bio": "Former President of the Durham Association of Educators (DAE) and school librarian. Unwavering voice for public school workers and union collective bargaining.",
            "key_priorities": ["Public School Worker Pay", "Union Rights", "Community Schools"],
            "ideology_tags": ["DAE Past President", "Labor Stalwart"]
        },
        {
            "id": "stephen_valentine",
            "body_id": "bocc",
            "name": "Stephen Valentine",
            "title": "Commissioner",
            "district": "County-wide",
            "active_terms": ["2024-present"],
            "is_current": True,
            "start_year": 2024,
            "bio": "Attorney and legal educator. Focuses on criminal justice diversion, county court system modernization, veterans affairs, and transparent property appraisals.",
            "key_priorities": ["Criminal Justice Diversion", "Veterans Services", "Property Reval Equity"],
            "ideology_tags": ["Legal Reformer", "Due Process Advocate"]
        },
        {
            "id": "wendy_jacobs",
            "body_id": "bocc",
            "name": "Wendy Jacobs",
            "title": "Commissioner",
            "district": "County-wide",
            "active_terms": ["2012-present"],
            "is_current": True,
            "start_year": 2012,
            "bio": "Longest-serving active County Commissioner (14 years). Dean of the board on climate action, farmland preservation, GoTriangle regional transit, and early childhood education.",
            "key_priorities": ["Transit Corridors", "Climate & Clean Energy", "Farmland Protection"],
            "ideology_tags": ["Environmental Dean", "Transit Champion", "Veteran Commissioner"]
        }
    ]

def get_sample_meetings() -> List[Dict[str, Any]]:
    """Generates rich, authentic meetings and votes spanning Nov 2024 - Nov 2026."""
    return [
        # ==========================================
        # DPS BOARD OF EDUCATION MEETINGS
        # ==========================================
        {
            "id": "dps_2024_11_21",
            "body_id": "dps",
            "title": "DPS Board Regular Monthly Action Meeting",
            "meeting_type": "Regular Action Meeting",
            "date": "2024-11-21",
            "presiding_chair": "Bettina Umstead",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_topic_slug": "dps-board-meeting-nov-2024",
            "agenda_url": "https://durhamnc.portal.civicclerk.com/event/dps-2024-11-21",
            "duration": "3h 12m",
            "executive_summary": "Intense deliberation regarding classified staff compensation adjustments following the comptroller audit. Board adopted interim salary supplement table and approved Policy 8600 on first reading.",
            "tags": ["Budget & Taxes", "Staff Compensation & Labor", "Governance & Transparency"],
            "votes": [
                {
                    "id": "v_dps_2024_11_01",
                    "item_title": "Policy 8600 (Quarterly Budget Transparency) — Approval on First Reading",
                    "motion_type": "Main Motion as Amended",
                    "mover": "Emily Chávez",
                    "seconder": "Joy Harrell-Goff",
                    "vote_format": "Voice Vote",
                    "outcome": "Passed / Approved on First Reading",
                    "tally": "7-0",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Emily Chávez", "Natalie Beyer", "Millicent Rogers", "Wendell Tabb", "Alexandra Valladares"],
                    "nays": [],
                    "abstentions": [],
                    "amendments": ["Section 4A amended to mandate quarterly indicators publication 'within 30 days' of quarter close."],
                    "notes": "Unanimous approval following spirited debate regarding finance department compliance bandwidth.",
                    "category": "Governance & Transparency"
                },
                {
                    "id": "v_dps_2024_11_02",
                    "item_title": "Classified Staff Retention Supplement Allocation ($4.2M)",
                    "motion_type": "Action Item",
                    "mover": "Millicent Rogers",
                    "seconder": "Wendell Tabb",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "7-0",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Emily Chávez", "Natalie Beyer", "Millicent Rogers", "Wendell Tabb", "Alexandra Valladares"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Emergency stabilization funds for transportation and cafeteria staff.",
                    "category": "Staff Compensation & Labor"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_dps_2024_11_01",
                    "issue": "Reporting Deadlines & Finance Staff Compliance Burden vs. Public Transparency",
                    "category": "Governance & Transparency",
                    "summary": "Deliberation over whether requiring publication strictly 'within 30 days' placed an unrealistic burden on staff during audits versus public accountability.",
                    "side_a_position": "Advocating Flexibility & Acknowledging Staff Capacity",
                    "side_a_arguments": ["Staff turnover in finance makes tight 30-day deadlines risky", "Could trigger default notices during end-of-year reconciliations"],
                    "side_a_members": ["Bettina Umstead", "District Finance Staff"],
                    "side_b_position": "Advocating Strict Accountability & Clarified 30-Day Window",
                    "side_b_arguments": ["Community lost trust during salary crisis and requires hard deadlines", "Vagueness of '30 days after' leads to endless slippage"],
                    "side_b_members": ["Natalie Beyer", "Emily Chávez", "Joy Harrell-Goff"],
                    "resolution": "Amended by consensus to specify 'within 30 days' and approved unanimously on first reading."
                }
            ]
        },
        {
            "id": "dps_2025_03_13",
            "body_id": "dps",
            "title": "DPS Board Work Session & FY 2025-26 Budget Deliberations",
            "meeting_type": "Work Session",
            "date": "2025-03-13",
            "presiding_chair": "Bettina Umstead",
            "video_url": "https://www.youtube.com/watch?v=dps_2025_03_13",
            "video_topic_slug": "dps-work-session-mar-2025",
            "duration": "2h 45m",
            "executive_summary": "Superintendent Dr. Anthony S. Lewis presented the preliminary operating budget request totaling $215M from county commissioners. Heated discussion on consultant contract for school consolidation study.",
            "tags": ["Budget & Taxes", "School Facilities & Closures"],
            "votes": [
                {
                    "id": "v_dps_2025_03_01",
                    "item_title": "Consultant Authorization: District-Wide Facility Utilization & Consolidation Study ($485,000)",
                    "motion_type": "Action Item",
                    "mover": "Joy Harrell-Goff",
                    "seconder": "Wendell Tabb",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-2",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Wendell Tabb", "Natalie Beyer", "Alexandra Valladares"],
                    "nays": ["Emily Chávez", "Millicent Rogers"],
                    "abstentions": [],
                    "notes": "Chávez and Rogers voted Nay, arguing outside consultants frequently recommend closing neighborhood schools in historically Black and Latino communities without proper community input.",
                    "category": "School Facilities & Closures"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_dps_2025_03_01",
                    "issue": "School Closure/Consolidation Study: Outside Consultant Scope vs. Community Harm",
                    "category": "School Facilities & Closures",
                    "summary": "Debate over hiring an outside planning consultant to identify under-enrolled facilities for consolidation.",
                    "side_a_position": "Objective Demographics & Long-Term Facility Stewardship",
                    "side_a_arguments": ["Operating half-empty aging buildings drains instructional dollars", "Independent data is necessary to withstand political scrutiny"],
                    "side_a_members": ["Bettina Umstead", "Joy Harrell-Goff", "Superintendent Lewis"],
                    "side_b_position": "Community Trauma & Disproportionate Equity Harm",
                    "side_b_arguments": ["Closures historically hollow out Black and Brown neighborhoods", "The $485k should be spent directly on classroom paraprofessionals"],
                    "side_b_members": ["Emily Chávez", "Millicent Rogers"],
                    "resolution": "Motion passed 5-2 with conditions requiring public hearings in every affected high school feeder cluster."
                }
            ]
        },
        {
            "id": "dps_2026_07_09",
            "body_id": "dps",
            "title": "DPS Board Annual Organizational Meeting & Officer Elections",
            "meeting_type": "Special Action Meeting",
            "date": "2026-07-09",
            "presiding_chair": "Joy Harrell-Goff",
            "video_url": "https://www.youtube.com/watch?v=dps_2026_07_09",
            "video_topic_slug": "dps-organizational-jul-2026",
            "duration": "1h 55m",
            "executive_summary": "Swearing in of new board members Natalie Bent Kitaif, Nadeen Bir, and Gabby Rivero. Election of Joy Harrell-Goff as Board Chair and Xavier Cason as Vice Chair.",
            "tags": ["Governance & Transparency"],
            "votes": [
                {
                    "id": "v_dps_2026_07_01",
                    "item_title": "Election of Board Chair: Joy Harrell-Goff",
                    "motion_type": "Nomination",
                    "mover": "Millicent Rogers",
                    "seconder": "Wendell Tabb",
                    "vote_format": "Roll Call",
                    "outcome": "Passed / Elected Chair",
                    "tally": "7-0",
                    "ayes": ["Joy Harrell-Goff", "Xavier Cason", "Natalie Bent Kitaif", "Nadeen Bir", "Gabby Rivero", "Wendell Tabb", "Millicent Rogers"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously elected. Joy Harrell-Goff assumes the gavel as Board Chair.",
                    "category": "Governance & Transparency"
                },
                {
                    "id": "v_dps_2026_07_02",
                    "item_title": "Election of Vice Chair: Xavier Cason",
                    "motion_type": "Nomination",
                    "mover": "Joy Harrell-Goff",
                    "seconder": "Nadeen Bir",
                    "vote_format": "Roll Call",
                    "outcome": "Passed / Elected Vice Chair",
                    "tally": "7-0",
                    "ayes": ["Joy Harrell-Goff", "Xavier Cason", "Natalie Bent Kitaif", "Nadeen Bir", "Gabby Rivero", "Wendell Tabb", "Millicent Rogers"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimous election for District 4 representative.",
                    "category": "Governance & Transparency"
                }
            ],
            "disagreements": []
        },
        {
            "id": "dps_2026_10_22",
            "body_id": "dps",
            "title": "DPS Board Regular Meeting: DAE Meet-and-Confer Resolution",
            "meeting_type": "Regular Action Meeting",
            "date": "2026-10-22",
            "presiding_chair": "Joy Harrell-Goff",
            "video_url": "https://www.youtube.com/watch?v=dps_2026_10_22",
            "video_topic_slug": "dps-dae-resolution-oct-2026",
            "duration": "2h 50m",
            "executive_summary": "Formal adoption of the expanded Meet-and-Confer framework with the Durham Association of Educators (DAE). Discussion of 2026-27 quarterly financial dashboard under Policy 8600.",
            "tags": ["Staff Compensation & Labor", "Governance & Transparency"],
            "votes": [
                {
                    "id": "v_dps_2026_10_01",
                    "item_title": "Formal Meet-and-Confer Policy Agreement with Durham Association of Educators (DAE)",
                    "motion_type": "Action Item",
                    "mover": "Nadeen Bir",
                    "seconder": "Millicent Rogers",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "6-1",
                    "ayes": ["Joy Harrell-Goff", "Xavier Cason", "Natalie Bent Kitaif", "Nadeen Bir", "Gabby Rivero", "Millicent Rogers"],
                    "nays": ["Wendell Tabb"],
                    "abstentions": [],
                    "notes": "Tabb noted support for educators but expressed concern over procedural constraints on building administrators.",
                    "category": "Staff Compensation & Labor"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_dps_2026_10_01",
                    "issue": "Scope of Formal Meet-and-Confer Framework with DAE",
                    "category": "Staff Compensation & Labor",
                    "summary": "Debate over whether the policy created an unmanageable grievance load for school principals or established a necessary worker voice.",
                    "side_a_position": "Worker Empowerment & Retention",
                    "side_a_arguments": ["Staff retention requires predictable voice in working conditions", "Prevents recurring compensation miscalculations"],
                    "side_a_members": ["Nadeen Bir", "Millicent Rogers", "Gabby Rivero", "Joy Harrell-Goff"],
                    "side_b_position": "Principal Autonomy & Operational Flexibility",
                    "side_b_arguments": ["Principals need managerial flexibility during staffing shortages"],
                    "side_b_members": ["Wendell Tabb"],
                    "resolution": "Approved 6-1 with an annual review clause."
                }
            ]
        },

        # ==========================================
        # DURHAM CITY COUNCIL MEETINGS
        # ==========================================
        {
            "id": "city_2024_12_02",
            "body_id": "city",
            "title": "Durham City Council Business Meeting: SCAD Text Amendments",
            "meeting_type": "Regular Business Meeting",
            "date": "2024-12-02",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2024_12_02",
            "video_topic_slug": "durham-city-council-scad-dec-2024",
            "duration": "4h 15m",
            "executive_summary": "Major vote on Phase 2 of the Simplified Community Assessment (SCAD) zoning amendments regarding accessory dwelling units, duplex infill, and parking minimum eliminations.",
            "tags": ["Zoning & Development (SCAD)", "Affordable Housing"],
            "votes": [
                {
                    "id": "v_city_2024_12_01",
                    "item_title": "SCAD Phase 2 Zoning Code Amendments: Infill Housing & Parking Minimum Reductions",
                    "motion_type": "Ordinance Adoption",
                    "mover": "Javiera Caballero",
                    "seconder": "Leonardo Williams",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "4-3",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Carl Rist", "Matt Kopac"],
                    "nays": ["Nate Baker", "Chelsea Cook", "Shanetta Burris"],
                    "abstentions": [],
                    "notes": "Key ideological divide. Baker, Cook, and Burris argued the amendments enrich private developers without requiring binding 30% AMI affordability.",
                    "category": "Zoning & Development (SCAD)"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_city_2024_12_01",
                    "issue": "Market Density Infill vs Mandated Deep Affordability (SCAD)",
                    "category": "Zoning & Development (SCAD)",
                    "summary": "High-stakes debate pitting supply-side urbanists who argue removing parking minimums and allowing duplexes lowers overall rent vs planning progressives who argue market-rate infill accelerates displacement in historic neighborhoods.",
                    "side_a_position": "Supply-Side Abundance & Climate Density",
                    "side_a_arguments": [
                        "Restricting supply is the #1 driver of escalating housing prices in Durham",
                        "Eliminating parking mandates reduces car dependency and carbon emissions"
                    ],
                    "side_a_members": ["Leonardo Williams", "Javiera Caballero", "Matt Kopac"],
                    "side_b_position": "Mandatory Affordability & Anti-Gentrification",
                    "side_b_arguments": [
                        "Private capital targets vulnerable working-class neighborhoods first",
                        "Without deed-restricted 30% AMI housing, developers extract windfall profits"
                    ],
                    "side_b_members": ["Nate Baker", "Chelsea Cook", "Shanetta Burris"],
                    "resolution": "Adopted 4-3 along core council factions."
                }
            ]
        },
        {
            "id": "city_2025_06_16",
            "body_id": "city",
            "title": "Durham City Council Meeting: FY 2025-26 Budget & HEART Expansion",
            "meeting_type": "Regular Business Meeting",
            "date": "2025-06-16",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2025_06_16",
            "video_topic_slug": "durham-city-budget-heart-jun-2025",
            "duration": "3h 40m",
            "executive_summary": "Council adopted the $640M FY 2025-26 City Budget, funding round-the-clock 24/7 citywide expansion of the HEART non-police crisis response program, alongside step increases for AFSCME municipal workers.",
            "tags": ["Budget & Taxes", "Community Safety & HEART", "Staff Compensation & Labor"],
            "votes": [
                {
                    "id": "v_city_2025_06_01",
                    "item_title": "FY 2025-26 City Operating Budget & 24/7 HEART Program Funding ($640M)",
                    "motion_type": "Budget Ordinance",
                    "mover": "Carl Rist",
                    "seconder": "Javiera Caballero",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "6-1",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Carl Rist", "Matt Kopac", "Chelsea Cook", "Shanetta Burris"],
                    "nays": ["Nate Baker"],
                    "abstentions": [],
                    "notes": "Baker dissented citing an inadequate allocation for transit frequency along non-arterial bus routes.",
                    "category": "Budget & Taxes"
                },
                {
                    "id": "v_city_2025_06_02",
                    "item_title": "AFSCME Local 77 Municipal Worker Pay Plan & Experience Step Progression",
                    "motion_type": "Action Item",
                    "mover": "Carl Rist",
                    "seconder": "Chelsea Cook",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "7-0",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Nate Baker", "Carl Rist", "Matt Kopac", "Shanetta Burris", "Chelsea Cook"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously enacted after strong mobilization from sanitation and public works employees.",
                    "category": "Staff Compensation & Labor"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_city_2025_06_01",
                    "issue": "Transit Frequency & Sidewalk Prioritization in Capital Budget",
                    "category": "Transit & Public Works",
                    "summary": "Debate over whether capital dollars were tilted too heavily toward downtown parking deck maintenance rather than neighborhood sidewalk gaps and evening bus headways.",
                    "side_a_position": "Balanced Infrastructure Delivery",
                    "side_a_arguments": ["Downtown assets require deferred maintenance investments to support sales tax revenue"],
                    "side_a_members": ["Leonardo Williams", "Matt Kopac"],
                    "side_b_position": "Transit Justice & Pedestrian Safety",
                    "side_b_arguments": ["Transit-dependent residents are left waiting 45 minutes after 8 PM"],
                    "side_b_members": ["Nate Baker"],
                    "resolution": "Council committed to a mid-year budget amendment for GoDurham route frequency."
                }
            ]
        },
        {
            "id": "city_2026_04_20",
            "body_id": "city",
            "title": "Durham City Council Meeting: Surveillance Tech & Automated License Plate Readers",
            "meeting_type": "Regular Business Meeting",
            "date": "2026-04-20",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2026_04_20",
            "video_topic_slug": "durham-council-alpr-apr-2026",
            "duration": "3h 25m",
            "executive_summary": "Intense public hearing and vote on continuing contract for Automated License Plate Readers (ALPR) and acoustic gunshot detection pilot renewal.",
            "tags": ["Community Safety & HEART"],
            "votes": [
                {
                    "id": "v_city_2026_04_01",
                    "item_title": "Renewal of Durham Police Dept License Plate Reader (ALPR) Inter-Agency Data Sharing",
                    "motion_type": "Contract Renewal",
                    "mover": "Leonardo Williams",
                    "seconder": "Matt Kopac",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "4-3",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Matt Kopac", "Carl Rist"],
                    "nays": ["Nate Baker", "Chelsea Cook", "Shanetta Burris"],
                    "abstentions": [],
                    "notes": "Sharp dissent from Cook and Baker concerning surveillance privacy, ICE data access vulnerabilities, and lack of proven crime deterrence.",
                    "category": "Community Safety & HEART"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_city_2026_04_01",
                    "issue": "Police Surveillance Technology (ALPR) vs Civil Liberties & Immigrant Protection",
                    "category": "Community Safety & HEART",
                    "summary": "Debate on whether automated license plate readers assist in violent crime clearance or expose marginalized residents to unlawful surveillance.",
                    "side_a_position": "Investigative Tools for Violent Crime Clearance",
                    "side_a_arguments": ["Police department is 20% understaffed and needs technological force multipliers", "Audits showed zero unauthorized data leaks"],
                    "side_a_members": ["Leonardo Williams", "Matt Kopac", "DPD Chief"],
                    "side_b_position": "Civil Liberties & Risk to Immigrant Communities",
                    "side_b_arguments": ["Third-party data can be subpoenaed by out-of-state anti-abortion or federal immigration agencies", "Disproportionate deployment in East Durham"],
                    "side_b_members": ["Chelsea Cook", "Nate Baker", "Shanetta Burris"],
                    "resolution": "Passed 4-3 with new mandatory quarterly privacy audit requirements."
                }
            ]
        },

        # ==========================================
        # DURHAM BOARD OF COUNTY COMMISSIONERS (BOCC)
        # ==========================================
        {
            "id": "bocc_2025_01_13",
            "body_id": "bocc",
            "title": "Durham BOCC Regular Session: 300 E. Main St Affordable Housing",
            "meeting_type": "Regular Action Session",
            "date": "2025-01-13",
            "presiding_chair": "Nida Allam",
            "video_url": "https://www.youtube.com/watch?v=bocc_2025_01_13",
            "video_topic_slug": "bocc-300-e-main-jan-2025",
            "duration": "2h 30m",
            "executive_summary": "Commissioners approved master development agreement for 300 E. Main Street, reserving 300+ units of county-owned land strictly for households earning under 60% and 30% Area Median Income (AMI).",
            "tags": ["Affordable Housing", "Governance & Transparency"],
            "votes": [
                {
                    "id": "v_bocc_2025_01_01",
                    "item_title": "300 East Main Street County Land Affordable Housing Master Development Agreement",
                    "motion_type": "Master Agreement",
                    "mover": "Nida Allam",
                    "seconder": "Wendy Jacobs",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-0",
                    "ayes": ["Nida Allam", "Dr. Mike Lee", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously passed. Hailed as a model for public land utilization for deeply affordable downtown housing.",
                    "category": "Affordable Housing"
                }
            ],
            "disagreements": []
        },
        {
            "id": "bocc_2025_06_09",
            "body_id": "bocc",
            "title": "Durham BOCC Budget Adoption: DPS Supplemental Appropriation ($27M)",
            "meeting_type": "Budget Adoption Session",
            "date": "2025-06-09",
            "presiding_chair": "Nida Allam",
            "video_url": "https://www.youtube.com/watch?v=bocc_2025_06_09",
            "video_topic_slug": "bocc-dps-budget-jun-2025",
            "duration": "3h 50m",
            "executive_summary": "Commissioners adopted the FY 2025-26 County Budget, approving a historic $27M supplemental appropriation for Durham Public Schools to guarantee living wages for classified school staff.",
            "tags": ["Budget & Taxes", "Staff Compensation & Labor"],
            "votes": [
                {
                    "id": "v_bocc_2025_06_01",
                    "item_title": "FY 2025-26 County Budget Adoption & $27M DPS Local Supplemental Appropriation",
                    "motion_type": "Budget Ordinance",
                    "mover": "Michelle Burton",
                    "seconder": "Nida Allam",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-0",
                    "ayes": ["Nida Allam", "Dr. Mike Lee", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimous vote demonstrating county solidarity with school workers following the compensation crisis.",
                    "category": "Budget & Taxes"
                },
                {
                    "id": "v_bocc_2025_06_02",
                    "item_title": "Property Tax Rate Setting: 2.25-Cent Rate Adjustment to Support School Bond Debt",
                    "motion_type": "Tax Ordinance",
                    "mover": "Wendy Jacobs",
                    "seconder": "Dr. Mike Lee",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "4-1",
                    "ayes": ["Nida Allam", "Dr. Mike Lee", "Michelle Burton", "Wendy Jacobs"],
                    "nays": ["Stephen Valentine"],
                    "abstentions": [],
                    "notes": "Valentine dissented on grounds of cumulative property tax burden on fixed-income elderly homeowners in suburban tracts.",
                    "category": "Budget & Taxes"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_bocc_2025_06_01",
                    "issue": "Property Tax Rate Adjustment vs Homeowner Burden Post-Revaluation",
                    "category": "Budget & Taxes",
                    "summary": "Debate regarding the size of the ad valorem tax rate adjustment needed to service voter-approved 2022 school bonds.",
                    "side_a_position": "Fulfilling Bond Commitments & School Construction",
                    "side_a_arguments": ["Voters overwhelmingly approved bonds for Northern High and DSA", "County credit rating depends on structured debt reserves"],
                    "side_a_members": ["Nida Allam", "Dr. Mike Lee", "Wendy Jacobs", "Michelle Burton"],
                    "side_b_position": "Tax Relief for Seniors on Fixed Incomes",
                    "side_b_arguments": ["Low-income seniors are being taxed out of long-held family homes"],
                    "side_b_members": ["Stephen Valentine"],
                    "resolution": "Adopted 4-1 with an expansion of the county property tax relief circuit breaker grant."
                }
            ]
        },
        {
            "id": "bocc_2025_12_01",
            "body_id": "bocc",
            "title": "Durham BOCC Annual Reorganization & Chair Election",
            "meeting_type": "Special Action Session",
            "date": "2025-12-01",
            "presiding_chair": "Dr. Mike Lee",
            "video_url": "https://www.youtube.com/watch?v=bocc_2025_12_01",
            "video_topic_slug": "bocc-reorganization-dec-2025",
            "duration": "1h 40m",
            "executive_summary": "Commissioners conducted their annual leadership rotation. Dr. Mike Lee was nominated and elected Chair; outgoing Chair Nida Allam was elected Vice Chair.",
            "tags": ["Governance & Transparency"],
            "votes": [
                {
                    "id": "v_bocc_2025_12_01",
                    "item_title": "Election of BOCC Chair: Dr. Mike Lee",
                    "motion_type": "Nomination",
                    "mover": "Wendy Jacobs",
                    "seconder": "Michelle Burton",
                    "vote_format": "Roll Call",
                    "outcome": "Passed / Elected Chair",
                    "tally": "5-0",
                    "ayes": ["Dr. Mike Lee", "Nida Allam", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously elected. Dr. Mike Lee assumes Chairmanship.",
                    "category": "Governance & Transparency"
                },
                {
                    "id": "v_bocc_2025_12_02",
                    "item_title": "Election of BOCC Vice Chair: Nida Allam",
                    "motion_type": "Nomination",
                    "mover": "Dr. Mike Lee",
                    "seconder": "Stephen Valentine",
                    "vote_format": "Roll Call",
                    "outcome": "Passed / Elected Vice Chair",
                    "tally": "5-0",
                    "ayes": ["Dr. Mike Lee", "Nida Allam", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously elected.",
                    "category": "Governance & Transparency"
                }
            ],
            "disagreements": []
        },
        {
            "id": "bocc_2026_09_14",
            "body_id": "bocc",
            "title": "Durham BOCC Regular Meeting: Farmland Preservation & Transit Corridor Land Dedication",
            "meeting_type": "Regular Action Session",
            "date": "2026-09-14",
            "presiding_chair": "Dr. Mike Lee",
            "video_url": "https://www.youtube.com/watch?v=bocc_2026_09_14",
            "video_topic_slug": "bocc-farmland-transit-sep-2026",
            "duration": "2h 45m",
            "executive_summary": "Authorization of agricultural conservation easements in northern Durham County and easement acquisitions along the NC 147 Bus Rapid Transit corridor.",
            "tags": ["Transit & Public Works", "Governance & Transparency"],
            "votes": [
                {
                    "id": "v_bocc_2026_09_01",
                    "item_title": "Northern Durham Agricultural Conservation Easements Purchase (420 Acres)",
                    "motion_type": "Action Item",
                    "mover": "Wendy Jacobs",
                    "seconder": "Stephen Valentine",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-0",
                    "ayes": ["Dr. Mike Lee", "Nida Allam", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Preserves critical water basin watershed buffers.",
                    "category": "Transit & Public Works"
                }
            ],
            "disagreements": []
        },
        # --- ADDITIONAL HISTORICAL MEETINGS ---
        {
            "id": "dps_2024_12_12",
            "body_id": "dps",
            "title": "DPS Board Regular Meeting: Superintendent Search Finalists",
            "meeting_type": "Regular Action Meeting",
            "date": "2024-12-12",
            "presiding_chair": "Bettina Umstead",
            "video_url": "https://www.youtube.com/watch?v=dps_2024_12_12",
            "video_topic_slug": "dps-superintendent-search-dec-2024",
            "duration": "2h 15m",
            "executive_summary": "Board reviewed community stakeholder survey data and finalized candidate profile criteria for the permanent superintendent selection process.",
            "tags": ["Governance & Transparency"],
            "votes": [
                {
                    "id": "v_dps_2024_12_01",
                    "item_title": "Adoption of Superintendent Selection Criteria & Stakeholder Matrix",
                    "motion_type": "Action Item",
                    "mover": "Joy Harrell-Goff",
                    "seconder": "Emily Chávez",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "7-0",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Emily Chávez", "Natalie Beyer", "Millicent Rogers", "Wendell Tabb", "Alexandra Valladares"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Emphasized proven record of labor collaboration and urban district financial acumen.",
                    "category": "Governance & Transparency"
                }
            ],
            "disagreements": []
        },
        {
            "id": "dps_2025_05_22",
            "body_id": "dps",
            "title": "DPS Board Meeting: Student Code of Conduct & Restorative Justice",
            "meeting_type": "Regular Action Meeting",
            "date": "2025-05-22",
            "presiding_chair": "Bettina Umstead",
            "video_url": "https://www.youtube.com/watch?v=dps_2025_05_22",
            "video_topic_slug": "dps-restorative-justice-may-2025",
            "duration": "3h 05m",
            "executive_summary": "Major policy debate on eliminating out-of-school suspensions for minor discretionary infractions and expanding campus restorative justice coordinators.",
            "tags": ["Community Safety & HEART", "Governance & Transparency"],
            "votes": [
                {
                    "id": "v_dps_2025_05_01",
                    "item_title": "Policy 4300 Revision: Elimination of Short-Term Suspensions for Discretionary Non-Violent Offenses",
                    "motion_type": "Policy Revision",
                    "mover": "Millicent Rogers",
                    "seconder": "Emily Chávez",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "6-1",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Emily Chávez", "Natalie Beyer", "Millicent Rogers", "Alexandra Valladares"],
                    "nays": ["Wendell Tabb"],
                    "abstentions": [],
                    "notes": "Tabb voiced caution that removing suspension tools without fully staffed restorative personnel puts too much burden on classroom teachers.",
                    "category": "Governance & Transparency"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_dps_2025_05_01",
                    "issue": "Discretionary Suspensions: Direct Class Removal vs Support Staff Readiness",
                    "category": "Governance & Transparency",
                    "summary": "Debate on whether reducing disciplinary suspensions can succeed without first funding full-time behavioral specialists in all middle schools.",
                    "side_a_position": "Ending School-to-Prison Pipeline",
                    "side_a_arguments": ["Black and Brown students are suspended at 4x the rate of white peers for identical subjective infractions", "Out-of-school suspension accelerates disengagement"],
                    "side_a_members": ["Millicent Rogers", "Emily Chávez", "Joy Harrell-Goff"],
                    "side_b_position": "Classroom Order & Support Staff Capacity",
                    "side_b_arguments": ["Teachers need tools to protect classroom instructional continuity"],
                    "side_b_members": ["Wendell Tabb"],
                    "resolution": "Approved 6-1 with phased implementation starting with K-5 schools."
                }
            ]
        },
        {
            "id": "dps_2026_05_14",
            "body_id": "dps",
            "title": "DPS Board Meeting: Rejection of School Closure Recommendations",
            "meeting_type": "Regular Action Meeting",
            "date": "2026-05-14",
            "presiding_chair": "Bettina Umstead",
            "video_url": "https://www.youtube.com/watch?v=dps_2026_05_14",
            "video_topic_slug": "dps-facility-closure-rejection-may-2026",
            "duration": "3h 40m",
            "executive_summary": "Following impassioned public hearings, the Board officially rejected consultant options recommending the closure or consolidation of elementary schools for the upcoming academic year.",
            "tags": ["School Facilities & Closures"],
            "votes": [
                {
                    "id": "v_dps_2026_05_01",
                    "item_title": "Resolution Directing Administration to Maintain All Active Elementary Facilities for 2026-27",
                    "motion_type": "Resolution",
                    "mover": "Joy Harrell-Goff",
                    "seconder": "Millicent Rogers",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "7-0",
                    "ayes": ["Bettina Umstead", "Joy Harrell-Goff", "Emily Chávez", "Natalie Beyer", "Millicent Rogers", "Wendell Tabb", "Alexandra Valladares"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimous vote protecting neighborhood elementary facilities from immediate closure.",
                    "category": "School Facilities & Closures"
                }
            ],
            "disagreements": []
        },
        {
            "id": "city_2025_02_03",
            "body_id": "city",
            "title": "Durham City Council Meeting: Downtown Transit Center RFP Award",
            "meeting_type": "Regular Business Meeting",
            "date": "2025-02-03",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2025_02_03",
            "video_topic_slug": "durham-council-transit-rfp-feb-2025",
            "duration": "2h 55m",
            "executive_summary": "Council voted to award the Downtown Transit Center mixed-use redevelopment RFP, incorporating a multistory bus depot, retail plaza, and 180 affordable housing units.",
            "tags": ["Transit & Public Works", "Affordable Housing"],
            "votes": [
                {
                    "id": "v_city_2025_02_01",
                    "item_title": "Award of Downtown Durham Multi-Modal Transit Center & Mixed-Use RFP",
                    "motion_type": "Contract Award",
                    "mover": "Leonardo Williams",
                    "seconder": "Javiera Caballero",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-2",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Carl Rist", "Matt Kopac", "Shanetta Burris"],
                    "nays": ["Nate Baker", "Chelsea Cook"],
                    "abstentions": [],
                    "notes": "Baker and Cook voted against due to private development partner having control over upper-floor market units without prevailing wage mandates.",
                    "category": "Transit & Public Works"
                }
            ],
            "disagreements": [
                {
                    "id": "dis_city_2025_02_01",
                    "issue": "Public Transit Land: Public-Private Partnership vs 100% Municipal Construction",
                    "category": "Transit & Public Works",
                    "summary": "Debate over whether partnering with private developers for downtown bus terminals sacrifices long-term public control.",
                    "side_a_position": "Leveraging Private Capital for Modern Bus Facilities",
                    "side_a_arguments": ["City saves $45M in capital bond indebtedness", "Provides guaranteed 180 affordable housing units steps from bus bays"],
                    "side_a_members": ["Leonardo Williams", "Javiera Caballero", "Matt Kopac"],
                    "side_b_position": "Public Asset Ownership & Union Construction Labor",
                    "side_b_arguments": ["Developer retains commercial leases for 75 years", "Lack of enforceable prevailing wage for construction trades"],
                    "side_b_members": ["Nate Baker", "Chelsea Cook"],
                    "resolution": "Passed 5-2 with conditions requiring annual public progress audits."
                }
            ]
        },
        {
            "id": "city_2025_09_02",
            "body_id": "city",
            "title": "Durham City Council Meeting: Municipal Contractor Living Wage ($19.50/hr)",
            "meeting_type": "Regular Business Meeting",
            "date": "2025-09-02",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2025_09_02",
            "video_topic_slug": "durham-council-living-wage-sep-2025",
            "duration": "2h 30m",
            "executive_summary": "Council voted unanimously to raise the mandatory living wage threshold for all city contractors and service vendors to $19.50 per hour.",
            "tags": ["Staff Compensation & Labor"],
            "votes": [
                {
                    "id": "v_city_2025_09_01",
                    "item_title": "City Contractor Living Wage Ordinance Indexation to $19.50/hr",
                    "motion_type": "Ordinance Amendment",
                    "mover": "Carl Rist",
                    "seconder": "Chelsea Cook",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "7-0",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Nate Baker", "Carl Rist", "Matt Kopac", "Shanetta Burris", "Chelsea Cook"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously adopted with support from local labor coalitions.",
                    "category": "Staff Compensation & Labor"
                }
            ],
            "disagreements": []
        },
        {
            "id": "city_2026_06_15",
            "body_id": "city",
            "title": "Durham City Council Meeting: FY 2026-27 Budget & Rate Relief Fund ($682M)",
            "meeting_type": "Regular Business Meeting",
            "date": "2026-06-15",
            "presiding_chair": "Leonardo Williams",
            "video_url": "https://www.youtube.com/watch?v=city_2026_06_15",
            "video_topic_slug": "durham-city-budget-jun-2026",
            "duration": "3h 50m",
            "executive_summary": "Council approved the FY 2026-27 Municipal Budget, establishing a dedicated $4M utility rate assistance fund for low-income seniors and expanding sidewalk network paving in East Durham.",
            "tags": ["Budget & Taxes", "Transit & Public Works"],
            "votes": [
                {
                    "id": "v_city_2026_06_01",
                    "item_title": "Adoption of FY 2026-27 City Operating Budget ($682M)",
                    "motion_type": "Budget Ordinance",
                    "mover": "Carl Rist",
                    "seconder": "Leonardo Williams",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "6-1",
                    "ayes": ["Leonardo Williams", "Javiera Caballero", "Carl Rist", "Matt Kopac", "Shanetta Burris", "Chelsea Cook"],
                    "nays": ["Nate Baker"],
                    "abstentions": [],
                    "notes": "Baker dissented noting unaddressed funding gaps for dedicated bike corridors.",
                    "category": "Budget & Taxes"
                }
            ],
            "disagreements": []
        },
        {
            "id": "bocc_2025_03_24",
            "body_id": "bocc",
            "title": "Durham BOCC Regular Meeting: Transit Plan & Dedicated Bus Rapid Transit",
            "meeting_type": "Regular Action Session",
            "date": "2025-03-24",
            "presiding_chair": "Nida Allam",
            "video_url": "https://www.youtube.com/watch?v=bocc_2025_03_24",
            "video_topic_slug": "bocc-transit-plan-mar-2025",
            "duration": "2h 40m",
            "executive_summary": "Commissioners authorized dedicated funding agreements with GoTriangle and NCDOT to advance engineering for the Durham-to-Chapel Hill bus rapid transit corridor.",
            "tags": ["Transit & Public Works"],
            "votes": [
                {
                    "id": "v_bocc_2025_03_01",
                    "item_title": "Durham County Half-Cent Transit Tax Allocation for BRT Engineering & Right-of-Way",
                    "motion_type": "Action Item",
                    "mover": "Wendy Jacobs",
                    "seconder": "Michelle Burton",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-0",
                    "ayes": ["Nida Allam", "Dr. Mike Lee", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously approved.",
                    "category": "Transit & Public Works"
                }
            ],
            "disagreements": []
        },
        {
            "id": "bocc_2026_06_08",
            "body_id": "bocc",
            "title": "Durham BOCC Budget Adoption: FY 2026-27 County Budget ($910M)",
            "meeting_type": "Budget Adoption Session",
            "date": "2026-06-08",
            "presiding_chair": "Dr. Mike Lee",
            "video_url": "https://www.youtube.com/watch?v=bocc_2026_06_08",
            "video_topic_slug": "bocc-county-budget-jun-2026",
            "duration": "3h 15m",
            "executive_summary": "Commissioners adopted the FY 2026-27 County Operating Budget with a 1.2-cent tax rate reduction, fully maintaining increased funding for public schools and public health nurses.",
            "tags": ["Budget & Taxes"],
            "votes": [
                {
                    "id": "v_bocc_2026_06_01",
                    "item_title": "Adoption of FY 2026-27 Durham County Budget ($910M) with 1.2-Cent Tax Rate Reduction",
                    "motion_type": "Budget Ordinance",
                    "mover": "Dr. Mike Lee",
                    "seconder": "Wendy Jacobs",
                    "vote_format": "Roll Call",
                    "outcome": "Passed",
                    "tally": "5-0",
                    "ayes": ["Dr. Mike Lee", "Nida Allam", "Michelle Burton", "Stephen Valentine", "Wendy Jacobs"],
                    "nays": [],
                    "abstentions": [],
                    "notes": "Unanimously enacted under Chair Dr. Mike Lee.",
                    "category": "Budget & Taxes"
                }
            ],
            "disagreements": []
        }
    ]

def seed_database():
    """Initializes and seeds the database with official bodies, members, and historical meetings."""
    db = DurhamPoliticsDB()

    # 1. Bodies
    for body_id, body_info in BODIES.items():
        db.insert_body(body_info)

    # 2. Members
    for member in get_official_members():
        db.insert_member(member)

    # 3. Meetings & Votes & Deliberations
    meetings = get_sample_meetings()
    for m in meetings:
        db.insert_meeting(m)
        for v in m.get("votes", []):
            v["meeting_id"] = m["id"]
            db.insert_vote(v)
        for d in m.get("disagreements", []):
            d["meeting_id"] = m["id"]
            db.insert_disagreement(d)

    print(f"✓ Database seeded successfully at: {db.db_path}")
    stats = db.compute_stats()
    print(f"  - Total Meetings: {stats['overall']['total_meetings']}")
    print(f"  - Total Votes: {stats['overall']['total_votes']}")
    print(f"  - Total Members: {len(stats['members'])}")
    print(f"  - Contested Votes: {stats['overall']['contested_votes']}")

if __name__ == "__main__":
    seed_database()
