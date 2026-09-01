"""
(ENGLISH)
Records completed laps from Assetto Corsa in CSV files,
for then be analysed (ghost lap, delta, travagem, etc).

Uses the functions from capture.py to connect a read the shared memory
(physics + graphics); this file only records.
"""

"""
(PORTUGUÊS)
Grava voltas completas do Assetto Corsa em ficheiros CSV,
para depois serem comparadas (ghost lap, delta, travagem, etc).

Usa as funções de capture.py para ligar e ler a shared memory
(physics + graphics); este ficheiro trata só da gravação.
"""

import time
from capture import connect_physics, connect_graphics, read_physics, read_graphics, connect_static, read_static

import pandas as pd
import os
from datetime import datetime

def record_frame(physics, graphics):
    frame = {
        "position": graphics.normalizedCarPosition,
        "speed": physics.speedKmh,
        "gas": physics.gas,
        "brake": physics.brake,
        "gear": physics.gear,
        "timestamp": time.time(),
        "tyre_wear_fl": physics.tyreWear[0],
        "tyre_wear_fr": physics.tyreWear[1],
        "tyre_wear_rl": physics.tyreWear[2],
        "tyre_wear_rr": physics.tyreWear[3],
    }
    return frame

def start_recording():
    return []


def create_session_folder(track_name, base_folder="data"):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{track_name}_{timestamp}"
    session_path = os.path.join(base_folder, folder_name)
    os.makedirs(session_path, exist_ok=True)
    return session_path

def save_lap_to_csv(frames, lap_number, session_folder, lap_time_ms):
    os.makedirs(session_folder, exist_ok=True)
    df = pd.DataFrame(frames)
    df["lap_time_ms"] = lap_time_ms
    filepath = os.path.join(session_folder, f"lap_{lap_number}.csv")
    df.to_csv(filepath, index=False)
    print(f"Lap {lap_number} saved in {filepath} ({len(frames)} frames, {lap_time_ms/1000:.2f}s)")


def find_best_lap(session_folder, min_coverage=0.85):
    best_lap_file = None
    best_duration = None

    for filename in os.listdir(session_folder):
        if filename.endswith(".csv"):
            filepath = os.path.join(session_folder, filename)
            df = pd.read_csv(filepath)
            
            coverage = df["position"].max() - df["position"].min()
            if coverage < min_coverage:
                continue

            duration = df["lap_time_ms"].iloc[0] / 1000.0

            if best_duration is None or duration < best_duration:
                best_duration = duration
                best_lap_file = filepath

    return best_lap_file, best_duration


if __name__ == "__main__":
    # Teste rápido isolado: liga, grava 1-2 voltas, e confirma que os CSVs saem bem
    print("Connecting to Assetto Corsa's shared memory ...")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
        shm_static = connect_static()
        static_data = read_static(shm_static)
        session_folder = create_session_folder(static_data.track)
        shm_static.close()
    except Exception as e:
        print(f"Error opening shared memory: {e}")
        exit()

    print(f"Connected! Recording to {session_folder} (Ctrl+C to stop)...\n")

    try:
        last_laps = 0
        frames = start_recording()
        while True:
            p = read_physics(shm_physics)
            g = read_graphics(shm_graphics)

            frame = record_frame(p, g)
            frames.append(frame)

            if g.completedLaps > last_laps:
                save_lap_to_csv(frames, g.completedLaps, session_folder, g.iLastTime)
                frames = start_recording()
                last_laps = g.completedLaps

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by the user.")
    finally:
        shm_physics.close()
        shm_graphics.close()