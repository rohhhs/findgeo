import pandas as pd
import ast
import json

import os
from ..definitions import *


def clearDataBaseArrays(tablepath: str, tablekey: str, newtablepath: str) -> str:
    """
    Cleans a CSV database by extracting the first valid address from array-like strings in the specified column.
    
    Args:
        tablepath: Path to the input CSV file
        tablekey: Column name containing array-like address strings to clean
        newtablepath: Path to save the cleaned CSV file
    
    Returns:
        Path to the new cleaned CSV file
    """
    df = pd.read_csv(tablepath)
    
    def clean_array_value(value):
        if pd.isna(value) or value == "":
            return value
        # Try to evaluate as Python literal (handles ["item1", "item2"] format)
        try:
            parsed = ast.literal_eval(str(value))
            if isinstance(parsed, list):
                # Return first non-empty item from list
                for item in parsed:
                    if item and str(item).strip():
                        return str(item).strip()
                return ""
            else:
                return str(parsed)
        except (ValueError, SyntaxError):
            # If not a Python literal, try JSON parsing
            try:
                parsed = json.loads(str(value))
                if isinstance(parsed, list):
                    for item in parsed:
                        if item and str(item).strip():
                            return str(item).strip()
                    return ""
                else:
                    return str(parsed)
            except (json.JSONDecodeError, TypeError):
                # Return original value if no parsing worked
                return str(value)
    
    df[tablekey] = df[tablekey].apply(clean_array_value)
    df.to_csv(newtablepath, index=False)
    return newtablepath

path001 = os.path.join(ASSET_DATA_DIR,"database004.csv")
path002 = os.path.join(ASSET_DATA_DIR,"database005.csv")

# Example usage:
new_table_path = clearDataBaseArrays(tablepath=path001, tablekey="address", newtablepath=path002)

# Libraries to install:
# pandas