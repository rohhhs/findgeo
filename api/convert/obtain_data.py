import os
import sys
import pandas as pd
import json

def changeJsonData(json_object_with_head_and_data, key, previous_value, value_to_change):
    """
    Changes a specific value in the JSON data based on the key and previous value.
    
    Args:
        json_object_with_head_and_data (dict): JSON object with "head" and "data" keys
        key (str): The key name that corresponds to a column in the head
        previous_value (str): The current value to be replaced
        value_to_change (str): The new value to replace the previous value
    
    Returns:
        tuple: (status: bool, changed_data: dict)
    """
    # Validate input structure
    if not isinstance(json_object_with_head_and_data, dict):
        return False, json_object_with_head_and_data
    
    if "head" not in json_object_with_head_and_data or "data" not in json_object_with_head_and_data:
        return False, json_object_with_head_and_data
    
    head = json_object_with_head_and_data["head"]
    data = json_object_with_head_and_data["data"]
    
    # Find the index of the key in the head
    try:
        head_key_number = head.index(key)
    except ValueError:
        # Key not found in head
        return False, json_object_with_head_and_data
    
    # Create a deep copy to avoid modifying the original data
    import copy
    result_data = copy.deepcopy(json_object_with_head_and_data)
    
    # Flag to track if any changes were made
    changed = False
    
    # Iterate through the data rows
    for row_idx in range(len(result_data["data"])):
        # Check if the row has enough columns
        if head_key_number < len(result_data["data"][row_idx]):
            # Check if the value matches the previous value
            if result_data["data"][row_idx][head_key_number] == previous_value:
                # Replace the value
                result_data["data"][row_idx][head_key_number] = value_to_change
                changed = True
    
    return changed, result_data

def arrayChangeJson(data_dict, filename_array, changed_filename_array, key="filename"):
    """
    Used to obtain array of values and resolve to changeJsonData one-by-one . 

    Update the data_dict by replacing old filenames with new ones using changeJsonData function . 
    
    Args:
        data_dict: Original data dictionary with head and data
        filename_array: Original filenames to replace
        changed_filename_array: New filenames to replace with
        key: The column key to update (default: "filename")
    
    Returns:
        Updated data_dict with new filenames
    """
    updated_data_dict = data_dict.copy()  # Work with a copy to avoid modifying original
    
    for i in range(len(filename_array)):
        previous_value = filename_array[i]
        value_to_change = changed_filename_array[i]
        
        # Call changeJsonData for each filename pair
        status , updated_data_dict = changeJsonData(
            json_object_with_head_and_data=updated_data_dict,
            key=key,
            previous_value=previous_value,
            value_to_change=value_to_change
        )
    
    return updated_data_dict

def extractKeys(data_dict, key="filename"):
    """
    Extract an array of values from data_dict where key matches a column header
    
    Args:
        data_dict: Dictionary containing data with 'data' key and 'head' key
        key: The column name to search for
    
    Returns:
        List of values from the specified column
    """
    if "data" not in data_dict or "head" not in data_dict:
        return []
    
    # Find the index of the key in the header
    header = data_dict["head"]
    column_index = -1
    
    for i, header_item in enumerate(header):
        # Handle both string headers and dict headers with 'name' key
        if isinstance(header_item, str) and header_item.lower() == key.lower():
            column_index = i
            break
        elif isinstance(header_item, dict) and header_item.get('name', '').lower() == key.lower():
            column_index = i
            break
        elif isinstance(header_item, dict) and str(header_item.get('id', '')).lower() == key.lower():
            column_index = i
            break
    
    if column_index == -1:
        # Try to find similar keywords if exact match not found
        for i, header_item in enumerate(header):
            header_name = ""
            if isinstance(header_item, str):
                header_name = header_item.lower()
            elif isinstance(header_item, dict):
                header_name = header_item.get('name', '').lower() or str(header_item.get('id', '')).lower()
            
            if key.lower() in header_name or header_name in key.lower():
                column_index = i
                break
    
    if column_index == -1:
        print(f"Column '{key}' not found in headers: {header}")
        return []
    
    # Extract values from the specified column
    filename_array = []
    for row in data_dict["data"]:
        if column_index < len(row):
            filename_array.append(row[column_index])
    
    return filename_array

def loadTable(filepath, start=0, amount=None):
    """
    Load data from a CSV or XLSX file and return head and data in JSON format.
    
    Args:
        filepath (str): Path to the CSV or XLSX file (max 256 characters)
        start (int, optional): Starting line for data loading (default: 0)
        amount (int, optional): Number of lines to load from start (default: all)
    
    Returns:
        str: JSON string containing 'head' and 'data' keys
    """
    if not isinstance(filepath, str) or len(filepath) > 256:
        raise ValueError("filepath must be a string with maximum 256 characters")
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Determine file extension
    _, ext = os.path.splitext(filepath.lower())
    
    if ext == '.csv':
        df = pd.read_csv(filepath)
    elif ext == '.xlsx':
        df = pd.read_excel(filepath, engine='openpyxl')
    else:
        raise ValueError("Unsupported file format. Please provide a .csv or .xlsx file.")
    
    # Handle start and amount parameters
    start = int(start) if start is not None else 0
    amount = int(amount) if amount is not None else len(df) - start
    
    if start < 0:
        start = max(0, len(df) + start)
    if amount < 0:
        amount = len(df) - start
    
    end = min(start + amount, len(df))
    
    # Extract the required portion of the dataframe
    selected_df = df.iloc[start:end]
    
    # Prepare the result
    result = {
        "head": df.columns.tolist(),
        "data": selected_df.values.tolist()
    }
    
    return json.dumps(result)

def cleanTable(json_data, file_data_path):
    """
    Cleans JSON data by removing entries where the filename doesn't exist in the asset directory.
    
    Args:
        json_data (dict): JSON data with "head" and "data" keys
        
    Returns:
        dict: Cleaned JSON data with only existing files
    """
    head = json_data.get("head", [])
    data = json_data.get("data", [])
    
    # Find the index of the "filename" key in head
    try:
        filename_index = head.index("filename")
    except ValueError:
        # If "filename" key doesn't exist, return original data
        return {
            "head": head,
            "data": data
        }
    
    cleaned_data = []
    
    for row in data:
        if filename_index < len(row):
            filename = row[filename_index]
            file_path = os.path.join(file_data_path, filename)
            
            # Check if file exists
            if os.path.isfile(file_path):
                cleaned_data.append(row)
    
    return {
        "head": head,
        "data": cleaned_data
    }