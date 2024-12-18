
import pygame
import logging
import random 
import json
import os
from typing import Optional, List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)

SCREEN_WIDTH = 1440
GRAY = (128, 128, 128)

# Define maximum time_scale to prevent game instability
MAX_TIME_SCALE = 10

def load_character_info():
    """Load character information from JSON file"""
    try:
        with open('character_info.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("character_info.json not found!")
        raise
    except json.JSONDecodeError:
        logging.error("Invalid JSON in character_info.json!")
        raise

class Character:
    def __init__(self, sprites, x: float, y: float, team: str, character_type: str, time_scale: float = 1):
        self.sprites = sprites
        self.x = x
        self.y = y
        self.team = team
        self.original_y = y
        self.character_type = character_type
        self.time_scale = min(max(time_scale, 1), MAX_TIME_SCALE)

        # Load character info
        try:
            character_info = load_character_info()
            if character_type not in character_info:
                raise ValueError(f"Invalid character type: {character_type}")
                
            char_info = character_info[character_type]
            self.max_hp = char_info['hp']
            self.hp = char_info['hp']
            self.attack_range = char_info["attack_range"]
            self.base_damage = char_info["attack_damage"]

            # Skills dictionary with timing information
            self.skills = {
                skill_name: {
                    "damage": damage,
                    "sprites": self.sprites.get(skill_name, []) if self.sprites else [],
                    "damage_frame": len(self.sprites.get(skill_name, [])) // 2 if self.sprites else 0
                }
                for skill_name, damage in char_info["skills"].items()
            }
        except Exception as e:
            logging.error(f"Error loading character info: {e}")
            raise

        # Movement attributes
        self.walk_speed = 100
        self.run_speed = 200
        self.vel_x = 0
        self.vel_y = 0

        # Combat attributes
        self.damage = self.base_damage
        self.last_attack_time = 0
        self.attack_frame_index = 0
        self.damage_cooldown = 0.5 / self.time_scale

        # Animation timing
        self.animation_speed = 0.15 
        self.attack_speed = 1.0 
        self.attack_cooldown_timer = 0.0
        self.time_since_last_frame = 0.0

        # State management
        self.valid_actions = ['Idle', 'Walk', 'Run', 'Attack', 'Skill']
        self.current_action = 'Idle' if (self.sprites and 'Idle' in self.sprites) else 'Walk'
        self.current_sprites = []
        self.sprite_index = 0
        self.previous_sprites = []
        self.previous_index = 0
        
        # Initialize current sprites
        if self.sprites:
            if self.current_action == "Attack":
                attack_key = f"{self.current_action}_{0}"
                self.current_sprites = self.sprites.get(attack_key, [])
            else:
                self.current_sprites = self.sprites.get(self.current_action, [])
            
            if not self.current_sprites:
                fallback_action = 'Idle' if 'Idle' in self.sprites else 'Walk'
                self.current_sprites = self.sprites.get(fallback_action, [])
            
            self.previous_sprites = self.current_sprites.copy()

        # Initialize as not in progress so first update will trigger action selection
        self.action_in_progress = False
        self.damage_applied = False
        self.is_dead = False
        self.dead_animation_completed = False
        self.target = None
        
        # Add explicit damage application tracking
        self.current_attack_type = None
        self.damage_already_applied = False
        self.last_attack_time = 0
        self.damage_cooldown = 0.5 / self.time_scale  # Time between attacks
        
        # Initialize attack frames more explicitly
        self.attack_damage_frames = {}
        if self.sprites:
            # For regular attacks
            for i in range(2):  # Assuming Attack_0 and Attack_1
                attack_key = f'Attack_{i}'
                if attack_key in self.sprites:
                    # Set damage frame to middle of animation
                    self.attack_damage_frames[attack_key] = len(self.sprites[attack_key]) // 2
            
            # For skills
            for skill_name in self.skills:
                if skill_name in self.sprites:
                    self.attack_damage_frames[skill_name] = len(self.sprites[skill_name]) // 2

        self.aoe_skills = {}
        if character_type == "Fire_vizard":
            self.aoe_skills["skill2"] = True  # Mark Fire_vizard's skill2 as AoE

    def get_hitbox(self):
        """Get character's hitbox for collision detection"""
        if not self.current_sprites:
            return pygame.Rect(self.x, self.y, 40, 40)
        
        sprite = self.current_sprites[self.sprite_index]
        return pygame.Rect(self.x, self.y, sprite.get_width(), sprite.get_height())
    # Add these helper functions at the start of the Character class

    def get_center_position(self):
        """Get character's center position"""
        hitbox = self.get_hitbox()
        return (hitbox.x + hitbox.width / 2, hitbox.y + hitbox.height / 2)

    def get_distance_to(self, target):
        """Calculate distance to target's center"""
        our_x, our_y = self.get_center_position()
        
        if hasattr(target, 'get_center_position'):
            target_x, target_y = target.get_center_position()
        else:
            # Handle castle case
            target_x = target.x + target.width / 2
            target_y = target.y + target.height / 2
        
        return ((target_x - our_x) ** 2 + (target_y - our_y) ** 2) ** 0.5

    def is_valid_target(self, target):
        """Check if target is valid for attacks"""
        if not target:
            return False
            
        # For characters
        if hasattr(target, 'is_dead'):
            return not target.is_dead and target.team != self.team
            
        # For castle
        if hasattr(target, 'is_destroyed'):
            return not target.is_destroyed()
            
        return False

    def check_collision(self, x, y, others):
        """Check if position would cause collision"""
        test_rect = pygame.Rect(x, y, self.get_hitbox().width, self.get_hitbox().height)
        
        for other in others:
            if other == self or not self.is_valid_target(other):
                continue
                
            other_rect = (pygame.Rect(other.x, other.y, other.width, other.height) 
                        if hasattr(other, 'width') else other.get_hitbox())
                        
            if test_rect.colliderect(other_rect):
                return True
                
        return False

    # Replace the existing update method with this simplified version
    def update(self, enemies, enemy_castle, delta_time, current_time):
        """Main update loop with simplified logic"""
        if self.hp <= 0:
            if not self.is_dead:
                self.is_dead = True
                self.vel_x = 0
                self.vel_y = 0
            self.handle_death(delta_time)
            return

        # Update animation
        self.update_animation(delta_time)
        
        # Only process actions if not dead and animation complete
        if not self.action_in_progress:
            # Find closest valid target
            valid_targets = [e for e in enemies if self.is_valid_target(e)]
            if enemy_castle and not enemy_castle.is_destroyed():
                valid_targets.append(enemy_castle)
                
            closest_target = None
            closest_dist = float('inf')
            
            for target in valid_targets:
                dist = self.get_distance_to(target)
                if ((self.team == 'left' and target.x > self.x) or 
                    (self.team == 'right' and target.x < self.x)):
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_target = target

            # Set action based on distance
            if closest_target:
                self.target = closest_target
                if closest_dist <= self.attack_range:
                    # Target in range - attack or use skill
                    if current_time - self.last_attack_time >= self.damage_cooldown:
                        self.set_action('Skill' if random.random() < 0.3 else 'Attack')
                        self.last_attack_time = current_time
                else:
                    # Move towards target
                    self.set_action('Walk' if random.random() < 0.8 else 'Run')
            else:
                # No valid targets - move forward
                self.set_action('Walk')

        # Apply movement
        if self.current_action in ['Walk', 'Run']:
            speed = self.run_speed if self.current_action == 'Run' else self.walk_speed
            new_x = self.x + (speed if self.team == 'left' else -speed) * delta_time
            
            # Check boundaries
            new_x = max(0, min(new_x, SCREEN_WIDTH - self.get_hitbox().width))
            
            # Only move if no collision
            if not self.check_collision(new_x, self.y, enemies + [enemy_castle]):
                self.x = new_x
            else:
                # Stop and prepare to attack
                self.set_action('Idle')
                
        # Handle damage application
        elif self.is_attack_or_skill_action(self.current_action):
            if (self.current_attack_type and not self.damage_already_applied and 
                self.sprite_index == self.get_damage_frame()):
                self.apply_damage_to_target()
                self.damage_already_applied = True

    # Replace the existing is_within_attack_range method with this simplified version
    def is_within_attack_range(self, target):

        """Simplified attack range check"""
        if not self.is_valid_target(target):
            return False
            
        distance = self.get_distance_to(target)
        
        # Check if target is in the correct direction
        our_x = self.get_center_position()[0]
        target_x = (target.x + target.width / 2 if hasattr(target, 'width') 
                else target.get_center_position()[0])
        
        correct_direction = ((self.team == 'left' and target_x > our_x) or
                            (self.team == 'right' and target_x < our_x))
        
        return distance <= self.attack_range and correct_direction
    
    def get_attack_box(self):
        """Get attack box for visualization purposes only"""
        hitbox = self.get_hitbox()
        character_center_x = hitbox.x + (hitbox.width / 2)
        character_center_y = hitbox.y + (hitbox.height / 2)
        
        # Create a box around the attack range circle for visualization
        if self.team == 'left':
            return pygame.Rect(character_center_x, character_center_y - self.attack_range,
                            self.attack_range, self.attack_range * 2)
        else:
            return pygame.Rect(character_center_x - self.attack_range, character_center_y - self.attack_range,
                            self.attack_range, self.attack_range * 2)
    
    def is_within_attack_range(self, target):
        """Check if target is within attack range using center-to-center distance"""
        if not target:
            return False
        
        # Get our center position
        hitbox = self.get_hitbox()
        our_center_x = hitbox.x + (hitbox.width / 2)
        our_center_y = hitbox.y + (hitbox.height / 2)
        
        # Get target's center position
        target_box = (
            pygame.Rect(target.x, target.y, target.width, target.height)
            if hasattr(target, 'width') else target.get_hitbox()
        )
        target_center_x = target_box.x + (target_box.width / 2)
        target_center_y = target_box.y + (target_box.height / 2)
        
        # Calculate actual center-to-center distance
        distance = ((target_center_x - our_center_x) ** 2 + 
                    (target_center_y - our_center_y) ** 2) ** 0.5
        
        # Check if target is in the correct direction
        if self.team == 'left':
            correct_direction = target_center_x > our_center_x
        else:
            correct_direction = target_center_x < our_center_x
        
        # Add debug logging
        print(f"{self.team} character at {our_center_x:.1f} checking target at {target_center_x:.1f}, "
            f"distance: {distance:.1f}, range: {self.attack_range}, in range: {distance <= self.attack_range}")
        
        return distance <= self.attack_range and correct_direction
    
    def is_attack_or_skill_action(self, action_name):
        if action_name in self.skills:
            return True
        action_lower = action_name.lower()
        return 'attack' in action_lower or 'skill' in action_lower

    def is_blocked_ahead(self, enemies, enemy_castle):
        """Check if there are any obstacles ahead of the character."""
        if not self.current_sprites:
            return False
            
        # Calculate the position where the character wants to move
        move_direction = 1 if self.team == 'left' else -1
        next_x = self.x + (self.vel_x * 0.016)  # Approximate next position
        
        # Get next hitbox
        next_hitbox = self.get_hitbox()
        next_hitbox.x = next_x
        
        # Check collision with enemies
        for enemy in enemies:
            if enemy == self.target or enemy.hp <= 0:
                continue
                
            if next_hitbox.colliderect(enemy.get_hitbox()):
                return True
        
        # Check collision with enemy castle
        if enemy_castle and enemy_castle != self.target:
            castle_rect = pygame.Rect(enemy_castle.x, enemy_castle.y,
                                    enemy_castle.width,
                                    enemy_castle.height)
            if next_hitbox.colliderect(castle_rect):
                return True
        
        return False
    
    def has_reached_opposite_side(self):
        """Check if character has reached the enemy castle"""
        if self.team == 'left':
            return self.x >= SCREEN_WIDTH - 150  # Adjusted to stop before castle
        else:
            return self.x <= 150  # Adjusted to stop before castle

    def apply_action(self, enemies, enemy_castle, scaled_delta_time):
        """Enhanced apply_action with improved combat positioning and AoE mechanics"""
        if self.is_dead:
            return
            
        # Store original position
        old_x = self.x
        old_y = self.y

        # Reset velocity
        self.vel_x = 0
        
        # Update attack cooldown
        if self.attack_cooldown_timer > 0:
            self.attack_cooldown_timer -= scaled_delta_time

        action_lower = self.current_action.lower()

        # Clear invalid targets
        if self.target:
            if hasattr(self.target, 'is_dead') and self.target.is_dead:
                self.target = None
            elif hasattr(self.target, 'is_destroyed') and self.target.is_destroyed():
                self.target = None

        # Enhanced target selection considering AoE potential
        if self.character_type == "Fire_vizard" and not self.target:
            best_target = None
            max_targets_hit = 0
            
            # Check each potential target for AoE value
            for potential_target in enemies:
                if not self.is_valid_target(potential_target):
                    continue
                    
                # Count how many enemies would be hit if we target this one
                targets_hit = 1  # Count the target itself
                target_x = (potential_target.x + potential_target.width/2 
                        if hasattr(potential_target, 'width') 
                        else potential_target.get_center_position()[0])
                
                # Check other enemies within AoE range
                for other in enemies:
                    if other == potential_target or not self.is_valid_target(other):
                        continue
                        
                    other_x = (other.x + other.width/2 
                            if hasattr(other, 'width') 
                            else other.get_center_position()[0])
                    
                    # Assume AoE radius is 1.5x normal attack range
                    if abs(other_x - target_x) <= self.attack_range * 1.5:
                        targets_hit += 1
                
                # Update best target if this one would hit more enemies
                if targets_hit > max_targets_hit:
                    max_targets_hit = targets_hit
                    best_target = potential_target
            
            if best_target:
                self.target = best_target

        # Improved movement and positioning logic
        if self.target:
            distance_to_target = self.get_distance_to(self.target)
            optimal_range = self.attack_range * 0.8  # Stay at 80% of max range
            
            if action_lower.startswith(('walk', 'run')):
                # Move towards optimal range
                if distance_to_target > self.attack_range:
                    # Move closer
                    speed = self.run_speed if action_lower.startswith('run') else self.walk_speed
                    self.vel_x = speed if self.team == 'left' else -speed
                elif distance_to_target < optimal_range:
                    # Back up a bit
                    speed = self.walk_speed
                    self.vel_x = -speed if self.team == 'left' else speed
                else:
                    # In optimal range - prepare to attack
                    self.vel_x = 0
                    if self.character_type == "Fire_vizard" and max_targets_hit > 1:
                        self.set_action('skill2')  # Use AoE skill when multiple targets available
                    else:
                        self.set_action('Attack')
        else:
            # No target - move forward
            if action_lower.startswith('walk'):
                speed = self.walk_speed
                self.vel_x = speed if self.team == 'left' else -speed
            elif action_lower.startswith('run'):
                speed = self.run_speed
                self.vel_x = speed if self.team == 'left' else -speed
        
        # Check for collisions before applying movement
        if self.vel_x != 0:
            new_x = self.x + self.vel_x * scaled_delta_time
            
            # Only stop if collision is with non-target
            collision_with_non_target = False
            test_rect = pygame.Rect(new_x, self.y, self.get_hitbox().width, self.get_hitbox().height)
            
            for other in enemies + [enemy_castle]:
                if other == self.target:
                    continue
                    
                other_rect = (pygame.Rect(other.x, other.y, other.width, other.height) 
                            if hasattr(other, 'width') else other.get_hitbox())
                
                if test_rect.colliderect(other_rect):
                    collision_with_non_target = True
                    break
            
            if not collision_with_non_target:
                self.x = max(0, min(new_x, SCREEN_WIDTH - self.get_hitbox().width))
            else:
                self.x = old_x
                if action_lower.startswith(('walk', 'run')):
                    self.set_action('Idle')

        # Enhanced AoE damage application
        if (self.is_attack_or_skill_action(self.current_action) and 
            self.sprite_index == self.get_damage_frame() and 
            not self.damage_already_applied):
            
            if self.character_type == "Fire_vizard" and self.current_action == "skill2":
                # Apply AoE damage
                attack_center_x = self.x + (self.attack_range if self.team == 'left' else -self.attack_range)
                aoe_range = self.attack_range * 1.5
                
                for target in enemies + [enemy_castle]:
                    if not self.is_valid_target(target):
                        continue
                        
                    target_x = (target.x + target.width/2 
                            if hasattr(target, 'width') 
                            else target.get_center_position()[0])
                    
                    if abs(target_x - attack_center_x) <= aoe_range:
                        # Apply AoE damage to all targets in range
                        damage = self.skills["skill2"]["damage"]
                        target.take_damage(damage)
                
                self.damage_already_applied = True
            else:
                # Normal single-target damage
                if self.target and self.is_within_attack_range(self.target):
                    if self.current_action.startswith('skill'):
                        damage = self.skills[self.current_action]["damage"]
                    else:
                        damage = self.damage
                    self.target.take_damage(damage)
                    self.damage_already_applied = True

    def detect_enemy_or_castle(self, enemies, enemy_castle):
        """Detect nearby enemies or castle within attack range."""
        enemy_in_range = None
        forward_enemies = [e for e in enemies if e.team != self.team and e.hp > 0]
        
        # Sort enemies by distance
        forward_enemies.sort(key=lambda e: abs(self.x - e.x))

        # Check for enemies in attack range
        for enemy in forward_enemies:
            if ((self.team == 'left' and enemy.x >= self.x) or
                (self.team == 'right' and enemy.x <= self.x)):
                if self.is_within_attack_range(enemy):
                    enemy_in_range = enemy
                    break

        # Check castle only if no enemies are in range
        castle_in_range = None
        if not enemy_in_range:  # Only check castle if no enemies are in range
            if enemy_castle:
                castle_x = enemy_castle.x
                if ((self.team == 'left' and castle_x >= self.x) or
                    (self.team == 'right' and castle_x <= self.x)):
                    if self.is_within_attack_range(enemy_castle):
                        castle_in_range = enemy_castle

        return enemy_in_range, castle_in_range

    def get_damage_frame(self) -> int:
        """Get the frame at which damage should be applied for current attack"""
        if not self.current_attack_type:
            return 0
            
        if self.current_attack_type.startswith('Attack'):
            return len(self.sprites.get(self.current_attack_type, [])) // 2
        elif self.current_attack_type in self.skills:
            return len(self.sprites.get(self.current_attack_type, [])) // 2
        return 0

    def update_animation(self, delta_time: float) -> None:
        """Update animation frames"""
        if not self.current_sprites:
            self.action_in_progress = False
            return
            
        self.time_since_last_frame += delta_time
        if self.time_since_last_frame >= self.animation_speed:
            self.time_since_last_frame = 0.0
            
            self.previous_index = self.sprite_index
            next_index = (self.sprite_index + 1) % len(self.current_sprites)
            
            # If animation completes, reset attack states
            if next_index == 0:
                if self.is_attack_or_skill_action(self.current_action):
                    self.action_in_progress = False
                    self.current_attack_type = None
                    self.damage_already_applied = False
                else:
                    self.action_in_progress = False
            
            self.sprite_index = next_index

    def set_action(self, action_name: str) -> None:
        """Set character action with single-damage tracking"""
        if action_name not in self.valid_actions and action_name != 'Dead':
            action_name = 'Walk'

        self.previous_sprites = self.current_sprites
        self.previous_index = self.sprite_index
        self.current_action = action_name
        
        if self.sprites:
            if action_name == "Attack":
                attack_num = random.randint(0, 1)
                self.current_attack_type = f"Attack_{attack_num}"
                self.current_sprites = self.sprites.get(self.current_attack_type, [])
            elif action_name == "Skill":
                skill_name = f"skill{random.randint(1, 2)}"
                self.current_attack_type = skill_name
                self.current_sprites = self.sprites.get(skill_name, [])
            else:
                self.current_attack_type = None
                self.current_sprites = self.sprites.get(action_name, [])
                
            if not self.current_sprites:
                self.current_sprites = self.sprites.get('Walk', [])
            
            self.sprite_index = 0
            self.damage_already_applied = False  # Reset damage tracking for new action

        self.time_since_last_frame = 0.0
        self.action_in_progress = True

    def handle_death(self, delta_time):
        if not self.dead_animation_completed:
            if self.current_action != 'Dead' and self.sprites and 'Dead' in self.sprites:
                self.set_action('Dead')
            else:
                self.dead_animation_completed = True

            if not self.dead_animation_completed:
                self.time_since_last_frame += delta_time
                if self.time_since_last_frame >= self.animation_speed and self.current_sprites:
                    self.time_since_last_frame = 0.0
                    self.sprite_index += 1
                    if self.sprite_index >= len(self.current_sprites):
                        self.dead_animation_completed = True

    def apply_damage_to_target(self) -> None:
        """Apply damage once per attack"""
        if not self.current_attack_type or not self.target or self.damage_already_applied:
            return

        # Calculate damage amount
        damage_amount = self.damage  # Default to base damage
        if self.current_attack_type in self.skills:
            damage_amount = self.skills[self.current_attack_type]['damage']

        # Check if current attack/skill is AoE
        is_aoe = self.current_attack_type in self.aoe_skills
        attack_box = self.get_attack_box()

        if is_aoe:
            # Handle AoE damage
            if hasattr(self, '_all_characters'):
                for potential_target in self._all_characters:
                    if (potential_target != self and 
                        potential_target.team != self.team and 
                        potential_target.hp > 0):
                        
                        target_box = potential_target.get_hitbox()
                        if attack_box.colliderect(target_box):
                            potential_target.take_damage(damage_amount)
            
            # Check castle for AoE
            if hasattr(self.target, 'width'):  # Castle check
                castle_box = pygame.Rect(self.target.x, self.target.y,
                                      self.target.width, self.target.height)
                if attack_box.colliderect(castle_box):
                    self.target.take_damage(damage_amount)
        else:
            # Single target damage
            target_box = (pygame.Rect(self.target.x, self.target.y, 
                                    self.target.width, self.target.height)
                         if hasattr(self.target, 'width')
                         else self.target.get_hitbox())
            
            if attack_box.colliderect(target_box):
                self.target.take_damage(damage_amount)

        self.damage_already_applied = True  # Mark damage as applied for this attack
        
    def is_dead_and_animation_completed(self):
        return self.hp <= 0 and self.dead_animation_completed

    def take_damage(self, amount: float) -> None:
        """Improved damage receiving with interruption of walking"""
        old_hp = self.hp
        self.hp = max(0, self.hp - amount)
        # print(f"{self.character_type} took {amount} damage. HP: {old_hp} -> {self.hp}")
        
        # When taking damage, interrupt walking animations
        if self.current_action.lower().startswith('walk'):
            self.set_action('Idle')
            self.vel_x = 0
        
        if self.hp <= 0 and not self.is_dead:
            self.is_dead = True
            # print(f"{self.character_type} has been defeated!")
            
    def draw(self, surface, camera_offset=0):
        """Draw the character with proper sprite handling"""
        if self.dead_animation_completed:
            return
            
        sprites_to_use = self.current_sprites if self.current_sprites else self.previous_sprites
        index_to_use = min(self.sprite_index, len(sprites_to_use) - 1) if sprites_to_use else 0
        
        if sprites_to_use and 0 <= index_to_use < len(sprites_to_use):
            sprite = sprites_to_use[index_to_use]
            draw_x = self.x - camera_offset
            draw_y = self.y
            surface.blit(sprite, (draw_x, draw_y))
            
            # Draw HP bar
            if self.hp > 0:
                bar_width = 50
                bar_height = 5
                hp_ratio = self.hp / self.max_hp
                bar_x = draw_x + (sprite.get_width() - bar_width) / 2
                bar_y = draw_y - bar_height - 5
                pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, bar_height))
                hp_color = (255 * (1 - hp_ratio), 255 * hp_ratio, 0)
                pygame.draw.rect(surface, hp_color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))