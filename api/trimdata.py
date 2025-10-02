from pathlib import Path
import re
import os

def trimPath(path_str, base_dir):
    """
    Trim the provided path string so it starts from base_dir.
    This function is robust to:
      - paths missing the leading slash (e.g. "home/konstantin/...")
      - base_dir occurrences where some internal slashes were lost (e.g. "...websitefindgeo_web...")
    It returns the part of the path that follows base_dir (no leading slash).
    If no reasonable match is found, the original path_str is returned and a warning is printed.
    """
    if path_str is None:
        return path_str

    # Normalize both strings to forward slashes for matching
    norm_path = path_str.replace('\\', '/')
    base_posix = str(base_dir).replace('\\', '/')

    # Remove leading slash from the base for flexible searching
    base_nolead = base_posix.lstrip('/')

    # Split into components and build a regex that allows zero or one slash between components
    # This makes the match robust to missing slashes between components
    components = [comp for comp in base_nolead.split('/') if comp != '']
    if not components:
        print(f"Warning: base_dir '{base_dir}' has no components; returning original path.")
        return path_str

    # pattern: home/?konstantin/?Documents/?website/?findgeo_web/?  (slash between components is optional)
    pattern_str = ''.join(re.escape(c) + r'/?' for c in components)
    pattern = re.compile(pattern_str)

    m = pattern.search(norm_path)
    if m:
        # take everything after the matched base
        relative_part = norm_path[m.end():].lstrip('/')
        return relative_part

    # fallback: maybe the concatenated base without slashes exists as substring
    if base_nolead in norm_path:
        idx = norm_path.find(base_nolead)
        relative_part = norm_path[idx + len(base_nolead):].lstrip('/')
        return relative_part

    # nothing matched
    print(f"Warning: Path '{path_str}' does not contain base directory '{base_posix}'")
    return path_str