import argparse
import os
import datetime
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import json

DATA_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6.1/csv/MODIS_C6_1_Global_24h.csv"
REGION_DIR = "regions"
OUTPUT_DIR = "output"

def load_region(region_name):
    path = os.path.join(REGION_DIR, f"{region_name}.json")
    with open(path, "r") as f:
        region = json.load(f)
    return region

def download_fire_data():
    df = pd.read_csv(DATA_URL)
    df["geometry"] = df.apply(lambda row: Point(row["longitude"], row["latitude"]), axis=1)
    gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    return gdf

def filter_by_bbox(gdf, bbox):
    minx, miny, maxx, maxy = bbox
    return gdf.cx[minx:maxx, miny:maxy]

def save_geojson(gdf, region_name, date_str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{region_name}_{date_str}.geojson")
    gdf.to_file(output_path, driver="GeoJSON")
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Deforestation Alert CLI")
    parser.add_argument("--region", required=True, help="Region name (must match a JSON file in 'regions')")
    parser.add_argument("--threshold", type=int, default=100, help="Alert threshold for fire points")
    args = parser.parse_args()

    today = datetime.date.today().isoformat()
    region = load_region(args.region)
    bbox = region["bbox"]

    print(f"Downloading fire data for {today}...")
    gdf = download_fire_data()
    filtered = filter_by_bbox(gdf, bbox)
    fire_count = len(filtered)

    if fire_count > args.threshold:
        print(f"ALERT!: {fire_count} fire points detected in {region['name']} on {today}")
    else:
        print(f"No alert: {fire_count} fire points in {region['name']}")

    out_file = save_geojson(filtered, args.region, today)
    print(f"Saved fire points to {out_file}")

if __name__ == "__main__":
    main()
