"""
Subjugate Online - Combat System
Handles all combat mechanics including attacks, skills, and damage calculation
"""

import time
import random
from typing import Optional, Dict, Any
from shared.constants import (
    ATTACK_COOLDOWN, ATTACK_RANGE_MELEE, DamageType, SkillType
)
from shared.utils import calculate_damage, calculate_distance, Logger
from shared.game_data import SKILL_DATABASE, get_skill_data
from server.game_server.world_manager import PlayerEntity, NPCEntity

logger = Logger.get_logger(__name__)


class CombatSystem:
    """Manages combat interactions"""

    def __init__(self, world_manager):
        self.world = world_manager
        self.active_cooldowns: Dict[int, Dict[int, float]] = {}  # {character_id: {skill_id: end_time}}

    def basic_attack(self, attacker_id: int, target_id: int, target_type: str) -> Optional[Dict[str, Any]]:
        """
        Execute a basic attack

        Args:
            attacker_id: Attacking player ID
            target_id: Target ID
            target_type: 'player' or 'npc'

        Returns:
            Combat result dict or None if invalid
        """
        attacker = self.world.get_player(attacker_id)
        if not attacker or attacker.is_dead:
            return None

        # Check attack cooldown
        current_time = time.time()
        if not attacker.can_attack(current_time, ATTACK_COOLDOWN):
            return None

        # Get target
        if target_type == 'player':
            target = self.world.get_player(target_id)
        elif target_type == 'npc':
            target = self.world.get_npc(target_id)
        else:
            return None

        if not target:
            return None

        # Check range
        distance = calculate_distance(attacker.position, target.position)
        if distance > ATTACK_RANGE_MELEE:
            return None

        # Calculate damage
        attacker_stats = {
            'attack': attacker.attack,
            'level': attacker.level
        }

        target_stats = {
            'defense': target.defense if hasattr(target, 'defense') else 0,
            'level': target.level if hasattr(target, 'level') else 1
        }

        damage = calculate_damage(attacker_stats, target_stats, 1.0, DamageType.PHYSICAL)

        # Apply damage
        target_died = target.apply_damage(damage)

        # Update attacker's last attack time
        attacker.last_attack_time = current_time

        # Build result
        result = {
            'attacker_id': attacker_id,
            'target_id': target_id,
            'target_type': target_type,
            'damage': damage,
            'target_hp': target.hp,
            'target_died': target_died
        }

        logger.debug(f"Basic attack: {attacker.name} -> Target {target_id}, damage={damage}, died={target_died}")

        return result

    def use_skill(self, caster_id: int, skill_id: int, target_id: Optional[int] = None,
                  target_type: str = 'npc') -> Optional[Dict[str, Any]]:
        """
        Use a skill

        Args:
            caster_id: Caster player ID
            skill_id: Skill ID
            target_id: Target ID (optional for AoE/self-cast)
            target_type: 'player' or 'npc'

        Returns:
            Skill result dict or None if invalid
        """
        caster = self.world.get_player(caster_id)
        if not caster or caster.is_dead:
            return None

        # Get skill data
        skill_data = get_skill_data(skill_id)
        if not skill_data:
            return None

        # Check MP cost
        mp_cost = skill_data.get('mp_cost', 0)
        if caster.mp < mp_cost:
            return None

        # Check cooldown
        current_time = time.time()
        if not self._check_skill_cooldown(caster_id, skill_id, current_time):
            return None

        # Check required level
        required_level = skill_data.get('required_level', 1)
        if caster.level < required_level:
            return None

        # Consume MP
        caster.mp -= mp_cost

        # Set cooldown
        self._set_skill_cooldown(caster_id, skill_id, current_time, skill_data.get('cooldown', 0))

        # Handle healing skills
        if skill_id == SkillType.HEAL:
            heal_amount = skill_data.get('heal_amount', 100)
            caster.heal(heal_amount)
            return {
                'caster_id': caster_id,
                'skill_id': skill_id,
                'heal_amount': heal_amount,
                'caster_hp': caster.hp
            }

        # Handle damage skills
        if target_id is None:
            return None

        # Get target
        if target_type == 'player':
            target = self.world.get_player(target_id)
        elif target_type == 'npc':
            target = self.world.get_npc(target_id)
        else:
            return None

        if not target:
            return None

        # Check range
        skill_range = skill_data.get('range', ATTACK_RANGE_MELEE)
        distance = calculate_distance(caster.position, target.position)
        if distance > skill_range:
            return None

        # Calculate damage
        damage_multiplier = skill_data.get('damage_multiplier', 1.0)
        damage_type = skill_data.get('damage_type', DamageType.PHYSICAL)

        caster_stats = {
            'attack': caster.attack,
            'level': caster.level
        }

        target_stats = {
            'defense': target.defense if hasattr(target, 'defense') else 0,
            'level': target.level if hasattr(target, 'level') else 1
        }

        damage = calculate_damage(caster_stats, target_stats, damage_multiplier, damage_type)

        # Apply damage
        target_died = target.apply_damage(damage)

        # Handle AoE
        targets_hit = [(target_id, damage, target.hp, target_died)]

        aoe_radius = skill_data.get('aoe_radius', 0)
        if aoe_radius > 0:
            # Find nearby enemies
            nearby_npcs = self.world.get_nearby_npcs(target.position, aoe_radius)
            for npc in nearby_npcs:
                if npc.instance_id != target_id:
                    aoe_damage = int(damage * 0.7)  # 70% damage to secondary targets
                    died = npc.apply_damage(aoe_damage)
                    targets_hit.append((npc.instance_id, aoe_damage, npc.hp, died))

        result = {
            'caster_id': caster_id,
            'skill_id': skill_id,
            'skill_name': skill_data.get('name', 'Unknown'),
            'targets_hit': targets_hit,
            'caster_mp': caster.mp
        }

        logger.debug(f"Skill used: {caster.name} used {skill_data.get('name')}, targets={len(targets_hit)}")

        return result

    def _check_skill_cooldown(self, character_id: int, skill_id: int, current_time: float) -> bool:
        """Check if skill is off cooldown"""
        if character_id not in self.active_cooldowns:
            return True

        cooldown_end = self.active_cooldowns[character_id].get(skill_id, 0)
        return current_time >= cooldown_end

    def _set_skill_cooldown(self, character_id: int, skill_id: int, current_time: float, cooldown: float):
        """Set skill cooldown"""
        if character_id not in self.active_cooldowns:
            self.active_cooldowns[character_id] = {}

        self.active_cooldowns[character_id][skill_id] = current_time + cooldown

    def handle_player_death(self, character_id: int, killer_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Handle player death

        Returns:
            Death event data
        """
        player = self.world.get_player(character_id)
        if not player:
            return {}

        player.is_dead = True
        player.hp = 0

        logger.info(f"Player died: {player.name} (Killer ID: {killer_id})")

        return {
            'character_id': character_id,
            'killer_id': killer_id,
            'was_pvp': killer_id is not None
        }

    def respawn_player(self, character_id: int, spawn_position: tuple) -> bool:
        """
        Respawn a dead player

        Args:
            character_id: Player to respawn
            spawn_position: Position to spawn at

        Returns:
            True if successful
        """
        player = self.world.get_player(character_id)
        if not player:
            return False

        player.is_dead = False
        player.hp = player.max_hp
        player.mp = player.max_mp

        # Move to spawn position
        self.world.update_player_position(
            character_id,
            spawn_position[0],
            spawn_position[1],
            spawn_position[2],
            0.0
        )

        logger.info(f"Player respawned: {player.name}")

        return True

    def grant_experience(self, character_id: int, xp_amount: int) -> Optional[Dict[str, Any]]:
        """
        Grant experience to a player

        Returns:
            Level up data if player leveled, else None
        """
        from shared.utils import calculate_xp_for_level

        player = self.world.get_player(character_id)
        if not player:
            return None

        # Apply XP multiplier from reincarnation perks
        xp_multiplier = player.reincarnation_perks.get('xp_multiplier', 0)
        final_xp = int(xp_amount * (1.0 + xp_multiplier))

        # This would be updated in database in real implementation
        # For now just track in memory

        logger.debug(f"XP granted: {player.name} gained {final_xp} XP")

        # Check for level up (simplified)
        # In full implementation, this would check against character's current XP
        # and grant level-up stats

        return None
