import pygame
import os
import sys
import random
import re

# Initialize Pygame
pygame.init()

# Constants for the screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 400

# Colors
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Castle Siege Game with Resized Castles")

# Load Background
background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
background.fill(WHITE)

# Castle Class
class Castle:
    def __init__(self, x, y, team):
        self.x = x
        self.y = y
        self.team = team
        self.hp = 1000
        self.max_hp = 1000

        # Desired castle width
        self.desired_width = 100  # Adjust as needed

        # Load castle images for different HP levels and resize them
        self.images = {}
        for hp_level in [100, 50, 0]:
            image_name = f"castle_{team}_{hp_level}.png"
            image_path = os.path.join('sprites',team,'castle' ,image_name)
            if os.path.exists(image_path):
                image = pygame.image.load(image_path).convert_alpha()
                # Scale the image to the desired width, maintaining aspect ratio
                aspect_ratio = image.get_height() / image.get_width()
                desired_height = int(self.desired_width * aspect_ratio)
                scaled_image = pygame.transform.scale(image, (self.desired_width, desired_height))
                self.images[hp_level] = scaled_image
            else:
                # If image does not exist, use a placeholder
                desired_height = 150  # Default height
                self.images[hp_level] = pygame.Surface((self.desired_width, desired_height), pygame.SRCALPHA)
                self.images[hp_level].fill((150, 150, 150, 255))

        # Set initial image
        self.update_image()

        self.width = self.current_image.get_width()
        self.height = self.current_image.get_height()

    def update_image(self):
        # Update the castle image based on current HP
        hp_ratio = self.hp / self.max_hp
        if hp_ratio > 0.5:
            self.current_image = self.images[100]
        elif hp_ratio > 0:
            self.current_image = self.images[50]
        else:
            self.current_image = self.images[0]

    def draw(self, surface):
        # Draw the castle image
        surface.blit(self.current_image, (self.x, self.y))

        # Draw HP bar above the castle
        bar_width = self.width
        bar_height = 10
        hp_ratio = self.hp / self.max_hp
        bar_x = self.x
        bar_y = self.y - bar_height - 5  # 5 pixels above the castle
        # Draw background bar (gray)
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, bar_height))
        # Draw HP bar (green to red based on HP)
        hp_color = (255 * (1 - hp_ratio), 255 * hp_ratio, 0)
        pygame.draw.rect(surface, hp_color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0:
            self.hp = 0
        # Update the castle image based on new HP
        self.update_image()

    def is_destroyed(self):
        return self.hp <= 0

# Character Class
class Character:
    def __init__(self, sprites, x, y, team, character_type):
        self.sprites = sprites  # Dict of actions and their frames
        self.x = x
        self.y = y
        self.team = team
        self.character_type = character_type

        # Original Y position for resetting after jump
        self.original_y = y

        # Health Points
        self.hp = 100

        # Attack Range based on character type
        attack_ranges = {
            'Fire_vizard': 200,
            'Lightning_Mage': 300,
            'Wanderer_Magican': 100
        }
        self.attack_range = attack_ranges.get(character_type, 100)

        # Damage to deal
        self.damage = 10

        # Build lists of movement and attack actions
        movement_action_names = ['walk', 'idle', 'run']
        attack_action_names = ['attack', 'skill', 'jump']

        self.movement_actions = [
            action for action in self.sprites.keys()
            if any(action.lower().startswith(name) for name in movement_action_names)
        ]

        self.attack_actions = [
            action for action in self.sprites.keys()
            if any(action.lower().startswith(name) for name in attack_action_names)
            and action.lower() != 'dead'
        ]

        # Create a list of attack actions excluding 'Jump' for attacking the castle
        self.attack_actions_no_jump = [
            action for action in self.attack_actions
            if not action.lower().startswith('jump')
        ]

        # Start with a random movement action
        self.current_action = random.choice(self.movement_actions)
        self.current_sprites = self.sprites[self.current_action]
        self.sprite_index = 0
        self.frame_counter = 0
        self.action_in_progress = True

        # Flag to check if damage has been applied for current attack
        self.damage_applied = False

        # Flag to indicate if character is dead and dead animation is completed
        self.dead_animation_completed = False

        # Variables for jump mechanics
        self.is_jumping = False

        # Target (can be an enemy character or enemy castle)
        self.target = None

    def update(self, enemies, enemy_castle):
        # If character is dead
        if self.hp <= 0:
            # Handle death animation
            self.handle_death()
            return  # No further updates if dead

        # Initialize castle_in_range
        castle_in_range = False

        # Skip enemy detection if character is jumping
        if self.current_action.lower().startswith('jump'):
            enemy_in_range = None
            # Do not detect the castle while jumping
            castle_in_range = False
        else:
            # Check if there are enemies within attack range and in front
            enemy_in_range = None
            for enemy in enemies:
                # Skip enemies that are jumping
                if enemy.current_action.lower().startswith('jump'):
                    continue

                if enemy.team != self.team and enemy.hp > 0:
                    if self.team == 'left' and enemy.x > self.x:
                        distance = enemy.x - self.x
                        if distance <= self.attack_range:
                            enemy_in_range = enemy
                            break  # Attack the first enemy in front and within range
                    elif self.team == 'right' and enemy.x < self.x:
                        distance = self.x - enemy.x
                        if distance <= self.attack_range:
                            enemy_in_range = enemy
                            break  # Attack the first enemy in front and within range

            # If no enemy character is in range, check if enemy castle is in range
            if enemy_in_range is None:
                if self.team == 'left' and enemy_castle.x > self.x:
                    distance = enemy_castle.x - self.x
                    if distance <= self.attack_range:
                        castle_in_range = True
                elif self.team == 'right' and enemy_castle.x < self.x:
                    distance = self.x - enemy_castle.x
                    if distance <= self.attack_range:
                        castle_in_range = True
                else:
                    castle_in_range = False
            else:
                castle_in_range = False

        # Interrupt movement actions if enemy comes into range
        if (enemy_in_range or castle_in_range) and self.current_action in self.movement_actions:
            # Determine available attack actions
            if castle_in_range:
                # Exclude 'Jump' when attacking castle
                available_attack_actions = self.attack_actions_no_jump
            else:
                available_attack_actions = self.attack_actions

            # Choose a random attack action
            if available_attack_actions:
                self.current_action = random.choice(available_attack_actions)
                self.current_sprites = self.sprites[self.current_action]
                self.sprite_index = 0
                self.action_in_progress = True
                self.damage_applied = False  # Reset damage flag
                self.frame_counter = 0  # Reset frame counter

                # Set target
                if enemy_in_range:
                    self.target = enemy_in_range
                elif castle_in_range:
                    self.target = enemy_castle

                # Check if the chosen action is 'Jump'
                if self.current_action.lower().startswith('jump'):
                    self.is_jumping = True  # Start jumping

        # Update the frame counter
        self.frame_counter += 1

        # Update the sprite index for animation every 5 frames
        if self.frame_counter % 5 == 0:
            self.sprite_index += 1

            if self.sprite_index >= len(self.current_sprites):
                # Current action is complete
                self.sprite_index = 0
                self.action_in_progress = False

                # After completing an attack action, apply damage
                if self.current_action in self.attack_actions and not self.damage_applied:
                    if self.target and not (isinstance(self.target, Character) and self.target.current_action.lower().startswith('jump')):
                        self.target.take_damage(self.damage)
                    self.damage_applied = True
                    self.target = None  # Reset target after attack

                # Reset position after jump
                if self.current_action.lower().startswith('jump'):
                    self.y = self.original_y  # Reset Y position after jump

        # If action is not in progress, decide next action
        if not self.action_in_progress:
            if enemy_in_range or castle_in_range:
                # Determine available attack actions
                if castle_in_range:
                    # Exclude 'Jump' when attacking castle
                    available_attack_actions = self.attack_actions_no_jump
                else:
                    available_attack_actions = self.attack_actions

                # Choose a random attack action
                if available_attack_actions:
                    self.current_action = random.choice(available_attack_actions)
                    self.current_sprites = self.sprites[self.current_action]
                    self.sprite_index = 0
                    self.action_in_progress = True
                    self.damage_applied = False  # Reset damage flag
                    self.frame_counter = 0  # Reset frame counter

                    # Set target
                    if enemy_in_range:
                        self.target = enemy_in_range
                    elif castle_in_range:
                        self.target = enemy_castle

                    # Check if the chosen action is 'Jump'
                    if self.current_action.lower().startswith('jump'):
                        self.is_jumping = True  # Start jumping
            else:
                # If no enemy is in range, choose a movement action
                if self.movement_actions:
                    self.current_action = random.choice(self.movement_actions)
                    self.current_sprites = self.sprites[self.current_action]
                    self.sprite_index = 0
                    self.action_in_progress = True
                    self.frame_counter = 0  # Reset frame counter

        # Move the character based on the current action
        self.move()

    def move(self):
        # Handle movement based on current action
        if self.current_action.lower().startswith('walk'):
            self.move_forward(speed=2)
        elif self.current_action.lower().startswith('run'):
            self.move_forward(speed=4)
        elif self.current_action.lower().startswith('jump'):
            self.jump_over_enemy()
        # No movement during attack or other actions

    def move_forward(self, speed):
        if self.team == 'left':
            self.x += speed  # Move right
        else:
            self.x -= speed  # Move left

    def jump_over_enemy(self):
        # Move forward while simulating a jump arc
        jump_height = 50  # Maximum height of the jump
        jump_duration = len(self.current_sprites)  # Total frames in the jump animation

        # Calculate movement per frame
        speed = 3  # Horizontal speed during jump
        if self.team == 'left':
            self.x += speed  # Move right
        else:
            self.x -= speed  # Move left

        # Simulate jump arc by adjusting y position
        frame_ratio = self.sprite_index / (jump_duration - 1) if jump_duration > 1 else 0
        if frame_ratio <= 0.5:
            # Ascending
            self.y = self.original_y - (jump_height * (frame_ratio * 2))
        else:
            # Descending
            self.y = self.original_y - (jump_height * (1 - (frame_ratio - 0.5) * 2))

        # Ensure y does not go below ground level
        ground_y = self.original_y
        if self.y > ground_y:
            self.y = ground_y

        # Check if jump is completed
        if self.sprite_index >= len(self.current_sprites) - 1:
            self.is_jumping = False  # Jump completed
            self.y = self.original_y  # Reset Y position after jump

    def handle_death(self):
        # If dead animation is not yet completed
        if not self.dead_animation_completed:
            # If not already in 'Dead' action, switch to it
            if self.current_action != 'Dead' and 'Dead' in self.sprites:
                self.current_action = 'Dead'
                self.current_sprites = self.sprites[self.current_action]
                self.sprite_index = 0
                self.action_in_progress = True
                self.frame_counter = 0  # Reset frame counter

            # Update the frame counter
            self.frame_counter += 1

            # Update the sprite index for animation every 5 frames
            if self.frame_counter % 5 == 0:
                self.sprite_index += 1

                if self.sprite_index >= len(self.current_sprites):
                    # Dead animation is complete
                    self.dead_animation_completed = True

    def switch_to_idle(self):
        # Switch to 'Idle' action if not already in 'Idle' and character is alive
        if self.hp > 0 and self.current_action != 'Idle' and 'Idle' in self.sprites:
            self.current_action = 'Idle'
            self.current_sprites = self.sprites[self.current_action]
            self.sprite_index = 0
            self.action_in_progress = True
            self.frame_counter = 0  # Reset frame counter

    def draw(self, surface):
        # If dead animation is completed, do not draw the character
        if self.dead_animation_completed:
            return

        sprite = self.current_sprites[self.sprite_index]
        surface.blit(sprite, (self.x, self.y))

        # Draw HP bar if character is alive
        if self.hp > 0:
            # Define HP bar dimensions
            bar_width = 50
            bar_height = 5
            # Calculate HP ratio
            hp_ratio = self.hp / 100
            # Define bar position
            bar_x = self.x + (sprite.get_width() - bar_width) / 2
            bar_y = self.y - bar_height - 5  # 5 pixels above the sprite
            # Draw background bar (gray)
            pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, bar_height))
            # Draw HP bar (green to red based on HP)
            hp_color = (255 * (1 - hp_ratio), 255 * hp_ratio, 0)
            pygame.draw.rect(surface, hp_color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))

    def has_reached_opposite_side(self):
        # If character is dead, they don't move off the screen
        if self.hp <= 0:
            return False
        return self.x < 0 or self.x > SCREEN_WIDTH

    def is_dead_and_animation_completed(self):
        return self.dead_animation_completed

    def take_damage(self, amount):
        self.hp -= amount
        # If HP drops to zero or below, initiate dead action
        if self.hp <= 0:
            self.hp = 0
            # Switching to 'Dead' action will be handled in update method

# Function to load sprites from folders
def load_character_sprites(folder_path):
    action_sprites = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.png'):
            # Skip original images without '_left_' or '_right_' and frame number
            if not re.search(r'_(left|right)_\d+\.png$', file_name):
                continue  # Skip this file

            # Extract action name and frame number using regex
            match = re.match(r'(.+)_(left|right)_(\d+)\.png$', file_name)
            if match:
                action_base_name = match.group(1)  # e.g., 'Attack_1'
                direction = match.group(2)         # 'left' or 'right'
                frame_number = int(match.group(3)) # Frame number

                action_name = action_base_name  # Use action base name without direction

                # Load the image
                image = pygame.image.load(os.path.join(folder_path, file_name)).convert_alpha()
                if action_name not in action_sprites:
                    action_sprites[action_name] = []
                action_sprites[action_name].append((frame_number, image))
    # Sort the frames in each action by frame number
    for action_name in action_sprites:
        action_sprites[action_name].sort(key=lambda x: x[0])
        # Replace list of tuples with list of images
        action_sprites[action_name] = [image for frame_number, image in action_sprites[action_name]]
    return action_sprites

# Character Types
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magican"]

# Load all character sprites
loaded_sprites = {}
for char_type in CHARACTER_TYPES:
    loaded_sprites[char_type] = {}
    for team in ['left', 'right']:
        folder_path = os.path.join('sprites', team, char_type)
        action_sprites = load_character_sprites(folder_path)
        loaded_sprites[char_type][team] = action_sprites

# Create castles
left_castle = Castle(x=0, y=0, team='left')
right_castle = Castle(x=SCREEN_WIDTH - left_castle.width, y=0, team='right')

# Adjust castle Y positions based on their heights
left_castle.y = SCREEN_HEIGHT - left_castle.height
right_castle.y = SCREEN_HEIGHT - right_castle.height

# List to hold all characters
characters = []

# Game Over Flag
game_over = False
winner = None

# Game Loop
running = True
while running:
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if not game_over:
                if event.key == pygame.K_l:
                    # Generate character on the left
                    char_type = random.choice(list(loaded_sprites.keys()))
                    sprites = loaded_sprites[char_type]['left']
                    if sprites:
                        x = left_castle.x + left_castle.width  # Spawn in front of the left castle
                        # Get character sprite height
                        character_height = list(sprites.values())[0][0].get_height()
                        y = SCREEN_HEIGHT - character_height
                        character = Character(sprites, x, y, team='left', character_type=char_type)
                        characters.append(character)
                elif event.key == pygame.K_r:
                    # Generate character on the right
                    char_type = random.choice(list(loaded_sprites.keys()))
                    sprites = loaded_sprites[char_type]['right']
                    if sprites:
                        x = right_castle.x - list(sprites.values())[0][0].get_width()  # Spawn in front of the right castle
                        # Get character sprite height
                        character_height = list(sprites.values())[0][0].get_height()
                        y = SCREEN_HEIGHT - character_height
                        character = Character(sprites, x, y, team='right', character_type=char_type)
                        characters.append(character)

    # Clear screen and draw background
    screen.blit(background, (0, 0))

    # Draw castles
    left_castle.draw(screen)
    right_castle.draw(screen)

    # Update and draw characters
    if not game_over:
        for character in characters[:]:
            enemies = [c for c in characters if c != character]
            enemy_castle = right_castle if character.team == 'left' else left_castle
            character.update(enemies, enemy_castle)
            character.draw(screen)
            # Remove character if dead animation is completed or reaches opposite side
            if character.is_dead_and_animation_completed() or character.has_reached_opposite_side():
                characters.remove(character)
    else:
        # Game over: all characters stay in idle
        for character in characters:
            character.switch_to_idle()
            character.draw(screen)

    # Check for game over
    if not game_over:
        if left_castle.is_destroyed():
            game_over = True
            winner = "Right Team Wins!"
        elif right_castle.is_destroyed():
            game_over = True
            winner = "Left Team Wins!"

    # Display winner if game is over
    if game_over and winner:
        font = pygame.font.SysFont(None, 72)
        text = font.render(winner, True, BLACK)
        text_rect = text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        screen.blit(text, text_rect)

    # Refresh the display
    pygame.display.flip()

    # Frame rate
    pygame.time.delay(30)

pygame.quit()