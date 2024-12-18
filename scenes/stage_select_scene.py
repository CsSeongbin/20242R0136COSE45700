# scenes/stage_select_scene.py
import pygame
from .base_scene import Scene
from .utils.logger import load_stage_logs  # Import logger
import os

class StageSelectScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.screen = screen
        
        # Path to the background image
        background_path = os.path.join('sprites', 'stage_select_image.png')
        
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
                self.background = self.background_renderer.render_stage_select_background()
        else:
            print(f"Background image not found at {background_path}. Using default background.")
            self.background = self.background_renderer.render_stage_select_background()
        
        # Create a semi-transparent overlay
        self.overlay = pygame.Surface((self.screen.get_width(), self.screen.get_height()), pygame.SRCALPHA)
        self.overlay.fill((0, 0, 0, 100))  # Black with alpha=100 (out of 255)
        
        self.font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 28)
        self.selected_stage = 0
        self.stages = [
            {
                "name": f"Stage {i+1}",
                "description": f"Battle against AI.",
                "difficulty": "Easy" if i < 3 else "Medium" if i < 7 else "Hard",
                "ai_model": f"episode_{200 * (i+1)}"
            }
            for i in range(10)
        ]
        
        # Debug: Check for missing 'description' keys
        for idx, stage in enumerate(self.stages):
            if 'description' not in stage:
                print(f"Error: Stage {idx+1} is missing the 'description' key.")
        
        # Scrolling attributes
        self.start_stage = 0            # Index of the first visible stage
        self.visible_stage_count = 5    # Number of stages visible at once
        self.vertical_spacing = 100      # Space between each stage entry
        self.start_y = 120               # Starting Y-coordinate for the first visible stage
        self.stage_height = 90           # Approximate height per stage block
        
        # Load stage logs
        self.stage_logs = load_stage_logs()
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    # Prevent moving above the first stage
                    if self.selected_stage > 0:
                        self.selected_stage -= 1
                        # Adjust start_stage if necessary
                        if self.selected_stage < self.start_stage:
                            self.start_stage = max(self.start_stage - 1, 0)
                elif event.key == pygame.K_DOWN:
                    # Prevent moving below the last stage
                    if self.selected_stage < len(self.stages) - 1:
                        self.selected_stage += 1
                        # Adjust start_stage if necessary
                        if self.selected_stage >= self.start_stage + self.visible_stage_count:
                            self.start_stage = min(
                                self.start_stage + 1,
                                len(self.stages) - self.visible_stage_count
                            )
                elif event.key == pygame.K_RETURN:
                    from .game_scene import GameScene
                    self.switch_to_scene(GameScene(self.screen, self.selected_stage))
                elif event.key == pygame.K_ESCAPE:
                    from .home_scene import HomeScene
                    self.switch_to_scene(HomeScene(self.screen))
    
    def update(self, dt):
        pass

    # Utility function to render text with shadow
    def render_text_with_shadow(self, font, text, text_color, shadow_color, position, shadow_offset=(2, 2)):
        # Render shadow
        shadow = font.render(text, True, shadow_color)
        shadow_rect = shadow.get_rect(topleft=(position[0] + shadow_offset[0], position[1] + shadow_offset[1]))
        
        # Render main text
        main_text = font.render(text, True, text_color)
        main_rect = main_text.get_rect(topleft=position)
        
        return (shadow, shadow_rect, main_text, main_rect)
    
    def draw(self):
        # Blit the background
        self.screen.blit(self.background, (0, 0))
        
        # Blit the semi-transparent overlay
        self.screen.blit(self.overlay, (0, 0))
        
        # Draw title with shadow
        title_text = "Select Stage"
        shadow_color = (0, 0, 0)  # Black shadow
        text_color = (255, 255, 255)  # White text
        title_position = (self.screen.get_width() // 2, 50)
        
        shadow, shadow_rect, main_text, main_rect = self.render_text_with_shadow(
            self.font, title_text, text_color, shadow_color, title_position, shadow_offset=(2, 2)
        )
        
        # Center the shadow and text
        shadow_rect.center = title_position
        main_rect.center = title_position
        
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(main_text, main_rect)
        
        # Determine the range of stages to display
        end_stage = self.start_stage + self.visible_stage_count
        visible_stages = self.stages[self.start_stage:end_stage]
        
        # Draw stage options
        current_y = self.start_y
        for i, stage in enumerate(visible_stages):
            actual_stage_index = self.start_stage + i
            is_selected = (actual_stage_index == self.selected_stage)
            
            # Highlight selected stage with a semi-transparent rectangle
            if is_selected:
                highlight_color = (200, 200, 200, 150)  # Light gray with transparency
                highlight_rect = pygame.Surface((self.screen.get_width() - 200, self.stage_height), pygame.SRCALPHA)
                highlight_rect.fill(highlight_color)
                self.screen.blit(highlight_rect, (100, current_y - 10))
            
            # Draw stage name with shadow
            stage_name = stage["name"]
            text_color = (255, 0, 0) if is_selected else (255, 255, 255)  # Red for selected, white otherwise
            shadow_color = (0, 0, 0)
            stage_position = (120, current_y)
            
            shadow, shadow_rect, main_text, main_rect = self.render_text_with_shadow(
                self.font, stage_name, text_color, shadow_color, stage_position, shadow_offset=(2, 2)
            )
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(main_text, main_rect)
            
            # Draw stage description with shadow
            desc = stage.get("description", "No Description Available")
            desc_color = (200, 200, 200)  # Light gray
            desc_shadow_color = (0, 0, 0)
            desc_position = (120, current_y + 35)
            
            shadow, shadow_rect, desc_text, desc_rect = self.render_text_with_shadow(
                self.small_font, desc, desc_color, desc_shadow_color, desc_position, shadow_offset=(1, 1)
            )
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(desc_text, desc_rect)
            
            # Draw difficulty with shadow
            diff = stage.get("difficulty", "Unknown")
            diff_text_str = f"Difficulty: {diff}"
            diff_color = (200, 200, 200)  # Light gray
            diff_shadow_color = (0, 0, 0)
            diff_position = (120, current_y + 60)
            
            shadow, shadow_rect, diff_text, diff_rect = self.render_text_with_shadow(
                self.small_font, diff_text_str, diff_color, diff_shadow_color, diff_position, shadow_offset=(1, 1)
            )
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(diff_text, diff_rect)
            
            # Draw cleared status with shadow
            stage_key = str(actual_stage_index + 1)
            if stage_key in self.stage_logs and self.stage_logs[stage_key]["cleared"]:
                cleared_str = f"Cleared! Remaining Time: {self.stage_logs[stage_key]['remaining_time']}s"
                cleared_color = (0, 128, 0)  # Green
                cleared_shadow_color = (0, 0, 0)
                cleared_position = (self.screen.get_width() - 500, current_y + 35)
                
                shadow, shadow_rect, cleared_text, cleared_rect = self.render_text_with_shadow(
                    self.small_font, cleared_str, cleared_color, cleared_shadow_color, cleared_position, shadow_offset=(1, 1)
                )
                self.screen.blit(shadow, shadow_rect)
                self.screen.blit(cleared_text, cleared_rect)
                
                # Optional: Add a checkmark icon
                checkmark_path = os.path.join('assets', 'checkmark.png')
                if os.path.exists(checkmark_path):
                    try:
                        checkmark_img = pygame.image.load(checkmark_path).convert_alpha()
                        checkmark_img = pygame.transform.scale(checkmark_img, (30, 30))
                        checkmark_position = (self.screen.get_width() - 350, current_y + 35)
                        self.screen.blit(checkmark_img, checkmark_position)
                    except pygame.error as e:
                        print(f"Failed to load checkmark image: {e}")
            
            current_y += self.vertical_spacing  # Move to next stage position
        
        # Draw navigation instructions with shadow
        instructions = [
            "↑↓ : Select Stage",
            "ENTER : Start Game",
            "ESC : Back to Menu"
        ]
        
        instruction_y = self.screen.get_height() - 80
        for instruction in instructions:
            shadow_color = (0, 0, 0)
            text_color = (255, 255, 255)
            instr_position = (self.screen.get_width() // 2, instruction_y)
            
            shadow, shadow_rect, instr_text, instr_rect = self.render_text_with_shadow(
                self.small_font, instruction, text_color, shadow_color, instr_position, shadow_offset=(1, 1)
            )
            shadow_rect.center = instr_position
            instr_rect.center = instr_position
            
            self.screen.blit(shadow, shadow_rect)
            self.screen.blit(instr_text, instr_rect)
            
            instruction_y += 30
        
        # Draw scroll indicators with shadow
        self.draw_scroll_indicators()
    
    def draw_scroll_indicators(self):
        # Draw an up arrow if there are stages above the current view
        if self.start_stage > 0:
            up_arrow = self.small_font.render("↑", True, (255, 255, 255))
            up_shadow = self.small_font.render("↑", True, (0, 0, 0))
            up_rect = up_arrow.get_rect(center=(self.screen.get_width() // 2, self.start_y - 30))
            up_shadow_rect = up_shadow.get_rect(center=(self.screen.get_width() // 2 + 2, self.start_y - 28))
            self.screen.blit(up_shadow, up_shadow_rect)
            self.screen.blit(up_arrow, up_rect)
        
        # Draw a down arrow if there are stages below the current view
        if self.start_stage + self.visible_stage_count < len(self.stages):
            down_arrow = self.small_font.render("↓", True, (255, 255, 255))
            down_shadow = self.small_font.render("↓", True, (0, 0, 0))
            down_rect = down_arrow.get_rect(center=(self.screen.get_width() // 2, self.screen.get_height() - 30))
            down_shadow_rect = down_shadow.get_rect(center=(self.screen.get_width() // 2 + 2, self.screen.get_height() - 28))
            self.screen.blit(down_shadow, down_shadow_rect)
            self.screen.blit(down_arrow, down_rect)
