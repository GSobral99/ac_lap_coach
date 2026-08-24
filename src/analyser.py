from capture import connect_physics, connect_graphics, read_physics, read_graphics
import pandas as pd
import numpy as np
from voice import speak

def load_lap(filepath):
    df = pd.read_csv(filepath)
    
    drops = df[df["position"].diff() < -0.5].index
    if len(drops) > 0:
        df = df.iloc[:drops[0]]
    return df.reset_index(drop=True)

def align_by_position(lap_df, ghost_df, num_points=1000):
    start = max(lap_df["position"].min(), ghost_df["position"].min())
    end = min(lap_df["position"].max(), ghost_df["position"].max())
    
    cp = np.linspace(start, end, num_points)

    lap_elapsed = lap_df["timestamp"] - lap_df["timestamp"].iloc[0]
    ghost_elapsed = ghost_df["timestamp"] - ghost_df["timestamp"].iloc[0]

    lap_times = np.interp(cp, lap_df["position"], lap_elapsed)
    lap_speeds = np.interp(cp, lap_df["position"], lap_df["speed"])

    ghost_times = np.interp(cp, ghost_df["position"], ghost_elapsed)
    ghost_speeds = np.interp(cp, ghost_df["position"], ghost_df["speed"])

    # NOVO: rebasear ambos para começarem em 0 na entrada da zona de sobreposição
    lap_times = lap_times - lap_times[0]
    ghost_times = ghost_times - ghost_times[0]

    return cp, lap_times, lap_speeds, ghost_times, ghost_speeds

def compute_deltas(lap_times, ghost_times):
    delta = lap_times - ghost_times
    return delta

def find_biggest_losses(common_positions, delta, num_segments=20, top_n=3):
    segment_size = len(delta) // num_segments
    losses_per_segment = []

    for i in range(num_segments):
        start = i * segment_size
        end = start + segment_size
        segment_delta_change = delta[end - 1] - delta[start]
        losses_per_segment.append((common_positions[start], segment_delta_change))

    losses_per_segment.sort(key=lambda x: x[1], reverse=True)
    return losses_per_segment[:top_n]

def generate_feedback_messages(losses):
    messages = []
    for position, time_lost in losses:
        percent = position * 100
        message = f"You lost {time_lost:.1f} seconds in the {percent:.0f} percent of the lap"
        messages.append(message)
    return messages

if __name__ == "__main__":
    lap = load_lap("data/lap_5.csv")
    ghost = load_lap("data/lap_1.csv")
    
    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    losses = find_biggest_losses(common_pos, delta)
    
    messages = generate_feedback_messages(losses)
    speak(messages)