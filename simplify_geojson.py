import json
import sys
from topojson import Topology

def convert_geojson_to_topojson(input_file, output_file, simplify_factor=0.01):
    print(f"Reading GeoJSON file: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        geo_data = json.load(f)

    print("Converting to TopoJSON...")
    topo = Topology(geo_data, prequantize=True)
    
    if simplify_factor > 0:
        topo = topo.toposimplify(simplify_factor)

    with open(output_file, "w", encoding="utf-8") as out_f:
        json.dump(topo.to_dict(), out_f)

    print(f"TopoJSON saved as: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python simplify_geojson.py <input_geojson> <output_topojson> [simplify_factor]")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        simplify_factor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.01
        convert_geojson_to_topojson(input_file, output_file, simplify_factor)
