# scenes/game_scene.py
import pygame
import os
from typing import Dict, List, Any
from character import Character, load_character_info
from castle import Castle
from utils import load_character_sprites
from rl_agent import AIPlayerAgent
from .base_scene import Scene
from .utils.logger import load_stage_logs, save_stage_logs  # Corrected import

class GameConfig:
    SCREEN_WIDTH = 1440
    SCREEN_HEIGHT = 700  # Height for game background
    UI_HEIGHT = 100      # Height for UI elements
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
    GRAY = (200, 200, 200)  # Light Gray for UI Background
    BLUE = (0, 0, 255)
    RED = (255, 0, 0)
    
    BACKGROUND_FILL_COLOR = GRAY  # Solid color for remaining upper area
    
    # Stage-specific AI models for 10 stages
    STAGE_MODELS = {
        i: f"models/spawn_agent_episode_{200 * (i+1)}.pth" 
        for i in range(10)  # Stages 0 to 9
    }

class GameScene(Scene):
    def __init__(self, screen, stage_number):
        super().__init__(screen)
        self.config = GameConfig()
        self.stage_number = stage_number
        self.font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 36)
        self.pause_menu_active = False
        self.game_state = self.initialize_game_state()
        self.clock = pygame.time.Clock()
        self.initialize_ai_agent()
        self.stage_cleared = False  # Flag to prevent multiple logs

        # Load Character UI Images
        self.load_character_ui_images()

        # Assign the game background image scaled to SCREEN_HEIGHT
        self.background = self.get_background_image()
    
    def get_background_image(self):
        """Retrieve and scale the background image based on the stage's difficulty."""
        stage_info = self.get_stage_info()
        difficulty = stage_info.get("difficulty", "Easy")  # Default to "Easy" if not specified
        background_image_path = stage_info.get("background_image_path", "assets/backgrounds/easy_background.png")
        
        if os.path.exists(background_image_path):
            try:
                image = pygame.image.load(background_image_path).convert()
                image = pygame.transform.scale(image, (self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT))
                return image
            except pygame.error as e:
                print(f"Error loading background image: {e}")
        else:
            print(f"Background image not found at {background_image_path}. Using default background.")
        
        # Fallback to a solid color if background image fails to load
        fallback_background = pygame.Surface((self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT))
        fallback_background.fill(self.config.BACKGROUND_FILL_COLOR)
        return fallback_background

    def load_character_ui_images(self):
        """Load images for spawnable characters in the UI."""
        self.ui_character_images = {}
        for char_type in self.CHARACTER_TYPES:
            char_image_path = os.path.join('sprites', 'left', f"{char_type}", "Idle_left_0.png")
            if os.path.exists(char_image_path):
                try:
                    image = pygame.image.load(char_image_path).convert_alpha()
                    image = pygame.transform.scale(image, (50, 50))  # Adjust size as needed
                    self.ui_character_images[char_type] = image
                except pygame.error as e:
                    print(f"Error loading character UI image for {char_type}: {e}")
                    self.ui_character_images[char_type] = None
            else:
                print(f"Character UI image for {char_type} not found at {char_image_path}.")
                self.ui_character_images[char_type] = None

    def initialize_game_state(self):
        """Initialize the game state"""
        # Load character info
        self.CHARACTER_INFO = load_character_info()
        self.CHARACTER_TYPES = list(self.CHARACTER_INFO.keys())
        
        game_state = {
            'characters': [],
            'left_castle': Castle(x=0, y=self.config.SCREEN_HEIGHT-100, team='left', render=True),
            'right_castle': Castle(x=self.config.SCREEN_WIDTH-120, 
                                 y=self.config.SCREEN_HEIGHT-100, team='right', render=True),
            'left_gage': 0,
            'right_gage': 0,
            'camera_offset': 0,
            'elapsed_time': 0,
            'time_limit': self.config.TIME_LIMIT,
            'loaded_sprites': {},
            'game_over': False,
            'winner': None
        }
        
        # Load sprites
        for char_type in self.CHARACTER_TYPES:
            game_state['loaded_sprites'][char_type] = {
                'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
                'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
            }
        
        return game_state
        
    def initialize_ai_agent(self):
        """Initialize the AI agent for the appropriate stage"""
        state_size = 6 + 2 * len(self.CHARACTER_TYPES)  # Base features + character counts
        self.ai_agent = AIPlayerAgent(state_size=state_size, team='right')
        
        # Load the appropriate model for the stage
        model_path = self.config.STAGE_MODELS.get(self.stage_number)
        if model_path and os.path.exists(model_path):
            self.ai_agent.load(model_path)
        else:
            print(f"Warning: Could not load AI model for stage {self.stage_number + 1}")

    def spawn_character(self, team: str, character_type: str):
        """Spawn a character with the given type for the specified team"""
        if len([c for c in self.game_state['characters'] if c.team == team]) >= self.config.MAX_CHARACTERS // 2:
            return False
            
        sprites = self.game_state['loaded_sprites'][character_type][team]
        x = 100 if team == 'left' else self.config.SCREEN_WIDTH - 140
        y = self.config.SCREEN_HEIGHT - 100  # Position within game area
        
        character = Character(sprites=sprites, x=x, y=y, team=team, 
                            character_type=character_type, time_scale=1)
        self.game_state['characters'].append(character)
        return True

    def build_spawn_state(self):
        """Build state representation for AI agent"""
        left_castle = self.game_state['left_castle']
        right_castle = self.game_state['right_castle']
        characters = self.game_state['characters']
        
        # Castle status
        left_castle_hp_ratio = left_castle.hp / left_castle.max_hp
        right_castle_hp_ratio = right_castle.hp / right_castle.max_hp
        
        # Resource management
        left_gage_ratio = self.game_state['left_gage'] / self.config.MAX_GAGE
        right_gage_ratio = self.game_state['right_gage'] / self.config.MAX_GAGE
        
        # Team analysis
        alive_characters = [c for c in characters if c.hp > 0]
        left_team = [c for c in alive_characters if c.team == 'left']
        right_team = [c for c in alive_characters if c.team == 'right']
        
        # Type distribution
        left_counts = [0] * len(self.CHARACTER_TYPES)
        right_counts = [0] * len(self.CHARACTER_TYPES)
        
        for char in left_team:
            left_counts[self.CHARACTER_TYPES.index(char.character_type)] += 1
        for char in right_team:
            right_counts[self.CHARACTER_TYPES.index(char.character_type)] += 1
        
        # Normalize counts
        max_count = self.config.MAX_CHARACTERS / 2
        left_counts = [count / max_count for count in left_counts]
        right_counts = [count / max_count for count in right_counts]
        
        # Calculate team health
        total_left_hp = sum(c.hp / c.max_hp for c in left_team) / len(left_team) if left_team else 0
        total_right_hp = sum(c.hp / c.max_hp for c in right_team) / len(right_team) if right_team else 0
        
        state = [left_castle_hp_ratio, right_castle_hp_ratio,
                left_gage_ratio, right_gage_ratio,
                total_left_hp, total_right_hp] + left_counts + right_counts
        
        return state

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.pause_menu_active = not self.pause_menu_active
                elif self.pause_menu_active:
                    if event.key == pygame.K_r:  # Resume
                        self.pause_menu_active = False
                    elif event.key == pygame.K_q:  # Quit to menu
                        from .stage_select_scene import StageSelectScene
                        self.switch_to_scene(StageSelectScene(self.screen))
                elif not self.pause_menu_active:
                    # Handle character spawning (1-3 keys)
                    if event.unicode in "123" and self.game_state['left_gage'] >= self.config.SPAWN_COST:
                        char_idx = int(event.unicode) - 1
                        if char_idx < len(self.CHARACTER_TYPES):
                            if self.spawn_character('left', self.CHARACTER_TYPES[char_idx]):
                                self.game_state['left_gage'] -= self.config.SPAWN_COST

    def update(self, dt):
        if not self.pause_menu_active and not self.game_state['game_over']:
            current_time = pygame.time.get_ticks() / 1000
            
            # Update game time
            self.game_state['elapsed_time'] += dt
            
            # Update gages
            self.game_state['left_gage'] = min(self.game_state['left_gage'] + 
                                             self.config.GAGE_INCREMENT * dt,
                                             self.config.MAX_GAGE)
            self.game_state['right_gage'] = min(self.game_state['right_gage'] + 
                                              self.config.GAGE_INCREMENT * dt,
                                              self.config.MAX_GAGE)
            
            # AI agent decision
            if self.game_state['right_gage'] >= self.config.SPAWN_COST:
                spawn_state = self.build_spawn_state()
                ai_action = self.ai_agent.choose_action(spawn_state, deterministic=True)
                if ai_action < len(self.CHARACTER_TYPES):
                    if self.spawn_character('right', self.CHARACTER_TYPES[ai_action]):
                        self.game_state['right_gage'] -= self.config.SPAWN_COST
            
            # Update characters
            characters_to_remove = []
            for character in self.game_state['characters']:
                if character.is_dead:
                    characters_to_remove.append(character)
                    continue
                    
                enemies = [c for c in self.game_state['characters'] 
                          if c.team != character.team and not c.is_dead]
                enemy_castle = (self.game_state['right_castle'] if character.team == 'left'
                              else self.game_state['left_castle'])
                
                character.update(enemies, enemy_castle, dt, current_time)
            
            # Remove dead characters
            for char in characters_to_remove:
                self.game_state['characters'].remove(char)
            
            # Check game over conditions
            if (self.game_state['left_castle'].is_destroyed() or 
                self.game_state['right_castle'].is_destroyed() or
                self.game_state['elapsed_time'] >= self.game_state['time_limit']):
                
                self.game_state['game_over'] = True
                if self.game_state['left_castle'].is_destroyed():
                    self.game_state['winner'] = "Right Team Wins!"
                elif self.game_state['right_castle'].is_destroyed():
                    self.game_state['winner'] = "Left Team Wins!"
                elif self.game_state['left_castle'].hp > self.game_state['right_castle'].hp:
                    self.game_state['winner'] = "Left Team Wins!"
                elif self.game_state['right_castle'].hp > self.game_state['left_castle'].hp:
                    self.game_state['winner'] = "Right Team Wins!"
                else:
                    self.game_state['winner'] = "Draw!"
                
                # Log stage completion
                self.log_stage_completion()

    def log_stage_completion(self):
        """Log the stage completion with remaining time."""
        if not self.stage_cleared:
            logs = load_stage_logs()
            stage_key = str(self.stage_number + 1)  # Stages are 1-indexed
            remaining_time = max(0, self.config.TIME_LIMIT - self.game_state['elapsed_time'])
            logs[stage_key] = {
                "cleared": True,
                "remaining_time": round(remaining_time, 2)  # Round to 2 decimal places
            }
            save_stage_logs(logs)
            self.stage_cleared = True  # Prevent multiple logs

    def draw(self):
        # 1. Fill the entire window with the solid color for the UI area
        self.screen.fill(self.config.BACKGROUND_FILL_COLOR)
        
        # 2. Blit the game background image at the bottom of the window
        self.screen.blit(self.background, (0, self.config.UI_HEIGHT))
        
        # 3. Draw characters
        for character in self.game_state['characters']:
            character.draw(self.screen, self.game_state['camera_offset'])
        
        # 4. Draw castles
        self.game_state['left_castle'].draw(self.screen, self.game_state['camera_offset'])
        self.game_state['right_castle'].draw(self.screen, self.game_state['camera_offset'])
        
        # 5. Draw UI elements on top of the filled area
        self.draw_ui()
        
        # 6. Draw pause menu if active
        if self.pause_menu_active:
            self.draw_pause_menu()
        
        # 7. Draw game over screen if game is over
        if self.game_state['game_over']:
            self.draw_game_over()

    def draw_ui(self):
        # Calculate the starting Y-coordinate for UI elements
        ui_start_y = 0  # UI is at the top
        
        # 1. Draw timer
        remaining_time = max(0, self.game_state['time_limit'] - self.game_state['elapsed_time'])
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        timer_text = self.font.render(f"{minutes:02}:{seconds:02}", True, self.config.BLACK)
        self.screen.blit(timer_text, (self.config.SCREEN_WIDTH // 2 - 50, ui_start_y + 10))
        
        # 2. Draw gage bars with borders for clarity
        # Left Gage
        pygame.draw.rect(self.screen, self.config.BLACK, (50, ui_start_y + 20, self.config.MAX_GAGE, 20), 2)  # Border
        pygame.draw.rect(self.screen, self.config.BLUE, (52, ui_start_y + 22, 
                                                         self.game_state['left_gage'] - 4, 16))  # Filled
        
        # Right Gage
        pygame.draw.rect(self.screen, self.config.BLACK, 
                         (self.config.SCREEN_WIDTH - 250, ui_start_y + 20, self.config.MAX_GAGE, 20), 2)  # Border
        pygame.draw.rect(self.screen, self.config.RED, 
                         (self.config.SCREEN_WIDTH - 248, ui_start_y + 22, 
                          self.game_state['right_gage'] - 4, 16))  # Filled
        
        # 3. Draw character selection info with preloaded images
        y_offset = ui_start_y + 80
        for i, char_type in enumerate(self.CHARACTER_TYPES):
            # Retrieve preloaded character image
            char_image = self.ui_character_images.get(char_type)
            if char_image:
                self.screen.blit(char_image, (50 + i*200, y_offset - 40))
            else:
                # Optionally, draw a placeholder if image is missing
                placeholder = pygame.Surface((50, 50))
                placeholder.fill(self.config.BLACK)
                self.screen.blit(placeholder, (50 + i*200, y_offset - 40))
            
            # Draw spawn instruction next to the image
            key_text = self.small_font.render(f"Press {i+1}", True, self.config.BLACK)
            self.screen.blit(key_text, (110 + i*200, y_offset - 10))
    

    def draw_pause_menu(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        # Draw pause menu text
        screen_center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        
        pause_text = self.font.render("PAUSED", True, self.config.WHITE)
        resume_text = self.font.render("Press R to Resume", True, self.config.WHITE)
        quit_text = self.font.render("Press Q to Quit", True, self.config.WHITE)
        
        self.screen.blit(pause_text, 
                        pause_text.get_rect(center=(screen_center[0], screen_center[1] - 100)))
        self.screen.blit(resume_text, 
                        resume_text.get_rect(center=screen_center))
        self.screen.blit(quit_text, 
                        quit_text.get_rect(center=(screen_center[0], screen_center[1] + 100)))

    def draw_game_over(self):
        # Draw semi-transparent overlay
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        # Draw game over text and results
        screen_center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        
        # Draw winner announcement
        winner_text = self.font.render(self.game_state['winner'], True, self.config.WHITE)
        self.screen.blit(winner_text, 
                        winner_text.get_rect(center=(screen_center[0], screen_center[1] - 100)))
        
        # Draw final scores
        left_score = f"Left Castle HP: {int(self.game_state['left_castle'].hp)}"
        right_score = f"Right Castle HP: {int(self.game_state['right_castle'].hp)}"
        
        score_font = pygame.font.Font(None, 48)
        left_score_text = score_font.render(left_score, True, self.config.BLUE)
        right_score_text = score_font.render(right_score, True, self.config.RED)
        
        self.screen.blit(left_score_text, 
                        left_score_text.get_rect(center=(screen_center[0], screen_center[1])))
        self.screen.blit(right_score_text, 
                        right_score_text.get_rect(center=(screen_center[0], screen_center[1] + 50)))
        
        # Draw instructions to continue
        continue_text = self.small_font.render("Press SPACE to continue or ESC for menu", 
                                             True, self.config.WHITE)
        self.screen.blit(continue_text, 
                        continue_text.get_rect(center=(screen_center[0], screen_center[1] + 150)))

    def get_stage_info(self):
        """Get information about the current stage"""
        stage_info = {
            i: {
                "name": f"Stage {i+1} - {'Novice' if i < 3 else 'Advanced' if i < 7 else 'Master'}",
                "description": f"Battle against AI trained for {200 * (i+1)} episodes.",
                "difficulty": "Easy" if i < 3 else "Medium" if i < 7 else "Hard",
                "ai_model": f"episode_{200 * (i+1)}",
                "background_image_path": os.path.join('sprites', f"game_scene_{'1' if i < 3 else '2' if i < 7 else '3'}.png")
            }
            for i in range(10)
        }
        return stage_info.get(self.stage_number, stage_info[0])
