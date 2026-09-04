"""
Tests for tracks.py.
Uses a small fake entry patched into TRACKS instead of relying on the
real Monza/Portimao calibration, so these tests stay stable even if
that calibration data changes.
"""
import pytest

import tracks


@pytest.fixture(autouse=True)
def fake_track(monkeypatch):
    monkeypatch.setitem(tracks.TRACKS, "fake_track", [
        (0.10, 0.14, 1),
        (0.40, 0.46, 2),
        (0.80, 0.85, 3),
    ])


class TestGetCorner:
    def test_position_inside_a_corner_returns_its_number_and_true(self):
        number, inside = tracks.get_corner("fake_track", 0.12)
        assert number == 1
        assert inside is True

    def test_position_on_a_straight_returns_next_corner_and_false(self):
        """Between Turn 1 (ends 0.14) and Turn 2 (starts 0.40), 0.20 should
        point forward at Turn 2, flagged as "not inside" (i.e. "before")."""
        number, inside = tracks.get_corner("fake_track", 0.20)
        assert number == 2
        assert inside is False

    def test_position_past_the_last_corner_returns_none(self):
        number, inside = tracks.get_corner("fake_track", 0.95)
        assert number is None
        assert inside is False

    def test_unknown_track_returns_none(self):
        number, inside = tracks.get_corner("some_track_never_calibrated", 0.50)
        assert number is None
        assert inside is False


class TestGetCornerRange:
    def test_returns_the_range_for_a_known_corner(self):
        assert tracks.get_corner_range("fake_track", 2) == (0.40, 0.46)

    def test_returns_none_for_a_corner_number_that_does_not_exist(self):
        assert tracks.get_corner_range("fake_track", 99) is None

    def test_returns_none_for_unknown_track(self):
        assert tracks.get_corner_range("some_track_never_calibrated", 1) is None
