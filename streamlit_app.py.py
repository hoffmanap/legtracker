import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Page Configuration
st.set_page_config(
    page_title="National Housing Reform Tracker",
    page_icon="🏗️",
    layout="wide"
)

# 2. Load Data
@st.cache_data(ttl=3600) # Refreshes cache every hour
def load_data():
    try:
        df = pd.read_csv('legislation_master.csv')
        # Ensure coordinates are numeric
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
        return df.dropna(subset=['Lat', 'Lon'])
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

df = load_data()

# 3. Sidebar Filters
st.sidebar.title("🔍 Filter Radar")
st.sidebar.markdown("Track zoning, building codes, and permitting reform.")

if not df.empty:
    all_themes = sorted(df['Theme'].unique())
    selected_themes = st.sidebar.multiselect("Reform Themes", all_themes, default=all_themes)

    all_statuses = sorted(df['Status'].unique())
    selected_status = st.sidebar.multiselect("Legislation Status", all_statuses, default=all_statuses)

    # Filter Dataframe
    mask = df['Theme'].isin(selected_themes) & df['Status'].isin(selected_status)
    filtered_df = df[mask]
else:
    filtered_df = df

# 4. Main UI
st.title("🏗️ National Housing Reform Dashboard")
st.markdown(f"**Last Update:** {pd.Timestamp.now().strftime('%Y-%m-%d')} (via GitHub Actions)")

# Top Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Bills/Items", len(filtered_df))
col2.metric("States Active", filtered_df['State'].nunique() if not filtered_df.empty else 0)
col3.metric("Enacted Laws", len(filtered_df[filtered_df['Status'] == 'Enacted']))

# 5. Interactive Leaflet Map
st.subheader("🗺️ Geographic Reform Map")
if not filtered_df.empty:
    # Center map on the average of filtered coordinates
    m = folium.Map(
        location=[filtered_df['Lat'].mean(), filtered_df['Lon'].mean()], 
        zoom_start=4, 
        tiles="CartoDB positron"
    )

    for i, row in filtered_df.iterrows():
        # Color code: Green for Enacted, Orange for Active/Proposed
        color = "green" if row['Status'] == 'Enacted' else "orange"
        
        popup_html = f"""
            <div style="font-family: sans-serif; font-size: 12px;">
                <h4 style="margin-bottom:5px;">{row['State']}: {row['Identifier']}</h4>
                <b>Theme:</b> {row['Theme']}<br>
                <b>Status:</b> {row['Status']}<br>
                <p>{row['Summary']}</p>
                <a href="{row['Link']}" target="_blank" style="color: blue;">View Full Legislation</a>
            </div>
        """
        
        folium.CircleMarker(
            location=[row['Lat'], row['Lon']],
            radius=9,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['State']}: {row['Identifier']}"
        ).add_to(m)

    st_folium(m, width="100%", height=500)
else:
    st.warning("No data found for the selected filters.")

# 6. Searchable Database Table
st.subheader("📑 Detailed Legislation Database")
search_query = st.text_input("Search by keyword (e.g., 'ADU', 'Texas', 'Single-Stair')")

if search_query:
    filtered_df = filtered_df[
        filtered_df.apply(lambda row: search_query.lower() in row.astype(str).str.lower().values, axis=1)
    ]

st.dataframe(
    filtered_df,
    column_config={
        "Link": st.column_config.LinkColumn("Resource Link"),
        "Lat": None, # Hide coordinates from table
        "Lon": None
    },
    hide_index=True,
    use_container_width=True
)