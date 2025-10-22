"""
Subjugate Online - NPC AI System
Handles NPC behavior, aggro, and combat
"""

import time
import random
from typing import Optional, Dict, List
from shared.utils import calculate_distance, normalize_vector, Logger
from shared.game_data import NPC_DATABASE, get_npc_data
from server.game_server.world_manager import NPCEntity, WorldManager

logger = Logger.get_logger(__name__)


class NPCAISystem:
    """Manages NPC AI behavior"""

    def __init__(self, world_manager: WorldManager):
        self.world = world_manager
        self.npc_attack_cooldown = 2.0  # NPC attack cooldown in seconds

    def update(self, delta_time: float):
        """
        Update all NPC AI

        Args:
            delta_time: Time since last update in seconds
        """
        current_time = time.time()

        for npc in self.world.get_all_npcs():
            self._update_npc_ai(npc, delta_time, current_time)

    def _update_npc_ai(self, npc: NPCEntity, delta_time: float, current_time: float):
        """Update individual NPC AI"""

        if npc.hp <= 0:
            # NPC is dead, don't update
            return

        # State machine
        if npc.state == 'idle':
            self._ai_idle(npc, current_time)

        elif npc.state == 'patrolling':
            self._ai_patrol(npc, delta_time)

        elif npc.state == 'chasing':
            self._ai_chase(npc, delta_time, current_time)

        elif npc.state == 'attacking':
            self._ai_attack(npc, current_time)

    def _ai_idle(self, npc: NPCEntity, current_time: float):
        """Idle state - look for targets or start patrolling"""

        # Check for nearby players
        nearby_players = self.world.get_nearby_players(npc.position, npc.aggro_range)

        if nearby_players:
            # Found a target, start chasing
            target = nearby_players[0]  # Target first player found
            npc.target_id = target.character_id
            npc.state = 'chasing'
            logger.debug(f"NPC {npc.name} (ID: {npc.instance_id}) aggroed {target.name}")
        else:
            # Randomly start patrolling
            if random.random() < 0.1:  # 10% chance per update
                npc.state = 'patrolling'

    def _ai_patrol(self, npc: NPCEntity, delta_time: float):
        """Patrol state - wander around spawn point"""

        # Check for nearby players
        nearby_players = self.world.get_nearby_players(npc.position, npc.aggro_range)

        if nearby_players:
            # Found a target, start chasing
            target = nearby_players[0]
            npc.target_id = target.character_id
            npc.state = 'chasing'
            return

        # Patrol logic - simple random walk around spawn point
        max_wander_distance = 20.0
        distance_from_spawn = calculate_distance(npc.position, npc.spawn_position)

        if distance_from_spawn > max_wander_distance:
            # Return to spawn
            direction = (
                npc.spawn_position[0] - npc.position[0],
                0,
                npc.spawn_position[2] - npc.position[2]
            )
        else:
            # Random direction
            direction = (
                random.uniform(-1, 1),
                0,
                random.uniform(-1, 1)
            )

        direction = normalize_vector(direction)

        # Move
        move_speed = 2.0
        new_x = npc.position[0] + direction[0] * move_speed * delta_time
        new_y = npc.position[1]
        new_z = npc.position[2] + direction[2] * move_speed * delta_time

        self.world.update_npc_position(npc.instance_id, new_x, new_y, new_z, 0.0)

        # Randomly go back to idle
        if random.random() < 0.05:  # 5% chance
            npc.state = 'idle'

    def _ai_chase(self, npc: NPCEntity, delta_time: float, current_time: float):
        """Chase state - pursue target"""

        if npc.target_id is None:
            npc.state = 'idle'
            return

        # Get target
        target = self.world.get_player(npc.target_id)

        if not target or target.is_dead:
            # Target lost or dead
            npc.target_id = None
            npc.state = 'idle'
            return

        # Calculate distance to target
        distance = calculate_distance(npc.position, target.position)

        # Check if too far from spawn (leash)
        distance_from_spawn = calculate_distance(npc.position, npc.spawn_position)
        max_leash_distance = 50.0

        if distance_from_spawn > max_leash_distance:
            # Too far, reset
            logger.debug(f"NPC {npc.name} leashed, returning to spawn")
            npc.target_id = None
            npc.state = 'idle'
            npc.hp = npc.max_hp  # Reset HP when leashing
            self.world.update_npc_position(
                npc.instance_id,
                npc.spawn_position[0],
                npc.spawn_position[1],
                npc.spawn_position[2],
                0.0
            )
            return

        # Check attack range
        attack_range = 2.5
        if distance <= attack_range:
            npc.state = 'attacking'
            return

        # Move toward target
        direction = (
            target.position[0] - npc.position[0],
            0,
            target.position[2] - npc.position[2]
        )

        direction = normalize_vector(direction)

        # NPC move speed (slightly slower than players)
        move_speed = 4.0
        new_x = npc.position[0] + direction[0] * move_speed * delta_time
        new_y = npc.position[1]
        new_z = npc.position[2] + direction[2] * move_speed * delta_time

        self.world.update_npc_position(npc.instance_id, new_x, new_y, new_z, 0.0)

    def _ai_attack(self, npc: NPCEntity, current_time: float):
        """Attack state - attack target"""

        if npc.target_id is None:
            npc.state = 'idle'
            return

        # Get target
        target = self.world.get_player(npc.target_id)

        if not target or target.is_dead:
            npc.target_id = None
            npc.state = 'idle'
            return

        # Check distance
        distance = calculate_distance(npc.position, target.position)
        attack_range = 2.5

        if distance > attack_range:
            # Target moved away, chase
            npc.state = 'chasing'
            return

        # Check attack cooldown
        if (current_time - npc.last_attack_time) < self.npc_attack_cooldown:
            return

        # Perform attack
        self._npc_attack_player(npc, target, current_time)

    def _npc_attack_player(self, npc: NPCEntity, target, current_time: float):
        """NPC attacks a player"""
        from shared.utils import calculate_damage
        from shared.constants import DamageType

        attacker_stats = {
            'attack': npc.attack,
            'level': npc.level
        }

        defender_stats = {
            'defense': target.defense,
            'level': target.level
        }

        damage = calculate_damage(attacker_stats, defender_stats, 1.0, DamageType.PHYSICAL)

        # Apply damage to player
        target.apply_damage(damage)

        npc.last_attack_time = current_time

        logger.debug(f"NPC {npc.name} attacked {target.name} for {damage} damage (HP: {target.hp}/{target.max_hp})")

    def spawn_npc(self, npc_id: int, position: tuple) -> Optional[NPCEntity]:
        """
        Spawn an NPC

        Args:
            npc_id: NPC ID from NPC_DATABASE
            position: Spawn position

        Returns:
            Spawned NPC entity or None
        """
        npc_data = get_npc_data(npc_id)
        if not npc_data:
            logger.error(f"Failed to spawn NPC: invalid ID {npc_id}")
            return None

        npc = self.world.spawn_npc(npc_data, position)
        return npc

    def spawn_initial_npcs(self):
        """Spawn initial NPCs in the world"""
        # Spawn some basic monsters around the world
        spawn_configs = [
            # Slimes in safe zone
            {'npc_id': 5001, 'count': 10, 'area': (50, 150, 50, 150)},

            # Wolves in mid-level area
            {'npc_id': 5002, 'count': 8, 'area': (200, 300, 200, 300)},

            # Orcs in dangerous area
            {'npc_id': 5003, 'count': 5, 'area': (400, 500, 400, 500)},

            # Boss: Dragon Lord
            {'npc_id': 6001, 'count': 1, 'area': (500, 510, 500, 510)},
        ]

        for config in spawn_configs:
            npc_id = config['npc_id']
            count = config['count']
            area = config['area']  # (min_x, max_x, min_z, max_z)

            for _ in range(count):
                x = random.uniform(area[0], area[1])
                z = random.uniform(area[2], area[3])
                position = (x, 0.0, z)

                self.spawn_npc(npc_id, position)

        logger.info(f"Spawned initial NPCs: {self.world.get_npc_count()} total")

    def handle_npc_death(self, npc_instance_id: int, killer_id: Optional[int] = None) -> Dict:
        """
        Handle NPC death

        Args:
            npc_instance_id: NPC instance ID
            killer_id: Player who killed the NPC

        Returns:
            Death event data including loot
        """
        npc = self.world.get_npc(npc_instance_id)
        if not npc:
            return {}

        # Generate loot
        loot = self._generate_loot(npc)

        # Remove NPC from world
        self.world.remove_npc(npc_instance_id)

        logger.info(f"NPC died: {npc.name} (Instance ID: {npc_instance_id}, Killer: {killer_id})")

        # Respawn after delay (simplified - in production would use a respawn timer)
        # For now, immediately respawn boss NPCs at their spawn location
        from shared.constants import NPCType
        if npc.npc_type == NPCType.BOSS:
            # Schedule respawn (would need a proper scheduler in production)
            pass

        return {
            'npc_instance_id': npc_instance_id,
            'npc_id': npc.npc_id,
            'npc_name': npc.name,
            'killer_id': killer_id,
            'xp_reward': npc.xp_reward,
            'loot': loot
        }

    def _generate_loot(self, npc: NPCEntity) -> List[int]:
        """
        Generate loot from an NPC

        Args:
            npc: NPC entity

        Returns:
            List of item IDs
        """
        loot = []

        # Each item in loot table has a chance to drop
        for item_id in npc.loot_table:
            drop_chance = 0.3  # 30% base drop chance
            if random.random() < drop_chance:
                loot.append(item_id)

        return loot
