"""
precinct_friendly_names.py
Official human-readable / facility precinct names for North Carolina counties
where official State Board of Elections shapefiles or voter files contain
alphanumeric codes, bare numbers, or symbol-like names.
"""

import re

STATEWIDE_FRIENDLY_NAMES = {
    'DURHAM': {
        '30-3': 'East Regional Library',
        '30-4': 'Spring Valley Elementary',
        '33-1': 'Bethesda Elementary',
        '33-2': "Lowe's Grove Baptist",
        '35-4': 'Lyons Farm Elementary',
        '35-5': 'Zakat Community Center',
        '56': "St. Stephen's Episcopal",
        '55-11': 'Weaver Street Rec Center',
        '55-49': 'NCCU Turner Law Building'
    },
    'FORSYTH': {
        '016': 'Sedge Garden United Methodist',
        '017': 'Glenn High School',
        '076': 'Agape Faith Church',
        '077': 'Southwest Elementary',
        '085': 'East Forsyth High School',
        '124': 'Heaven View United Pentecostal'
    },
    'UNION': {
        '0005': 'Monroe Fire Dept Station 4',
        '005': 'Monroe Fire Dept Station 4',
        '0019': 'Mineral Springs VFD',
        '019': 'Mineral Springs VFD',
        '0020A': 'Waxhaw VFD',
        '020A': 'Waxhaw VFD',
        '0020B': 'Waxhaw Bible Church',
        '020B': 'Waxhaw Bible Church',
        '0030': 'Cornerstone Community Church',
        '030': 'Cornerstone Community Church',
        '0044': 'Millbridge Clubhouse',
        '044': 'Millbridge Clubhouse',
        '0045': 'New Town Elementary',
        '045': 'New Town Elementary'
    },
    'ONSLOW': {
        'NE22A': 'Northeast A (Enon Chapel)',
        'NE22B': 'Northeast B (Centerview)'
    },
    'ASHE': {
        '13': 'Obids'
    },
    'SWAIN': {
        'BC1': 'Bryson City 1',
        'BC2': 'Bryson City 2',
        'WHCH': 'Whittier/Cherokee'
    },
    'SCOTLAND': {
        '01-16': 'Scotland County Annex',
        '02-25': 'South Johnson Elementary',
        '03': 'Scotland Place',
        '04': 'National Guard Armory',
        '05-10': 'Gibson Fire Station',
        '06-89': 'Laurel Hill Community Center',
        '07': 'Wagram Recreation Center'
    },
    'LEE': {
        'A1': 'Southern Lee High School',
        'A2': 'J. Glenn Edwards Elementary',
        'B1': 'Deep River Elementary',
        'B2': 'B.T. Bullock Elementary',
        'C1': 'Greenwood Elementary',
        'C2': 'Tramway Elementary',
        'D1': 'J.R. Ingram Elementary',
        'D2': 'American Legion Post 382',
        'E1': 'Broadway Elementary',
        'E2': 'East Lee Middle School'
    },
    'WAYNE': {
        '01': 'Fremont Town Hall',
        '02': 'Eureka Methodist Church',
        '03': 'Little River Fire Station',
        '04': 'Pikeville Fire Station',
        '05': 'Belfast Fire Department',
        '06': 'Crossway Church',
        '07': 'New Hope Fire Station',
        '08': 'Oakland Fire Station',
        '09': 'Westwood United Methodist',
        '10': 'Word of Truth Christian Fellowship',
        '11': 'Greenleaf Christian Church',
        '12': 'Adamsville Baptist Church',
        '13': 'Central Heights FWB Church',
        '14': 'New Hope Friends Church',
        '15': 'Seven Springs Baptist Church',
        '16': 'American Legion Post 11',
        '17': 'St. James AME Zion Church',
        '18': 'WAGES Building',
        '1920': 'First African Baptist Church',
        '21': 'St. Luke United Methodist',
        '22': 'Faith Alliance Church',
        '23': 'The Hydrant Wesleyan Church',
        '24': 'WoodmenLife Lodge 481',
        '2530': 'Steele Memorial Library',
        '26': 'Dudley Fire Station',
        '27': 'Mays Chapel Church',
        '28': 'Indian Springs Fire Station',
        '29': 'Wayne County Public Library'
    },
    'NEW HANOVER': {
        'CF01': 'Wrightsboro School',
        'CF02': 'Castle Hayne Elementary',
        'CF05': 'CFCC North Campus (McKeithan Ctr)',
        'CF06': 'Northside Baptist Church',
        'FP03': 'Kure Beach Town Hall',
        'FP04': 'Myrtle Grove Middle School',
        'FP06': 'Bellamy Elementary School',
        'FP07': 'Anderson Elementary School',
        'FP08': 'Carolina Beach Muni Complex',
        'H01': 'Cape Fear Christian Church',
        'H02': 'Northeast Regional Library',
        'H04': 'College Park Elementary',
        'H05': 'Blair Elementary School',
        'H06': 'Freedom Baptist Church',
        'H08': 'Ogden Elementary School',
        'H10': 'Eaton Elementary School',
        'H11': 'Coastal Community Baptist Church',
        'H12': 'Porters Neck Elementary',
        'H13': 'Porters Neck Village',
        'M02': 'Masonboro Elementary',
        'M03': 'Moose Lodge',
        'M04': 'United Advent Christian Church',
        'M06': 'Myrtle Grove Baptist Church',
        'M07': 'Harbor United Methodist',
        'W03': 'MLK Center',
        'W08': 'Board of Education (Spencer Bldg)',
        'W12': 'Forest Hills School',
        'W15': 'Career Readiness Academy (Mosley)',
        'W16': 'Lifepoint Church',
        'W17': 'Holly Tree Elementary',
        'W21': 'Codington Elementary',
        'W25': 'CFCC McLeod Building',
        'W26': 'Sunset Park Elementary',
        'W27': 'Freeman Elementary',
        'W29': 'Williston Middle School',
        'W30': 'Cape Fear Presbyterian',
        'W31': 'Senior Resource Center',
        'W33': 'Bradley Creek Elementary',
        'W34': 'UNCW Warwick Center',
        'W35': 'Wesley Memorial UMC',
        'WB': 'Wrightsville Beach Town Hall'
    },
    'CABARRUS': {
        '01-02': 'Flowes Store Volunteer Fire Station',
        '01-04': 'Hickory Ridge Middle School',
        '01-07': 'Harrisburg Elementary School',
        '01-08': 'Rocky River Elementary School',
        '01-10': 'Harrisburg Town Hall',
        '01-11': 'Providence Baptist Church',
        '02-01': 'Rock Hill AME Zion Church',
        '02-02': 'Furr Elementary School',
        '02-03': 'Jay M. Robinson High School',
        '02-06': 'Winecoff Elementary School',
        '02-08': 'Odell Primary School',
        '02-09': 'Cox Mill Elementary School',
        '02-10': 'Weddington Hills Elementary',
        '03-00': 'Gilwood Presbyterian Church',
        '04-01': 'Mt. Olivet Methodist Church',
        '04-03': 'New Hope Lutheran Church',
        '04-08': 'Northwest Cabarrus High School',
        '04-09': 'Covenant Presbyterian Church',
        '04-11': 'Kannapolis YMCA',
        '04-12': 'Second Presbyterian Church',
        '04-13': 'Cabarrus Shrine Club',
        '05-00': 'Concord Middle School',
        '06-00': 'Cross of Christ Lutheran Church',
        '07-00': 'Bethlehem Church',
        '08-00': 'Mt. Pleasant High School',
        '09-00': 'Georgeville Fire Station',
        '10-00': 'Bethel Elementary School',
        '11-01': 'Kerr Memorial Baptist Church',
        '11-02': 'Center United Methodist Church',
        '12-03': 'All Saints Episcopal Church',
        '12-04': 'Concord High School',
        '12-05': 'Cabarrus Senior Center',
        '12-08': 'Hartsell Recreation Center',
        '12-09': 'Wolf Meadow Elementary School',
        '12-11': 'Epworth United Methodist Church',
        '12-12': 'Central Cabarrus High School',
        '12-13': 'First Missionary Baptist Church',
        '12-14': 'St. James Catholic Church'
    },
    'NORTHAMPTON': {
        'GAPL': 'Garysburg/Pleasant Hill'
    },
    'PITT': {
        '1513A': 'Greenville 13A'
    }
}

def format_precinct_name(county, pid, raw_name=None):
    """
    Returns an official, human-readable name for a precinct.
    Applies county-specific friendly name maps, cleans up formatting,
    and standardizes precinct numbering.
    """
    county_upper = str(county).upper().strip()
    pid_str = str(pid).strip()

    if county_upper in STATEWIDE_FRIENDLY_NAMES and pid_str in STATEWIDE_FRIENDLY_NAMES[county_upper]:
        return STATEWIDE_FRIENDLY_NAMES[county_upper][pid_str]

    if county_upper == 'GATES' and raw_name:
        return re.sub(r'\s+', ' ', raw_name).strip()

    if county_upper == 'WAKE':
        if raw_name and raw_name.startswith('Precinct '):
            return raw_name
        return f"Precinct {pid_str}"

    if county_upper == 'MECKLENBURG':
        if raw_name and raw_name.startswith('Precinct '):
            return raw_name
        clean_num = pid_str.lstrip('0') or '0'
        return f"Precinct {clean_num}"

    if county_upper == 'GUILFORD':
        if raw_name and raw_name.startswith('Precinct '):
            return raw_name
        return f"Precinct {pid_str}"

    return raw_name or f"Precinct {pid_str}"

