"""
Sweep de parâmetros para calibrar deteção de curvas contra um número
real conhecido de curvas da pista.

Usage:
    python calibrate_corners.py <fast_lane.ai> <numero_real_de_curvas>
"""

import sys
from parse_ai_spline import parse_ai_file, detect_corner_apexes


def sweep(filepath, target_corners):
    spline = parse_ai_file(filepath)

    prominence_values = [150, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800]
    gap_values = [40, 60, 80, 100, 120, 150]

    matches = []

    for prom in prominence_values:
        for gap in gap_values:
            apexes, _ = detect_corner_apexes(spline, prominence_radius=prom, min_apex_gap_m=gap)
            count = len(apexes)
            if count == target_corners:
                matches.append((prom, gap, count))

    return matches


if __name__ == "__main__":
    filepath = sys.argv[1]
    target = int(sys.argv[2])

    matches = sweep(filepath, target)

    if not matches:
        print(f"No combination gave exactly {target} corners. Try widening the search ranges.")
    else:
        print(f"Combinations that give exactly {target} corners:")
        for prom, gap, count in matches:
            print(f"  prominence_radius={prom}, min_apex_gap_m={gap}")