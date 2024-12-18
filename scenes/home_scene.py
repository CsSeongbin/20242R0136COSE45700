# scenes/home_scene.py
import pygame
from .base_scene import Scene
from .stage_select_scene import StageSelectScene
from .multiplayer_scene import MultiplayerGameScene
from .network_launcher_scene import NetworkLauncherScene
import os

class HomeScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.screen = screen

        # Path to the background image
        background_path = os.path.join('sprites', 'main_home_image.png')

        # Load the background image
        if os.path.exists(background_path):
            try:
                self.background = pygame.image.load(background_path).convert()
                # Scale the background to fit the screen
                self.background = pygame.transform.scale(
                    self.background, 
                    (self.screen.get_width(), self.screen.get_height())
                )
            except pygame.error as e:
                print(f"Failed to load background image: {e}")
                # Fallback to the programmatically rendered background
                self.background = self.background_renderer.render_home_background()
        else:
            print(f"Background image not found at {background_path}. Using default background.")
            # Fallback to the programmatically rendered background
            self.background = self.background_renderer.render_home_background()
        
        # Create a semi-transparent overlay
        self.overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 100))  # Black with alpha=100 (out of 255)

        # Initialize fonts
        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)

        # Menu options
        self.selected_option = 0
        self.options = [
            "Campaign",
            "Local Multiplayer",
            "Network Game",
            "Quit"
        ]
        
        # Load any additional assets if necessary
        # For example, checkmark icons can be loaded here if used

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_option = (self.selected_option - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    self.handle_selection()

    def handle_selection(self):
        selected = self.options[self.selected_option]
        if selected == "Campaign":
            self.switch_to_scene(StageSelectScene(self.screen))
        elif selected == "Local Multiplayer":
            self.switch_to_scene(MultiplayerGameScene(self.screen))
        elif selected == "Network Game":
            self.switch_to_scene(NetworkLauncherScene(self.screen))
        elif selected == "Quit":
            self.next_scene = None

    def update(self, dt):
        pass

    def draw(self):
        # Blit the background
        self.screen.blit(self.background, (0, 0))
        
        # Blit the semi-transparent overlay
        self.screen.blit(self.overlay, (0, 0))
        
        # Draw title with shadow
        title_text = "Castle Defense Game"
        title_color = (255, 255, 255)  # White text
        shadow_color = (0, 0, 0)        # Black shadow
        title_position = (self.screen.get_width() // 2, 100)
        
        shadow, shadow_rect, main_text, main_rect = self.render_text_with_shadow(
            self.font, title_text, title_color, shadow_color, title_position, shadow_offset=(3, 3)
        )
        
        # Center the shadow and text
        shadow_rect.center = title_position
        main_rect.center = title_position
        
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(main_text, main_rect)
        
        # Draw menu options with shadows
        start_y = 250
        for i, option in enumerate(self.options):
            color = (255, 0, 0) if i == self.selected_option else (255, 255, 255)
            shadow_col = (0, 0, 0) if i == self.selected_option else (0, 0, 0)
            option_position = (self.screen.get_width() // 2, start_y + i * 80)
            
            shadow, shadow_rect, main_text, main_rect = self.render_text_with_shadow(
                self.font, option, color, shadow_col, option_position, shadow_offset=(2, 2)
            )
            
            shadow_rect.center = option_position
            main_rect.center = option_position
            
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(main_text, main_rect)
        
        # Draw controls hint with shadow
        controls_text = "↑↓: Select   ENTER: Confirm"
        controls_color = (255, 255, 255)  # White text
        controls_shadow_color = (0, 0, 0)  # Black shadow
        controls_position = (self.screen.get_width() // 2, 200)
        
        shadow, shadow_rect, main_text, main_rect = self.render_text_with_shadow(
            self.small_font, controls_text, controls_color, controls_shadow_color, controls_position, shadow_offset=(1, 1)
        )
        
        shadow_rect.center = controls_position
        main_rect.center = controls_position
        
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(main_text, main_rect)

    def render_text_with_shadow(self, font, text, text_color, shadow_color, position, shadow_offset=(2, 2)):
        """
        Renders text with a shadow.

        Parameters:
            font (pygame.font.Font): The font to use.
            text (str): The text to render.
            text_color (tuple): The color of the main text.
            shadow_color (tuple): The color of the shadow.
            position (tuple): The (x, y) position to center the text.
            shadow_offset (tuple): The (x, y) offset for the shadow.

        Returns:
            tuple: Surfaces and rects for shadow and main text.
        """
        # Render shadow
        shadow = font.render(text, True, shadow_color)
        shadow_rect = shadow.get_rect()
        shadow_rect.center = (position[0] + shadow_offset[0], position[1] + shadow_offset[1])
        
        # Render main text
        main_text = font.render(text, True, text_color)
        main_rect = main_text.get_rect()
        main_rect.center = position
        
        return (shadow, shadow_rect, main_text, main_rect)
