import streamlit as st
import requests
import pandas as pd

def get_device_events(search_term, search_type, limit=10):
    url = "https://api.fda.gov/device/event.json"
    
    search_mapping = {
        "Manufacturer": "manufacturer.name",
        "Model": "device.brand_name",
        "Device Type": "device.generic_name"
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

search_type = st.selectbox("Search by:", ["Manufacturer", "Model", "Device Type"])
search_term = st.text_input(f"Enter {search_type.lower()}:")
limit = st.number_input("Number of events to retrieve:", min_value=1, max_value=100, value=10)

if st.button("Get Device Events"):
    if search_term:
        events = get_device_events(search_term, search_type, limit)
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
        st.warning(f"Please enter a {search_type.lower()}.")    
