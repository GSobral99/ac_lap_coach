"""
Lê dados de telemetria em tempo real do Assetto Corsa
via shared memory (Local\\acpmf_physics).

Requisitos: o Assetto Corsa tem de estar aberto e numa sessão
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


def connect_physics():
    """Abre a shared memory de fisica do AC."""
    shm = mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), "Local\\acpmf_physics")
    return shm


def read_physics(shm):
    """Le a struct atual da shared memory."""
    shm.seek(0)
    data = shm.read(ctypes.sizeof(SPageFilePhysics))
    physics = SPageFilePhysics.from_buffer_copy(data)
    return physics


def main():
    print("A tentar ligar a shared memory do Assetto Corsa...")
    print("(Certifica-te que o AC esta aberto E numa pista, nao so no menu)\n")

    try:
        shm = connect_physics()
    except Exception as e:
        print(f"Erro ao abrir shared memory: {e}")
        print("Verifica se o Assetto Corsa esta a correr.")
        return

    print("Ligado! A ler dados (Ctrl+C para parar)...\n")

    try:
        while True:
            p = read_physics(shm)
            print(
                f"Speed: {p.speedKmh:6.1f} km/h | "
                f"Gear: {p.gear:2d} | "
                f"RPM: {p.rpms:5d} | "
                f"Gas: {p.gas:.2f} | "
                f"Brake: {p.brake:.2f}"
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nParado pelo utilizador.")
    finally:
        shm.close()


if __name__ == "__main__":
    main()