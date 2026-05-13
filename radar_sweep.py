import os
import pandas as pd
import requests
import time

# 1. Configuration & API Keys
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')

# Center points for map markers (Expanded for common hubs)
# Updated Coordinate Mapping for all 50 States + DC & PR
STATE_COORDS = {
    'AL': [32.806671, -86.79113], 'AK': [61.370716, -152.404419], 'AZ': [33.729759, -111.431221],
    'AR': [34.969704, -92.373123], 'CA': [36.116203, -119.681564], 'CO': [39.059811, -105.311104],
    'CT': [41.597782, -72.755371], 'DE': [39.318523, -75.507141], 'DC': [38.897438, -77.026817],
    'FL': [27.766279, -81.686783], 'GA': [33.040619, -83.643074], 'HI': [21.094318, -157.498337],
    'ID': [44.240459, -114.478828], 'IL': [40.349457, -88.986137], 'IN': [39.849426, -86.258278],
    'IA': [42.011539, -93.210526], 'KS': [38.5266, -96.726486], 'KY': [37.66814, -84.670067],
    'LA': [31.169546, -91.867805], 'ME': [44.693947, -69.381927], 'MD': [39.063946, -76.802101],
    'MA': [42.230171, -71.530106], 'MI': [43.326618, -84.536064], 'MN': [45.694454, -93.900192],
    'MS': [32.741646, -89.678696], 'MO': [38.456085, -92.288368], 'MT': [46.921925, -110.454353],
    'NE': [41.12537, -98.268082], 'NV': [38.313515, -117.055374], 'NH': [43.452492, -71.563896],
    'NJ': [40.298904, -74.521011], 'NM': [34.840515, -106.248482], 'NY': [42.165726, -74.948051],
    'NC': [35.630066, -79.806419], 'ND': [47.528912, -99.784012], 'OH': [40.388783, -82.764915],
    'OK': [35.565342, -96.928917], 'OR': [44.572021, -122.070938], 'PA': [40.590752, -77.209755],
    'RI': [41.680893, -71.51178], 'SC': [33.856892, -80.945007], 'SD': [44.299782, -99.438828],
    'TN': [35.747845, -86.692345], 'TX': [31.054487, -97.563461], 'UT': [40.150032, -111.862434],
    'VT': [44.045876, -72.710686], 'VA': [37.769337, -78.169968], 'WA
}

def get_all_state_sessions():
    """Fetches the latest session ID for every state/jurisdiction available."""
    if not LEGISCAN_KEY:
        print("Error: No LegiScan API Key found.")
        return {}
    
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getDatasetList"
    try:
        res = requests.get(url).json()
        datasets = res.get('datasetlist', [])
        
        # We want the single most recent session for each unique state
        latest_sessions = {}
        for d in datasets:
            state = d['state']
            # LegiScan lists datasets in reverse chronological order
            if state not in latest_sessions:
                latest_sessions[state] = d['session_id']
        return latest_sessions
    except Exception as e:
        print(f"Error fetching state session list: {e}")
        return {}

def fetch_legiscan_master_list(state, session_id):
    """Pulls the full master list for a specific state session and filters locally."""
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getMasterList&id={session_id}"
    bills = []
    
    # Technical keywords for housing and zoning reform
    keywords = [
        'zoning', 'accessory dwelling', 'adu', 'lot split', 
        'middle housing', 'parking minimum', 'building code',
        'residential density', 'transit oriented', 'floor area ratio'
    ]
    
    try:
        res = requests.get(url).json()
        masterlist = res.get('masterlist', {})
        
        for idx in masterlist:
            if idx == 'session': continue
            item = masterlist[idx]
            
            # Search both title and description for keywords
            content = f"{item.get('title', '')} {item.get('description', '')}".lower()
            
            if any(k in content for k in keywords):
                # Fallback to US center if state coords aren't defined
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
    
    # 1. Dynamically get ALL states and their current session IDs
    session_map = get_all_state_sessions()
    print(f"Starting national sweep. Targeting {len(session_map)} jurisdictions.")
    
    all_new_data = []
    
    # 2. Loop through every active jurisdiction
    for state, s_id in session_map.items():
        print(f"Scanning {state} (Session {s_id})...")
        state_bills = fetch_legiscan_master_list(state, s_id)
        if state_bills:
            all_new_data.append(pd.DataFrame(state_bills))
        
        # Small delay to stay within API rate limits
        time.sleep(0.2)
    
    # 3. Consolidate and Save
    if all_new_data:
        new_df = pd.concat(all_new_data, ignore_index=True)
        
        # If we already have a database, merge and deduplicate
        if os.path.exists(file_path):
            existing_df = pd.read_csv(file_path)
            final_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            final_df = new_df
            
        # Deduplicate by URL (Link) and drop empty entries
        final_df = final_df.drop_duplicates(subset=['Link']).dropna(subset=['Link'])
        
        final_df.to_csv(file_path, index=False)
        print(f"--- National Sweep Complete: {len(final_df)} total bills tracked ---")
    else:
        print("No new relevant bills found in this sweep.")
