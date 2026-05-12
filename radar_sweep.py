import os
import pandas as pd
import requests

# 1. Configuration
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')
NEWS_KEY = os.getenv('NEWS_API_KEY')

# Add or remove states here as needed
TARGET_STATES = ['TX', 'CA', 'IL', 'MT', 'WA', 'OR']

# Center points for the map markers
STATE_COORDS = {
    'TX': [31.9686, -99.9018], 'CA': [36.7783, -119.4179], 'IL': [40.6331, -89.3985],
    'MT': [46.8797, -110.3626], 'WA': [47.7511, -120.7401], 'OR': [43.8041, -120.5542]
}

def fetch_legiscan_master_list(state):
    """Pulls and filters the full master list for a specific state session."""
    if not LEGISCAN_KEY: return pd.DataFrame()
    
    # Step 1: Get the current session ID for the state
    list_url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getDatasetList&state={state}"
    try:
        session_res = requests.get(list_url).json()
        if 'datasetlist' not in session_res:
            print(f"Could not find session list for {state}")
            return pd.DataFrame()
            
        # We grab the most recent session (index 0)
        latest_session = session_res['datasetlist'][0]['session_id']
        
        # Step 2: Pull the Master List for that session
        master_url = f"https://api.legiscan.com/?key={LEGISCAN_KEY}&op=getMasterList&id={latest_session}"
        master_data = requests.get(master_url).json()
        
        bills = []
        # Keywords for local filtering
        keywords = ['zoning', 'housing', 'parking', 'lot split', 'middle housing', 'adu', 'accessory dwelling']
        
        for idx in master_data.get('masterlist', {}):
            if idx == 'session': continue
            bill = master_data['masterlist'][idx]
            
            title = bill.get('title', '').lower()
            desc = bill.get('description', '').lower()
            
            # If any keyword matches, we save it
            if any(k in title or k in desc for k in keywords):
                bills.append({
                    'State': state,
                    'City': 'Statewide',
                    'Identifier': bill.get('number'),
                    'Theme': 'Housing/Zoning',
                    'Summary': bill.get('title'),
                    'Status': bill.get('last_action', 'Active'),
                    'Link': bill.get('url'),
                    'Lat': STATE_COORDS.get(state, [39.8, -98.5])[0],
                    'Lon': STATE_COORDS.get(state, [39.8, -98.5])[1],
                    'Source': f'LegiScan {state}'
                })
        print(f"✅ {state}: Processed session {latest_session}, found {len(bills)} matches.")
        return pd.DataFrame(bills)
    except Exception as e:
        print(f"❌ Error processing {state}: {e}")
        return pd.DataFrame()

def get_news_data():
    """Generic US news sweep for housing reform."""
    if not NEWS_KEY: return pd.DataFrame()
    query = 'zoning OR "middle housing" OR "parking reform"'
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q={query}&country=us&language=en"
    try:
        res = requests.get(url).json()
        news = []
        for art in res.get('results', []):
            news.append({
                'State': 'US', 'City': art.get('ai_region', 'Local'),
                'Identifier': 'News', 'Theme': 'Proposed', 'Summary': art.get('title'),
                'Status': 'Proposed', 'Link': art.get('link'), 'Lat': 39.8, 'Lon': -98.5, 'Source': 'News'
            })
        return pd.DataFrame(news)
    except: return pd.DataFrame()

if __name__ == "__main__":
    file_path = 'legislation_master.csv'
    
    # 1. Loop through all target states
    all_new_data = []
    for state in TARGET_STATES:
        state_df = fetch_legiscan_master_list(state)
        all_new_data.append(state_df)
    
    # 2. Add News
    all_new_data.append(get_news_data())
    
    # 3. Combine everything
    new_data_combined = pd.concat(all_new_data, ignore_index=True)
    
    if os.path.exists(file_path):
        master_df = pd.read_csv(file_path)
        final_df = pd.concat([master_df, new_data_combined], ignore_index=True)
    else:
        final_df = new_data_combined
        
    # Deduplicate and Save
    final_df = final_df.drop_duplicates(subset=['Link']).dropna(subset=['Link'])
    final_df.to_csv(file_path, index=False)
    print(f"--- Sweep Complete: {len(final_df)} total items in database ---")
