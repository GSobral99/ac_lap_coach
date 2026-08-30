from capture import connect_physics, connect_graphics, read_physics, read_graphics
import pandas as pd
import numpy as np
from voice import speak
from tracks import get_corner

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
    
    real_losses = [l for l in losses_per_segment if l[1] > 0]
    return real_losses[:top_n]

from tracks import get_corner, get_corner_range

def generate_feedback_messages(losses, common_positions=None, delta=None, track_name=None):
    messages = []
    for position, time_lost in losses:
        corner, inside_corner = get_corner(track_name, position)

        if corner is None:
            location = f"the {position * 100:.0f} percent of the lap"
            message = f"You lost {time_lost:.1f} seconds at {location}"

        elif inside_corner:
            label = None
            corner_range = get_corner_range(track_name, corner)
            if corner_range and common_positions is not None and delta is not None:
                label = classify_loss_within_corner(common_positions, delta, corner_range[0], corner_range[1])

            if label:
                message = f"You lost {time_lost:.1f} seconds {label} turn {corner}"
            else:
                message = f"You lost {time_lost:.1f} seconds at turn {corner}"

        else:
            message = f"You lost {time_lost:.1f} seconds before turn {corner}"

        messages.append(message)
    return messages

def compute_tyre_wear_rate(lap_df):
    """
    Devolve o desgaste total (em pontos) de cada roda ao longo da volta,
    do início ao fim.
    """
    wheels = ["tyre_wear_fl", "tyre_wear_fr", "tyre_wear_rl", "tyre_wear_rr"]
    wear_rates = {}
    
    for wheel in wheels:
        start_wear = lap_df[wheel].iloc[0]
        end_wear = lap_df[wheel].iloc[-1]
        wear_rates[wheel] = start_wear - end_wear  # positivo = desgastou
    
    return wear_rates

def compare_tyre_wear(lap_df, ghost_df, threshold_ratio=1.15):
    """
    Compara a taxa de desgaste da volta atual com a da ghost.
    Devolve mensagens de aviso se alguma roda estiver a gastar
    significativamente mais rápido (threshold_ratio = quanto mais, ex: 1.3 = 30% mais).
    """
    lap_wear = compute_tyre_wear_rate(lap_df)
    ghost_wear = compute_tyre_wear_rate(ghost_df)
    
    wheel_labels = {
        "tyre_wear_fl": "front left",
        "tyre_wear_fr": "front right",
        "tyre_wear_rl": "rear left",
        "tyre_wear_rr": "rear right",
    }
    
    messages = []
    for wheel, label in wheel_labels.items():
        if ghost_wear[wheel] > 0 and lap_wear[wheel] > ghost_wear[wheel] * threshold_ratio:
            messages.append(f"You're wearing your {label} tyre faster than usual")
    
    return messages


def classify_loss_within_corner(common_positions, delta, corner_start, corner_end):
    """
    Given a corner's (start, end) range, determines whether most time
    was lost in the first half (entry) or second half (exit).
    Returns "entering", "exiting", or None if there isn't enough data
    inside the range to tell.
    """
    mid = (corner_start + corner_end) / 2

    entry_mask = (common_positions >= corner_start) & (common_positions < mid)
    exit_mask = (common_positions >= mid) & (common_positions < corner_end)

    if not entry_mask.any() or not exit_mask.any():
        return None

    entry_delta_change = delta[entry_mask][-1] - delta[entry_mask][0]
    exit_delta_change = delta[exit_mask][-1] - delta[exit_mask][0]

    if entry_delta_change > exit_delta_change:
        return "entering"
    else:
        return "exiting"
    
    
if __name__ == "__main__":
    lap = load_lap("data/lap_5.csv")
    ghost = load_lap("data/lap_1.csv")
    
    common_pos, lap_times, lap_speeds, ghost_times, ghost_speeds = align_by_position(lap, ghost)
    delta = compute_deltas(lap_times, ghost_times)
    losses = find_biggest_losses(common_pos, delta)
    
    messages = generate_feedback_messages(losses, track_name="acf_portimao")
    speak(messages)