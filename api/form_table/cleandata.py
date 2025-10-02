import pandas as pd
import os

from ..definitionsdefinitions import *

def cleanDataBase(tablepath: str, tablekey: str, newtablepath: str) -> str:
    """
    Cleans a CSV database by keeping only rows where the specified key has non-empty, non-None values.
    
    Args:
        tablepath: Path to the input CSV file
        tablekey: Column name to check for non-empty values
        newtablepath: Path to save the cleaned CSV file
    
    Returns:
        Path to the new cleaned CSV file
    """
    df = pd.read_csv(tablepath)
    df_cleaned = df[df[tablekey].notna() & (df[tablekey].str.strip() != "")]
    df_cleaned.to_csv(newtablepath, index=False)
    return newtablepath

path001 = os.path.join(ASSET_DATA_DIR,"database003.csv")
path002 = os.path.join(ASSET_DATA_DIR,"database004.csv")

# Example usage:
new_table_path = cleanDataBase(tablepath=path001, tablekey="address", newtablepath=path002)

# Libraries to install:
# pandas