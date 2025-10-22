"""
Network Protocol Definition for Subjugate Online
Binary packet-based protocol for efficient client-server communication
"""

import struct
import enum
import zlib
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


class PacketType(enum.IntEnum):
    """All packet types used in the game"""
    # Connection & Authentication (0-99)
    HANDSHAKE = 0
    LOGIN_REQUEST = 1
    LOGIN_RESPONSE = 2
    LOGOUT = 3
    REGISTER_REQUEST = 4
    REGISTER_RESPONSE = 5
    PING = 6
    PONG = 7

    # Character Management (100-199)
    CHARACTER_LIST_REQUEST = 100
    CHARACTER_LIST_RESPONSE = 101
    CHARACTER_CREATE = 102
    CHARACTER_DELETE = 103
    CHARACTER_SELECT = 104
    CHARACTER_INFO = 105

    # World & Movement (200-299)
    ENTER_WORLD = 200
    LEAVE_WORLD = 201
    MOVE_REQUEST = 202
    MOVE_UPDATE = 203
    POSITION_SYNC = 204
    TELEPORT = 205
    ZONE_CHANGE = 206

    # Combat & PVP (300-399)
    ATTACK_REQUEST = 300
    ATTACK_RESPONSE = 301
    DAMAGE_DEALT = 302
    PLAYER_DIED = 303
    PLAYER_KILLED = 304
    REINCARNATE = 305
    COMBAT_STATE = 306
    SKILL_USE = 307
    BUFF_APPLY = 308
    BUFF_REMOVE = 309

    # Territory Control (400-499)
    TERRITORY_INFO = 400
    TERRITORY_CLAIM = 401
    TERRITORY_DEFEND = 402
    TERRITORY_BUFF = 403
    TERRITORY_UPDATE = 404
    GUILD_TERRITORY = 405

    # Inventory & Items (500-599)
    INVENTORY_UPDATE = 500
    ITEM_PICKUP = 501
    ITEM_DROP = 502
    ITEM_USE = 503
    EQUIPMENT_UPDATE = 504
    TRADE_REQUEST = 505
    TRADE_UPDATE = 506

    # Chat & Social (600-699)
    CHAT_MESSAGE = 600
    WHISPER = 601
    GUILD_CHAT = 602
    WORLD_ANNOUNCEMENT = 603
    PLAYER_LIST = 604

    # Stats & Progression (700-799)
    LEVEL_UP = 700
    STAT_UPDATE = 701
    SKILL_LEARN = 702
    REINCARNATION_PERKS = 703
    ACHIEVEMENT_UNLOCK = 704

    # World State (800-899)
    NPC_SPAWN = 800
    NPC_DESPAWN = 801
    OBJECT_SPAWN = 802
    OBJECT_INTERACT = 803
    WEATHER_UPDATE = 804
    TIME_UPDATE = 805

    # Admin & System (900-999)
    ADMIN_COMMAND = 900
    SERVER_SHUTDOWN = 901
    KICK_PLAYER = 902
    BAN_PLAYER = 903
    ERROR_MESSAGE = 999


class GameMode(enum.IntEnum):
    """Player game modes"""
    HARDCORE_IRONMAN = 0
    ULTIMATE_HARDCORE_IRONMAN = 1


class CombatState(enum.IntEnum):
    """Combat states"""
    IDLE = 0
    IN_COMBAT = 1
    DEAD = 2
    REINCARNATING = 3


class TerritoryState(enum.IntEnum):
    """Territory control states"""
    NEUTRAL = 0
    CONTESTED = 1
    CONTROLLED = 2


@dataclass
class Packet:
    """Base packet structure"""
    packet_type: PacketType
    payload: bytes = b''
    compressed: bool = False
    encrypted: bool = False
    sequence: int = 0

    HEADER_FORMAT = '!HIHBB'  # Type(2), Length(4), Sequence(4), Flags(1), Checksum(1)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_PAYLOAD_SIZE = 65535

    def serialize(self) -> bytes:
        """Serialize packet to bytes"""
        payload = self.payload
        flags = 0

        # Compress if payload is large
        if len(payload) > 512 and not self.compressed:
            payload = zlib.compress(payload)
            self.compressed = True

        if self.compressed:
            flags |= 0x01
        if self.encrypted:
            flags |= 0x02

        # Calculate checksum
        checksum = self._calculate_checksum(payload)

        # Pack header
        header = struct.pack(
            self.HEADER_FORMAT,
            self.packet_type,
            len(payload),
            self.sequence,
            flags,
            checksum
        )

        return header + payload

    @classmethod
    def deserialize(cls, data: bytes) -> 'Packet':
        """Deserialize bytes to packet"""
        if len(data) < cls.HEADER_SIZE:
            raise ValueError("Insufficient data for packet header")

        # Unpack header
        packet_type, payload_length, sequence, flags, checksum = struct.unpack(
            cls.HEADER_FORMAT,
            data[:cls.HEADER_SIZE]
        )

        # Extract payload
        if len(data) < cls.HEADER_SIZE + payload_length:
            raise ValueError("Insufficient data for packet payload")

        payload = data[cls.HEADER_SIZE:cls.HEADER_SIZE + payload_length]

        # Verify checksum
        if cls._calculate_checksum(payload) != checksum:
            raise ValueError("Packet checksum mismatch")

        # Decompress if needed
        compressed = bool(flags & 0x01)
        if compressed:
            payload = zlib.decompress(payload)

        return cls(
            packet_type=PacketType(packet_type),
            payload=payload,
            compressed=compressed,
            encrypted=bool(flags & 0x02),
            sequence=sequence
        )

    @staticmethod
    def _calculate_checksum(data: bytes) -> int:
        """Calculate simple checksum for packet validation"""
        return sum(data) & 0xFF

    def pack_string(self, s: str) -> bytes:
        """Pack a string with length prefix"""
        encoded = s.encode('utf-8')
        return struct.pack('!H', len(encoded)) + encoded

    @staticmethod
    def unpack_string(data: bytes, offset: int = 0) -> Tuple[str, int]:
        """Unpack a length-prefixed string"""
        length = struct.unpack('!H', data[offset:offset+2])[0]
        string = data[offset+2:offset+2+length].decode('utf-8')
        return string, offset + 2 + length

    def pack_json(self, obj: Any) -> bytes:
        """Pack a JSON-serializable object"""
        json_str = json.dumps(obj)
        return self.pack_string(json_str)

    @staticmethod
    def unpack_json(data: bytes, offset: int = 0) -> Tuple[Any, int]:
        """Unpack a JSON object"""
        json_str, new_offset = Packet.unpack_string(data, offset)
        return json.loads(json_str), new_offset


class PacketBuilder:
    """Helper class for building packets with payloads"""

    @staticmethod
    def login_request(username: str, password_hash: str, version: str) -> Packet:
        """Build login request packet"""
        payload = b''
        payload += struct.pack('!H', len(username.encode('utf-8'))) + username.encode('utf-8')
        payload += struct.pack('!H', len(password_hash.encode('utf-8'))) + password_hash.encode('utf-8')
        payload += struct.pack('!H', len(version.encode('utf-8'))) + version.encode('utf-8')

        return Packet(PacketType.LOGIN_REQUEST, payload)

    @staticmethod
    def login_response(success: bool, message: str, session_token: str = "") -> Packet:
        """Build login response packet"""
        payload = struct.pack('!?', success)
        payload += struct.pack('!H', len(message.encode('utf-8'))) + message.encode('utf-8')
        if success:
            payload += struct.pack('!H', len(session_token.encode('utf-8'))) + session_token.encode('utf-8')

        return Packet(PacketType.LOGIN_RESPONSE, payload)

    @staticmethod
    def character_info(char_data: Dict[str, Any]) -> Packet:
        """Build character info packet"""
        json_payload = json.dumps(char_data).encode('utf-8')
        return Packet(PacketType.CHARACTER_INFO, json_payload)

    @staticmethod
    def move_update(entity_id: int, x: float, y: float, z: float,
                   rotation: float, velocity_x: float, velocity_y: float, velocity_z: float) -> Packet:
        """Build movement update packet"""
        payload = struct.pack('!Iffffff', entity_id, x, y, z, rotation, velocity_x, velocity_y, velocity_z)
        return Packet(PacketType.MOVE_UPDATE, payload)

    @staticmethod
    def attack_request(target_id: int, skill_id: int) -> Packet:
        """Build attack request packet"""
        payload = struct.pack('!II', target_id, skill_id)
        return Packet(PacketType.ATTACK_REQUEST, payload)

    @staticmethod
    def damage_dealt(attacker_id: int, target_id: int, damage: int,
                    is_critical: bool, is_fatal: bool) -> Packet:
        """Build damage dealt packet"""
        payload = struct.pack('!III??', attacker_id, target_id, damage, is_critical, is_fatal)
        return Packet(PacketType.DAMAGE_DEALT, payload)

    @staticmethod
    def player_died(player_id: int, killer_id: int, reincarnation_score: int) -> Packet:
        """Build player death packet"""
        payload = struct.pack('!III', player_id, killer_id, reincarnation_score)
        return Packet(PacketType.PLAYER_DIED, payload)

    @staticmethod
    def reincarnate(player_id: int, perks: List[Dict[str, Any]]) -> Packet:
        """Build reincarnation packet"""
        payload = struct.pack('!I', player_id)
        perks_json = json.dumps(perks).encode('utf-8')
        payload += struct.pack('!H', len(perks_json)) + perks_json
        return Packet(PacketType.REINCARNATE, payload)

    @staticmethod
    def territory_update(territory_id: int, owner_guild_id: int, state: TerritoryState,
                        buffs: List[Dict[str, Any]]) -> Packet:
        """Build territory update packet"""
        payload = struct.pack('!IIB', territory_id, owner_guild_id, state)
        buffs_json = json.dumps(buffs).encode('utf-8')
        payload += struct.pack('!H', len(buffs_json)) + buffs_json
        return Packet(PacketType.TERRITORY_UPDATE, payload)

    @staticmethod
    def chat_message(sender: str, message: str, channel: str = "global") -> Packet:
        """Build chat message packet"""
        payload = b''
        payload += struct.pack('!H', len(channel.encode('utf-8'))) + channel.encode('utf-8')
        payload += struct.pack('!H', len(sender.encode('utf-8'))) + sender.encode('utf-8')
        payload += struct.pack('!H', len(message.encode('utf-8'))) + message.encode('utf-8')
        return Packet(PacketType.CHAT_MESSAGE, payload)

    @staticmethod
    def stat_update(stats: Dict[str, Any]) -> Packet:
        """Build stat update packet"""
        json_payload = json.dumps(stats).encode('utf-8')
        return Packet(PacketType.STAT_UPDATE, json_payload)

    @staticmethod
    def error_message(error_code: int, message: str) -> Packet:
        """Build error message packet"""
        payload = struct.pack('!I', error_code)
        payload += struct.pack('!H', len(message.encode('utf-8'))) + message.encode('utf-8')
        return Packet(PacketType.ERROR_MESSAGE, payload)


class PacketParser:
    """Helper class for parsing packet payloads"""

    @staticmethod
    def parse_login_request(packet: Packet) -> Tuple[str, str, str]:
        """Parse login request packet"""
        offset = 0
        username, offset = Packet.unpack_string(packet.payload, offset)
        password_hash, offset = Packet.unpack_string(packet.payload, offset)
        version, offset = Packet.unpack_string(packet.payload, offset)
        return username, password_hash, version

    @staticmethod
    def parse_login_response(packet: Packet) -> Tuple[bool, str, Optional[str]]:
        """Parse login response packet"""
        success = struct.unpack('!?', packet.payload[0:1])[0]
        offset = 1
        message, offset = Packet.unpack_string(packet.payload, offset)
        session_token = None
        if success and offset < len(packet.payload):
            session_token, _ = Packet.unpack_string(packet.payload, offset)
        return success, message, session_token

    @staticmethod
    def parse_move_update(packet: Packet) -> Dict[str, Any]:
        """Parse movement update packet"""
        entity_id, x, y, z, rotation, vx, vy, vz = struct.unpack('!Ifffffff', packet.payload)
        return {
            'entity_id': entity_id,
            'position': {'x': x, 'y': y, 'z': z},
            'rotation': rotation,
            'velocity': {'x': vx, 'y': vy, 'z': vz}
        }

    @staticmethod
    def parse_attack_request(packet: Packet) -> Tuple[int, int]:
        """Parse attack request packet"""
        target_id, skill_id = struct.unpack('!II', packet.payload)
        return target_id, skill_id

    @staticmethod
    def parse_damage_dealt(packet: Packet) -> Dict[str, Any]:
        """Parse damage dealt packet"""
        attacker_id, target_id, damage, is_critical, is_fatal = struct.unpack('!III??', packet.payload)
        return {
            'attacker_id': attacker_id,
            'target_id': target_id,
            'damage': damage,
            'is_critical': is_critical,
            'is_fatal': is_fatal
        }

    @staticmethod
    def parse_chat_message(packet: Packet) -> Dict[str, str]:
        """Parse chat message packet"""
        offset = 0
        channel, offset = Packet.unpack_string(packet.payload, offset)
        sender, offset = Packet.unpack_string(packet.payload, offset)
        message, _ = Packet.unpack_string(packet.payload, offset)
        return {'channel': channel, 'sender': sender, 'message': message}

    @staticmethod
    def parse_json_payload(packet: Packet) -> Dict[str, Any]:
        """Parse JSON payload packet"""
        return json.loads(packet.payload.decode('utf-8'))
