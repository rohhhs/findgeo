"""
sat_screenshot.py

Install required package:
    pip install requests

Usage examples:
    # treat inputs as (lat, lon)
    from sat_screenshot import load_images
    load_images(55.7664, 37.75801, 4, provider='mapbox')        # typical (lat,lon)
    # or if you prefer (lon,lat) order:
    load_images(37.75801, 55.7664, 4, coord_order='lonlat')

Environment variables expected (set before running):
    MAPBOX_ACCESS_TOKEN  - for Mapbox Static Images calls
    SENTINELHUB_TOKEN    - for Sentinel Hub WMS (or configure the OAuth flow yourself)
"""

import math
import os
import requests
from typing import Tuple, List

# ---------- utilities ----------
def _auto_detect_latlon(a: float, b: float, coord_order: str='auto') -> Tuple[float,float]:
    """
    Return (lat, lon).
    coord_order: 'auto'|'latlon'|'lonlat'
    auto: if first value in [-90,90] and second in [-180,180] -> assume lat,lon
          otherwise if first absolute>90 -> assume lon,lat
          fallback -> assume lat,lon
    """
    if coord_order == 'latlon':
        return float(a), float(b)
    if coord_order == 'lonlat':
        return float(b), float(a)  # returns (lat, lon)
    a_f = float(a); b_f = float(b)
    if -90 <= a_f <= 90 and -180 <= b_f <= 180:
        return a_f, b_f
    if abs(a_f) > 90 and -90 <= b_f <= 90:
        # likely (lon, lat) given a out of latitude bounds
        return b_f, a_f
    # fallback: assume (lat, lon)
    return a_f, b_f

def meters_to_zoom(ground_width_m: float, lat_deg: float, image_px: int) -> int:
    """
    Compute approximate Mapbox/Slippy zoom level required for 'ground_width_m' to map to image_px.
    Uses formula meters_per_pixel = 156543.03392 * cos(lat) / 2**zoom
    Solve for zoom.
    """
    lat_rad = math.radians(lat_deg)
    meters_per_pixel = ground_width_m / image_px
    # avoid zero/negative
    base = 156543.03392 * math.cos(lat_rad)
    if meters_per_pixel <= 0 or base <= 0:
        return 0
    zoom_f = math.log2(base / meters_per_pixel)
    zoom = int(round(zoom_f))
    # clamp reasonable zoom range
    return max(0, min(22, zoom))

def meters_to_deg_bbox(lon: float, lat: float, half_width_m: float, half_height_m: float=None) -> Tuple[float,float,float,float]:
    """
    Very simple conversion: convert meter offsets to degrees using approximate meters per degree.
    Good for small areas (hundreds to a few thousand meters).
    Returns bbox as (minx, miny, maxx, maxy) in lon/lat order for typical WMS bbox.
    """
    if half_height_m is None:
        half_height_m = half_width_m
    # 1 deg latitude ~ 111_320 m
    dlat = half_height_m / 111320.0
    # 1 deg longitude ~ 111320 * cos(lat) m
    dlon = half_width_m / (111320.0 * math.cos(math.radians(lat)))
    min_lon = lon - dlon
    max_lon = lon + dlon
    min_lat = lat - dlat
    max_lat = lat + dlat
    return (min_lon, min_lat, max_lon, max_lat)

# ---------- Mapbox implementation ----------
def _download_mapbox(lat: float, lon: float, ground_width_m: float, filename: str, access_token: str, img_size_px: Tuple[int,int]=(1024,1024)):
    """
    Mapbox Static Images call: https://docs.mapbox.com/api/maps/static-images/
    We compute zoom from ground_width_m and image width px.
    """
    width_px, height_px = img_size_px
    zoom = meters_to_zoom(ground_width_m, lat, width_px)
    # Mapbox style for satellite:
    style = "mapbox/satellite-v9"
    # build URL
    base = "https://api.mapbox.com/styles/v1"
    # center as lon,lat,zoom
    center = f"{lon},{lat},{zoom}"
    size = f"{width_px}x{height_px}"
    url = f"{base}/{style}/static/{center}/{size}?access_token={access_token}"
    # optional: add &attribution=false&logo=false to reduce overlay (but obey terms!)
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in resp.iter_content(4096):
            f.write(chunk)
    return filename

# ---------- Sentinel Hub (WMS) implementation ----------
def _download_sentinel_wms(lat: float, lon: float, ground_width_m: float, filename: str, token: str, width_px:int=1024, height_px:int=1024, layers:str="TRUE_COLOR"):
    """
    Simple WMS GetMap template for Sentinel Hub (you need to configure an instance and token).
    This is a generic template — adapt per your sentinel-hub instance URL and layers config.
    Example WMS base: https://creodias.sentinel-hub.com/ogc/wms/<instance_id>
    Or use services.sentinel-hub.com if you have an account.
    """
    # compute bbox from ground width
    half = ground_width_m / 2.0
    bbox = meters_to_deg_bbox(lon, lat, half)
    min_lon, min_lat, max_lon, max_lat = bbox
    # example WMS endpoint - REPLACE with your instance's endpoint
    # NOTE: you must register at Sentinel Hub, create a config/instance, then use the correct WMS endpoint.
    wms_base = os.environ.get("SENTINEL_WMS_BASE") or "https://services.sentinel-hub.com/ogc/wms/2296b642-e092-4696-949f-764f76a79d53"
    params = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
        "VERSION": "1.3.0",
        "LAYERS": layers,
        "CRS": "EPSG:4326",
        "BBOX": f"{min_lat},{min_lon},{max_lat},{max_lon}" if False else f"{min_lon},{min_lat},{max_lon},{max_lat}",  # sentinel expects lon,lat bbox order for EPSG:4326 in many deployments; check your instance!
        "WIDTH": str(width_px),
        "HEIGHT": str(height_px),
    }
    # Send request with Bearer token (if required)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = requests.get(wms_base, params=params, headers=headers, stream=True, timeout=40)
    resp.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in resp.iter_content(4096):
            f.write(chunk)
    return filename

# ---------- main public function ----------
def load_images(a: float, b: float, amount: int=4, coord_order: str='auto', provider: str='mapbox',
                out_dir: str='sat_images', sizes_m: List[int]=None, img_size_px: Tuple[int,int]=(1024,1024)):
    """
    Download `amount` satellite images around the coordinate (auto-detect lat/lon).
    provider: 'mapbox' or 'sentinel'
    sizes_m: optional list of ground widths in meters to request (centered). If None default [200,500,1000,...]
    Returns list of saved file paths.
    """
    lat, lon = _auto_detect_latlon(a, b, coord_order=coord_order)
    if sizes_m is None:
        sizes_m = [20000, 50000, 100000]
    # pad sizes if amount > len(sizes_m)
    while len(sizes_m) < amount:
        sizes_m.append(sizes_m[-1] * 2)
    sizes_m = sizes_m[:amount]
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    if provider == 'mapbox':
        token = os.environ.get("MAPBOX_ACCESS_TOKEN")
        if not token:
            raise RuntimeError("Set MAPBOX_ACCESS_TOKEN environment variable for Mapbox access.")
        for idx, meters in enumerate(sizes_m, start=1):
            fname = os.path.join(out_dir, f"sat_mapbox_{idx}_{meters}m.png")
            print(f"Requesting Mapbox {meters} m image -> {fname}")
            _download_mapbox(lat, lon, meters, fname, token, img_size_px=img_size_px)
            saved.append(fname)
    elif provider == 'sentinel':
        token = "PLAKab191f17b8b548818b4ab05a970889f9"
        if not token:
            raise RuntimeError("Set SENTINELHUB_TOKEN environment variable for Sentinel Hub access.")
        # sentinel WMS base must be set via env var SENTINEL_WMS_BASE (see code)
        for idx, meters in enumerate(sizes_m, start=1):
            fname = os.path.join(out_dir, f"sat_sentinel_{idx}_{meters}m.png")
            print(f"Requesting Sentinel WMS {meters} m image -> {fname}")
            _download_sentinel_wms(lat, lon, meters, fname, token, width_px=img_size_px[0], height_px=img_size_px[1])
            saved.append(fname)
    else:
        raise ValueError("Unknown provider. Use 'mapbox' or 'sentinel'.")
    return saved

# If run as a script:
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage: python sat_screenshot.py <lat_or_lon> <lon_or_lat> <amount> [provider]")
        sys.exit(1)
    a = float(sys.argv[1]); b = float(sys.argv[2]); n = int(sys.argv[3])
    prov = sys.argv[4] if len(sys.argv) >= 5 else 'sentinel'
    saved = load_images(a, b, n, provider=prov)
    print("Saved:", saved)
