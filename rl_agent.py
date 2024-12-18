# rl_agent.py

import numpy as np
import random
import os
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import json

# Load character types from character_info.json
def load_character_types():
    try:
        with open('character_info.json', 'r') as f:
            character_info = json.load(f)
            return list(character_info.keys())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise Exception(f"Error loading character types: {e}")

# =============================
# Action Definitions
# =============================

CHARACTER_TYPES = load_character_types()
VALID_ACTIONS = ['Idle', 'Walk', 'Run', 'Attack', 'Skill']

# Updated action definitions for spawn agent
ACTION_SPAWN_FIRE_VIZARD = 0
ACTION_SPAWN_LIGHTNING_MAGE = 1
ACTION_SPAWN_WANDERER_MAGICIAN = 2
ACTION_DO_NOTHING = 3
ACTION_SPACE_SIZE = 4  # [Spawn Fire_vizard, Spawn Lightning_Mage, Spawn Wanderer_Magician, Do Nothing]

PLAYER_ACTION_SPACE_SIZE = ACTION_SPACE_SIZE
CHARACTER_ACTION_SPACE_SIZE = len(VALID_ACTIONS)

# =============================
# Common Hyperparameters
# =============================

# DQN Hyperparameters
GAMMA = 0.99         # Discount factor
EPSILON_START = 1.0  # Starting exploration rate
EPSILON_END = 0.01   # Minimum exploration rate
EPSILON_DECAY = 0.995  # Decay rate per episode
LR = 1e-4            # Learning rate for DQN
BATCH_SIZE = 64
MEMORY_SIZE = 10000
TARGET_UPDATE_FREQ = 1000  # Steps

# PPO Hyperparameters
PPO_LR = 3e-4
PPO_GAMMA = 0.99
PPO_LAMBDA = 0.95
PPO_CLIP = 0.2
PPO_EPOCHS = 5
PPO_BATCH_SIZE = 64
PPO_ENT_COEF = 0.01
PPO_VF_COEF = 0.5
PPO_MAX_GRAD_NORM = 0.5

# Device Configuration
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =============================
# Base DQN Agent
# =============================

class BaseDQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        self.memory = deque(maxlen=MEMORY_SIZE)
        self.gamma = GAMMA
        self.epsilon = EPSILON_START
        self.epsilon_min = EPSILON_END
        self.epsilon_decay = EPSILON_DECAY
        self.learning_rate = LR
        self.device = DEVICE

        # Networks
        self.policy_net = self.build_model().to(self.device)
        self.target_net = self.build_model().to(self.device)
        self.update_target_network()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        self.steps_done = 0

    def build_model(self):
        model = nn.Sequential(
            nn.Linear(self.state_size, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, self.action_size)
        )
        return model

    def update_target_network(self):
        self.target_net.load_state_dict(self.policy_net.state_dict())

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def choose_action(self, state, deterministic=True):
        self.steps_done += 1
        if not deterministic and random.random() < self.epsilon:
            return random.randrange(self.action_size)
        else:
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
            return torch.argmax(q_values).item()

    def replay(self):
        if len(self.memory) < BATCH_SIZE:
            return

        batch = random.sample(self.memory, BATCH_SIZE)
        state_batch = torch.FloatTensor(np.array([sample[0] for sample in batch])).to(self.device)
        action_batch = torch.LongTensor([sample[1] for sample in batch]).unsqueeze(1).to(self.device)
        reward_batch = torch.FloatTensor([sample[2] for sample in batch]).to(self.device)
        next_state_batch = torch.FloatTensor(np.array([sample[3] for sample in batch])).to(self.device)
        done_batch = torch.FloatTensor([sample[4] for sample in batch]).to(self.device)

        q_values = self.policy_net(state_batch).gather(1, action_batch)

        with torch.no_grad():
            next_q_values = self.target_net(next_state_batch).max(1)[0]

        expected_q_values = reward_batch + (1 - done_batch) * self.gamma * next_q_values

        loss = nn.MSELoss()(q_values.squeeze(), expected_q_values)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def decay_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self, filename):
        torch.save({
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps_done': self.steps_done
        }, filename)

    def load(self, filename):
        if os.path.exists(filename):
            checkpoint = torch.load(filename)
            self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
            self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.epsilon = checkpoint['epsilon']
            self.steps_done = checkpoint['steps_done']
            self.update_target_network()

# =============================
# AI Player Agent (DQN-based)
# =============================

class AIPlayerAgent(BaseDQNAgent):
    def __init__(self, state_size, team='left'):
        self.team = team
        super().__init__(state_size=state_size, action_size=PLAYER_ACTION_SPACE_SIZE)

    def decide_character_type(self, action):
        """
        Maps the chosen action to a character type.
        """
        if action == ACTION_SPAWN_FIRE_VIZARD:
            return CHARACTER_TYPES[0]
        elif action == ACTION_SPAWN_LIGHTNING_MAGE:
            return CHARACTER_TYPES[1]
        elif action == ACTION_SPAWN_WANDERER_MAGICIAN:
            return CHARACTER_TYPES[2]
        else:
            return None  # Do nothing

