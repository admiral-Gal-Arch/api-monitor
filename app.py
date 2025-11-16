import os  # <-- ADDED THIS
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title="UptimeRobot Dashboard",
    page_icon="🤖",
    layout="wide"
)

# --- UptimeRobot API Settings ---
API_URL = "https://api.uptimerobot.com/v2/getMonitors"

# --- UPDATED SECTION ---
# This now reads from Render's Environment Variables
API_KEY = os.environ.get("UPTIMEROBOT_API_KEY", "")

# Check if the key was loaded successfully
if not API_KEY:
    st.error("API Key not found. Please check your UPTIMEROBOT_API_KEY environment variable in Render.")
    st.stop()
# --- END UPDATED SECTION ---


# --- Helper Dictionaries & Functions ---

# Map UptimeRobot status codes to human-readable text and icons
STATUS_MAP = {
    0: ("Paused", "⏸️"),
    1: ("Not Checked Yet", "❔"),
    2: ("Up", "✅"),
    8: ("Seems Down", "⚠️"),
    9: ("Down", "🔥"),
}

@st.cache_data(ttl=300)  # Cache data for 5 minutes (300 seconds)
def fetch_uptimerobot_data(api_key):
    """
    Fetches monitor data from the UptimeRobot API.
    """
    payload = {
        "api_key": api_key,
        "format": "json",
        "response_times": 1,         # Include response times
        "custom_uptime_ratios": 1,   # Include 7-day and 30-day uptime
        "logs": 1,                   # Include logs
        "logs_limit": 50             # Limit logs to the most recent 50
    }
    
    try:
        response = requests.post(API_URL, data=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        if data.get("stat") == "ok":
            return data.get("monitors", [])
        else:
            st.error(f"API Error: {data.get('error', 'Unknown error')}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"HTTP Request failed: {e}")
        return None

def process_monitor_data(monitors):
    """
    Processes the raw monitor data for display.
    """
    if not monitors:
        return {}
        
    # Create a dictionary for easy lookup by friendly_name
    monitor_dict = {m['friendly_name']: m for m in monitors}
    return monitor_dict

# --- Main Application ---

st.title("🤖 UptimeRobot Monitor Dashboard")

# Fetch and process data
monitors_list = fetch_uptimerobot_data(API_KEY)
monitors_dict = process_monitor_data(monitors_list)

if not monitors_dict:
    st.warning("No monitor data found or an error occurred.")
    st.stop() # Stop execution if there's no data

# --- Sidebar for Monitor Selection ---
st.sidebar.title("Navigation")
monitor_names = sorted(monitors_dict.keys())
selected_monitor_name = st.sidebar.selectbox(
    "Select a Monitor",
    monitor_names
)

# --- Main Dashboard Area ---
if selected_monitor_name:
    monitor = monitors_dict[selected_monitor_name]
    
    st.header(f"Monitor: {monitor['friendly_name']}")
    st.markdown(f"**URL:** `{monitor['url']}`")

    # --- 1. Key Performance Indicators (KPIs) ---
    status_text, status_icon = STATUS_MAP.get(monitor['status'], ("Unknown", "❓"))
    
    # Get custom uptime ratios (default to 'N/A' if not present)
    uptime_ratios = monitor.get('custom_uptime_ratio', '0-0').split('-')
    uptime_7_day = uptime_ratios[0] if len(uptime_ratios) > 0 else 'N/A'
    uptime_30_day = uptime_ratios[1] if len(uptime_ratios) > 1 else 'N/A'

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Status", f"{status_icon} {status_text}")
    col2.metric("7-Day Uptime", f"{uptime_7_day}%")
    col3.metric("30-Day Uptime", f"{uptime_30_day}%")

    st.divider()

    # --- 2. Response Time Chart ---
    st.subheader("Recent Response Times (ms)")
    if 'response_times' in monitor and monitor['response_times']:
        rt_data = monitor['response_times']
        
        # Convert to DataFrame for charting
        df_rt = pd.DataFrame(rt_data)
        df_rt['datetime'] = pd.to_datetime(df_rt['datetime'], unit='s')
        df_rt = df_rt.rename(columns={'value': 'Response Time (ms)'})
        df_rt = df_rt.set_index('datetime')
        
        st.line_chart(df_rt)
    else:
        st.info("No response time data available for this monitor.")

    # --- 3. Event Logs ---
    st.subheader("Recent Events")
    if 'logs' in monitor and monitor['logs']:
        log_data = monitor['logs']
        
        # Process log data
        processed_logs = []
        for log in log_data:
            log_type, log_icon = STATUS_MAP.get(log['type'], ("Event", "ℹ️"))
            processed_logs.append({
                "Event": f"{log_icon} {log_type}",
                "Timestamp": datetime.fromtimestamp(log['datetime']).strftime('%Y-%m-%d %H:%M:%S'),
                "Details": log.get('reason', {}).get('detail', 'N/A')
            })
        
        df_logs = pd.DataFrame(processed_logs)
        st.dataframe(df_logs, use_container_width=True)
    else:
        st.info("No logs available for this monitor.")

    # --- 4. Raw Data Expander (for debugging) ---
    with st.expander("Show Raw API Data for this Monitor"):
        st.json(monitor)
