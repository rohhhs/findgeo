import os
import sys
import json
import csv
import time

from convert_image import convertImages
from obtain_data import changeJsonData , arrayChangeJson , loadTable , extractKeys , cleanTable
from save_file import saveCsv
from ..definitions import *
from ..trimdata import trimPath

start_time = time.time()

def log_timeline_point(point_number, description):
    """Log timeline point with exact time from start"""
    elapsed_time = time.time() - start_time
    print(f"[{elapsed_time:.3f}s] Timeline point {point_number}: {description}")

if __name__ == "__main__":
    log_timeline_point(0, "Script started")
    
    ### Image processing setting
    filepath001 = ASSET_DATA_DIR / "19-001_gin_garbage_echd_19.08.25.xlsx" # data source directory
    imagepath001 = os.path.join(ASSET_IMAGE_PATH , "data19-001") # image source directory
    suffix = "19-002" #filename suffix
    new_imagepath = os.path.join(ASSET_IMAGE_PATH , f"newdata{suffix}") # new images destination directory
    key = "Имя файла" # table head key name value

    log_timeline_point(1, "File was set up")

    if filepath001.exists():
        result001 = loadTable(str(filepath001))
        log_timeline_point(2, "Table loaded .")

        result002 = cleanTable(json.loads(result001) , imagepath001)
        log_timeline_point(3, "Table Cleaned . Found only existing files . ")

        with open(f'./api/convert/jsondata001{suffix}.json', 'w', encoding="utf-8") as f:
            f.write(json.dumps(result002))
        log_timeline_point(4, "Only existing file with data was written .")
        
        filename_array = extractKeys(result002, key)
        log_timeline_point(5, "'filename' keys was extracted .")

        absolute_image_paths = [os.path.join(imagepath001, image_filename) for image_filename in filename_array]

        changed_filename_array = convertImages(
            filepaths=absolute_image_paths,
            quality=62,
            extension=".jpg",
            new_path=new_imagepath
        )

        trimmed_changed_filename_array = [trimPath(p, BASE_DIR) for p in changed_filename_array]

        log_timeline_point(6, "New images was converted , resized or minified and saved to new directory . ")

        result003 = arrayChangeJson(
            data_dict=result002,
            filename_array=filename_array,
            changed_filename_array=trimmed_changed_filename_array,
            key=key
        )
        log_timeline_point(7, "Data dictionary was changed with new values by key 'filename' . ")

        with open(f'./api/convert/jsondata002{suffix}.json', 'w', encoding="utf-8") as f:
            f.write(json.dumps(result003))

        log_timeline_point(8, "New data dictionary was written to a file .")

        status, path = saveCsv(
            filename=f"{suffix}_003.csv",
            filepath=ASSET_DATA_DIR,
            filedata=result003
        )

        log_timeline_point(9, "CSV with new dictionary was saved")

        print(status, path)
    else:
        print(f"File does not exist: {filepath001}")
        log_timeline_point(9, "File not found - script ended")

    total_time = time.time() - start_time
    print(f"\nTotal execution time: {total_time:.3f} seconds")