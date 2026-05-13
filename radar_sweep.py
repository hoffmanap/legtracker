import os
import pandas as pd
import requests
import time

# 1. Configuration & API Keys
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')

# Center points for map markers (Expanded for common hubs)
STATE_COORDS = {
    'TX': [31.9686, -99.9018], 'CA': [36.7783, -119.4179], 'IL': [40.6331, -89.3985],
    'MT': [46.8797, -110.3626], 'WA': [47.7511, -120.7401], 'OR': [43.8041, -120.5542],
    'NY': [40.7128, -74.0060], 'FL': [27.6648, -81.5158], 'GA': [32.1656, -82.9001]
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
