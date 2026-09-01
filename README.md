# AC Lap Coach

A telemetry-based lap coach for Assetto Corsa Classic. It reads live car data straight from the game's shared memory, records completed laps, compares your current lap with personal best (so called "ghost" lap), and speaks out where you lost time.

Built as a portfolio project to demonstrate real-time data capture, signal processing (interpolation-based lap alignment), and systems-level debugging

## What it does

1. **Captures** live telemetry (speed, throttle, brake, gear, track position, tyre wear/temperature) from Assetto Corsa via its shared memory API.
2. **Records** each completed lap to a CSV file.
3. **Identifies** your fastest recorded lap as a reference ("ghost") - only among laps that actually cover most of the track (see below).
4. **Compares** any lap against the ghost by aligning both on track position (not time), using linear interpolation to handle laps with different frame counts and timestamps.
5. **Finds** the track segments where the most time was lost, labelled by corner number where the track has been calibrated (e.g. "entering Turn 4"), or by lap percentage otherwise.
6. **Compares tyre wear** per wheel against the ghost lap, and flags wheels wearing noticeably faster than usual.
7. **Speaks** all of this feedback out loud after each lap.

## Architecture

```
src/
├── capture.py    # Connects to and reads AC shared memory (physics + graphics + static)
├── recorder.py   # Records completed laps to CSV, finds the fastest valid lap
├── analyser.py   # Aligns laps by position, computes time/tyre deltas, finds losses
└── voice.py      # Text-to-speech feedback
tracks.py                  # Per-track corner number lookup by normalized position
parse_ai_spline.py         # Detects corner apexes from a track's fast_lane.ai file
calibrate_corners.py       # Sweeps detection parameters to match a known corner count
test_corner_calling.py     # Live sanity check: speaks "Turn N" as you enter each corner
main.py                    # Ties it all together into a live coaching loop
```

Each module has a single responsibility: `capture.py` only knows how to read shared memory, `recorder.py` only knows how to persist and select laps, `analyser.py` only works with already-recorded data (no live dependency), and `voice.py` only knows how to speak.

## How it works - the interesting bits

**Reading the game's memory directly.** Assetto Corsa exposes live telemetry through named shared memory blocks (`Local\acpmf_physics`, `Local\acpmf_graphics`, `Local\acpmf_static`). This project reads them with `ctypes` and `mmap`, mapping the raw byte layout to Python structs that mirror Kunos' official C++ definitions.

**Comparing laps by position.** Two laps never have the same number of samples or the same timestamps, so you can't compare "frame 50 of lap A" to "frame 50 of lap B" directly. Instead, both laps are resampled onto a shared axis of normalized track position using `numpy.interp`, which lets you ask "what was my elapsed time/speed at 43% of the track?" even if that exact point wasn't recorded.

**Handling messy real-world data.** A few edge cases had to be handled explicitly:
- Laps can start partway through a session, so the two laps being compared don't always cover the same range of track position - the analysis is restricted to the overlapping range only, and both laps' elapsed time is rebased to zero at the start of that overlap so the comparison stays fair regardless of where each recording began.
- **A lap can't become the ghost unless it covers most of the track.** In Hotlap mode especially, the very first lap recorded after launching the tool is really just the warm-up stretch from wherever the car started to the start/finish line - `completedLaps` only ticks over once you actually cross the line, but recording starts as soon as the script connects. That "lap" might only cover 10-15% of the track, and comparing against it produces meaningless deltas concentrated in a tiny sliver of the lap. `find_best_lap()` now requires a minimum position coverage (`position.max() - position.min() >= 0.85` by default) for a lap to even be considered as a ghost candidate, regardless of how fast its recorded time looks. This isn't Hotlap-specific - the same guard also protects against any lap whose recording started late for other reasons (off-track resets, restarting the script mid-session, etc.), since the check is about actual data coverage, not which lap number it happens to be.
- The position value wraps from ~1.0 back to 0.0 at the start/finish line, and a couple of frames from the *next* lap can bleed into the end of a recording - these are trimmed before interpolation.
- Time deltas are computed from *elapsed time since the start of each lap*, not absolute system time - otherwise two laps recorded minutes apart would show meaningless multi-minute "deltas".
- Lap duration used to pick the fastest lap comes straight from the game's own `iLastTime` field, not from recomputing it off recorded timestamps - a lap whose recording started mid-track would otherwise look artificially short.

**Detecting corners automatically from the track file.** Rather than hand-guessing where each corner is, `parse_ai_spline.py` parses the track's `fast_lane.ai` file (the AI racing line Assetto Corsa ships with every track) and reads the corner radius the game itself computed at every point along the line. It treats curvature (1/radius) as a signal and finds its local peaks with `scipy.signal.find_peaks` - each peak is a corner apex. This gives one entry per real corner regardless of how tight or wide it is, without depending on any one driver's braking habits.

**Entry vs. exit within a corner.** For a lap's biggest losses that fall inside a calibrated corner, the feedback also says whether the time was lost on the way in or the way out (e.g. "lost 1.1 seconds exiting Turn 4"), by comparing how much the time delta grew in the first half of the corner's position range versus the second half.

**Tyre wear feedback.** Each wheel's wear rate (start-of-lap wear minus end-of-lap wear) is compared against the ghost lap's wear rate; a wheel wearing noticeably faster than in the ghost lap (by a configurable ratio) gets flagged by name (e.g. "you're wearing your front left tyre faster than usual"). Note: this was tuned and tested with the session's tyre wear rate multiplier set to 3x for faster iteration - the comparison ratio may need recalibrating for realistic (1x) wear rates, where lap-to-lap variation is smaller.

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

## Usage

1. Launch Assetto Corsa and get on track.
2. Run:
```bash
   python main.py
```
3. Drive. Each completed lap is recorded automatically. Once there's a valid ghost lap (see the coverage requirement above - this usually means from your second or third lap onward), you'll hear spoken feedback comparing your lap to it.

### Running components individually

For debugging or testing a single piece:
```bash
python src/capture.py    # print live telemetry
python src/recorder.py   # record laps without live comparison
python src/analyser.py   # compare two specific saved laps
```

## Adding corner names for a new track

By default, feedback refers to positions as a percentage of the lap (e.g. "at 43 percent of the lap"). To get corner numbers instead (e.g. "at Turn 5"), a track needs to be calibrated once and added to `tracks.py`. This is a three-step process:

**1. Detect corner apexes from the track's AI file.**

Every track ships with a `fast_lane.ai` file under its Steam install folder (`.../assettocorsa/content/tracks/<track>/ai/fast_lane.ai`). Look up how many corners the track officially has, then find detection parameters that match that count:

```bash
python calibrate_corners.py "<path to fast_lane.ai>" <known_corner_count>
```

This sweeps a grid of `prominence_radius` / `min_apex_gap_m` combinations and prints every combination that detects exactly that many corners. Pick one from the middle of the list (extremes tend to be less stable), then run:

```bash
python parse_ai_spline.py "<path to fast_lane.ai>" <prominence_radius> <track_key> <min_apex_gap_m>
```

This prints a ready-to-paste list of `(position, corner_number)` apexes.

**2. Turn apexes into ranges and add them to `tracks.py`.**

`tracks.py` looks up corners by *range* (start, end, number), not by single point, since your car spends a few dozen meters inside each corner. Convert each apex into a small range around it (e.g. ±0.02) and add it under a new key in `TRACKS`. The key must exactly match the string AC reports in the static block - run `main.py` once and check the `[DEBUG] Track read from static block` line, or read it directly with `capture.py`'s `connect_static`/`read_static`.

If two corners are very close together (a chicane, or a fast technical sequence), a fixed ±0.02 margin can make their ranges overlap, which makes the closer-numbered one always win. If that happens, narrow the margins for just those corners, or treat the sequence as a single named zone rather than separate turns.

Known limitation: corner ranges don't wrap around the start/finish line, so positions just after the last mapped corner (e.g. the final 5-10% of the lap, after the last turn but before crossing the line) fall back to percentage-based feedback instead of naming the upcoming Turn 1.

**3. Test it on track before trusting it.**

Corner detection is based on track curvature, not on how you actually drive - and the apex-to-range conversion is a rough approximation, not something the game confirms. **Always verify a new track's calibration by actually driving it** before relying on the spoken feedback:

```bash
python test_corner_calling.py
```

This connects live and speaks "Turn N" the moment your position enters a corner's range, without recording or comparing laps - just drive a lap and listen for whether the callout lines up with when you actually turn in. If a corner is announced early, late, not at all, or the wrong number entirely, that corner's range needs adjusting in `tracks.py`. This has already caught real issues during development (overlapping ranges in a tight sequence of corners) - don't skip this step for a track you haven't verified yet.

## Status

- [x] Shared memory capture (physics + graphics + static)
- [x] Lap recording to CSV
- [x] Fastest *valid* lap detection (uses the game's own lap time, and requires minimum track coverage)
- [x] Position-aligned lap comparison
- [x] Spoken feedback
- [x] Add and update code comments to English
- [x] Live integration (`main.py`) - record, compare, and speak automatically without manual steps between phases
- [x] Automatic corner detection from track AI files, with live on-track verification tool
- [x] Entry/exit classification within a corner
- [x] Tyre wear feedback (per-wheel, relative to ghost lap)
- [ ] Live phone dashboard (Streamlit, read-only view of live telemetry + last lap summary over local network)
- [ ] Post-session dashboard (delta graph, track map coloured by time gained/lost)
- [ ] Recalibrate tyre wear thresholds against realistic (1x) wear rate
- [ ] Corner ranges that wrap around the start/finish line

## Notes

Commercial and open-source AC coaching tools already exist (Simulator-Controller/Jona, PitWise, Grognaks Race Engineer, among others). This project isn't trying to replace them - it's a from-scratch exploration of the underlying problem (shared memory parsing, signal alignment, real-time systems) built to demonstrate engineering depth for automotive/motorsport-adjacent roles.