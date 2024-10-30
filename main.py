import pygame
import os
import sys
import json
import time
import random
from character import Character
from castle import Castle
from utils import load_character_sprites

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 400

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)  # Added GRAY color for empty slots

# Load Background
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Castle Siege Game")
background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
background.fill(WHITE)

# Load character info from JSON file
with open("character_info.json", "r") as file:
    character_info = json.load(file)

# Character types
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magician"]

# Load all character sprites, specifically idle images for slot display
loaded_sprites = {}
idle_sprites = {"left": {}, "right": {}}  # Stores idle images for each character type by team

for char_type in CHARACTER_TYPES:
    loaded_sprites[char_type] = {
        'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
        'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
    }
    # Load the idle images for each team from the loaded sprites
    # For left team
    if 'Idle' in loaded_sprites[char_type]['left']:
        image = loaded_sprites[char_type]['left']['Idle'][0]
        # Scale the image to fit the slot size
        image = pygame.transform.scale(image, (40, 40))
        idle_sprites['left'][char_type] = image
    else:
        print(f"No Idle action found for {char_type} left")

    # For right team
    if 'Idle' in loaded_sprites[char_type]['right']:
        image = loaded_sprites[char_type]['right']['Idle'][0]
        # Scale the image to fit the slot size
        image = pygame.transform.scale(image, (40, 40))
        idle_sprites['right'][char_type] = image
    else:
        print(f"No Idle action found for {char_type} right")

# Create castles
left_castle = Castle(x=0, y=0, team='left')
right_castle = Castle(x=SCREEN_WIDTH - 100, y=SCREEN_HEIGHT - 100, team='right')

left_castle.y = SCREEN_HEIGHT - left_castle.height
right_castle.y = SCREEN_HEIGHT - right_castle.height

# Characters list and game status
characters = []
game_over = False
winner = None

# Slot management
max_slots = 5  # Maximum slots available
slot_addition_timer = 5000  # Time in seconds to add one slot
last_slot_time = pygame.time.get_ticks()  # Time tracking for slot additions
left_team_slots = []  # Start with 0 slots for left team
right_team_slots = []  # Start with 0 slots for right team

# Initialize game timer
game_start_ticks = pygame.time.get_ticks()
time_limit = 5 * 60 * 1000  # 5 minutes in milliseconds

# Initialize clock for FPS control
clock = pygame.time.Clock()

# Empty slot image (a gray square)
empty_slot_image = pygame.Surface((40, 40))
empty_slot_image.fill(GRAY)


def spawn_character(team):
    global left_team_slots, right_team_slots
    if team == 'left' and left_team_slots:
        char_type = left_team_slots.pop(0)
        sprites = loaded_sprites[char_type]['left']

        # Spawn at the center of the left castle
        x = left_castle.x + left_castle.width // 2 - list(sprites.values())[0][0].get_width() // 2
        y = SCREEN_HEIGHT - list(sprites.values())[0][0].get_height()

        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team='left',
            character_type=char_type,
            character_info=character_info
        )
        characters.append(character)
    elif team == 'right' and right_team_slots:
        char_type = right_team_slots.pop(0)
        sprites = loaded_sprites[char_type]['right']

        # Spawn at the center of the right castle
        x = right_castle.x + right_castle.width // 2 - list(sprites.values())[0][0].get_width() // 2
        y = SCREEN_HEIGHT - list(sprites.values())[0][0].get_height()

        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team='right',
            character_type=char_type,
            character_info=character_info
        )
        characters.append(character)

# Game loop
running = True
while running:
    delta_time = clock.tick(60) / 1000.0
    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False  # Exit the game loop
        elif event.type == pygame.KEYDOWN:
            if not game_over:
                if event.key == pygame.K_l:
                    spawn_character('left')
                elif event.key == pygame.K_r:
                    spawn_character('right')
                elif event.key == pygame.K_k:
                    # Move the leftmost character to the end of the left team's slot queue
                    if len(left_team_slots) > 0:
                        character_to_move = left_team_slots.pop(0)
                        left_team_slots.append(character_to_move)
                elif event.key == pygame.K_e:
                    # Move the leftmost character to the end of the right team's slot queue
                    if len(right_team_slots) > 0:
                        character_to_move = right_team_slots.pop(0)
                        right_team_slots.append(character_to_move)
    current_ticks = pygame.time.get_ticks()
    # Add one slot with a new character type every 5 seconds if slots are available
    if current_ticks - last_slot_time >= slot_addition_timer:
        last_slot_time = current_ticks
        if len(left_team_slots) < max_slots:
            left_team_slots.append(random.choice(CHARACTER_TYPES))
        if len(right_team_slots) < max_slots:
            right_team_slots.append(random.choice(CHARACTER_TYPES))

    # In the game loop, calculate remaining time
    elapsed_ticks = pygame.time.get_ticks() - game_start_ticks
    remaining_ticks = max(0, time_limit - elapsed_ticks)
    remaining_time = remaining_ticks / 1000  # Convert to seconds

    # Check if the time limit is reached
    if remaining_time <= 0 and not game_over:
        game_over = True
        if left_castle.hp > right_castle.hp:
            winner = "Left Team Wins!"
        elif right_castle.hp > left_castle.hp:
            winner = "Right Team Wins!"
        else:
            winner = "Draw!"

    # Update and draw game state
    screen.blit(background, (0, 0))
    left_castle.draw(screen)
    right_castle.draw(screen)

    if not game_over:
        characters_to_remove = []
        for character in characters:
            if character.is_dead_and_animation_completed() or character.has_reached_opposite_side():
                characters_to_remove.append(character)
            else:
                # Update and draw the character
                enemies = [c for c in characters if c.team != character.team and c.hp > 0]
                enemy_castle = right_castle if character.team == 'left' else left_castle
                character.update(enemies, enemy_castle, delta_time)
                character.draw(screen)
        # Remove characters outside the loop
        for character in characters_to_remove:
            characters.remove(character)
    else:
        for character in characters:
            character.switch_to_idle()
            character.draw(screen)

    # Display timer at the center of the screen
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    font = pygame.font.SysFont(None, 36)
    timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, BLACK)
    screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH / 2, 20)))

    # Display slots with empty squares and idle images for each team
    slot_margin = 5

    # Left team slots (above the left castle)
    left_slot_x_start = left_castle.x  # Start at the left side of the castle
    left_slot_y = left_castle.y - 40 - 20  # 20 pixels above the castle

    for i in range(max_slots):
        slot_rect = pygame.Rect(
            left_slot_x_start + i * (40 + slot_margin),
            left_slot_y,
            40,
            40
        )
        if i < len(left_team_slots):
            # Slot is filled, display the character's idle image
            char_type = left_team_slots[i]
            idle_image = idle_sprites["left"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            # Slot is empty, display the empty slot image
            screen.blit(empty_slot_image, slot_rect)

    # Right team slots (above the right castle)
    right_slot_x_start = right_castle.x + right_castle.width - (max_slots * (40 + slot_margin) - slot_margin)
    right_slot_y = right_castle.y - 40 - 20  # 20 pixels above the castle

    for i in range(max_slots):
        slot_rect = pygame.Rect(
            right_slot_x_start + i * (40 + slot_margin),
            right_slot_y,
            40,
            40
        )
        if i < len(right_team_slots):
            # Slot is filled, display the character's idle image
            char_type = right_team_slots[i]
            idle_image = idle_sprites["right"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            # Slot is empty, display the empty slot image
            screen.blit(empty_slot_image, slot_rect)

    # Check if game over
    if not game_over:
        if left_castle.is_destroyed():
            game_over = True
            winner = "Right Team Wins!"
        elif right_castle.is_destroyed():
            game_over = True
            winner = "Left Team Wins!"

    # Display winner text if game is over
    if game_over and winner:
        font = pygame.font.SysFont(None, 72)
        text = font.render(winner, True, BLACK)
        screen.blit(text, text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))

    pygame.display.flip()
    clock.tick(60)  # Limit to 60 FPS

pygame.quit()
