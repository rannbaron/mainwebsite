import json

with open('/home/rann/src/website/mainwebsite/.nc_voting_cache/all_institutions.json') as f:
    institutions = json.load(f)

with open('/home/rann/src/website/mainwebsite/.nc_voting_cache/county_early_voting_sites.json') as f:
    sites_by_county = json.load(f)

# Collect campus coordinates for all 111 institutions
campus_geo_list = []
for inst in institutions:
    cname = inst['county'].upper()
    sites = sites_by_county.get(cname, [])
    keyword = inst.get('site_keyword', '').upper()
    best = None
    for s in sites:
        if keyword and (keyword in s['Name'].upper() or keyword in s['SiteAddressStreet'].upper()):
            best = s
            break
    if not best and sites:
        best = sites[0]
    lat = best['SiteCoordLat'] if best else 35.7796
    lon = best['SiteCoordLong'] if best else -78.6382
    campus_geo_list.append({
        'key': inst['key'],
        'name': inst['name'],
        'short_name': inst['short_name'],
        'city': inst['city'],
        'county': inst['county'].title() + " County",
        'lat': lat,
        'lon': lon
    })

print(f"Compiled geolocation data for {len(campus_geo_list)} campuses.")
with open('/home/rann/src/website/mainwebsite/.nc_voting_cache/campus_geo_data.json', 'w', encoding='utf-8') as f:
    json.dump(campus_geo_list, f, indent=2)
