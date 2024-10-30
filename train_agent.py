import time
import random
import os
import json
import numpy as np
import pickle
from character import Character
from castle import Castle
from utils import load_character_sprites
from rl_agent import DQNAgent, TARGET_UPDATE_FREQ

# Action constants
ACTION_SPAWN = 0
ACTION_CHANGE_SLOT = 1
ACTION_DO_NOTHING = 2
ACTION_SPACE_SIZE = 3  # Total number of possible actions

# Screen dimensions
SCREEN_WIDTH = 1440
SCREEN_HEIGHT = 400

# Colors (used only when rendering)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)

# Character types
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magician"]
CHARACTER_TYPE_MAPPING = {name: idx for idx, name in enumerate(CHARACTER_TYPES)}
NUM_CHARACTER_TYPES = len(CHARACTER_TYPES)

# Action types for characters
ACTION_NAMES = ['Walk', 'Run', 'Attack', 'Skill', 'Idle', 'Jump', 'Dead']
ACTION_MAPPING = {name: idx for idx, name in enumerate(ACTION_NAMES)}
NUM_ACTION_TYPES = len(ACTION_NAMES)

MAX_CHARACTERS = 50  # Maximum number of characters considered on the field

# Load character info from JSON file
with open("character_info.json", "r") as file:
    character_info = json.load(file)

def map_action_name(action_name):
    action_name_lower = action_name.lower()
    if 'walk' in action_name_lower:
        return ACTION_MAPPING['Walk']
    elif 'run' in action_name_lower:
        return ACTION_MAPPING['Run']
    elif 'attack' in action_name_lower:
        return ACTION_MAPPING['Attack']
    elif 'skill' in action_name_lower:
        return ACTION_MAPPING['Skill']
    elif 'idle' in action_name_lower:
        return ACTION_MAPPING['Idle']
    elif 'jump' in action_name_lower:
        return ACTION_MAPPING['Jump']
    elif 'dead' in action_name_lower:
        return ACTION_MAPPING['Dead']
    else:
        return ACTION_MAPPING['Idle']  # Default to 'Idle'

def spawn_character(team):
    global left_team_slots, right_team_slots, characters
    if team == 'left' and left_team_slots:
        char_type = left_team_slots.pop(0)
        if render:
            sprites = loaded_sprites[char_type]['left']
            sprite_width = list(sprites.values())[0][0].get_width()
            sprite_height = list(sprites.values())[0][0].get_height()
            x = left_castle.x + left_castle.width // 2 - sprite_width // 2
            y = SCREEN_HEIGHT - sprite_height
        else:
            sprites = None
            x = left_castle.x + left_castle.width // 2
            y = SCREEN_HEIGHT  # Position is arbitrary in headless mode

        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team='left',
            character_type=char_type,
            character_info=character_info,
            time_scale=time_scale
        )
        characters.append(character)
    elif team == 'right' and right_team_slots:
        char_type = right_team_slots.pop(0)
        if render:
            sprites = loaded_sprites[char_type]['right']
            sprite_width = list(sprites.values())[0][0].get_width()
            sprite_height = list(sprites.values())[0][0].get_height()
            x = right_castle.x + right_castle.width // 2 - sprite_width // 2
            y = SCREEN_HEIGHT - sprite_height
        else:
            sprites = None
            x = right_castle.x + right_castle.width // 2
            y = SCREEN_HEIGHT  # Position is arbitrary in headless mode

        character = Character(
            sprites=sprites,
            x=x,
            y=y,
            team='right',
            character_type=char_type,
            character_info=character_info,
            time_scale=time_scale
        )
        characters.append(character)

# Initialize the agent for the left team
state_size = (
    MAX_CHARACTERS * (NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES) +  # Characters' features
    2 +  # Castle HPs
    5 * (NUM_CHARACTER_TYPES + 1) +  # Slots information (agent.max_slots is 5)
    1  # Time remaining
)
agent = DQNAgent(state_size=state_size, action_size=ACTION_SPACE_SIZE, team='left', max_slots=5)

# Hyperparameters for early stopping
MOVING_AVERAGE_WINDOW = 100  # Number of episodes to consider for moving average
CHANGE_THRESHOLD = 1e-5      # Threshold for change in moving average
PATIENCE = 10                # Number of consecutive times the change must be below threshold


# Initialize variables for early stopping
episode_rewards = []
moving_average_rewards = []
change_counter = 0  # Counts consecutive times the change is below threshold

# Variables to track the best model
best_moving_average = -float('inf')
best_model_episode = 0

wins = 0  # Initialize wins counter

# Main training loop
episode = 0  # Total number of training episodes
while True:
    episode += 1
    game_elapsed_time = 0.0  # Accumulates scaled delta_time

    # Determine if we should render this episode
    render = False  # Render every 1000 episodes
    if render:
        import pygame
        # Initialize Pygame and clock
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Episode {episode + 1}")
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill(WHITE)
        # Empty slot image
        empty_slot_image = pygame.Surface((40, 40))
        empty_slot_image.fill(GRAY)
        font = pygame.font.SysFont(None, 36)
        clock = pygame.time.Clock()  # Initialize clock for timing

        # Load all character sprites
        loaded_sprites = {}
        idle_sprites = {"left": {}, "right": {}}
        for char_type in CHARACTER_TYPES:
            loaded_sprites[char_type] = {
                'left': load_character_sprites(os.path.join('sprites', 'left', char_type)),
                'right': load_character_sprites(os.path.join('sprites', 'right', char_type))
            }
            # Load the idle images for slot display
            for team in ['left', 'right']:
                if 'Idle' in loaded_sprites[char_type][team]:
                    image = loaded_sprites[char_type][team]['Idle'][0]
                    image = pygame.transform.scale(image, (40, 40))
                    idle_sprites[team][char_type] = image
    else:
        # In headless mode, we don't need Pygame at all
        pass  # No need to load sprites or initialize Pygame

    # Set time_scale depending on render
    if render:
        time_scale = 1
        time_limit = 5 * 60  # 5 minutes
        slot_addition_interval = 5.0  # seconds
    else:
        time_scale = 50
        time_limit = 5 * 60  # 5 minutes, do not scale down
        slot_addition_interval = 5.0 / time_scale

    # Reset game state for each episode
    characters = []
    game_over = False
    winner = None

    # Create castle instances
    if render:
        left_castle = Castle(x=0, y=0, team='left', render=True)
        right_castle = Castle(x=SCREEN_WIDTH - 100, y=0, team='right', render=True)
    else:
        left_castle = Castle(x=0, y=0, team='left', render=False)
        right_castle = Castle(x=SCREEN_WIDTH - 100, y=0, team='right', render=False)
    left_castle.y = SCREEN_HEIGHT - left_castle.height
    right_castle.y = SCREEN_HEIGHT - right_castle.height

    # Initialize slots as empty lists
    left_team_slots = []
    right_team_slots = []

    slot_addition_timer = 0.0  # Accumulates delta_time for slot addition

    # Game timer
    game_start_time = time.perf_counter()

    # Initialize last_frame_time for delta_time calculation
    last_frame_time = time.perf_counter()

    total_reward = 0  # Accumulate total reward for this episode

    # Variables for detailed reward components
    enemy_units_killed = 0
    initial_left_castle_hp = left_castle.hp
    initial_right_castle_hp = right_castle.hp

    # Keep track of enemy units that have been killed
    previous_enemy_units = set()
    
    while not game_over:
        current_time = time.perf_counter()
        delta_time = current_time - last_frame_time
        last_frame_time = current_time

        if not render:
            # Accelerate time when not rendering
            delta_time *= time_scale
        # Accumulate the scaled game time
        game_elapsed_time += delta_time

        # Handle events only if rendering
        if render:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()

        # Agent's turn (for the left team)
        # Build state representation
        state_size = (
            MAX_CHARACTERS * (NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES) +
            2 +  # Castle HPs
            agent.max_slots * (NUM_CHARACTER_TYPES + 1) +
            1  # Time remaining
        )
        state = np.zeros(state_size)

        # Characters on the field
        character_features = []
        for c in characters:
            if c.hp > 0:
                # Type one-hot encoding
                type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
                type_one_hot[CHARACTER_TYPE_MAPPING[c.character_type]] = 1

                # Normalize position X (0 to 1)
                x_normalized = c.x / SCREEN_WIDTH

                # Team indicator
                team_indicator = 1 if c.team == 'left' else 0

                # Health normalized
                hp_normalized = c.hp / c.max_hp

                # Action one-hot encoding
                action_one_hot = np.zeros(NUM_ACTION_TYPES)
                action_index = map_action_name(c.current_action)
                action_one_hot[action_index] = 1

                # Character feature vector
                char_feature = np.concatenate((type_one_hot, [x_normalized, team_indicator, hp_normalized], action_one_hot))
                character_features.append(char_feature)

        # Pad or truncate to MAX_CHARACTERS
        if len(character_features) > MAX_CHARACTERS:
            character_features = character_features[:MAX_CHARACTERS]
        else:
            for _ in range(MAX_CHARACTERS - len(character_features)):
                character_features.append(np.zeros(NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES))

        # Flatten the character features to form the state vector
        character_features_flat = np.array(character_features).flatten()

        # Castle HPs normalized
        own_castle_hp_normalized = left_castle.hp / left_castle.max_hp
        enemy_castle_hp_normalized = right_castle.hp / right_castle.max_hp
        castle_features = [own_castle_hp_normalized, enemy_castle_hp_normalized]

        # Slot information
        slot_features = []
        for slot in left_team_slots:
            # Slot is filled
            slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
            slot_type_one_hot[CHARACTER_TYPE_MAPPING[slot]] = 1
            slot_filled = 1  # Slot is filled
            slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
            slot_features.append(slot_feature)

        # Pad or truncate to agent.max_slots
        for _ in range(agent.max_slots - len(slot_features)):
            # Empty slot
            slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
            slot_filled = 0
            slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
            slot_features.append(slot_feature)

        slot_features_flat = np.array(slot_features).flatten()

        # Time remaining normalized
        remaining_time = max(0, time_limit - game_elapsed_time)
        time_remaining_normalized = remaining_time / time_limit

        # Combine all features into the state vector
        state = np.concatenate([
            character_features_flat,
            castle_features,
            slot_features_flat,
            [time_remaining_normalized]
        ])

        # Choose an action
        action = agent.choose_action(state)

        # Initialize reward
        reward = 0

        # Perform the action
        if action == ACTION_SPAWN:  # Spawn character
            if left_team_slots:
                spawn_character('left')
                reward += 0  # Neutral reward for valid action
            else:
                reward += -5  # Penalty for invalid action
        elif action == ACTION_CHANGE_SLOT:  # Change slot order
            if len(left_team_slots) > 1:
                character_to_move = left_team_slots.pop(0)
                left_team_slots.append(character_to_move)
                reward += 0  # Neutral reward
            else:
                reward += -5  # Penalty for invalid action
        elif action == ACTION_DO_NOTHING:  # Do nothing
            reward += 0

        # Add one slot with a new character type every slot_addition_interval seconds if slots are available
        slot_addition_timer += delta_time
        if slot_addition_timer >= slot_addition_interval:
            slot_addition_timer -= slot_addition_interval
            if len(left_team_slots) < agent.max_slots:
                new_char = random.choice(CHARACTER_TYPES)
                left_team_slots.append(new_char)
            if len(right_team_slots) < agent.max_slots:
                new_char = random.choice(CHARACTER_TYPES)
                right_team_slots.append(new_char)

        # Right team spawns characters as fast as possible
        if right_team_slots:
            spawn_character('right')

        # Update characters
        characters_to_remove = []
        for character in characters:
            if character.is_dead_and_animation_completed() or character.has_reached_opposite_side():
                characters_to_remove.append(character)
                continue
            enemies = [c for c in characters if c.team != character.team and c.hp > 0]
            enemy_castle = right_castle if character.team == 'left' else left_castle
            character.update(enemies, enemy_castle, delta_time)  # Pass delta_time

        for character in characters_to_remove:
            characters.remove(character)

        # Calculate reward components
        # Castle health difference
        left_castle_hp_diff = initial_left_castle_hp - left_castle.hp
        right_castle_hp_diff = initial_right_castle_hp - right_castle.hp

        # Reward for minimizing damage to our castle
        castle_damage_penalty = left_castle_hp_diff / left_castle.max_hp * 50  # Scale as needed
        reward -= castle_damage_penalty

        # Reward for damaging enemy castle
        enemy_castle_damage_reward = right_castle_hp_diff / right_castle.max_hp * 50  # Scale as needed
        reward += enemy_castle_damage_reward

        # Reward for killing enemy units
        # This reward is added when enemy units are killed, already accounted for above

        # Update initial castle HPs for next step
        initial_left_castle_hp = left_castle.hp
        initial_right_castle_hp = right_castle.hp

        # Check for game over
        if left_castle.is_destroyed():
            # Penalty for losing faster
            time_penalty = (time_limit - game_elapsed_time) / time_limit * 200  # Scale as needed
            reward -= 200 + time_penalty  # Base penalty plus time penalty
            game_over = True
            winner = "Right Team Wins!"
        elif right_castle.is_destroyed():
            # Reward for winning faster
            time_bonus = (time_limit - game_elapsed_time) / time_limit * 200  # Scale as needed
            reward += 200 + time_bonus  # Base reward plus time bonus
            game_over = True
            winner = "Left Team Wins!"

        # Build next state
        # (Same as above, rebuild the state after action is taken)
        character_features = []
        for c in characters:
            if c.hp > 0:
                # Type one-hot encoding
                type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
                type_one_hot[CHARACTER_TYPE_MAPPING[c.character_type]] = 1

                # Normalize position X (0 to 1)
                x_normalized = c.x / SCREEN_WIDTH

                # Team indicator
                team_indicator = 1 if c.team == 'left' else 0

                # Health normalized
                hp_normalized = c.hp / c.max_hp

                # Action one-hot encoding
                action_one_hot = np.zeros(NUM_ACTION_TYPES)
                action_index = map_action_name(c.current_action)
                action_one_hot[action_index] = 1

                # Character feature vector
                char_feature = np.concatenate((type_one_hot, [x_normalized, team_indicator, hp_normalized], action_one_hot))
                character_features.append(char_feature)

        # Pad or truncate to MAX_CHARACTERS
        if len(character_features) > MAX_CHARACTERS:
            character_features = character_features[:MAX_CHARACTERS]
        else:
            for _ in range(MAX_CHARACTERS - len(character_features)):
                character_features.append(np.zeros(NUM_CHARACTER_TYPES + 1 + 1 + 1 + NUM_ACTION_TYPES))

        # Flatten the character features to form the next state vector
        character_features_flat = np.array(character_features).flatten()

        # Castle HPs normalized
        own_castle_hp_normalized = left_castle.hp / left_castle.max_hp
        enemy_castle_hp_normalized = right_castle.hp / right_castle.max_hp
        castle_features = [own_castle_hp_normalized, enemy_castle_hp_normalized]

        # Slot information
        slot_features = []
        for slot in left_team_slots:
            # Slot is filled
            slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
            slot_type_one_hot[CHARACTER_TYPE_MAPPING[slot]] = 1
            slot_filled = 1  # Slot is filled
            slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
            slot_features.append(slot_feature)

        # Pad or truncate to agent.max_slots
        for _ in range(agent.max_slots - len(slot_features)):
            # Empty slot
            slot_type_one_hot = np.zeros(NUM_CHARACTER_TYPES)
            slot_filled = 0
            slot_feature = np.concatenate((slot_type_one_hot, [slot_filled]))
            slot_features.append(slot_feature)

        slot_features_flat = np.array(slot_features).flatten()

        # Time remaining normalized
        remaining_time = max(0, time_limit - game_elapsed_time)
        time_remaining_normalized = remaining_time / time_limit

        # Combine all features into the next state vector
        next_state = np.concatenate([
            character_features_flat,
            castle_features,
            slot_features_flat,
            [time_remaining_normalized]
        ])

        # Remember the experience
        done = 1 if game_over else 0
        agent.remember(state, action, reward, next_state, done)

        # Replay experiences and train
        agent.replay()

        # Update target network
        if agent.steps_done % TARGET_UPDATE_FREQ == 0:
            agent.update_target_network()

        # Decay epsilon after each step
        agent.decay_epsilon()

        # Accumulate total reward for this episode
        total_reward += reward

        # Check for game over due to time limit
        if not game_over and game_elapsed_time >= time_limit:
            game_over = True
            if left_castle.hp > right_castle.hp:
                # Reward for winning faster
                time_bonus = (time_limit - game_elapsed_time) / time_limit * 100  # Less than winning before time limit
                reward += 100 + time_bonus
                winner = "Left Team Wins!"
            elif right_castle.hp > left_castle.hp:
                # Penalty for losing faster
                time_penalty = (time_limit - game_elapsed_time) / time_limit * 100  # Scale as needed
                reward -= 100 + time_penalty  # Base penalty plus time penalty
                winner = "Right Team Wins!"
            else:
                winner = "Draw!"

        # If game over, remember the final transition
        if game_over:
            agent.remember(state, action, reward, next_state, 1)
            agent.replay()
            agent.update_target_network()

        # Rendering
        if render:
            screen.fill(WHITE)
            # Render the game
            screen.blit(background, (0, 0))
            left_castle.draw(screen)
            right_castle.draw(screen)

            # Draw characters
            for character in characters:
                character.draw(screen)

            # Display slots with empty squares and idle images for each team
            slot_margin = 5

            # Left team slots (above the left castle)
            left_slot_x_start = left_castle.x  # Start at the left side of the castle
            left_slot_y = left_castle.y - 40 - 20  # 20 pixels above the castle

            for i in range(agent.max_slots):
                slot_rect = pygame.Rect(
                    left_slot_x_start + i * (40 + slot_margin),
                    left_slot_y,
                    40,
                    40
                )
                if i < len(left_team_slots):
                    # Slot is filled, display the character's idle image
                    char_type = left_team_slots[i]
                    idle_image = idle_sprites["left"][char_type]
                    screen.blit(idle_image, slot_rect)
                else:
                    # Slot is empty, display the empty slot image
                    screen.blit(empty_slot_image, slot_rect)

            # Right team slots (above the right castle)
            right_slot_x_start = right_castle.x + right_castle.width - (agent.max_slots * (40 + slot_margin) - slot_margin)
            right_slot_y = right_castle.y - 40 - 20  # 20 pixels above the castle

            for i in range(agent.max_slots):
                slot_rect = pygame.Rect(
                    right_slot_x_start + i * (40 + slot_margin),
                    right_slot_y,
                    40,
                    40
                )
                if i < len(right_team_slots):
                    # Slot is filled, display the character's idle image
                    char_type = right_team_slots[i]
                    idle_image = idle_sprites["right"][char_type]
                    screen.blit(idle_image, slot_rect)
                else:
                    # Slot is empty, display the empty slot image
                    screen.blit(empty_slot_image, slot_rect)

            # Display timer at the center of the screen
            remaining_time = max(0, time_limit - game_elapsed_time)
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            timer_text = font.render(f"Time: {minutes:02}:{seconds:02}", True, BLACK)
            screen.blit(timer_text, timer_text.get_rect(center=(SCREEN_WIDTH / 2, 20)))

            # Display winner text if game is over
            if game_over and winner:
                font_large = pygame.font.SysFont(None, 72)
                text = font_large.render(winner, True, BLACK)
                screen.blit(text, text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)))

            pygame.display.flip()
            clock.tick(60)  # Limit to 60 FPS during rendering

    # Update win count
    if winner == "Left Team Wins!":
        wins += 1
    # After the episode ends, store the total reward
    episode_rewards.append(total_reward)

    # Compute moving average reward
    if len(episode_rewards) >= MOVING_AVERAGE_WINDOW:
        recent_rewards = episode_rewards[-MOVING_AVERAGE_WINDOW:]
        moving_average = sum(recent_rewards) / MOVING_AVERAGE_WINDOW
        moving_average_rewards.append(moving_average)

        # Save best model
        if moving_average > best_moving_average:
            best_moving_average = moving_average
            best_model_episode = episode
            agent.save('models/dqn_model_best.pth')

        # Check for early stopping
        if len(moving_average_rewards) >= 2:
            change = abs(moving_average_rewards[-1] - moving_average_rewards[-2])
            if change < CHANGE_THRESHOLD:
                change_counter += 1
                if change_counter >= PATIENCE:
                    print(f"Early stopping: change in moving average reward below threshold for {PATIENCE} consecutive times.")
                    break
            else:
                change_counter = 0  # Reset counter if change is above threshold
    else:
        moving_average_rewards.append(total_reward)  # Initialize moving average rewards

    # Print progress
    print(f"Episode {episode}: Total Reward: {total_reward}, Winner: {winner}")

    # Optionally, print or log the moving average reward
    if episode % 100 == 0:
        print(f"Episode {episode}: Moving Average Reward: {moving_average_rewards[-1]:.2f}")

    # Save the model periodically
    if episode % 1000 == 999:
        agent.save(f'models/dqn_model_{episode}.pth')
    import pickle

    # Save the reward and moving average reward data
    with open(f'reward/episode_rewards_{episode}.pkl', 'wb') as f:
        pickle.dump(episode_rewards, f)

    with open(f'reward/moving_average_rewards_{episode}.pkl', 'wb') as f:
        pickle.dump(moving_average_rewards, f)

    if render:
        pygame.display.quit()
        pygame.quit()  # Clean up Pygame resources after rendering

# After training loop ends
print(f"Training completed after {episode} episodes.")
print(f"Best moving average reward: {best_moving_average:.2f} at episode {best_model_episode}")
agent.save('models/dqn_model_final.pth')