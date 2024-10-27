from PIL import Image
import os

# Get the current working directory
current_directory = os.getcwd()

# Iterate through all files in the current directory
for filename in os.listdir(current_directory):
    if filename.endswith('.png'):
        # Open the image file
        image_path = os.path.join(current_directory, filename)
        with Image.open(image_path) as img:
            # Flip the image by Y-axis
            flipped_img = img.transpose(method=Image.FLIP_LEFT_RIGHT)
            
            # Save the flipped image with a new name
            flipped_image_path = os.path.join(current_directory, f"flipped_{filename}")
            flipped_img.save(flipped_image_path)

print("All PNG files have been flipped by the Y-axis.")
