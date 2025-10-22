"""
Subjugate Online - Dynamic Quest System
Advanced quest system with daily quests, achievements, and dynamic objectives
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from shared.utils import Logger
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class QuestObjective:
    """Represents a quest objective"""

    def __init__(self, objective_type: str, target: Any, required: int):
        self.objective_type = objective_type  # 'kill', 'collect', 'reach_level', 'capture_territory'
        self.target = target  # NPC ID, item ID, level, etc.
        self.required = required  # Amount required
        self.current = 0  # Current progress

    def is_complete(self) -> bool:
        """Check if objective is complete"""
        return self.current >= self.required

    def update_progress(self, amount: int = 1):
        """Update objective progress"""
        self.current = min(self.current + amount, self.required)

    def get_progress_percentage(self) -> float:
        """Get progress as percentage"""
        return (self.current / self.required) * 100.0 if self.required > 0 else 100.0


class Quest:
    """Represents a quest"""

    def __init__(
        self,
        quest_id: int,
        name: str,
        description: str,
        quest_type: str,
        min_level: int = 1
    ):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.quest_type = quest_type  # 'story', 'daily', 'weekly', 'achievement'
        self.min_level = min_level

        self.objectives: List[QuestObjective] = []
        self.rewards = {
            'xp': 0,
            'gold': 0,
            'items': [],  # List of item IDs
            'legacy_points': 0  # For reincarnation
        }

        self.is_repeatable = quest_type in ['daily', 'weekly']
        self.cooldown_time = None  # For repeatable quests

    def add_objective(self, objective: QuestObjective):
        """Add an objective to the quest"""
        self.objectives.append(objective)

    def is_complete(self) -> bool:
        """Check if all objectives are complete"""
        return all(obj.is_complete() for obj in self.objectives)

    def get_incomplete_objectives(self) -> List[QuestObjective]:
        """Get incomplete objectives"""
        return [obj for obj in self.objectives if not obj.is_complete()]


class ActiveQuest:
    """Represents an active quest for a player"""

    def __init__(self, quest: Quest):
        self.quest = quest
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.turned_in = False

    def mark_complete(self):
        """Mark quest as complete"""
        self.completed_at = datetime.utcnow()

    def turn_in(self):
        """Turn in completed quest"""
        if self.quest.is_complete():
            self.turned_in = True
            return True
        return False


class QuestSystem:
    """Manages quests and player quest progress"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.quests: Dict[int, Quest] = {}
        self.player_quests: Dict[int, List[ActiveQuest]] = {}  # character_id -> active quests
        self.player_completed: Dict[int, List[int]] = {}  # character_id -> completed quest IDs
        self.next_quest_id = 1

        # Initialize quest database
        self._initialize_quests()

    def _initialize_quests(self):
        """Initialize quest database with starter quests"""
        # === STARTER QUESTS ===
        quest = Quest(
            quest_id=1,
            name="First Blood",
            description="Defeat your first monster",
            quest_type="story",
            min_level=1
        )
        quest.add_objective(QuestObjective('kill', 'any', 1))
        quest.rewards['xp'] = 50
        quest.rewards['gold'] = 10
        self.quests[1] = quest

        # === DAILY QUESTS ===
        quest = Quest(
            quest_id=100,
            name="Daily Monster Hunt",
            description="Defeat 20 monsters",
            quest_type="daily",
            min_level=1
        )
        quest.add_objective(QuestObjective('kill', 'monster', 20))
        quest.rewards['xp'] = 500
        quest.rewards['gold'] = 100
        quest.rewards['legacy_points'] = 10
        self.quests[100] = quest

        quest = Quest(
            quest_id=101,
            name="Daily PvP Challenge",
            description="Defeat 3 players in PvP combat",
            quest_type="daily",
            min_level=10
        )
        quest.add_objective(QuestObjective('pvp_kill', 'player', 3))
        quest.rewards['xp'] = 1000
        quest.rewards['gold'] = 200
        quest.rewards['legacy_points'] = 25
        self.quests[101] = quest

        # === TERRITORY QUESTS ===
        quest = Quest(
            quest_id=200,
            name="Territory Conqueror",
            description="Capture any territory",
            quest_type="achievement",
            min_level=15
        )
        quest.add_objective(QuestObjective('capture_territory', 'any', 1))
        quest.rewards['xp'] = 2000
        quest.rewards['legacy_points'] = 50
        self.quests[200] = quest

        # === BOSS QUESTS ===
        quest = Quest(
            quest_id=300,
            name="Dragon Slayer",
            description="Defeat the Dragon Lord",
            quest_type="story",
            min_level=45
        )
        quest.add_objective(QuestObjective('kill_boss', 6001, 1))  # Dragon Lord ID
        quest.rewards['xp'] = 10000
        quest.rewards['gold'] = 5000
        quest.rewards['legacy_points'] = 100
        quest.rewards['items'] = [1003]  # Legendary Blade
        self.quests[300] = quest

        # === REINCARNATION QUESTS ===
        quest = Quest(
            quest_id=400,
            name="Path of Rebirth",
            description="Reach level 100 and reincarnate",
            quest_type="achievement",
            min_level=1
        )
        quest.add_objective(QuestObjective('reach_level', 100, 1))
        quest.add_objective(QuestObjective('reincarnate', 1, 1))
        quest.rewards['legacy_points'] = 500
        self.quests[400] = quest

        logger.info(f"Quest system initialized with {len(self.quests)} quests")

    def get_available_quests(self, character_id: int, character_level: int) -> List[Quest]:
        """Get available quests for a character"""
        available = []

        # Get player's active and completed quests
        active_quest_ids = [aq.quest.quest_id for aq in self.player_quests.get(character_id, [])]
        completed_quest_ids = self.player_completed.get(character_id, [])

        for quest in self.quests.values():
            # Check if already active
            if quest.quest_id in active_quest_ids:
                continue

            # Check if already completed (and not repeatable)
            if not quest.is_repeatable and quest.quest_id in completed_quest_ids:
                continue

            # Check level requirement
            if character_level < quest.min_level:
                continue

            available.append(quest)

        return available

    def accept_quest(self, character_id: int, quest_id: int) -> bool:
        """Accept a quest"""
        quest = self.quests.get(quest_id)
        if not quest:
            return False

        # Initialize player quest tracking if needed
        if character_id not in self.player_quests:
            self.player_quests[character_id] = []

        # Check if already active
        if any(aq.quest.quest_id == quest_id for aq in self.player_quests[character_id]):
            return False

        # Accept quest (create a fresh instance)
        active_quest = ActiveQuest(self._create_quest_instance(quest))
        self.player_quests[character_id].append(active_quest)

        logger.info(f"Character {character_id} accepted quest {quest.name}")
        return True

    def _create_quest_instance(self, quest: Quest) -> Quest:
        """Create a fresh instance of a quest with new objectives"""
        new_quest = Quest(
            quest.quest_id,
            quest.name,
            quest.description,
            quest.quest_type,
            quest.min_level
        )
        new_quest.rewards = quest.rewards.copy()
        new_quest.is_repeatable = quest.is_repeatable

        # Copy objectives
        for obj in quest.objectives:
            new_obj = QuestObjective(obj.objective_type, obj.target, obj.required)
            new_quest.add_objective(new_obj)

        return new_quest

    def abandon_quest(self, character_id: int, quest_id: int) -> bool:
        """Abandon a quest"""
        if character_id not in self.player_quests:
            return False

        # Find and remove quest
        for i, active_quest in enumerate(self.player_quests[character_id]):
            if active_quest.quest.quest_id == quest_id:
                del self.player_quests[character_id][i]
                logger.info(f"Character {character_id} abandoned quest {quest_id}")
                return True

        return False

    def update_quest_progress(
        self,
        character_id: int,
        event_type: str,
        target: Any,
        amount: int = 1
    ) -> List[Quest]:
        """
        Update quest progress for a character

        Args:
            character_id: Character ID
            event_type: Type of event ('kill', 'collect', etc.)
            target: Event target (NPC ID, item ID, etc.)
            amount: Amount to add to progress

        Returns:
            List of quests that were completed
        """
        if character_id not in self.player_quests:
            return []

        completed_quests = []

        for active_quest in self.player_quests[character_id]:
            if active_quest.completed_at:
                continue  # Already complete

            # Update objectives
            for objective in active_quest.quest.objectives:
                # Check if objective matches event
                if objective.objective_type == event_type:
                    # Check target match
                    if objective.target == 'any' or objective.target == target:
                        objective.update_progress(amount)

                        # Special case: 'kill' also counts for 'monster'
                        if event_type == 'kill' and objective.target == 'monster':
                            objective.update_progress(amount)

            # Check if quest complete
            if active_quest.quest.is_complete() and not active_quest.completed_at:
                active_quest.mark_complete()
                completed_quests.append(active_quest.quest)
                logger.info(f"Character {character_id} completed quest {active_quest.quest.name}")

        return completed_quests

    def turn_in_quest(self, character_id: int, quest_id: int) -> Optional[Dict[str, Any]]:
        """
        Turn in a completed quest

        Returns:
            Quest rewards or None if failed
        """
        if character_id not in self.player_quests:
            return None

        # Find completed quest
        for i, active_quest in enumerate(self.player_quests[character_id]):
            if active_quest.quest.quest_id == quest_id:
                if not active_quest.quest.is_complete():
                    return None

                if active_quest.turned_in:
                    return None

                # Turn in quest
                active_quest.turn_in()

                # Track completion
                if character_id not in self.player_completed:
                    self.player_completed[character_id] = []

                if quest_id not in self.player_completed[character_id]:
                    self.player_completed[character_id].append(quest_id)

                # Remove from active quests
                del self.player_quests[character_id][i]

                logger.info(f"Character {character_id} turned in quest {active_quest.quest.name}")

                # Return rewards
                return active_quest.quest.rewards

        return None

    def get_active_quests(self, character_id: int) -> List[ActiveQuest]:
        """Get character's active quests"""
        return self.player_quests.get(character_id, [])

    def get_quest_by_id(self, quest_id: int) -> Optional[Quest]:
        """Get quest by ID"""
        return self.quests.get(quest_id)

    def generate_daily_quests(self, character_level: int) -> List[Quest]:
        """Generate random daily quests based on character level"""
        daily_quests = []

        # Get all daily quest templates
        daily_templates = [q for q in self.quests.values() if q.quest_type == 'daily']

        # Filter by level
        available = [q for q in daily_templates if character_level >= q.min_level]

        # Return up to 3 daily quests
        return random.sample(available, min(3, len(available)))
