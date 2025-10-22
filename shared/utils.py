"""
Subjugate Online - Utility Functions
Helper functions used throughout the codebase
"""

import hashlib
import secrets
import time
import math
from typing import Tuple, Optional
import logging

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash a password with SHA-256 and salt

    Args:
        password: Plain text password
        salt: Optional salt, generates new one if not provided

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(32)

    pwd_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return pwd_hash, salt

def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verify a password against a hash"""
    computed_hash, _ = hash_password(password, salt)
    return computed_hash == hashed

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def calculate_distance(pos1: Tuple[float, float, float],
                       pos2: Tuple[float, float, float]) -> float:
    """Calculate 3D Euclidean distance between two positions"""
    dx = pos1[0] - pos2[0]
    dy = pos1[1] - pos2[1]
    dz = pos1[2] - pos2[2]
    return math.sqrt(dx*dx + dy*dy + dz*dz)

def calculate_distance_2d(pos1: Tuple[float, float],
                          pos2: Tuple[float, float]) -> float:
    """Calculate 2D distance (ignoring height)"""
    dx = pos1[0] - pos2[0]
    dz = pos1[1] - pos2[1]
    return math.sqrt(dx*dx + dz*dz)

def normalize_vector(vec: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """Normalize a 3D vector"""
    magnitude = math.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
    if magnitude == 0:
        return (0, 0, 0)
    return (vec[0]/magnitude, vec[1]/magnitude, vec[2]/magnitude)

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b"""
    return a + (b - a) * t

def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a value between min and max"""
    return max(min_val, min(max_val, value))

def get_timestamp() -> int:
    """Get current Unix timestamp in milliseconds"""
    return int(time.time() * 1000)

def calculate_xp_for_level(level: int) -> int:
    """
    Calculate total XP required to reach a level
    Formula: XP = level^3 * 100
    """
    return int(level ** 3 * 100)

def calculate_level_from_xp(xp: int) -> int:
    """Calculate level from total XP"""
    level = 1
    while calculate_xp_for_level(level + 1) <= xp:
        level += 1
    return level

def calculate_damage(attacker_stats: dict, defender_stats: dict,
                    skill_multiplier: float = 1.0,
                    damage_type: int = 0) -> int:
    """
    Calculate damage dealt in combat

    Args:
        attacker_stats: Dict with 'attack', 'level' keys
        defender_stats: Dict with 'defense', 'level' keys
        skill_multiplier: Damage multiplier from skill
        damage_type: Type of damage (Physical/Magical/True)

    Returns:
        Final damage value
    """
    from shared.constants import DamageType

    base_damage = attacker_stats['attack'] * skill_multiplier

    if damage_type == DamageType.TRUE:
        # True damage ignores defense
        return int(base_damage)

    # Apply defense reduction
    defense = defender_stats['defense']
    damage_reduction = defense / (defense + 100)

    final_damage = base_damage * (1 - damage_reduction)

    # Level difference modifier
    level_diff = attacker_stats['level'] - defender_stats['level']
    level_modifier = 1.0 + (level_diff * 0.02)  # 2% per level difference
    level_modifier = clamp(level_modifier, 0.5, 1.5)

    final_damage *= level_modifier

    # Random variance (90-110%)
    import random
    variance = random.uniform(0.9, 1.1)
    final_damage *= variance

    return max(1, int(final_damage))

def calculate_success_score(character_data: dict) -> float:
    """
    Calculate success score for reincarnation perk calculation

    Args:
        character_data: Dict with life statistics

    Returns:
        Success score (0.0 - 1.0)
    """
    from shared.constants import SuccessMetrics, MAX_LEVEL

    # Normalize metrics
    level_score = character_data.get('level', 1) / MAX_LEVEL

    # Kills normalized to a reasonable max (e.g., 1000 kills = 1.0)
    kills_score = min(character_data.get('total_kills', 0) / 1000, 1.0)

    # Territory control time (hours, max 100 hours = 1.0)
    territory_score = min(character_data.get('territory_control_time', 0) / 360000, 1.0)

    # Boss kills (max 50 = 1.0)
    boss_kills_score = min(character_data.get('boss_kills', 0) / 50, 1.0)

    # Playtime (hours, max 200 hours = 1.0)
    playtime_score = min(character_data.get('playtime', 0) / 720000, 1.0)

    # Weighted sum
    total_score = (
        level_score * SuccessMetrics.LEVEL_WEIGHT +
        kills_score * SuccessMetrics.KILLS_WEIGHT +
        territory_score * SuccessMetrics.TERRITORY_WEIGHT +
        boss_kills_score * SuccessMetrics.BOSS_KILLS_WEIGHT +
        playtime_score * SuccessMetrics.PLAYTIME_WEIGHT
    )

    return total_score

def calculate_reincarnation_perks(reincarnation_count: int, success_score: float) -> dict:
    """
    Calculate perk bonuses based on reincarnation count and success

    Args:
        reincarnation_count: Number of times reincarnated
        success_score: Success score from previous life (0.0 - 1.0)

    Returns:
        Dict of perk bonuses
    """
    from shared.constants import (
        PERK_HP_BONUS, PERK_MP_BONUS, PERK_ATTACK_BONUS,
        PERK_DEFENSE_BONUS, PERK_SPEED_BONUS, PERK_XP_MULTIPLIER
    )

    # Base perks multiply by reincarnation count
    multiplier = reincarnation_count * success_score

    return {
        'hp_bonus': int(PERK_HP_BONUS * multiplier),
        'mp_bonus': int(PERK_MP_BONUS * multiplier),
        'attack_bonus': int(PERK_ATTACK_BONUS * multiplier),
        'defense_bonus': int(PERK_DEFENSE_BONUS * multiplier),
        'speed_bonus': PERK_SPEED_BONUS * multiplier,
        'xp_multiplier': PERK_XP_MULTIPLIER * multiplier
    }

def get_spawn_position(zone_type: int = 0) -> Tuple[float, float, float]:
    """Get a spawn position based on zone type"""
    # Default spawn positions for different zones
    spawn_positions = {
        0: (100.0, 0.0, 100.0),  # Safe zone spawn
        1: (500.0, 0.0, 500.0),  # PVP zone spawn
        2: (250.0, 0.0, 250.0),  # Territory zone spawn
    }
    return spawn_positions.get(zone_type, (0.0, 0.0, 0.0))

def get_chunk_id(position: Tuple[float, float, float], chunk_size: float) -> Tuple[int, int]:
    """Get chunk ID for spatial partitioning"""
    chunk_x = int(position[0] / chunk_size)
    chunk_z = int(position[2] / chunk_size)
    return (chunk_x, chunk_z)

def get_surrounding_chunks(chunk_id: Tuple[int, int], radius: int = 1) -> list:
    """Get list of surrounding chunk IDs"""
    chunks = []
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            chunks.append((chunk_id[0] + dx, chunk_id[1] + dz))
    return chunks

class Logger:
    """Custom logger wrapper with color support"""

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a configured logger instance"""
        logger = logging.getLogger(name)

        if not logger.handlers:
            from shared.constants import LOG_LEVEL, LOG_FORMAT

            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(handler)
            logger.setLevel(LOG_LEVEL)

        return logger

def format_time(seconds: int) -> str:
    """Format seconds into human-readable time"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 16:
        return False
    return username.isalnum()

def validate_password(password: str) -> bool:
    """Validate password strength"""
    if not password or len(password) < 6:
        return False
    return True

def validate_character_name(name: str) -> bool:
    """Validate character name"""
    if not name or len(name) < 3 or len(name) > 16:
        return False
    return name.replace(' ', '').isalnum()
