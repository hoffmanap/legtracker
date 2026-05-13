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
        df['Lat'] = pd.to_numeric(df['Lat'], errors='coerce')
        df['Lon'] = pd.to_numeric(df['Lon'], errors='coerce')
        # Ensure Theme column exists; default to 'General' if missing
        if 'Theme' not in df.columns:
            df['Theme'] = 'Housing & Zoning Policy'
        return df.dropna(subset=['Lat', 'Lon'])
    except FileNotFoundError:
        return pd.DataFrame(columns=['State', 'Identifier', 'Theme', 'Summary', 'Status', 'Link', 'Lat', 'Lon', 'Source'])

df = load_data()

# 3. Sidebar Filters
st.sidebar.title("Search & Filters")
st.sidebar.markdown("Filter the national database by state, theme, or status.")

# Keyword Search
search_query = st.sidebar.text_input("Search Summary or Identifier", "")

# Theme Filter (New)
all_themes = sorted(df['Theme'].unique().astype(str).tolist())
selected_themes = st.sidebar.multiselect("Select Policy Themes", options=all_themes, default=all_themes)

# State Multi-select
all_states = sorted(df['State'].unique().tolist())
selected_states = st.sidebar.multiselect("Select States", options=all_states, default=all_states)

# Status Multi-select
all_statuses = sorted(df['Status'].unique().astype(str).tolist())
selected_statuses = st.sidebar.multiselect("Select Bill Status", options=all_statuses, default=all_statuses)

# 4. Filter Logic
filtered_df = df[
    (df['State'].isin(selected_states)) &
    (df['Status'].isin(selected_statuses)) &
    (df['Theme'].isin(selected_themes))
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
    st.metric("Themes Active", len(filtered_df['Theme'].unique()))
with col3:
    if not filtered_df.empty:
        common_status = filtered_df['Status'].value_counts().idxmax()
    else:
        common_status = "N/A"
    st.metric("Primary Status", common_status)

# 6. The Map
st.subheader("Geospatial View")

def get_status_color(status):
    s = str(status).lower()
    if any(word in s for word in ['pass', 'sign', 'enact', 'enrolled', 'chapter']):
        return "#28a745" # Green
    if any(word in s for word in ['fail', 'die', 'dead', 'veto', 'withdraw', 'defeat']):
        return "#dc3545" # Red
    return "#3186cc" # Blue

if not filtered_df.empty:
    m = folium.Map(location=[39.8283, -98.5795], zoom_start=4, tiles="cartodbpositron")
    
    for _, row in filtered_df.iterrows():
        popup_lines = [
            "<div style='font-family: sans-serif; min-width: 200px;'>",
            f"<b>{row['Identifier']} ({row['State']})</b><br>",
            f"<span style='background: #eee; padding: 2px 5px; border-radius: 3px; font-size: 10px;'>{row['Theme']}</span><br>",
            f"<i style='color: #666;'>{row['Status']}</i><br><br>",
            f"<p style='font-size: 12px; line-height: 1.4;'>{row['Summary']}</p>",
            f"<a href='{row['Link']}' target='_blank' style='color: #3186cc; font-weight: bold;'>View Full Bill Text</a>",
            "</div>"
        ]
        popup_html = "".join(popup_lines)
        
        marker_color = get_status_color(row['Status'])
        
        folium.CircleMarker(
            location=[row['Lat'], row['Lon']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{row['Theme']} | {row['State']}: {row['Identifier']}",
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=0.7
        ).add_to(m)
    
    st_folium(m, width=1400, height=600, returned_objects=[])
else:
    st.warning("No data found matching those filters.")

# 7. Data Table View
st.subheader("Legislative Detail Table")
st.dataframe(
    filtered_df[['State', 'Identifier', 'Status', 'Theme', 'Summary', 'Link']],
    column_config={"Link": st.column_config.LinkColumn("LegiScan Link")},
    use_container_width=True,
    hide_index=True
)
