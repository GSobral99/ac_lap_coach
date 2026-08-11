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
from capture import connect_physics, connect_graphics, read_physics, read_graphics
import pandas as pd
import os

def record_frame(physics, graphics):
    frame = {
        "position": graphics.normalizedCarPosition,
        "speed": physics.speedKmh,
        "gas": physics.gas,
        "brake": physics.brake,
        "gear": physics.gear,
        "timestamp": time.time(),
    }
    return frame

def start_recording():
    return []

def save_lap_to_csv(frames, lap_number):
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(frames)
    df.to_csv(f"data/lap_{lap_number}.csv", index=False)
    print(f"Lap {lap_number} saved in data/lap_{lap_number}.csv ({len(frames)} frames)")

def find_best_lap(data_folder="data"):
    best_lap_file = None
    best_duration = None
    for filename in os.listdir(data_folder):
        if filename.endswith(".csv"):
            filepath = os.path.join(data_folder, filename)
            df = pd.read_csv(filepath)
            duration = df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]
            
            if best_duration is None or duration < best_duration:
                best_duration = duration
                best_lap_file = filepath
    return best_lap_file, best_duration



def main():
    print("Connecting to Assetto Corsa's shared memory ...")
    print("(Make sure AC is running And on a track, not the menu)\n")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
    except Exception as e:
        print(f"Error opening shared memory: {e}")
        print("Verify that Assetto Corsa is running.")
        return

    print("Connected! Reading data (Ctrl+C to stop)...\n")

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
                frames = start_recording()
                last_laps = g.completedLaps
            print(
                f"Speed: {p.speedKmh:6.1f} km/h | "
                f"Position: {g.normalizedCarPosition:.3f} | "
                f"Laps: {g.completedLaps:2d}"
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopped by the user.")
    finally:
        shm_physics.close()
        shm_graphics.close()


if __name__ == "__main__":
    main()