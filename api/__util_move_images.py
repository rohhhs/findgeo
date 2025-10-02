import os
import shutil
from typing import List
import pandas as pd

from definitions import *

def ReplaceExistingImages(tablepath: str, currentImageFolder: str, newImageFolder: str) -> List[str]:
    """
    Replaces existing images in a database by moving image files from current folder to new folder.
    
    Args:
        tablepath: Path to the CSV file containing image file paths
        currentImageFolder: Path to the current image folder
        newImageFolder: Path to the new image folder
    
    Returns:
        List of new image file paths in the new folder
    """
    # Read the table
    df = pd.read_csv(tablepath)
    
    # Identify image file paths in the table
    image_columns = []
    for col in df.columns:
        # Check if the column contains file paths (by checking for common image extensions)
        if df[col].dtype == 'object':
            sample_values = df[col].dropna().head(10)  # Sample first 10 non-null values
            if any(isinstance(val, str) and any(ext in val.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']) for val in sample_values):
                image_columns.append(col)
    
    new_image_paths = []
    
    # Create new image folder if it doesn't exist
    os.makedirs(newImageFolder, exist_ok=True)
    
    for col in image_columns:
        for idx, img_path in df[col].dropna().items():
            # Check if the image path is a relative path to the current folder
            full_current_path = os.path.join(currentImageFolder, os.path.basename(img_path))
            
            # If the file exists in the current folder, move it to the new folder
            if os.path.exists(full_current_path):
                new_file_path = os.path.join(newImageFolder, os.path.basename(img_path))
                shutil.move(full_current_path, new_file_path)
                new_image_paths.append(new_file_path)
                
                # Update the dataframe with the new path
                df.at[idx, col] = os.path.relpath(new_file_path, os.path.dirname(tablepath))
    
    # Write the updated table back to the file
    df.to_csv(tablepath, index=False)
    
    return new_image_paths

if __name__ == "__main__" : 
    newpaths = ReplaceExistingImages(os.path.join(ASSET_DATA_DIR , "database001.csv") , os.path.join(ASSET_IMAGE_PATH , "database001") , os.path.join(ASSET_IMAGE_PATH , "database002"))
    print (newpaths)