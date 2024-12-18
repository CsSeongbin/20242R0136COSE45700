# network_game_scene.py
import time
import pygame
import os
import logging
from typing import Dict, List, Any, Optional
from .base_scene import Scene
from character import Character, load_character_info
from castle import Castle
from network_manager import NetworkManager, NetworkMessage
from serialization import GameStateSerializer
from .background import BackgroundRenderer  # Ensure correct import path
import re 

def load_character_sprites(folder_path):
    action_sprites = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.png'):
            match = re.match(r'(.+)_(left|right)_(\d+)\.png$', file_name)
            if match:
                action_name = match.group(1)
                frame_number = int(match.group(3))
                image = pygame.image.load(os.path.join(folder_path, file_name)).convert_alpha()
                if action_name not in action_sprites:
                    action_sprites[action_name] = []
                action_sprites[action_name].append((frame_number, image))
    for action_name in action_sprites:
        action_sprites[action_name].sort(key=lambda x: x[0])
        action_sprites[action_name] = [image for _, image in action_sprites[action_name]]
    return action_sprites

class NetworkGameScene(Scene):
    def __init__(self, screen, network_manager: NetworkManager):
        super().__init__(screen)
        self.network_manager = network_manager
        self.is_host = network_manager.is_host

        self.expected_sequence = 0  # Initialize to 0 or the starting sequence number
        self.buffer = {}  # Buffer to store out-of-order messages
        self.BUFFER_LIMIT = 100  # Maximum number of buffered messages
        
        # Game configuration
        self.config = {
            'SCREEN_WIDTH': 1440,
            'SCREEN_HEIGHT': 400,
            'UI_HEIGHT': 100,
            'WINDOW_HEIGHT': 500,
            'MAX_CHARACTERS': 50,
            'SPAWN_COST': 20,
            'MAX_GAGE': 200,
            'TIME_LIMIT': 180,
            'GAGE_INCREMENT': 4,
            'FPS': 60,
            'WHITE': (255, 255, 255),
            'BLACK': (0, 0, 0),
            'GRAY': (128, 128, 128),
            'BLUE': (0, 0, 255),
            'RED': (255, 0, 0)
        }
        
        # Initialize UI elements
        self.background_renderer = BackgroundRenderer(
            self.config['SCREEN_WIDTH'], 
            self.config['SCREEN_HEIGHT'] + self.config['UI_HEIGHT']
        )
        self.background = self.background_renderer.render_game_background(0)
        self.font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 36)
        
        # State management
        self.pause_menu_active = False
        self.connection_error = False
        self.error_message = ""
        self.return_to_menu_countdown = 3
        self.error_timer = 0
        
        # Load character info
        self.CHARACTER_INFO = load_character_info()
        self.CHARACTER_TYPES = list(self.CHARACTER_INFO.keys())
        
        # Initialize game state
        self.game_state = self.initialize_game_state()

        # Set the initial game state in NetworkManager
        self.network_manager.last_game_state = self.game_state
        
        # Control keys
        self.host_keys = [pygame.K_1, pygame.K_2, pygame.K_3]
        self.client_keys = [pygame.K_8, pygame.K_9, pygame.K_0]

        # Time synchronization
        self.time_offset = 0.0
        self.last_heartbeat = time.time()

    def initialize_game_state(self) -> Dict[str, Any]:
        """Initialize the game state"""
        game_state = {
            'characters': [],
            'left_castle': Castle(x=0, 
                                y=self.config['SCREEN_HEIGHT']-100, 
                                team='left', 
                                render=True),
            'right_castle': Castle(x=self.config['SCREEN_WIDTH']-100, 
                                y=self.config['SCREEN_HEIGHT']-100, 
                                team='right', 
                                render=True),
            'left_gage': 0,
            'right_gage': 0,
            'camera_offset': 0,
            'elapsed_time': 0,
            'time_limit': self.config['TIME_LIMIT'],
            'game_over': False,
            'winner': None,
            'loaded_sprites': {}
        }
        
        # Load sprites
        for char_type in self.CHARACTER_TYPES:
            game_state['loaded_sprites'][char_type] = {
                'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
                'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
            }
            
        return game_state

    def handle_game_input(self, event):
        """Handle game input events"""
        team = 'left' if self.is_host else 'right'
        gage_key = f"{team}_gage"
        keys = self.host_keys if self.is_host else self.client_keys
        
        for i, key in enumerate(keys):
            if event.key == key and self.game_state[gage_key] >= self.config['SPAWN_COST']:
                if i < len(self.CHARACTER_TYPES):
                    char_type = self.CHARACTER_TYPES[i]
                    if self.is_host:
                        if self.spawn_character(team, char_type):
                            self.game_state[gage_key] -= self.config['SPAWN_COST']
                            logging.info(f"Spawned {char_type} for {team}. Gage: {self.game_state[gage_key]}")
                    else:
                        self.network_manager.send_message("spawn_request", char_type)
                        logging.info(f"Sent spawn_request for {char_type} from client.")

    def update_client(self, dt):
        """Update game state for client"""
        # Update client's gage
        self.game_state['right_gage'] = min(
            self.game_state['right_gage'] + 
            self.config['GAGE_INCREMENT'] * dt,
            self.config['MAX_GAGE']
        )
        logging.debug(f"Client gage updated: {self.game_state['right_gage']}")
                                            
        # Update characters
        characters_to_remove = []
        for character in self.game_state['characters']:
            if character.is_dead:
                characters_to_remove.append(character)
                continue
                
            enemies = [c for c in self.game_state['characters'] 
                      if c.team != character.team and not c.is_dead]
            enemy_castle = self.game_state['right_castle'] if character.team == 'left' else self.game_state['left_castle']
            
            character.update(enemies, enemy_castle, dt, self.game_state['elapsed_time'])
        
        # Remove dead characters
        for char in characters_to_remove:
            self.game_state['characters'].remove(char)
            logging.info(f"Removed dead character: {char.character_type} from {char.team}")

    def update_host(self, dt):
        """Update game state for host"""
        # Update game time
        self.game_state['elapsed_time'] += dt
        
        # Update gages
        self.game_state['left_gage'] = min(
            self.game_state['left_gage'] + 
            self.config['GAGE_INCREMENT'] * dt,
            self.config['MAX_GAGE']
        )
        self.game_state['right_gage'] = min(
            self.game_state['right_gage'] + 
            self.config['GAGE_INCREMENT'] * dt,
            self.config['MAX_GAGE']
        )
        logging.debug(f"Host gages updated: Left - {self.game_state['left_gage']}, Right - {self.game_state['right_gage']}")
        
        # Update characters
        characters_to_remove = []
        for character in self.game_state['characters']:
            if character.is_dead:
                characters_to_remove.append(character)
                continue
                
            enemies = [c for c in self.game_state['characters'] 
                      if c.team != character.team and not c.is_dead]
            enemy_castle = self.game_state['right_castle'] if character.team == 'left' else self.game_state['left_castle']
            
            character.update(enemies, enemy_castle, dt, self.game_state['elapsed_time'])
        
        # Remove dead characters
        for char in characters_to_remove:
            self.game_state['characters'].remove(char)
            logging.info(f"Removed dead character: {char.character_type} from {char.team}")
        
        # Check win conditions
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
            
            logging.info(f"Game Over: {self.game_state['winner']}")
        
        # Send state to client
        self.network_manager.send_game_state(self.game_state)

    def draw_game_objects(self):
        """Draw game objects with proper layering"""
        # Draw castles
        self.game_state['left_castle'].draw(self.screen, self.game_state['camera_offset'])
        self.game_state['right_castle'].draw(self.screen, self.game_state['camera_offset'])
        
        # Draw characters sorted by Y position for proper layering
        sorted_characters = sorted(self.game_state['characters'], key=lambda x: x.y)
        for character in sorted_characters:
            character.draw(self.screen, self.game_state['camera_offset'])

    def draw_ui(self):
        """Draw user interface elements"""
        # Draw timer
        remaining_time = max(0, self.game_state['time_limit'] - self.game_state['elapsed_time'])
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        timer_text = self.font.render(f"{minutes:02}:{seconds:02}", True, self.config['BLACK'])
        self.screen.blit(timer_text, (self.config['SCREEN_WIDTH'] // 2 - 50, 20))
        
        # Draw gage bars
        pygame.draw.rect(self.screen, self.config['BLUE'], 
                        (50, self.config['SCREEN_HEIGHT'] + 20, 
                         self.game_state['left_gage'], 20))
        pygame.draw.rect(self.screen, self.config['RED'],
                        (self.config['SCREEN_WIDTH'] - 250, self.config['SCREEN_HEIGHT'] + 20,
                         self.game_state['right_gage'], 20))
        
        # Draw character selection info
        y_offset = self.config['SCREEN_HEIGHT'] + 50
        keys = self.host_keys if self.is_host else self.client_keys
        team_color = self.config['BLUE'] if self.is_host else self.config['RED']
        team_text = "Host (Left)" if self.is_host else "Client (Right)"
        
        team_label = self.small_font.render(team_text, True, team_color)
        self.screen.blit(team_label, (50, y_offset - 30))
        
        for i, char_type in enumerate(self.CHARACTER_TYPES):
            key_display = keys[i] if i < len(keys) else None
            if key_display:
                key_text = self.small_font.render(
                    f"Press {pygame.key.name(key_display).upper()} for {char_type}", 
                    True, 
                    team_color
                )
                self.screen.blit(key_text, (50 + i*200, y_offset))
        
        # Draw castle HP
        left_hp = f"Left Castle: {int(self.game_state['left_castle'].hp)}"
        right_hp = f"Right Castle: {int(self.game_state['right_castle'].hp)}"
        left_hp_text = self.small_font.render(left_hp, True, self.config['BLUE'])
        right_hp_text = self.small_font.render(right_hp, True, self.config['RED'])
        self.screen.blit(left_hp_text, (50, 60))
        self.screen.blit(right_hp_text, (self.config['SCREEN_WIDTH'] - 250, 60))

    def draw_connection_status(self):
        """Draw connection status indicator with null safety"""
        if not hasattr(self, 'network_manager') or self.network_manager is None:
            status_color = (255, 0, 0)  # Red for disconnected
            status_text = "Disconnected"
        else:
            status_color = (0, 255, 0) if self.network_manager.connected else (255, 0, 0)
            status_text = "Connected" if self.network_manager.connected else "Disconnected"
        
        text = self.small_font.render(status_text, True, status_color)
        self.screen.blit(text, (self.screen.get_width() - text.get_width() - 10, 10))

    def draw_network_stats(self):
        """Draw network statistics with null safety"""
        if not hasattr(self, 'network_manager') or self.network_manager is None:
            return
            
        try:
            stats = self.network_manager.get_network_stats()
            texts = [
                f"RTT: {stats['average_rtt']*1000:.1f}ms",
                f"Pending: {stats['pending_messages']}",
                f"Loss Rate: {stats['message_loss_rate']*100:.1f}%"
            ]
            
            y = 40
            for text_str in texts:
                stat_text = self.small_font.render(text_str, True, self.config['BLACK'])
                self.screen.blit(stat_text, (10, y))
                y += 20
        except Exception as e:
            logging.error(f"Error drawing network stats: {e}")

    def update(self, dt):
        """Update with better connection error handling"""
        if self.connection_error or not self.network_manager:
            self.error_timer += dt
            if self.error_timer >= self.return_to_menu_countdown:
                self.return_to_menu()
            return
        
        try:
            if not self.network_manager.connected:
                self.handle_disconnection()
                return
                
            if self.pause_menu_active or self.game_state['game_over']:
                return
                
            # Update network manager
            self.network_manager.update()
            
            # Process network messages
            while True:
                message = self.network_manager.get_next_message()
                if not message:
                    break
                self.handle_network_message(message)
            
            # Update game state based on role
            if self.is_host:
                self.update_host(dt)
            else:
                self.update_client(dt)
        except Exception as e:
            logging.error(f"Error in update: {e}")
            self.handle_disconnection()

    def draw_error_screen(self):
        """Draw network error screen"""
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        center_x = self.screen.get_width() // 2
        center_y = self.screen.get_height() // 2
        
        error_text = self.font.render(self.error_message, True, self.config['WHITE'])
        self.screen.blit(error_text, 
                        error_text.get_rect(center=(center_x, center_y - 50)))
        
        remaining = max(0, self.return_to_menu_countdown - self.error_timer)
        countdown_text = self.small_font.render(
            f"Returning to menu in {remaining:.1f} seconds...", 
            True, 
            self.config['WHITE']
        )
        self.screen.blit(countdown_text, 
                        countdown_text.get_rect(center=(center_x, center_y + 50)))
        
        escape_text = self.small_font.render(
            "Press ESC to return to menu now", 
            True, 
            self.config['WHITE']
        )
        self.screen.blit(escape_text, 
                        escape_text.get_rect(center=(center_x, center_y + 100)))

    def draw_pause_menu(self):
        """Draw pause menu overlay"""
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        screen_center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        
        pause_text = self.font.render("PAUSED", True, self.config['WHITE'])
        resume_text = self.small_font.render("Press R to Resume", True, self.config['WHITE'])
        quit_text = self.small_font.render("Press Q to Quit", True, self.config['WHITE'])
        
        self.screen.blit(pause_text, 
                        pause_text.get_rect(center=(screen_center[0], screen_center[1] - 100)))
        self.screen.blit(resume_text, 
                        resume_text.get_rect(center=screen_center))
        self.screen.blit(quit_text, 
                        quit_text.get_rect(center=(screen_center[0], screen_center[1] + 100)))

    def draw_game_over(self):
        """Draw game over screen"""
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        screen_center = (self.screen.get_width() // 2, self.screen.get_height() // 2)
        
        winner_text = self.font.render(self.game_state['winner'], True, self.config['WHITE'])
        self.screen.blit(winner_text, 
                        winner_text.get_rect(center=(screen_center[0], screen_center[1] - 100)))
        
        left_score = f"Left Castle HP: {int(self.game_state['left_castle'].hp)}"
        right_score = f"Right Castle HP: {int(self.game_state['right_castle'].hp)}"
        
        score_font = pygame.font.Font(None, 48)
        left_score_text = score_font.render(left_score, True, self.config['BLUE'])
        right_score_text = score_font.render(right_score, True, self.config['RED'])
        
        self.screen.blit(left_score_text, 
                        left_score_text.get_rect(center=(screen_center[0], screen_center[1])))
        self.screen.blit(right_score_text, 
                        right_score_text.get_rect(center=(screen_center[0], screen_center[1] + 50)))

    def draw(self):
        """Main draw method"""
        # Draw base game elements
        self.screen.blit(self.background, (0, 0))
        
        # Draw game objects
        self.draw_game_objects()
        
        # Draw UI elements
        self.draw_ui()
        
        # Draw network information
        self.draw_network_stats()
        self.draw_connection_status()
        
        # Draw overlays
        if self.connection_error:
            self.draw_error_screen()
        elif self.pause_menu_active:
            self.draw_pause_menu()
        elif self.game_state['game_over']:
            self.draw_game_over()
            
        pygame.display.flip()

    def spawn_character(self, team: str, character_type: str) -> bool:
        """Spawn a character with network synchronization"""
        if len([c for c in self.game_state['characters'] if c.team == team]) >= self.config['MAX_CHARACTERS'] // 2:
            logging.warning(f"Cannot spawn more characters for team {team}. Max limit reached.")
            return False
            
        x = 100 if team == 'left' else self.config['SCREEN_WIDTH'] - 140
        y = self.config['SCREEN_HEIGHT'] - 100
        
        try:
            character = Character(
                sprites=self.game_state['loaded_sprites'][character_type][team],
                x=x, y=y,
                team=team,
                character_type=character_type,
                time_scale=1
            )
            
            self.game_state['characters'].append(character)
            logging.info(f"Spawned {character_type} for team {team} at position ({x}, {y}).")
            return True
            
        except Exception as e:
            logging.error(f"Error spawning character: {e}")
            return False

    def handle_disconnection(self):
        """Handle network disconnection"""
        if not self.connection_error:
            self.connection_error = True
            self.error_message = "Connection Lost"
            self.error_timer = 0
            logging.warning("Connection lost, preparing to return to menu.")
            
            # Clean up network manager
            if self.network_manager:
                try:
                    self.network_manager.close()
                except:
                    pass
                self.network_manager = None

    def return_to_menu(self):
        """Clean up and return to main menu"""
        self.clean_up()
        from .home_scene import HomeScene  # Ensure this import is correct
        self.switch_to_scene(HomeScene(self.screen))
    
    def process_game_state(self, message: NetworkMessage):
        """Process the game_state or delta_state message"""
        try:
            # Deserialize the game state directly as it is now only MessagePack serialized
            updated_state = GameStateSerializer.deserialize_game_state(
                message.data,
                self.game_state.get('loaded_sprites', {})
            )
            if updated_state:
                # Apply delta updates
                self.game_state.update(updated_state)
                logging.info(f"Game state updated from host. Sequence: {message.sequence_number}")
        except Exception as e:
            logging.error(f"Error processing game_state message: {e}")
            self.handle_disconnection()

    def handle_spawn_request(self, message: NetworkMessage):
        """Handle spawn_request messages when hosting"""
        try:
            # Validate spawn request
            if not isinstance(message.data, str) or message.data not in self.CHARACTER_TYPES:
                logging.warning(f"Invalid spawn request: {message.data}")
                return
                
            if self.game_state['right_gage'] >= self.config['SPAWN_COST']:
                if self.spawn_character('right', message.data):
                    self.game_state['right_gage'] -= self.config['SPAWN_COST']
                    logging.info(f"Spawned {message.data} for right team. Gage: {self.game_state['right_gage']}")
                    # Send updated game state to client
                    self.network_manager.send_game_state(self.game_state)
        except Exception as e:
            logging.error(f"Error handling spawn_request: {e}")
            self.handle_disconnection()

    def handle_network_message(self, message: NetworkMessage):
        """Enhanced network message handling with sequence ordering"""
        try:
            logging.info(f"Received message type: {message.type}, sequence: {message.sequence_number}")

            if message.type != "ack":
                # Send an acknowledgment for the received message
                self.network_manager.send_ack(message.sequence_number)
            
            # Handle messages based on type
            if message.type == "game_state" or message.type == "delta_state":
                # Check sequence number
                if message.sequence_number < self.expected_sequence:
                    logging.debug(f"Ignoring old message {message.sequence_number}. Expected: {self.expected_sequence}")
                    return  # Ignore old messages

                elif message.sequence_number == self.expected_sequence:
                    # Process the message
                    self.process_game_state(message)
                    self.expected_sequence += 1

                    # Check if there are buffered messages that can now be processed
                    while self.expected_sequence in self.buffer:
                        buffered_message = self.buffer.pop(self.expected_sequence)
                        self.process_game_state(buffered_message)
                        self.expected_sequence += 1

                else:
                    # Future message, buffer it
                    if len(self.buffer) < self.BUFFER_LIMIT:
                        self.buffer[message.sequence_number] = message
                        logging.warning(f"Out-of-order message received. Expected: {self.expected_sequence}, Received: {message.sequence_number}. Buffered.")
                    else:
                        logging.error("Buffer limit reached. Dropping out-of-order message.")
            
            elif message.type == "spawn_request" and self.is_host:
                # Handle spawn request
                self.handle_spawn_request(message)

            elif message.type == "retransmit_request" and self.is_host:
                # Handle retransmission request
                self.handle_retransmit_request(message)
            
            # Handle other message types if any

        except Exception as e:
            logging.error(f"Error handling network message: {e}")
            self.handle_disconnection()

    def handle_retransmit_request(self, message: NetworkMessage):
        """Handle retransmission requests from client"""
        try:
            missing_sequence = message.data
            # Retrieve the message from pending_acks or history
            if missing_sequence in self.pending_acks:
                message_to_retransmit, _, _ = self.pending_acks[missing_sequence]
                self.network_manager.retransmit_message(message_to_retransmit)
                logging.info(f"Retransmitted message {missing_sequence} upon client request.")
            else:
                logging.warning(f"Retransmission requested for unknown sequence {missing_sequence}.")
        except Exception as e:
            logging.error(f"Error handling retransmit_request: {e}")
            self.handle_disconnection()

    def sync_time(self, server_time: float):
        """Synchronize client time with server"""
        current_time = pygame.time.get_ticks() / 1000
        self.time_offset = server_time - current_time
        logging.debug(f"Synchronized time with server. Time offset: {self.time_offset}")

    def handle_events(self, events):
        """Enhanced event handling"""
        for event in events:
            if event.type == pygame.QUIT:
                self.clean_up()
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.connection_error:
                        self.return_to_menu()
                    else:
                        self.pause_menu_active = not self.pause_menu_active
                        logging.info(f"Pause menu active: {self.pause_menu_active}")
                elif self.pause_menu_active:
                    self.handle_pause_menu_input(event)
                elif not self.game_state['game_over']:
                    self.handle_game_input(event)
            elif event.type == pygame.VIDEORESIZE:
                self.handle_resize(event)
            elif event.type == pygame.ACTIVEEVENT:
                self.handle_window_event(event)

    def handle_resize(self, event):
        """Handle window resize events"""
        new_width, new_height = event.w, event.h
        if new_width != self.screen.get_width() or new_height != self.screen.get_height():
            self.config['SCREEN_WIDTH'] = new_width
            self.config['SCREEN_HEIGHT'] = new_height - self.config['UI_HEIGHT']
            self.config['WINDOW_HEIGHT'] = new_height
            self.background_renderer = BackgroundRenderer(new_width, new_height)
            self.background = self.background_renderer.render_game_background(0)  # Adjust stage_number as needed
            logging.info(f"Window resized to ({new_width}, {new_height}). Background re-rendered.")

    def handle_window_event(self, event):
        """Handle window minimize/restore events"""
        if event.state == pygame.APPACTIVE:
            if event.gain:  # Window restored
                self.resume_game()
            else:  # Window minimized
                self.pause_game()

    def resume_game(self):
        """Resume game after window restore"""
        if self.network_manager and not self.network_manager.connected:
            self.handle_disconnection()
        elif self.is_host:
            self.network_manager.send_game_state(self.game_state)
            logging.info("Resumed game and sent game state to client.")

    def pause_game(self):
        """Handle game pause"""
        self.pause_menu_active = True
        logging.info("Game paused due to window minimize.")

    def clean_up(self):
        """Enhanced cleanup with state saving"""
        if self.network_manager:
            try:
                # Save final game state if needed
                if self.game_state.get('game_over'):
                    self.save_game_results()
                self.network_manager.close()
                logging.info("Network manager closed.")
            except Exception as e:
                logging.error(f"Error during cleanup: {e}")
            finally:
                self.network_manager = None

    def save_game_results(self):
        """Save game results for statistics"""
        try:
            results = {
                'winner': self.game_state.get('winner'),
                'duration': self.game_state.get('elapsed_time'),
                'left_castle_hp': self.game_state['left_castle'].hp,
                'right_castle_hp': self.game_state['right_castle'].hp,
                'timestamp': pygame.time.get_ticks() / 1000
            }
            # Implement your saving mechanism here (e.g., write to a file or database)
            logging.info(f"Game results: {results}")
        except Exception as e:
            logging.error(f"Error saving game results: {e}")

