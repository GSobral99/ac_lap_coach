# AC Lap Coach

A telemetry-based lap coach for Assetto Corsa Classic. It reads live car data straight from the game's shared memory, records completed laps, compares your current lap with personal best (so called "ghost" lap), and speaks out where you lost time.

Built as a portfolio project to demonstrate real-time data capture, signal processing (interpolation-based lap alignment), and systems-level debugging.

## What it does

1. **Captures** live telemetry (speed, throttle, brake, gear, track position) from Assetto Corsa via its shared memory API.
2. **Records** each completed lap to a CSV file.
3. **Identifies** your fastest recorded lap as a reference ("ghost").
4. **Compares** any lap against the ghost by aligning both on track position (not time), using linear interpolation to handle laps with different frame counts and timestamps.
5. **Finds** the track segments where the most time was lost.
6. **Speaks** the feedback out loud (e.g. "You lost 2.8 seconds at 59 percent of the lap").

## Architecture

```
src/
├── capture.py    # Connects to and reads AC shared memory (physics + graphics)
├── recorder.py   # Records completed laps to CSV, finds the fastest lap
├── analyser.py   # Aligns laps by position, computes time deltas, finds losses
└── voice.py      # Text-to-speech feedback
main.py           # Ties it all together into a live coaching loop
```

Each module has a single responsibility: `capture.py` only knows how to read shared memory, `recorder.py` only knows how to persist and select laps, `analyser.py` only works with already-recorded data (no live dependency), and `voice.py` only knows how to speak.

## How it works — the interesting bits

**Reading the game's memory directly.** Assetto Corsa exposes live telemetry through named shared memory blocks (`Local\acpmf_physics`, `Local\acpmf_graphics`). This project reads them with `ctypes` and `mmap`, mapping the raw byte layout to Python structs that mirror Kunos' official C++ definitions.

**Comparing laps by position** Two laps never have the same number of samples or the same timestamps, so you can't compare "frame 50 of lap A" to "frame 50 of lap B" directly. Instead, both laps are resampled onto a shared axis of normalized track position using `numpy.interp`, which lets ask "what was my elapsed time/speed at 43% of the track?" even if that exact point wasn't recorded.

**Handling messy real-world data.** A few edge cases had to be handled explicitly:
- Laps can start partway through a session, so the two laps being compared don't always cover the same range of track position — the analysis is restricted to the overlapping range only.
- The position value wraps from ~1.0 back to 0.0 at the start/finish line, and a couple of frames from the *next* lap can bleed into the end of a recording — these are trimmed before interpolation.
- Time deltas are computed from *elapsed time since the start of each lap*, not absolute system time — otherwise two laps recorded minutes apart would show meaningless multi-minute "deltas".

**Text-to-speech on Windows.** `pyttsx3` has a known issue on Windows where only the first of several sequential `say()` calls is actually spoken. Rather than fight it, feedback is spoken via a direct call to the Windows SAPI synthesizer through PowerShell (`System.Speech.Synthesis.SpeechSynthesizer`), which is more reliable in this case, where I was having some problems with `pyttsx3`.

## Requirements

- Assetto Corsa (classic, not Competizione)
- Python 3.12+
- Windows (for the SAPI-based voice feedback)

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage (before implementation of main.py)

1. Launch Assetto Corsa and get on track (Practice or Hotlap mode -- not just the menu).
2. Run the recorder to capture laps:
   ```bash
   python src/recorder.py
   ```
3. Drive a few laps. Each completed lap is saved to `data/lap_<n>.csv`.
4. Compare a lap against your best:
   ```bash
   python src/analyser.py
   ```

## Status

- [x] Shared memory capture (physics + graphics)
- [x] Lap recording to CSV
- [x] Fastest lap detection
- [x] Position-aligned lap comparison
- [x] Spoken feedback
- [ ] Add and Update code comments to english
- [ ] Live integration (`main.py`) — record, compare, and speak automatically without manual steps between phases
- [ ] Tyre wear / degradation feedback
- [ ] Post-session dashboard (Streamlit)
- [ ] Update and upgrade for better performance
- [ ] Add extras

## Notes

Commercial and open-source AC coaching tools already exist (Simulator-Controller/Jona, PitWise, Grognaks Race Engineer, among others). This project isn't trying to replace them — it's a from-scratch exploration of the underlying problem (shared memory parsing, signal alignment, real-time systems) built to demonstrate engineering depth for automotive/motorsport-adjacent roles.