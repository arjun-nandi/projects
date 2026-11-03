import streamlit as st
import geopandas as gpd
import pydeck as pdk
import pandas as pd

st.set_page_config(layout="wide", page_title="Sub-Regional Growth Tracker")

# ---------------------------------------------------------
# 1. LIGHTSPEED CACHED DATA LOADING
# ---------------------------------------------------------
@st.cache_data
def load_sa2_layer():
    # High-level regional file (~few MBs)
    gdf = gpd.read_parquet("sa2_simplified.parquet")
    if gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
    return gdf

@st.cache_data
def load_mesh_block_layer():
    # Ultra-granular local file. 
    # HACKATHON TIP: Ensure this file is filtered down to your target city/state 
    # (e.g. Greater Melbourne) beforehand so it loads in under 2 seconds.
    gdf = gpd.read_parquet("mesh_blocks_simplified.parquet")
    if gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
    return gdf

# ---------------------------------------------------------
# 2. SIDEBAR CONTROLS (Demo Driver)
# ---------------------------------------------------------
st.sidebar.title("🗺️ Map Controls")
view_resolution = st.sidebar.radio(
    "Select Geographic Resolution:",
    options=["Statistical Area 2 (SA2) - Macro Trends", "Mesh Block (MB) - Deep Dive"]
)

# ---------------------------------------------------------
# 3. DYNAMIC LAYER SELECTION & RENDER
# ---------------------------------------------------------
if "SA2" in view_resolution:
    st.subheader("📊 Macro Investment Landscapes (SA2 Level)")
    gdf_to_render = load_sa2_layer()
    
    # Example mock metric mapping for SA2
    gdf_to_render["metric"] = 75  # Replace with actual predictive growth score
    gdf_to_render["fill_color"] = gdf_to_render["metric"].apply(lambda x:) # Clean Blue
    tooltip_text = "SA2 Region: {sa2_name}\nGrowth Score: {metric}%"

else:
    st.subheader("🔍 Micro Footprint Intelligence (Mesh Block Level)")
    gdf_to_render = load_mesh_block_layer()
    
    # Example mock metric mapping for Mesh Blocks (e.g., Residential vs Commercial potential)
    gdf_to_render["fill_color"] = [[255, 165, 0, 160]] * len(gdf_to_render) # Clean Orange
    tooltip_text = "Mesh Block ID: {MB_CODE21}\nSA2 Parent: {sa2_name}"

# Convert active layer to __geo_interface__ for WebGL rendering
geo_data = gdf_to_render.__geo_interface__

# Define Pydeck interactive vector layer
geojson_layer = pdk.Layer(
    "GeoJsonLayer",
    geo_data,
    opacity=0.8,
    stroked=True,
    filled=True,
    get_line_color=[255, 255, 255, 80],
    get_fill_color="properties.fill_color",
    pickable=True,
    auto_highlight=True
)

# Center viewport natively around your demo's main case study site
view_state = pdk.ViewState(
    latitude=-37.825,
    longitude=145.123,
    zoom=11 if "SA2" in view_resolution else 14, # Dynamically pull closer for Mesh Blocks
    pitch=0
)

st.pydeck_chart(pdk.Deck(
    layers=[geojson_layer],
    initial_view_state=view_state,
    map_style="mapbox://styles/mapbox/dark-v9", # Dark mode makes colored polygons pop beautifully
    tooltip={"text": tooltip_text}
))
