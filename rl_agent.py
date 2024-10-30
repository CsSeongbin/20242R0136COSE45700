import numpy as np
import random
import pickle
import os
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque

# Hyperparameters
GAMMA = 0.99         # Discount factor
EPSILON_START = 1.0  # Starting exploration rate
EPSILON_END = 0.01   # Minimum exploration rate
EPSILON_DECAY = 0.995  # Decay rate per episode
LR = 1e-4            # Learning rate
BATCH_SIZE = 64
MEMORY_SIZE = 10000
TARGET_UPDATE_FREQ = 1000  # Steps
MAX_CHARACTERS = 20        # Maximum number of characters considered on the field

# Define the action space
ACTION_SPAWN = 0
ACTION_CHANGE_SLOT = 1
ACTION_DO_NOTHING = 2
ACTION_SPACE_SIZE = 3  # Total number of possible actions

# Map character types to indices
CHARACTER_TYPES = ["Fire_vizard", "Lightning_Mage", "Wanderer_Magician"]
CHARACTER_TYPE_MAPPING = {name: idx for idx, name in enumerate(CHARACTER_TYPES)}
NUM_CHARACTER_TYPES = len(CHARACTER_TYPES)

class DQNAgent:
    def __init__(self, state_size, action_size, team='left', max_slots=5):
        self.state_size = state_size
        self.action_size = action_size
        self.team = team
        self.max_slots = max_slots

        self.memory = deque(maxlen=MEMORY_SIZE)
        self.gamma = GAMMA
        self.epsilon = EPSILON_START
        self.epsilon_min = EPSILON_END
        self.epsilon_decay = EPSILON_DECAY
        self.learning_rate = LR
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Define the policy and target networks
        self.policy_net = self.build_model().to(self.device)
        self.target_net = self.build_model().to(self.device)
        self.update_target_network()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.learning_rate)
        self.steps_done = 0

    def build_model(self):
        # Define a simple feedforward neural network
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

    def choose_action(self, state):
        self.steps_done += 1
        if random.random() < self.epsilon:
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

        # Compute Q(s_t, a)
        q_values = self.policy_net(state_batch).gather(1, action_batch)

        # Compute V(s_{t+1}) for all next states.
        with torch.no_grad():
            next_q_values = self.target_net(next_state_batch).max(1)[0]

        # Compute the expected Q values
        expected_q_values = reward_batch + (1 - done_batch) * self.gamma * next_q_values

        # Compute loss
        loss = nn.MSELoss()(q_values.squeeze(), expected_q_values)

        # Optimize the model
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

    def decay_epsilon(self):
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self, filename):
        torch.save(self.policy_net.state_dict(), filename)

    def load(self, filename):
        if os.path.exists(filename):
            self.policy_net.load_state_dict(torch.load(filename))
            self.update_target_network()

