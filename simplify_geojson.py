import geopandas as gpd

# Input and output paths
input_file = r"C:/tmp/KZN/KZN_wards.geojson"
output_file = r"C:/tmp/KZN/KZN_wards_optimized.geojson"

# Load the GeoJSON file
gdf = gpd.read_file(input_file)

# Ensure the GeoDataFrame has a "UID" column
if "UID" not in gdf.columns:
    raise ValueError("The GeoJSON file does not contain a 'UID' column!")

# Simplify the geometries (tolerance can be adjusted for more compression)
gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.001, preserve_topology=True)

# Save the optimized GeoJSON
gdf.to_file(output_file, driver="GeoJSON")

print(f"Optimized GeoJSON saved at: {output_file}")
