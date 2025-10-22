"""
Main Client Application for Subjugate Online
3D MMORPG Client with OpenGL rendering
"""

import pygame
from pygame.locals import *
import logging
import time
import json
from typing import Dict, Optional, List
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from subjugate_online.shared.protocol import Packet, PacketType, PacketBuilder, PacketParser
from subjugate_online.shared.utils import hash_password
from .renderer import Renderer, UIRenderer
from .network_client import NetworkClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameState:
    """Manages game state"""

    LOGIN = "login"
    CHARACTER_SELECT = "character_select"
    PLAYING = "playing"
    REINCARNATING = "reincarnating"


class SubjugateOnlineClient:
    """Main client application"""

    def __init__(self):
        # Rendering
        self.renderer = Renderer(1280, 720)
        self.ui_renderer = UIRenderer(1280, 720)

        # Networking
        self.login_client = NetworkClient()
        self.game_client = NetworkClient()

        # Game state
        self.state = GameState.LOGIN
        self.running = True
        self.clock = pygame.time.Clock()

        # Player data
        self.account_id: Optional[int] = None
        self.session_token: Optional[str] = None
        self.characters: List[Dict] = []
        self.selected_character: Optional[Dict] = None
        self.player_entity_id: Optional[int] = None
        self.player_data: Optional[Dict] = None

        # World data
        self.world_entities: Dict[int, Dict] = {}  # entity_id -> entity_data
        self.territories: List[Dict] = []

        # UI state
        self.chat_messages: List[str] = []
        self.input_text = ""
        self.show_chat_input = False

        # Input state
        self.keys_pressed = set()
        self.mouse_sensitivity = 0.2
        self.movement_speed = 5.0

        # Register packet handlers
        self._register_handlers()

        # Login credentials (for testing - in production use UI)
        self.username = ""
        self.password = ""

        logger.info("Client initialized")

    def _register_handlers(self):
        """Register network packet handlers"""
        # Login server handlers
        self.login_client.register_handler(PacketType.HANDSHAKE, self._handle_handshake)
        self.login_client.register_handler(PacketType.LOGIN_RESPONSE, self._handle_login_response)
        self.login_client.register_handler(PacketType.CHARACTER_LIST_RESPONSE, self._handle_character_list)
        self.login_client.register_handler(PacketType.CHARACTER_SELECT, self._handle_character_select)
        self.login_client.register_handler(PacketType.CHARACTER_INFO, self._handle_character_created)

        # Game server handlers
        self.game_client.register_handler(PacketType.ENTER_WORLD, self._handle_enter_world)
        self.game_client.register_handler(PacketType.MOVE_UPDATE, self._handle_move_update)
        self.game_client.register_handler(PacketType.DAMAGE_DEALT, self._handle_damage_dealt)
        self.game_client.register_handler(PacketType.PLAYER_DIED, self._handle_player_died)
        self.game_client.register_handler(PacketType.REINCARNATE, self._handle_reincarnation)
        self.game_client.register_handler(PacketType.CHAT_MESSAGE, self._handle_chat_message)
        self.game_client.register_handler(PacketType.TERRITORY_INFO, self._handle_territory_info)
        self.game_client.register_handler(PacketType.STAT_UPDATE, self._handle_stat_update)
        self.game_client.register_handler(PacketType.PING, self._handle_ping)

    def connect_to_login_server(self, host: str = "localhost", port: int = 8888) -> bool:
        """Connect to login server"""
        return self.login_client.connect(host, port)

    def connect_to_game_server(self, host: str = "localhost", port: int = 8889) -> bool:
        """Connect to game server"""
        return self.game_client.connect(host, port)

    def login(self, username: str, password: str):
        """Login to the server"""
        self.username = username
        self.password = password

        password_hash = hash_password(password)
        packet = PacketBuilder.login_request(username, password_hash, "1.0.0")
        self.login_client.send_packet(packet)

        logger.info(f"Sent login request for {username}")

    def request_character_list(self):
        """Request character list"""
        packet = Packet(PacketType.CHARACTER_LIST_REQUEST)
        self.login_client.send_packet(packet)

    def create_character(self, name: str, game_mode: str = "hardcore_ironman"):
        """Create a new character"""
        data = {
            'name': name,
            'game_mode': game_mode
        }
        packet = Packet(PacketType.CHARACTER_CREATE,
                       json.dumps(data).encode('utf-8'))
        self.login_client.send_packet(packet)

        logger.info(f"Requesting character creation: {name}")

    def select_character(self, character_id: int):
        """Select a character"""
        data = {'character_id': character_id}
        packet = Packet(PacketType.CHARACTER_SELECT,
                       json.dumps(data).encode('utf-8'))
        self.login_client.send_packet(packet)

        logger.info(f"Selecting character: {character_id}")

    def enter_world(self):
        """Enter the game world"""
        data = {
            'session_token': self.session_token,
            'character_id': self.selected_character['id']
        }
        packet = Packet(PacketType.ENTER_WORLD,
                       json.dumps(data).encode('utf-8'))
        self.game_client.send_packet(packet)

        logger.info("Entering world...")

    def send_movement(self, x: float, y: float, z: float, rotation: float,
                     vx: float = 0, vy: float = 0, vz: float = 0):
        """Send movement update"""
        if self.player_entity_id is None:
            return

        packet = PacketBuilder.move_update(
            self.player_entity_id, x, y, z, rotation, vx, vy, vz
        )
        self.game_client.send_packet(packet)

    def send_attack(self, target_id: int, skill_id: int = 0):
        """Send attack request"""
        packet = PacketBuilder.attack_request(target_id, skill_id)
        self.game_client.send_packet(packet)
        logger.info(f"Attacking target {target_id}")

    def send_chat(self, message: str, channel: str = "global"):
        """Send chat message"""
        packet = PacketBuilder.chat_message(self.username, message, channel)
        self.game_client.send_packet(packet)

    def request_reincarnation(self):
        """Request reincarnation"""
        if self.player_entity_id:
            packet = Packet(PacketType.REINCARNATE,
                          json.dumps({'entity_id': self.player_entity_id}).encode('utf-8'))
            self.game_client.send_packet(packet)
            logger.info("Requesting reincarnation...")

    # Packet handlers

    def _handle_handshake(self, packet: Packet):
        """Handle handshake"""
        logger.info("Received handshake from server")

    def _handle_login_response(self, packet: Packet):
        """Handle login response"""
        success, message, session_token = PacketParser.parse_login_response(packet)

        if success:
            self.session_token = session_token
            logger.info(f"Login successful: {message}")
            self.request_character_list()
        else:
            logger.error(f"Login failed: {message}")

    def _handle_character_list(self, packet: Packet):
        """Handle character list"""
        data = json.loads(packet.payload.decode('utf-8'))
        self.characters = data.get('characters', [])

        logger.info(f"Received {len(self.characters)} characters")

        if len(self.characters) > 0:
            self.state = GameState.CHARACTER_SELECT
        else:
            # Auto-create first character for testing
            logger.info("No characters found, creating default character...")
            self.create_character("TestHero", "hardcore_ironman")

    def _handle_character_created(self, packet: Packet):
        """Handle character creation response"""
        data = json.loads(packet.payload.decode('utf-8'))
        logger.info(f"Character created: {data.get('name')}")

        # Refresh character list
        self.request_character_list()

    def _handle_character_select(self, packet: Packet):
        """Handle character selection response"""
        data = json.loads(packet.payload.decode('utf-8'))

        if data.get('success'):
            self.selected_character = data.get('character')
            game_host = data.get('game_server_host', 'localhost')
            game_port = data.get('game_server_port', 8889)

            logger.info(f"Character selected: {self.selected_character['name']}")
            logger.info(f"Connecting to game server: {game_host}:{game_port}")

            # Connect to game server
            if self.connect_to_game_server(game_host, game_port):
                time.sleep(0.5)  # Wait for connection
                self.enter_world()

    def _handle_enter_world(self, packet: Packet):
        """Handle entering world"""
        data = json.loads(packet.payload.decode('utf-8'))

        if data.get('success'):
            self.player_entity_id = data.get('entity_id')
            self.player_data = data.get('player_data')

            logger.info(f"Entered world as entity {self.player_entity_id}")

            self.state = GameState.PLAYING

            # Request territory info
            self.game_client.send_packet(Packet(PacketType.TERRITORY_INFO))
        else:
            # Could be a join notification
            logger.info(f"Player joined: {data.get('name')}")

    def _handle_move_update(self, packet: Packet):
        """Handle movement update"""
        move_data = PacketParser.parse_move_update(packet)
        entity_id = move_data['entity_id']

        # Update entity in world
        if entity_id not in self.world_entities:
            self.world_entities[entity_id] = {}

        self.world_entities[entity_id].update({
            'position': move_data['position'],
            'rotation': move_data['rotation'],
            'velocity': move_data['velocity']
        })

    def _handle_damage_dealt(self, packet: Packet):
        """Handle damage dealt"""
        damage_data = PacketParser.parse_damage_dealt(packet)

        message = f"{damage_data['attacker_id']} dealt {damage_data['damage']} damage to {damage_data['target_id']}"
        if damage_data['is_critical']:
            message += " (CRITICAL!)"

        self.chat_messages.append(message)
        logger.info(message)

    def _handle_player_died(self, packet: Packet):
        """Handle player death"""
        player_id, killer_id, reincarnation_score = struct.unpack('!III', packet.payload)

        if player_id == self.player_entity_id:
            self.chat_messages.append(f"You were killed! Reincarnation score: {reincarnation_score}")
            self.state = GameState.REINCARNATING
        else:
            self.chat_messages.append(f"Player {player_id} was killed by {killer_id}")

        logger.info(f"Player {player_id} died. Killer: {killer_id}, Score: {reincarnation_score}")

    def _handle_reincarnation(self, packet: Packet):
        """Handle reincarnation"""
        logger.info("Reincarnation successful!")
        self.chat_messages.append("You have been reincarnated with new perks!")
        self.state = GameState.PLAYING

    def _handle_chat_message(self, packet: Packet):
        """Handle chat message"""
        chat_data = PacketParser.parse_chat_message(packet)
        message = f"[{chat_data['channel']}] {chat_data['sender']}: {chat_data['message']}"
        self.chat_messages.append(message)
        logger.info(message)

    def _handle_territory_info(self, packet: Packet):
        """Handle territory info"""
        data = json.loads(packet.payload.decode('utf-8'))
        self.territories = data.get('territories', [])
        logger.info(f"Received info for {len(self.territories)} territories")

    def _handle_stat_update(self, packet: Packet):
        """Handle stat update"""
        data = json.loads(packet.payload.decode('utf-8'))
        if self.player_data:
            self.player_data.update(data)

    def _handle_ping(self, packet: Packet):
        """Handle ping from server"""
        # Send pong back
        pong_packet = Packet(PacketType.PONG, packet.payload)
        self.game_client.send_packet(pong_packet)

    def handle_input(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False

            elif event.type == KEYDOWN:
                self.keys_pressed.add(event.key)

                # Chat input
                if event.key == K_RETURN:
                    if self.show_chat_input:
                        if self.input_text:
                            self.send_chat(self.input_text)
                            self.input_text = ""
                        self.show_chat_input = False
                    else:
                        self.show_chat_input = True

                elif event.key == K_ESCAPE:
                    if self.show_chat_input:
                        self.show_chat_input = False
                        self.input_text = ""
                    else:
                        self.running = False

                # Reincarnation
                elif event.key == K_r and self.state == GameState.REINCARNATING:
                    self.request_reincarnation()

                # Attack (space)
                elif event.key == K_SPACE and self.state == GameState.PLAYING:
                    # Find nearest target
                    # In full implementation, would have proper targeting
                    pass

                # Chat input text
                elif self.show_chat_input:
                    if event.key == K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.unicode and len(self.input_text) < 100:
                        self.input_text += event.unicode

            elif event.type == KEYUP:
                if event.key in self.keys_pressed:
                    self.keys_pressed.remove(event.key)

            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 4:  # Scroll up
                    self.renderer.camera.zoom(-1.0)
                elif event.button == 5:  # Scroll down
                    self.renderer.camera.zoom(1.0)

            elif event.type == MOUSEMOTION:
                if pygame.mouse.get_pressed()[2]:  # Right mouse button
                    dx, dy = event.rel
                    self.renderer.camera.rotate(
                        -dy * self.mouse_sensitivity,
                        -dx * self.mouse_sensitivity
                    )

    def update_player_movement(self, delta_time: float):
        """Update player movement based on input"""
        if self.state != GameState.PLAYING or not self.player_data:
            return

        # Get current position
        pos = self.player_data['position']
        x, y, z = pos['x'], pos['y'], pos['z']
        rotation = self.player_data.get('rotation', 0)

        vx, vy, vz = 0, 0, 0
        moved = False

        # WASD movement
        if K_w in self.keys_pressed:
            z -= self.movement_speed * delta_time
            moved = True
        if K_s in self.keys_pressed:
            z += self.movement_speed * delta_time
            moved = True
        if K_a in self.keys_pressed:
            x -= self.movement_speed * delta_time
            moved = True
        if K_d in self.keys_pressed:
            x += self.movement_speed * delta_time
            moved = True

        # Update position
        if moved:
            self.player_data['position'] = {'x': x, 'y': y, 'z': z}
            self.send_movement(x, y, z, rotation, vx, vy, vz)

        # Update camera to follow player
        self.renderer.camera.update((x, y, z))

    def render(self):
        """Render the scene"""
        if self.state == GameState.PLAYING and self.player_data:
            # Build world data for rendering
            world_data = {
                'players': {},
                'npcs': {},
                'territories': self.territories
            }

            # Add player
            world_data['players'][self.player_entity_id] = {
                **self.player_data,
                'is_self': True
            }

            # Add other entities
            for entity_id, entity_data in self.world_entities.items():
                if entity_id != self.player_entity_id:
                    world_data['players'][entity_id] = entity_data

            # Render scene
            self.renderer.draw_scene(world_data)

            # Render UI
            self.ui_renderer.draw_hud(self.player_data)
            self.ui_renderer.draw_chat(self.chat_messages)

            # Draw FPS
            fps = self.clock.get_fps()
            self.ui_renderer.draw_fps(fps)

            # Draw chat input
            if self.show_chat_input:
                self.ui_renderer.draw_text(
                    f"> {self.input_text}_",
                    10,
                    self.ui_renderer.screen_height - 30,
                    (255, 255, 0)
                )

            # Draw reincarnation prompt
            if self.state == GameState.REINCARNATING:
                self.ui_renderer.draw_text(
                    "You have died! Press R to reincarnate",
                    self.ui_renderer.screen_width // 2 - 200,
                    self.ui_renderer.screen_height // 2,
                    (255, 0, 0)
                )

        else:
            # Draw login/character select screen
            self.renderer.clear()
            if self.state == GameState.LOGIN:
                self.ui_renderer.draw_text(
                    "Connecting to server...",
                    self.ui_renderer.screen_width // 2 - 100,
                    self.ui_renderer.screen_height // 2,
                    (255, 255, 255)
                )
            elif self.state == GameState.CHARACTER_SELECT:
                self.ui_renderer.draw_text(
                    "Character Select",
                    self.ui_renderer.screen_width // 2 - 80,
                    50,
                    (255, 255, 255)
                )

        self.renderer.flip()

    def run(self):
        """Main game loop"""
        logger.info("Starting client...")

        # Connect to login server
        if not self.connect_to_login_server():
            logger.error("Failed to connect to login server")
            return

        # Auto-login for testing
        time.sleep(0.5)
        self.login("testuser", "password123")

        last_time = time.time()

        while self.running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            # Handle input
            self.handle_input()

            # Process network packets
            self.login_client.process_packets()
            self.game_client.process_packets()

            # Update game state
            if self.state == GameState.PLAYING:
                self.update_player_movement(delta_time)

                # Send periodic pings
                self.game_client.send_ping()

            # Render
            self.render()

            # Limit framerate
            self.clock.tick(60)

        # Cleanup
        self.login_client.disconnect()
        self.game_client.disconnect()
        pygame.quit()

        logger.info("Client stopped")


def main():
    """Main entry point"""
    client = SubjugateOnlineClient()
    client.run()


if __name__ == "__main__":
    import struct
    main()
