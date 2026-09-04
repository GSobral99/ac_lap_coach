"""
Tests for parse_ai_spline.py.
test_parse_ai_file exercises the real binary format against an actual
file on disk. detect_corner_apexes is
tested against a directly-constructed spline dict
so the corner-detection logic can be verified without
needing a full real fast_lane.ai for every case.
"""
from parse_ai_spline import parse_ai_file, detect_corner_apexes


class TestParseAiFile:
    def test_reads_expected_point_and_extra_counts(self, sample_ai_bytes):
        spline = parse_ai_file(sample_ai_bytes)
        assert spline["version"] == 7
        assert len(spline["points"]) == 3
        assert len(spline["extras"]) == 3
        assert spline["has_grid"] is True

    def test_point_positions_are_read_correctly(self, sample_ai_bytes):
        spline = parse_ai_file(sample_ai_bytes)
        lengths = [p["length"] for p in spline["points"]]
        assert lengths == [0.0, 10.0, 20.0]

    def test_rejects_unsupported_version(self, tmp_path):
        import struct
        bad_file = tmp_path / "bad.ai"
        with open(bad_file, "wb") as f:
            f.write(struct.pack("<i", 3))  # unsupported version
        try:
            parse_ai_file(bad_file)
            assert False, "expected ValueError for unsupported .ai version"
        except ValueError:
            pass


class TestDetectCornerApexes:
    def test_finds_the_one_corner_in_the_sample(self, sample_spline):
        apexes, total_length = detect_corner_apexes(sample_spline, prominence_radius=300.0, min_apex_gap_m=60.0)
        assert len(apexes) >= 1

    def test_apex_position_is_near_the_middle_of_the_track(self, sample_spline):
        apexes, total_length = detect_corner_apexes(sample_spline, prominence_radius=300.0, min_apex_gap_m=60.0)
        position, radius = apexes[0]
        assert 0.4 < position < 0.6

    def test_straight_track_has_no_corners(self, straight_spline):
        apexes, total_length = detect_corner_apexes(straight_spline, prominence_radius=300.0, min_apex_gap_m=60.0)
        assert apexes == []
