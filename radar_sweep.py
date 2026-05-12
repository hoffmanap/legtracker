import os
import pandas as pd
from pylegiscan import LegiScan
import requests

# Load API Keys from GitHub Secrets
LEGISCAN_KEY = os.getenv('LEGISCAN_API_KEY')
NEWS_KEY = os.getenv('NEWS_API_KEY')

def get_new_bills():
    legis = LegiScan(LEGISCAN_KEY)
    # Search for zoning/building code reform keywords nationwide
    results = legis.search(state='ALL', query='zoning reform "lot split" ADU')
    
    bill_list = []
    for b in results['results']:
        bill_list.append({
            'Source': 'LegiScan',
            'State': b['state'],
            'Identifier': b['bill_number'],
            'Title': b['title'],
            'Theme': 'Legislative Bill',
            'Link': b['url'],
            'Status': 'Proposed' # Or map status IDs from LegiScan
        })
    return pd.DataFrame(bill_list)

def get_housing_news():
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_KEY}&q=housing%20zoning%20reform&language=en"
    response = requests.get(url).json()
    
    news_list = []
    for article in response.get('results', []):
        news_list.append({
            'Source': 'News Tracker',
            'State': 'Multiple', # News is often national/regional
            'Identifier': 'News Report',
            'Title': article['title'],
            'Theme': 'News/Proposed',
            'Link': article['link'],
            'Status': 'Proposed'
        })
    return pd.DataFrame(news_list)

# Execute and merge with existing data
if __name__ == "__main__":
    master_df = pd.read_csv('legislation_master.csv')
    new_data = pd.concat([get_new_bills(), get_housing_news()])
    
    # Merge and remove duplicates based on the Link/Identifier
    updated_master = pd.concat([master_df, new_data]).drop_duplicates(subset=['Link'])
    updated_master.to_csv('legislation_master.csv', index=False)