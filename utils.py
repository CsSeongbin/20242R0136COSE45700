import os
import pygame
import re

def load_character_sprites(folder_path):
    action_sprites = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.png'):
            match = re.match(r'(.+)_(left|right)_(\d+)\.png$', file_name)
            if match:
                action_name = match.group(1)
                frame_number = int(match.group(3))
                image = pygame.image.load(os.path.join(folder_path, file_name)).convert_alpha()
                if action_name not in action_sprites:
                    action_sprites[action_name] = []
                action_sprites[action_name].append((frame_number, image))
    for action_name in action_sprites:
        action_sprites[action_name].sort(key=lambda x: x[0])
        action_sprites[action_name] = [image for _, image in action_sprites[action_name]]
    return action_sprites
