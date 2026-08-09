"""
Grava voltas completas do Assetto Corsa em ficheiros CSV,
para depois serem comparadas (ghost lap, delta, travagem, etc).

Usa as funções de capture.py para ligar e ler a shared memory
(physics + graphics); este ficheiro trata só da gravação.
"""

import time
from capture import connect_physics, connect_graphics, read_physics, read_graphics
import pandas as pd
import os

# a fazer:
# - start_recording()
# - record_frame(physics, graphics)
# - deteção de mudança de volta (completedLaps a aumentar)
# - save_lap_to_csv(frames, lap_number)


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
    print(f"Volta {lap_number} guardada em data/lap_{lap_number}.csv ({len(frames)} frames)")


def main():
    print("A tentar ligar a shared memory do Assetto Corsa...")
    print("(Certifica-te que o AC esta aberto E numa pista, nao so no menu)\n")

    try:
        shm_physics = connect_physics()
        shm_graphics = connect_graphics()
    except Exception as e:
        print(f"Erro ao abrir shared memory: {e}")
        print("Verifica se o Assetto Corsa esta a correr.")
        return

    print("Ligado! A ler dados (Ctrl+C para parar)...\n")

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
        print("\nParado pelo utilizador.")
    finally:
        shm_physics.close()
        shm_graphics.close()


if __name__ == "__main__":
    main()