#!/usr/bin/env python3
"""
Improved Sentinel Hub satellite image downloader with clearer auth error handling.

Fixes applied:
- Robust check for missing/invalid client_id & client_secret.
- Clear, actionable error when OAuth returns 401 (Unauthorized) including server body.
- Optional sourcing of credentials from environment or `definitions` module.
- Small retry/backoff for token fetch to handle transient issues.
- Proper CRS (EPSG:4326) for bbox and correct meters->degrees conversion.
- Raises descriptive exceptions instead of silently failing.
- Simple example that uses ASSET_IMAGE_PATH from definitions if available.

Usage:
  - Provide client_id/client_secret via args or environment:
      SENTINELHUB_CLIENT_ID, SENTINELHUB_CLIENT_SECRET
  - Or pass them explicitly to request_satellite_street_images(...)
"""
import os
import math
import time
import json
import requests
from typing import Iterable, List, Optional

# If you already have a definitions.py with ASSET_IMAGE_PATH, import it safely:
try:
    from ..definitions import ASSET_IMAGE_PATH  # type: ignore
except Exception:
    ASSET_IMAGE_PATH = os.getcwd()

def request_satellite_street_images(
    out_dir: str,
    latitude: float,
    longitude: float,
    sizes_m: Iterable[int],
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    pixels: int = 512,
    max_cloud_coverage: int = 20,
    time_from: str = "2020-01-01T00:00:00Z",
    time_to: Optional[str] = None,
    session: Optional[requests.Session] = None,
    token_retries: int = 2,
    token_timeout: int = 30,
) -> List[str]:
    """
    Download true-color satellite images from Sentinel Hub.

    Returns a list of saved file paths.

    Raises:
        ValueError: missing credentials
        RuntimeError: token acquisition failure or API returned unexpected result
        requests.HTTPError: for non-JSON HTTP errors (with details)
    """
    # Resolve credentials: argument -> environment
    client_id = client_id or os.getenv("SENTINELHUB_CLIENT_ID")
    client_secret = client_secret or os.getenv("SENTINELHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ValueError(
            "Missing Sentinel Hub credentials. Provide client_id and client_secret "
            "either as arguments or via environment variables "
            "SENTINELHUB_CLIENT_ID / SENTINELHUB_CLIENT_SECRET."
        )

    if time_to is None:
        time_to = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    os.makedirs(out_dir, exist_ok=True)
    sess = session or requests.Session()
    sess.headers.update({"User-Agent": "sat-image-fetcher/1.0"})

    # Acquire OAuth token with simple retry/backoff
    token_url = "https://services.sentinel-hub.com/oauth/token"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    token = None
    last_exc = None
    backoff = 1.0
    for attempt in range(1, token_retries + 2):
        try:
            r = sess.post(token_url, data=token_payload, timeout=token_timeout)
            # If 401, raise a clear error with response body for debugging
            if r.status_code == 401:
                # Try to parse JSON error if available
                body = ""
                try:
                    body = json.dumps(r.json(), indent=2, ensure_ascii=False)
                except Exception:
                    body = r.text.strip()
                raise RuntimeError(
                    "Sentinel Hub OAuth failed with 401 Unauthorized. "
                    "Check client_id/client_secret. Server response:\n" + body
                )
            r.raise_for_status()
            token = r.json().get("access_token")
            if not token:
                raise RuntimeError("OAuth response did not contain access_token: " + r.text)
            break
        except Exception as e:
            last_exc = e
            if attempt > token_retries:
                # Exhausted retries
                raise RuntimeError(f"Failed to obtain OAuth token after {attempt} attempts: {e}") from e
            time.sleep(backoff)
            backoff *= 2.0

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Precompute meters -> degrees
    meters_per_deg_lat = 111320.0
    lat_rad = math.radians(latitude)
    meters_per_deg_lon = 111320.0 * max(1e-6, math.cos(lat_rad))  # avoid zero near poles

    api_url = "https://services.sentinel-hub.com/api/v1/process"

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B04","B03","B02","dataMask"],
            output: { bands: 4 }
        };
    }
    function normalize(v) {
        return Math.pow(Math.min(Math.max(v * 2.5, 0.0), 1.0), 0.95);
    }
    function evaluatePixel(sample) {
        return [ normalize(sample.B04), normalize(sample.B03), normalize(sample.B02), sample.dataMask ];
    }
    """

    saved_files: List[str] = []
    for size in sizes_m:
        size = int(size)
        if size <= 0:
            continue

        lat_delta = size / meters_per_deg_lat
        lon_delta = size / meters_per_deg_lon

        min_lon = longitude - lon_delta / 2.0
        min_lat = latitude - lat_delta / 2.0
        max_lon = longitude + lon_delta / 2.0
        max_lat = latitude + lat_delta / 2.0

        payload = {
            "input": {
                "bounds": {
                    "bbox": [min_lon, min_lat, max_lon, max_lat],
                    "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"},
                },
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {"from": time_from, "to": time_to},
                            "maxCloudCoverage": max_cloud_coverage,
                        },
                        "processing": {"upsampling": "BICUBIC", "downsampling": "BICUBIC"},
                    }
                ],
            },
            "output": {
                "width": pixels,
                "height": pixels,
                "responses": [{"identifier": "default", "format": {"type": "image/png"}}],
            },
            "evalscript": evalscript,
        }

        resp = sess.post(api_url, json=payload, headers=headers, timeout=120)
        # If unauthorized here (rare if token was good), include details
        if resp.status_code == 401:
            try:
                body = json.dumps(resp.json(), indent=2, ensure_ascii=False)
            except Exception:
                body = resp.text
            raise RuntimeError(f"API returned 401 Unauthorized when requesting image. Server response:\n{body}")

        if resp.status_code != 200:
            # surface API error body if available
            try:
                err = resp.json()
                raise RuntimeError(f"Sentinel Hub API error {resp.status_code}: {json.dumps(err)}")
            except ValueError:
                resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "image" not in content_type:
            # Often the API will return JSON explaining why (clouds, empty, etc.)
            try:
                info = resp.json()
            except Exception:
                raise RuntimeError(f"Unexpected non-image response. Content-Type: {content_type}")
            raise RuntimeError(f"Unexpected API JSON response instead of image: {json.dumps(info)}")

        ts = int(time.time())
        safe_lat = f"{latitude:.6f}"
        safe_lon = f"{longitude:.6f}"
        filename = os.path.join(out_dir, f"{safe_lat}_{safe_lon}_{size}m_{ts}.png")
        with open(filename, "wb") as fh:
            fh.write(resp.content)
        saved_files.append(filename)

    return saved_files


# Example runner for CLI / debugging
if __name__ == "__main__":
    # Try to use definitions ASSET_IMAGE_PATH if available
    out = os.path.join(ASSET_IMAGE_PATH, "sat_images002")
    try:
        files = request_satellite_street_images(
            out_dir=out,
            latitude=55.8171027685086,
            longitude=37.4656205177302,
            sizes_m=[200, 500, 1000],
            pixels=768,
        )
        print("Saved files:")
        for f in files:
            print(" -", f)
    except Exception as exc:
        # Print full error to help debugging (do NOT log secrets)
        print("ERROR:", exc)
        # If it's a credentials error, hint to the user
        if "401" in str(exc) or "Unauthorized" in str(exc):
            print("Hint: verify SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET are correct and not expired.")
