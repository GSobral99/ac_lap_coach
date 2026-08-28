"""
(ENGLISH)
Manual corner maps for each track, so lap-loss feedback can reference
a corner number instead of a raw percentage of the lap.

Assetto Corsa's shared memory does not expose "which corner am I in",
only `normalizedCarPosition` (0.0 to 1.0). So each track's corners are
defined here by hand, as (start, end, corner_number) ranges over that
same 0.0-1.0 axis.

The key used in TRACKS must match exactly the string the game reports
in the static block (`static_data.track`, printed by main.py/capture.py
as [DEBUG] Track read from static block). If your feedback keeps
falling back to percentages, the key is probably wrong - print it once
and copy it here.

To add/tune a track: drive a lap, look at the position where you enter
and exit each corner (recorder.py's CSVs have a "position" column), and
fill in the ranges below. Ranges don't need to touch (straights are the
gaps in between) but shouldn't overlap.
"""

"""
(PORTUGUÊS)
Mapas manuais de curvas para cada pista, para que o feedback de perdas
de tempo indique o número da curva em vez de uma percentagem crua da volta.

A shared memory do Assetto Corsa não expõe "em que curva estou", só
`normalizedCarPosition` (0.0 a 1.0). Por isso as curvas de cada pista
são definidas aqui à mão, como intervalos (start, end, numero_da_curva)
nesse mesmo eixo 0.0-1.0.

A chave usada em TRACKS tem de corresponder exatamente à string que o
jogo devolve no bloco static (`static_data.track`, impresso pelo
main.py/capture.py como [DEBUG] Track read from static block). Se o
feedback continuar a cair para percentagens, a chave provavelmente
está errada - imprime-a uma vez e copia para aqui.

Para adicionar/afinar uma pista: dá uma volta, vê a posição onde entras
e sais de cada curva (os CSVs do recorder.py têm uma coluna "position"),
e preenche os intervalos abaixo. Os intervalos não precisam de se tocar
(as retas são os espaços entre eles) mas não se devem sobrepor.
"""

# TODO: confirm these ranges against real lap data - they are placeholders
# to get the structure working, not measured corner-by-corner yet.
TRACKS = {
    "acf_portimao": [
    (0.0648, 0.1048, 1),
    (0.1021, 0.1421, 2),
    (0.1342, 0.1742, 3),
    (0.1582, 0.1982, 4),
    (0.2890, 0.3290, 5),
    (0.3308, 0.3708, 6),
    (0.3829, 0.4229, 7),
    (0.3986, 0.4386, 8),
    (0.4234, 0.4634, 9),
    (0.4979, 0.5379, 10),
    (0.5676, 0.6076, 11),
    (0.6012, 0.6412, 12),
    (0.6658, 0.7058, 13),
    (0.7094, 0.7494, 14),
    (0.7957, 0.8357, 15),
    ],
    "monza": [
    (0.1623 - 0.02, 0.1623 + 0.02, 1),
    (0.1988 - 0.02, 0.1988 + 0.02, 2),
    (0.2517 - 0.02, 0.2517 + 0.02, 3),
    (0.3712 - 0.02, 0.3712 + 0.02, 4),
    (0.3920 - 0.02, 0.3920 + 0.02, 5),
    (0.4427 - 0.02, 0.4427 + 0.02, 6),
    (0.4974 - 0.02, 0.4974 + 0.02, 7),
    (0.6829 - 0.02, 0.6829 + 0.02, 8),
    (0.7011 - 0.02, 0.7011 + 0.02, 9),
    (0.7319 - 0.02, 0.7319 + 0.02, 10),
    (0.9029 - 0.02, 0.9029 + 0.02, 11),
    ],
}


def get_corner(track_name, position):
    """
    Returns (corner_number, inside_corner) for a normalized track position.

    - If the position falls inside a defined corner range: (number, True).
    - If it falls on a straight, between corners: (number of the NEXT
      corner, False) - useful to say "lost time before Turn N".
    - If the track isn't in TRACKS, or position is past the last corner:
      (None, False).
    """
    corners = TRACKS.get(track_name)
    if not corners:
        return None, False

    for start, end, number in corners:
        if start <= position < end:
            return number, True

    upcoming = [c for c in corners if c[0] > position]
    if upcoming:
        next_corner = min(upcoming, key=lambda c: c[0])
        return next_corner[2], False

    return None, False