import csv
import json
from pathlib import Path

INPUT_FILE = Path("../data/ostrava_osm.geojson")
OUTPUT_FILE = Path("../data/places.csv")


def category_from_properties(props: dict) -> str | None:
    # Map OSM properties to a small set of demo categories.
    if props.get("amenity") in {
        "hospital",
        "school",
        "university",
        "restaurant",
        "pharmacy",
        "parking",
    }:
        return props["amenity"]

    if props.get("highway") == "bus_stop":
        return "bus_stop"

    if props.get("leisure") == "park":
        return "park"

    return None


def get_point_from_geometry(geometry: dict):
    # Extract a representative lon/lat point from the GeoJSON geometry.
    """
    Returns longitude, latitude.
    For Point: returns the point.
    For Polygon/MultiPolygon/LineString: computes a simple average of coordinates.
    This is enough for a school demo dataset.
    """
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")

    if not coords:
        return None

    if geom_type == "Point":
        lon, lat = coords
        return lon, lat

    points = []

    # Recursively collect coordinate pairs from nested geometry arrays.
    def collect(c):
        if isinstance(c, list) and len(c) >= 2 and isinstance(c[0], (int, float)) and isinstance(c[1], (int, float)):
            points.append(c)
        elif isinstance(c, list):
            for item in c:
                collect(item)

    collect(coords)

    if not points:
        return None

    lon = sum(p[0] for p in points) / len(points)
    lat = sum(p[1] for p in points) / len(points)
    return lon, lat


def build_address(props: dict) -> str:
    # Build a human-readable address from OSM-style fields.
    street = props.get("addr:street", "")
    house_number = props.get("addr:housenumber", "")
    city = props.get("addr:city", "Ostrava")

    address_parts = []

    if street:
        if house_number:
            address_parts.append(f"{street} {house_number}")
        else:
            address_parts.append(street)

    if city:
        address_parts.append(city)

    return ", ".join(address_parts)


def main():
    # Convert the input GeoJSON into a CSV dataset for import.
    with INPUT_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        category = category_from_properties(props)
        if not category:
            continue

        point = get_point_from_geometry(geometry)
        if not point:
            continue

        lon, lat = point

        name = props.get("name")
        if not name:
            name = f"{category}_{props.get('@id', len(rows) + 1)}"

        rows.append({
            "name": name,
            "category": category,
            "address": build_address(props),
            "latitude": lat,
            "longitude": lon,
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["name", "category", "address", "latitude", "longitude"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Exported {len(rows)} places to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()