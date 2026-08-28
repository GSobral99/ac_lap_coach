"""
Live corner-calling test.

Connects to AC's shared memory and speaks the corner number out loud
the moment your car's position enters a corner range defined in
tracks.py. Use this to sanity-check a track's corner calibration by
driving a lap and listening for whether "Turn N" is announced at the
moment you actually turn in, not early/late/never.

This does NOT record laps or do any lap comparison - it's a standalone
diagnostic tool, separate from main.py.

Usage:
    python test_corner_calling.py
"""

import sys
import os
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from capture import connect_physics, connect_graphics, connect_static, read_physics, read_graphics, read_static
from tracks import get_corner
from voice import speak


def main():
    print("Connecting to Assetto Corsa's shared memory ...")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
        shm_static = connect_static()
        static_data = read_static(shm_static)
        track_name = static_data.track
        shm_static.close()
    except Exception as e:
        print(f"Error opening shared memory: {e}")
        return

    print(f"Track: '{track_name}'")
    print("Connected! Drive a lap - corner numbers will be announced as you enter each one.")
    print("(Ctrl+C to stop)\n")

    last_announced_corner = None

    try:
        while True:
            p = read_physics(shm_physics)
            g = read_graphics(shm_graphics)
            position = g.normalizedCarPosition

            corner_number, inside_corner = get_corner(track_name, position)

            if inside_corner and corner_number != last_announced_corner:
                print(f"[{position:.4f}] Entering Turn {corner_number}")
                speak([f"Turn {corner_number}"])
                last_announced_corner = corner_number

            if not inside_corner:
                # reset so the same corner can be announced again next lap
                last_announced_corner = None

            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped by the user.")
    finally:
        shm_physics.close()
        shm_graphics.close()


if __name__ == "__main__":
    main()