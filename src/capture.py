"""
(ENGLISH)
Reads telemetry data in real time from Assetto Corsa
from shared memory (Local\\acpmf_physics e Local\\acpmf_graphics).

Requirements: Assetto Corsa needs to be running
(in a session, not on at he menu) for the data to show up.
"""

"""
(PORTUGUÊS)
Lê dados de telemetria em tempo real do Assetto Corsa (classico)
via shared memory (Local\\acpmf_physics e Local\\acpmf_graphics).

Requisito: o Assetto Corsa tem de estar aberto e numa sessão
(numa pista, não só no menu) para os dados aparecerem.
"""

import mmap
import ctypes
import time

class SPageFilePhysics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpms", ctypes.c_int),
        ("steerAngle", ctypes.c_float),
        ("speedKmh", ctypes.c_float),
        ("velocity", ctypes.c_float * 3),
        ("accG", ctypes.c_float * 3),
        ("wheelSlip", ctypes.c_float * 4),
        ("wheelLoad", ctypes.c_float * 4),
        ("wheelsPressure", ctypes.c_float * 4),
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("tyreWear", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD", ctypes.c_float * 4),
        ("suspensionTravel", ctypes.c_float * 4),
        ("drs", ctypes.c_float),
        ("tc", ctypes.c_float),
        ("heading", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("roll", ctypes.c_float),
        ("cgHeight", ctypes.c_float),
        ("carDamage", ctypes.c_float * 5),
        ("numberOfTyresOut", ctypes.c_int),
        ("pitLimiterOn", ctypes.c_int),
        ("abs", ctypes.c_float),
    ]

class SPageFileGraphics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("currTime", ctypes.c_wchar * 15),
        ("lstTime", ctypes.c_wchar * 15),
        ("bstTime", ctypes.c_wchar * 15),
        ("split", ctypes.c_wchar * 15),
        ("completedLaps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("iCurrentTime", ctypes.c_int),
        ("iLastTime", ctypes.c_int),
        ("iBestTime", ctypes.c_int),
        ("sessionTimeLeft", ctypes.c_float),
        ("distanceTraveled", ctypes.c_float),
        ("isInPit", ctypes.c_int),
        ("currentSectorIndex", ctypes.c_int),
        ("lastSectorTime", ctypes.c_int),
        ("numberOfLaps", ctypes.c_int),
        ("tyreCompound", ctypes.c_wchar * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition", ctypes.c_float),
    ]
    
class SPageFileStatic(ctypes.Structure):
    _fields_ = [
        ("smVersion", ctypes.c_wchar * 15),
        ("acVersion", ctypes.c_wchar * 15),
        ("numberOfSessions", ctypes.c_int),
        ("numCars", ctypes.c_int),
        ("carModel", ctypes.c_wchar * 33),
        ("track", ctypes.c_wchar * 33),
        ("playerName", ctypes.c_wchar * 33),
        ("playerSurname", ctypes.c_wchar * 33),
        ("playerNick", ctypes.c_wchar * 33),
        ("sectorCount", ctypes.c_int),
        #can had more parameters if I need in the future
    ]

def connect_physics():
    """Opens the AC physics shared memory."""
    shm = mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), "Local\\acpmf_physics")
    return shm

def read_physics(shm):
    """Reads current struct of the physics shared memory."""
    shm.seek(0)
    data = shm.read(ctypes.sizeof(SPageFilePhysics))
    physics = SPageFilePhysics.from_buffer_copy(data)
    return physics

def connect_graphics():
    """Opens the shared memory of graphics of AC (position in the track, laps, etc)."""
    shm = mmap.mmap(-1, ctypes.sizeof(SPageFileGraphics), "Local\\acpmf_graphics")
    return shm

def read_graphics(shm):
    """Reads current struct of graphics shared memory."""
    shm.seek(0)
    data = shm.read(ctypes.sizeof(SPageFileGraphics))
    graphics = SPageFileGraphics.from_buffer_copy(data)
    return graphics

def connect_static():
    shm = mmap.mmap(-1, ctypes.sizeof(SPageFileStatic), "Local\\acpmf_static")
    return shm

def read_static(shm):
    shm.seek(0)
    data = shm.read(ctypes.sizeof(SPageFileStatic))
    static = SPageFileStatic.from_buffer_copy(data)
    return static

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
        while True:
            p = read_physics(shm_physics)
            g = read_graphics(shm_graphics)
            print(
                f"Speed: {p.speedKmh:6.1f} km/h | "
                f"Gear: {p.gear:2d} | "
                f"RPM: {p.rpms:5d} | "
                f"Gas: {p.gas:.2f} | "
                f"Brake: {p.brake:.2f} | "
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