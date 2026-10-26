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

with open(f'{CACHE_DIR}/county_boe_info.json') as f:
    boe_list = json.load(f)
boe_by_county = {c['Name'].upper(): c for c in boe_list}

with open(f'{CACHE_DIR}/county_early_voting_sites.json') as f:
    sites_by_county = json.load(f)

# NCSBE Approved list
# Format: institution name regex -> approved category
approved_raw = [
    ('Alamance Community College', 'Student, Employee, Early College Student, Early College Employee'),
    ('Appalachian State University', 'Student & Employee'),
    ('Asheville-Buncombe Technical Comm College', 'Student'),
    ('Beaufort County Community College', 'Student'),
    ('Caldwell Community College & Technical Institute', 'Student'),
    ('Campbell University', 'Student Voter ID Card'),
    ('Cape Fear Community College', 'Student & Employee'),
    ('Catawba College', 'Student (Catawba One Card)'),
    ('Chowan University', 'Student (HawksCard)'),
    ('Cleveland Community College', 'Student'),
    ('College of the Albemarle', 'Student'),
    ('Davidson College', 'Student (CatCard)'),
    ('Davidson-Davie Community College', 'Student Voter ID Card'),
    ('Duke University', 'Student Voter ID Card & DukeCard'),
    ('Durham Technical Comm College', 'Student'),
    ('East Carolina University', 'Student & Employee'),
    ('Elizabeth City State Univ', 'Student'),
    ('Elon University', 'Student'),
    ('Fayetteville State University', 'Student & Employee'),
    ('Guilford College', 'Student'),
    ('Halifax Community College', 'Student'),
    ('Isothermal Community College', 'Student (Includes REaCH Student Early College ID)'),
    ('James Sprunt Community College', 'Student'),
    ('Lees-McRae College', 'Student'),
    ('Lenoir-Rhyne University', 'Student'),
    ('Livingstone College', 'Student'),
    ('Mars Hill University', 'Student'),
    ('Mayland Community College', 'Student'),
    ('Meredith College', 'Student'),
    ('Methodist University', 'Student'),
    ('NC A&T', 'Student & Employee'),
    ('NC State University', 'Student & Employee'),
    ('North Carolina Central University', 'Student & Employee'),
    ('Piedmont Community College', 'Student'),
    ('Pitt Comm. College', 'Student & Employee'),
    ('Queens University of Charlotte', 'Student'),
    ('Randolph Community College', 'Student & Employee'),
    ('Rowan-Cabarrus Community College', 'Student & Employee'),
    ("Saint Augustine's University", 'Student'),
    ('Sandhills Community College', 'Student, SandHoke Early College Student, Employee'),
    ('Shaw University', 'Student'),
    ('Southwestern Community College', 'Student'),
    ('UNC Asheville', 'Student & Employee'),
    ('UNC Chapel Hill', 'Student & Employee (Physical card only)'),
    ('UNC Charlotte', 'Student & Employee (Physical card only)'),
    ('UNC Greensboro', 'Student & Employee'),
    ('UNC Pembroke', 'Student & Employee'),
    ('UNC School of the Arts', 'Student & Employee'),
    ('UNC Wilmington', 'Student & Employee'),
    ('Wake Forest University', 'Student (Deacon OneCard)'),
    ('Wake Technical Comm College', 'Student'),
    ('Warren Wilson College', 'Student'),
    ('Wayne Community College', 'Student (Includes Early/Middle College Student ID)'),
    ('Western Carolina University', 'Student & Employee'),
    ('Western Piedmont Comm College', 'Student'),
    ('Wilkes Community College', 'Student & Employee'),
    ('Wilson Community College', 'Student'),
    ('Wingate University', 'Student'),
    ('Winston-Salem State Univ', 'Student & Employee')
]

print("Script template created successfully")
