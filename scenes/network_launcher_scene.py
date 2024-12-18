import pygame
import socket
from typing import Optional, Tuple
from .base_scene import Scene
from network_manager import NetworkManager

class NetworkLauncherScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.font = pygame.font.Font(None, 64)
        self.small_font = pygame.font.Font(None, 36)
        
        # Scene states
        self.STATES = {
            'MENU': 0,
            'HOST': 1,
            'JOIN': 2,
            'WAITING': 3,
            'CONNECTING': 4,
            'ERROR': 5
        }
        self.current_state = self.STATES['MENU']
        
        # Menu options
        self.menu_options = ['Host Game', 'Join Game', 'Back']
        self.selected_option = 0
        
        # Network settings
        self.port = 5555
        self.network_manager: Optional[NetworkManager] = None
        self.ip_address = ''
        self.error_message = ''
        
        # Input handling
        self.input_text = ''
        self.input_active = False
        
        # Get local IP
        self.local_ip = self.get_local_ip()
        
    def get_local_ip(self) -> str:
        """Get the local IP address"""
        try:
            # Create a temporary socket to get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return '127.0.0.1'

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.current_state == self.STATES['MENU']:
                    self.handle_menu_input(event)
                elif self.current_state == self.STATES['JOIN']:
                    self.handle_join_input(event)
                elif self.current_state == self.STATES['ERROR']:
                    if event.key == pygame.K_ESCAPE:
                        self.current_state = self.STATES['MENU']
                elif event.key == pygame.K_ESCAPE:
                    from .home_scene import HomeScene
                    self.switch_to_scene(HomeScene(self.screen))

    def handle_menu_input(self, event):
        """Handle input in the main menu state"""
        if event.key == pygame.K_UP:
            self.selected_option = (self.selected_option - 1) % len(self.menu_options)
        elif event.key == pygame.K_DOWN:
            self.selected_option = (self.selected_option + 1) % len(self.menu_options)
        elif event.key == pygame.K_RETURN:
            if self.menu_options[self.selected_option] == 'Host Game':
                self.start_host()
            elif self.menu_options[self.selected_option] == 'Join Game':
                self.current_state = self.STATES['JOIN']
                self.input_text = ''
                self.input_active = True
            elif self.menu_options[self.selected_option] == 'Back':
                from .home_scene import HomeScene
                self.switch_to_scene(HomeScene(self.screen))

    def handle_join_input(self, event):
        """Handle input in the join game state"""
        if event.key == pygame.K_RETURN:
            if self.input_text:
                self.start_client(self.input_text)
        elif event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
        else:
            # Only allow IP address characters
            if event.unicode in '0123456789.':
                self.input_text += event.unicode

    def start_host(self):
        """Initialize host game"""
        try:
            self.network_manager = NetworkManager(is_host=True)
            if self.network_manager.start_server(self.port):
                self.current_state = self.STATES['WAITING']
            else:
                self.error_message = "Failed to start server"
                self.current_state = self.STATES['ERROR']
        except Exception as e:
            self.error_message = f"Error starting server: {str(e)}"
            self.current_state = self.STATES['ERROR']

    def start_client(self, ip: str):
        """Initialize client game"""
        try:
            self.network_manager = NetworkManager(is_host=False)
            self.current_state = self.STATES['CONNECTING']
            
            if self.network_manager.connect_to_server(ip, self.port):
                from .network_game_scene import NetworkGameScene
                self.switch_to_scene(NetworkGameScene(self.screen, self.network_manager))
            else:
                self.error_message = "Failed to connect to server"
                self.current_state = self.STATES['ERROR']
        except Exception as e:
            self.error_message = f"Error connecting to server: {str(e)}"
            self.current_state = self.STATES['ERROR']

    def update(self, dt):
        if self.current_state == self.STATES['WAITING'] and self.network_manager:
            if self.network_manager.connected:
                from .network_game_scene import NetworkGameScene
                self.switch_to_scene(NetworkGameScene(self.screen, self.network_manager))

    def draw(self):
        # Fill background
        self.screen.fill((255, 255, 255))
        
        if self.current_state == self.STATES['MENU']:
            self.draw_menu()
        elif self.current_state == self.STATES['HOST']:
            self.draw_host_screen()
        elif self.current_state == self.STATES['JOIN']:
            self.draw_join_screen()
        elif self.current_state == self.STATES['WAITING']:
            self.draw_waiting_screen()
        elif self.current_state == self.STATES['CONNECTING']:
            self.draw_connecting_screen()
        elif self.current_state == self.STATES['ERROR']:
            self.draw_error_screen()

    def draw_menu(self):
        """Draw the main menu screen"""
        title = self.font.render("Network Game", True, (0, 0, 0))
        title_rect = title.get_rect(center=(self.screen.get_width() // 2, 100))
        self.screen.blit(title, title_rect)
        
        start_y = 250
        for i, option in enumerate(self.menu_options):
            color = (255, 0, 0) if i == self.selected_option else (0, 0, 0)
            text = self.font.render(option, True, color)
            rect = text.get_rect(center=(self.screen.get_width() // 2, start_y + i * 80))
            self.screen.blit(text, rect)

    def draw_host_screen(self):
        """Draw the host game screen"""
        title = self.font.render("Host Game", True, (0, 0, 0))
        self.screen.blit(title, title.get_rect(center=(self.screen.get_width() // 2, 100)))
        
        ip_text = self.small_font.render(f"Your IP: {self.local_ip}", True, (0, 0, 0))
        self.screen.blit(ip_text, ip_text.get_rect(center=(self.screen.get_width() // 2, 250)))

    def draw_join_screen(self):
        """Draw the join game screen"""
        title = self.font.render("Join Game", True, (0, 0, 0))
        self.screen.blit(title, title.get_rect(center=(self.screen.get_width() // 2, 100)))
        
        prompt = self.small_font.render("Enter Host IP:", True, (0, 0, 0))
        self.screen.blit(prompt, prompt.get_rect(center=(self.screen.get_width() // 2, 200)))
        
        # Draw input box
        input_text = self.small_font.render(self.input_text, True, (0, 0, 0))
        input_rect = pygame.Rect(self.screen.get_width() // 2 - 100, 250, 200, 40)
        pygame.draw.rect(self.screen, (200, 200, 200), input_rect)
        self.screen.blit(input_text, input_text.get_rect(center=input_rect.center))

    def draw_waiting_screen(self):
        """Draw the waiting for connection screen"""
        title = self.font.render("Waiting for Player...", True, (0, 0, 0))
        self.screen.blit(title, title.get_rect(center=(self.screen.get_width() // 2, 100)))
        
        ip_text = self.small_font.render(f"Your IP: {self.local_ip}", True, (0, 0, 0))
        self.screen.blit(ip_text, ip_text.get_rect(center=(self.screen.get_width() // 2, 250)))

    def draw_connecting_screen(self):
        """Draw the connecting screen"""
        title = self.font.render("Connecting...", True, (0, 0, 0))
        self.screen.blit(title, title.get_rect(center=(self.screen.get_width() // 2, 100)))

    def draw_error_screen(self):
        """Draw the error screen"""
        title = self.font.render("Error", True, (255, 0, 0))
        self.screen.blit(title, title.get_rect(center=(self.screen.get_width() // 2, 100)))
        
        error_text = self.small_font.render(self.error_message, True, (0, 0, 0))
        self.screen.blit(error_text, error_text.get_rect(center=(self.screen.get_width() // 2, 250)))
        
        instruction = self.small_font.render("Press ESC to return to menu", True, (0, 0, 0))
        self.screen.blit(instruction, instruction.get_rect(center=(self.screen.get_width() // 2, 400)))
