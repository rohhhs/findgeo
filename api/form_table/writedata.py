# Required libraries:
# pip install pandas openpyxl

from typing import List
from pathlib import Path
import pandas as pd
import json

def _detect_csv_delimiter(path: Path, sample_bytes: int = 8192) -> str:
    candidates = [',', ';', '\t', '|']
    try:
        data = path.read_bytes()[:sample_bytes].decode('utf-8', errors='replace')
    except Exception:
        try:
            data = path.read_text(encoding='latin1', errors='replace')[:sample_bytes]
        except Exception:
            return ','
    counts = {d: data.count(d) for d in candidates}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ','

def writeDataBase(filepath: str, head: List[str], data: List[List[str]]) -> str:
    """
    Append rows to an existing .csv or .xlsx file by matching keys (columns).
    - filepath: existing CSV/Excel file path (must exist).
    - head: list of column names for the provided data rows.
    - data: list of rows; each row must have the same length as head.
    
    Behavior:
    - If existing file has columns, only columns that are *common* between existing file and head
      will receive values from the appended rows. Other existing columns will be blank for new rows.
    - If the file has no columns (empty), the provided head will become the file's columns and all data written.
    - File is overwritten with the appended content preserved.
    - Returns JSON string: {"head":[...],"data":[ [...], [...], ... ]} representing file content after write.
    """
    p = Path(filepath)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    # Validate incoming data shape
    for i, row in enumerate(data):
        if len(row) != len(head):
            raise ValueError(f"Row {i} length ({len(row)}) doesn't match head length ({len(head)}).")

    suffix = p.suffix.lower()
    if suffix not in ('.csv', '.xlsx', '.xls'):
        raise ValueError("Unsupported file format. Only .csv and .xlsx/.xls are supported.")

    # Read existing file
    if suffix == '.csv':
        delim = _detect_csv_delimiter(p)
        try:
            existing_df = pd.read_csv(p, sep=delim, dtype=str, encoding='utf-8', engine='python')
        except Exception:
            existing_df = pd.read_csv(p, sep=delim, dtype=str, encoding='latin1', engine='python')
    else:
        existing_df = pd.read_excel(p, dtype=str, engine='openpyxl')

    # Normalize columns to strings
    existing_df.columns = [str(c) for c in existing_df.columns]
    existing_cols = list(existing_df.columns)

    # If file has no headers/columns, create using provided head
    if len(existing_cols) == 0:
        final_cols = head.copy()
        # Build new_df directly from provided head/data
        new_df = pd.DataFrame(data, columns=head, dtype=str)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)
    else:
        # Only columns that are common between provided head and existing columns will be filled.
        # Compute mapping from head index to column name
        head_index = {col: idx for idx, col in enumerate(head)}
        # Build list of dicts for new rows aligned to existing_cols
        new_rows = []
        for row in data:
            new_row = {}
            for col in existing_cols:
                if col in head_index:
                    new_row[col] = row[head_index[col]]
                else:
                    new_row[col] = ""
            new_rows.append(new_row)
        new_df = pd.DataFrame(new_rows, columns=existing_cols, dtype=str)
        combined_df = pd.concat([existing_df, new_df], ignore_index=True, sort=False)
        final_cols = existing_cols

    # Ensure all final columns exist; keep any extra columns that appeared
    for col in final_cols:
        if col not in combined_df.columns:
            combined_df[col] = ""
    extra_cols = [c for c in combined_df.columns if c not in final_cols]
    ordered_cols = final_cols + extra_cols
    combined_df = combined_df.reindex(columns=ordered_cols)

    # Clean and cast to str
    combined_df = combined_df.fillna("").astype(str)

    # Save back
    if suffix == '.csv':
        combined_df.to_csv(p, index=False, sep=delim, encoding='utf-8')
    else:
        combined_df.to_excel(p, index=False, engine='openpyxl')

    payload = {"head": ordered_cols, "data": combined_df[ordered_cols].values.tolist()}
    return json.dumps(payload, ensure_ascii=False)


# ---------------------------
# Example usage:
# ---------------------------
if __name__ == "__main__":
    ASSET_DATA_CONTENT_PATH = "/path/to/assets"  # change to your real path
    example_filepath = f"{ASSET_DATA_CONTENT_PATH}/table001.csv"  # must exist already
    head = ["filename", "camera", "longitude", "latitude"]
    data = [
        ["./asset/image/content/image001.jpg", "125192", "60.012412", "51.151254"]
    ]

    try:
        new_content = writeDataBase(filepath=example_filepath, head=head, data=data)
        print(new_content)  # JSON string with updated file head/data
    except Exception as e:
        print("Error:", e)
