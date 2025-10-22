"""
Subjugate Online - Achievement and Leaderboard System
Tracks player achievements and maintains global leaderboards
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from shared.utils import Logger
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class Achievement:
    """Represents an achievement"""

    def __init__(
        self,
        achievement_id: int,
        name: str,
        description: str,
        category: str,
        hidden: bool = False
    ):
        self.achievement_id = achievement_id
        self.name = name
        self.description = description
        self.category = category  # 'combat', 'reincarnation', 'territory', 'social', 'crafting'
        self.hidden = hidden  # Hidden until unlocked

        # Requirements
        self.requirements: Dict[str, Any] = {}

        # Rewards
        self.rewards = {
            'legacy_points': 0,
            'title': None
        }

        self.points = 10  # Achievement points

    def check_completion(self, player_stats: Dict[str, Any]) -> bool:
        """Check if achievement requirements are met"""
        for req_key, req_value in self.requirements.items():
            player_value = player_stats.get(req_key, 0)

            if isinstance(req_value, (int, float)):
                if player_value < req_value:
                    return False
            elif isinstance(req_value, list):
                # Must have all items in list
                if not all(item in player_value for item in req_value):
                    return False

        return True


class LeaderboardEntry:
    """Represents a leaderboard entry"""

    def __init__(
        self,
        rank: int,
        character_id: int,
        character_name: str,
        value: Any,
        additional_data: Optional[Dict] = None
    ):
        self.rank = rank
        self.character_id = character_id
        self.character_name = character_name
        self.value = value
        self.additional_data = additional_data or {}


class AchievementSystem:
    """Manages achievements and leaderboards"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.achievements: Dict[int, Achievement] = {}
        self.player_achievements: Dict[int, List[int]] = {}  # character_id -> achievement_ids
        self.player_stats: Dict[int, Dict[str, Any]] = {}  # character_id -> stats

        # Initialize achievements
        self._initialize_achievements()

        logger.info(f"Achievement system initialized with {len(self.achievements)} achievements")

    def _initialize_achievements(self):
        """Initialize achievement database"""
        # === COMBAT ACHIEVEMENTS ===
        ach = Achievement(1, "First Kill", "Defeat your first enemy", "combat")
        ach.requirements = {'total_kills': 1}
        ach.rewards['legacy_points'] = 10
        ach.points = 5
        self.achievements[1] = ach

        ach = Achievement(2, "Novice Slayer", "Defeat 100 enemies", "combat")
        ach.requirements = {'total_kills': 100}
        ach.rewards['legacy_points'] = 50
        ach.points = 10
        self.achievements[2] = ach

        ach = Achievement(3, "Master Slayer", "Defeat 1000 enemies", "combat")
        ach.requirements = {'total_kills': 1000}
        ach.rewards['legacy_points'] = 200
        ach.rewards['title'] = "The Slayer"
        ach.points = 25
        self.achievements[3] = ach

        ach = Achievement(4, "Boss Hunter", "Defeat 10 bosses", "combat")
        ach.requirements = {'boss_kills': 10}
        ach.rewards['legacy_points'] = 100
        ach.points = 20
        self.achievements[4] = ach

        ach = Achievement(5, "PvP Warrior", "Defeat 50 players in PvP", "combat")
        ach.requirements = {'player_kills': 50}
        ach.rewards['legacy_points'] = 150
        ach.rewards['title'] = "The Conqueror"
        ach.points = 30
        self.achievements[5] = ach

        # === REINCARNATION ACHIEVEMENTS ===
        ach = Achievement(100, "Reborn", "Complete your first reincarnation", "reincarnation")
        ach.requirements = {'reincarnation_count': 1}
        ach.rewards['legacy_points'] = 100
        ach.points = 25
        self.achievements[100] = ach

        ach = Achievement(101, "Twice Blessed", "Reincarnate 3 times", "reincarnation")
        ach.requirements = {'reincarnation_count': 3}
        ach.rewards['legacy_points'] = 300
        ach.rewards['title'] = "The Reborn"
        ach.points = 50
        self.achievements[101] = ach

        ach = Achievement(102, "Eternal Soul", "Reach maximum reincarnations (10)", "reincarnation")
        ach.requirements = {'reincarnation_count': 10}
        ach.rewards['legacy_points'] = 1000
        ach.rewards['title'] = "The Eternal"
        ach.points = 100
        self.achievements[102] = ach

        # === LEVEL ACHIEVEMENTS ===
        ach = Achievement(200, "Apprentice", "Reach level 25", "progression")
        ach.requirements = {'level': 25}
        ach.rewards['legacy_points'] = 25
        ach.points = 10
        self.achievements[200] = ach

        ach = Achievement(201, "Journeyman", "Reach level 50", "progression")
        ach.requirements = {'level': 50}
        ach.rewards['legacy_points'] = 75
        ach.points = 20
        self.achievements[201] = ach

        ach = Achievement(202, "Master", "Reach level 100", "progression")
        ach.requirements = {'level': 100}
        ach.rewards['legacy_points'] = 200
        ach.rewards['title'] = "The Master"
        ach.points = 50
        self.achievements[202] = ach

        ach = Achievement(203, "Legend", "Reach level 150", "progression")
        ach.requirements = {'level': 150}
        ach.rewards['legacy_points'] = 500
        ach.rewards['title'] = "The Legend"
        ach.points = 100
        self.achievements[203] = ach

        # === TERRITORY ACHIEVEMENTS ===
        ach = Achievement(300, "Territory Holder", "Capture any territory", "territory")
        ach.requirements = {'territories_captured': 1}
        ach.rewards['legacy_points'] = 100
        ach.points = 25
        self.achievements[300] = ach

        ach = Achievement(301, "Conqueror", "Capture all 5 territories", "territory")
        ach.requirements = {'territories_captured': 5}
        ach.rewards['legacy_points'] = 500
        ach.rewards['title'] = "The Overlord"
        ach.points = 75
        self.achievements[301] = ach

        # === SPECIAL ACHIEVEMENTS ===
        ach = Achievement(900, "Ultimate Ironman", "Create an Ultimate Ironman character", "special")
        ach.requirements = {'game_mode': 1}  # Ultimate Ironman
        ach.rewards['legacy_points'] = 50
        ach.points = 20
        self.achievements[900] = ach

        ach = Achievement(901, "Survivor", "Survive 100 hours of gameplay", "special")
        ach.requirements = {'playtime': 360000}  # 100 hours in seconds
        ach.rewards['legacy_points'] = 200
        ach.rewards['title'] = "The Survivor"
        ach.points = 50
        self.achievements[901] = ach

        ach = Achievement(999, "Perfect Run", "Reach level 100 without dying", "special", hidden=True)
        ach.requirements = {'level': 100, 'deaths': 0}
        ach.rewards['legacy_points'] = 1000
        ach.rewards['title'] = "The Flawless"
        ach.points = 200
        self.achievements[999] = ach

    def check_achievements(self, character_id: int) -> List[Achievement]:
        """
        Check and award new achievements for a character

        Returns:
            List of newly unlocked achievements
        """
        if character_id not in self.player_achievements:
            self.player_achievements[character_id] = []

        if character_id not in self.player_stats:
            return []

        player_stats = self.player_stats[character_id]
        unlocked_achievements = []

        for achievement in self.achievements.values():
            # Skip if already unlocked
            if achievement.achievement_id in self.player_achievements[character_id]:
                continue

            # Check if requirements met
            if achievement.check_completion(player_stats):
                self.player_achievements[character_id].append(achievement.achievement_id)
                unlocked_achievements.append(achievement)

                logger.info(f"Character {character_id} unlocked achievement: {achievement.name}")

        return unlocked_achievements

    def update_player_stat(self, character_id: int, stat: str, value: Any):
        """Update a player stat and check for achievements"""
        if character_id not in self.player_stats:
            self.player_stats[character_id] = {}

        self.player_stats[character_id][stat] = value

        # Check for new achievements
        return self.check_achievements(character_id)

    def increment_player_stat(self, character_id: int, stat: str, amount: int = 1):
        """Increment a player stat"""
        if character_id not in self.player_stats:
            self.player_stats[character_id] = {}

        current = self.player_stats[character_id].get(stat, 0)
        self.player_stats[character_id][stat] = current + amount

        # Check for new achievements
        return self.check_achievements(character_id)

    def get_player_achievements(self, character_id: int) -> List[Achievement]:
        """Get all achievements unlocked by a player"""
        achievement_ids = self.player_achievements.get(character_id, [])
        return [self.achievements[aid] for aid in achievement_ids if aid in self.achievements]

    def get_achievement_progress(self, character_id: int, achievement_id: int) -> Dict[str, Any]:
        """Get progress towards an achievement"""
        achievement = self.achievements.get(achievement_id)
        if not achievement:
            return {}

        player_stats = self.player_stats.get(character_id, {})

        progress = {}
        for req_key, req_value in achievement.requirements.items():
            player_value = player_stats.get(req_key, 0)
            progress[req_key] = {
                'current': player_value,
                'required': req_value,
                'percentage': (player_value / req_value * 100.0) if isinstance(req_value, (int, float)) else 0
            }

        return progress

    def get_achievement_points(self, character_id: int) -> int:
        """Get total achievement points for a player"""
        achievements = self.get_player_achievements(character_id)
        return sum(ach.points for ach in achievements)


class LeaderboardSystem:
    """Manages global leaderboards"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

        # Leaderboard types
        self.leaderboard_types = [
            'level',
            'total_kills',
            'player_kills',
            'boss_kills',
            'reincarnation_count',
            'territory_control_time',
            'achievement_points',
            'guild_points'
        ]

    def get_leaderboard(
        self,
        leaderboard_type: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[LeaderboardEntry]:
        """
        Get a leaderboard

        Args:
            leaderboard_type: Type of leaderboard
            limit: Maximum entries to return
            offset: Offset for pagination

        Returns:
            List of leaderboard entries
        """
        if leaderboard_type not in self.leaderboard_types:
            return []

        # In production, this would query the database
        # For now, return an empty list
        # Example query:
        # SELECT character_id, name, <stat> FROM characters
        # ORDER BY <stat> DESC
        # LIMIT <limit> OFFSET <offset>

        return []

    def get_player_rank(self, character_id: int, leaderboard_type: str) -> Optional[int]:
        """Get a player's rank in a leaderboard"""
        if leaderboard_type not in self.leaderboard_types:
            return None

        # In production, this would query the database
        # Example query:
        # SELECT COUNT(*) + 1 FROM characters
        # WHERE <stat> > (SELECT <stat> FROM characters WHERE id = <character_id>)

        return None

    def get_top_players(self, leaderboard_type: str, count: int = 10) -> List[LeaderboardEntry]:
        """Get top players for a leaderboard"""
        return self.get_leaderboard(leaderboard_type, limit=count)
