"""
Tests for analyser.load_lap(), split into its own file since it needs
to write a real CSV to disk.
"""
from analyser import load_lap


class TestLoadLap:
    def test_trims_frames_that_leak_from_the_next_lap(self, wraparound_lap_df, tmp_path):
        """
        wraparound_lap_df has two extra rows at the end where position
        drops back near 0.0 (the next lap bleeding into this recording).
        load_lap() must cut those off before any analysis touches them.
        """
        csv_path = tmp_path / "lap_leaky.csv"
        wraparound_lap_df.to_csv(csv_path, index=False)

        clean = load_lap(csv_path)

        assert len(clean) == len(wraparound_lap_df) - 2
        # position must now be monotonically non-decreasing throughout
        assert (clean["position"].diff().dropna() >= 0).all()

    def test_leaves_a_clean_lap_untouched(self, fast_lap_df, tmp_path):
        csv_path = tmp_path / "lap_clean.csv"
        fast_lap_df.to_csv(csv_path, index=False)

        clean = load_lap(csv_path)

        assert len(clean) == len(fast_lap_df)
