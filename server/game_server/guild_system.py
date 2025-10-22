"""
Subjugate Online - Guild/Clan System
Manages guilds for territory warfare and social organization
"""

from typing import Dict, List, Optional, Set
from datetime import datetime
from shared.utils import Logger
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class GuildMember:
    """Represents a guild member"""

    def __init__(self, character_id: int, character_name: str, rank: str):
        self.character_id = character_id
        self.character_name = character_name
        self.rank = rank  # 'leader', 'officer', 'member'
        self.joined_at = datetime.utcnow()
        self.contribution_points = 0
        self.is_online = False


class Guild:
    """Represents a guild"""

    def __init__(self, guild_id: int, name: str, leader_id: int, leader_name: str):
        self.guild_id = guild_id
        self.name = name
        self.tag = ""  # Guild tag/abbreviation
        self.level = 1
        self.experience = 0
        self.members: Dict[int, GuildMember] = {}
        self.max_members = 50
        self.created_at = datetime.utcnow()

        # Guild resources
        self.treasury = 0
        self.guild_points = 0

        # Territory control
        self.controlled_territories: Set[int] = set()

        # Guild bonuses (unlock with guild level)
        self.bonuses = {
            'hp_bonus': 0,
            'attack_bonus': 0,
            'defense_bonus': 0,
            'xp_bonus': 0.0
        }

        # Add leader
        leader = GuildMember(leader_id, leader_name, 'leader')
        self.members[leader_id] = leader

    def add_member(self, character_id: int, character_name: str) -> bool:
        """Add a member to the guild"""
        if len(self.members) >= self.max_members:
            return False

        if character_id in self.members:
            return False

        member = GuildMember(character_id, character_name, 'member')
        self.members[character_id] = member

        logger.info(f"Player {character_name} joined guild {self.name}")
        return True

    def remove_member(self, character_id: int) -> bool:
        """Remove a member from the guild"""
        if character_id not in self.members:
            return False

        # Cannot remove leader
        if self.members[character_id].rank == 'leader':
            return False

        member_name = self.members[character_id].character_name
        del self.members[character_id]

        logger.info(f"Player {member_name} left guild {self.name}")
        return True

    def promote_member(self, character_id: int, new_rank: str) -> bool:
        """Promote/demote a member"""
        if character_id not in self.members:
            return False

        if new_rank not in ['leader', 'officer', 'member']:
            return False

        self.members[character_id].rank = new_rank
        return True

    def add_experience(self, xp: int):
        """Add guild experience"""
        self.experience += xp

        # Check for level up
        xp_needed = self.get_xp_for_next_level()
        while self.experience >= xp_needed and self.level < 100:
            self.experience -= xp_needed
            self.level += 1
            self._update_guild_bonuses()
            logger.info(f"Guild {self.name} reached level {self.level}!")

    def get_xp_for_next_level(self) -> int:
        """Get XP needed for next guild level"""
        return 1000 * self.level

    def _update_guild_bonuses(self):
        """Update guild bonuses based on level"""
        self.bonuses['hp_bonus'] = self.level * 10
        self.bonuses['attack_bonus'] = self.level * 2
        self.bonuses['defense_bonus'] = self.level * 2
        self.bonuses['xp_bonus'] = self.level * 0.01  # 1% per level

        # Increase max members
        self.max_members = 50 + (self.level * 2)

    def get_online_members(self) -> List[GuildMember]:
        """Get all online members"""
        return [m for m in self.members.values() if m.is_online]

    def get_member_count(self) -> int:
        """Get total member count"""
        return len(self.members)

    def get_online_member_count(self) -> int:
        """Get online member count"""
        return len(self.get_online_members())


class GuildSystem:
    """Manages guilds in the game"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.guilds: Dict[int, Guild] = {}
        self.character_to_guild: Dict[int, int] = {}  # character_id -> guild_id
        self.guild_name_to_id: Dict[str, int] = {}
        self.next_guild_id = 1

        # Load guilds from database
        self._load_guilds()

    def _load_guilds(self):
        """Load guilds from database"""
        # In production, this would load from database
        # For now, we'll create guilds dynamically
        logger.info("Guild system initialized")

    def create_guild(self, leader_id: int, leader_name: str, guild_name: str, guild_tag: str) -> Optional[Guild]:
        """
        Create a new guild

        Args:
            leader_id: Character ID of guild leader
            leader_name: Name of guild leader
            guild_name: Name of the guild
            guild_tag: Guild tag (3-5 characters)

        Returns:
            Created guild or None if failed
        """
        # Check if character already in a guild
        if leader_id in self.character_to_guild:
            logger.warning(f"Character {leader_id} already in a guild")
            return None

        # Check if guild name taken
        if guild_name.lower() in [g.name.lower() for g in self.guilds.values()]:
            logger.warning(f"Guild name '{guild_name}' already taken")
            return None

        # Validate guild tag
        if len(guild_tag) < 3 or len(guild_tag) > 5:
            logger.warning(f"Invalid guild tag: {guild_tag}")
            return None

        # Create guild
        guild_id = self.next_guild_id
        self.next_guild_id += 1

        guild = Guild(guild_id, guild_name, leader_id, leader_name)
        guild.tag = guild_tag

        self.guilds[guild_id] = guild
        self.character_to_guild[leader_id] = guild_id
        self.guild_name_to_id[guild_name.lower()] = guild_id

        logger.info(f"Guild '{guild_name}' [{guild_tag}] created by {leader_name}")

        return guild

    def disband_guild(self, guild_id: int, requester_id: int) -> bool:
        """Disband a guild (leader only)"""
        guild = self.guilds.get(guild_id)
        if not guild:
            return False

        # Check if requester is leader
        if requester_id not in guild.members or guild.members[requester_id].rank != 'leader':
            return False

        # Remove all members from tracking
        for character_id in list(guild.members.keys()):
            if character_id in self.character_to_guild:
                del self.character_to_guild[character_id]

        # Remove guild
        if guild.name.lower() in self.guild_name_to_id:
            del self.guild_name_to_id[guild.name.lower()]

        del self.guilds[guild_id]

        logger.info(f"Guild '{guild.name}' disbanded")
        return True

    def join_guild(self, guild_id: int, character_id: int, character_name: str) -> bool:
        """Join a guild"""
        # Check if character already in a guild
        if character_id in self.character_to_guild:
            return False

        guild = self.guilds.get(guild_id)
        if not guild:
            return False

        # Add member
        if guild.add_member(character_id, character_name):
            self.character_to_guild[character_id] = guild_id
            return True

        return False

    def leave_guild(self, character_id: int) -> bool:
        """Leave a guild"""
        guild_id = self.character_to_guild.get(character_id)
        if not guild_id:
            return False

        guild = self.guilds.get(guild_id)
        if not guild:
            return False

        # Remove member
        if guild.remove_member(character_id):
            del self.character_to_guild[character_id]
            return True

        return False

    def get_guild_by_character(self, character_id: int) -> Optional[Guild]:
        """Get guild of a character"""
        guild_id = self.character_to_guild.get(character_id)
        if not guild_id:
            return None

        return self.guilds.get(guild_id)

    def get_guild_by_id(self, guild_id: int) -> Optional[Guild]:
        """Get guild by ID"""
        return self.guilds.get(guild_id)

    def get_guild_by_name(self, guild_name: str) -> Optional[Guild]:
        """Get guild by name"""
        guild_id = self.guild_name_to_id.get(guild_name.lower())
        if not guild_id:
            return None

        return self.guilds.get(guild_id)

    def set_member_online(self, character_id: int, is_online: bool):
        """Set member online status"""
        guild = self.get_guild_by_character(character_id)
        if guild and character_id in guild.members:
            guild.members[character_id].is_online = is_online

    def add_guild_experience(self, guild_id: int, xp: int):
        """Add experience to a guild"""
        guild = self.guilds.get(guild_id)
        if guild:
            guild.add_experience(xp)

    def update_territory_control(self, territory_id: int, guild_id: Optional[int]):
        """Update territory control for guilds"""
        # Remove territory from all guilds
        for guild in self.guilds.values():
            if territory_id in guild.controlled_territories:
                guild.controlled_territories.remove(territory_id)

        # Add to new controlling guild
        if guild_id and guild_id in self.guilds:
            self.guilds[guild_id].controlled_territories.add(territory_id)

    def get_guild_buffs(self, character_id: int) -> Dict[str, float]:
        """Get guild buffs for a character"""
        guild = self.get_guild_by_character(character_id)
        if not guild:
            return {
                'hp_bonus': 0,
                'attack_bonus': 0,
                'defense_bonus': 0,
                'xp_bonus': 0.0
            }

        return guild.bonuses.copy()

    def get_all_guilds(self) -> List[Guild]:
        """Get all guilds"""
        return list(self.guilds.values())

    def get_guild_ranking(self) -> List[tuple]:
        """
        Get guild ranking by various metrics

        Returns:
            List of (guild, score) tuples sorted by score
        """
        rankings = []

        for guild in self.guilds.values():
            # Calculate guild score
            score = (
                guild.level * 100 +
                guild.guild_points +
                len(guild.controlled_territories) * 500 +
                guild.get_member_count() * 10
            )

            rankings.append((guild, score))

        # Sort by score descending
        rankings.sort(key=lambda x: x[1], reverse=True)

        return rankings
