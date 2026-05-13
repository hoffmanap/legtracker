import os
import pandas as pd
import requests
import time

# 1. Configuration & API Keys
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')

# Expanded Coordinate Mapping for all 50 States + DC & PR
STATE_COORDS = {
    'AL': [32.806671, -86.79113], 'AK': [61.370716, -152.404419], 'AZ': [33.729759, -111.431221],
    'AR': [34.969704, -92.373123], 'CA': [36.116203, -119.681564], 'CO': [39.059811, -105.311104],
    'CT': [41.597782, -72.755371], 'DE': [39.318523, -75.507141], 'DC': [38.897438, -77.026817],
    'FL': [27.766279, -81.686783], 'GA': [33.040619, -83.643074], 'HI': [21.094318, -157.498337],
    'ID': [44.240459, -114.478828], 'IL': [40.349457, -88.986137], 'IN': [39.849426, -86.258278],
    'IA': [42.011539, -93.210526], 'KS': [38.526600, -96.726486], 'KY': [37.668140, -84.670067],
    'LA': [31.169546, -91.867805], 'ME': [44.693947, -69.381927], 'MD': [39.063946, -76.802101],
    'MA': [42.230171, -71.530106], 'MI': [43.326618, -84.536064], 'MN': [45.694454, -93.900192],
    'MS': [32.741646, -89.678696], 'MO': [38.456085, -92.288368], 'MT': [46.921925, -110.454353],
    'NE': [41.125370, -98.268082], 'NV': [38.313515, -117.055374], 'NH': [43.452492, -71.563896],
    'NJ': [40.298904, -74.521011], 'NM': [34.840515, -106.248482], 'NY': [42.165726, -74.948051],
    'NC': [35.630066, -79.806419], 'ND': [47.528912, -99.784012], 'OH': [40.388783, -82.764915],
    'OK': [35.565342, -96.928917], 'OR': [44.572021, -122.070938], 'PA': [40.590752, -77.209755],
    'RI': [41.680893, -71.511780], 'SC': [33.856892, -80.945007], 'SD': [44.299782, -99.438828],
    'TN': [35.747845, -86.692345], 'TX': [31.054487, -97.563461], 'UT': [40.150032, -111.862434],
    'VT': [44.045876, -72.710686], 'VA': [37.769337, -78.169968], 'WA': [47.400902, -121.490494],
    'WV': [38.491227, -80.954457], 'WI': [44.268543, -89.616508], 'WY': [42.755966, -107.302490],
    'PR': [18.220800, -66.590100]
}

def get_all_state_sessions():
    """Fetches the latest session ID for every available state/jurisdiction."""
    if not LEGISCAN_KEY: return {}
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getDatasetList"
    try:
        res = requests.get(url).json()
        datasets = res.get('datasetlist', [])
        latest_sessions = {}
        for d in datasets:
            state = d['state']
            if state not in latest_sessions:
                latest_sessions[state] = d['session_id']
        return latest_sessions
    except Exception as e:
        print(f"Error fetching state list: {e}")
        return {}

def fetch_legiscan_master_list(state, session_id):
    """Pulls and filters master list using precise coordinate mapping."""
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getMasterList&id={session_id}"
    bills = []
    keywords = ['zoning', 'accessory dwelling', 'adu', 'lot split', 'middle housing', 
                'parking minimum', 'building code', 'density', 'transit oriented']
    
    try:
        res = requests.get(url).json()
        masterlist = res.get('masterlist', {})
        for idx in masterlist:
            if idx == 'session': continue
            item = masterlist[idx]
            content = f"{item.get('title', '')} {item.get('description', '')}".lower()
            if any(k in content for k in keywords):
                coords = STATE_COORDS.get(state, [39.8283, -98.5795])
                bills.append({
                    'State': state,
                    'Identifier': item.get('number'),
                    'Theme': 'Housing & Zoning Policy',
                    'Summary': item.get('title'),
                    'Status': item.get('last_action', 'Active'),
                    'Link': item.get('url'),
                    'Lat': coords[0],
                    'Lon': coords[1],
                    'Source': f'LegiScan {state}'
                })
        return bills
    except Exception as e:
        print(f"Error processing {state}: {e}")
        return []

if __name__ == "__main__":
    file_path = 'legislation_master.csv'
    session_map = get_all_state_sessions()
    print(f"Starting national sweep. Targeting {len(session_map)} jurisdictions.")
    
    all_new_data = []
    for state, s_id in session_map.items():
        print(f"Scanning {state} (Session {s_id})...")
        state_bills = fetch_legiscan_master_list(state, s_id)
        if state_bills:
            all_new_data.append(pd.DataFrame(state_bills))
        time.sleep(0.2)
    
    if all_new_data:
        new_df = pd.concat(all_new_data, ignore_index=True)
        if os.path.exists(file_path):
            existing_df = pd.read_csv(file_path)
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df
        final_df = final_df.drop_duplicates(subset=['Link']).dropna(subset=['Link'])
        final_df.to_csv(file_path, index=False)
        print(f"Sweep Complete: {len(final_df)} total items tracked.")
    else:
        print("No new relevant bills found.")
