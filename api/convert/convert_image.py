from PIL import Image
import os
from typing import List, Optional
from pathlib import Path

def convertImages(
    filepaths: List[str],
    quality: int = 85,
    width: Optional[int] = None,
    height: Optional[int] = None,
    extension: str = ".jpg",
    new_path: Optional[str] = "./asset/image/newdata"
) -> List[str]:
    """
    Convert images to specified quality, dimensions, and format.
    
    Args:
        filepaths: List of image file paths to convert
        quality: Quality percentage for JPEG compression (1-100)
        width: Target width in pixels (optional, maintains aspect ratio if height provided)
        height: Target height in pixels (optional, maintains aspect ratio if width provided)
        extension: Target file extension (default: .jpg)
        new_path: Output directory path for converted images (default: "./asset/image/newdata")
    
    Returns:
        List of converted image file paths in the new directory
    """
    # Ensure output directory exists
    output_dir = new_path
    os.makedirs(output_dir, exist_ok=True)
    
    result_paths = []
    
    for filepath in filepaths:
        # Open original image
        with Image.open(filepath) as img:
            original_width, original_height = img.size
            
            # Calculate target dimensions
            target_width = width
            target_height = height
            
            if width is not None and height is not None:
                # Both dimensions specified - resize to exact dimensions
                target_width = width
                target_height = height
            elif width is not None:
                # Only width specified - calculate height maintaining aspect ratio
                target_height = int(original_height * width / original_width)
            elif height is not None:
                # Only height specified - calculate width maintaining aspect ratio
                target_width = int(original_height * height / original_width)
            else:
                # Neither specified - keep original dimensions
                target_width = original_width
                target_height = original_height
            
            # Resize image
            resized_img = img.resize((target_width, target_height), Image.LANCZOS)
            
            # Generate output filename with new extension
            base_filename = os.path.splitext(os.path.basename(filepath))[0]
            output_filename = base_filename + extension
            output_path = os.path.join(output_dir, output_filename)
            
            # Determine save parameters based on extension
            save_kwargs = {}
            if extension.lower() in ['.jpg', '.jpeg']:
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
            elif extension.lower() == '.png':
                save_kwargs['optimize'] = True
            
            # Handle RGB mode for JPEG
            if extension.lower() in ['.jpg', '.jpeg'] and resized_img.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB for JPEG compatibility
                if resized_img.mode == 'P':
                    resized_img = resized_img.convert('RGBA')
                if resized_img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', resized_img.size, (255, 255, 255))
                    if resized_img.mode == 'RGBA':
                        background.paste(resized_img, mask=resized_img.split()[-1])
                    else:
                        background.paste(resized_img)
                    resized_img = background
            
            # Save image
            resized_img.save(output_path, **save_kwargs)
            
            result_paths.append(output_path)
    
    return result_paths

# Example usage:
# if __name__ == "__main__":