import os
import pandas as pd
import requests

# 1. Robust Import Logic
try:
    from pylegiscan.api import LegiScan
except ImportError:
    try:
        from pylegiscan import LegiScan
    except ImportError:
        class LegiScan:
            def __init__(self, key): self.key = key
            def search(self, **kwargs): return {"results": []}

LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')
NEWS_KEY = os.getenv('NEWS_API_KEY')

STATE_COORDS = {
    'AL': [32.3, -86.9], 'AZ': [34.0, -111.1], 'CA': [36.8, -119.4],
    'CO': [39.6, -105.8], 'FL': [27.7, -81.5], 'GA': [32.2, -82.9],
    'MN': [46.7, -94.7], 'NC': [35.8, -79.0], 'NY': [40.7, -74.0],
    'TX': [31.9, -99.9], 'WA': [47.8, -120.7], 'PR': [18.2, -66.6]
}

def get_legiscan_data():
    if not LEGISCAN_KEY: return pd.DataFrame()
    try:
        legis = LegiScan(LEGISCAN_KEY)
        # Simplified query to match the broad results you saw on the web
        query = 'zoning OR "middle housing" OR parking OR "lot split"'
        
        all_bills = []
        # We check TX specifically first, then ALL states
        for target_state in ['TX', 'ALL']:
            print(f"Deep Scanning LegiScan for {target_state}...")
            # 'year=1' is the magic fix. It tells the API to ignore the 2026 filter 
            # and look at the entire 2025-2026 biennium session.
            results = legis.search(state=target_state, query=query, year=1)
            
            raw_list = results.get('results', [])
            print(f"Found {len(raw_list)} items in {target_state}.")
            
            for b in raw_list:
                if 'bill_number' not in b: continue
                s_code = b.get('state', 'US')
                all_bills.append({
                    'State': s_code,
                    'City': 'Statewide',
                    'Identifier': b.get('bill_number'),
                    'Theme': 'Zoning/Land Use',
                    'Summary': b.get('title', 'No Title'),
                    'Status': 'Active',
                    'Link': b.get('url', ''),
                    'Lat': STATE_COORDS.get(s_code, [39.8, -98.5])[0],
                    'Lon': STATE_COORDS.get(s_code, [39.8, -98.5])[1],
                    'Source': f'LegiScan ({target_state})'
                })
        
        df = pd.DataFrame(all_bills)
        return df.drop_duplicates(subset=['Identifier', 'State']) if not df.empty else df
    except Exception as e:
        print(f"LegiScan Error: {e}")
        return pd.DataFrame()

def get_news_data():
    if not NEWS_KEY: return pd.DataFrame()
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q=zoning%20OR%20housing%20reform&country=us&language=en"
    try:
        response = requests.get(url).json()
        news = []
        for art in response.get('results', []):
            news.append({
                'State': 'US', 'City': art.get('ai_region', 'Local/Multiple'),
                'Identifier': 'News Alert', 'Theme': 'Local Reform',
                'Summary': art.get('title', ''), 'Status': 'Proposed',
                'Link': art.get('link', ''), 'Lat': 39.8, 'Lon': -98.5, 'Source': 'News Tracker'
            })
        return pd.DataFrame(news)
    except Exception as e:
        print(f"News Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    file_path = 'legislation_master.csv'
    master_df = pd.read_csv(file_path) if os.path.exists(file_path) else pd.DataFrame(columns=['State', 'City', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

    new_data = pd.concat([get_legiscan_data(), get_news_data()], ignore_index=True)
    
    # Merge with existing, keeping the newest info
    final_df = pd.concat([master_df, new_data], ignore_index=True)
    final_df = final_df.drop_duplicates(subset=['Link'], keep='first').dropna(subset=['Link'])
    
    final_df.to_csv(file_path, index=False)
    print(f"Done. Database now contains {len(final_df)} records.")
