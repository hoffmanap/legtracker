import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Setup
st.set_page_config(page_title="Housing Reform Tracker", layout="wide", page_icon="🏘️")

@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv('legislation_master.csv')
    df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
    df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
    return df.dropna(subset=['Lat', 'Lon'])

# 2. Sidebar & Navigation
st.sidebar.header("Filter Results")
df = load_data()

# Filter by State
states = sorted(df['State'].unique())
selected_states = st.sidebar.multiselect("Select States", states, default=states)

# Filter by Theme
themes = sorted(df['Theme'].unique())
selected_themes = st.sidebar.multiselect("Reform Themes", themes, default=themes)

# Apply Filters
filtered_df = df[
    (df['State'].isin(selected_states)) & 
    (df['Theme'].isin(selected_themes))
]

# 3. UI Header
st.title("🏗️ State & Local Housing Reform Radar")
st.write(f"Tracking **{len(filtered_df)}** pro-housing initiatives across the US.")

# 4. The Map
st.subheader("Geographic Reach")
if not filtered_df.empty:
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="CartoDB Positron")
    
    for _, row in filtered_df.iterrows():
        color = "green" if row['Status'] == "Enacted" else "blue"
        location_text = f"{row['City']}, {row['State']}" if row['City'] != "Statewide" else f"{row['State']} (Statewide)"
        
        popup_content = f"""
            <div style="font-family: Arial; font-size: 13px; width: 200px;">
                <h5 style="margin:0;">{location_text}</h5>
                <hr style="margin:5px 0;">
                <b>Theme:</b> {row['Theme']}<br>
                <b>Status:</b> {row['Status']}<br>
                <p style="margin-top:5px;">{row['Summary']}</p>
                <a href="{row['Link']}" target="_blank">View Official Source</a>
            </div>
        """
        
        folium.CircleMarker(
            location=[row['Lat'], row['Lon']],
            radius=8,
            color=color,
            fill=True,
            fill_opacity=0.6,
            popup=folium.Popup(popup_content, max_width=250),
            tooltip=location_text
        ).add_to(m)
    
    st_folium(m, width="100%", height=500)

# 5. The Searchable Table
st.subheader("Legislative Records")
search = st.text_input("🔍 Search by City, State, or Keyword (e.g. 'El Paso' or 'Lot Split')")

if search:
    table_df = filtered_df[filtered_df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]
else:
    table_df = filtered_df

st.dataframe(
    table_df[['State', 'City', 'Identifier', 'Theme', 'Status', 'Summary', 'Link', 'Source']],
    column_config={"Link": st.column_config.LinkColumn("Link")},
    use_container_width=True,
    hide_index=True
)
