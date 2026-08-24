import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from capture import connect_physics, connect_graphics, read_physics, read_graphics, connect_static, read_static
from recorder import start_recording, record_frame, save_lap_to_csv, find_best_lap, create_session_folder
from analyser import load_lap, align_by_position, compute_deltas, find_biggest_losses, generate_feedback_messages
from voice import speak


def process_completed_lap(lap_number, session_folder):
    """Compares completed lap with the ghost one, and gives voice feedback."""
    print(f"\n[DEBUG] --- Processing completed lap {lap_number} ---")

    best_file, best_duration = find_best_lap(session_folder)
    lap_file = os.path.join(session_folder, f"lap_{lap_number}.csv")

    print(f"[DEBUG] session_folder = {session_folder}")
    print(f"[DEBUG] lap_file       = {lap_file}")
    print(f"[DEBUG] best_file      = {best_file}")
    print(f"[DEBUG] best_duration  = {best_duration}")
    print(f"[DEBUG] normpath match = {os.path.normpath(best_file) == os.path.normpath(lap_file)}")

    if os.path.normpath(best_file) == os.path.normpath(lap_file):
        print("[DEBUG] This lap IS the new best lap. Speaking 'New best lap!'")
        speak(["New best lap!"])
        return

    print(f"[DEBUG] Loading lap file: {lap_file}")
    lap = load_lap(lap_file)
    print(f"[DEBUG] Lap loaded: {len(lap)} rows, position range {lap['position'].min():.4f} - {lap['position'].max():.4f}")

    print(f"[DEBUG] Loading ghost file: {best_file}")
    ghost = load_lap(best_file)
    print(f"[DEBUG] Ghost loaded: {len(ghost)} rows, position range {ghost['position'].min():.4f} - {ghost['position'].max():.4f}")

    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    print(f"[DEBUG] delta range: min={delta.min():.3f}s max={delta.max():.3f}s final={delta[-1]:.3f}s")

    losses = find_biggest_losses(common_pos, delta)
    print(f"[DEBUG] Biggest losses: {losses}")

    messages = generate_feedback_messages(losses)
    print(f"[DEBUG] Messages to speak: {messages}")

    speak(messages)
    print("[DEBUG] --- Done processing lap ---\n")


def main():
    print("Connecting to Assetto Corsa's shared memory ...")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
        shm_static = connect_static()
        static_data = read_static(shm_static)
        print(f"[DEBUG] Track read from static block: '{static_data.track}'")
        session_folder = create_session_folder(static_data.track)
        print(f"[DEBUG] Session folder created: {session_folder}")
        shm_static.close()
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
                print(f"\n[DEBUG] Lap boundary detected: completedLaps went from {last_laps} to {g.completedLaps}")
                print(f"[DEBUG] iLastTime = {g.iLastTime} ms")
                print(f"[DEBUG] frames collected for this lap: {len(frames)}")

                save_lap_to_csv(frames, g.completedLaps, session_folder, g.iLastTime)
                process_completed_lap(g.completedLaps, session_folder)

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