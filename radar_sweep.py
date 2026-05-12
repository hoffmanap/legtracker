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
    """Fetches state-level bills via LegiScan API with fallback logic."""
    if not LEGISCAN_KEY: 
        print("Skipping LegiScan: No API Key.")
        return pd.DataFrame()
    
    try:
        legis = LegiScan(LEGISCAN_KEY)
        
        # Strict Boolean Syntax for 2026 technical housing reforms
        query = '("middle housing" OR "zoning reform" OR "parking minimums" OR "accessory dwelling" OR "lot split" OR "housing")'
        
        # Attempt National Search
        results = legis.search(state='ALL', query=query)
        raw_list = results.get('results', [])
        
        # Texas-Specific Fallback if National returns 0
        if not raw_list:
            print("National search returned 0. Forcing Texas-specific sweep...")
            tx_results = legis.search(state='TX', query='zoning OR housing')
            raw_list = tx_results.get('results', [])

        bills = []
        print(f"LegiScan found {len(raw_list)} potential matches.")
        
        for b in raw_list:
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
        return pd.DataFrame(bills)
    except Exception as e:
        print(f"LegiScan Error: {e}")
        return pd.DataFrame()

def get_news_data():
    """Fetches local news via NewsData.io API."""
    if not NEWS_KEY: 
        print("Skipping News Tracker: No API Key.")
        return pd.DataFrame()
    
    # Broadened search for 2026 local ordinance trends
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
    
    # Initialize or Load Database
    if os.path.exists(file_path):
        master_df = pd.read_csv(file_path)
    else:
        master_df = pd.DataFrame(columns=['State', 'City', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

    # Gather data from both streams
    new_bills = get_legiscan_data()
    new_news = get_news_data()
    
    # Merge and Deduplicate by the Link column
    updated_df = pd.concat([master_df, new_bills, new_news], ignore_index=True)
    updated_df = updated_df.drop_duplicates(subset=['Link'], keep='first')
    
    # Clean up any potential empty rows
    updated_df = updated_df.dropna(subset=['Link'])
    
    updated_df.to_csv(file_path, index=False)
    print(f"Total database count: {len(updated_df)} items.")
