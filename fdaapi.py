import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# Global variables for rate limiting
REQUESTS_PER_MINUTE = 240
REQUESTS_PER_DAY = 120000
last_request_time = time.time()
daily_request_count = 0
last_reset_date = datetime.now().date()

def check_rate_limit():
    global last_request_time, daily_request_count, last_reset_date
    current_time = time.time()
    current_date = datetime.now().date()

    # Reset daily count if it's a new day
    if current_date > last_reset_date:
        daily_request_count = 0
        last_reset_date = current_date

    # Check if we've exceeded daily limit
    if daily_request_count >= REQUESTS_PER_DAY:
        st.error("Daily API request limit reached. Please try again tomorrow.")
        return False

    # Ensure we don't exceed requests per minute
    if current_time - last_request_time < 60 / REQUESTS_PER_MINUTE:
        time.sleep(60 / REQUESTS_PER_MINUTE - (current_time - last_request_time))

    last_request_time = time.time()
    daily_request_count += 1
    return True

@st.cache_data(ttl=3600)
def get_api_data(field, limit=10):
    if not check_rate_limit():
        return []

    url = "https://api.fda.gov/device/event.json"
    params = {
        "api_key": "FmMZcDlQm1SHtM2uXegetgdRueXrulaWS1liIegh",
        "count": field,
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        st.error(f"API request failed with status code {response.status_code}")
        return []
    
    data = response.json()
    if 'results' not in data:
        st.warning(f"No results found for {field}")
        return []
    
    return [item['term'] for item in data['results']][:10]  # Limit to first 10 results

@st.cache_data(ttl=3600)
def get_modalities_with_events(limit=100):
    if not check_rate_limit():
        return []

    url = "https://api.fda.gov/device/event.json"
    params = {
        "api_key": "FmMZcDlQm1SHtM2uXegetgdRueXrulaWS1liIegh",
        "count": "device.generic_name.exact",
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        st.error(f"API request failed with status code {response.status_code}")
        return []
    
    data = response.json()
    if 'results' not in data:
        st.warning("No modalities found with adverse events")
        return []
    
    return [item['term'] for item in data['results']]

def get_device_events(modality, limit=10):
    if not check_rate_limit():
        return {}

    url = "https://api.fda.gov/device/event.json"
    
    params = {
        "api_key": "FmMZcDlQm1SHtM2uXegetgdRueXrulaWS1liIegh",
        "search": f"device.generic_name:'{modality}'",
        "limit": limit
    }

    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        st.error(f"API request failed with status code {response.status_code}")
        return {}
    
    return response.json()

st.title("FDA Device Adverse Events")

# Fetch and cache modalities with adverse events (increased limit to 100)
modalities = get_modalities_with_events(100)

# Create modality dropdown with search functionality
selected_modality = st.selectbox("Select modality:", modalities, index=None, placeholder="Search for a modality...")

limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

if st.button("Get Device Events"):
    if selected_modality:
        with st.spinner("Fetching device events..."):
            events = get_device_events(selected_modality, limit)
        if 'results' in events and events['results']:
            data = []
            for event in events['results']:
                # Determine severity based on event type
                severity = "Low"
                event_types = event.get('event_type', [])
                if "Death" in event_types:
                    severity = "High"
                elif "Injury" in event_types or "Malfunction" in event_types:
                    severity = "Medium"

                data.append({
                    "Event ID": event['event_key'],
                    "Date of Event": event.get('date_of_event', 'Not specified'),
                    "Product Problems": ', '.join(event.get('product_problems', ['Not specified'])),
                    "Event Type": ', '.join(event_types),
                    "Severity": severity,
                    "Manufacturer": event.get('manufacturer', {}).get('name', ['Not specified'])[0],
                    "Brand Name": event.get('device', [{}])[0].get('brand_name', 'Not specified'),
                    "Generic Name": event.get('device', [{}])[0].get('generic_name', 'Not specified')
                })
            
            df = pd.DataFrame(data)
            
            # Color-code severity
            def color_severity(val):
                if val == "High":
                    return 'background-color: #FFCCCB'
                elif val == "Medium":
                    return 'background-color: #FFFFA1'
                else:
                    return 'background-color: #90EE90'

            styled_df = df.style.applymap(color_severity, subset=['Severity'])
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Add download button for CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{selected_modality}_events.csv",
                mime="text/csv",
            )
        else:
            st.warning(f"No events found for the specified modality.")
    else:
        st.warning("Please select a modality.")

# Add footer with API information
st.markdown("---")
st.markdown("Data provided by the [FDA Adverse Event Reporting System API](https://open.fda.gov/apis/device/event/)")