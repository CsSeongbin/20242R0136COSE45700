import pygame
import os

# Initialize Pygame
pygame.init()

# Constants for the screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400

# Colors
WHITE = (255, 255, 255)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Generate Sprites")

# Character Class
def load_sprite_sheet(filename, flip=False):
    sprite_sheet = pygame.image.load(filename).convert_alpha()
    sheet_width, sheet_height = sprite_sheet.get_size()
    num_sprites = sheet_width // sheet_height
    sprite_width = sheet_width // num_sprites
    sprite_height = sheet_height
    sprites = []
    for i in range(num_sprites):
        rect = pygame.Rect(i * sprite_width, 0, sprite_width, sprite_height)
        sprite = sprite_sheet.subsurface(rect)
        if flip:
            sprite = pygame.transform.flip(sprite, True, False)
        sprites.append(sprite)
    return sprites, num_sprites

# Character Types
CHARACTER_TYPES = {
    "fire_vizard": "sprites/left/Fire_vizard",
    "lightning_mage": "sprites/left/Lightning_Mage",
    "wanderer_magican": "sprites/left/Wanderer_Magican"
}

# Generate left-facing and right-facing sprites and save them
for char_type, folder_path in CHARACTER_TYPES.items():
    left_folder_path = folder_path
    right_folder_path = folder_path.replace("left", "right")
    
    # Create directories if they do not exist
    if not os.path.exists(left_folder_path):
        os.makedirs(left_folder_path)
    if not os.path.exists(right_folder_path):
        os.makedirs(right_folder_path)
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".png"):
            # Load left-facing sprites
            sprites, sprite_count = load_sprite_sheet(os.path.join(folder_path, file_name))
            # Save each sprite as an individual image for left-facing character
            for i, sprite in enumerate(sprites):
                left_sprite_filename = os.path.join(left_folder_path, f"{file_name[:-4]}_left_{i}.png")
                pygame.image.save(sprite, left_sprite_filename)
            
            # Load right-facing sprites (flipped version)
            right_sprites, right_sprite_count = load_sprite_sheet(os.path.join(folder_path, file_name), flip=True)
            # Save each sprite as an individual image for right-facing character
            for i, sprite in enumerate(right_sprites):
                right_sprite_filename = os.path.join(right_folder_path, f"{file_name[:-4]}_right_{i}.png")
                pygame.image.save(sprite, right_sprite_filename)

print("Left-facing and right-facing sprites have been generated and saved.")

pygame.quit()
