"""
Tests for analyser.py.
These exercise's: load_lap -> align_by_position ->
compute_deltas -> find_biggest_losses, plus the tyre wear comparison,
against synthetic-but-realistic lap DataFrames (see conftest.py).
"""
import numpy as np
import pandas as pd

from analyser import (
    align_by_position,
    compute_deltas,
    compute_tyre_wear_rate,
    compare_tyre_wear,
    find_biggest_losses,
)


class TestAlignByPosition:
    def test_output_length_matches_num_points(self, fast_lap_df, slow_lap_df):
        cp, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(
            fast_lap_df, slow_lap_df, num_points=500
        )
        assert len(cp) == 500
        assert len(lap_times) == len(cp)
        assert len(ghost_times) == len(cp)

    def test_elapsed_time_is_rebased_to_zero_at_overlap_start(self, fast_lap_df, slow_lap_df):
        """
        Both laps elapsed time must start at 0 at the beginning of the
        common (overlapping) position range - not at each recording's
        own first frame - otherwise laps that start recording at
        different points on track produce a biased comparison.
        """
        cp, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(fast_lap_df, slow_lap_df)
        assert lap_times[0] == 0.0
        assert ghost_times[0] == 0.0

    def test_restricts_to_overlapping_position_range(self, fast_lap_df, partial_coverage_lap_df):
        """
        If one lap only covers positions 0.90-0.99, the common position
        axis must not extend outside that range, even though the other
        lap covers the full track.
        """
        cp, *_ = align_by_position(fast_lap_df, partial_coverage_lap_df)
        assert cp.min() >= partial_coverage_lap_df["position"].min() - 1e-9
        assert cp.max() <= fast_lap_df["position"].max() + 1e-9


class TestComputeDeltas:
    def test_delta_is_elementwise_difference(self):
        lap_times = np.array([0.0, 1.0, 2.0, 3.0])
        ghost_times = np.array([0.0, 0.8, 1.9, 2.7])
        delta = compute_deltas(lap_times, ghost_times)
        assert np.allclose(delta, [0.0, 0.2, 0.1, 0.3])

    def test_slower_lap_has_positive_final_delta(self, fast_lap_df, slow_lap_df):
        """fast_lap_df (80s) vs slow_lap_df (85s) as ghost: the 'lap' here
        is actually the ghost's ghost - flip roles so the ghost (fast) is
        the reference and confirm the slower lap ends up behind it."""
        cp, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(slow_lap_df, fast_lap_df)
        delta = compute_deltas(lap_times, ghost_times)
        assert delta[-1] > 0


class TestFindBiggestLosses:
    def test_returns_at_most_top_n_segments(self):
        common_positions = np.linspace(0, 1, 200)
        # a delta that ramps up steadily (one long, real loss)
        delta = np.linspace(0, 5, 200)
        losses = find_biggest_losses(common_positions, delta, num_segments=20, top_n=3)
        assert len(losses) <= 3

    def test_only_returns_genuine_losses_not_gains(self):
        """
        If a lap is faster than the ghost almost everywhere (delta mostly
        negative/flat), find_biggest_losses must not report negative
        "losses" - a segment where you gained time is not a loss.
        """
        common_positions = np.linspace(0, 1, 200)
        delta = np.linspace(0, -3, 200)  # continuously gaining time, never losing
        losses = find_biggest_losses(common_positions, delta, num_segments=20, top_n=3)
        assert all(time_lost > 0 for _, time_lost in losses)

    def test_identifies_the_segment_with_the_real_spike(self):
        """
        A single sharp ramp in delta - fully contained within one segment,
        flat everywhere else - should be identified as the top loss, with
        its reported position falling within that segment.
        """
        n = 200  # 20 segments of 10 points each
        common_positions = np.linspace(0, 1, n)
        delta = np.zeros(n)
        ramp_segment = 9  # points 90-99
        start, end = ramp_segment * 10, ramp_segment * 10 + 10
        delta[start:end] = np.linspace(0, 2.0, end - start)  # ramps up inside this segment...
        delta[end:] = 2.0  # ...and stays there for the rest of the lap

        losses = find_biggest_losses(common_positions, delta, num_segments=20, top_n=1)

        assert len(losses) == 1
        position, time_lost = losses[0]
        assert 0.44 < position < 0.51  # segment 9 starts at position 90/200 = 0.45
        assert time_lost > 0


class TestTyreWear:
    def test_compute_tyre_wear_rate_is_start_minus_end(self, fast_lap_df):
        rates = compute_tyre_wear_rate(fast_lap_df)
        expected_fl = fast_lap_df["tyre_wear_fl"].iloc[0] - fast_lap_df["tyre_wear_fl"].iloc[-1]
        assert rates["tyre_wear_fl"] == expected_fl
        assert rates["tyre_wear_fl"] > 0  # wear should decrease start->end, so this is positive

    def test_flags_wheel_wearing_much_faster_than_ghost(self, fast_lap_df, slow_lap_df):
        aggressive_lap = fast_lap_df.copy()
        aggressive_lap["tyre_wear_fl"] = np.linspace(100.0, 80.0, len(aggressive_lap))  # much more wear
        messages = compare_tyre_wear(aggressive_lap, slow_lap_df, threshold_ratio=1.15)
        assert any("front left" in m for m in messages)

    def test_no_warning_when_wear_is_similar(self, fast_lap_df):
        # compare a lap against a near-identical copy of itself
        near_identical = fast_lap_df.copy()
        messages = compare_tyre_wear(fast_lap_df, near_identical, threshold_ratio=1.15)
        assert messages == []
