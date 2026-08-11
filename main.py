import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from capture import connect_physics, connect_graphics, read_physics, read_graphics
from recorder import start_recording, record_frame, save_lap_to_csv, find_best_lap
from analyser import load_lap, align_by_position, compute_deltas, find_biggest_losses, generate_feedback_messages
from voice import speak

def process_completed_lap(lap_number):
    """Compares completed lap with the ghost one, and gives voice feedback."""
    best_file, best_duration = find_best_lap()
    lap_file = f"data/lap_{lap_number}.csv"

    if os.path.normpath(best_file) == os.path.normpath(lap_file):
        speak(["New best lap!"])
        return

    lap = load_lap(lap_file)
    ghost = load_lap(best_file)

    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    losses = find_biggest_losses(common_pos, delta)

    messages = generate_feedback_messages(losses)
    speak(messages)


def main():
    print("Connecting to Assetto Corsa's shared memory ...")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
    except Exception as e:
        print(f"Error opening shared memory: {e}")
        return

    print("Connected! Recording laps (Ctrl+C to stop)...\n")

    try:
        last_laps = 0
        frames = start_recording()
        while True:
            p = read_physics(shm_physics)
            g = read_graphics(shm_graphics)

            frame = record_frame(p, g)
            frames.append(frame)

            if g.completedLaps > last_laps:
                save_lap_to_csv(frames, g.completedLaps)
                process_completed_lap(g.completedLaps)
                frames = start_recording()
                last_laps = g.completedLaps

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by the user.")
    finally:
        shm_physics.close()
        shm_graphics.close()


if __name__ == "__main__":
    main()