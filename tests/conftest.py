"""
Adds `src/` and the project root to sys.path so tests can import
`analyser`, `recorder`, `capture` (from src/) and `tracks`,
`parse_ai_spline` and `main` as well.
"""
import os
import sys
import struct

import numpy as np
import pandas as pd
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)


def _make_lap_df(num_points, duration_s, wear_start=100.0, wear_end=95.0, start_ts=1_700_000_000.0):
    """
    Builds a synthetic lap DataFrame with the same columns
    recorder.record_frame() actually produces, plus lap_time_ms
    . Position goes from ~0 to ~1,
    timestamp increases steadily over duration_s.
    """
    position = np.linspace(0.01, 0.99, num_points)
    timestamp = start_ts + np.linspace(0, duration_s, num_points)
    speed = 100 + 100 * np.sin(np.linspace(0, np.pi, num_points))  # slower at both ends, faster mid-lap

    df = pd.DataFrame({
        "position": position,
        "speed": speed,
        "gas": np.clip(np.sin(np.linspace(0, np.pi, num_points)), 0, 1),
        "brake": 0.0,
        "gear": 4,
        "timestamp": timestamp,
        "tyre_wear_fl": np.linspace(wear_start, wear_end, num_points),
        "tyre_wear_fr": np.linspace(wear_start, wear_end + 1, num_points),
        "tyre_wear_rl": np.linspace(wear_start, wear_end, num_points),
        "tyre_wear_rr": np.linspace(wear_start, wear_end + 1, num_points),
        "lap_time_ms": duration_s * 1000,
    })
    return df


@pytest.fixture
def fast_lap_df():
    """A 80s lap covering the full track (position ~0.01 to ~0.99)."""
    return _make_lap_df(num_points=200, duration_s=80.0)


@pytest.fixture
def slow_lap_df():
    """An 85s lap over the same track range, used as a 'ghost' to compare against."""
    return _make_lap_df(num_points=180, duration_s=85.0, start_ts=1_700_001_000.0)


@pytest.fixture
def partial_coverage_lap_df():
    """
    A lap that only covers the last ~10% of the track - simulates the
    Hotlap warm-up-stretch case that find_best_lap() must reject as a
    ghost candidate regardless of how fast it looks.
    """
    return _make_lap_df(num_points=20, duration_s=8.0, start_ts=1_700_002_000.0).assign(
        position=np.linspace(0.90, 0.99, 20)
    )


@pytest.fixture
def wraparound_lap_df():
    """
    A lap whose last two rows "leak" into the next lap (position drops
    back near 0 right at the end) - the exact edge case load_lap() has
    to trim before any interpolation happens.
    """
    df = _make_lap_df(num_points=50, duration_s=80.0)
    leak = pd.DataFrame({
        "position": [0.001, 0.004],
        "speed": [90.0, 91.0],
        "gas": [0.5, 0.5],
        "brake": [0.0, 0.0],
        "gear": [3, 3],
        "timestamp": [df["timestamp"].iloc[-1] + 0.1, df["timestamp"].iloc[-1] + 0.2],
        "tyre_wear_fl": [94.9, 94.8],
        "tyre_wear_fr": [95.9, 95.8],
        "tyre_wear_rl": [94.9, 94.8],
        "tyre_wear_rr": [95.9, 95.8],
        "lap_time_ms": [80000, 80000],
    })
    return pd.concat([df, leak], ignore_index=True)


@pytest.fixture
def sample_spline():
    """
    A synthetic 'parsed .ai spline' with the exact shape
    detect_corner_apexes() expects: {"points": [{"length": ...}, ...],
    "extras": [{"radius": ...}, ...]}. Radius is large almost
    everywhere, with one clear dip - one real corner - around the midpoint.
    """
    n = 200
    total_length = 2000.0
    lengths = np.linspace(0, total_length, n)

    radius = np.full(n, 800.0)
    dip_center = n // 2
    dip_width = 8
    for i in range(dip_center - dip_width, dip_center + dip_width):
        # smooth-ish dip down to ~25m at the very center
        distance_from_center = abs(i - dip_center)
        radius[i] = 25.0 + distance_from_center * 90.0

    points = [{"length": float(l)} for l in lengths]
    extras = [{"radius": float(r)} for r in radius]
    return {"points": points, "extras": extras}


@pytest.fixture
def straight_spline():
    """Same shape as sample_spline, but with no dip anywhere - a straight line."""
    n = 100
    total_length = 1000.0
    lengths = np.linspace(0, total_length, n)
    points = [{"length": float(l)} for l in lengths]
    extras = [{"radius": 0.0} for _ in range(n)]  # 0 = AC's "no data" sentinel, treated as infinite
    return {"points": points, "extras": extras}


@pytest.fixture
def sample_ai_bytes(tmp_path):
    """
    A real, minimal, valid fast_lane.ai (v7) file on disk, built with the
    exact binary layout parse_ai_spline.parse_ai_file() reads: header,
    N points (POINT_FMT = "<3f f i"), N extras (EXTRA_FMT = "<9f 3f f 3f f f"),
    then a has_grid flag. Three points/extras is enough to test the parser
    itself; corner-detection logic is tested separately against
    `sample_spline`, which doesn't need real binary I/O.
    """
    num_points = 3
    path = tmp_path / "fast_lane.ai"

    with open(path, "wb") as f:
        f.write(struct.pack("<i", 7))            # version
        f.write(struct.pack("<i", num_points))   # num_points
        f.write(struct.pack("<i", 90000))        # lap_time (ms, unused by our code)
        f.write(struct.pack("<i", num_points))   # sample_count

        for i in range(num_points):
            # x, y, z, length, id
            f.write(struct.pack("<3f f i", float(i * 10), 0.0, 0.0, float(i * 10), i))

        f.write(struct.pack("<i", num_points))   # num_extra
        for i in range(num_points):
            # speed, gas, brake, obsolete_lat_g, radius, side_left, side_right,
            # camber, direction, nx, ny, nz, length, fx, fy, fz, tag, grade
            vals = [50.0, 1.0, 0.0, 0.0, 500.0, 5.0, 5.0, 0.0, 0.0, 0.0, 0.0, 1.0, 10.0, 1.0, 0.0, 0.0, 0.0, 0.0]
            f.write(struct.pack("<9f 3f f 3f f f", *vals))

        f.write(struct.pack("<i", 1))            # has_grid = True

    return path
