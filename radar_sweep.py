import os
import pandas as pd
import requests

# 1. Robust Import Logic for LegiScan
try:
    from pylegiscan.api import LegiScan
except ImportError:
    try:
        from pylegiscan import LegiScan
    except ImportError:
        class LegiScan:
            def __init__(self, key): self.key = key
            def search(self, **kwargs): return {"results": []}

# 2. Configuration & API Keys
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')
NEWS_KEY = os.getenv('NEWS_API_KEY')

# Geocoding fallback for States (Center points)
STATE_COORDS = {
    'AL': [32.3182, -86.9023], 'AZ': [34.0489, -111.0937], 'CA': [36.7783, -119.4179],
    'CO': [39.5501, -105.7821], 'FL': [27.6648, -81.5158], 'GA': [32.1656, -82.9001],
    'MN': [46.7296, -94.6859], 'NC': [35.7596, -79.0193], 'NY': [40.7128, -74.0060],
    'TX': [31.9686, -99.9018], 'WA': [47.7511, -120.7401], 'PR': [18.2208, -66.5901]
}

def get_legiscan_data():
    """Fetches state-level bills with optimized search parameters."""
    if not LEGISCAN_KEY: 
        print("Skipping LegiScan: No API Key.")
        return pd.DataFrame()
    
    try:
        legis = LegiScan(LEGISCAN_KEY)
        
        # Simplified query for maximum API compatibility
        query = 'zoning OR "middle housing" OR parking OR "accessory dwelling" OR "lot split"'
        
        # CRITICAL FIX: We loop through TX specifically and use year=1 
        # year=1 tells LegiScan to search ALL years in the current session cycle (2025-2026)
        # Without this, the API often misses bills filed late last year that are still active.
        states_to_check = ['TX', 'ALL']
        all_raw_results = []
        
        for state in states_to_check:
            print(f"Querying LegiScan for {state}...")
            # We use the search method. If pylegiscan doesn't support 'year', 
            # it will just ignore it, but most modern wrappers do.
            results = legis.search(state=state, query=query, year=1)
            batch = results.get('results', [])
            all_raw_results.extend(batch)
            print(f"Batch from {state} yielded {len(batch)} items.")

        bills = []
        for b in all_raw_results:
            if not b.get('bill_number'): continue
            
            state_code = b.get('state', 'US')
            coords = STATE_COORDS.get(state_code, [31.9, -99.9])
            
            bills.append({
                'State': state_code,
                'City': 'Statewide',
                'Identifier': b.get('bill_number'),
                'Theme': 'Zoning/Land Use',
                'Summary': b.get('title', 'No Title Provided'),
                'Status': 'Active',
                'Link': b.get('url', ''),
                'Lat': coords[0],
                'Lon': coords[1],
                'Source': 'LegiScan'
            })
            
        df = pd.DataFrame(bills)
        if not df.empty:
            # Deduplicate so TX results aren't doubled by the 'ALL' search
            df = df.drop_duplicates(subset=['Identifier', 'State'])
            
        return df
    except Exception as e:
        print(f"LegiScan API Error: {e}")
        return pd.DataFrame()

def get_news_data():
    """Fetches local news via NewsData.io API."""
    if not NEWS_KEY: 
        print("Skipping News Tracker: No API Key.")
        return pd.DataFrame()
    
    keywords = 'zoning OR "middle housing" OR "parking" OR "housing reform"'
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q={keywords}&country=us&language=en"
    
    try:
        response = requests.get(url).json()
        news = []
        raw_news = response.get('results', [])
        print(f"News Tracker found {len(raw_news)} items.")
        
        for art in raw_news:
            news.append({
                'State': 'US',
                'City': art.get('ai_region', 'Local/Multiple'),
                'Identifier': 'News Alert',
                'Theme': 'Proposed/News',
                'Summary': art.get('title', ''),
                'Status': 'Proposed',
                'Link': art.get('link', ''),
                'Lat': 39.8283,
                'Lon': -98.5795,
                'Source': 'News Tracker'
            })
        return pd.DataFrame(news)
    except Exception as e:
        print(f"News Tracker error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    file_path = 'legislation_master.csv'
    
    # Load existing or create new
    if os.path.exists(file_path):
        master_df = pd.read_csv(file_path)
    else:
        master_df = pd.DataFrame(columns=['State', 'City', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

    # Scrape
    new_bills = get_legiscan_data()
    new_news = get_news_data()
    
    # Combine and Clean
    updated_df = pd.concat([master_df, new_bills, new_news], ignore_index=True)
    updated_df = updated_df.drop_duplicates(subset=['Link'], keep='first').dropna(subset=['Link'])
    
    updated_df.to_csv(file_path, index=False)
    print(f"Radar Sweep Complete. Total database count: {len(updated_df)}.")
