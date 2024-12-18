# backgrounds.py
import pygame
import random
import math

class BackgroundRenderer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        
    def render_home_background(self):
        """Create home scene background"""
        surface = pygame.Surface((self.width, self.height))
        
        # Sky gradient
        for y in range(self.height):
            color = self._interpolate_color((135, 206, 235), (224, 246, 255), y/self.height)
            pygame.draw.line(surface, color, (0, y), (self.width, y))
            
        # Draw clouds
        for _ in range(5):
            x = random.randint(0, self.width)
            y = random.randint(50, 200)
            self._draw_cloud(surface, x, y)
            
        # Draw castles silhouette
        castle_color = (44, 62, 80)
        self._draw_castle(surface, 100, castle_color)  # Left castle
        self._draw_castle(surface, self.width - 200, castle_color)  # Right castle
        
        # Draw ground
        ground_rect = pygame.Rect(0, self.height - 200, self.width, 200)
        pygame.draw.rect(surface, (144, 169, 85), ground_rect)
        
        return surface
        
    def render_stage_select_background(self):
        """Create stage select background"""
        surface = pygame.Surface((self.width, self.height))
        
        # Background gradient
        for y in range(self.height):
            color = self._interpolate_color((44, 83, 100), (15, 32, 39), y/self.height)
            pygame.draw.line(surface, color, (0, y), (self.width, y))
            
        # Grid pattern
        for x in range(0, self.width, 50):
            pygame.draw.line(surface, (255, 255, 255, 30), (x, 0), (x, self.height))
        for y in range(0, self.height, 50):
            pygame.draw.line(surface, (255, 255, 255, 30), (0, y), (self.width, y))
            
        # Stage indicators
        colors = [(76, 175, 80), (255, 193, 7), (244, 67, 54)]  # Green, Yellow, Red
        for i, color in enumerate(colors):
            x = (i + 1) * (self.width // 4)
            pygame.draw.circle(surface, color, (x, 200), 40)
            font = pygame.font.Font(None, 48)
            text = font.render(str(i + 1), True, (255, 255, 255))
            text_rect = text.get_rect(center=(x, 200))
            surface.blit(text, text_rect)
            
            # Connecting lines
            if i < len(colors) - 1:
                next_x = ((i + 2) * self.width) // 4
                pygame.draw.line(surface, (255, 255, 255), 
                               (x + 50, 200), (next_x - 50, 200), 2)
        
        return surface
        
    def render_game_background(self, stage_number):
        """Create game stage background"""
        surface = pygame.Surface((self.width, self.height))
        
        if stage_number == 0:  # Stage 1 - Peaceful meadow
            # Sky
            for y in range(self.height):
                color = self._interpolate_color((178, 225, 255), (212, 241, 249), y/self.height)
                pygame.draw.line(surface, color, (0, y), (self.width, y))
                
            # Clouds
            for _ in range(8):
                x = random.randint(0, self.width)
                y = random.randint(50, 150)
                self._draw_cloud(surface, x, y)
                
            # Ground
            ground_rect = pygame.Rect(0, self.height - 200, self.width, 200)
            pygame.draw.rect(surface, (144, 169, 85), ground_rect)
            
            # Ground details
            for _ in range(100):
                x = random.randint(0, self.width)
                y = random.randint(self.height - 190, self.height - 10)
                pygame.draw.circle(surface, (112, 130, 56), (x, y), 2)
                
        elif stage_number == 1:  # Stage 2 - Desert battlefield
            # Sky
            for y in range(self.height):
                color = self._interpolate_color((255, 184, 140), (222, 98, 98), y/self.height)
                pygame.draw.line(surface, color, (0, y), (self.width, y))
                
            # Mountains
            mountain_color = (139, 69, 19)
            points = [(0, self.height - 200)]
            for i in range(5):
                x = self.width * (i + 1) // 5
                y = self.height - 200 - random.randint(50, 150)
                points.append((x, y))
            points.append((self.width, self.height - 200))
            pygame.draw.polygon(surface, mountain_color, points)
            
            # Ground
            ground_rect = pygame.Rect(0, self.height - 200, self.width, 200)
            pygame.draw.rect(surface, (184, 115, 51), ground_rect)
            
        else:  # Stage 3 - Dark realm
            # Sky
            for y in range(self.height):
                color = self._interpolate_color((75, 108, 183), (24, 40, 72), y/self.height)
                pygame.draw.line(surface, color, (0, y), (self.width, y))
                
            # Mystical effects
            for _ in range(50):
                x = random.randint(0, self.width)
                y = random.randint(0, self.height - 200)
                radius = random.randint(1, 3)
                opacity = random.randint(30, 100)
                star_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(star_surf, (255, 255, 255, opacity), (radius, radius), radius)
                surface.blit(star_surf, (x - radius, y - radius))
                
            # Ground
            ground_rect = pygame.Rect(0, self.height - 200, self.width, 200)
            pygame.draw.rect(surface, (62, 75, 102), ground_rect)
            
        return surface
    
    def _interpolate_color(self, color1, color2, factor):
        """Interpolate between two colors"""
        return tuple(int(color1[i] + (color2[i] - color1[i]) * factor) for i in range(3))
    
    def _draw_cloud(self, surface, x, y):
        """Draw a simple cloud"""
        cloud_color = (255, 255, 255, 128)
        cloud_surf = pygame.Surface((100, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(cloud_surf, cloud_color, (0, 0, 60, 30))
        pygame.draw.ellipse(cloud_surf, cloud_color, (20, 10, 60, 30))
        pygame.draw.ellipse(cloud_surf, cloud_color, (40, 0, 60, 30))
        surface.blit(cloud_surf, (x - 50, y - 25))
    
    def _draw_castle(self, surface, x, color):
        """Draw a simple castle silhouette"""
        points = [
            (x, self.height - 200),  # base left
            (x, self.height - 300),  # tower left
            (x + 25, self.height - 350),  # tower point
            (x + 50, self.height - 300),  # tower right
            (x + 100, self.height - 300),  # wall top
            (x + 100, self.height - 200),  # base right
        ]
        pygame.draw.polygon(surface, color, points)