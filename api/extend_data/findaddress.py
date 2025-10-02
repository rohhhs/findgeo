# Requires: pip install requests
from typing import List, Tuple
import math
import requests

# Globals you may set before calling:
YANDEX_API_KEY = "$$$"
# YANDEX_IAM_TOKEN = "ya...iam-token..."  # if using Yandex Cloud endpoint

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in kilometers between two WGS84 coords."""
    R = 6371.0088  # Earth radius km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.asin(math.sqrt(a))

def FindAddress(latitude: float, longitude: float, results: int = 5, lang: str = "ru_RU") -> List[str]:
    """
    Return a list of the closest streets/places/regions to the given coordinates,
    ordered by geographic distance (closest first). Each item is formatted as:
      "<Geocoder text> (lat, lon) — <distance_km> km"

    Behavior & notes:
    - Uses global YANDEX_IAM_TOKEN (Bearer) with the Yandex Cloud geocoder endpoint when set,
      otherwise falls back to the public geocode-maps.yandex.ru endpoint using YANDEX_API_KEY (apikey param).
    - To prioritize precise results we query multiple `kind` values supported by Yandex Geocoder
      in order of strictness (house -> street -> metro -> locality -> district -> province -> country).
      The `kind` parameter helps restrict the returned object types.
    - The function de-duplicates by the returned textual address (GeocoderMetaData.text) and
      sorts final results by distance from the input point.
    - If the API returns fewer than `results` entries for strict kinds, the function broadens the kinds
      to collect more candidates.
    - See Yandex Geocoder docs for `kind` values (common ones: house, street, metro, locality, district, province, country).
    """

    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude must be provided")

    # endpoints
    YANDEX_CLOUD_URL = "https://geocode-maps.yandexcloud.net/1.x/"
    YANDEX_PUBLIC_URL = "https://geocode-maps.yandex.ru/1.x/"

    iam = globals().get("YANDEX_IAM_TOKEN")
    apikey = globals().get("YANDEX_API_KEY")

    # choose endpoint
    if iam:
        base_url = YANDEX_CLOUD_URL
    else:
        base_url = YANDEX_PUBLIC_URL

    headers = {
        "Accept": "application/json",
        "User-Agent": "FindAddress/1.0",
    }
    if iam:
        headers["Authorization"] = f"Bearer {iam}"

    # kinds ordered from most specific to less specific
    kinds_priority = ["house", "street", "metro", "locality", "district", "province", "country", "other"]

    collected = {}  # text -> (lat, lon, distance_km, kind)
    max_per_kind = max(1, results)  # request this many per kind to fill results faster

    for kind in kinds_priority:
        params = {
            "format": "json",
            "geocode": f"{longitude},{latitude}",  # Yandex expects lon,lat
            "results": str(max_per_kind),
            "lang": lang,
            # include kind param to filter by object type for stricter matches
            "kind": kind
        }
        if (not iam) and apikey:
            params["apikey"] = apikey

        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=6.0)
        except requests.RequestException as e:
            # network error — continue to next kind or endpoint choice
            continue

        # If unauthenticated on cloud endpoint, try public endpoint fallback once
        if resp.status_code in (401, 403) and base_url == YANDEX_CLOUD_URL:
            # switch to public endpoint and try with apikey (if available), else continue
            base_url = YANDEX_PUBLIC_URL
            if apikey:
                params["apikey"] = apikey
            try:
                resp = requests.get(base_url, params=params, headers={k: v for k, v in headers.items() if k != "Authorization"}, timeout=6.0)
            except requests.RequestException:
                continue

        if not resp.ok:
            # skip this kind if API returned error (rate limits, bad request, etc.)
            continue

        try:
            j = resp.json()
        except ValueError:
            continue

        members = (
            j.get("response", {})
             .get("GeoObjectCollection", {})
             .get("featureMember", [])
        ) or []

        for m in members:
            if not isinstance(m, dict):
                continue
            geo = m.get("GeoObject") or {}
            # preferred textual representation
            text = (
                geo.get("metaDataProperty", {})
                   .get("GeocoderMetaData", {})
                   .get("text")
                or geo.get("name")
                or geo.get("description")
            )
            # extract coordinates: Point.pos is "lon lat"
            lat_out = None
            lon_out = None
            try:
                pos = (geo.get("Point") or {}).get("pos")
                if pos:
                    lon_str, lat_str = pos.strip().split()
                    lon_out = float(lon_str)
                    lat_out = float(lat_str)
            except Exception:
                # fallback: sometimes meta geocoder metadata contains point
                try:
                    meta_point = (j.get("response", {})
                                    .get("GeoObjectCollection", {})
                                    .get("metaDataProperty", {})
                                    .get("GeocoderResponseMetaData", {})
                                    .get("Point", {})
                                    .get("pos"))
                    if meta_point:
                        lon_str, lat_str = meta_point.strip().split()
                        lon_out = float(lon_str)
                        lat_out = float(lat_str)
                except Exception:
                    pass

            if not text:
                continue

            # compute distance in km if coords present
            if lat_out is not None and lon_out is not None:
                dist = _haversine_km(latitude, longitude, lat_out, lon_out)
            else:
                dist = float("inf")

            # de-duplicate by text; keep the closest occurrence for equal text
            prev = collected.get(text)
            if prev is None or dist < prev[2]:
                collected[text] = (lat_out if lat_out is not None else latitude,
                                   lon_out if lon_out is not None else longitude,
                                   dist,
                                   kind)

        # stop early if we have enough unique candidates
        if len(collected) >= results:
            break

    # if still not enough results and we used a strict endpoint, try a relaxed request without 'kind'
    if len(collected) < results:
        params = {
            "format": "json",
            "geocode": f"{longitude},{latitude}",
            "results": str(results * 2),
            "lang": lang,
        }
        if (not iam) and apikey:
            params["apikey"] = apikey
        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=6.0)
            if resp.ok:
                j = resp.json()
                members = (
                    j.get("response", {})
                     .get("GeoObjectCollection", {})
                     .get("featureMember", [])
                ) or []
                for m in members:
                    geo = m.get("GeoObject") or {}
                    text = (
                        geo.get("metaDataProperty", {})
                           .get("GeocoderMetaData", {})
                           .get("text")
                        or geo.get("name")
                        or geo.get("description")
                    )
                    lat_out = None
                    lon_out = None
                    try:
                        pos = (geo.get("Point") or {}).get("pos")
                        if pos:
                            lon_str, lat_str = pos.strip().split()
                            lon_out = float(lon_str)
                            lat_out = float(lat_str)
                    except Exception:
                        pass
                    if not text:
                        continue
                    if lat_out is not None and lon_out is not None:
                        dist = _haversine_km(latitude, longitude, lat_out, lon_out)
                    else:
                        dist = float("inf")
                    prev = collected.get(text)
                    if prev is None or dist < prev[2]:
                        collected[text] = (lat_out if lat_out is not None else latitude,
                                           lon_out if lon_out is not None else longitude,
                                           dist,
                                           "relaxed")

        except requests.RequestException:
            pass

    # prepare sorted results by distance (closest first). If distance is inf, they go to the end.
    entries: List[Tuple[str, float, float, float, str]] = []  # (text, lat, lon, dist, kind)
    for text, (lat_out, lon_out, dist, kind) in collected.items():
        entries.append((text, lat_out, lon_out, dist, kind))
    entries.sort(key=lambda e: e[3])

    # format output strings and limit to requested count
    out: List[str] = []
    for text, lat_out, lon_out, dist, kind in entries[:results]:
        # distance formatting: if infinite, omit km value
        if math.isfinite(dist):
            out.append(f"{text} ({lat_out:.6f}, {lon_out:.6f}) — {dist:.3f} km [{kind}]")
        else:
            out.append(f"{text} (approx: {lat_out:.6f}, {lon_out:.6f}) [{kind}]")

    return out

def simplifiedFindAddress(latitude: float, longitude: float, results: int = 5, lang: str = "ru_RU") -> List[str]:
    """
    Return a list of the closest streets/places/regions to the given coordinates,
    ordered by geographic distance (closest first). Each item is formatted as:
      "<Geocoder text> (lat, lon) — <distance_km> km"

    Behavior & notes:
    - Uses global YANDEX_IAM_TOKEN (Bearer) with the Yandex Cloud geocoder endpoint when set,
      otherwise falls back to the public geocode-maps.yandex.ru endpoint using YANDEX_API_KEY (apikey param).
    - To prioritize precise results we query multiple `kind` values supported by Yandex Geocoder
      in order of strictness (house -> street -> metro -> locality -> district -> province -> country).
      The `kind` parameter helps restrict the returned object types.
    - The function de-duplicates by the returned textual address (GeocoderMetaData.text) and
      sorts final results by distance from the input point.
    - If the API returns fewer than `results` entries for strict kinds, the function broadens the kinds
      to collect more candidates.
    - See Yandex Geocoder docs for `kind` values (common ones: house, street, metro, locality, district, province, country).
    """

    if latitude is None or longitude is None:
        raise ValueError("latitude and longitude must be provided")

    # endpoints
    YANDEX_CLOUD_URL = "https://geocode-maps.yandexcloud.net/1.x/"
    YANDEX_PUBLIC_URL = "https://geocode-maps.yandex.ru/1.x/"

    iam = globals().get("YANDEX_IAM_TOKEN")
    apikey = globals().get("YANDEX_API_KEY")

    # choose endpoint
    if iam:
        base_url = YANDEX_CLOUD_URL
    else:
        base_url = YANDEX_PUBLIC_URL

    headers = {
        "Accept": "application/json",
        "User-Agent": "FindAddress/1.0",
    }
    if iam:
        headers["Authorization"] = f"Bearer {iam}"

    # kinds ordered from most specific to less specific
    kinds_priority = ["house", "street", "metro", "locality", "district", "province", "country", "other"]

    collected = {}  # text -> (lat, lon, distance_km, kind)
    max_per_kind = max(1, results)  # request this many per kind to fill results faster

    for kind in kinds_priority:
        params = {
            "format": "json",
            "geocode": f"{longitude},{latitude}",  # Yandex expects lon,lat
            "results": str(max_per_kind),
            "lang": lang,
            # include kind param to filter by object type for stricter matches
            "kind": kind
        }
        if (not iam) and apikey:
            params["apikey"] = apikey

        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=6.0)
        except requests.RequestException as e:
            # network error — continue to next kind or endpoint choice
            continue

        # If unauthenticated on cloud endpoint, try public endpoint fallback once
        if resp.status_code in (401, 403) and base_url == YANDEX_CLOUD_URL:
            # switch to public endpoint and try with apikey (if available), else continue
            base_url = YANDEX_PUBLIC_URL
            if apikey:
                params["apikey"] = apikey
            try:
                resp = requests.get(base_url, params=params, headers={k: v for k, v in headers.items() if k != "Authorization"}, timeout=6.0)
            except requests.RequestException:
                continue

        if not resp.ok:
            # skip this kind if API returned error (rate limits, bad request, etc.)
            continue

        try:
            j = resp.json()
        except ValueError:
            continue

        members = (
            j.get("response", {})
             .get("GeoObjectCollection", {})
             .get("featureMember", [])
        ) or []

        for m in members:
            if not isinstance(m, dict):
                continue
            geo = m.get("GeoObject") or {}
            # preferred textual representation
            text = (
                geo.get("metaDataProperty", {})
                   .get("GeocoderMetaData", {})
                   .get("text")
                or geo.get("name")
                or geo.get("description")
            )
            # extract coordinates: Point.pos is "lon lat"
            lat_out = None
            lon_out = None
            try:
                pos = (geo.get("Point") or {}).get("pos")
                if pos:
                    lon_str, lat_str = pos.strip().split()
                    lon_out = float(lon_str)
                    lat_out = float(lat_str)
            except Exception:
                # fallback: sometimes meta geocoder metadata contains point
                try:
                    meta_point = (j.get("response", {})
                                    .get("GeoObjectCollection", {})
                                    .get("metaDataProperty", {})
                                    .get("GeocoderResponseMetaData", {})
                                    .get("Point", {})
                                    .get("pos"))
                    if meta_point:
                        lon_str, lat_str = meta_point.strip().split()
                        lon_out = float(lon_str)
                        lat_out = float(lat_str)
                except Exception:
                    pass

            if not text:
                continue

            # compute distance in km if coords present
            if lat_out is not None and lon_out is not None:
                dist = _haversine_km(latitude, longitude, lat_out, lon_out)
            else:
                dist = float("inf")

            # de-duplicate by text; keep the closest occurrence for equal text
            prev = collected.get(text)
            if prev is None or dist < prev[2]:
                collected[text] = (lat_out if lat_out is not None else latitude,
                                   lon_out if lon_out is not None else longitude,
                                   dist,
                                   kind)

        # stop early if we have enough unique candidates
        if len(collected) >= results:
            break

    # if still not enough results and we used a strict endpoint, try a relaxed request without 'kind'
    if len(collected) < results:
        params = {
            "format": "json",
            "geocode": f"{longitude},{latitude}",
            "results": str(results * 2),
            "lang": lang,
        }
        if (not iam) and apikey:
            params["apikey"] = apikey
        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=6.0)
            if resp.ok:
                j = resp.json()
                members = (
                    j.get("response", {})
                     .get("GeoObjectCollection", {})
                     .get("featureMember", [])
                ) or []
                for m in members:
                    geo = m.get("GeoObject") or {}
                    text = (
                        geo.get("metaDataProperty", {})
                           .get("GeocoderMetaData", {})
                           .get("text")
                        or geo.get("name")
                        or geo.get("description")
                    )
                    lat_out = None
                    lon_out = None
                    try:
                        pos = (geo.get("Point") or {}).get("pos")
                        if pos:
                            lon_str, lat_str = pos.strip().split()
                            lon_out = float(lon_str)
                            lat_out = float(lat_str)
                    except Exception:
                        pass
                    if not text:
                        continue
                    if lat_out is not None and lon_out is not None:
                        dist = _haversine_km(latitude, longitude, lat_out, lon_out)
                    else:
                        dist = float("inf")
                    prev = collected.get(text)
                    if prev is None or dist < prev[2]:
                        collected[text] = (lat_out if lat_out is not None else latitude,
                                           lon_out if lon_out is not None else longitude,
                                           dist,
                                           "relaxed")

        except requests.RequestException:
            pass

    # prepare sorted results by distance (closest first). If distance is inf, they go to the end.
    entries: List[Tuple[str, float, float, float, str]] = []  # (text, lat, lon, dist, kind)
    for text, (lat_out, lon_out, dist, kind) in collected.items():
        entries.append((text, lat_out, lon_out, dist, kind))
    entries.sort(key=lambda e: e[3])

    # format output strings and limit to requested count
    out: List[str] = []
    for text, lat_out, lon_out, dist, kind in entries[:results]:
        # distance formatting: if infinite, omit km value
        if math.isfinite(dist):
            out.append(f"{text}   {dist:.3f} km")
        else:
            out.append(f"{text}")

    return out

# -------------------------
# Example usage:
# -------------------------
if __name__ == "__main__":
    # set your credentials before calling, e.g.:
    # or
    YANDEX_IAM_TOKEN = "$$$"
    results = simplifiedFindAddress(55.8171027685086, 37.4656205177302, results=2, lang="ru_RU")
    for r in results:
        print(r)
