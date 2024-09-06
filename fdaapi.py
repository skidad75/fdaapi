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
def get_modalities_with_events(limit=10):
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
    
    return [item['term'] for item in data['results']][:10]  # Limit to first 10 results

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

# Fetch and cache modalities with adverse events (limited to 10)
modalities = get_modalities_with_events()

# Create modality dropdown
selected_modality = st.selectbox("Select modality:", modalities)

limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

if st.button("Get Device Events"):
    if selected_modality:
        events = get_device_events(selected_modality, limit)
        if 'results' in events and events['results']:
            data = []
            for event in events['results']:
                data.append({
                    "Event ID": event['event_key'],
                    "Date of Event": event.get('date_of_event', 'Not specified'),
                    "Product Problems": ', '.join(event.get('product_problems', ['Not specified'])),
                    "Event Type": ', '.join(event.get('event_type', ['Not specified'])),
                    "Manufacturer": event.get('manufacturer', {}).get('name', ['Not specified'])[0],
                    "Brand Name": event.get('device', [{}])[0].get('brand_name', 'Not specified'),
                    "Generic Name": event.get('device', [{}])[0].get('generic_name', 'Not specified')
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning(f"No events found for the specified modality.")
    else:
        st.warning("Please select a modality.")

# ... existing code ...
