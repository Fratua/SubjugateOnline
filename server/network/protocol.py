"""
Subjugate Online - Network Protocol
Binary protocol using MessagePack for efficient serialization
"""

import msgpack
import struct
from typing import Dict, Any, Optional
from shared.constants import PacketType, MAX_PACKET_SIZE
from shared.utils import Logger

logger = Logger.get_logger(__name__)


class Packet:
    """Base packet class"""

    def __init__(self, packet_type: int, data: Optional[Dict[str, Any]] = None):
        self.packet_type = packet_type
        self.data = data or {}

    def serialize(self) -> bytes:
        """
        Serialize packet to bytes

        Format: [4 bytes: length][4 bytes: type][N bytes: msgpack data]
        """
        # Pack data with MessagePack
        packed_data = msgpack.packb(self.data, use_bin_type=True)

        # Create header: packet type (4 bytes)
        header = struct.pack('!I', self.packet_type)

        # Full packet: header + data
        packet = header + packed_data

        # Prefix with length (4 bytes)
        length = len(packet)
        if length > MAX_PACKET_SIZE:
            raise ValueError(f"Packet size {length} exceeds maximum {MAX_PACKET_SIZE}")

        final_packet = struct.pack('!I', length) + packet

        return final_packet

    @staticmethod
    def deserialize(data: bytes) -> Optional['Packet']:
        """
        Deserialize bytes to packet

        Returns:
            Packet object or None if invalid
        """
        try:
            # Read packet type (first 4 bytes)
            if len(data) < 4:
                return None

            packet_type = struct.unpack('!I', data[:4])[0]

            # Read msgpack data (remaining bytes)
            if len(data) > 4:
                packet_data = msgpack.unpackb(data[4:], raw=False)
            else:
                packet_data = {}

            return Packet(packet_type, packet_data)

        except Exception as e:
            logger.error(f"Failed to deserialize packet: {e}")
            return None

    def __repr__(self):
        return f"<Packet(type={self.packet_type}, data={self.data})>"


class PacketBuffer:
    """Buffer for handling incomplete packets from stream"""

    def __init__(self):
        self.buffer = bytearray()
        self.expected_length = None

    def add_data(self, data: bytes):
        """Add data to buffer"""
        self.buffer.extend(data)

    def get_packet(self) -> Optional[Packet]:
        """
        Extract a complete packet from buffer if available

        Returns:
            Packet or None if incomplete
        """
        # Need at least 4 bytes to read length
        if len(self.buffer) < 4:
            return None

        # Read expected length if not yet known
        if self.expected_length is None:
            self.expected_length = struct.unpack('!I', self.buffer[:4])[0]

        # Check if we have the complete packet (4 bytes length header + packet data)
        total_length = 4 + self.expected_length
        if len(self.buffer) < total_length:
            return None

        # Extract packet data (skip the 4-byte length header)
        packet_data = bytes(self.buffer[4:total_length])

        # Remove processed data from buffer
        self.buffer = self.buffer[total_length:]
        self.expected_length = None

        # Deserialize and return packet
        return Packet.deserialize(packet_data)

    def has_complete_packet(self) -> bool:
        """Check if buffer contains a complete packet"""
        if len(self.buffer) < 4:
            return False

        if self.expected_length is None:
            self.expected_length = struct.unpack('!I', self.buffer[:4])[0]

        return len(self.buffer) >= (4 + self.expected_length)


# ============================================================================
# PACKET BUILDERS - Helper functions to create common packets
# ============================================================================

def create_login_response(success: bool, session_token: Optional[str] = None,
                          error_code: int = 0, message: str = "") -> Packet:
    """Create login response packet"""
    return Packet(PacketType.LOGIN_RESPONSE, {
        'success': success,
        'session_token': session_token,
        'error_code': error_code,
        'message': message
    })


def create_register_response(success: bool, error_code: int = 0, message: str = "") -> Packet:
    """Create registration response packet"""
    return Packet(PacketType.REGISTER_RESPONSE, {
        'success': success,
        'error_code': error_code,
        'message': message
    })


def create_character_list_response(characters: list) -> Packet:
    """Create character list response packet"""
    return Packet(PacketType.CHARACTER_LIST_RESPONSE, {
        'characters': characters
    })


def create_character_create_response(success: bool, character_id: Optional[int] = None,
                                     error_code: int = 0, message: str = "") -> Packet:
    """Create character creation response packet"""
    return Packet(PacketType.CHARACTER_CREATE_RESPONSE, {
        'success': success,
        'character_id': character_id,
        'error_code': error_code,
        'message': message
    })


def create_character_select_response(success: bool, character_data: Optional[Dict] = None,
                                     game_server_host: str = "", game_server_port: int = 0,
                                     error_code: int = 0, message: str = "") -> Packet:
    """Create character select response packet"""
    return Packet(PacketType.CHARACTER_SELECT_RESPONSE, {
        'success': success,
        'character_data': character_data,
        'game_server_host': game_server_host,
        'game_server_port': game_server_port,
        'error_code': error_code,
        'message': message
    })


def create_player_spawn(character_id: int, character_data: Dict) -> Packet:
    """Create player spawn packet"""
    return Packet(PacketType.PLAYER_SPAWN, {
        'character_id': character_id,
        'character_data': character_data
    })


def create_player_despawn(character_id: int) -> Packet:
    """Create player despawn packet"""
    return Packet(PacketType.PLAYER_DESPAWN, {
        'character_id': character_id
    })


def create_player_position_update(character_id: int, x: float, y: float, z: float, rotation: float) -> Packet:
    """Create position update packet"""
    return Packet(PacketType.PLAYER_POSITION_UPDATE, {
        'character_id': character_id,
        'x': x,
        'y': y,
        'z': z,
        'rotation': rotation
    })


def create_stats_update(character_id: int, stats: Dict) -> Packet:
    """Create stats update packet"""
    return Packet(PacketType.STATS_UPDATE, {
        'character_id': character_id,
        'stats': stats
    })


def create_damage_dealt(attacker_id: int, target_id: int, damage: int, target_hp: int) -> Packet:
    """Create damage dealt packet"""
    return Packet(PacketType.DAMAGE_DEALT, {
        'attacker_id': attacker_id,
        'target_id': target_id,
        'damage': damage,
        'target_hp': target_hp
    })


def create_player_death(character_id: int, killer_id: Optional[int] = None) -> Packet:
    """Create player death packet"""
    return Packet(PacketType.PLAYER_DEATH, {
        'character_id': character_id,
        'killer_id': killer_id
    })


def create_reincarnation_response(success: bool, perks: Optional[Dict] = None,
                                  error_code: int = 0, message: str = "") -> Packet:
    """Create reincarnation response packet"""
    return Packet(PacketType.REINCARNATION_RESPONSE, {
        'success': success,
        'perks': perks,
        'error_code': error_code,
        'message': message
    })


def create_territory_status(territories: list) -> Packet:
    """Create territory status packet"""
    return Packet(PacketType.TERRITORY_STATUS, {
        'territories': territories
    })


def create_territory_captured(territory_id: int, controller_name: str, buffs: Dict) -> Packet:
    """Create territory captured packet"""
    return Packet(PacketType.TERRITORY_CAPTURED, {
        'territory_id': territory_id,
        'controller_name': controller_name,
        'buffs': buffs
    })


def create_chat_message(sender_name: str, message: str, channel: str = "global") -> Packet:
    """Create chat message packet"""
    return Packet(PacketType.CHAT_MESSAGE, {
        'sender': sender_name,
        'message': message,
        'channel': channel
    })


def create_npc_spawn(npc_id: int, npc_data: Dict) -> Packet:
    """Create NPC spawn packet"""
    return Packet(PacketType.NPC_SPAWN, {
        'npc_id': npc_id,
        'npc_data': npc_data
    })


def create_npc_update(npc_id: int, npc_data: Dict) -> Packet:
    """Create NPC update packet"""
    return Packet(PacketType.NPC_UPDATE, {
        'npc_id': npc_id,
        'npc_data': npc_data
    })


def create_error_packet(error_code: int, message: str) -> Packet:
    """Create error packet"""
    return Packet(PacketType.ERROR, {
        'error_code': error_code,
        'message': message
    })


def create_heartbeat() -> Packet:
    """Create heartbeat packet"""
    return Packet(PacketType.HEARTBEAT, {})
