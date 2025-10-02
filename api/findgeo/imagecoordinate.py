from typing import List, Tuple
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

def FindGeoImage(filepath: str) -> Tuple[bool, List[str]]:
    """
    Extracts geolocation data from an image file.
    
    Args:
        filepath: Path to the image file
        
    Returns:
        A tuple containing:
        - Boolean indicating if geolocation data was found
        - List containing [latitude, longitude] as strings if found, otherwise empty list
    """
    try:
        image = Image.open(filepath)
        exif_data = image._getexif()
        
        if not exif_data:
            return False, []
        
        # Get GPS info from EXIF data
        gps_info = {}
        for tag, value in exif_data.items():
            tag_name = TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                for gps_tag, gps_value in value.items():
                    gps_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                    gps_info[gps_tag_name] = gps_value
                break
        
        # Extract latitude and longitude
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = _convert_to_degrees(gps_info["GPSLatitude"])
            lon = _convert_to_degrees(gps_info["GPSLongitude"])
            
            # Adjust for N/S and E/W
            if gps_info.get("GPSLatitudeRef") == "S":
                lat = -lat
            if gps_info.get("GPSLongitudeRef") == "W":
                lon = -lon
                
            return True, [str(lat), str(lon)]
        else:
            return False, []
            
    except Exception:
        return False, []

def _convert_to_degrees(value):
    """Converts GPS coordinates from degrees/minutes/seconds to decimal degrees."""
    d0 = value[0][0]
    d1 = value[0][1]
    m0 = value[1][0]
    m1 = value[1][1]
    s0 = value[2][0]
    s1 = value[2][1]
    
    degrees = float(d0) / float(d1)
    minutes = float(m0) / float(m1)
    seconds = float(s0) / float(s1)
    
    return degrees + (minutes / 60.0) + (seconds / 3600.0)