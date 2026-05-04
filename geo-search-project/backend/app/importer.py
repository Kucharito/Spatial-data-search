import csv
from pathlib import Path
from typing import Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "places.csv"


def import_places(connection, csv_path: Path = DEFAULT_CSV_PATH, clear: bool = True) -> Tuple[int, Path]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    inserted_count = 0

    with connection.cursor() as cursor:
        if clear:
            cursor.execute("TRUNCATE TABLE places RESTART IDENTITY;")

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required_columns = {"name", "category", "address", "latitude", "longitude"}
            if not required_columns.issubset(reader.fieldnames or []):
                raise ValueError(
                    "CSV file must contain columns: name, category, address, latitude, longitude"
                )

            insert_query = """
                INSERT INTO places (name, category, address, latitude, longitude, geom)
                VALUES (
                    %(name)s,
                    %(category)s,
                    %(address)s,
                    %(latitude)s,
                    %(longitude)s,
                    ST_SetSRID(ST_MakePoint(%(longitude)s, %(latitude)s), 4326)::geography
                );
            """

            for row in reader:
                payload = {
                    "name": row["name"].strip(),
                    "category": row["category"].strip(),
                    "address": row["address"].strip(),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                }
                cursor.execute(insert_query, payload)
                inserted_count += 1

    connection.commit()
    return inserted_count, csv_path
