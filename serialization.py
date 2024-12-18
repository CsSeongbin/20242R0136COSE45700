# serialization.py
import logging
import pickle
import zlib
from typing import Dict, List, Any, Optional
from character import Character
from castle import Castle
import msgpack

class GameStateSerializer:
    @staticmethod
    def serialize_character(character: Character) -> Dict:
        """Convert a Character object to a serializable dictionary, excluding sprite data"""
        return {
            'x': character.x,
            'y': character.y,
            'team': character.team,
            'character_type': character.character_type,
            'hp': character.hp,
            'max_hp': character.max_hp,
            'current_action': character.current_action,
            'is_dead': character.is_dead,
            'sprite_index': character.sprite_index,
            'vel_x': character.vel_x if hasattr(character, 'vel_x') else 0,
            'vel_y': character.vel_y if hasattr(character, 'vel_y') else 0,
            'action_in_progress': character.action_in_progress if hasattr(character, 'action_in_progress') else False,
            'time_scale': character.time_scale if hasattr(character, 'time_scale') else 1.0
        }

    @staticmethod
    def deserialize_character(data: Dict, loaded_sprites: Dict) -> Character:
        """Create a Character object from serialized data, reusing existing sprites"""
        sprites = loaded_sprites[data['character_type']][data['team']]
        char = Character(
            sprites=sprites,
            x=data['x'],
            y=data['y'],
            team=data['team'],
            character_type=data['character_type'],
            time_scale=data.get('time_scale', 1.0)
        )
        
        # Update state
        char.hp = data['hp']
        char.max_hp = data['max_hp']
        char.current_action = data['current_action']
        char.is_dead = data['is_dead']
        char.sprite_index = data['sprite_index']
        char.vel_x = data.get('vel_x', 0)
        char.vel_y = data.get('vel_y', 0)
        char.action_in_progress = data.get('action_in_progress', False)
        return char

    @staticmethod
    def serialize_castle(castle: Castle) -> Dict:
        """Convert a Castle object to a serializable dictionary, excluding sprite data"""
        return {
            'x': castle.x,
            'y': castle.y,
            'team': castle.team,
            'hp': castle.hp,
            'max_hp': castle.max_hp,
            'width': castle.width,
            'height': castle.height,
            'full_hp_threshold': castle.full_hp_threshold,
            'destroyed_threshold': castle.destroyed_threshold
        }

    @staticmethod
    def serialize_game_state(game_state: Dict) -> bytes:
        """Serialize the game state using MessagePack"""
        serialized = {
            'characters': [GameStateSerializer.serialize_character(c) 
                          for c in game_state['characters']],
            'left_castle': GameStateSerializer.serialize_castle(game_state['left_castle']),
            'right_castle': GameStateSerializer.serialize_castle(game_state['right_castle']),
            'left_gage': game_state['left_gage'],
            'right_gage': game_state['right_gage'],
            'elapsed_time': game_state['elapsed_time'],
            'time_limit': game_state.get('time_limit', 180),
            'game_over': game_state.get('game_over', False),
            'winner': game_state.get('winner', None),
            'camera_offset': game_state.get('camera_offset', 0)
        }
        return msgpack.packb(serialized, use_bin_type=True)
    
    @staticmethod
    def deserialize_game_state(data: bytes, loaded_sprites: Dict) -> Dict:
        """Deserialize the game state using MessagePack"""
        try:
            unpacked = msgpack.unpackb(data, raw=False)
            game_state = {
                'characters': [GameStateSerializer.deserialize_character(c, loaded_sprites) 
                             for c in unpacked['characters']],
                'left_castle': GameStateSerializer.deserialize_castle(unpacked['left_castle']),
                'right_castle': GameStateSerializer.deserialize_castle(unpacked['right_castle']),
                'left_gage': unpacked['left_gage'],
                'right_gage': unpacked['right_gage'],
                'elapsed_time': unpacked['elapsed_time'],
                'time_limit': unpacked.get('time_limit', 180),
                'game_over': unpacked.get('game_over', False),
                'winner': unpacked.get('winner', None),
                'camera_offset': unpacked.get('camera_offset', 0),
                'loaded_sprites': loaded_sprites  # Preserve loaded sprites
            }
            
            # Update castle states
            game_state['left_castle'].hp = unpacked['left_castle']['hp']
            game_state['right_castle'].hp = unpacked['right_castle']['hp']
            
            logging.debug("Deserialized game state successfully with MessagePack.")
            return game_state
        except Exception as e:
            logging.error(f"Error deserializing game state: {e}")
            return {}

    @staticmethod
    def deserialize_castle(data: Dict) -> Castle:
        """Deserialize castle data"""
        castle = Castle(x=data['x'], y=data['y'], team=data['team'])
        castle.hp = data['hp']
        castle.max_hp = data['max_hp']
        castle.width = data['width']
        castle.height = data['height']
        castle.full_hp_threshold = data['full_hp_threshold']
        castle.destroyed_threshold = data['destroyed_threshold']
        return castle