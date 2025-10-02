import csv
import math
from typing import List, Dict

def FindGeoCoordinate(latitude: float, longitude: float, CsvFilepath: str) -> List[Dict]:
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371  # Earth radius in kilometers
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    with open(CsvFilepath, 'r', newline='', encoding='utf-8-sig') as csvfile:
        reader = csv.DictReader(csvfile)
        rows_with_distance = []

        for row in reader:
            try:
                # Clean keys of invisible characters
                cleaned_row = {}
                for key, value in row.items():
                    cleaned_key = key.strip().lstrip('\ufeff')  # Remove BOM and other invisible chars
                    cleaned_row[cleaned_key] = value
                row = cleaned_row
                
                row_lat = float(row["latitude"])
                row_lon = float(row["longitude"])
                distance = haversine_distance(latitude, longitude, row_lat, row_lon)
                rows_with_distance.append((row, distance))
            except (ValueError, KeyError):
                continue

    if not rows_with_distance:
        return []

    min_distance = min(rows_with_distance, key=lambda x: x[1])[1]
    nearest_rows = [row for row, dist in rows_with_distance if dist == min_distance]

    return nearest_rows