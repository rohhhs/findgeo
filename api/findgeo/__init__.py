import os
import time

from ..definitions import *
from api.findgeo.findcoordinate import FindGeoCoordinate
from api.findgeo.imagecoordinate import FindGeoImage
# from findcoordinate import FindGeoCoordinate

start_time = time.time()

def timeLine(point_number, description):
    """Log timeline point with exact time from start"""
    elapsed_time = time.time() - start_time
    print(f"[{elapsed_time:.3f}s] Timeline point {point_number}: {description}")

if __name__ == "__main__":
    timeLine(0, "Script started")

    list_of_rows = FindGeoCoordinate(latitude=59.102312, longitude=31.123534, CsvFilepath=os.path.join(ASSET_DATA_DIR, "database001.csv"))

    print (list_of_rows)

    # coordinates_found, geocoordinates = FindGeoImage(os.path.join(ASSET_IMAGE_PATH, "IMG_3542.HEIC"))
    # print(coordinates_found , os.path.join(ASSET_IMAGE_PATH, "IMG_3542.HEIC"))
    # if coordinates_found:
    #     latitude = geocoordinates[0]
    #     longitude = geocoordinates[1]
    #     print (geocoordinates)
