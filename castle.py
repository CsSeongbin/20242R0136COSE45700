# castle.py

import pygame
import os

class Castle:
    def __init__(self, x, y, team, hp=1000, render=True, scale=1.2):
        self.x = x
        self.y = y
        self.team = team.lower()  # Ensure team is lowercase ('left' or 'right')
        self.hp = hp
        self.max_hp = hp
        self.render = render
        self.scale = scale  # Scaling factor

        # Define HP thresholds
        self.full_hp_threshold = 0.5  # 50%
        self.destroyed_threshold = 0   # 0%

        # Map HP thresholds to corresponding image filenames
        self.hp_to_image = {
            'full': f"castle_{self.team}_0.png",
            'half': f"castle_{self.team}_50.png",
            'destroyed': f"castle_{self.team}_100.png"
        }

        # Load images
        self.images = self.load_images()

        # Set current image based on initial HP
        self.current_image = self.get_current_image()

        # Set width and height based on the current image
        if self.current_image:
            self.width = self.current_image.get_width()
            self.height = self.current_image.get_height()
        else:
            self.width = int(100 * self.scale)  # Default width scaled
            self.height = int(100 * self.scale)  # Default height scaled

    def load_images(self):
        """
        Load images for each HP state.
        """
        images = {}
        folder = os.path.join('sprites', self.team, 'castle')
        for stage, filename in self.hp_to_image.items():
            image_path = os.path.join(folder, filename)
            if os.path.exists(image_path):
                try:
                    image = pygame.image.load(image_path).convert_alpha()
                    # Apply scaling based on the scale attribute
                    width = int(100 * self.scale)  # Base width 100
                    height = int(100 * self.scale)  # Base height 100
                    image = pygame.transform.scale(image, (width, height))
                    images[stage] = image
                except pygame.error as e:
                    print(f"Error loading image '{image_path}': {e}")
                    images[stage] = None
            else:
                print(f"Warning: Image '{image_path}' does not exist.")
                images[stage] = None
        return images

    def get_current_image(self):
        """
        Determine which image to display based on current HP.
        """
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0.0

        if hp_ratio > self.full_hp_threshold:
            stage = 'full'
        elif hp_ratio > self.destroyed_threshold:
            stage = 'half'
        else:
            stage = 'destroyed'

        return self.images.get(stage, None)

    def update(self):
        """
        Update the current image based on HP changes.
        """
        new_image = self.get_current_image()
        if new_image != self.current_image:
            self.current_image = new_image
            if self.current_image:
                self.width = self.current_image.get_width()
                self.height = self.current_image.get_height()
            else:
                self.width = int(100 * self.scale)
                self.height = int(100 * self.scale)  # Default size if image fails to load

    def draw(self, surface, camera_offset=0):
        """
        Draw the current sprite and HP bar on the given surface.
        """
        if not self.render:
            return

        if self.current_image:
            draw_x = self.x - camera_offset
            draw_y = self.y
            surface.blit(self.current_image, (draw_x, draw_y))
        else:
            # Draw a placeholder rectangle if image is missing
            pygame.draw.rect(surface, (255, 0, 0), (self.x - camera_offset, self.y, self.width, self.height))

        # Draw HP bar above the castle
        bar_width = self.width
        bar_height = 10
        hp_ratio = self.hp / self.max_hp if self.max_hp > 0 else 0.0
        bar_x = self.x - camera_offset
        bar_y = self.y - self.height - bar_height - 5  # Adjusted y based on scaled height

        # Background bar
        pygame.draw.rect(surface, (128, 128, 128), (bar_x, bar_y, bar_width, bar_height))
        # HP bar
        pygame.draw.rect(surface, (255 * (1 - hp_ratio), 255 * hp_ratio, 0),
                         (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def take_damage(self, amount):
        """
        Reduce the castle's HP by the specified amount.
        """
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0

    def is_destroyed(self):
        """
        Check if the castle is destroyed.
        """
        return self.hp <= 0
