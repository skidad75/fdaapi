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

@st.cache_data(ttl=3600)
def get_high_severity_events(limit=100):
    if not check_rate_limit():
        return []

    url = "https://api.fda.gov/device/event.json"
    params = {
        "api_key": "FmMZcDlQm1SHtM2uXegetgdRueXrulaWS1liIegh",
        "search": "event_type:death",
        "limit": limit
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        st.error(f"API request failed with status code {response.status_code}")
        return []
    
    data = response.json()
    if 'results' not in data:
        st.warning("No high severity events found")
        return []
    
    return data['results']

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

# Create tabs for different features
tab1, tab2 = st.tabs(["Modality-specific Events", "High Severity Events"])

with tab1:
    # Fetch and cache modalities with adverse events (increased limit to 100)
    modalities = get_modalities_with_events(100)

    # Create modality dropdown with search functionality
    selected_modality = st.selectbox("Select modality:", modalities, index=None, placeholder="Search for a modality...")

    limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

    # Add severity filter
    severity_options = ["All", "High", "Medium", "Low"]
    selected_severity = st.selectbox("Filter by severity:", severity_options)

    if st.button("Get Device Events"):
        if selected_modality:
            with st.spinner("Fetching device events..."):
                events = get_device_events(selected_modality, limit)
            if 'results' in events and events['results']:
                data = []
                manufacturers = set()
                for event in events['results']:
                    # Determine severity based on event type
                    severity = "Low"
                    event_types = event.get('event_type', [])
                    if "Death" in event_types:
                        severity = "High"
                    elif "Injury" in event_types or "Malfunction" in event_types:
                        severity = "Medium"

                    # Extract manufacturer name correctly
                    manufacturer = event.get('manufacturer', [{}])[0].get('name', 'Not specified')
                    manufacturers.add(manufacturer)

                    # Safely get brand_name and generic_name
                    device_info = event.get('device', [{}])[0]
                    brand_name = device_info.get('brand_name', 'Not specified')
                    generic_name = device_info.get('generic_name', 'Not specified')
                    
                    # Ensure brand_name and generic_name are strings
                    brand_name = brand_name[0] if isinstance(brand_name, list) else brand_name
                    generic_name = generic_name[0] if isinstance(generic_name, list) else generic_name

                    data.append({
                        "Event ID": event['event_key'],
                        "Date of Event": event.get('date_of_event', 'Not specified'),
                        "Product Problems": ', '.join(event.get('product_problems', ['Not specified'])),
                        "Event Type": ', '.join(event_types),
                        "Severity": severity,
                        "Manufacturer": manufacturer,
                        "Brand Name": brand_name,
                        "Generic Name": generic_name
                    })
                
                df = pd.DataFrame(data)

                # Add manufacturer filter
                manufacturer_options = ["All"] + list(manufacturers)
                selected_manufacturer = st.selectbox("Filter by manufacturer:", manufacturer_options)

                # Apply filters
                if selected_severity != "All":
                    df = df[df["Severity"] == selected_severity]
                if selected_manufacturer != "All":
                    df = df[df["Manufacturer"] == selected_manufacturer]

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
                    file_name=f"{selected_modality}_events_filtered.csv",
                    mime="text/csv",
                )
            else:
                st.warning(f"No events found for the specified modality.")
        else:
            st.warning("Please select a modality.")

with tab2:
    st.header("High Severity Events Across All Modalities")
    
    limit_high_severity = st.number_input("Number of high severity events to retrieve:", min_value=1, max_value=100, value=10, key="high_severity_limit")
    
    if st.button("Get High Severity Events"):
        with st.spinner("Fetching high severity events..."):
            high_severity_events = get_high_severity_events(limit_high_severity)
        
        if high_severity_events:
            data = []
            for event in high_severity_events:
                # Extract manufacturer name correctly
                manufacturer = event.get('manufacturer', [{}])[0].get('name', 'Not specified')
                
                # Safely get brand_name and generic_name
                device_info = event.get('device', [{}])[0]
                brand_name = device_info.get('brand_name', 'Not specified')
                generic_name = device_info.get('generic_name', 'Not specified')
                
                # Ensure brand_name and generic_name are strings
                brand_name = brand_name[0] if isinstance(brand_name, list) else brand_name
                generic_name = generic_name[0] if isinstance(generic_name, list) else generic_name

                data.append({
                    "Event ID": event['event_key'],
                    "Date of Event": event.get('date_of_event', 'Not specified'),
                    "Product Problems": ', '.join(event.get('product_problems', ['Not specified'])),
                    "Event Type": ', '.join(event.get('event_type', ['Not specified'])),
                    "Manufacturer": manufacturer,
                    "Brand Name": brand_name,
                    "Generic Name": generic_name
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            # Add download button for CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download high severity events as CSV",
                data=csv,
                file_name="high_severity_events.csv",
                mime="text/csv",
            )
        else:
            st.warning("No high severity events found.")

# Add footer with API information
st.markdown("---")
st.markdown("Data provided by the [FDA Adverse Event Reporting System API](https://open.fda.gov/apis/device/event/)")