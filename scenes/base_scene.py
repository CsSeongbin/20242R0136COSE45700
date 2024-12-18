# scenes/base_scene.py
import pygame
import os
from .background import BackgroundRenderer

class Scene:
    def __init__(self, screen):
        self.screen = screen
        self.next_scene = self
        self.background_renderer = BackgroundRenderer(screen.get_width(), screen.get_height())

        # Load background images
        self.backgrounds = {
            'home': pygame.image.load(os.path.join('assets', 'home_background.svg')),
            'stage_select': pygame.image.load(os.path.join('assets', 'stage_select_background.svg')),
            'stage1': pygame.image.load(os.path.join('assets', 'game_background_1.svg')),
            'stage2': pygame.image.load(os.path.join('assets', 'game_background_2.svg')),
            'stage3': pygame.image.load(os.path.join('assets', 'game_background_3.svg'))
        }
        
        # Scale backgrounds to screen size
        for key in self.backgrounds:
            self.backgrounds[key] = pygame.transform.scale(
                self.backgrounds[key], 
                (self.screen.get_width(), self.screen.get_height())
            )
    def switch_to_scene(self, next_scene):
        """Switch to a new scene"""
        self.next_scene = next_scene
    
    def terminate(self):
        """Terminate the game"""
        self.is_terminated = True
    
    def handle_events(self, events):
        """Handle input events"""
        raise NotImplementedError
    
    def update(self, dt):
        """Update game state"""
        raise NotImplementedError
    
    def draw(self):
        """Draw the scene"""
        raise NotImplementedError