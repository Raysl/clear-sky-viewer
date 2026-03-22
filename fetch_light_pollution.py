#!/usr/bin/env python3
"""
Fetch real light pollution data from lightpollutionmap.info GeoServer WMS.
Uses GetFeatureInfo on the World Atlas 2015 layer — no API key or rate limit.

HOW TO USE:
1. Install requests:  pip install requests
2. Run:  python3 fetch_light_pollution.py
3. Takes ~15-30 minutes for 33K cities
4. Output: city_db.js with real Bortle levels

Returns GRAY_INDEX = artificial sky brightness in mcd/m² from Falchi et al. 2016.
"""

import json
import math
import os
import time
import sys
from collections import Counter

try:
    import requests
except ImportError:
    print("ERROR: Please install requests:  pip install requests")
    sys.exit(1)

INPUT_FILE = "city_db.js"
OUTPUT_FILE = "city_db.js"       # Overwrite in place
CACHE_FILE = "lp_cache.json"     # Resume cache

# GeoServer WMS endpoint — standard WMS, no key needed
WMS_URL = "https://www.lightpollutionmap.info/geoserver/gwc/service/wms"

# WA_2015 = World Atlas 2015 (Falchi et al.)
LAYER = "PostGIS:WA_2015"


def to_mercator(lon, lat):
    """Convert lon/lat (EPSG:4326) to Web Mercator (EPSG:3857)."""
    x = lon * 20037508.34 / 180.0
    lat_rad = math.radians(lat)
    y = math.log(math.tan(math.pi / 4 + lat_rad / 2)) * 20037508.34 / math.pi
    return x, y


def mcd_to_bortle(mcd):
    """Convert artificial sky brightness (mcd/m²) to Bortle class.

    Based on Falchi et al. 2016 World Atlas thresholds.
    Natural sky ≈ 0.174 mcd/m² (21.6 mag/arcsec²).
    Total brightness = natural + artificial.
    """
    if mcd is None or mcd < 0:
        return 4  # Default if no data

    if mcd < 0.01:        # Pristine dark sky
        return 1
    elif mcd < 0.02:      # Excellent dark site
        return 2
    elif mcd < 0.08:      # ~21.5 mag/arcsec² total
        return 3
    elif mcd < 0.17:      # ~21.0 mag/arcsec²
        return 4
    elif mcd < 0.38:      # ~20.25 mag/arcsec²
        return 5
    elif mcd < 0.87:      # ~19.5 mag/arcsec²
        return 6
    elif mcd < 2.0:       # ~18.5 mag/arcsec²
        return 7
    elif mcd < 6.0:       # ~17.5 mag/arcsec²
        return 8
    else:                  # > 6 mcd/m², inner city
        return 9


def query_brightness(lon, lat, session):
    """Query GeoServer WMS GetFeatureInfo for sky brightness at a coordinate.

    Returns artificial brightness in mcd/m², or None on failure.
    """
    mx, my = to_mercator(lon, lat)
    d = 100  # 100m buffer around point
    bbox = f"{mx-d},{my-d},{mx+d},{my+d}"

    params = {
        'SERVICE': 'WMS',
        'VERSION': '1.1.1',
        'REQUEST': 'GetFeatureInfo',
        'LAYERS': LAYER,
        'QUERY_LAYERS': LAYER,
        'INFO_FORMAT': 'application/json',
        'SRS': 'EPSG:3857',
        'BBOX': bbox,
        'WIDTH': '256',
        'HEIGHT': '256',
        'X': '128',
        'Y': '128',
    }

    for attempt in range(3):
        try:
            resp = session.get(WMS_URL, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get('features', [])
                if features:
                    props = features[0].get('properties', {})
                    val = props.get('GRAY_INDEX')
                    if val is not None:
                        return float(val)
                return None
            elif resp.status_code == 429:
                time.sleep(3)
                continue
            else:
                return None
        except Exception:
            if attempt < 2:
                time.sleep(1)
            continue
    return None


def load_cache():
    """Load cached results to resume interrupted runs."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_cache(cache):
    """Save cache to disk."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def parse_city_db(filename):
    """Parse the existing city_db.js file."""
    cities = []
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line.startswith('['):
                continue
            if line.endswith(','):
                line = line[:-1]
            try:
                entry = json.loads(line)
                cities.append(entry)
            except:
                continue
    return cities


def main():
    print("=== Light Pollution Fetcher (GeoServer WMS) ===\n")

    print(f"Reading cities from {INPUT_FILE}...")
    cities = parse_city_db(INPUT_FILE)
    print(f"Loaded {len(cities)} cities")

    cache = load_cache()
    print(f"Cache has {len(cache)} entries\n")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    })

    total = len(cities)
    queried = 0
    cached_hits = 0
    failures = 0
    start_time = time.time()

    for i, city in enumerate(cities):
        lat, lon = city[3], city[4]

        # Round to 0.01° grid for caching (nearby cities share same value)
        cache_key = f"{round(lat, 2)},{round(lon, 2)}"

        if cache_key in cache:
            mcd = cache[cache_key]
            cached_hits += 1
        else:
            mcd = query_brightness(lon, lat, session)
            cache[cache_key] = mcd
            queried += 1

            if mcd is None:
                failures += 1

            # Small delay between requests (30ms)
            time.sleep(0.03)

            # Save cache every 500 queries
            if queried % 500 == 0:
                save_cache(cache)
                elapsed = time.time() - start_time
                rate = queried / elapsed if elapsed > 0 else 0
                remaining = (total - i) / rate / 60 if rate > 0 else 0
                print(f"  [{i+1}/{total}] Queried: {queried} | "
                      f"Cache: {cached_hits} | Fails: {failures} | "
                      f"Rate: {rate:.0f}/s | ETA: {remaining:.0f}min")

        # Update Bortle level
        if mcd is not None:
            city[6] = mcd_to_bortle(mcd)

        # Progress every 2000 cities
        if (i + 1) % 2000 == 0:
            elapsed = time.time() - start_time
            rate = (queried or 1) / elapsed if elapsed > 0 else 1
            remaining = (total - i) / max(rate, 0.1) / 60
            print(f"  [{i+1}/{total}] Queried: {queried} | "
                  f"Cache: {cached_hits} | Fails: {failures} | "
                  f"ETA: {remaining:.0f}min")

    # Final cache save
    save_cache(cache)

    elapsed = time.time() - start_time
    print(f"\nDone in {elapsed/60:.1f} minutes!")
    print(f"Queried: {queried} | Cache hits: {cached_hits} | Failures: {failures}")

    # Bortle distribution
    dist = Counter(c[6] for c in cities)
    print("\nBortle distribution:")
    for b in sorted(dist):
        print(f"  B{b}: {dist[b]} cities")

    # Write output
    print(f"\nWriting {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('// City database - GeoNames + World Atlas 2015 satellite light pollution data\n')
        f.write(f'// {len(cities)} cities with real Bortle levels from Falchi et al. 2016\n')
        f.write('// Format: [city, region, country, lat, lon, timezone, bortle]\n')
        f.write('const CITY_DB = [\n')

        for i, c in enumerate(cities):
            name = str(c[0]).replace('\\', '\\\\').replace('"', '\\"')
            region = str(c[1]).replace('\\', '\\\\').replace('"', '\\"')
            country = str(c[2]).replace('\\', '\\\\').replace('"', '\\"')
            comma = ',' if i < len(cities) - 1 else ''
            f.write(f'["{name}","{region}","{country}",{c[3]},{c[4]},"{c[5]}",{c[6]}]{comma}\n')

        f.write('];\n')

    size = os.path.getsize(OUTPUT_FILE)
    print(f"Output: {OUTPUT_FILE} ({size / 1024:.0f} KB)")
    print("\nYour city_db.js now has real satellite-measured Bortle levels!")


if __name__ == '__main__':
    main()
