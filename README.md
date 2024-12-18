# Castle Defense Game

Castle Defense Game is a strategic and engaging tower defense game where players can face off against AI opponents, compete in multiplayer, or even join networked matches. The game includes different modes, such as VS AI, 2 Players, and Network Game.

---

## Features
- **VS AI Mode**: Battle against AI opponents of varying difficulties, trained for different stages.
- **Multiplayer Mode**: Play with a friend locally in a two-player game.
- **Network Mode**: Host or join a game over a network and battle against another player.

---

## Installation

1. Clone this repository:
    ```bash
    git clone <repository-url>
    cd 20242R0136COSE45700
    ```

2. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

---

## How to Play

### General
1. Launch the game:
    ```bash
    python game.py
    ```
2. Use the arrow keys and ENTER to navigate the menu.
3. Choose a game mode from the main menu:
    - **VS AI**: Face AI in a series of stages.
    - **2 Players**: Play with a friend locally.
    - **Network Game**: Host or join a game over a network.
    - **Quit**: Exit the game.

### VS AI Mode
1. Select "VS AI" from the main menu.
2. Use arrow keys to select a stage and press ENTER to start.
3. Spawn characters by pressing `1`, `2`, or `3`. Each key corresponds to a character type.
4. The game ends when a castle is destroyed or the timer runs out.

### 2 Players Mode
1. Select "2 Players" from the main menu.
2. Each player uses predefined keys to spawn their characters:
   - Left Player: `1`, `2`, `3`
   - Right Player: `8`, `9`, `0`
3. Compete to destroy the opponent's castle.

### Network Game Mode
#### Host a Game
1. Select "Network Game" from the main menu and choose "Host Game".
2. Share your IP address (displayed on the screen) with the joining player.
3. Wait for the player to join.
4. Once connected, the game will start automatically.

#### Join a Game
1. Select "Network Game" from the main menu and choose "Join Game".
2. Enter the host's IP address and press ENTER.
3. Once connected, the game will start automatically.

---

## Development

### Code Structure
- `game.py`: Main entry point for the game.
- `scenes/`: Contains implementations for all scenes, including home, stage select, and gameplay.
- `utils.py`: Utility functions for loading sprites and other assets.
- `rl_agent.py`: Reinforcement learning agents for AI gameplay.
- `network_manager.py`: Handles networking for multiplayer games.
- `character.py`: Logic for characters and their actions.
- `castle.py`: Logic for castles and their states.
