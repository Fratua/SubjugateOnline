"""
Game entities: Players, NPCs, and objects in the game world
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import time
import logging

from subjugate_online.shared.utils import calculate_damage, calculate_distance_3d, is_in_territory

logger = logging.getLogger(__name__)


@dataclass
class Vector3:
    """3D vector for position and velocity"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {'x': self.x, 'y': self.y, 'z': self.z}

    def distance_to(self, other: 'Vector3') -> float:
        """Calculate distance to another vector"""
        return calculate_distance_3d(self.to_dict(), other.to_dict())


@dataclass
class Stats:
    """Character stats"""
    level: int = 1
    experience: int = 0
    health: int = 100
    max_health: int = 100
    mana: int = 50
    max_mana: int = 50
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    vitality: int = 10
    attack_power: int = 10
    defense: int = 5
    magic_power: int = 5
    magic_defense: int = 5

    # Multipliers from perks
    experience_multiplier: float = 1.0
    damage_multiplier: float = 1.0
    defense_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'level': self.level,
            'experience': self.experience,
            'health': self.health,
            'max_health': self.max_health,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'strength': self.strength,
            'dexterity': self.dexterity,
            'intelligence': self.intelligence,
            'vitality': self.vitality,
            'attack_power': self.attack_power,
            'defense': self.defense,
            'magic_power': self.magic_power,
            'magic_defense': self.magic_defense
        }


class Entity:
    """Base entity class"""

    def __init__(self, entity_id: int, name: str, position: Vector3):
        self.entity_id = entity_id
        self.name = name
        self.position = position
        self.rotation = 0.0
        self.velocity = Vector3()
        self.zone = "spawn_zone"
        self.is_alive = True
        self.last_update = time.time()

    def update(self, delta_time: float):
        """Update entity state"""
        # Update position based on velocity
        self.position.x += self.velocity.x * delta_time
        self.position.y += self.velocity.y * delta_time
        self.position.z += self.velocity.z * delta_time
        self.last_update = time.time()

    def distance_to(self, other: 'Entity') -> float:
        """Calculate distance to another entity"""
        return self.position.distance_to(other.position)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'entity_id': self.entity_id,
            'name': self.name,
            'position': self.position.to_dict(),
            'rotation': self.rotation,
            'velocity': self.velocity.to_dict(),
            'zone': self.zone,
            'is_alive': self.is_alive
        }


class Player(Entity):
    """Player entity"""

    def __init__(self, entity_id: int, character_id: int, account_id: int, name: str,
                 position: Vector3, stats: Stats, game_mode: str):
        super().__init__(entity_id, name, position)
        self.character_id = character_id
        self.account_id = account_id
        self.stats = stats
        self.game_mode = game_mode

        # Combat state
        self.is_in_combat = False
        self.combat_start_time = 0.0
        self.last_attack_time = 0.0
        self.attack_cooldown = 1.0  # seconds
        self.target_id: Optional[int] = None
        self.current_killstreak = 0

        # Inventory
        self.inventory: List[Dict[str, Any]] = []
        self.equipment: Dict[str, Any] = {}
        self.skills: Dict[str, int] = {}

        # Reincarnation
        self.reincarnation_count = 0
        self.reincarnation_perks: List[Dict[str, Any]] = []
        self.lifetime_kills = 0
        self.lifetime_deaths = 0
        self.lifetime_damage_dealt = 0
        self.lifetime_damage_taken = 0
        self.territory_captures = 0

        # Guild
        self.guild_id: Optional[int] = None

        # Active buffs
        self.active_buffs: List[Dict[str, Any]] = []

        # Session tracking
        self.session_id: Optional[str] = None
        self.login_time = time.time()
        self.last_activity = time.time()

    def take_damage(self, damage: int, attacker_id: int) -> bool:
        """
        Take damage from an attack
        Returns True if player died
        """
        self.stats.health -= damage
        self.lifetime_damage_taken += damage
        self.is_in_combat = True
        self.combat_start_time = time.time()

        if self.stats.health <= 0:
            self.stats.health = 0
            self.is_alive = False
            self.is_in_combat = False
            self.current_killstreak = 0
            return True

        return False

    def can_attack(self) -> bool:
        """Check if player can perform an attack"""
        return time.time() - self.last_attack_time >= self.attack_cooldown

    def perform_attack(self, target: 'Player', skill_id: int = 0) -> Dict[str, Any]:
        """
        Perform an attack on a target
        Returns damage info dict
        """
        if not self.can_attack():
            return {'success': False, 'reason': 'On cooldown'}

        if not target.is_alive:
            return {'success': False, 'reason': 'Target is dead'}

        # Calculate damage
        skill_multiplier = 1.0  # TODO: Load from skill data
        damage_result = calculate_damage(
            self.stats.to_dict(),
            target.stats.to_dict(),
            skill_multiplier
        )

        # Apply damage multipliers from perks
        damage = int(damage_result['damage'] * self.stats.damage_multiplier)

        # Apply damage to target
        target_died = target.take_damage(damage, self.entity_id)

        # Update attacker state
        self.last_attack_time = time.time()
        self.is_in_combat = True
        self.combat_start_time = time.time()
        self.lifetime_damage_dealt += damage
        self.target_id = target.entity_id

        if target_died:
            self.lifetime_kills += 1
            self.current_killstreak += 1

        return {
            'success': True,
            'damage': damage,
            'is_critical': damage_result['is_critical'],
            'target_died': target_died,
            'target_health': target.stats.health
        }

    def heal(self, amount: int):
        """Heal the player"""
        self.stats.health = min(self.stats.health + amount, self.stats.max_health)

    def gain_experience(self, amount: int):
        """Gain experience points"""
        # Apply experience multiplier from perks
        amount = int(amount * self.stats.experience_multiplier)
        self.stats.experience += amount

        # Check for level up
        exp_needed = self._calculate_exp_for_next_level()
        if self.stats.experience >= exp_needed:
            self.level_up()

    def _calculate_exp_for_next_level(self) -> int:
        """Calculate experience needed for next level"""
        return (self.stats.level * self.stats.level) * 100

    def level_up(self):
        """Level up the character"""
        self.stats.level += 1

        # Increase stats
        self.stats.max_health += 10
        self.stats.max_mana += 5
        self.stats.strength += 1
        self.stats.dexterity += 1
        self.stats.intelligence += 1
        self.stats.vitality += 1

        # Recalculate derived stats
        self.stats.attack_power = 10 + self.stats.strength * 2 + self.stats.dexterity
        self.stats.defense = 5 + self.stats.vitality
        self.stats.magic_power = 5 + self.stats.intelligence * 2
        self.stats.magic_defense = 5 + self.stats.intelligence

        # Full heal on level up
        self.stats.health = self.stats.max_health
        self.stats.mana = self.stats.max_mana

        logger.info(f"Player {self.name} leveled up to {self.stats.level}")

    def apply_buff(self, buff: Dict[str, Any]):
        """Apply a buff to the player"""
        self.active_buffs.append(buff)
        logger.debug(f"Applied buff {buff['type']} to {self.name}")

    def remove_buff(self, buff_type: str):
        """Remove a buff from the player"""
        self.active_buffs = [b for b in self.active_buffs if b['type'] != buff_type]
        logger.debug(f"Removed buff {buff_type} from {self.name}")

    def update(self, delta_time: float):
        """Update player state"""
        super().update(delta_time)

        # Exit combat if no activity for 10 seconds
        if self.is_in_combat and time.time() - self.combat_start_time > 10.0:
            self.is_in_combat = False
            self.target_id = None

        # Health regeneration (1% per second when not in combat)
        if not self.is_in_combat and self.stats.health < self.stats.max_health:
            regen = max(1, int(self.stats.max_health * 0.01 * delta_time))
            self.heal(regen)

        # Mana regeneration (2% per second)
        if self.stats.mana < self.stats.max_mana:
            regen = max(1, int(self.stats.max_mana * 0.02 * delta_time))
            self.stats.mana = min(self.stats.mana + regen, self.stats.max_mana)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'character_id': self.character_id,
            'account_id': self.account_id,
            'stats': self.stats.to_dict(),
            'game_mode': self.game_mode,
            'is_in_combat': self.is_in_combat,
            'current_killstreak': self.current_killstreak,
            'reincarnation_count': self.reincarnation_count,
            'reincarnation_perks': self.reincarnation_perks,
            'guild_id': self.guild_id,
            'active_buffs': self.active_buffs
        })
        return base


class NPC(Entity):
    """NPC entity"""

    def __init__(self, entity_id: int, name: str, position: Vector3, npc_type: str, level: int):
        super().__init__(entity_id, name, position)
        self.npc_type = npc_type
        self.level = level
        self.health = 100 * level
        self.max_health = 100 * level
        self.aggro_range = 10.0
        self.target_id: Optional[int] = None
        self.spawn_position = Vector3(position.x, position.y, position.z)
        self.respawn_time = 60.0  # seconds

    def take_damage(self, damage: int, attacker_id: int) -> bool:
        """Take damage, returns True if NPC died"""
        self.health -= damage
        self.target_id = attacker_id

        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True

        return False

    def reset(self):
        """Reset NPC to spawn state"""
        self.health = self.max_health
        self.is_alive = True
        self.position = Vector3(self.spawn_position.x, self.spawn_position.y, self.spawn_position.z)
        self.target_id = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        base = super().to_dict()
        base.update({
            'npc_type': self.npc_type,
            'level': self.level,
            'health': self.health,
            'max_health': self.max_health
        })
        return base
