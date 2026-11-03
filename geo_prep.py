from pathlib import Path
import geopandas as gpd


def optimize_boundaries(
    input_shp: str, output_path: str, tolerance: float = 0.0001, state_filter: str = None
):
    """
    Simplifies and shrinks ABS Shapefiles into demo-ready spatial files.
    
    Parameters:
    - input_shp: Path to the raw ABS Mesh Block shapefile (.shp)
    - output_path: Path to save the optimized file (.geojson or .parquet)
    - tolerance: Degree of simplification. 0.0001 preserves suburb edges perfectly 
                 while stripping out thousands of redundant coordinate points.
    - state_filter: e.g., 'Victoria' or 'New South Wales' to drop unneeded states.
    """
    print("⏳ Loading raw ABS boundaries...")
    gdf = gpd.read_file(input_shp)

    # 1. State Filter (Massive file size reduction if your demo focuses on one region)
    if state_filter and "STE_NAME21" in gdf.columns:
        print(f"✂️ Filtering boundaries to: {state_filter}")
        gdf = gdf[gdf["STE_NAME21"].str.upper() == state_filter.upper()]

    # 2. Select minimal required attribute matrix
    columns_to_keep = ["MB_CODE21", "SA2_CODE21", "SA2_NAME21", "geometry"]
    gdf = gdf[[c for c in columns_to_keep if c in gdf.columns]]

    # 3. Simplify Geometries (Reduces vertex count drastically)
    print(f"⚡ Simplifying geometry loops (Tolerance: {tolerance})...")
    gdf["geometry"] = gdf["geometry"].simplify(tolerance=tolerance, preserve_topology=True)

    # 4. Save to a high-speed format
    out = Path(output_path)
    print(f"💾 Saving optimized file to {out.name}...")
    
    if out.suffix.lower() == ".parquet":
        # Parquet is incredibly fast for loading spatial tables into memory
        gdf.to_parquet(out)
    else:
        # GeoJSON is perfect if you are feeding data directly to leafmap, folium, or Mapbox
        gdf.to_file(out, driver="GeoJSON")

    print(f"🎉 Optimization Complete! Output file size: {out.stat().st_size / (1024*1024):.2f} MB")


# ==========================================
# Run Once Before Demo
# ==========================================
if __name__ == "__main__":
    # Example: Creating a lightweight file for Victoria
    optimize_boundaries(
        input_shp="MB_2021_AUST_GDA2020.shp",
        output_path="sa2_simplified.geojson", # Or use .parquet for pure Python speed
        tolerance=0.0001,
        state_filter="Victoria" 
    )
