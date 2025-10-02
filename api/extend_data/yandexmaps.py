import requests
import math
import os

def calculate_zoom_level(latitude, target_width_meters, image_width_px=640):
    """
    Calculate appropriate zoom level for Yandex Maps to get approximately
    the desired width in meters at given latitude.
    
    Yandex uses standard web mercator projection where:
    meters_per_pixel = (156543.03392 * cos(latitude)) / (2^zoom)
    """
    # Convert latitude to radians
    lat_rad = math.radians(latitude)
    
    # Calculate numerator for zoom calculation
    numerator = 156543.03392 * math.cos(lat_rad) * image_width_px
    
    # Calculate zoom level
    zoom = math.log2(numerator / target_width_meters)
    
    # Clamp to valid zoom range (0-21 for Yandex Maps)
    return max(0, min(21, round(zoom)))

def loadImages(longitude, latitude, amount=4):
    """
    Download satellite images from Yandex Maps API for specified location.
    
    Parameters:
    longitude (float): Longitude of the center point
    latitude (float): Latitude of the center point
    amount (int): Number of images to download (max 4 for this implementation)
    
    Returns:
    List of filenames for downloaded images
    """
    # Get Yandex API key from environment variable or replace with your key
    api_key = os.getenv("YANDEX_API_KEY", "YOUR_API_KEY_HERE")
    if api_key == "YOUR_API_KEY_HERE":
        print("Warning: Please set YANDEX_API_KEY environment variable or replace in code")
    
    base_url = "https://static-maps.yandex.ru/1.x/"
    image_size = "640,640"  # Width,height in pixels
    
    # Target widths in meters for the 4 images (200m, 500m, 1km, 2km)
    target_widths = [200, 500, 1000, 2000]
    target_widths = target_widths[:amount]
    
    downloaded_files = []
    
    for i, width_m in enumerate(target_widths):
        # Calculate appropriate zoom level for this width
        zoom = calculate_zoom_level(latitude, width_m)
        
        # Prepare parameters for API request
        params = {
            "ll": f"{longitude},{latitude}",  # Note: Yandex uses lon,lat format
            "z": zoom,
            "l": "sat",  # 'sat' for satellite imagery
            "size": image_size,
            "key": api_key
        }
        
        # Make request to Yandex Static Maps API
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            filename = f"satellite_{width_m}m.jpg"
            with open(filename, "wb") as f:
                f.write(response.content)
            downloaded_files.append(filename)
            print(f"Successfully downloaded {filename} (zoom level: {zoom})")
        else:
            print(f"Failed to download image for {width_m}m area: HTTP {response.status_code}")
            print(f"Response: {response.text}")
    
    return downloaded_files

# Example usage:
# images = loadImages(37.75801, 55.7664, 4)  # Moscow coordinates (lon, lat)