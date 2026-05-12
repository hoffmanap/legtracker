import os
import pandas as pd
import requests
from pylegiscan import LegiScan

# 1. Configuration & API Keys
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
    if not LEGISCAN_KEY: return pd.DataFrame()
    
    legis = LegiScan(LEGISCAN_KEY)
    # Search for pro-housing keywords
    query = 'zoning reform OR "accessory dwelling unit" OR "lot split" OR "building code"'
    results = legis.search(state='ALL', query=query)
    
    bills = []
    for b in results.get('results', []):
        state = b['state']
        coords = STATE_COORDS.get(state, [39.8283, -98.5795]) # Default to US center
        
        bills.append({
            'State': state,
            'City': 'Statewide',
            'Identifier': b['bill_number'],
            'Theme': 'Legislative Bill',
            'Summary': b['title'],
            'Status': 'Active',
            'Link': b['url'],
            'Lat': coords[0],
            'Lon': coords[1],
            'Source': 'LegiScan'
        })
    return pd.DataFrame(bills)

def get_news_data():
    """Fetches local/national news via NewsData.io API."""
    if not NEWS_KEY: return pd.DataFrame()
    
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q=zoning%20reform%20housing&language=en&country=us"
    try:
        response = requests.get(url).json()
        news = []
        for art in response.get('results', []):
            # Simple check for city mentions in title
            city = "Local/Multiple" 
            state = "US"
            
            # Use AI region tags if available in the API response
            if art.get('ai_region'):
                city = art['ai_region']
            
            news.append({
                'State': state,
                'City': city,
                'Identifier': 'News Alert',
                'Theme': 'Proposed/News',
                'Summary': art['title'],
                'Status': 'Proposed',
                'Link': art['link'],
                'Lat': 39.8283, # Default center for news
                'Lon': -98.5795,
                'Source': 'News Tracker'
            })
        return pd.DataFrame(news)
    except:
        return pd.DataFrame()

if __name__ == "__main__":
    # Load existing database
    file_path = 'legislation_master.csv'
    if os.path.exists(file_path):
        master_df = pd.read_csv(file_path)
    else:
        master_df = pd.DataFrame(columns=['State', 'City', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

    # Gather new data
    new_bills = get_legiscan_data()
    new_news = get_news_data()
    
    # Merge, remove duplicates by Link, and save
    updated_df = pd.concat([master_df, new_bills, new_news], ignore_index=True)
    updated_df = updated_df.drop_duplicates(subset=['Link'], keep='first')
    
    updated_df.to_csv(file_path, index=False)
    print(f"Sweep complete. {len(updated_df)} total records stored.")
