import streamlit as st
import os
import json
import datetime
import pandas as pd
import geopandas as gpd
import requests
from shapely.geometry import Point
import folium
from streamlit_folium import st_folium

# Constants
DATA_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6.1/csv/MODIS_C6_1_Global_24h.csv"
REGION_DIR = "regions"
OUTPUT_DIR = "output"

# Functions
def load_region_names():
    return [f.replace(".json", "") for f in os.listdir(REGION_DIR) if f.endswith(".json")]

def load_region(region_name):
    with open(os.path.join(REGION_DIR, f"{region_name}.json"), "r") as f:
        return json.load(f)

def download_fire_data():
    df = pd.read_csv(DATA_URL)
    df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
    return gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")

def filter_by_bbox(gdf, bbox):
    minx, miny, maxx, maxy = bbox
    return gdf.cx[minx:maxx, miny:maxy]

def display_folium_map(gdf, bbox):
    gdf = gdf.dropna(subset=["latitude", "longitude"])
    gdf = gdf[gdf.geometry.is_valid]

    center_lat = (bbox[1] + bbox[3]) / 2
    center_lon = (bbox[0] + bbox[2]) / 2
    m = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    for _, row in gdf.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=3,
            color="red",
            fill=True,
            fill_opacity=0.7,
        ).add_to(m)
    return m

# Streamlit App
st.set_page_config(layout="wide")
st.title("🌍 Deforestation Alert System (Prototype)")

region_names = load_region_names()
region_name = st.selectbox("Select Region", region_names)
threshold = st.slider("Set fire point threshold", min_value=10, max_value=500, value=100, step=10)

if st.button("Run Alert"):
    with st.spinner("Downloading and processing fire data..."):
        region = load_region(region_name)
        bbox = region["bbox"]
        gdf = download_fire_data()
        filtered = filter_by_bbox(gdf, bbox)
        filtered = filtered.dropna(subset=["latitude", "longitude"])
        filtered = filtered[filtered.geometry.is_valid]
        count = len(filtered)
        date_str = datetime.date.today().isoformat()

    st.success(f"{count} fire points detected in {region['name']} on {date_str}")

    if count > threshold:
        st.error(f"🔥 ALERT: Fire count exceeds threshold ({threshold})")
    else:
        st.info("✅ Fire activity within normal limits")

    with st.container():
        st.markdown("### 🔥 Fire Map")
        if not filtered.empty:
            folium_map = display_folium_map(filtered, bbox)
            st_data = st_folium(folium_map, width=700, height=500)
        else:
            st.warning("No fire data available in this region today.")

    # Download output
    geojson_data = filtered.to_json()
    st.download_button("Download GeoJSON", geojson_data, file_name=f"{region_name}_{date_str}.geojson", mime="application/json")
