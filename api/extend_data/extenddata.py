# Requires (only if you call external FindAddress which uses HTTP): pip install requests
# The functions below use only Python stdlib.

from typing import List, Union, Iterator, Tuple
from pathlib import Path
import csv
import json
import tempfile
import os
import shutil

from ..definitions import *
from findaddress import *
from definequality import * 

def parseRow(tablepath: str, keys: List[str], encoding: str = "utf-8-sig") -> Iterator[Tuple[str, ...]]:
    """
    Generator: yields tuples with values for the requested `keys` for each row in the CSV.
    - tablepath: path to .csv file
    - keys: list of column names to extract (order preserved)
    Yields (value_for_key1, value_for_key2, ...)
    """
    csv_path = Path(tablepath)
    if not csv_path.exists() or csv_path.suffix.lower() != ".csv":
        raise FileNotFoundError(f"CSV file not found: {tablepath}")

    with csv_path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                yield tuple((row.get(k, "").strip() for k in keys))
            except Exception:
                yield tuple(("" for _ in keys))


def ExtendData(
    tablepath: str,
    searchkey: Union[str, List[str]],
    searchvalues: Union[str, List[str]],
    tablekey: str,
    extenddata: Union[List[str], str],
    encoding: str = "utf-8-sig",
    json_store: bool = True
) -> List[List[str]]:
    """
    Update CSV rows where all searchkey == searchvalue (exact string match after strip).
    - If resulting stored value contains a single unique item -> store as plain string (no JSON array).
    - If resulting stored value contains multiple items -> store as JSON array when json_store=True,
      otherwise join by " | ".
    Returns a list of updated rows (each row represented as a list of column values in CSV header order).

    Parameters:
      - tablepath: path to CSV file (must exist, .csv)
      - searchkey: single key or list of keys to match
      - searchvalues: single value or list of values corresponding to searchkey(s)
      - tablekey: column name to write/extend (will be created if missing)
      - extenddata: list of strings or a single string to add to the row's tablekey field
      - json_store: if True, multi-value fields stored as JSON array; single values always stored as plain string
    """
    csv_path = Path(tablepath)
    if not csv_path.exists() or csv_path.suffix.lower() != ".csv":
        raise FileNotFoundError(f"CSV file not found or not .csv: {tablepath}")

    # Normalize search keys/values to lists
    if isinstance(searchkey, str):
        search_keys = [searchkey]
    else:
        search_keys = list(searchkey)

    if isinstance(searchvalues, str):
        search_vals = [searchvalues]
    else:
        search_vals = list(searchvalues)

    if len(search_keys) != len(search_vals):
        raise ValueError("searchkey and searchvalues must have the same length")

    # normalize extenddata to list for merging logic
    if isinstance(extenddata, str):
        new_items = [extenddata]
    elif isinstance(extenddata, list):
        new_items = [str(x) for x in extenddata]
    else:
        new_items = [str(extenddata)]

    updated_rows: List[List[str]] = []

    # Read CSV fully, update matching rows in memory, then write back atomically
    with csv_path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames) if reader.fieldnames else []

        # Ensure tablekey exists in header
        if tablekey not in fieldnames:
            fieldnames.append(tablekey)

        all_rows = [dict(row) for row in reader]

    # Helper to parse existing cell into a list of strings
    def _parse_existing_cell(cell: str) -> List[str]:
        if cell is None:
            return []
        cell = str(cell).strip()
        if cell == "":
            return []
        # try parse json array
        try:
            parsed = json.loads(cell)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
            # if primitive, convert to list
            return [str(parsed)]
        except Exception:
            # fallback: treat as a single plain string (don't split)
            return [cell]

    # iterate and update
    for row in all_rows:
        matched = True
        for k, v in zip(search_keys, search_vals):
            existing_val = row.get(k, "")
            if existing_val is None:
                existing_val = ""
            if str(existing_val).strip() != str(v).strip():
                matched = False
                break

        if matched:
            existing_cell = row.get(tablekey, "")
            existing_list = _parse_existing_cell(existing_cell)

            # Merge new_items into existing_list, preserving order and uniqueness
            merged = []
            for item in existing_list:
                if item not in merged:
                    merged.append(item)
            for item in new_items:
                if item not in merged:
                    merged.append(item)

            # Prepare stored string:
            # - If merged has exactly one unique value -> store that value as plain string (no JSON array)
            # - If merged has multiple values -> store JSON array if json_store True, else a readable joined string
            if len(merged) == 0:
                stored_value = ""
            elif len(merged) == 1:
                stored_value = merged[0]
            else:
                if json_store:
                    # store as JSON array (unicode preserved)
                    stored_value = json.dumps(merged, ensure_ascii=False)
                else:
                    stored_value = " | ".join(merged)

            row[tablekey] = stored_value

            # record updated row as ordered list matching header
            updated_rows.append([row.get(fn, "") for fn in fieldnames])

    # If no rows matched, return empty list (no write)
    if not updated_rows:
        return []

    # Write back to CSV atomically (preserving header order)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="extenddata_", suffix=".csv", dir=str(csv_path.parent))
    try:
        # Use os.fdopen to write using the fd we got
        with os.fdopen(tmp_fd, "w", encoding=encoding, newline="") as out_fh:
            writer = csv.DictWriter(out_fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            # ensure all rows include all header keys (fill missing keys with empty string)
            for row in all_rows:
                out_row = {k: (row.get(k, "") if row.get(k, "") is not None else "") for k in fieldnames}
                writer.writerow(out_row)
        # replace original file
        shutil.move(tmp_path, str(csv_path))
    finally:
        # ensure tmp removed if something went wrong
        if Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
            except Exception:
                pass

    return updated_rows


# -------------------------
# Example usage:
# -------------------------
if __name__ == "__main__":
    # Example CSV file
    csvfile = os.path.join(ASSET_DATA_DIR,"database001.csv")

    def count_rows_simple(filename): 
        """Simple line counter (assumes file exists and is readable).""" 
        with open(filename, 'r') as file: 
            return sum(1 for _ in file) 
    rownumber = 0
    rowsamount = count_rows_simple(csvfile)

    # Example: for each row get latitude/longitude, ask your FindAddress (external) and store closest single address
    # Note: FindAddress(...) is not included here; it usually requires requests and your Yandex API key.
    # from findaddress import FindAddress
    # pip install requests

    # for lat, lon , adrs in parseRow(csvfile, ["latitude", "longitude","address"]):
    #     if not lat or not lon:
    #         continue
        
    #     if adrs == "":
    #         # Example: call your FindAddress function which returns a list of address strings ordered by distance
    #         addresses = simplifiedFindAddress(float(lat), float(lon), results=1, lang="ru_RU")
    #         # For demonstration we will fabricate an address list:
    #         # addresses = [f"Россия, Москва, Волоколамское шоссе, 58к1   0.031 km"]
    #         # We want to save only the closest single address (plain string, not JSON array):
    #         best = addresses[0] if addresses else ""
    #         updated = ExtendData(
    #             tablepath=csvfile,
    #             searchkey=["latitude", "longitude"],
    #             searchvalues=[lat, lon],
    #             tablekey="address",
    #             extenddata=best,      # pass a single string -> stored as plain string
    #             json_store=True       # json_store True still keeps single values plain; multiple values become JSON
    #         )
    #         # if updated:
    #         #     print("Updated row saved for", lat, lon)
    #     rownumber += 1 
    #     print (rownumber , "/" , rowsamount)
    for image , quality in parseRow(csvfile, ["filename", "quality"]):
        if not image:
            continue
        if quality == "":
            path = os.path.join(ASSET_IMAGE_DATABASE001_PATH, image)
            defined_quality =  DefineImageQuality(path)

            updated = ExtendData(
                tablepath=csvfile,
                searchkey=["filename"],
                searchvalues=[image],
                tablekey="quality",
                extenddata=defined_quality,      # pass a single string -> stored as plain string
                json_store=True       # json_store True still keeps single values plain; multiple values become JSON
            )
        
        rownumber += 1 
        print (rownumber , "/" , rowsamount)