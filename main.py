import sys
import os
import time
import json
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from capture import connect_physics, connect_graphics, read_physics, read_graphics, connect_static, read_static
from recorder import start_recording, record_frame, save_lap_to_csv, find_best_lap, create_session_folder
from voice import speak
from analyser import load_lap, align_by_position, compute_deltas, find_biggest_losses, generate_feedback_messages, compute_tyre_wear_rate, compare_tyre_wear

def write_live_state(p, g, filepath="data/live_state.json"):
    state = {
        "speed": p.speedKmh,
        "rpm": p.rpms,
        "gear": p.gear,
        "gas": p.gas,
        "brake": p.brake,
        "position": g.normalizedCarPosition,
        "lap": g.completedLaps,
        "tyre_temp_fl": p.tyreCoreTemperature[0],
        "tyre_temp_fr": p.tyreCoreTemperature[1],
        "tyre_temp_rl": p.tyreCoreTemperature[2],
        "tyre_temp_rr": p.tyreCoreTemperature[3],
    }
    tmp_path = filepath + ".tmp"
    with open(filepath, "w") as f:
        json.dump(state, f)
    os.replace(tmp_path, filepath)

def write_lap_summary(lap_number, lap_time_ms, messages, filepath="data/last_lap_summary.json"):
    summary = {
        "lap_number": lap_number,
        "lap_time_s": lap_time_ms / 1000.0,
        "messages": messages,
    }
    with open(filepath, "w") as f:
        json.dump(summary, f)

def process_completed_lap(lap_number, session_folder, track_name):
    print(f"\n[DEBUG] --- Processing completed lap {lap_number} ---")

    best_file, best_duration = find_best_lap(session_folder)
    lap_file = os.path.join(session_folder, f"lap_{lap_number}.csv")
    
    if os.path.normpath(best_file) == os.path.normpath(lap_file):
        speak(["New best lap!"])
        write_lap_summary(lap_number, best_duration * 1000, ["New best lap!"])
        return

    lap = load_lap(lap_file)
    ghost = load_lap(best_file)
    print(f"[DEBUG] Lap {lap_number} position range: {lap['position'].min():.4f} - {lap['position'].max():.4f}")
    print(f"[DEBUG] Ghost position range: {ghost['position'].min():.4f} - {ghost['position'].max():.4f}")
    
    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    losses = find_biggest_losses(common_pos, delta)
    print(f"[DEBUG] delta range: min={delta.min():.3f}s max={delta.max():.3f}s final={delta[-1]:.3f}s")
    print(f"[DEBUG] Biggest losses (raw): {losses}")
    print(f"[DEBUG] best_file used as ghost: {best_file}")
    time_messages = generate_feedback_messages(losses, common_positions=common_pos, delta=delta, track_name=track_name)
    tyre_messages = compare_tyre_wear(lap, ghost)

    all_messages = time_messages + tyre_messages
    print(f"[DEBUG] Messages to speak: {all_messages}")

    speak(all_messages)

    lap_df = load_lap(lap_file)
    lap_time_ms = lap_df["lap_time_ms"].iloc[0]
    write_lap_summary(lap_number, lap_time_ms, all_messages)

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
            write_live_state(p, g)

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