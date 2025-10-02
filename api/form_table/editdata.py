# Required libraries:
# pip install pandas openpyxl

import os
import csv
import json
from typing import List
import pandas as pd

def editRowDataBase(
    filepath: str,
    columnKey: str,
    rowFieldValue: str,
    head: List[str],
    data: List[List[str]],
) -> str:
    """
    Edit rows in a CSV or Excel file identified by columnKey == rowFieldValue.
    - filepath: path to .csv or .xlsx/.xls file (must exist).
    - columnKey: the column name to search for an exact match.
    - rowFieldValue: the exact value in columnKey used to find rows to edit.
    - head: list of column names for the provided data (order corresponds to each data row).
    - data: list of rows (each row is a list of values) to apply. If multiple rows match:
            - if len(data) == number_of_matches they are applied in order,
            - otherwise the first data row is applied to all matches.
    Returns:
      JSON string like: {"editedData": ["col1,col2,col3", "val1,val2,val3", ...]}
    Raises:
      FileNotFoundError, KeyError, ValueError on failure cases.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    # Helper: read CSV with delimiter detection
    def _read_csv_with_dialect(path: str):
        with open(path, "r", newline="", encoding="utf-8") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample)
                delim = dialect.delimiter
            except Exception:
                delim = ","  # fallback
        df = pd.read_csv(path, sep=delim, dtype=str, keep_default_na=False, engine="python")
        return df, delim

    # Load data
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(filepath, dtype=str)
        write_as = "excel"
        out_delim = ","  # for string serialization
    else:
        df, detected_delim = _read_csv_with_dialect(filepath)
        write_as = "csv"
        out_delim = detected_delim

    # Normalize columns and values
    df.columns = df.columns.map(str)
    df = df.fillna("").astype(str)

    if columnKey not in df.columns:
        raise KeyError(f"columnKey '{columnKey}' not found in file columns: {list(df.columns)}")

    # Find matching rows (exact match)
    matches = df.index[df[columnKey] == str(rowFieldValue)].tolist()
    if not matches:
        raise ValueError(f"No rows found where {columnKey} == {rowFieldValue}")

    # Prepare data rows to apply
    if not data or not isinstance(data, list) or not all(isinstance(r, (list, tuple)) for r in data):
        raise ValueError("data must be a list of list/tuple values (rows)")

    # If provided head length doesn't match data row length -> error
    for r in data:
        if len(r) != len(head):
            raise ValueError("Each data row length must equal length of head")

    # If multiple matches and number of provided data rows equals number of matches -> map one-to-one
    # Otherwise use first provided data row for all matches
    if len(data) == len(matches):
        mapped_rows = data
    else:
        mapped_rows = [data[0]] * len(matches)

    # Ensure columns present: if any head item not in df.columns -> create new column with empty string
    for col in head:
        if col not in df.columns:
            df[col] = ""  # new column appended (to the end)

    # Apply edits
    for idx, match_index in enumerate(matches):
        row_values = mapped_rows[idx]
        for col_name, value in zip(head, row_values):
            # Only update if value is not None (allow empty string to set empty)
            df.at[match_index, str(col_name)] = "" if value is None else str(value)

    # Save back to file (overwrite)
    if write_as == "excel":
        # preserve Excel format
        df.to_excel(filepath, index=False)
    else:
        df.to_csv(filepath, index=False, sep=out_delim, quoting=csv.QUOTE_MINIMAL)

    # Build editedData as list of delimiter-joined row strings (header first)
    rows = [list(df.columns)]
    rows.extend(df.values.tolist())
    serialized_rows = [out_delim.join([str(cell) for cell in row]) for row in rows]

    result = {"editedData": serialized_rows}
    return json.dumps(result, ensure_ascii=False)

# --------------------------
# Example usage:
# --------------------------
if __name__ == "__main__":
    ASSET_DATA_CONTENT_PATH = "/path/to/assets"
    filepath = f"{ASSET_DATA_CONTENT_PATH}/table001.csv"
    new_content = editRowDataBase(
        filepath=filepath,
        columnKey="filename",
        rowFieldValue="image2201.jpg",
        head=["filename", "camera", "longitude", "latitude"],
        data=[["./asset/image/content/image001.jpg", "125192", "60.012412", "51.151254"]],
    )
    print(new_content)
