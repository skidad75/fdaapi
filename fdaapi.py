import streamlit as st
import requests
import pandas as pd

def get_api_data(field, limit=1000):
    url = "https://api.fda.gov/device/event.json"
    params = {
        "count": field,
        "limit": limit
    }
    headers = {
        'Authorization': '4AeebrN6spDSoz0ReOT9T38uICCFZBEALM6SxKAU'
    }
    response = requests.get(url, headers=headers, params=params)
    return [item['term'] for item in response.json()['results']]

def get_device_events(search_term, search_type, limit=10):
    url = "https://api.fda.gov/device/event.json"
    
    search_mapping = {
        "Manufacturer": "manufacturer.name",
        "Model": "device.brand_name",
        "Modality": "device.generic_name"
    }
    
    params = {
        "search": f"{search_mapping[search_type]}:'{search_term}'",
        "limit": limit
    }
    
    headers = {
        'Authorization': '4AeebrN6spDSoz0ReOT9T38uICCFZBEALM6SxKAU'
    }

    response = requests.get(url, headers=headers, params=params)
    return response.json()

st.title("FDA Device Adverse Events")

# Fetch options for dropdowns
manufacturers = get_api_data("manufacturer.name.exact")
models = get_api_data("device.brand_name.exact")
modalities = get_api_data("device.generic_name.exact")

# Create dropdowns
search_type = st.selectbox("Search by:", ["Manufacturer", "Model", "Modality"])

# Populate the list of options based on the selected search type
if search_type == "Manufacturer":
    search_term = st.selectbox("Select manufacturer:", manufacturers)
elif search_type == "Model":
    search_term = st.selectbox("Select model:", models)
else:
    search_term = st.selectbox("Select modality:", modalities)

# Add device type selection
device_types = get_api_data("device.device_class")
selected_device_type = st.selectbox("Select device type:", device_types)

limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

if st.button("Get Device Events"):
    if search_term and selected_device_type:
        events = get_device_events(f"{search_term} AND device.device_class:{selected_device_type}", search_type, limit)
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
            st.error(f"No events found for the specified {search_type.lower()}.")
    else:
        st.warning(f"Please select both a {search_type.lower()} and a device type.")
