import pygame
import random

SCREEN_WIDTH = 1440
GRAY = (128, 128, 128)

class Character:
    def __init__(self, sprites, x, y, team, character_type, character_info, time_scale=1):
        self.sprites = sprites  # This could be None in headless mode
        self.x = x
        self.y = y
        self.team = team
        self.character_type = character_type
        self.original_y = y

        # Load character-specific info from character_info
        char_info = character_info[character_type]
        self.max_hp = char_info['hp']
        self.hp = char_info['hp']
        self.attack_range = char_info["attack_range"]
        self.base_damage = char_info["attack_damage"]
        self.skills = {
            skill_name: {
                "damage": damage,
                "sprites": self.sprites.get(skill_name, []) if self.sprites else []
            }
            for skill_name, damage in char_info["skills"].items()
        }

        # Set default damage to base_damage from character_info
        self.damage = self.base_damage  

        # Movement and action parameters
        self.walk_speed = 100 * time_scale  # Pixels per second
        self.run_speed = 200 * time_scale   # Pixels per second
        self.jump_speed = 100 * time_scale  # Pixels per second

        # Animation and timing
        self.animation_speed = (0.1 / time_scale)  # Time per frame in seconds

        # Attack timing
        self.attack_speed = (1.0 / time_scale)  # Time between attacks in seconds

        # Animation and timing
        self.current_action = random.choice(self.get_movement_actions())
        self.current_sprites = self.sprites[self.current_action] if self.sprites else []
        self.sprite_index = 0
        self.time_since_last_frame = 0
        self.action_in_progress = True
        self.damage_applied = False
        self.dead_animation_completed = False
        self.is_jumping = False
        self.target = None

    def get_movement_actions(self):
        if self.sprites:
            return [action for action in self.sprites if any(name in action.lower() for name in ['walk'])]
        else:
            return ['walk']  # Default movement action in headless mode

    def get_attack_actions(self):
        if self.sprites:
            return [action for action in self.sprites if any(name in action.lower() for name in ['attack', 'skill', 'jump'])]
        else:
            return ['attack']  # Default attack action in headless mode

    def get_attack_actions_no_jump(self):
        if self.sprites:
            return [action for action in self.get_attack_actions() if not action.lower().startswith('jump')]
        else:
            return ['attack']  # Default attack action in headless mode

    def is_within_attack_range(self, target):
        distance = abs(self.x - target.x)
        return distance <= self.attack_range

    def has_reached_opposite_side(self):
        return (self.team == 'left' and self.x >= SCREEN_WIDTH) or (self.team == 'right' and self.x <= 0)

    def update(self, enemies, enemy_castle, delta_time):
        if self.hp <= 0:
            self.handle_death(delta_time)
            return

        enemy_in_range, castle_in_range = self.detect_enemy_or_castle(enemies, enemy_castle)

        if (enemy_in_range or castle_in_range) and not self.action_in_progress:
            self.initiate_attack(enemy_in_range, castle_in_range)

        # Animation timing
        self.time_since_last_frame += delta_time
        if self.time_since_last_frame >= self.animation_speed:
            self.time_since_last_frame = 0
            if self.current_sprites:
                self.sprite_index += 1
                if self.sprite_index >= len(self.current_sprites):
                    self.sprite_index = 0
                    self.action_in_progress = False

                    # Apply damage after attack animation completes
                    if self.current_action in self.get_attack_actions() and not self.damage_applied:
                        if self.target:
                            self.target.take_damage(self.damage)
                            self.attack_cooldown = self.attack_speed  # Reset attack cooldown
                        self.damage_applied = True
                        self.target = None

                    if self.current_action.lower().startswith('jump'):
                        self.y = self.original_y
                        self.is_jumping = False
            else:
                # No sprites, so we consider the action completed after one "frame"
                self.action_in_progress = False
                self.damage_applied = False

                # Apply damage
                if self.current_action in self.get_attack_actions() and not self.damage_applied:
                    if self.target:
                        self.target.take_damage(self.damage)
                        self.attack_cooldown = self.attack_speed  # Reset attack cooldown
                    self.damage_applied = True
                    self.target = None

                if self.current_action.lower().startswith('jump'):
                    self.y = self.original_y
                    self.is_jumping = False

        if not self.action_in_progress and not (enemy_in_range or castle_in_range):
            self.select_movement_action()

        self.move(delta_time, enemy_castle)

        # Ensure y position is reset after jump if action is completed
        if not self.action_in_progress and self.current_action.lower().startswith('jump'):
            self.y = self.original_y
            self.is_jumping = False

    def move(self, delta_time, enemy_castle):
        if self.current_action.lower().startswith('walk'):
            self.move_forward(speed=self.walk_speed, delta_time=delta_time)
        elif self.current_action.lower().startswith('run'):
            self.move_forward(speed=self.run_speed, delta_time=delta_time)
        elif self.current_action.lower().startswith('jump'):
            self.jump_over_enemy(delta_time, enemy_castle)

    def move_forward(self, speed, delta_time):
        distance = speed * delta_time
        self.x += distance if self.team == 'left' else -distance

    def jump_over_enemy(self, delta_time, enemy_castle):
        jump_height = 50
        jump_distance = 250
        displacement_to_castle = abs(self.x - enemy_castle.x)

        # Check if jump distance exceeds displacement to castle
        if jump_distance > displacement_to_castle:
            # Prevent jump by switching to a non-jump movement action
            self.select_movement_action()
            return

        # Calculate the total duration of the jump based on animation frames
        if self.current_sprites:
            jump_duration = len(self.current_sprites) * self.animation_speed
        else:
            jump_duration = self.animation_speed  # Assume at least one frame

        # Calculate the amount of horizontal movement per second
        speed = self.jump_speed

        # Move x position incrementally
        distance = speed * delta_time
        self.x += distance if self.team == 'left' else -distance

        # Update y position to create the arc
        time_in_animation = self.sprite_index * self.animation_speed + self.time_since_last_frame
        frame_ratio = time_in_animation / jump_duration if jump_duration > 0 else 0
        frame_ratio = min(max(frame_ratio, 0), 1)  # Clamp frame_ratio between 0 and 1

        if frame_ratio <= 0.5:
            self.y = self.original_y - (jump_height * (2 * frame_ratio))
        else:
            self.y = self.original_y - (jump_height * (2 * (1 - frame_ratio)))

        if self.y > self.original_y:
            self.y = self.original_y

    def detect_enemy_or_castle(self, enemies, enemy_castle):
        enemy_in_range = None
        proximity_threshold = self.attack_range * 1.5

        # Filter enemies within proximity threshold and in front of the character
        potential_enemies = [
            enemy for enemy in enemies
            if enemy.team != self.team
            and enemy.hp > 0
            and not enemy.is_jumping
            and abs(self.x - enemy.x) <= proximity_threshold
            and (
                (self.team == 'left' and enemy.x >= self.x) or
                (self.team == 'right' and enemy.x <= self.x)
            )
        ]

        # Check for enemies in attack range
        for enemy in potential_enemies:
            if self.is_within_attack_range(enemy):
                enemy_in_range = enemy
                break

        # Check if the castle is in front and within attack range
        castle_in_range = None
        if (
            (self.team == 'left' and enemy_castle.x >= self.x) or
            (self.team == 'right' and enemy_castle.x <= self.x)
        ) and self.is_within_attack_range(enemy_castle):
            castle_in_range = enemy_castle

        return enemy_in_range, castle_in_range

    def initiate_attack(self, enemy_in_range, castle_in_range):
        if self.skills and random.random() < 0.1:
            # Use a skill with a 10% chance
            selected_skill = random.choice(list(self.skills.keys()))
            self.current_action = selected_skill
            self.current_sprites = self.skills[selected_skill]["sprites"]
            self.damage = self.skills[selected_skill]["damage"]
        else:
            # Use a basic attack
            available_attack_actions = self.get_attack_actions_no_jump() if castle_in_range else self.get_attack_actions()
            if available_attack_actions:
                self.current_action = random.choice(available_attack_actions)
                if self.sprites:
                    self.current_sprites = self.sprites.get(self.current_action, [])
                else:
                    self.current_sprites = []
                self.damage = self.base_damage  # Set damage to the character's base attack damage
            else:
                # No attack actions available; default to 'attack'
                self.current_action = 'attack'
                self.current_sprites = []
                self.damage = self.base_damage
        self.sprite_index = 0
        self.action_in_progress = True
        self.damage_applied = False
        self.time_since_last_frame = 0
        self.target = enemy_in_range if enemy_in_range else castle_in_range
        self.is_jumping = self.current_action.lower().startswith('jump')

    def select_movement_action(self):
        movement_actions = self.get_movement_actions()
        if movement_actions:
            self.current_action = random.choice(movement_actions)
            if self.sprites:
                self.current_sprites = self.sprites.get(self.current_action, [])
            else:
                self.current_sprites = []
        else:
            self.current_action = 'walk'  # Default movement action
            self.current_sprites = []
        self.sprite_index = 0
        self.action_in_progress = True
        self.time_since_last_frame = 0

    def handle_death(self, delta_time):
        if not self.dead_animation_completed:
            if self.current_action != 'Dead' and self.sprites and 'Dead' in self.sprites:
                self.current_action = 'Dead'
                self.current_sprites = self.sprites[self.current_action]
                self.sprite_index = 0
                self.action_in_progress = True
                self.time_since_last_frame = 0
            else:
                # No death animation; mark as completed
                self.dead_animation_completed = True

            # Animation timing
            self.time_since_last_frame += delta_time
            if self.time_since_last_frame >= self.animation_speed and self.current_sprites:
                self.time_since_last_frame = 0
                self.sprite_index += 1
                if self.sprite_index >= len(self.current_sprites):
                    self.dead_animation_completed = True

    def switch_to_idle(self):
        if self.hp > 0 and self.current_action != 'Idle' and self.sprites and 'Idle' in self.sprites:
            self.current_action = 'Idle'
            self.current_sprites = self.sprites[self.current_action]
            self.sprite_index = 0
            self.action_in_progress = True
            self.time_since_last_frame = 0

    def draw(self, surface):
        if self.dead_animation_completed:
            return
        if self.sprites and self.current_sprites:
            sprite = self.current_sprites[self.sprite_index]
            surface.blit(sprite, (self.x, self.y))

            if self.hp > 0:
                bar_width = 50
                bar_height = 5
                hp_ratio = self.hp / self.max_hp
                bar_x = self.x + (sprite.get_width() - bar_width) / 2
                bar_y = self.y - bar_height - 5
                pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, bar_height))
                hp_color = (255 * (1 - hp_ratio), 255 * hp_ratio, 0)
                pygame.draw.rect(surface, hp_color, (bar_x, bar_y, bar_width * hp_ratio, bar_height))
        else:
            # In headless mode, no need to draw
            pass

    def is_dead_and_animation_completed(self):
        return self.dead_animation_completed

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
