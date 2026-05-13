import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Page Configuration
st.set_page_config(
    page_title="National Housing Policy Radar",
    page_icon="🏠",
    layout="wide"
)

# 2. Load Data
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('legislation_master.csv')
        # Ensure coordinates are numeric
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
        return df.dropna(subset=['Lat', 'Lon'])
    except FileNotFoundError:
        return pd.DataFrame(columns=['State', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

df = load_data()

# 3. Sidebar Filters
st.sidebar.title("Search & Filters")
st.sidebar.markdown("Filter the national database by state, status, or keyword.")

# Keyword Search
search_query = st.sidebar.text_input("Search Summary or Identifier", "")

# State Multi-select
all_states = sorted(df['State'].unique().tolist())
selected_states = st.sidebar.multiselect("Select States", options=all_states, default=all_states)

# Status Multi-select
all_statuses = sorted(df['Status'].unique().astype(str).tolist())
selected_statuses = st.sidebar.multiselect("Select Bill Status", options=all_statuses, default=all_statuses)

# 4. Filter Logic
filtered_df = df[
    (df['State'].isin(selected_states)) &
    (df['Status'].isin(selected_statuses))
]

if search_query:
    filtered_df = filtered_df[
        filtered_df['Summary'].str.contains(search_query, case=False, na=False) |
        filtered_df['Identifier'].str.contains(search_query, case=False, na=False)
    ]

# 5. Main Dashboard Layout
st.title("🏠 Housing & Zoning Policy Radar")
st.markdown(f"Currently tracking **{len(filtered_df)}** relevant bills across selected filters.")

# Metrics Row
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("States Represented", len(filtered_df['State'].unique()))
with col2:
    st.metric("Total Items", len(filtered_df))
with col3:
    st.metric("Most Common Status", filtered_df['Status'].value_counts().idxmax() if not filtered_df.empty else "N/A")

# 6. The Map
st.subheader("Geospatial View")
if not filtered_df.empty:
    # Center map on the average coordinates of the US
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="cartodbpositron")
    
    for _, row in filtered_df.iterrows():
        # Corrected popup string formatting
        popup_html = f"""
        <b>{row['Identifier']} ({row['State']})</b><br>
        <i>{row['Status']}</i><br><br>
        {row['Summary']}<br><br>
        <a href="{row['Link']}" target="_blank">View Full Bill Text</a>
        """
        folium.Marker(
            location=[row['Lat'], row['Lon']],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['State']}: {row['Identifier']}"
        ).add_to(m)
    
    st_folium(m, width=1400, height=600, returned_objects=[])
else:
    st.warning("No data found matching those filters. Try broadening your search.")

# 7. Data Table View
st.subheader("Legislative Detail Table")
st.dataframe(
    filtered_df[['State', 'Identifier', 'Status', 'Theme', 'Summary', 'Link']],
    column_config={
        "Link": st.column_config.LinkColumn("LegiScan Link")
    },
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.caption("Data source: LegiScan API. Updates occur monthly.")
