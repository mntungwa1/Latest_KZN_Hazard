import geopandas as gpd
from topojson import Topology
import sys
import os

def convert_geojson_to_topojson(input_file, output_file, simplify_factor=0.01):
    """
    Convert GeoJSON to TopoJSON with geometry simplification.

    :param input_file: Path to input GeoJSON file.
    :param output_file: Path to save TopoJSON file.
    :param simplify_factor: Simplification tolerance (in coordinate units).
    """
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    print(f"Reading GeoJSON file: {input_file}")
    gdf = gpd.read_file(input_file)

    # Simplify geometry using Shapely
    print(f"Simplifying geometries with tolerance = {simplify_factor}...")
    gdf["geometry"] = gdf["geometry"].simplify(simplify_factor, preserve_topology=True)

    print("Converting to TopoJSON...")
    topo = Topology(gdf)

    print(f"Saving TopoJSON to: {output_file}")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(topo.to_json())
    print("Conversion completed successfully!")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simplify_geojson.py <input.geojson> <output.json> [simplify_factor]")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        simplify_factor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
        convert_geojson_to_topojson(input_file, output_file, simplify_factor)
