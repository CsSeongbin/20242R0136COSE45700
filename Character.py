import pygame

# Character Class
def load_sprite_sheet(filename):
    sprite_sheet = pygame.image.load(filename).convert_alpha()
    sheet_width, sheet_height = sprite_sheet.get_size()
    num_sprites = sheet_width // sheet_height
    sprite_width = sheet_width // num_sprites
    sprite_height = sheet_height
    sprites = []
    for i in range(num_sprites):
        rect = pygame.Rect(i * sprite_width, 0, sprite_width, sprite_height)
        sprite = sprite_sheet.subsurface(rect)
        sprites.append(sprite)
    return sprites, num_sprites

class Character:
    def __init__(self, sprite_sheet_path, idle_sprite_sheet_path, x, y):
        self.walk_sprites, self.walk_sprite_count = load_sprite_sheet(sprite_sheet_path)
        self.idle_sprites, self.idle_sprite_count = load_sprite_sheet(idle_sprite_sheet_path)
        self.x = x
        self.y = y
        self.sprite_index = 0
        self.is_walking = False
        self.current_sprites = self.idle_sprites
        self.current_sprite_count = self.idle_sprite_count
        self.frame_counter = 0

    def update(self):
        # Update the current sprite list based on movement state
        if self.is_walking:
            self.current_sprites = self.walk_sprites
            self.current_sprite_count = self.walk_sprite_count
        else:
            self.current_sprites = self.idle_sprites
            self.current_sprite_count = self.idle_sprite_count

        # Update the sprite index for animation every 5 frames
        self.frame_counter += 1
        if self.frame_counter % 5 == 0:
            self.sprite_index = (self.sprite_index + 1) % self.current_sprite_count

    def draw(self, surface):
        print(self.sprite_index)
        sprite = self.current_sprites[self.sprite_index]
        surface.blit(sprite, (self.x, self.y))

    def move(self, direction):
        if direction == "left":
            self.x -= 2
        elif direction == "right":
            self.x += 2
        self.is_walking = True

    def stop(self):
        self.is_walking = False