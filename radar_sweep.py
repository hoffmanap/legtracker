import os
import pandas as pd
import requests
import time

LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')

def get_all_state_sessions():
    """Fetches the latest session ID for every available state/jurisdiction."""
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getDatasetList"
    try:
        res = requests.get(url).json()
        datasets = res.get('datasetlist', [])
        
        # We want the most recent session for each unique state
        latest_sessions = {}
        for d in datasets:
            state = d['state']
            if state not in latest_sessions:
                latest_sessions[state] = d['session_id']
        return latest_sessions
    except Exception as e:
        print(f"Error fetching state list: {e}")
        return {}

def process_state(state, session_id):
    """Pulls the full master list for a session and filters for technical housing terms."""
    url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getMasterList&id={session_id}"
    bills = []
    # Technical keywords specifically for zoning/building code reform
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
            
            # Search both title and description
            content = f"{item.get('title', '')} {item.get('description', '')}".lower()
            
            if any(k in content for k in keywords):
                bills.append({
                    'State': state,
                    'Identifier': item.get('number'),
                    'Theme': 'Housing & Zoning Policy',
                    'Summary': item.get('title'),
                    'Status': item.get('last_action'),
                    'Last_Action_Date': item.get('last_action_date'),
                    'Link': item.get('url'),
                    'Source': 'LegiScan Monthly Sweep'
                })
        return bills
    except:
        return []

if __name__ == "__main__":
    session_map = get_all_state_sessions()
    print(f"Starting 50-state sweep. Targeting {len(session_map)} jurisdictions.")
    
    all_bills = []
    for state, s_id in session_map.items():
        print(f"Processing {state}...")
        state_bills = process_state(state, s_id)
        all_bills.extend(state_bills)
        # Small sleep to respect API rate limits during the big sweep
        time.sleep(0.5) 
    
    # Save the deep dive to your master CSV
    df = pd.DataFrame(all_bills)
    if not df.empty:
        # We replace the file for the monthly sweep to ensure we have fresh statuses
        df.to_csv('legislation_master.csv', index=False)
        print(f"Sweep complete! {len(df)} relevant bills found nationwide.")
