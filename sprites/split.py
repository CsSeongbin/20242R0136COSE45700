from PIL import Image
import os

def split_image_auto(input_image_path, output_dir):
    """
    Splits an image into sub-images where each sub-image's width equals the height of the original image,
    flips the image horizontally if the side is 'right', 
    and names the parts using the format {original_image_name}_left/right_{0-99}.

    :param input_image_path: Path to the input image
    :param output_dir: Directory where the sub-images will be saved
    """
    # Open the input image
    image = Image.open(input_image_path)
    width, height = image.size

    # Define sub-image width as the height of the image
    sub_width = height

    # Calculate the number of sub-images
    cols = width // sub_width

    # Extract the original image name (without extension)
    original_name = os.path.splitext(os.path.basename(input_image_path))[0]

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Determine the side ("left" or "right") based on the file path
    side = input_image_path.split('/')[0].lower()  # Extract and convert side to lowercase

    # Loop through and split the image
    for col in range(cols):
        left = col * sub_width
        right = left + sub_width

        cropped_image = image.crop((left, 0, right, height))
        
        # Flip the image horizontally if the side is 'right'
        if side == 'right':
            cropped_image = cropped_image.transpose(Image.FLIP_LEFT_RIGHT)
        
        filename = f"{output_dir}/{original_name}_{side}_{col}.png"
        
        cropped_image.save(filename)
        print(f"Saved: {filename}")

# Example usage
# Replace 'input_image.png' with your input image path and 'output_folder' with your output directory
split_image_auto('right/Wanderer_Magician/skill1.png', 'right/Wanderer_Magician')
