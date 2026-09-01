"""
AC Lap Coach — phone/browser dashboard.

Reads the JSON state files written by main.py while it's running
(data/live_state.json and data/last_lap_summary.json) and displays
them, auto-refreshing periodically.

This is read-only and completely decoupled from main.py — it doesn't
touch the shared memory itself, so it can run on the same PC while
main.py is connected to AC, and be viewed from a phone on the same
Wi-Fi network.

Usage:
    streamlit run dashboard.py --server.address 0.0.0.0

Then on your phone (same Wi-Fi as the PC), open:
    http://<PC's local IP>:8501
"""

import json
import os
import time

import streamlit as st

LIVE_STATE_PATH = "data/live_state.json"
LAP_SUMMARY_PATH = "data/last_lap_summary.json"
REFRESH_SECONDS = 0.5


def load_json_safe(filepath):
    """Reads a JSON file, returns None if it doesn't exist yet or is
    mid-write (main.py writes it many times per second, so an empty/
    partial read is expected occasionally, not an error)."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return None



def format_gear(gear_value):
    if gear_value == 0:
        return "R"
    elif gear_value == 1:
        return "N"
    else:
        return str(gear_value - 1)
    
st.set_page_config(page_title="AC Lap Coach", layout="centered")
st.title("🏁 AC Lap Coach")

tab_live, tab_summary = st.tabs(["Live", "Last Lap"])

with tab_live:
    state = load_json_safe(LIVE_STATE_PATH)

    if state is None:
        st.info("Waiting for data... make sure main.py is running and you're on track.")
    else:
        st.metric("Speed", f"{state['speed']:.0f} km/h")

        col1, col2, col3 = st.columns(3)
        col1.metric("Gear", format_gear(state["gear"]))
        col2.metric("RPM", f"{state['rpm']:.0f}")
        col3.metric("Lap", state["lap"])

        st.progress(min(max(state["position"], 0.0), 1.0), text="Track position")

        col_gas, col_brake = st.columns(2)
        col_gas.metric("Throttle", f"{state['gas'] * 100:.0f}%")
        col_brake.metric("Brake", f"{state['brake'] * 100:.0f}%")

        st.subheader("Tyre temperatures")
        t1, t2 = st.columns(2)
        t1.metric("Front Left", f"{state['tyre_temp_fl']:.0f}°C")
        t1.metric("Rear Left", f"{state['tyre_temp_rl']:.0f}°C")
        t2.metric("Front Right", f"{state['tyre_temp_fr']:.0f}°C")
        t2.metric("Rear Right", f"{state['tyre_temp_rr']:.0f}°C")

with tab_summary:
    summary = load_json_safe(LAP_SUMMARY_PATH)

    if summary is None:
        st.info("No completed lap yet.")
    else:
        st.metric(f"Lap {summary['lap_number']}", f"{summary['lap_time_s']:.2f}s")

        st.subheader("Feedback")
        if summary["messages"]:
            for message in summary["messages"]:
                st.write(f"- {message}")
        else:
            st.write("No losses to report.")

# Auto-refresh: re-runs the whole script after a short pause, which is
# how Streamlit updates without needing a manual page reload.
time.sleep(REFRESH_SECONDS)
st.rerun()