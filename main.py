import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from capture import connect_physics, connect_graphics, read_physics, read_graphics, connect_static, read_static
from recorder import start_recording, record_frame, save_lap_to_csv, find_best_lap, create_session_folder
from voice import speak
from analyser import load_lap, align_by_position, compute_deltas, find_biggest_losses, generate_feedback_messages, compute_tyre_wear_rate, compare_tyre_wear


def process_completed_lap(lap_number, session_folder, track_name):
    print(f"\n[DEBUG] --- Processing completed lap {lap_number} ---")

    best_file, best_duration = find_best_lap(session_folder)
    lap_file = os.path.join(session_folder, f"lap_{lap_number}.csv")

    if os.path.normpath(best_file) == os.path.normpath(lap_file):
        speak(["New best lap!"])
        return

    lap = load_lap(lap_file)
    ghost = load_lap(best_file)
    
    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    losses = find_biggest_losses(common_pos, delta)
    
    time_messages = generate_feedback_messages(losses, common_positions=common_pos, delta=delta, track_name=track_name)
    tyre_messages = compare_tyre_wear(lap, ghost)

    all_messages = time_messages + tyre_messages
    print(f"[DEBUG] Messages to speak: {all_messages}")

    speak(all_messages)
    print("[DEBUG] --- Done processing lap ---\n")


def main():
    print("Connecting to Assetto Corsa's shared memory ...")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
        shm_static = connect_static()
        static_data = read_static(shm_static)
        track_name = static_data.track
        print(f"[DEBUG] Track read from static block: '{track_name}'")
        session_folder = create_session_folder(track_name)
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
                process_completed_lap(g.completedLaps, session_folder, track_name)

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