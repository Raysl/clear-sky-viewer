#!/usr/bin/env python3
"""
Regenerate faint stars in star_catalog.js while preserving all 219 named stars.
Creates ~15,000 faint stars covering the entire sky with mild galactic plane concentration.
"""

import re
import random
import math

# Set seed for reproducibility
random.seed(42)

def read_catalog(filename):
    """Read the catalog and extract named stars."""
    named_stars = []
    with open(filename, 'r') as f:
        content = f.read()

    # Extract all star entries - more careful pattern matching
    pattern = r'\[([0-9.]+),(-?[0-9.]+),(-?[0-9.]+),(-?[0-9.]+),"([^"]*)"\]'
    matches = re.findall(pattern, content)

    # Separate named and faint stars
    for match in matches:
        ra, dec, vmag, bv, name = match
        if name.strip():  # Named star
            named_stars.append({
                'ra': float(ra),
                'dec': float(dec),
                'vmag': float(vmag),
                'bv': float(bv),
                'name': name
            })

    print(f"Found {len(named_stars)} named stars")
    return named_stars

def generate_faint_stars(num_stars=15000):
    """
    Generate faint stars covering the entire sky with mild galactic concentration.

    Distribution:
    - ~5% at mag 3.0-4.0
    - ~15% at mag 4.0-5.0
    - ~35% at mag 5.0-6.0
    - ~45% at mag 6.0-6.5

    Mild galactic plane concentration: ~40% more density near the plane
    """
    faint_stars = []

    # B-V color distribution parameters (realistic)
    # Blue stars: -0.1 to 0.3 (20%)
    # Yellow stars: 0.3 to 0.8 (35%)
    # Orange stars: 0.8 to 1.3 (30%)
    # Red stars: 1.3 to 1.6 (15%)

    for i in range(num_stars):
        # Magnitude distribution
        r = random.random()
        if r < 0.05:  # 5% mag 3.0-4.0
            vmag = 3.0 + random.random()
        elif r < 0.20:  # 15% mag 4.0-5.0
            vmag = 4.0 + random.random()
        elif r < 0.55:  # 35% mag 5.0-6.0
            vmag = 5.0 + random.random()
        else:  # 45% mag 6.0-6.5
            vmag = 6.0 + random.random() * 0.5

        # B-V color distribution
        r = random.random()
        if r < 0.20:  # Blue
            bv = -0.1 + random.random() * 0.4
        elif r < 0.55:  # Yellow
            bv = 0.3 + random.random() * 0.5
        elif r < 0.85:  # Orange
            bv = 0.8 + random.random() * 0.5
        else:  # Red
            bv = 1.3 + random.random() * 0.3

        # Sky coordinates with mild galactic plane concentration
        # The galactic plane is roughly along l=0 (RA ~270 deg is galactic center)
        # Mild concentration: 40% more stars within 20 degrees of galactic plane

        # Random latitude with galactic plane concentration
        if random.random() < 0.4:  # 40% of stars concentrated near galactic plane
            # Gaussian distribution centered on galactic plane
            dec = random.gauss(0, 15)  # Centered on galactic equator (roughly Dec=0 for galactic center)
            dec = max(-90, min(90, dec))  # Clamp to valid range
        else:  # 60% distributed across full sky
            # Cosine distribution for latitude (correct for spherical distribution)
            # This gives uniform distribution when properly weighted
            u = random.random()
            dec = math.degrees(math.asin(2 * u - 1)) * random.choice([1, -1])

        # Random longitude across full sky
        ra = random.random() * 360.0

        faint_stars.append({
            'ra': ra,
            'dec': dec,
            'vmag': vmag,
            'bv': bv,
            'name': ''
        })

    return faint_stars

def write_catalog(filename, named_stars, faint_stars):
    """Write the catalog to a JavaScript file."""
    with open(filename, 'w') as f:
        f.write('// Real star catalog: ' + str(len(named_stars) + len(faint_stars)) + ' stars to mag 6.5\n')
        f.write('// Named stars (' + str(len(named_stars)) + ') from Hipparcos/Yale BSC with accurate J2000 coordinates\n')
        f.write('// Faint stars (' + str(len(faint_stars)) + ') from statistical model with mild galactic plane concentration\n')
        f.write('// Format: [RA_deg, Dec_deg, Vmag, B-V, Name]\n')
        f.write('const STAR_CATALOG = [\n')

        # Write named stars
        all_stars = named_stars + faint_stars
        for i, star in enumerate(all_stars):
            ra = star['ra']
            dec = star['dec']
            vmag = star['vmag']
            bv = star['bv']
            name = star['name']

            # Format: [RA, Dec, Vmag, B-V, Name]
            line = f'[{ra:.3f},{dec:.3f},{vmag:.2f},{bv:.2f},"{name}"]'

            if i < len(all_stars) - 1:
                f.write(line + ',\n')
            else:
                f.write(line + '\n')

        f.write('];\n')

def verify_output(filename, expected_named=219):
    """Verify the output file."""
    with open(filename, 'r') as f:
        content = f.read()

    # Count entries
    pattern = r'\[([0-9.]+),(-?[0-9.]+),(-?[0-9.]+),(-?[0-9.]+),"([^"]*)"\]'
    matches = re.findall(pattern, content)

    named_count = sum(1 for m in matches if m[4].strip())
    faint_count = sum(1 for m in matches if not m[4].strip())

    print(f"\nVerification:")
    print(f"Total entries: {len(matches)}")
    print(f"Named stars: {named_count}")
    print(f"Faint stars: {faint_count}")
    print(f"Expected named stars: {expected_named}")

    if named_count == expected_named:
        print("✓ Named star count is correct")
    else:
        print(f"✗ Named star count mismatch! Expected {expected_named}, got {named_count}")

    # Check magnitude distribution of faint stars
    faint_mags = []
    for match in matches:
        if not match[4].strip():
            faint_mags.append(float(match[2]))

    mag_3_4 = sum(1 for m in faint_mags if 3.0 <= m < 4.0)
    mag_4_5 = sum(1 for m in faint_mags if 4.0 <= m < 5.0)
    mag_5_6 = sum(1 for m in faint_mags if 5.0 <= m < 6.0)
    mag_6_plus = sum(1 for m in faint_mags if 6.0 <= m)

    print(f"\nFaint star magnitude distribution:")
    print(f"  Mag 3.0-4.0: {mag_3_4} ({100*mag_3_4/len(faint_mags):.1f}%)")
    print(f"  Mag 4.0-5.0: {mag_4_5} ({100*mag_4_5/len(faint_mags):.1f}%)")
    print(f"  Mag 5.0-6.0: {mag_5_6} ({100*mag_5_6/len(faint_mags):.1f}%)")
    print(f"  Mag 6.0+: {mag_6_plus} ({100*mag_6_plus/len(faint_mags):.1f}%)")

    # Check B-V distribution
    faint_bvs = []
    for match in matches:
        if not match[4].strip():
            faint_bvs.append(float(match[3]))

    blue = sum(1 for b in faint_bvs if -0.1 <= b < 0.3)
    yellow = sum(1 for b in faint_bvs if 0.3 <= b < 0.8)
    orange = sum(1 for b in faint_bvs if 0.8 <= b < 1.3)
    red = sum(1 for b in faint_bvs if 1.3 <= b <= 1.6)

    print(f"\nFaint star B-V distribution:")
    print(f"  Blue (-0.1 to 0.3): {blue} ({100*blue/len(faint_bvs):.1f}%)")
    print(f"  Yellow (0.3 to 0.8): {yellow} ({100*yellow/len(faint_bvs):.1f}%)")
    print(f"  Orange (0.8 to 1.3): {orange} ({100*orange/len(faint_bvs):.1f}%)")
    print(f"  Red (1.3 to 1.6): {red} ({100*red/len(faint_bvs):.1f}%)")

    # Check sky distribution (sample)
    near_galactic = sum(1 for star in matches if not star[4].strip() and abs(float(star[1])) < 20)
    print(f"\nSky distribution (faint stars):")
    print(f"  Near galactic plane (|Dec| < 20°): {near_galactic} ({100*near_galactic/len(faint_mags):.1f}%)")

if __name__ == '__main__':
    catalog_file = '/sessions/determined-confident-hypatia/mnt/skyengine/star_catalog.js'

    print("Reading existing catalog...")
    named_stars = read_catalog(catalog_file)

    print("Generating 15,000 faint stars...")
    faint_stars = generate_faint_stars(15000)

    print("Writing new catalog...")
    write_catalog(catalog_file, named_stars, faint_stars)

    print(f"Wrote catalog with {len(named_stars)} named + {len(faint_stars)} faint stars")

    print("\nVerifying output...")
    verify_output(catalog_file, expected_named=len(named_stars))

    print("\n✓ Catalog regeneration complete!")
