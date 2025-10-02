from pathlib import Path
import re
import os

# Set base location relative to the current file (api/init.py)
BASE_DIR = Path(__file__).resolve().parent.parent
ASSET_DATA_DIR = BASE_DIR / "asset" / "data"
ASSET_DATA_ENCRYPTION_DIR = BASE_DIR / "asset" / "data" / "encryption"
ASSET_IMAGE_PATH = BASE_DIR / "asset" / "image"
ASSET_IMAGE_DATABASE001_PATH = BASE_DIR / "asset" / "image" / "database001"
ASSET_IMAGE_NEWDATA_PATH = BASE_DIR / "asset" / "image" / "newdata"
ASSET_IMAGE_DATA_PATH = BASE_DIR / "asset" / "image" / "data"

if __name__ == "__main__":
    print(BASE_DIR)