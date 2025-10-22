"""
Subjugate Online - 3D Game Client
Main game client using Panda3D for rendering
"""

import sys
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.actor.Actor import Actor
from panda3d.core import (
    AmbientLight, DirectionalLight, Vec3, Vec4, Point3,
    CollisionTraverser, CollisionNode, CollisionSphere,
    CollisionHandlerQueue, WindowProperties, TextNode, GeomNode
)
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel
import time

from shared.constants import PacketType, ATTACK_COOLDOWN
from shared.utils import Logger
from server.network.protocol import Packet
from client.network_client import NetworkClient

logger = Logger.get_logger(__name__)


class RemotePlayer:
    """Represents a remote player in the world"""

    def __init__(self, character_id: int, character_data: dict, render):
        self.character_id = character_id
        self.name = character_data.get('name', 'Unknown')
        self.level = character_data.get('level', 1)
        self.hp = character_data.get('hp', 100)
        self.max_hp = character_data.get('max_hp', 100)

        position = character_data.get('position', [0, 0, 0])
        self.position = Vec3(position[0], position[2], position[1])  # Panda3D uses Z-up

        # Create visual representation (simple colored sphere for now)
        from panda3d.core import NodePath, GeomNode
        from direct.gui.OnscreenText import OnscreenText

        self.model = render.attachNewNode(f"player_{character_id}")
        self.model.setPos(self.position)

        # Create a simple sphere to represent player
        from panda3d.core import CardMaker
        cm = CardMaker(f"player_card_{character_id}")
        cm.setFrame(-0.5, 0.5, -1, 1)
        card = self.model.attachNewNode(cm.generate())
        card.setColor(0.2, 0.5, 1.0, 1.0)
        card.setBillboardPointEye()

        # Name tag
        self.name_tag = OnscreenText(
            text=self.name,
            pos=(0, 1.5),
            scale=0.5,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.model
        )
        self.name_tag.setBillboardPointEye()

    def update_position(self, x: float, y: float, z: float):
        """Update player position"""
        self.position = Vec3(x, z, y)  # Convert to Panda3D coordinates
        if self.model:
            self.model.setPos(self.position)

    def update_stats(self, stats: dict):
        """Update player stats"""
        self.hp = stats.get('hp', self.hp)
        self.max_hp = stats.get('max_hp', self.max_hp)
        self.level = stats.get('level', self.level)

    def destroy(self):
        """Remove from scene"""
        if self.model:
            self.model.removeNode()


class RemoteNPC:
    """Represents an NPC in the world"""

    def __init__(self, instance_id: int, npc_data: dict, render):
        self.instance_id = instance_id
        self.name = npc_data.get('name', 'NPC')
        self.level = npc_data.get('level', 1)
        self.hp = npc_data.get('hp', 100)
        self.max_hp = npc_data.get('max_hp', 100)

        position = npc_data.get('position', [0, 0, 0])
        self.position = Vec3(position[0], position[2], position[1])

        # Create visual representation
        self.model = render.attachNewNode(f"npc_{instance_id}")
        self.model.setPos(self.position)

        # Create sphere (red color for enemy)
        from panda3d.core import CardMaker
        cm = CardMaker(f"npc_card_{instance_id}")
        cm.setFrame(-0.5, 0.5, -1, 1)
        card = self.model.attachNewNode(cm.generate())
        card.setColor(1.0, 0.2, 0.2, 1.0)
        card.setBillboardPointEye()

        # Name tag
        self.name_tag = OnscreenText(
            text=f"{self.name} (Lv.{self.level})",
            pos=(0, 1.5),
            scale=0.4,
            fg=(1, 0.5, 0.5, 1),
            align=TextNode.ACenter,
            mayChange=True,
            parent=self.model
        )
        self.name_tag.setBillboardPointEye()

    def update(self, npc_data: dict):
        """Update NPC data"""
        position = npc_data.get('position', list(self.position))
        self.position = Vec3(position[0], position[2], position[1])

        if self.model:
            self.model.setPos(self.position)

        self.hp = npc_data.get('hp', self.hp)

    def destroy(self):
        """Remove from scene"""
        if self.model:
            self.model.removeNode()


class SubjugateOnlineClient(ShowBase):
    """Main game client"""

    def __init__(self, character_data: dict, session_token: str):
        ShowBase.__init__(self)

        # Character data
        self.character_data = character_data
        self.session_token = session_token
        self.character_id = character_data['id']

        # Network
        self.network = NetworkClient()
        self.setup_packet_handlers()

        # Player state
        self.player_pos = Vec3(
            character_data['position'][0],
            character_data['position'][2],
            character_data['position'][1]
        )
        self.player_rotation = 0.0
        self.player_velocity = Vec3(0, 0, 0)
        self.move_speed = character_data.get('speed', 5.0)

        # Combat state
        self.target_id = None
        self.target_type = None
        self.last_attack_time = 0.0

        # Remote entities
        self.remote_players = {}  # {character_id: RemotePlayer}
        self.remote_npcs = {}  # {instance_id: RemoteNPC}

        # Setup game
        self.setup_window()
        self.setup_lighting()
        self.setup_camera()
        self.setup_player()
        self.setup_world()
        self.setup_ui()
        self.setup_controls()

        # Add update tasks
        self.taskMgr.add(self.update_task, "update")
        self.taskMgr.add(self.network_task, "network")

        logger.info(f"Game client initialized for {character_data['name']}")

    def setup_window(self):
        """Setup game window"""
        props = WindowProperties()
        props.setTitle("Subjugate Online - 3D MMORPG")
        props.setSize(1280, 720)
        self.win.requestProperties(props)

        # Disable mouse control of camera (we'll handle it ourselves)
        self.disableMouse()

    def setup_lighting(self):
        """Setup scene lighting"""
        # Ambient light
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.3, 0.3, 0.3, 1))
        ambient_np = self.render.attachNewNode(ambient)
        self.render.setLight(ambient_np)

        # Directional light (sun)
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(0.8, 0.8, 0.7, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-60, -50, 0)
        self.render.setLight(sun_np)

    def setup_camera(self):
        """Setup camera (third-person)"""
        self.camera.setPos(self.player_pos.x, self.player_pos.y - 15, self.player_pos.z + 10)
        self.camera.lookAt(self.player_pos)

    def setup_player(self):
        """Setup player model"""
        # Create simple player representation (blue cube)
        from panda3d.core import CardMaker
        cm = CardMaker("player_card")
        cm.setFrame(-0.5, 0.5, -1, 1)

        self.player_model = self.render.attachNewNode(cm.generate())
        self.player_model.setPos(self.player_pos)
        self.player_model.setColor(0.2, 1.0, 0.2, 1.0)
        self.player_model.setBillboardPointEye()

    def setup_world(self):
        """Setup world (simple ground plane)"""
        # Create ground plane
        from panda3d.core import CardMaker
        cm = CardMaker("ground")
        cm.setFrame(-500, 500, -500, 500)

        ground = self.render.attachNewNode(cm.generate())
        ground.setP(-90)  # Rotate to be horizontal
        ground.setPos(0, 0, -0.1)
        ground.setColor(0.3, 0.5, 0.3, 1.0)

    def setup_ui(self):
        """Setup user interface"""
        # Character info
        self.ui_name = OnscreenText(
            text=f"{self.character_data['name']} (Lv.{self.character_data['level']})",
            pos=(-1.3, 0.9),
            scale=0.06,
            fg=(1, 1, 1, 1),
            align=TextNode.ALeft
        )

        # HP bar
        self.ui_hp = OnscreenText(
            text=f"HP: {self.character_data['hp']}/{self.character_data['max_hp']}",
            pos=(-1.3, 0.83),
            scale=0.05,
            fg=(1, 0.2, 0.2, 1),
            align=TextNode.ALeft
        )

        # MP bar
        self.ui_mp = OnscreenText(
            text=f"MP: {self.character_data['mp']}/{self.character_data['max_mp']}",
            pos=(-1.3, 0.77),
            scale=0.05,
            fg=(0.2, 0.2, 1, 1),
            align=TextNode.ALeft
        )

        # Position indicator
        self.ui_pos = OnscreenText(
            text=f"Pos: {self.player_pos.x:.1f}, {self.player_pos.z:.1f}",
            pos=(-1.3, -0.9),
            scale=0.04,
            fg=(0.7, 0.7, 0.7, 1),
            align=TextNode.ALeft
        )

        # Instructions
        self.ui_help = OnscreenText(
            text="WASD: Move | Space: Attack | T: Target Nearest | R: Reincarnate | ESC: Quit",
            pos=(0, -0.95),
            scale=0.04,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter
        )

        # Chat log (simple)
        self.ui_chat = OnscreenText(
            text="Welcome to Subjugate Online!",
            pos=(-1.3, 0.5),
            scale=0.04,
            fg=(1, 1, 0.5, 1),
            align=TextNode.ALeft,
            mayChange=True
        )

    def setup_controls(self):
        """Setup input controls"""
        # Movement keys
        self.keys = {
            'w': False,
            'a': False,
            's': False,
            'd': False
        }

        self.accept('w', self.set_key, ['w', True])
        self.accept('w-up', self.set_key, ['w', False])
        self.accept('a', self.set_key, ['a', True])
        self.accept('a-up', self.set_key, ['a', False])
        self.accept('s', self.set_key, ['s', True])
        self.accept('s-up', self.set_key, ['s', False])
        self.accept('d', self.set_key, ['d', True])
        self.accept('d-up', self.set_key, ['d', False])

        # Action keys
        self.accept('space', self.attack)
        self.accept('t', self.target_nearest_npc)
        self.accept('r', self.request_reincarnation)
        self.accept('escape', self.quit_game)

    def set_key(self, key, value):
        """Set key state"""
        self.keys[key] = value

    def attack(self):
        """Perform attack"""
        current_time = time.time()

        if (current_time - self.last_attack_time) < ATTACK_COOLDOWN:
            return

        if self.target_id is None:
            self.add_chat_message("No target selected")
            return

        # Send attack request
        packet = Packet(PacketType.ATTACK_REQUEST, {
            'target_id': self.target_id,
            'target_type': self.target_type
        })

        self.network.send_packet(packet)
        self.last_attack_time = current_time

        self.add_chat_message(f"Attacking target {self.target_id}...")

    def target_nearest_npc(self):
        """Target nearest NPC"""
        nearest_npc = None
        nearest_dist = float('inf')

        for npc in self.remote_npcs.values():
            dist = (npc.position - self.player_pos).length()
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_npc = npc

        if nearest_npc:
            self.target_id = nearest_npc.instance_id
            self.target_type = 'npc'
            self.add_chat_message(f"Targeted {nearest_npc.name} (Lv.{nearest_npc.level})")
        else:
            self.add_chat_message("No NPCs nearby")

    def request_reincarnation(self):
        """Request reincarnation"""
        packet = Packet(PacketType.REINCARNATION_REQUEST, {})
        self.network.send_packet(packet)
        self.add_chat_message("Requesting reincarnation...")

    def quit_game(self):
        """Quit the game"""
        logger.info("Quitting game...")
        self.network.disconnect()
        sys.exit(0)

    def add_chat_message(self, message: str):
        """Add message to chat log"""
        self.ui_chat.setText(message)

    def update_task(self, task):
        """Main update loop"""
        dt = globalClock.getDt()

        # Update movement
        self.update_movement(dt)

        # Update camera
        self.update_camera()

        # Update UI
        self.update_ui()

        return Task.cont

    def update_movement(self, dt):
        """Update player movement"""
        # Calculate movement vector
        move_vec = Vec3(0, 0, 0)

        if self.keys['w']:
            move_vec.y += 1
        if self.keys['s']:
            move_vec.y -= 1
        if self.keys['a']:
            move_vec.x -= 1
        if self.keys['d']:
            move_vec.x += 1

        # Normalize and apply speed
        if move_vec.length() > 0:
            move_vec.normalize()
            move_vec *= self.move_speed * dt

            # Update position
            self.player_pos += move_vec
            self.player_model.setPos(self.player_pos)

            # Send position update to server
            packet = Packet(PacketType.PLAYER_MOVE, {
                'x': self.player_pos.x,
                'y': self.player_pos.z,  # Convert back to server coordinates
                'z': self.player_pos.y,
                'rotation': self.player_rotation
            })

            self.network.send_packet(packet)

    def update_camera(self):
        """Update camera to follow player"""
        camera_offset = Vec3(0, -15, 10)
        target_pos = self.player_pos + camera_offset

        # Smooth camera movement
        current_pos = self.camera.getPos()
        new_pos = current_pos + (target_pos - current_pos) * 0.1

        self.camera.setPos(new_pos)
        self.camera.lookAt(self.player_pos)

    def update_ui(self):
        """Update UI elements"""
        self.ui_pos.setText(f"Pos: {self.player_pos.x:.1f}, {self.player_pos.y:.1f}")

    def network_task(self, task):
        """Process network packets"""
        self.network.process_incoming_packets()
        return Task.cont

    # ========================================================================
    # PACKET HANDLERS
    # ========================================================================

    def setup_packet_handlers(self):
        """Setup packet handlers"""
        self.network.register_handler(PacketType.PLAYER_SPAWN, self.handle_player_spawn)
        self.network.register_handler(PacketType.PLAYER_DESPAWN, self.handle_player_despawn)
        self.network.register_handler(PacketType.PLAYER_POSITION_UPDATE, self.handle_player_position_update)
        self.network.register_handler(PacketType.NPC_SPAWN, self.handle_npc_spawn)
        self.network.register_handler(PacketType.NPC_UPDATE, self.handle_npc_update)
        self.network.register_handler(PacketType.NPC_DESPAWN, self.handle_npc_despawn)
        self.network.register_handler(PacketType.DAMAGE_DEALT, self.handle_damage_dealt)
        self.network.register_handler(PacketType.STATS_UPDATE, self.handle_stats_update)
        self.network.register_handler(PacketType.CHAT_MESSAGE, self.handle_chat_message)
        self.network.register_handler(PacketType.REINCARNATION_RESPONSE, self.handle_reincarnation_response)

    def handle_player_spawn(self, packet: Packet):
        """Handle player spawn"""
        character_id = packet.data.get('character_id')
        character_data = packet.data.get('character_data', {})

        if character_id == self.character_id:
            # Self spawn (initial connection)
            return

        # Create remote player
        if character_id not in self.remote_players:
            player = RemotePlayer(character_id, character_data, self.render)
            self.remote_players[character_id] = player
            logger.info(f"Remote player spawned: {player.name}")

    def handle_player_despawn(self, packet: Packet):
        """Handle player despawn"""
        character_id = packet.data.get('character_id')

        if character_id in self.remote_players:
            self.remote_players[character_id].destroy()
            del self.remote_players[character_id]

    def handle_player_position_update(self, packet: Packet):
        """Handle player position update"""
        character_id = packet.data.get('character_id')

        if character_id in self.remote_players:
            x = packet.data.get('x', 0)
            y = packet.data.get('y', 0)
            z = packet.data.get('z', 0)

            self.remote_players[character_id].update_position(x, y, z)

    def handle_npc_spawn(self, packet: Packet):
        """Handle NPC spawn"""
        instance_id = packet.data.get('npc_id')
        npc_data = packet.data.get('npc_data', {})

        if instance_id not in self.remote_npcs:
            npc = RemoteNPC(instance_id, npc_data, self.render)
            self.remote_npcs[instance_id] = npc
            logger.info(f"NPC spawned: {npc.name}")

    def handle_npc_update(self, packet: Packet):
        """Handle NPC update"""
        instance_id = packet.data.get('npc_id')
        npc_data = packet.data.get('npc_data', {})

        if instance_id in self.remote_npcs:
            self.remote_npcs[instance_id].update(npc_data)

    def handle_npc_despawn(self, packet: Packet):
        """Handle NPC despawn"""
        instance_id = packet.data.get('npc_id')

        if instance_id in self.remote_npcs:
            self.remote_npcs[instance_id].destroy()
            del self.remote_npcs[instance_id]

    def handle_damage_dealt(self, packet: Packet):
        """Handle damage dealt"""
        attacker_id = packet.data.get('attacker_id')
        target_id = packet.data.get('target_id')
        damage = packet.data.get('damage')

        self.add_chat_message(f"Damage: {damage}")

    def handle_stats_update(self, packet: Packet):
        """Handle stats update"""
        stats = packet.data.get('stats', {})

        if 'hp' in stats:
            self.character_data['hp'] = stats['hp']
            self.ui_hp.setText(f"HP: {self.character_data['hp']}/{self.character_data['max_hp']}")

        if 'mp' in stats:
            self.character_data['mp'] = stats['mp']
            self.ui_mp.setText(f"MP: {self.character_data['mp']}/{self.character_data['max_mp']}")

    def handle_chat_message(self, packet: Packet):
        """Handle chat message"""
        sender = packet.data.get('sender', 'Unknown')
        message = packet.data.get('message', '')

        self.add_chat_message(f"{sender}: {message}")

    def handle_reincarnation_response(self, packet: Packet):
        """Handle reincarnation response"""
        success = packet.data.get('success', False)
        message = packet.data.get('message', '')

        if success:
            self.add_chat_message(f"Reincarnation successful! {message}")
        else:
            self.add_chat_message(f"Reincarnation failed: {message}")

    def connect_to_game_server(self, host: str, port: int) -> bool:
        """Connect to game server"""
        if not self.network.connect(host, port):
            logger.error("Failed to connect to game server")
            return False

        # Send handshake
        packet = Packet(PacketType.GAME_SERVER_CONNECT, {
            'session_token': self.session_token,
            'character_id': self.character_id
        })

        self.network.send_packet(packet)

        return True
