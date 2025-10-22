"""
Subjugate Online - World Manager
Manages world state, spatial partitioning, and entity tracking
"""

import time
from typing import Dict, List, Set, Tuple, Optional
from shared.constants import CHUNK_SIZE, VIEW_DISTANCE, WORLD_SIZE
from shared.utils import get_chunk_id, get_surrounding_chunks, calculate_distance, Logger

logger = Logger.get_logger(__name__)


class Entity:
    """Base entity class"""

    def __init__(self, entity_id: int, entity_type: str, position: Tuple[float, float, float]):
        self.id = entity_id
        self.type = entity_type  # 'player', 'npc', etc.
        self.position = position
        self.rotation = 0.0
        self.chunk_id = get_chunk_id(position, CHUNK_SIZE)
        self.last_update = time.time()

    def update_position(self, x: float, y: float, z: float, rotation: float):
        """Update entity position"""
        self.position = (x, y, z)
        self.rotation = rotation
        self.chunk_id = get_chunk_id(self.position, CHUNK_SIZE)
        self.last_update = time.time()

    def get_position(self) -> Tuple[float, float, float]:
        """Get entity position"""
        return self.position


class PlayerEntity(Entity):
    """Player entity with additional data"""

    def __init__(self, character_id: int, character_data: dict):
        position = (
            character_data.get('position_x', 100.0),
            character_data.get('position_y', 0.0),
            character_data.get('position_z', 100.0)
        )
        super().__init__(character_id, 'player', position)

        self.character_id = character_id
        self.name = character_data.get('name', 'Unknown')
        self.level = character_data.get('level', 1)
        self.hp = character_data.get('hp', 100)
        self.max_hp = character_data.get('max_hp', 100)
        self.mp = character_data.get('mp', 50)
        self.max_mp = character_data.get('max_mp', 50)
        self.attack = character_data.get('attack', 10)
        self.defense = character_data.get('defense', 10)
        self.speed = character_data.get('speed', 5.0)
        self.game_mode = character_data.get('game_mode', 0)
        self.reincarnation_count = character_data.get('reincarnation_count', 0)
        self.reincarnation_perks = character_data.get('reincarnation_perks', {})

        # Combat state
        self.is_dead = False
        self.target_id = None
        self.last_attack_time = 0.0
        self.active_buffs = {}

        # Movement
        self.velocity = (0.0, 0.0, 0.0)

    def get_stats(self) -> dict:
        """Get player stats"""
        return {
            'character_id': self.character_id,
            'name': self.name,
            'level': self.level,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'mp': self.mp,
            'max_mp': self.max_mp,
            'attack': self.attack,
            'defense': self.defense,
            'speed': self.speed,
            'position': list(self.position),
            'rotation': self.rotation
        }

    def apply_damage(self, damage: int) -> bool:
        """
        Apply damage to player

        Returns:
            True if player died
        """
        self.hp = max(0, self.hp - damage)
        if self.hp == 0:
            self.is_dead = True
            return True
        return False

    def heal(self, amount: int):
        """Heal player"""
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_mp(self, amount: int):
        """Restore MP"""
        self.mp = min(self.max_mp, self.mp + amount)

    def can_attack(self, current_time: float, cooldown: float) -> bool:
        """Check if player can attack"""
        return (current_time - self.last_attack_time) >= cooldown


class NPCEntity(Entity):
    """NPC entity"""

    def __init__(self, instance_id: int, npc_data: dict, position: Tuple[float, float, float]):
        super().__init__(instance_id, 'npc', position)

        self.instance_id = instance_id
        self.npc_id = npc_data.get('id', 0)
        self.name = npc_data.get('name', 'NPC')
        self.npc_type = npc_data.get('type', 0)
        self.level = npc_data.get('level', 1)
        self.hp = npc_data.get('hp', 100)
        self.max_hp = npc_data.get('hp', 100)
        self.attack = npc_data.get('attack', 10)
        self.defense = npc_data.get('defense', 5)
        self.xp_reward = npc_data.get('xp_reward', 10)
        self.loot_table = npc_data.get('loot_table', [])
        self.aggro_range = npc_data.get('aggro_range', 5.0)
        self.skills = npc_data.get('skills', [])

        # AI state
        self.state = 'idle'  # idle, patrolling, chasing, attacking
        self.target_id = None
        self.spawn_position = position
        self.last_attack_time = 0.0

    def get_data(self) -> dict:
        """Get NPC data"""
        return {
            'instance_id': self.instance_id,
            'npc_id': self.npc_id,
            'name': self.name,
            'level': self.level,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'position': list(self.position),
            'rotation': self.rotation,
            'state': self.state
        }

    def apply_damage(self, damage: int) -> bool:
        """
        Apply damage to NPC

        Returns:
            True if NPC died
        """
        self.hp = max(0, self.hp - damage)
        return self.hp == 0


class WorldManager:
    """Manages world state and entity tracking with spatial partitioning"""

    def __init__(self):
        self.players: Dict[int, PlayerEntity] = {}
        self.npcs: Dict[int, NPCEntity] = {}

        # Spatial partitioning - chunk-based
        self.player_chunks: Dict[Tuple[int, int], Set[int]] = {}
        self.npc_chunks: Dict[Tuple[int, int], Set[int]] = {}

        self.next_npc_instance_id = 1

        logger.info("WorldManager initialized")

    # ========================================================================
    # PLAYER MANAGEMENT
    # ========================================================================

    def add_player(self, character_id: int, character_data: dict) -> PlayerEntity:
        """Add a player to the world"""
        player = PlayerEntity(character_id, character_data)
        self.players[character_id] = player

        # Add to spatial partition
        self._add_to_chunk(player.chunk_id, character_id, self.player_chunks)

        logger.info(f"Player added to world: {player.name} (ID: {character_id})")
        return player

    def remove_player(self, character_id: int):
        """Remove a player from the world"""
        player = self.players.get(character_id)
        if player:
            # Remove from spatial partition
            self._remove_from_chunk(player.chunk_id, character_id, self.player_chunks)

            del self.players[character_id]
            logger.info(f"Player removed from world: {player.name} (ID: {character_id})")

    def get_player(self, character_id: int) -> Optional[PlayerEntity]:
        """Get a player by ID"""
        return self.players.get(character_id)

    def update_player_position(self, character_id: int, x: float, y: float, z: float, rotation: float):
        """Update player position"""
        player = self.players.get(character_id)
        if player:
            old_chunk = player.chunk_id

            player.update_position(x, y, z, rotation)

            # Update chunk if changed
            if player.chunk_id != old_chunk:
                self._remove_from_chunk(old_chunk, character_id, self.player_chunks)
                self._add_to_chunk(player.chunk_id, character_id, self.player_chunks)

    def get_nearby_players(self, position: Tuple[float, float, float], radius: float) -> List[PlayerEntity]:
        """Get all players within radius of a position"""
        chunk_id = get_chunk_id(position, CHUNK_SIZE)
        search_radius = int(radius / CHUNK_SIZE) + 1
        nearby_chunks = get_surrounding_chunks(chunk_id, search_radius)

        nearby_players = []

        for chunk in nearby_chunks:
            player_ids = self.player_chunks.get(chunk, set())
            for player_id in player_ids:
                player = self.players.get(player_id)
                if player:
                    distance = calculate_distance(position, player.position)
                    if distance <= radius:
                        nearby_players.append(player)

        return nearby_players

    def get_visible_players(self, character_id: int) -> List[PlayerEntity]:
        """Get all players visible to a character"""
        player = self.players.get(character_id)
        if not player:
            return []

        return self.get_nearby_players(player.position, VIEW_DISTANCE)

    # ========================================================================
    # NPC MANAGEMENT
    # ========================================================================

    def spawn_npc(self, npc_data: dict, position: Tuple[float, float, float]) -> NPCEntity:
        """Spawn an NPC in the world"""
        instance_id = self.next_npc_instance_id
        self.next_npc_instance_id += 1

        npc = NPCEntity(instance_id, npc_data, position)
        self.npcs[instance_id] = npc

        # Add to spatial partition
        self._add_to_chunk(npc.chunk_id, instance_id, self.npc_chunks)

        logger.info(f"NPC spawned: {npc.name} (Instance ID: {instance_id})")
        return npc

    def remove_npc(self, instance_id: int):
        """Remove an NPC from the world"""
        npc = self.npcs.get(instance_id)
        if npc:
            # Remove from spatial partition
            self._remove_from_chunk(npc.chunk_id, instance_id, self.npc_chunks)

            del self.npcs[instance_id]
            logger.info(f"NPC removed: {npc.name} (Instance ID: {instance_id})")

    def get_npc(self, instance_id: int) -> Optional[NPCEntity]:
        """Get an NPC by instance ID"""
        return self.npcs.get(instance_id)

    def update_npc_position(self, instance_id: int, x: float, y: float, z: float, rotation: float):
        """Update NPC position"""
        npc = self.npcs.get(instance_id)
        if npc:
            old_chunk = npc.chunk_id

            npc.update_position(x, y, z, rotation)

            # Update chunk if changed
            if npc.chunk_id != old_chunk:
                self._remove_from_chunk(old_chunk, instance_id, self.npc_chunks)
                self._add_to_chunk(npc.chunk_id, instance_id, self.npc_chunks)

    def get_nearby_npcs(self, position: Tuple[float, float, float], radius: float) -> List[NPCEntity]:
        """Get all NPCs within radius of a position"""
        chunk_id = get_chunk_id(position, CHUNK_SIZE)
        search_radius = int(radius / CHUNK_SIZE) + 1
        nearby_chunks = get_surrounding_chunks(chunk_id, search_radius)

        nearby_npcs = []

        for chunk in nearby_chunks:
            npc_ids = self.npc_chunks.get(chunk, set())
            for npc_id in npc_ids:
                npc = self.npcs.get(npc_id)
                if npc:
                    distance = calculate_distance(position, npc.position)
                    if distance <= radius:
                        nearby_npcs.append(npc)

        return nearby_npcs

    def get_visible_npcs(self, character_id: int) -> List[NPCEntity]:
        """Get all NPCs visible to a character"""
        player = self.players.get(character_id)
        if not player:
            return []

        return self.get_nearby_npcs(player.position, VIEW_DISTANCE)

    # ========================================================================
    # SPATIAL PARTITIONING HELPERS
    # ========================================================================

    def _add_to_chunk(self, chunk_id: Tuple[int, int], entity_id: int, chunk_dict: dict):
        """Add entity to chunk"""
        if chunk_id not in chunk_dict:
            chunk_dict[chunk_id] = set()
        chunk_dict[chunk_id].add(entity_id)

    def _remove_from_chunk(self, chunk_id: Tuple[int, int], entity_id: int, chunk_dict: dict):
        """Remove entity from chunk"""
        if chunk_id in chunk_dict:
            chunk_dict[chunk_id].discard(entity_id)
            if not chunk_dict[chunk_id]:
                del chunk_dict[chunk_id]

    # ========================================================================
    # UTILITY
    # ========================================================================

    def get_all_players(self) -> List[PlayerEntity]:
        """Get all players in the world"""
        return list(self.players.values())

    def get_all_npcs(self) -> List[NPCEntity]:
        """Get all NPCs in the world"""
        return list(self.npcs.values())

    def get_player_count(self) -> int:
        """Get total player count"""
        return len(self.players)

    def get_npc_count(self) -> int:
        """Get total NPC count"""
        return len(self.npcs)
