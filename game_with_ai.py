# play_vs_ai.py

import pygame
import os
import torch
from typing import Dict, List, Any
import random
from character import Character, load_character_info
from castle import Castle
from utils import load_character_sprites
from rl_agent import AIPlayerAgent
from train_agent import spawn_character

# Game Configuration
class GameConfig:
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 400
    UI_HEIGHT = 100
    WINDOW_HEIGHT = SCREEN_HEIGHT + UI_HEIGHT
    MAX_CHARACTERS = 50
    SPAWN_COST = 20
    MAX_GAGE = 200
    TIME_LIMIT = 180  # 3 minutes
    GAGE_INCREMENT = 4
    FPS = 60
    
    # Colors
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (128, 128, 128)
    BLUE = (0, 0, 255)
    RED = (255, 0, 0)

CONFIG = GameConfig()

def initialize_game():
    """Initialize the game state"""
    pygame.init()
    window = pygame.display.set_mode((CONFIG.SCREEN_WIDTH, CONFIG.WINDOW_HEIGHT))
    pygame.display.set_caption("Battle Game - Play vs AI")
    clock = pygame.time.Clock()
    
    # Load character info
    CHARACTER_INFO = load_character_info()
    CHARACTER_TYPES = list(CHARACTER_INFO.keys())
    
    # Initialize game state
    game_state = {
        'characters': [],
        'left_castle': Castle(x=0, y=CONFIG.SCREEN_HEIGHT-100, team='left', render=True),
        'right_castle': Castle(x=CONFIG.SCREEN_WIDTH-100, y=CONFIG.SCREEN_HEIGHT-100, team='right', render=True),
        'left_gage': 0,
        'right_gage': 0,
        'camera_offset': 0,
        'elapsed_time': 0,
        'time_limit': CONFIG.TIME_LIMIT,
        'loaded_sprites': {}
    }
    
    # Load sprites
    for char_type in CHARACTER_TYPES:
        game_state['loaded_sprites'][char_type] = {
            'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
            'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
        }
    
    return window, clock, game_state, CHARACTER_TYPES

def draw_ui(window: pygame.Surface, game_state: Dict[str, Any], CHARACTER_TYPES: List[str]):
    """Draw the game UI"""
    font = pygame.font.SysFont(None, 36)
    small_font = pygame.font.SysFont(None, 24)
    
    # Draw timer
    remaining_time = max(0, game_state['time_limit'] - game_state['elapsed_time'])
    minutes = int(remaining_time // 60)
    seconds = int(remaining_time % 60)
    timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, CONFIG.BLACK)
    window.blit(timer_text, (CONFIG.SCREEN_WIDTH // 2 - 50, 20))
    
    # Draw gage bars
    pygame.draw.rect(window, CONFIG.BLUE, (50, CONFIG.SCREEN_HEIGHT + 20, 
                    game_state['left_gage'], 20))
    pygame.draw.rect(window, CONFIG.RED, (CONFIG.SCREEN_WIDTH - 250, CONFIG.SCREEN_HEIGHT + 20,
                    game_state['right_gage'], 20))
    
    # Draw character selection info
    y_offset = CONFIG.SCREEN_HEIGHT + 50
    for i, char_type in enumerate(CHARACTER_TYPES):
        key_text = small_font.render(f"Press {i+1} for {char_type}", True, CONFIG.BLACK)
        window.blit(key_text, (50 + i*200, y_offset))

def main():
    """Main game loop"""
    window, clock, game_state, CHARACTER_TYPES = initialize_game()
    
    # Load AI agent
    state_size = 6 + 2 * len(CHARACTER_TYPES)  # Base features + character counts
    ai_agent = AIPlayerAgent(state_size=state_size, team='right')
    ai_agent.load("models/spawn_agent_episode_380.pth")  # Load trained model
    
    running = True
    while running:
        delta_time = clock.tick(CONFIG.FPS) / 1000.0
        current_time = pygame.time.get_ticks() / 1000
        
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Handle character spawning (1-3 keys)
                if event.unicode in "123" and game_state['left_gage'] >= CONFIG.SPAWN_COST:
                    char_idx = int(event.unicode) - 1
                    if char_idx < len(CHARACTER_TYPES):
                        spawn_character('left', CHARACTER_TYPES[char_idx], 
                                     game_state['loaded_sprites'], 
                                     game_state['characters'], 1)
                        game_state['left_gage'] -= CONFIG.SPAWN_COST
        
        # Update game state
        game_state['elapsed_time'] += delta_time
        
        # Update gages
        game_state['left_gage'] = min(game_state['left_gage'] + CONFIG.GAGE_INCREMENT * delta_time,
                                    CONFIG.MAX_GAGE)
        game_state['right_gage'] = min(game_state['right_gage'] + CONFIG.GAGE_INCREMENT * delta_time,
                                     CONFIG.MAX_GAGE)
        
        # AI agent decision
        if game_state['right_gage'] >= CONFIG.SPAWN_COST:
            spawn_state = build_spawn_state(
                game_state['left_castle'],
                game_state['right_castle'],
                game_state['characters'],
                game_state['left_gage'],
                game_state['right_gage']
            )
            ai_action = ai_agent.choose_action(spawn_state, deterministic=True)
            if ai_action < len(CHARACTER_TYPES):
                spawn_character('right', CHARACTER_TYPES[ai_action],
                              game_state['loaded_sprites'],
                              game_state['characters'], 1)
                game_state['right_gage'] -= CONFIG.SPAWN_COST
        
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
            
            character.update(enemies, enemy_castle, delta_time, current_time)
        
        # Remove dead characters
        for char in characters_to_remove:
            game_state['characters'].remove(char)
        
        # Draw game state
        window.fill(CONFIG.WHITE)
        
        # Draw characters
        for character in game_state['characters']:
            character.draw(window, game_state['camera_offset'])
        
        # Draw castles
        game_state['left_castle'].draw(window, game_state['camera_offset'])
        game_state['right_castle'].draw(window, game_state['camera_offset'])
        
        # Draw UI
        draw_ui(window, game_state, CHARACTER_TYPES)
        
        pygame.display.flip()
        
        # Check game over
        if (game_state['left_castle'].is_destroyed() or 
            game_state['right_castle'].is_destroyed() or
            game_state['elapsed_time'] >= game_state['time_limit']):
            running = False
    
    pygame.quit()

def build_spawn_state(left_castle, right_castle, characters, left_gage, right_gage):
    """Build state representation for AI agent"""
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
    
    CHARACTER_TYPES = list(load_character_info().keys())
    
    # Type distribution
    left_counts = [0] * len(CHARACTER_TYPES)
    right_counts = [0] * len(CHARACTER_TYPES)
    
    for char in left_team:
        left_counts[CHARACTER_TYPES.index(char.character_type)] += 1
    for char in right_team:
        right_counts[CHARACTER_TYPES.index(char.character_type)] += 1
    
    # Normalize counts
    max_count = CONFIG.MAX_CHARACTERS / 2
    left_counts = [count / max_count for count in left_counts]
    right_counts = [count / max_count for count in right_counts]
    
    # Calculate team health
    total_left_hp = sum(c.hp / c.max_hp for c in left_team) / len(left_team) if left_team else 0
    total_right_hp = sum(c.hp / c.max_hp for c in right_team) / len(right_team) if right_team else 0
    
    state = [left_castle_hp_ratio, right_castle_hp_ratio,
             left_gage_ratio, right_gage_ratio,
             total_left_hp, total_right_hp] + left_counts + right_counts
    
    return state

if __name__ == "__main__":
    main()