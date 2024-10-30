import pygame
import os

class Castle:
    def __init__(self, x, y, team, hp=1000, render=True):
        self.x = x
        self.y = y
        self.team = team
        self.hp = hp
        self.max_hp = hp
        self.width = 100  # Default width
        self.height = 100  # Default height
        self.images = []
        self.image_index = 0
        self.animation_counter = 0
        self.animation_speed = 5  # Adjust as needed

        if render:
            self.images = self.load_images()
            # Set width and height based on the first image
            if self.images:
                self.width = self.images[0].get_width()
                self.height = self.images[0].get_height()

    def load_images(self):
        images = []
        folder = os.path.join('sprites', self.team, 'castle')
        for file_name in sorted(os.listdir(folder)):
            if file_name.endswith('.png'):
                image_path = os.path.join(folder, file_name)
                image = pygame.image.load(image_path).convert_alpha()
                # Scale the image
                image = pygame.transform.scale(image, (100, 100))  # Adjust size as needed
                images.append(image)
        return images

    def update(self):
        if self.images:
            self.animation_counter += 1
            if self.animation_counter % self.animation_speed == 0:
                self.image_index = (self.image_index + 1) % len(self.images)

    def draw(self, surface):
        if self.images:
            image = self.images[self.image_index]
            surface.blit(image, (self.x, self.y))
            # Draw HP bar
            bar_width = self.width
            bar_height = 10
            hp_ratio = self.hp / self.max_hp
            bar_x = self.x
            bar_y = self.y - bar_height - 5
            pygame.draw.rect(surface, (128, 128, 128), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(surface, (255 * (1 - hp_ratio), 255 * hp_ratio, 0), (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0

    def is_destroyed(self):
        return self.hp <= 0
