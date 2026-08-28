"""
Parser for Assetto Corsa's fast_lane.ai (AiSpline v7).

Binary layout (little-endian), reverse-engineered / documented by the
community (see gro-ove/actools, AcTools.AiFile):

    int32   version              (must be 7)
    int32   num_points
    int32   lap_time
    int32   sample_count
    AiPoint[num_points]:
        float32 x, y, z          (world position)
        float32 length           (distance travelled along the spline, meters)
        int32   id
    int32   num_points_extra
    AiPointExtra[num_points_extra]:
        float32 speed
        float32 gas
        float32 brake
        float32 obsolete_lat_g
        float32 radius           (corner radius at this point, meters)
        float32 side_left
        float32 side_right
        float32 camber
        float32 direction
        float32 normal_x, normal_y, normal_z
        float32 length            (NOT cumulative - ignore for positioning)
        float32 forward_x, forward_y, forward_z
        float32 tag
        float32 grade
    int32   has_grid             (0/1, grid data ignored here)

Corner detection strategy: rather than thresholding raw radius (noisy,
sensitive to arbitrary cutoffs, tends to fragment chicanes or merge
distinct corners), this treats curvature (1/radius) as a signal and finds
its local peaks - each peak is a corner apex. This naturally gives one
entry per real corner, regardless of how tight or how wide it is, as
long as it's tighter than its surroundings.

Usage:
    python parse_ai_spline.py <path_to_fast_lane.ai> [prominence_radius] [track_key] [min_apex_gap_m]

    prominence_radius: an apex must be at least this much "tighter" (in
    equivalent radius terms) than the surrounding straight/wide sections
    to count as a real corner. Lower = more sensitive (more corners
    detected, including small ones). Try 400-600 as a starting point.

    min_apex_gap_m: minimum distance (meters) between two detected
    apexes; prevents one physical corner's noisy samples from being
    counted as two. Try 60 as a starting point.
"""

import struct
import sys

import numpy as np
from scipy.signal import find_peaks

POINT_FMT = "<3f f i"          # x,y,z, length, id           -> 20 bytes
POINT_SIZE = struct.calcsize(POINT_FMT)

EXTRA_FMT = "<9f 3f f 3f f f"  # 9 floats, normal(3), length, forward(3), tag, grade -> 18 floats
EXTRA_SIZE = struct.calcsize(EXTRA_FMT)


def parse_ai_file(filepath):
    with open(filepath, "rb") as f:
        data = f.read()

    offset = 0

    def read_i32():
        nonlocal offset
        (val,) = struct.unpack_from("<i", data, offset)
        offset += 4
        return val

    version = read_i32()
    if version != 7:
        raise ValueError(f"Unsupported .ai version: {version} (only version 7 is handled)")

    num_points = read_i32()
    lap_time = read_i32()
    sample_count = read_i32()

    points = []
    for _ in range(num_points):
        x, y, z, length, pid = struct.unpack_from(POINT_FMT, data, offset)
        offset += POINT_SIZE
        points.append({"x": x, "y": y, "z": z, "length": length, "id": pid})

    num_extra = read_i32()
    extras = []
    for _ in range(num_extra):
        vals = struct.unpack_from(EXTRA_FMT, data, offset)
        offset += EXTRA_SIZE
        (speed, gas, brake, obsolete_lat_g, radius, side_left, side_right,
         camber, direction, nx, ny, nz, length, fx, fy, fz, tag, grade) = vals
        extras.append({"speed": speed, "radius": radius})

    has_grid = read_i32() if offset + 4 <= len(data) else 0

    return {
        "version": version,
        "lap_time": lap_time,
        "sample_count": sample_count,
        "points": points,
        "extras": extras,
        "has_grid": bool(has_grid),
    }


def detect_corner_apexes(spline, prominence_radius=450.0, min_apex_gap_m=60.0, smooth_window=5):
    """
    Finds corner apexes as local peaks in curvature (1/radius).

    Returns (apex_positions, total_length) where apex_positions is a list
    of (normalized_position, apex_radius_m), sorted by position.
    """
    points = spline["points"]
    extras = spline["extras"]
    if len(points) != len(extras):
        raise ValueError(
            f"points ({len(points)}) and extras ({len(extras)}) counts don't match - "
            "can't align radius to position by index."
        )

    total_length = points[-1]["length"]
    pos = np.array([p["length"] / total_length for p in points])

    radius = np.array([e["radius"] for e in extras], dtype=float)
    # radius == 0 is AC's "no data" sentinel on long straights - treat as
    # effectively infinite (i.e. definitely not a corner).
    radius = np.where(radius <= 0, 1e6, radius)
    curvature = 1.0 / radius

    if smooth_window > 1:
        kernel = np.ones(smooth_window) / smooth_window
        curvature = np.convolve(curvature, kernel, mode="same")

    avg_spacing = total_length / len(points)
    min_dist_points = max(1, int(min_apex_gap_m / avg_spacing))

    peak_idx, _ = find_peaks(
        curvature,
        distance=min_dist_points,
        prominence=1.0 / prominence_radius,
    )

    apexes = [(float(pos[i]), float(1.0 / curvature[i])) for i in peak_idx]
    apexes.sort(key=lambda a: a[0])
    return apexes, total_length


def print_tracks_py_snippet(track_key, apexes):
    print(f'    "{track_key}": [')
    for idx, (position, radius) in enumerate(apexes, start=1):
        print(f'        ({position:.4f}, {idx}),  # apex radius ~{radius:.0f}m')
    print("    ],")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_ai_spline.py <fast_lane.ai> [prominence_radius] [track_key] [min_apex_gap_m]")
        sys.exit(1)

    filepath = sys.argv[1]
    prominence_radius = float(sys.argv[2]) if len(sys.argv) > 2 else 450.0
    track_key = sys.argv[3] if len(sys.argv) > 3 else "TRACK_NAME_HERE"
    min_apex_gap_m = float(sys.argv[4]) if len(sys.argv) > 4 else 60.0

    spline = parse_ai_file(filepath)
    print(f"# Parsed {filepath}")
    print(f"# version={spline['version']} points={len(spline['points'])} "
          f"extras={len(spline['extras'])} has_grid={spline['has_grid']}")

    apexes, total_length = detect_corner_apexes(
        spline, prominence_radius=prominence_radius, min_apex_gap_m=min_apex_gap_m
    )
    print(f"# total track length ~= {total_length:.1f} m")
    print(f"# detected {len(apexes)} corner(s) with prominence_radius={prominence_radius}m "
          f"min_apex_gap_m={min_apex_gap_m}m\n")

    print_tracks_py_snippet(track_key, apexes)