"""
Tests for recorder.py.
record_frame() takes physics/graphics objects as read from AC's shared
memory (via capture.py). We don't touch the real shared memory here.
"""
import os

from recorder import (
    record_frame,
    start_recording,
    create_session_folder,
    save_lap_to_csv,
    find_best_lap,
)


class FakePhysics:
    def __init__(self, speed=120.0, gas=0.8, brake=0.0, gear=4, tyre_wear=(98.0, 97.5, 98.2, 97.8)):
        self.speedKmh = speed
        self.gas = gas
        self.brake = brake
        self.gear = gear
        self.tyreWear = tyre_wear


class FakeGraphics:
    def __init__(self, position=0.5):
        self.normalizedCarPosition = position


class TestRecordFrame:
    def test_returns_expected_keys(self):
        frame = record_frame(FakePhysics(), FakeGraphics())
        expected_keys = {"position", "speed", "gas", "brake", "gear", "timestamp"}
        assert expected_keys.issubset(frame.keys())

    def test_values_come_from_the_right_source(self):
        physics = FakePhysics(speed=250.0, gear=6)
        graphics = FakeGraphics(position=0.73)
        frame = record_frame(physics, graphics)
        assert frame["speed"] == 250.0
        assert frame["gear"] == 6
        assert frame["position"] == 0.73


class TestStartRecording:
    def test_returns_an_empty_list(self):
        assert start_recording() == []


class TestCreateSessionFolder:
    def test_creates_a_directory_named_after_the_track(self, tmp_path):
        session_folder = create_session_folder("monza", base_folder=str(tmp_path))
        assert os.path.isdir(session_folder)
        assert "monza" in os.path.basename(session_folder)


class TestFindBestLap:
    def test_picks_the_fastest_lap_among_valid_candidates(self, tmp_path, fast_lap_df, slow_lap_df):
        session_folder = str(tmp_path)
        save_lap_to_csv(fast_lap_df.to_dict("records"), 1, session_folder, lap_time_ms=80_000)
        save_lap_to_csv(slow_lap_df.to_dict("records"), 2, session_folder, lap_time_ms=85_000)

        best_file, best_duration = find_best_lap(session_folder)

        assert best_file.endswith("lap_1.csv")
        assert best_duration == 80.0

    def test_ignores_laps_with_insufficient_track_coverage(self, tmp_path, partial_coverage_lap_df, slow_lap_df):
        """
        partial_coverage_lap_df only spans position 0.90-0.99 (~9% of the
        track) but has a very fast lap_time_ms - it must NOT be picked as
        the ghost over a full lap, it doesn't matter if it has less time.
        """
        session_folder = str(tmp_path)
        save_lap_to_csv(partial_coverage_lap_df.to_dict("records"), 1, session_folder, lap_time_ms=8_000)
        save_lap_to_csv(slow_lap_df.to_dict("records"), 2, session_folder, lap_time_ms=85_000)

        best_file, best_duration = find_best_lap(session_folder, min_coverage=0.85)

        assert best_file.endswith("lap_2.csv")

    def test_returns_none_when_no_lap_has_enough_coverage(self, tmp_path, partial_coverage_lap_df):
        session_folder = str(tmp_path)
        save_lap_to_csv(partial_coverage_lap_df.to_dict("records"), 1, session_folder, lap_time_ms=8_000)

        best_file, best_duration = find_best_lap(session_folder, min_coverage=0.85)

        assert best_file is None
        assert best_duration is None
