# network_manager.py

import socket
import pickle
import threading
import queue
import time
import zlib
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from serialization import GameStateSerializer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class NetworkMessage:
    type: str
    data: Any
    timestamp: float = 0.0
    sequence_number: int = 0

class NetworkManager:
    def __init__(self, is_host: bool = False):
        self.is_host = is_host
        self.socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        self.message_queue = queue.Queue()
        self.receive_queue = queue.Queue()
        
        # State management
        self.last_game_state: Optional[Dict] = None
        self.last_send_time = 0
        self.STATE_UPDATE_INTERVAL = 1/15  # Increased to 60 Hz
        
        # Sequence numbers for reliable ordering
        self.send_sequence = 0
        self.receive_sequence = 0
        
        # Message acknowledgment
        self.pending_acks = {}
        self.ack_timeout = 0.1  # 100ms timeout
        self.max_retries = 3
        
        # State compression
        self.last_full_state: Optional[Dict] = None
        self.state_send_counter = 0
        self.FULL_STATE_INTERVAL = 60  # Send full state every 60 frames
        
        # RTT measurement
        self.rtt_samples = []
        self.average_rtt = 0.0
        self.MAX_RTT_SAMPLES = 10

    def _measure_rtt(self, send_time: float) -> None:
        """Update RTT measurements"""
        rtt = time.time() - send_time
        self.rtt_samples.append(rtt)
        if len(self.rtt_samples) > self.MAX_RTT_SAMPLES:
            self.rtt_samples.pop(0)
        self.average_rtt = sum(self.rtt_samples) / len(self.rtt_samples)

    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using zlib"""
        return zlib.compress(data, level=6)

    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress zlib compressed data"""
        return zlib.decompress(data)

    def _calculate_state_delta(self, current_state: Dict) -> Dict:
        """Calculate delta between current and last state"""
        if not self.last_full_state:
            return current_state
            
        delta = {}
        for key, value in current_state.items():
            if key not in self.last_full_state or self.last_full_state[key] != value:
                delta[key] = value
        return delta

    def start_server(self, port: int = 5555) -> bool:
        """Start the game server with improved error handling"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', port))
            self.socket.settimeout(1.0)  # 1 second timeout for accept
            self.socket.listen(1)
            self.running = True
            
            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
            logging.info(f"Server started on port {port}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
            return False

    def connect_to_server(self, host: str, port: int = 5555) -> bool:
        """Connect to game server with timeout and retry"""
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(5.0)  # 5 second timeout for connection
                self.socket.connect((host, port))
                self.socket.settimeout(None)  # Reset timeout for normal operation
                self.connected = True
                self.running = True
                
                # Start receive thread
                receive_thread = threading.Thread(target=self._receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                logging.info(f"Connected to server at {host}:{port}")
                return True
                
            except Exception as e:
                logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                
        logging.error("Failed to connect after all retries")
        return False

    def request_retransmission(self, missing_sequence_number: int):
        """Request retransmission of a specific message"""
        try:
            self.send_message("retransmit_request", missing_sequence_number)
            logging.info(f"Requested retransmission for sequence {missing_sequence_number}")
        except Exception as e:
            logging.error(f"Error requesting retransmission: {e}")

    def send_game_state(self, game_state: Dict):
        """Send the full game state to the client without additional compression"""
        if not self.is_host or not self.connected:
            return
            
        current_time = time.time()
        if current_time - self.last_send_time >= self.STATE_UPDATE_INTERVAL:
            try:
                # Serialize full game state
                serialized_state = GameStateSerializer.serialize_game_state(game_state)
                
                # Send the serialized game state without additional compression
                self.send_message("game_state", serialized_state)
                self.last_send_time = current_time
                
                logging.info("Sent full game state to client.")
                
            except Exception as e:
                logging.error(f"Failed to send game state: {str(e)}")
                self.connected = False

    def send_initial_game_state(self, game_state: Dict):
        """Send the initial full game state to the client without additional compression"""
        try:
            serialized_state = GameStateSerializer.serialize_game_state(game_state, is_delta=False)
            self.send_message("game_state", serialized_state)
            logging.info("Sent initial full game state to client.")
        except Exception as e:
            logging.error(f"Failed to send initial game state: {e}")
            self.connected = False
    def send_message(self, message_type: str, data: Any):
        """Send message with reliability and compression"""
        try:
            # Create message with sequence number
            message = NetworkMessage(
                type=message_type,
                data=data,
                timestamp=time.time(),
                sequence_number=self.send_sequence
            )
            
            # Serialize and compress
            serialized = pickle.dumps(message)
            compressed = self._compress_data(serialized)
            
            # Send size and data
            size = len(compressed)
            size_bytes = size.to_bytes(4, byteorder='big')
            
            sock = self.client_socket if self.is_host else self.socket
            sock.sendall(size_bytes + compressed)
            
            # Store for potential retransmission
            self.pending_acks[self.send_sequence] = (message, time.time(), 0)
            logging.debug(f"Sent message type: {message_type}, sequence: {self.send_sequence}")
            self.send_sequence += 1
            
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            self.connected = False

    def retransmit_message(self, message: NetworkMessage):
        """Retransmit a specific message without altering its sequence number"""
        try:
            serialized = pickle.dumps(message)
            compressed = self._compress_data(serialized)
            
            size = len(compressed)
            size_bytes = size.to_bytes(4, byteorder='big')
            
            sock = self.client_socket if self.is_host else self.socket
            sock.sendall(size_bytes + compressed)
            
            # Update the send_time and retry count without altering the sequence number
            self.pending_acks[message.sequence_number] = (message, time.time(), self.pending_acks[message.sequence_number][2] + 1)
            logging.debug(f"Retransmitted message type: {message.type}, sequence: {message.sequence_number}, retry: {self.pending_acks[message.sequence_number][2]}")
        except Exception as e:
            logging.error(f"Error retransmitting message {message.sequence_number}: {e}")
            self.connected = False

    def update(self):
        """Process network messages and handle retransmissions"""
        current_time = time.time()
        
        # Handle message retransmission
        for seq, (message, send_time, retries) in list(self.pending_acks.items()):
            if current_time - send_time > self.ack_timeout:
                if retries < self.max_retries:
                    # Retransmit the existing message without creating a new sequence number
                    self.retransmit_message(message)
                else:
                    # Message failed after max retries
                    del self.pending_acks[seq]
                    logging.warning(f"Message {seq} failed after {self.max_retries} retries")
        
        # Process received messages
        while not self.receive_queue.empty():
            try:
                message = self.receive_queue.get_nowait()
                if message.type == "ack":
                    # Handle acknowledgment
                    if message.data in self.pending_acks:
                        del self.pending_acks[message.data]
                        logging.debug(f"Received ACK for message {message.data}")
                else:
                    # Queue message for game processing
                    self.message_queue.put(message)
            except queue.Empty:
                break

    def get_next_message(self):
        """Get next message from queue"""
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        """Enhanced close method with proper cleanup"""
        self.running = False
        self.connected = False
        
        # Close client socket
        if self.client_socket:
            try:
                self.client_socket.close()
                logging.info("Closed client socket.")
            except Exception as e:
                logging.error(f"Error closing client socket: {e}")
            self.client_socket = None
        
        # Close server socket
        if self.socket:
            try:
                self.socket.close()
                logging.info("Closed server socket.")
            except Exception as e:
                logging.error(f"Error closing server socket: {e}")
            self.socket = None
        
        # Clear queues
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except:
                pass
                
        while not self.receive_queue.empty():
            try:
                self.receive_queue.get_nowait()
            except:
                pass
        
        logging.info("Network manager closed.")

    def _accept_connections(self):
        """Accept connections with better error handling"""
        while self.running:
            try:
                if not self.socket:
                    break
                    
                client_socket, client_address = self.socket.accept()
                client_socket.settimeout(None)  # Clear timeout for normal operation
                self.client_socket = client_socket
                self.connected = True
                
                # Start receive thread for client
                receive_thread = threading.Thread(target=self._receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
                
                logging.info(f"Client connected from {client_address}")
                
                # Send initial game state if available
                if self.last_game_state:
                    self.send_initial_game_state(self.last_game_state)
                else:
                    logging.warning("No game state available to send to the client.")
                    
            except socket.timeout:
                # Timeout is expected, keep trying
                continue
            except Exception as e:
                if self.running:
                    logging.error(f"Error accepting connection: {e}")
                break
        
        self.connected = False
        logging.info("Accept thread terminating.")



    def send_ack(self, sequence_number: int):
        """Send an acknowledgment for a received message"""
        try:
            ack_message = NetworkMessage(
                type="ack",
                data=sequence_number,
                timestamp=time.time(),
                sequence_number=self.send_sequence  # Optional: Use a separate sequence for ACKs
            )
            
            serialized = pickle.dumps(ack_message)
            compressed = self._compress_data(serialized)
            
            size = len(compressed)
            size_bytes = size.to_bytes(4, byteorder='big')
            
            sock = self.client_socket if self.is_host else self.socket
            sock.sendall(size_bytes + compressed)
            
            logging.debug(f"Sent ACK for message {sequence_number}")
        except Exception as e:
            logging.error(f"Error sending ACK: {e}")
            self.connected = False

    def _receive_messages(self):
        """Receive messages with better error handling"""
        sock = self.client_socket if self.is_host else self.socket
        
        while self.running and sock and self.connected:
            try:
                # Receive message size
                size_data = sock.recv(4)
                if not size_data:
                    raise ConnectionError("Connection lost")
                    
                message_size = int.from_bytes(size_data, byteorder='big')
                
                # Receive full message
                message_data = b''
                while len(message_data) < message_size:
                    chunk_size = min(4096, message_size - len(message_data))
                    chunk = sock.recv(chunk_size)
                    if not chunk:
                        raise ConnectionError("Connection lost during message receive")
                    message_data += chunk
                
                # Process message
                decompressed = self._decompress_data(message_data)
                message = pickle.loads(decompressed)
                self.receive_queue.put(message)
                logging.debug(f"Received message type: {message.type}, sequence: {message.sequence_number}")
                
            except (ConnectionError, socket.error) as e:
                logging.error(f"Connection error in receive: {e}")
                self.connected = False
                break
            except (pickle.UnpicklingError, zlib.error, ValueError) as e:
                logging.error(f"Failed to deserialize message: {e}")
                continue  # Skip this message and continue receiving
            except Exception as e:
                logging.error(f"Error in receive: {e}")
                continue
        
        self.connected = False
        logging.info("Receive thread terminating.")

    def get_network_stats(self):
        """Get network stats with safety checks"""
        if not self.connected:
            return {
                'average_rtt': 0,
                'pending_messages': 0,
                'message_loss_rate': 0
            }
            
        return {
            'average_rtt': self.average_rtt,
            'pending_messages': len(self.pending_acks),
            'message_loss_rate': len(self.pending_acks) / max(1, self.send_sequence)
        }



