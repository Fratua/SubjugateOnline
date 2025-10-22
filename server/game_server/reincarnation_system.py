"""
Subjugate Online - Reincarnation System
Handles character reincarnation and perk calculation
"""

from typing import Optional, Dict, Any
from shared.constants import (
    REINCARNATION_LEVEL_REQUIREMENT, MAX_REINCARNATIONS, ErrorCode
)
from shared.utils import calculate_success_score, calculate_reincarnation_perks, Logger
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class ReincarnationSystem:
    """Manages character reincarnation"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def can_reincarnate(self, character_id: int) -> tuple[bool, str]:
        """
        Check if a character can reincarnate

        Returns:
            (can_reincarnate, reason)
        """
        character = self.db.get_character_by_id(character_id)
        if not character:
            return False, "Character not found"

        # Check level requirement
        if character.level < REINCARNATION_LEVEL_REQUIREMENT:
            return False, f"Minimum level {REINCARNATION_LEVEL_REQUIREMENT} required"

        # Check max reincarnations
        if character.reincarnation_count >= MAX_REINCARNATIONS:
            return False, f"Maximum reincarnations ({MAX_REINCARNATIONS}) reached"

        return True, "Can reincarnate"

    def perform_reincarnation(self, character_id: int) -> Optional[Dict[str, Any]]:
        """
        Perform character reincarnation

        Returns:
            Reincarnation result with perks, or None if failed
        """
        # Check if can reincarnate
        can_reincarnate, reason = self.can_reincarnate(character_id)
        if not can_reincarnate:
            logger.warning(f"Reincarnation failed for character {character_id}: {reason}")
            return None

        character = self.db.get_character_by_id(character_id)
        if not character:
            return None

        # Calculate success score based on previous life
        character_data = {
            'level': character.level,
            'total_kills': character.total_kills,
            'boss_kills': character.boss_kills,
            'territory_control_time': character.territory_control_time,
            'playtime': character.playtime
        }

        success_score = calculate_success_score(character_data)

        # Calculate new perks
        new_reincarnation_count = character.reincarnation_count + 1
        new_perks = calculate_reincarnation_perks(new_reincarnation_count, success_score)

        # Merge with existing perks (perks stack)
        current_perks = character.reincarnation_perks
        merged_perks = {
            'hp_bonus': current_perks.get('hp_bonus', 0) + new_perks['hp_bonus'],
            'mp_bonus': current_perks.get('mp_bonus', 0) + new_perks['mp_bonus'],
            'attack_bonus': current_perks.get('attack_bonus', 0) + new_perks['attack_bonus'],
            'defense_bonus': current_perks.get('defense_bonus', 0) + new_perks['defense_bonus'],
            'speed_bonus': current_perks.get('speed_bonus', 0) + new_perks['speed_bonus'],
            'xp_multiplier': current_perks.get('xp_multiplier', 0) + new_perks['xp_multiplier']
        }

        # Perform reincarnation in database
        success = self.db.reincarnate_character(character_id, success_score, merged_perks)

        if not success:
            logger.error(f"Failed to reincarnate character {character_id} in database")
            return None

        logger.info(f"Character {character.name} reincarnated! Count: {new_reincarnation_count}, Score: {success_score:.2f}")

        return {
            'character_id': character_id,
            'reincarnation_count': new_reincarnation_count,
            'success_score': success_score,
            'new_perks': new_perks,
            'total_perks': merged_perks,
            'previous_level': character.level,
            'previous_stats': {
                'total_kills': character.total_kills,
                'boss_kills': character.boss_kills,
                'territory_time': character.territory_control_time,
                'playtime': character.playtime
            }
        }

    def get_reincarnation_preview(self, character_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a preview of reincarnation results without actually reincarnating

        Returns:
            Preview data or None if cannot reincarnate
        """
        can_reincarnate, reason = self.can_reincarnate(character_id)
        if not can_reincarnate:
            return None

        character = self.db.get_character_by_id(character_id)
        if not character:
            return None

        # Calculate success score
        character_data = {
            'level': character.level,
            'total_kills': character.total_kills,
            'boss_kills': character.boss_kills,
            'territory_control_time': character.territory_control_time,
            'playtime': character.playtime
        }

        success_score = calculate_success_score(character_data)

        # Calculate potential perks
        new_reincarnation_count = character.reincarnation_count + 1
        new_perks = calculate_reincarnation_perks(new_reincarnation_count, success_score)

        return {
            'current_level': character.level,
            'reincarnation_count': character.reincarnation_count,
            'next_reincarnation_count': new_reincarnation_count,
            'success_score': success_score,
            'new_perks': new_perks,
            'can_reincarnate': True,
            'stats_breakdown': {
                'level_contribution': character.level / 150.0,
                'kills_contribution': min(character.total_kills / 1000, 1.0),
                'boss_kills_contribution': min(character.boss_kills / 50, 1.0),
                'territory_contribution': min(character.territory_control_time / 360000, 1.0),
                'playtime_contribution': min(character.playtime / 720000, 1.0)
            }
        }

    def apply_reincarnation_perks_to_player(self, player_entity, perks: Dict[str, Any]):
        """
        Apply reincarnation perks to a player entity

        Args:
            player_entity: PlayerEntity to apply perks to
            perks: Perk dictionary
        """
        player_entity.max_hp += perks.get('hp_bonus', 0)
        player_entity.hp = player_entity.max_hp

        player_entity.max_mp += perks.get('mp_bonus', 0)
        player_entity.mp = player_entity.max_mp

        player_entity.attack += perks.get('attack_bonus', 0)
        player_entity.defense += perks.get('defense_bonus', 0)
        player_entity.speed += perks.get('speed_bonus', 0)

        logger.debug(f"Applied reincarnation perks to {player_entity.name}: {perks}")
