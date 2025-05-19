import os
import shutil
from pillow_heif import register_heif_opener
from PIL import Image
import glob

def convert_and_move_images():
    # Register HEIF opener with Pillow
    register_heif_opener()
    
    # Create OLDimages directory if it doesn't exist
    if not os.path.exists('OLDimages'):
        os.makedirs('OLDimages')
    
    # First, move any converted JPGs from OLDimages back to main directory
    for jpg_file in glob.glob(os.path.join('OLDimages', '*.jpg')):
        try:
            shutil.move(jpg_file, os.path.basename(jpg_file))
            print(f"Moved converted JPG back to main directory: {jpg_file}")
        except Exception as e:
            print(f"Error moving JPG file: {str(e)}")
    
    # Get all image files (case-insensitive)
    image_extensions = ['*.HEIC', '*.heic', '*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
    processed_files = set()  # Keep track of processed files
    
    for ext in image_extensions:
        for image_file in glob.glob(ext, recursive=False):
            # Skip files that are already in OLDimages directory
            if image_file.startswith('OLDimages') or image_file in processed_files:
                continue
                
            try:
                # Skip if it's a JPG file that was created by our conversion
                if image_file.lower().endswith('.jpg') and os.path.exists(os.path.splitext(image_file)[0] + '.HEIC'):
                    continue
                
                # Open the image
                img = Image.open(image_file)
                
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Create new filename with .jpg extension
                new_filename = os.path.splitext(image_file)[0] + '.jpg'
                
                # Save as JPG
                img.save(new_filename, 'JPEG', quality=95)
                
                # Move original file to OLDimages directory
                shutil.move(image_file, os.path.join('OLDimages', image_file))
                
                print(f"Converted {image_file} to {new_filename} and moved original to OLDimages")
                processed_files.add(image_file)
                
            except Exception as e:
                print(f"Error processing {image_file}: {str(e)}")

if __name__ == "__main__":
    convert_and_move_images() 