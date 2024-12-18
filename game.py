# game.py
import pygame
import os
from scenes.home_scene import HomeScene
from scenes.utils.logger import initialize_stage_logs

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1440, 800))  # Increased height for better UI
        pygame.display.set_caption("Castle Defense Game")
        self.clock = pygame.time.Clock()
        
        # Ensure models directory exists
        if not os.path.exists("models"):
            os.makedirs("models")
        
        # Initialize stage logs
        initialize_stage_logs(total_stages=10)
        
        # Define required AI models for 10 stages
        required_models = [
            (f"models/spawn_agent_episode_{200 * (i+1)}.pth", f"Stage {i+1}") 
            for i in range(10)
        ]
        
        missing_models = []
        for model_path, stage_name in required_models:
            if not os.path.exists(model_path):
                missing_models.append(f"{stage_name} ({model_path})")
        
        if missing_models:
            print("Warning: The following AI models are missing:")
            for model in missing_models:
                print(f"- {model}")
            print("Please ensure all required model files are present in the models directory.")
        
        self.current_scene = HomeScene(self.screen)
    
    def run(self):
        running = True
        while running:
            # Handle events
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            
            # Update current scene
            self.current_scene.handle_events(events)
            dt = self.clock.tick(60) / 1000.0
            self.current_scene.update(dt)
            
            # Draw current scene
            self.current_scene.draw()
            pygame.display.flip()
            
            # Check for scene switch
            next_scene = self.current_scene.next_scene
            if next_scene is None:
                running = False
            elif next_scene is not self.current_scene:
                # Clean up old scene if it's a network scene
                if hasattr(self.current_scene, 'clean_up'):
                    self.current_scene.clean_up()
                self.current_scene = next_scene
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()
