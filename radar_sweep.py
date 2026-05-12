import os
import pandas as pd
import requests

# 1. Robust Import Logic for LegiScan
try:
    from pylegiscan import LegiScan
except ImportError:
    try:
        from pylegiscan.api import LegiScan
    except ImportError:
        # Fallback if library structure is unexpected
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
    """Fetches state-level bills via LegiScan API."""
    if not LEGISCAN_KEY: 
        print("No LegiScan API Key found.")
        return pd.DataFrame()
    
    try:
        legis = LegiScan(LEGISCAN_KEY)
        # Keyword search for technical housing reforms
        query = 'zoning reform OR "accessory dwelling unit" OR "lot split" OR "building code"'
        results = legis.search(state='ALL', query=query)
        
        bills = []
        for b in results.get('results', []):
            state = b.get('state', 'US')
            coords = STATE_COORDS.get(state, [39.8283, -98.5795])
            
            bills.append({
                'State': state,
                'City': 'Statewide', # Bills are typically statewide
                'Identifier': b.get('bill_number', 'N/A'),
                'Theme': 'Legislative Bill',
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
        print("No News API Key found.")
        return pd.DataFrame()
    
    # Query focused on local zoning/housing reform
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q=zoning%20reform%20housing&language=en&country=us"
    try:
        response = requests.get(url).json()
        news = []
        for art in response.get('results', []):
            # Default values
            city = art.get('ai_region', 'Local/Multiple')
            state = 'US'
            
            news.append({
                'State': state,
                'City': city,
                'Identifier': 'News Alert',
                'Theme': 'Proposed/News',
                'Summary': art.get('title', ''),
                'Status': 'Proposed',
                'Link': art.get('link', ''),
                'Lat': 39.8283, # Default US Center
                'Lon': -98.5795,
                'Source': 'News Tracker'
            })
        return pd.DataFrame(news)
    except Exception as e:
        print(f"NewsData Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    file_path = 'legislation_master.csv'
    
    # Initialize or Load Database
    if os.path.exists(file_path):
        master_df = pd.read_csv(file_path)
    else:
        # Create fresh with the correct columns (including City)
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
    print(f"Successfully processed {len(updated_df)} items.")
