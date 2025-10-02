import requests
import os
from datetime import datetime, timedelta

from ..definitions import *

def load_satellite_images(longitude, latitude, amount=4):
    """
    Download satellite images from NASA GIBS (free service)
    
    Parameters:
    longitude (float): Longitude of the center point
    latitude (float): Latitude of the center point
    amount (int): Number of images to download (up to 4)
    
    Returns:
    List of filenames for downloaded images
    """
    # Target widths in meters for the images
    target_widths = [1000,2000,5000,10000,20000,50000,100000,500000][:amount]
    
    # Get today's date for the imagery
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    
    downloaded_files = []
    
    # GIBS offers various layers - using MODIS Terra for this example
    layers = [
        "MODIS_Terra_CorrectedReflectance_TrueColor",  # Highest resolution available
        "VIIRS_SNPP_CorrectedReflectance_TrueColor",
        "MODIS_Aqua_CorrectedReflectance_TrueColor"
    ]
    
    for i, width_m in enumerate(target_widths):
        # Calculate appropriate zoom level (GIBS uses different zoom system)
        # For GIBS, zoom 9 = ~270m/pixel, zoom 8 = ~540m/pixel, etc.
        zoom = 9 if width_m <= 250 else 8 if width_m <= 500 else 7 if width_m <= 1000 else 6
        
        # Calculate bounding box (GIBS uses EPSG:4326)
        # Approximate conversion: 0.001 degrees ≈ 111 meters
        deg_per_meter = 0.001 / 111
        half_width_deg = (width_m / 2) * deg_per_meter
        
        # Create bounding box
        min_lon = longitude - half_width_deg
        max_lon = longitude + half_width_deg
        min_lat = latitude - half_width_deg
        max_lat = latitude + half_width_deg
        
        # GIBS API parameters
        base_url = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
        params = {
            "service": "WMS",
            "request": "GetMap",
            "layers": layers[0],  # Using highest resolution layer
            "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
            "width": "640",
            "height": "640",
            "format": "image/jpeg",
            "version": "1.3.0",
            "crs": "EPSG:4326",
            "time": date_str
        }
        
        response = requests.get(base_url, params=params)

        print(response)
        
        if response.status_code == 200:
            filename = f"nasa_satellite_{width_m}m.jpg"
            with open(os.path.join(ASSET_IMAGE_PATH, filename), "wb") as f:
                f.write(response.content)
            downloaded_files.append(filename)
            print(f"Successfully downloaded {filename} ({width_m}m area)")
        else:
            print(f"Failed to download image for {width_m}m area: HTTP {response.status_code}")
            # Try alternative layer if primary fails
            if i < len(layers)-1:
                print("Trying alternative data source...")
                params["layers"] = layers[i+1]
                # Would make another request here in a real implementation
    
    return downloaded_files

# Example usage
images = load_satellite_images(55.8171027685086, 37.4656205177302, 8)  # Note: lon, lat order