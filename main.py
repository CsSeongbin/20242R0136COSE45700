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
GRAY = (128, 128, 128)

# Create display and background
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Castle Siege Game")
background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
background.fill(WHITE)

# Load fonts once
font_small = pygame.font.SysFont(None, 36)
font_large = pygame.font.SysFont(None, 72)

# Load character info
with open("character_info.json", "r") as file:
    character_info = json.load(file)

# Character types
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magician"]

# Load sprites and idle images
loaded_sprites = {}
idle_sprites = {"left": {}, "right": {}}
for char_type in CHARACTER_TYPES:
    loaded_sprites[char_type] = {
        'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
        'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
    }

    # For left team
    if 'Idle' in loaded_sprites[char_type]['left']:
        image = loaded_sprites[char_type]['left']['Idle'][0]
        image = pygame.transform.scale(image, (40, 40))
        idle_sprites['left'][char_type] = image
    else:
        print(f"No Idle action found for {char_type} left")

    # For right team
    if 'Idle' in loaded_sprites[char_type]['right']:
        image = loaded_sprites[char_type]['right']['Idle'][0]
        image = pygame.transform.scale(image, (40, 40))
        idle_sprites['right'][char_type] = image
    else:
        print(f"No Idle action found for {char_type} right")

# Create castles
left_castle = Castle(x=0, y=0, team='left')
right_castle = Castle(x=SCREEN_WIDTH - 100, y=SCREEN_HEIGHT - 100, team='right')
left_castle.y = SCREEN_HEIGHT - left_castle.height
right_castle.y = SCREEN_HEIGHT - right_castle.height

# Characters and game status
characters = []
game_over = False
winner = None

# Slot management
max_slots = 5
slot_addition_timer = 5000  # ms
last_slot_time = pygame.time.get_ticks()
left_team_slots = []
right_team_slots = []

# Time limits and clocks
game_start_ticks = pygame.time.get_ticks()
time_limit = 5 * 60 * 1000  # 5 minutes in ms
clock = pygame.time.Clock()

# Empty slot image
empty_slot_image = pygame.Surface((40, 40))
empty_slot_image.fill(GRAY)

def spawn_character(team):
    global left_team_slots, right_team_slots, characters
    if team == 'left' and left_team_slots:
        char_type = left_team_slots.pop(0)
        sprites = loaded_sprites[char_type]['left']
        sprite_width = list(sprites.values())[0][0].get_width()
        sprite_height = list(sprites.values())[0][0].get_height()

        # Spawn slightly away from the left castle to avoid immediate blockage
        x = left_castle.x + left_castle.width + 10
        y = SCREEN_HEIGHT - sprite_height

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
        sprite_width = list(sprites.values())[0][0].get_width()
        sprite_height = list(sprites.values())[0][0].get_height()

        # Spawn slightly away from the right castle to avoid immediate blockage
        x = right_castle.x - sprite_width - 10
        y = SCREEN_HEIGHT - sprite_height

        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team='right',
            character_type=char_type,
            character_info=character_info
        )
        characters.append(character)


running = True
while running:
    delta_time = clock.tick(60) / 1000.0

    # Event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and not game_over:
            if event.key == pygame.K_l:
                spawn_character('left')
            elif event.key == pygame.K_r:
                spawn_character('right')
            elif event.key == pygame.K_k:
                # Cycle the left team's slot queue
                if len(left_team_slots) > 0:
                    left_team_slots.append(left_team_slots.pop(0))
            elif event.key == pygame.K_e:
                # Cycle the right team's slot queue
                if len(right_team_slots) > 0:
                    right_team_slots.append(right_team_slots.pop(0))

    # Add one slot with a random character every 5 seconds if available
    current_ticks = pygame.time.get_ticks()
    if current_ticks - last_slot_time >= slot_addition_timer:
        last_slot_time = current_ticks
        if len(left_team_slots) < max_slots:
            left_team_slots.append(random.choice(CHARACTER_TYPES))
        if len(right_team_slots) < max_slots:
            right_team_slots.append(random.choice(CHARACTER_TYPES))

    # Time calculations
    elapsed_ticks = pygame.time.get_ticks() - game_start_ticks
    remaining_ticks = max(0, time_limit - elapsed_ticks)
    remaining_time = remaining_ticks / 1000.0

    # Check time limit
    if remaining_time <= 0 and not game_over:
        game_over = True
        if left_castle.hp > right_castle.hp:
            winner = "Left Team Wins!"
        elif right_castle.hp > left_castle.hp:
            winner = "Right Team Wins!"
        else:
            winner = "Draw!"

    # Draw background and castles
    screen.blit(background, (0, 0))
    left_castle.draw(screen)
    right_castle.draw(screen)

    if not game_over:
        characters_to_remove = []
        for character in characters:
            if character.is_dead_and_animation_completed() or character.has_reached_opposite_side():
                characters_to_remove.append(character)
            else:
                enemies = [c for c in characters if c.team != character.team and c.hp > 0]
                enemy_castle = right_castle if character.team == 'left' else left_castle
                # Update character
                character.update(enemies, enemy_castle, delta_time)
                # Draw character
                character.draw(screen)

        for c in characters_to_remove:
            characters.remove(c)
    else:
        # Game over: switch all characters to idle for a clean end-state
        for character in characters:
            character.switch_to_idle()
            character.draw(screen)

    # Display timer
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    timer_text = font_small.render(f"Time: {minutes:02}:{seconds:02}", True, BLACK)
    screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH / 2, 20)))

    # Display slots for left team
    slot_margin = 5
    left_slot_x_start = left_castle.x
    left_slot_y = left_castle.y - 40 - 20
    for i in range(max_slots):
        slot_rect = pygame.Rect(left_slot_x_start + i * (40 + slot_margin), left_slot_y, 40, 40)
        if i < len(left_team_slots):
            char_type = left_team_slots[i]
            idle_image = idle_sprites["left"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            screen.blit(empty_slot_image, slot_rect)

    # Display slots for right team
    right_slot_x_start = right_castle.x + right_castle.width - (max_slots * (40 + slot_margin) - slot_margin)
    right_slot_y = right_castle.y - 40 - 20
    for i in range(max_slots):
        slot_rect = pygame.Rect(right_slot_x_start + i * (40 + slot_margin), right_slot_y, 40, 40)
        if i < len(right_team_slots):
            char_type = right_team_slots[i]
            idle_image = idle_sprites["right"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            screen.blit(empty_slot_image, slot_rect)

    # Check castles for destruction
    if not game_over:
        if left_castle.is_destroyed():
            game_over = True
            winner = "Right Team Wins!"
        elif right_castle.is_destroyed():
            game_over = True
            winner = "Left Team Wins!"

    # Display winner if game over
    if game_over and winner:
        text = font_large.render(winner, True, BLACK)
        screen.blit(text, text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))

    pygame.display.flip()

pygame.quit()
