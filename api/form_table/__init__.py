import os
import sys
import json
import csv
import time
import pandas as pd
from typing import Dict, List
import os

from ..definitions import *
from .formdata import readDataBase,formDataBase

start_time = time.time()

def timeLine(point_number, description):
    """Log timeline point with exact time from start"""
    elapsed_time = time.time() - start_time
    print(f"[{elapsed_time:.3f}s] Timeline point {point_number}: {description}")

if __name__ == "__main__":
    timeLine(0, "Script started")
    
    ### File setting paths 
    filename = "test.csv"

    # (1) read database 

    # (2) Python function to differently form current database by header using Dictionary with synonims {"filename" : ["filename","Имя файла","file_name","filepath" ...] , "camera":["camera","устройство","device"] , "latitude" : ["latitude","широта"] , "longitude" : ["longitude" , "долгота"]} and then recreate provided database to form with current database head keys . 
    
    # Example usage
    headkeys = {
        "filename": ["filename", "Имя файла", "file_name", "filepath"],
        "camera": ["camera", "устройство", "device"],
        "latitude": ["latitude", "широта"],
        "longitude": ["longitude", "долгота"],
        "address": ["address"],
        "subject": ["object"],
        "quality": ["quality"]
    }

    # Reform an Excel file
    new_path = formDataBase(os.path.join(ASSET_DATA_DIR , "test.xlsx"), headkeys, os.path.join(ASSET_DATA_DIR , "database003.csv"))
    print(f"New database created at: {new_path}")

    # # Reform a CSV file
    # new_path = formDataBase("data.csv", headkeys, "reformed_data.csv")
    # print(f"New database created at: {new_path}")