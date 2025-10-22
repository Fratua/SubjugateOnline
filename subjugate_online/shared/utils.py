"""
Utility functions for Subjugate Online
"""

import hashlib
import secrets
import string
import time
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: str = None) -> str:
    """Hash a password using SHA256 with salt"""
    if salt is None:
        salt = secrets.token_hex(16)

    hash_obj = hashlib.sha256()
    hash_obj.update(f"{password}{salt}".encode('utf-8'))
    return f"{salt}${hash_obj.hexdigest()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, hash_value = password_hash.split('$')
        return hash_password(password, salt) == password_hash
    except:
        return False


def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)


def generate_unique_id() -> str:
    """Generate a unique ID"""
    return f"{int(time.time() * 1000)}{secrets.token_hex(8)}"


def validate_username(username: str) -> bool:
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 32:
        return False

    allowed = set(string.ascii_letters + string.digits + '_-')
    return all(c in allowed for c in username)


def validate_character_name(name: str) -> bool:
    """Validate character name format"""
    if not name or len(name) < 3 or len(name) > 32:
        return False

    allowed = set(string.ascii_letters + string.digits + ' ')
    return all(c in allowed for c in name)


def validate_email(email: str) -> bool:
    """Basic email validation"""
    if not email or '@' not in email or '.' not in email:
        return False

    if len(email) < 5 or len(email) > 255:
        return False

    return True


def calculate_level_from_experience(experience: int) -> int:
    """Calculate level from experience points"""
    # Level formula: level = floor(sqrt(experience / 100))
    import math
    if experience <= 0:
        return 1
    return max(1, int(math.sqrt(experience / 100)))


def calculate_experience_for_level(level: int) -> int:
    """Calculate experience required for a level"""
    if level <= 1:
        return 0
    return (level * level) * 100


def calculate_reincarnation_score(stats: Dict[str, Any]) -> int:
    """
    Calculate reincarnation score based on character achievements
    Higher score = better perks in next life
    """
    score = 0

    # Level contribution (max 1000 points)
    level = stats.get('level', 1)
    score += min(1000, level * 10)

    # Kill/death ratio (max 500 points)
    kills = stats.get('kills', 0)
    deaths = max(1, stats.get('deaths', 1))
    kd_ratio = kills / deaths
    score += min(500, int(kd_ratio * 100))

    # Territory captures (max 500 points)
    territories = stats.get('territories_captured', 0)
    score += min(500, territories * 50)

    # Damage dealt (max 500 points)
    damage_dealt = stats.get('damage_dealt', 0)
    score += min(500, damage_dealt // 10000)

    # Playtime bonus (max 500 points)
    playtime_hours = stats.get('playtime_seconds', 0) / 3600
    score += min(500, int(playtime_hours * 10))

    return score


def calculate_reincarnation_perks(score: int) -> List[Dict[str, Any]]:
    """
    Calculate perks earned from reincarnation based on score
    """
    perks = []

    # Tier 1: 0-999 score
    if score >= 100:
        perks.append({
            'name': 'Reincarnated Soul',
            'description': '+5% experience gain',
            'type': 'experience_bonus',
            'value': 5
        })

    if score >= 300:
        perks.append({
            'name': 'Battle Veteran',
            'description': '+10 max health',
            'type': 'health_bonus',
            'value': 10
        })

    # Tier 2: 1000-1999 score
    if score >= 1000:
        perks.append({
            'name': 'Warrior\'s Spirit',
            'description': '+5% attack power',
            'type': 'attack_bonus',
            'value': 5
        })

    if score >= 1500:
        perks.append({
            'name': 'Iron Will',
            'description': '+5% defense',
            'type': 'defense_bonus',
            'value': 5
        })

    # Tier 3: 2000-2999 score
    if score >= 2000:
        perks.append({
            'name': 'Legendary Hero',
            'description': '+10% all stats',
            'type': 'all_stats_bonus',
            'value': 10
        })

    if score >= 2500:
        perks.append({
            'name': 'Immortal Essence',
            'description': '+15% experience gain',
            'type': 'experience_bonus',
            'value': 15
        })

    # Tier 4: 3000+ score
    if score >= 3000:
        perks.append({
            'name': 'Ascended Being',
            'description': '+20% damage dealt, +10% damage reduction',
            'type': 'combat_mastery',
            'value': 20
        })

    if score >= 4000:
        perks.append({
            'name': 'Divine Champion',
            'description': 'Start at level 10 with bonus equipment',
            'type': 'level_boost',
            'value': 10
        })

    return perks


def apply_perks_to_stats(base_stats: Dict[str, Any], perks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply reincarnation perks to character stats"""
    stats = base_stats.copy()

    for perk in perks:
        perk_type = perk.get('type')
        value = perk.get('value', 0)

        if perk_type == 'experience_bonus':
            stats['experience_multiplier'] = stats.get('experience_multiplier', 1.0) + (value / 100)

        elif perk_type == 'health_bonus':
            stats['max_health'] = stats.get('max_health', 100) + value
            stats['health'] = stats['max_health']

        elif perk_type == 'attack_bonus':
            stats['attack_power'] = int(stats.get('attack_power', 10) * (1 + value / 100))

        elif perk_type == 'defense_bonus':
            stats['defense'] = int(stats.get('defense', 5) * (1 + value / 100))

        elif perk_type == 'all_stats_bonus':
            multiplier = 1 + (value / 100)
            stats['strength'] = int(stats.get('strength', 10) * multiplier)
            stats['dexterity'] = int(stats.get('dexterity', 10) * multiplier)
            stats['intelligence'] = int(stats.get('intelligence', 10) * multiplier)
            stats['vitality'] = int(stats.get('vitality', 10) * multiplier)

        elif perk_type == 'level_boost':
            stats['level'] = max(stats.get('level', 1), value)
            stats['experience'] = calculate_experience_for_level(stats['level'])

    return stats


def calculate_damage(attacker_stats: Dict[str, Any], defender_stats: Dict[str, Any],
                     skill_multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Calculate damage dealt in combat
    Returns dict with damage, is_critical, and other info
    """
    import random

    # Base damage calculation
    attack_power = attacker_stats.get('attack_power', 10)
    defense = defender_stats.get('defense', 5)

    # Apply skill multiplier
    base_damage = int((attack_power - defense / 2) * skill_multiplier)
    base_damage = max(1, base_damage)  # Minimum 1 damage

    # Critical hit chance (5% base + dexterity bonus)
    dexterity = attacker_stats.get('dexterity', 10)
    crit_chance = 5 + (dexterity / 10)
    is_critical = random.random() * 100 < crit_chance

    # Apply critical multiplier
    if is_critical:
        base_damage = int(base_damage * 2.0)

    # Damage variance (±10%)
    variance = random.uniform(0.9, 1.1)
    final_damage = int(base_damage * variance)

    return {
        'damage': final_damage,
        'is_critical': is_critical,
        'base_damage': base_damage
    }


def calculate_distance_3d(pos1: Dict[str, float], pos2: Dict[str, float]) -> float:
    """Calculate 3D distance between two positions"""
    import math
    dx = pos1['x'] - pos2['x']
    dy = pos1['y'] - pos2['y']
    dz = pos1['z'] - pos2['z']
    return math.sqrt(dx*dx + dy*dy + dz*dz)


def is_in_territory(position: Dict[str, float], territory_center: Dict[str, float], radius: float) -> bool:
    """Check if a position is within a territory"""
    distance = calculate_distance_3d(position, territory_center)
    return distance <= radius


class PerformanceTimer:
    """Simple performance timer for profiling"""

    def __init__(self, name: str, log_threshold: float = 0.1):
        self.name = name
        self.log_threshold = log_threshold
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if elapsed > self.log_threshold:
            logger.warning(f"{self.name} took {elapsed:.3f}s (threshold: {self.log_threshold}s)")
        else:
            logger.debug(f"{self.name} took {elapsed:.3f}s")
