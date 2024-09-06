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

def get_api_data(field, limit=1000):
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
    
    return [item['term'] for item in data['results']]

def get_device_events(modality, device_type, limit=10):
    if not check_rate_limit():
        return {}

    url = "https://api.fda.gov/device/event.json"
    
    params = {
        "api_key": "FmMZcDlQm1SHtM2uXegetgdRueXrulaWS1liIegh",
        "search": f"device.generic_name:'{modality}' AND device.device_class:'{device_type}'",
        "limit": limit
    }

    response = requests.get(url, params=params)
    return response.json()

st.title("FDA Device Adverse Events")

# Fetch options for dropdowns
modalities = get_api_data("device.generic_name.exact")
device_types = get_api_data("device.device_class")

# Create dropdowns
selected_modality = st.selectbox("Select modality:", modalities)
selected_device_type = st.selectbox("Select device type:", device_types)

limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

if st.button("Get Device Events"):
    if selected_modality and selected_device_type:
        events = get_device_events(selected_modality, selected_device_type, limit)
        if 'results' in events:
            data = []
            for event in events['results']:
                data.append({
                    "Event ID": event['event_key'],
                    "Date of Event": event['date_of_event'],
                    "Product Problems": ', '.join(event.get('product_problems', ['Not specified'])),
                    "Event Type": ', '.join(event['event_type']),
                    "Manufacturer": event['manufacturer']['name'][0] if event['manufacturer']['name'] else 'Not specified',
                    "Brand Name": event['device'][0]['brand_name'] if event['device'][0]['brand_name'] else 'Not specified',
                    "Generic Name": event['device'][0]['generic_name'] if event['device'][0]['generic_name'] else 'Not specified'
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.error(f"No events found for the specified modality and device type.")
    else:
        st.warning("Please select both a modality and a device type.")
