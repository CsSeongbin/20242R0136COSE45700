# train_agent.py

import random
import os
import numpy as np
import pygame
from character import Character, load_character_info
from castle import Castle
from utils import load_character_sprites
import csv
from rl_agent import AIPlayerAgent  
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import re, glob

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =============================
# Game Constants and Configuration
# =============================

@dataclass
class GameConfig:
    WORLD_WIDTH: int = 1440
    SCREEN_WIDTH: int = 1440
    SCREEN_HEIGHT: int = 400
    UI_HEIGHT: int = 100
    WINDOW_HEIGHT: int = SCREEN_HEIGHT + UI_HEIGHT
    MAX_CHARACTERS: int = 50
    SPAWN_COST: int = 20
    MAX_GAGE: int = 200
    TIME_LIMIT: int = 180  # 3 minutes
    GAGE_INCREMENT: int = 4
    FPS: int = 60

    # Colors
    WHITE: Tuple[int, ...] = (255, 255, 255)
    BLACK: Tuple[int, ...] = (0, 0, 0)
    GRAY: Tuple[int, ...] = (128, 128, 128)
    BLUE: Tuple[int, ...] = (0, 0, 255)
    RED: Tuple[int, ...] = (255, 0, 0)

# Load configuration
CONFIG = GameConfig()

# Load character types from character_info.json
try:
    CHARACTER_INFO = load_character_info()
    CHARACTER_TYPES = list(CHARACTER_INFO.keys())
    NUM_CHARACTER_TYPES = len(CHARACTER_TYPES)
except Exception as e:
    logging.error(f"Failed to load character info: {e}")
    raise

CHARACTER_ACTIONS = ['Walk', 'Run', 'Attack', 'Skill', 'Idle']
CHARACTER_ACTION_SPACE_SIZE = len(CHARACTER_ACTIONS)

# Spawn Actions
class SpawnActions:
    SPAWN_FIRE_VIZARD = 0
    SPAWN_LIGHTNING_MAGE = 1
    SPAWN_WANDERER_MAGICIAN = 2
    DO_NOTHING = 3
    SPACE_SIZE = 4

# =============================
# State Building Functions
# =============================

def build_character_state(character: Character, 
                         characters: List[Character], 
                         enemy_castle: Castle) -> np.ndarray:
    """Builds a state vector for a single character."""
    
    # Basic character stats
    own_hp_ratio = character.hp / character.max_hp if character.max_hp > 0 else 0.0
    own_position_norm = character.x / CONFIG.WORLD_WIDTH
    
    # Distance features
    distance_to_castle = abs(character.x - enemy_castle.x) / CONFIG.WORLD_WIDTH
    castle_hp_ratio = enemy_castle.hp / enemy_castle.max_hp
    
    # Enemy analysis
    enemies = [c for c in characters if c.team != character.team and c.hp > 0]
    closest_enemy_dist = 1.0
    closest_enemy_hp_ratio = 0.0
    
    if enemies:
        distances = [(abs(character.x - e.x), e.hp / e.max_hp) for e in enemies]
        closest_idx = min(range(len(distances)), key=lambda i: distances[i][0])
        closest_enemy_dist = distances[closest_idx][0] / CONFIG.WORLD_WIDTH
        closest_enemy_hp_ratio = distances[closest_idx][1]
    
    # Team composition
    ally_counts = np.zeros(NUM_CHARACTER_TYPES, dtype=np.float32)
    enemy_counts = np.zeros(NUM_CHARACTER_TYPES, dtype=np.float32)
    
    for char in characters:
        if char.hp <= 0:
            continue
        counts = ally_counts if char.team == character.team else enemy_counts
        counts[CHARACTER_TYPES.index(char.character_type)] += 1
    
    # Normalize counts
    max_count = CONFIG.MAX_CHARACTERS / 2
    ally_counts /= max_count
    enemy_counts /= max_count
    
    state = np.concatenate([
        [own_hp_ratio, own_position_norm, distance_to_castle, 
         castle_hp_ratio, closest_enemy_dist, closest_enemy_hp_ratio],
        ally_counts,
        enemy_counts
    ])
    
    return state.astype(np.float32)

def build_spawn_state(left_castle: Castle, 
                     right_castle: Castle,
                     characters: List[Character],
                     left_gage: float,
                     right_gage: float) -> np.ndarray:
    """Builds a spawn state vector."""
    
    # Castle status
    left_castle_hp_ratio = left_castle.hp / left_castle.max_hp
    right_castle_hp_ratio = right_castle.hp / right_castle.max_hp
    
    # Resource management
    left_gage_ratio = left_gage / CONFIG.MAX_GAGE
    right_gage_ratio = right_gage / CONFIG.MAX_GAGE
    
    # Team analysis
    alive_characters = [c for c in characters if c.hp > 0]
    left_team = [c for c in alive_characters if c.team == 'left']
    right_team = [c for c in alive_characters if c.team == 'right']
    
    # Type distribution
    left_counts = np.zeros(NUM_CHARACTER_TYPES)
    right_counts = np.zeros(NUM_CHARACTER_TYPES)
    
    for char in left_team:
        left_counts[CHARACTER_TYPES.index(char.character_type)] += 1
    for char in right_team:
        right_counts[CHARACTER_TYPES.index(char.character_type)] += 1
    
    # Normalize counts
    max_count = CONFIG.MAX_CHARACTERS / 2
    left_counts = left_counts / max_count
    right_counts = right_counts / max_count
    
    # Calculate team health
    total_left_hp = sum(c.hp / c.max_hp for c in left_team) / len(left_team) if left_team else 0
    total_right_hp = sum(c.hp / c.max_hp for c in right_team) / len(right_team) if right_team else 0
    
    state = np.concatenate([
        [left_castle_hp_ratio, right_castle_hp_ratio,
         left_gage_ratio, right_gage_ratio,
         total_left_hp, total_right_hp],
        left_counts,
        right_counts
    ])
    
    return state.astype(np.float32)

# =============================
# Game State Management
# =============================

def initialize_game_state(render: bool) -> Dict[str, Any]:
    """Initialize the game state for a new episode."""
    game_state = {
        'characters': [],
        'left_castle': Castle(x=0, y=0, team='left', render=render),
        'right_castle': Castle(x=CONFIG.WORLD_WIDTH - 100, y=0, team='right', render=render),
        'left_gage': 0,
        'right_gage': 0,
        'spawn_cost': CONFIG.SPAWN_COST,
        'left_spawn_counts': {t: 0 for t in CHARACTER_TYPES},
        'right_spawn_counts': {t: 0 for t in CHARACTER_TYPES},
        'camera_offset': 0,
        'spawn_addition_timer': 0.0,
        'elapsed_time': 0.0,
        'time_limit': CONFIG.TIME_LIMIT,
    }

    # Adjust castle positions
    game_state['left_castle'].y = CONFIG.SCREEN_HEIGHT - game_state['left_castle'].height
    game_state['right_castle'].y = CONFIG.SCREEN_HEIGHT - game_state['right_castle'].height

    # Load sprites if rendering
    if render:
        game_state['loaded_sprites'] = {}
        for char_type in CHARACTER_TYPES:
            game_state['loaded_sprites'][char_type] = {
                'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
                'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
            }
    else:
        game_state['loaded_sprites'] = {
            char_type: {'left': None, 'right': None} for char_type in CHARACTER_TYPES
        }

    return game_state

def spawn_character(team: str, 
                   character_type: str, 
                   loaded_sprites: Dict[str, Dict[str, Any]], 
                   characters: List[Character],
                   time_scale: float) -> Optional[str]:
    """Spawns a character of a specific type for the given team."""
    if team not in ['left', 'right']:
        logging.error(f"Invalid team '{team}' specified for spawning.")
        return None

    if character_type not in CHARACTER_TYPES:
        logging.error(f"Invalid character type '{character_type}' specified for spawning.")
        return None

    # Calculate spawn position
    if loaded_sprites[character_type][team]:
        sprites = loaded_sprites[character_type][team]
        first_action = next(iter(sprites))
        sprite = sprites[first_action][0] if sprites[first_action] else None
        sprite_width = sprite.get_width() if sprite else 40
        sprite_height = sprite.get_height() if sprite else 40
    else:
        sprites = None
        sprite_width = 40
        sprite_height = 40

    x = 100 if team == 'left' else CONFIG.WORLD_WIDTH - 100 - sprite_width
    y = CONFIG.SCREEN_HEIGHT - sprite_height

    try:
        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team=team,
            character_type=character_type,
            time_scale=time_scale
        )
        characters.append(character)
        return character_type
    except Exception as e:
        logging.error(f"Error spawning character: {e}")
        return None

def handle_spawn_decision(team: str, 
                        action: int, 
                        game_state: Dict[str, Any],
                        agent: Optional[AIPlayerAgent]) -> None:
    """Handle spawn decision for a team."""
    gage_key = f"{team}_gage"
    
    if action == SpawnActions.DO_NOTHING:
        return
        
    if game_state[gage_key] < CONFIG.SPAWN_COST:
        return
        
    # Check character limit
    team_count = sum(1 for c in game_state['characters'] if c.team == team)
    if team_count >= CONFIG.MAX_CHARACTERS // 2:
        return
    
    # Determine character type
    if team == 'left' and agent:
        char_type = agent.decide_character_type(action)
    else:
        char_type = random.choice(CHARACTER_TYPES)
    
    if char_type:
        success = spawn_character(
            team, 
            char_type, 
            game_state['loaded_sprites'],
            game_state['characters'],
            time_scale=1
        )
        if success:
            game_state[gage_key] -= CONFIG.SPAWN_COST
            game_state[f'{team}_spawn_counts'][char_type] += 1

def update_game_state(game_state: Dict[str, Any], 
                     delta_time: float,
                     current_time: float,
                     spawn_agent: AIPlayerAgent,
                     render: bool) -> bool:
    """Update the game state with improved combat behavior."""
    game_state['elapsed_time'] += delta_time
    
    # Update spawn timer and gage
    game_state['spawn_addition_timer'] += delta_time
    if game_state['spawn_addition_timer'] >= 1.0:
        game_state['spawn_addition_timer'] -= 1.0
        
        # Update gages
        game_state['left_gage'] = min(game_state['left_gage'] + CONFIG.GAGE_INCREMENT, CONFIG.MAX_GAGE)
        game_state['right_gage'] = min(game_state['right_gage'] + CONFIG.GAGE_INCREMENT, CONFIG.MAX_GAGE)

        # Handle spawns...
        spawn_state = build_spawn_state(
            game_state['left_castle'], 
            game_state['right_castle'],
            game_state['characters'],
            game_state['left_gage'],
            game_state['right_gage']
        )

        left_action = spawn_agent.choose_action(spawn_state)
        handle_spawn_decision('left', left_action, game_state, spawn_agent)
        
        right_action = random.randrange(SpawnActions.SPACE_SIZE)
        handle_spawn_decision('right', right_action, game_state, None)

    # Update characters
    characters_to_remove = []
    for character in game_state['characters']:
        if character.is_dead:
            characters_to_remove.append(character)
            continue
            
        enemies = [c for c in game_state['characters'] 
                  if c.team != character.team and not c.is_dead]
        enemy_castle = (game_state['right_castle'] if character.team == 'left'
                       else game_state['left_castle'])
        
        # Update character with current time for combat timing
        character.update(enemies, enemy_castle, delta_time, current_time)
        
        # Only process actions if not currently executing one
        if not character.action_in_progress:
            # First, check for any enemies in attack range
            enemies_in_range = []
            for enemy in enemies:
                if character.is_within_attack_range(enemy):
                    if ((character.team == 'left' and enemy.x > character.x) or 
                        (character.team == 'right' and enemy.x < character.x)):
                        enemies_in_range.append(enemy)
            
            # Also check if castle is in range
            castle_in_range = False
            if not enemy_castle.is_destroyed() and character.is_within_attack_range(enemy_castle):
                if ((character.team == 'left' and enemy_castle.x > character.x) or 
                    (character.team == 'right' and enemy_castle.x < character.x)):
                    castle_in_range = True

            # If any enemies or castle in range, stop and attack
            if enemies_in_range or castle_in_range:
                # Stop movement
                character.vel_x = 0
                character.vel_y = 0
                
                # Set closest target
                if enemies_in_range:
                    character.target = min(enemies_in_range, 
                                        key=lambda e: character.get_distance_to(e))
                else:
                    character.target = enemy_castle

                # Choose attack action
                rand_val = random.random()
                if rand_val < 0.6:
                    character.set_action('Attack')
                elif rand_val < 0.8:
                    character.set_action('skill1')
                else:
                    character.set_action('skill2')
            else:
                # No enemies in range - find closest target and move towards it
                valid_targets = [e for e in enemies if not e.is_dead]
                if not enemy_castle.is_destroyed():
                    valid_targets.append(enemy_castle)
                
                closest_target = None
                closest_dist = float('inf')
                
                for target in valid_targets:
                    target_x = target.x if hasattr(target, 'x') else target.get_center_position()[0]
                    
                    if ((character.team == 'left' and target_x > character.x) or 
                        (character.team == 'right' and target_x < character.x)):
                        dist = character.get_distance_to(target)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_target = target
                
                if closest_target:
                    character.target = closest_target
                    character.set_action('Run')
                else:
                    # No valid targets - move forward
                    character.set_action('Run')

    # Remove dead or finished characters
    for char in characters_to_remove:
        game_state['characters'].remove(char)

    # Check game over conditions
    game_over, winner = check_game_over(game_state)
    if game_over:
        game_state['winner'] = winner
        return True

    return False

def check_game_over(game_state: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Check if the game is over and determine the winner."""
    if game_state['left_castle'].is_destroyed():
        return True, "Right Team Wins!"
    
    if game_state['right_castle'].is_destroyed():
        return True, "Left Team Wins!"
    
    if game_state['elapsed_time'] >= game_state['time_limit']:
        left_hp = game_state['left_castle'].hp
        right_hp = game_state['right_castle'].hp
        
        if left_hp > right_hp:
            return True, "Left Team Wins!"
        elif right_hp > left_hp:
            return True, "Right Team Wins!"
        else:
            return True, "Draw!"
            
    return False, None

def handle_time_and_events(clock: pygame.time.Clock, render: bool) -> float:
    """Handle time updates and pygame events."""
    if render:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    return {'type': 'camera_right'}
                elif event.key == pygame.K_LEFT:
                    return {'type': 'camera_left'}

    raw_dt = clock.tick(CONFIG.FPS) / 1000.0
    return raw_dt * (10 if render else 10)  # Time scaling factor

def draw_ui(game_state: Dict[str, Any], window: pygame.Surface) -> None:
    """Draw UI elements including timer, minimap, and scrollbar."""
    font = pygame.font.SysFont(None, 36)
    
    # Draw timer
    remaining_time = max(0, game_state['time_limit'] - game_state['elapsed_time'])
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, CONFIG.BLACK)
    window.blit(timer_text, timer_text.get_rect(center=(CONFIG.SCREEN_WIDTH / 2, 20)))

    # Draw minimap
    minimap_width = 200
    minimap_height = 20
    minimap_x = (CONFIG.SCREEN_WIDTH - minimap_width) // 2
    minimap_y = 50
    
    pygame.draw.rect(window, CONFIG.BLACK, (minimap_x, minimap_y, minimap_width, minimap_height), 2)
    
    # Draw character positions on minimap
    for char in game_state['characters']:
        color = CONFIG.BLUE if char.team == 'left' else CONFIG.RED
        mini_x = minimap_x + (char.x / CONFIG.WORLD_WIDTH) * minimap_width
        mini_y = minimap_y + minimap_height / 2
        pygame.draw.circle(window, color, (int(mini_x), int(mini_y)), 2)

    # Draw scrollbar
    scrollbar_y = CONFIG.SCREEN_HEIGHT + 50
    scrollbar_rect = pygame.Rect(0, scrollbar_y, CONFIG.SCREEN_WIDTH, 20)
    pygame.draw.rect(window, CONFIG.GRAY, scrollbar_rect)
    
    if CONFIG.WORLD_WIDTH > CONFIG.SCREEN_WIDTH:
        camera_ratio = game_state['camera_offset'] / (CONFIG.WORLD_WIDTH - CONFIG.SCREEN_WIDTH)
    else:
        camera_ratio = 0.0
        
    handle_x = int(camera_ratio * (CONFIG.SCREEN_WIDTH - 20))
    pygame.draw.rect(window, CONFIG.BLACK, (handle_x, scrollbar_y, 20, 20))

    # Draw winner if game is over
    if 'winner' in game_state:
        font_large = pygame.font.SysFont(None, 72)
        text = font_large.render(game_state['winner'], True, CONFIG.BLACK)
        window.blit(text, text.get_rect(center=(CONFIG.SCREEN_WIDTH / 2, CONFIG.SCREEN_HEIGHT / 2)))

def render_game(game_state: Dict[str, Any], window: pygame.Surface) -> None:
    """Render the current game state."""
    window.fill(CONFIG.WHITE)
    
    # Draw background
    background = pygame.Surface((CONFIG.WORLD_WIDTH, CONFIG.SCREEN_HEIGHT))
    background.fill(CONFIG.WHITE)
    camera_rect = pygame.Rect(game_state['camera_offset'], 0, CONFIG.SCREEN_WIDTH, CONFIG.SCREEN_HEIGHT)
    window.blit(background, (0, 0), area=camera_rect)

    # Draw castles
    game_state['left_castle'].draw(window, camera_offset=game_state['camera_offset'])
    game_state['right_castle'].draw(window, camera_offset=game_state['camera_offset'])

    # Draw characters
    for character in game_state['characters']:
        character.draw(window, camera_offset=game_state['camera_offset'])

    # Draw UI elements
    draw_ui(game_state, window)
    
    pygame.display.flip()

def compute_episode_results(game_state: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the results of the episode."""
    return {
        'winner': game_state.get('winner', 'No Winner'),
        'left_castle_hp': game_state['left_castle'].hp,
        'right_castle_hp': game_state['right_castle'].hp,
        'left_spawn_counts': game_state['left_spawn_counts'],
        'right_spawn_counts': game_state['right_spawn_counts'],
        'episode_duration': game_state.get('elapsed_time', 0)
    }

def log_episode_results(episode: int, results: Dict[str, Any], csv_file: str, write_header: bool) -> None:
    """Log the episode results to a CSV file."""
    if write_header:
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            header = ['episode', 'winner'] + \
                     [f'left_{t}' for t in CHARACTER_TYPES] + \
                     [f'right_{t}' for t in CHARACTER_TYPES]
            writer.writerow(header)

    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        row = [episode, results['winner']] + \
              [results['left_spawn_counts'][t] for t in CHARACTER_TYPES] + \
              [results['right_spawn_counts'][t] for t in CHARACTER_TYPES]
        writer.writerow(row)

def calculate_spawn_rewards(game_state, previous_state, action):
    """
    Calculate rewards for spawn agent actions based on multiple factors.
    
    Returns:
        total_reward: float
        reward_breakdown: dict
    """
    rewards = {
        'castle_health_reward': 0.0,
        'resource_management_reward': 0.0,
        'unit_composition_reward': 0.0,
        'tactical_positioning_reward': 0.0,
        'combat_outcome_reward': 0.0
    }
    
    # 1. Castle Health Reward (-5.0 to 5.0)
    left_castle_hp_ratio = game_state['left_castle'].hp / game_state['left_castle'].max_hp
    right_castle_hp_ratio = game_state['right_castle'].hp / game_state['right_castle'].max_hp
    previous_left_hp_ratio = previous_state['left_castle'].hp / previous_state['left_castle'].max_hp
    previous_right_hp_ratio = previous_state['right_castle'].hp / previous_state['right_castle'].max_hp
    
    castle_health_delta = (left_castle_hp_ratio - previous_left_hp_ratio) - \
                         (right_castle_hp_ratio - previous_right_hp_ratio)
    rewards['castle_health_reward'] = castle_health_delta * 1.0

    # 2. Resource Management Reward (-1.0 to 1.0)
    if action == SpawnActions.DO_NOTHING and game_state['left_gage'] < CONFIG.SPAWN_COST:
        # Reward for saving resources when can't afford spawn
        rewards['resource_management_reward'] = 0.1
    elif action != SpawnActions.DO_NOTHING and game_state['left_gage'] >= CONFIG.SPAWN_COST:
        # Small reward for efficient resource use
        rewards['resource_management_reward'] = 0.01
    else:
        # Penalty for spawning when can't afford or not spawning when can
        rewards['resource_management_reward'] = -0.1

    # 3. Unit Composition Reward (-2.0 to 2.0)
    left_units = [c for c in game_state['characters'] if c.team == 'left' and not c.is_dead]
    unit_types = [c.character_type for c in left_units]
    
    # Reward for maintaining balanced composition
    type_ratios = {t: unit_types.count(t) / len(unit_types) if unit_types else 0 
                   for t in CHARACTER_TYPES}
    balance_score = -abs(max(type_ratios.values()) - 1/len(CHARACTER_TYPES))
    rewards['unit_composition_reward'] = balance_score * 1.0

    # 4. Tactical Positioning Reward (-3.0 to 3.0)
    left_units_positions = [c.x / CONFIG.WORLD_WIDTH for c in left_units]
    if left_units_positions:
        # Reward for forward positioning and good spacing
        avg_position = sum(left_units_positions) / len(left_units_positions)
        position_score = avg_position * 2 - 1  # Transform to [-1, 1]
        rewards['tactical_positioning_reward'] = position_score * 1.0

    # 5. Combat Outcome Reward (-4.0 to 4.0)
    previous_enemies = [c for c in previous_state['characters'] 
                       if c.team == 'right' and not c.is_dead]
    current_enemies = [c for c in game_state['characters'] 
                      if c.team == 'right' and not c.is_dead]
    
    enemies_defeated = len(previous_enemies) - len(current_enemies)
    allies_lost = len([c for c in previous_state['characters'] if c.team == 'left']) - \
                 len([c for c in game_state['characters'] if c.team == 'left'])
    
    combat_score = enemies_defeated - allies_lost
    rewards['combat_outcome_reward'] = combat_score * 2.0

    # Calculate total reward
    total_reward = sum(rewards.values())
    
    # Add win/loss rewards
    if game_state.get('winner'):
        if game_state['winner'] == "Left Team Wins!":
            total_reward += 1000.0
            rewards['victory_reward'] = 1000.0
        elif game_state['winner'] == "Right Team Wins!":
            total_reward -= 1000.0
            rewards['victory_reward'] = -1000.0
    
    return total_reward, rewards 

def run_training_episode(episode: int,
                        config: Dict[str, Any],
                        spawn_agent: AIPlayerAgent) -> Dict[str, Any]:
    """Run a single training episode with reward calculation"""
    pygame.init()
    pygame.display.init()
    
    render = (episode % config['render_interval'] == 0)
    
    if render:
        window = pygame.display.set_mode((CONFIG.SCREEN_WIDTH, CONFIG.WINDOW_HEIGHT))
        pygame.display.set_caption(f"Episode {episode}")
    else:
        window = pygame.display.set_mode((1, 1))
        
    clock = pygame.time.Clock()
    game_state = initialize_game_state(render)
    previous_state = None
    game_over = False
    episode_rewards = []
    
    while not game_over:
        # Store previous state for reward calculation
        if previous_state is None:
            previous_state = {
                'left_castle': game_state['left_castle'],
                'right_castle': game_state['right_castle'],
                'characters': game_state['characters'].copy(),
                'left_gage': game_state['left_gage'],
                'right_gage': game_state['right_gage']
            }
        
        # Get spawn state and action
        spawn_state = build_spawn_state(
            game_state['left_castle'], 
            game_state['right_castle'],
            game_state['characters'],
            game_state['left_gage'],
            game_state['right_gage']
        )
        
        # Choose action
        action = spawn_agent.choose_action(spawn_state, deterministic=False)
        
        # Execute action
        handle_spawn_decision('left', action, game_state, spawn_agent)
        
        # Update game state
        delta_time = handle_time_and_events(clock, render)
        current_time = pygame.time.get_ticks() / 1000
        game_over = update_game_state(game_state, delta_time, current_time,
                                    spawn_agent, render)
        
        # Calculate rewards
        total_reward, reward_breakdown = calculate_spawn_rewards(game_state, previous_state, action)
        episode_rewards.append(total_reward)
        
        # Store state, action, reward for agent learning
        next_spawn_state = build_spawn_state(
            game_state['left_castle'],
            game_state['right_castle'],
            game_state['characters'],
            game_state['left_gage'],
            game_state['right_gage']
        )
        
        # Store experience in agent's memory
        spawn_agent.remember(spawn_state, action, total_reward, next_spawn_state, game_over)
        
        # Perform learning update
        if len(spawn_agent.memory) >= 64:
            loss = spawn_agent.replay()
            if render and loss is not None:
                print(f"Training loss: {loss:.4f}")
        
        # Update previous state
        previous_state = {
            'left_castle': game_state['left_castle'],
            'right_castle': game_state['right_castle'],
            'characters': game_state['characters'].copy(),
            'left_gage': game_state['left_gage'],
            'right_gage': game_state['right_gage']
        }
        
        if render:
            render_game(game_state, window)
    
    # Cleanup
    pygame.display.quit()
    pygame.quit()

    # Add rewards to results
    results = compute_episode_results(game_state)
    results['total_reward'] = sum(episode_rewards)
    results['avg_reward'] = sum(episode_rewards) / len(episode_rewards) if episode_rewards else 0
    
    return results

def find_latest_checkpoint() -> Optional[str]:
    """Find the latest checkpoint file in the models directory"""
    models_dir = Path("models")
    if not models_dir.exists():
        return None
        
    # Look for files matching pattern "spawn_agent_episode_*.pth"
    checkpoints = glob.glob(str(models_dir / "spawn_agent_episode_*.pth"))
    if not checkpoints:
        return None
        
    # Extract episode numbers and find the highest one
    episode_numbers = []
    for checkpoint in checkpoints:
        match = re.search(r'episode_(\d+)\.pth$', checkpoint)
        if match:
            episode_numbers.append((int(match.group(1)), checkpoint))
            
    if not episode_numbers:
        return None
        
    # Return the checkpoint with the highest episode number
    return max(episode_numbers, key=lambda x: x[0])[1]

def setup_training(start_from_checkpoint: bool = True) -> Dict[str, Any]:
    """Initialize training parameters and create necessary directories"""
    config = {
        'time_limit': CONFIG.TIME_LIMIT,
        'episodes': 5000,
        'render_interval': 1,
        'model_dir': Path("models"),
        'start_episode': 1,
        'checkpoint_path': None
    }
    
    config['model_dir'].mkdir(exist_ok=True)
    
    if start_from_checkpoint:
        checkpoint_path = find_latest_checkpoint()
        if checkpoint_path:
            # Extract episode number from checkpoint name
            match = re.search(r'episode_(\d+)\.pth$', checkpoint_path)
            if match:
                config['start_episode'] = int(match.group(1)) + 1
                config['checkpoint_path'] = checkpoint_path
                logging.info(f"Continuing training from checkpoint: {checkpoint_path}")
                logging.info(f"Starting from episode {config['start_episode']}")
    
    return config

def main() -> None:
    """Main training loop with checkpoint loading"""
    config = setup_training(start_from_checkpoint=True)
    
    # Initialize logging and statistics
    csv_file = 'training_results.csv'
    write_header = not os.path.exists(csv_file)
    
    # Calculate state sizes for spawn agent
    spawn_state_size = 6 + 2 * NUM_CHARACTER_TYPES  # Base features + character counts
    
    # Initialize spawn agent
    spawn_agent = AIPlayerAgent(state_size=spawn_state_size, team='left')
    
    # Load checkpoint if available
    if config['checkpoint_path']:
        try:
            spawn_agent.load(config['checkpoint_path'])
            logging.info("Successfully loaded checkpoint")
        except Exception as e:
            logging.error(f"Error loading checkpoint: {e}")
            logging.info("Starting fresh training")
            config['start_episode'] = 1
    
    # Training metrics
    reward_history = []
    
    # Training loop
    for episode in range(config['start_episode'], config['episodes'] + 1):
        logging.info(f"Starting episode {episode}")
        
        # Run episode with reward calculation
        results = run_training_episode(episode, config, spawn_agent)
        reward_history.append(results['total_reward'])
        
        # Log enhanced results
        log_episode_results(episode, results, csv_file, write_header)
        write_header = False
        
        # Log rewards
        logging.info(f"Episode {episode} - "
                    f"Total Reward: {results['total_reward']:.2f}, "
                    f"Average Reward: {results['avg_reward']:.2f}, "
                    f"Winner: {results['winner']}")
        
        # Save spawn agent model periodically
        if episode % 10 == 0:
            model_path = config['model_dir'] / f"spawn_agent_episode_{episode}.pth"
            spawn_agent.save(model_path)
            
            # Calculate and log average reward over last 100 episodes
            last_100_avg = sum(reward_history[-100:]) / min(100, len(reward_history))
            logging.info(f"Last 100 episodes average reward: {last_100_avg:.2f}")
            
if __name__ == "__main__":
    main()