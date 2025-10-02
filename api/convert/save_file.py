import os
import sys
import json
import csv
from ..definitions import *

def saveCsv(filename="default", filepath=None, filedata=None, chunk_size=10000):
    """
    Saves a JSON object with structure {"head": [...], "data": [[...], [...], ...]} to a CSV file.
    Handles large datasets by processing in chunks to avoid memory issues.
    
    Args:
        filename (str): Name of the file (max 64 characters). Defaults to "default"
        filepath (str): Path where the file will be saved (max 256 characters). 
                        If not provided, uses ASSET_DATA_DIR environment variable
        filedata (dict): JSON object with "head" and "data" keys
        chunk_size (int): Number of rows to process at once for large datasets. Defaults to 10000
    
    Returns:
        tuple: (status_message, filepath) where status_message indicates success/error,
               and filepath is the path where the file was saved
    """
    # Validate inputs
    if not isinstance(filedata, dict) or "head" not in filedata or "data" not in filedata:
        return "Error: filedata must be a dictionary with 'head' and 'data' keys", None
    
    # Validate chunk_size
    if not isinstance(chunk_size, int) or chunk_size <= 0:
        chunk_size = 10000  # Default chunk size
    
    # Process filename
    if not isinstance(filename, str):
        filename = "default"
    else:
        filename = filename[:64]  # Limit to 64 characters
    
    # Process filepath
    if filepath is None:
        filepath = str(ASSET_DATA_DIR)  # Use the predefined ASSET_DATA_DIR
    else:
        # Convert to string if it's a Path object
        filepath = str(filepath)
    
    # Ensure the directory exists
    os.makedirs(filepath, exist_ok=True)
    
    # Full file path
    full_path = os.path.join(filepath, filename if filename.endswith('.csv') else f"{filename}.csv")
    
    headers = filedata["head"]
    rows = filedata["data"]
    
    # Get total number of rows for progress tracking
    total_rows = len(rows)
    
    # Check if file exists and handle appending or merging logic
    if os.path.exists(full_path):
        with open(full_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            try:
                existing_headers = next(reader)
            except StopIteration:
                # File is empty, treat as new file
                existing_headers = []
    else:
        existing_headers = []
    
    # If there are existing headers, handle header matching
    if existing_headers:
        # Find common headers
        common_headers = []
        original_to_common_idx = []  # Maps original header index to common header index
        existing_to_common_idx = []  # Maps existing header index to common header index
        
        for i, h in enumerate(headers):
            if h in existing_headers:
                common_headers.append(h)
                original_to_common_idx.append(i)
                existing_to_common_idx.append(existing_headers.index(h))
        
        # If no common headers, default to original headers
        if not common_headers:
            common_headers = headers
            original_to_common_idx = list(range(len(headers)))
            # For existing rows, we'll fill missing values with empty strings
        else:
            headers = common_headers
    
    # Process data in chunks to handle large datasets
    if os.path.exists(full_path) and existing_headers:
        # Append mode - process in chunks
        with open(full_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Process rows in chunks
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk = rows[start_idx:end_idx]
                
                # Process each row in the chunk
                for row in chunk:
                    # Ensure row matches the existing header structure
                    if len(existing_headers) == len(headers):
                        # Headers match exactly - filter row to common columns only
                        filtered_row = []
                        for idx in original_to_common_idx:
                            if idx < len(row):
                                filtered_row.append(row[idx])
                            else:
                                filtered_row.append("")
                        writer.writerow(filtered_row)
                    else:
                        # Headers may be different - need to align values
                        aligned_row = []
                        for existing_header in existing_headers:
                            if existing_header in headers:
                                idx = headers.index(existing_header)
                                row_idx = original_to_common_idx[idx] if idx < len(original_to_common_idx) else -1
                                if row_idx >= 0 and row_idx < len(row):
                                    aligned_row.append(row[row_idx])
                                else:
                                    aligned_row.append("")
                            else:
                                aligned_row.append("")
                        writer.writerow(aligned_row)
    else:
        # Write new file with headers
        with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            # Process rows in chunks
            for start_idx in range(0, total_rows, chunk_size):
                end_idx = min(start_idx + chunk_size, total_rows)
                chunk = rows[start_idx:end_idx]
                
                # Process chunk
                processed_chunk = []
                for row in chunk:
                    if len(row) >= len(headers):
                        filtered_row = [row[i] if i < len(row) else "" for i in range(len(headers))]
                    else:
                        # If row is shorter than headers, pad with empty strings
                        filtered_row = []
                        for i in range(len(headers)):
                            if i < len(row):
                                filtered_row.append(row[i])
                            else:
                                filtered_row.append("")
                    processed_chunk.append(filtered_row)
                
                writer.writerows(processed_chunk)
    
    return f"Success: Data saved to CSV file (processed {total_rows} rows in chunks of {chunk_size})", full_path