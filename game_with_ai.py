# game_with_ai_scroll.py
import pygame
import os
import sys
import json
import time
import random
import numpy as np
from character import Character
from castle import Castle
from utils import load_character_sprites
from rl_agent import DQNAgent

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 720  # Fixed screen width
SCREEN_HEIGHT = 400

# World dimensions (expanded game world)
WORLD_WIDTH = 1440  # Adjust as desired for longer distance between castles

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)

# Load Background
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Castle Siege Game with AI Opponent and Scrollbar")
background = pygame.Surface((WORLD_WIDTH, SCREEN_HEIGHT))
background.fill(WHITE)

# Load character info from JSON file
with open("character_info.json", "r") as file:
    character_info = json.load(file)

# Character types
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magician"]
CHARACTER_TYPE_MAPPING = {name: idx for idx, name in enumerate(CHARACTER_TYPES)}
NUM_CHARACTER_TYPES = len(CHARACTER_TYPES)

# Action types for characters
ACTION_NAMES = ['Walk', 'Run', 'Attack', 'Skill', 'Idle', 'Jump', 'Dead']
ACTION_MAPPING = {name: idx for idx, name in enumerate(ACTION_NAMES)}
NUM_ACTION_TYPES = len(ACTION_NAMES)

# Define the action space
ACTION_SPAWN = 0
ACTION_CHANGE_SLOT = 1
ACTION_DO_NOTHING = 2
ACTION_SPACE_SIZE = 3  # Total number of possible actions

# Maximum number of characters considered on the field
MAX_CHARACTERS = 50

def map_action_name(action_name):
    action_name_lower = action_name.lower()
    if 'walk' in action_name_lower:
        return ACTION_MAPPING['Walk']
    elif 'run' in action_name_lower:
        return ACTION_MAPPING['Run']
    elif 'attack' in action_name_lower:
        return ACTION_MAPPING['Attack']
    elif 'skill' in action_name_lower:
        return ACTION_MAPPING['Skill']
    elif 'idle' in action_name_lower:
        return ACTION_MAPPING['Idle']
    elif 'jump' in action_name_lower:
        return ACTION_MAPPING['Jump']
    elif 'dead' in action_name_lower:
        return ACTION_MAPPING['Dead']
    else:
        return ACTION_MAPPING['Idle']  # Default to 'Idle'

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
right_castle = Castle(x=WORLD_WIDTH - 100, y=0, team='right')  # Use WORLD_WIDTH

left_castle.y = SCREEN_HEIGHT - left_castle.height
right_castle.y = SCREEN_HEIGHT - right_castle.height

# Characters list and game status
characters = []
game_over = False
winner = None

# Slot management
max_slots = 5  # Maximum slots available
slot_addition_timer = 5000  # Time in milliseconds to add one slot
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

# Camera (viewport) position
camera_x = 0  # Start at the leftmost position
camera_speed = 10  # Pixels per frame when scrolling

# Scrollbar dimensions
SCROLLBAR_HEIGHT = 20
scrollbar_rect = pygame.Rect(0, SCREEN_HEIGHT - SCROLLBAR_HEIGHT, SCREEN_WIDTH, SCROLLBAR_HEIGHT)
scroll_thumb_width = 100  # Width of the scroll thumb (adjust as needed)
scroll_thumb_rect = pygame.Rect(0, SCREEN_HEIGHT - SCROLLBAR_HEIGHT, scroll_thumb_width, SCROLLBAR_HEIGHT)
scrolling = False  # Flag to indicate if the scrollbar is being dragged

# Initialize the agent for the right team
state_size = (
    MAX_CHARACTERS * (NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES) +
    2 +  # Castle HPs
    max_slots * (NUM_CHARACTER_TYPES + 1) +
    1  # Time remaining
)

agent = DQNAgent(state_size=state_size, action_size=ACTION_SPACE_SIZE, team='right', max_slots=max_slots)
agent.load('models/dqn_model_best.pth')  # Load the trained model

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
                elif event.key == pygame.K_k:
                    # Move the leftmost character to the end of the left team's slot queue
                    if len(left_team_slots) > 0:
                        character_to_move = left_team_slots.pop(0)
                        left_team_slots.append(character_to_move)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left mouse button
                if scroll_thumb_rect.collidepoint(event.pos):
                    scrolling = True
                    mouse_x, _ = event.pos
                    offset_x = mouse_x - scroll_thumb_rect.x
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                scrolling = False
        elif event.type == pygame.MOUSEMOTION:
            if scrolling:
                mouse_x, _ = event.pos
                # Update scroll thumb position
                new_x = mouse_x - offset_x
                new_x = max(0, min(new_x, SCREEN_WIDTH - scroll_thumb_rect.width))
                scroll_thumb_rect.x = new_x
                # Update camera position based on scroll thumb position
                camera_x = (scroll_thumb_rect.x / (SCREEN_WIDTH - scroll_thumb_rect.width)) * (WORLD_WIDTH - SCREEN_WIDTH)

    current_ticks = pygame.time.get_ticks()
    # Add one slot with a new character type every 5 seconds if slots are available
    if current_ticks - last_slot_time >= slot_addition_timer:
        last_slot_time = current_ticks
        if len(left_team_slots) < max_slots:
            left_team_slots.append(random.choice(CHARACTER_TYPES))
        if len(right_team_slots) < max_slots:
            right_team_slots.append(random.choice(CHARACTER_TYPES))

    # Agent's turn (for the right team)
    # Build state representation
    state_size = (
        MAX_CHARACTERS * (NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES) +
        2 +  # Castle HPs
        agent.max_slots * (NUM_CHARACTER_TYPES + 1) +
        1  # Time remaining
    )
    state = np.zeros(state_size)

    # Characters on the field
    character_features = []
    for c in characters:
        if c.hp > 0:
            # Type one-hot encoding
            type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
            type_one_hot[CHARACTER_TYPE_MAPPING[c.character_type]] = 1

            # Normalize position X (0 to 1)
            x_normalized = c.x / WORLD_WIDTH

            # Team indicator
            team_indicator = 1 if c.team == 'right' else 0

            # Health normalized
            hp_normalized = c.hp / c.max_hp

            # Action one-hot encoding
            action_one_hot = np.zeros(NUM_ACTION_TYPES)
            action_index = map_action_name(c.current_action)
            action_one_hot[action_index] = 1

            # Character feature vector
            char_feature = np.concatenate((type_one_hot, [x_normalized, team_indicator, hp_normalized], action_one_hot))
            character_features.append(char_feature)

    # Pad or truncate to MAX_CHARACTERS
    if len(character_features) > MAX_CHARACTERS:
        character_features = character_features[:MAX_CHARACTERS]
    else:
        for _ in range(MAX_CHARACTERS - len(character_features)):
            character_features.append(np.zeros(NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES))

    # Flatten the character features to form the state vector
    character_features_flat = np.array(character_features).flatten()

    # Castle HPs normalized
    own_castle_hp_normalized = right_castle.hp / right_castle.max_hp
    enemy_castle_hp_normalized = left_castle.hp / left_castle.max_hp
    castle_features = [own_castle_hp_normalized, enemy_castle_hp_normalized]

    # Slot information
    slot_features = []
    for slot in right_team_slots:
        # Slot is filled
        slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
        slot_type_one_hot[CHARACTER_TYPE_MAPPING[slot]] = 1
        slot_filled = 1  # Slot is filled
        slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
        slot_features.append(slot_feature)

    # Pad or truncate to agent.max_slots
    for _ in range(agent.max_slots - len(slot_features)):
        # Empty slot
        slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
        slot_filled = 0
        slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
        slot_features.append(slot_feature)

    slot_features_flat = np.array(slot_features).flatten()

    # Time remaining normalized
    elapsed_ticks = pygame.time.get_ticks() - game_start_ticks
    remaining_ticks = max(0, time_limit - elapsed_ticks)
    remaining_time = remaining_ticks / 1000  # Convert to seconds
    time_remaining_normalized = remaining_time / (time_limit / 1000)  # Normalize to 0..1

    # Combine all features into the state vector
    state = np.concatenate([
        character_features_flat,
        castle_features,
        slot_features_flat,
        [time_remaining_normalized]
    ])

    # Choose an action
    action = agent.choose_action(state)

    # Perform the action
    if action == ACTION_SPAWN:
        if right_team_slots:
            spawn_character('right')
    elif action == ACTION_CHANGE_SLOT:
        if len(right_team_slots) > 1:
            character_to_move = right_team_slots.pop(0)
            right_team_slots.append(character_to_move)
    elif action == ACTION_DO_NOTHING:
        pass  # Do nothing

    # Update and draw game state
    # Clear the background
    background.fill(WHITE)

    # Draw the castles on the background surface
    left_castle.draw(background)
    right_castle.draw(background)

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
                character.draw(background)
        # Remove characters outside the loop
        for character in characters_to_remove:
            characters.remove(character)
    else:
        for character in characters:
            character.switch_to_idle()
            character.draw(background)

    # Blit the portion of the background corresponding to the camera position
    screen.blit(background.subsurface((int(camera_x), 0, SCREEN_WIDTH, SCREEN_HEIGHT)), (0, 0))

    # Display timer at the center of the screen
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    font = pygame.font.SysFont(None, 36)
    timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, BLACK)
    screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH / 2, 20)))

    # Display slots with empty squares and idle images for each team
    slot_margin = 5

    # Left team slots (above the left castle)
    left_slot_x_start = left_castle.x - camera_x  # Adjust for camera position
    left_slot_y = left_castle.y - 40 - 20  # 20 pixels above the castle

    for i in range(max_slots):
        slot_rect = pygame.Rect(
            left_slot_x_start + i * (40 + slot_margin),
            left_slot_y,
            40,
            40
        )
        if slot_rect.right < 0 or slot_rect.left > SCREEN_WIDTH:
            continue  # Skip drawing if slot is outside the current view
        if i < len(left_team_slots):
            # Slot is filled, display the character's idle image
            char_type = left_team_slots[i]
            idle_image = idle_sprites["left"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            # Slot is empty, display the empty slot image
            screen.blit(empty_slot_image, slot_rect)

    # Right team slots (above the right castle)
    right_slot_x_start = right_castle.x + right_castle.width - (max_slots * (40 + slot_margin) - slot_margin) - camera_x
    right_slot_y = right_castle.y - 40 - 20  # 20 pixels above the castle

    for i in range(max_slots):
        slot_rect = pygame.Rect(
            right_slot_x_start + i * (40 + slot_margin),
            right_slot_y,
            40,
            40
        )
        if slot_rect.right < 0 or slot_rect.left > SCREEN_WIDTH:
            continue  # Skip drawing if slot is outside the current view
        if i < len(right_team_slots):
            # Slot is filled, display the character's idle image
            char_type = right_team_slots[i]
            idle_image = idle_sprites["right"][char_type]
            screen.blit(idle_image, slot_rect)
        else:
            # Slot is empty, display the empty slot image
            screen.blit(empty_slot_image, slot_rect)

    # Draw the scrollbar
    pygame.draw.rect(screen, GRAY, scrollbar_rect)
    pygame.draw.rect(screen, BLACK, scroll_thumb_rect)

    # Check if game over
    if not game_over:
        if left_castle.is_destroyed():
            game_over = True
            winner = "Right Team Wins!"
        elif right_castle.is_destroyed():
            game_over = True
            winner = "Left Team Wins!"
        elif remaining_time <= 0:
            game_over = True
            if left_castle.hp > right_castle.hp:
                winner = "Left Team Wins!"
            elif right_castle.hp > left_castle.hp:
                winner = "Right Team Wins!"
            else:
                winner = "Draw!"

    # Display winner text if game is over
    if game_over and winner:
        font = pygame.font.SysFont(None, 72)
        text = font.render(winner, True, BLACK)
        screen.blit(text, text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))

    pygame.display.flip()
    clock.tick(60)  # Limit to 60 FPS

pygame.quit()
