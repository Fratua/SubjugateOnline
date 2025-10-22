"""
Database Models and ORM Layer for Subjugate Online
Uses SQLAlchemy with PostgreSQL for production persistence
"""

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, BigInteger, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.pool import QueuePool
from datetime import datetime
import enum
import json
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class GameMode(enum.Enum):
    """Player game modes"""
    HARDCORE_IRONMAN = "hardcore_ironman"
    ULTIMATE_HARDCORE_IRONMAN = "ultimate_hardcore_ironman"


class Account(Base):
    """Player account"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    session_token = Column(String(128), nullable=True, index=True)
    total_playtime = Column(BigInteger, default=0, nullable=False)  # in seconds

    # Relationships
    characters = relationship("Character", back_populates="account", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat(),
            'is_banned': self.is_banned,
            'is_admin': self.is_admin,
            'total_playtime': self.total_playtime
        }


class Character(Base):
    """Player character"""
    __tablename__ = 'characters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False, index=True)
    name = Column(String(32), unique=True, nullable=False, index=True)
    game_mode = Column(SQLEnum(GameMode), default=GameMode.HARDCORE_IRONMAN, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Core stats
    level = Column(Integer, default=1, nullable=False)
    experience = Column(BigInteger, default=0, nullable=False)
    health = Column(Integer, default=100, nullable=False)
    max_health = Column(Integer, default=100, nullable=False)
    mana = Column(Integer, default=50, nullable=False)
    max_mana = Column(Integer, default=50, nullable=False)

    # Combat stats
    strength = Column(Integer, default=10, nullable=False)
    dexterity = Column(Integer, default=10, nullable=False)
    intelligence = Column(Integer, default=10, nullable=False)
    vitality = Column(Integer, default=10, nullable=False)
    attack_power = Column(Integer, default=10, nullable=False)
    defense = Column(Integer, default=5, nullable=False)
    magic_power = Column(Integer, default=5, nullable=False)
    magic_defense = Column(Integer, default=5, nullable=False)

    # Position
    position_x = Column(Float, default=0.0, nullable=False)
    position_y = Column(Float, default=0.0, nullable=False)
    position_z = Column(Float, default=0.0, nullable=False)
    rotation = Column(Float, default=0.0, nullable=False)
    zone = Column(String(64), default="spawn_zone", nullable=False)

    # Reincarnation system
    reincarnation_count = Column(Integer, default=0, nullable=False)
    total_kills = Column(Integer, default=0, nullable=False)
    total_deaths = Column(Integer, default=0, nullable=False)
    lifetime_damage_dealt = Column(BigInteger, default=0, nullable=False)
    lifetime_damage_taken = Column(BigInteger, default=0, nullable=False)
    reincarnation_perks = Column(JSON, default=list, nullable=False)

    # PVP stats
    pvp_kills = Column(Integer, default=0, nullable=False)
    pvp_deaths = Column(Integer, default=0, nullable=False)
    territory_captures = Column(Integer, default=0, nullable=False)
    highest_killstreak = Column(Integer, default=0, nullable=False)
    current_killstreak = Column(Integer, default=0, nullable=False)

    # Inventory (stored as JSON)
    inventory = Column(JSON, default=list, nullable=False)
    equipment = Column(JSON, default=dict, nullable=False)
    bank = Column(JSON, default=list, nullable=False)  # Not available in Ultimate mode

    # Skills (stored as JSON)
    skills = Column(JSON, default=dict, nullable=False)

    # State
    is_online = Column(Boolean, default=False, nullable=False)
    is_dead = Column(Boolean, default=False, nullable=False)
    is_in_combat = Column(Boolean, default=False, nullable=False)
    last_death_time = Column(DateTime, nullable=True)

    # Guild
    guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=True, index=True)

    # Relationships
    account = relationship("Account", back_populates="characters")
    guild = relationship("Guild", back_populates="members")
    reincarnation_history = relationship("ReincarnationHistory", back_populates="character", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'account_id': self.account_id,
            'name': self.name,
            'game_mode': self.game_mode.value,
            'level': self.level,
            'experience': self.experience,
            'health': self.health,
            'max_health': self.max_health,
            'mana': self.mana,
            'max_mana': self.max_mana,
            'stats': {
                'strength': self.strength,
                'dexterity': self.dexterity,
                'intelligence': self.intelligence,
                'vitality': self.vitality,
                'attack_power': self.attack_power,
                'defense': self.defense,
                'magic_power': self.magic_power,
                'magic_defense': self.magic_defense
            },
            'position': {
                'x': self.position_x,
                'y': self.position_y,
                'z': self.position_z,
                'rotation': self.rotation,
                'zone': self.zone
            },
            'reincarnation': {
                'count': self.reincarnation_count,
                'perks': self.reincarnation_perks,
                'total_kills': self.total_kills,
                'total_deaths': self.total_deaths
            },
            'pvp': {
                'kills': self.pvp_kills,
                'deaths': self.pvp_deaths,
                'territory_captures': self.territory_captures,
                'killstreak': self.current_killstreak,
                'highest_killstreak': self.highest_killstreak
            },
            'inventory': self.inventory,
            'equipment': self.equipment,
            'skills': self.skills,
            'is_online': self.is_online,
            'is_dead': self.is_dead,
            'guild_id': self.guild_id
        }


class ReincarnationHistory(Base):
    """Track character reincarnation history"""
    __tablename__ = 'reincarnation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False, index=True)
    reincarnation_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Life stats
    level_achieved = Column(Integer, nullable=False)
    kills = Column(Integer, nullable=False)
    deaths = Column(Integer, nullable=False)
    damage_dealt = Column(BigInteger, nullable=False)
    territories_captured = Column(Integer, nullable=False)
    playtime_seconds = Column(BigInteger, nullable=False)

    # Killer info
    killed_by_character_id = Column(Integer, ForeignKey('characters.id'), nullable=True)
    killed_by_npc = Column(String(64), nullable=True)

    # Perks earned
    perks_earned = Column(JSON, default=list, nullable=False)
    reincarnation_score = Column(Integer, nullable=False)

    # Relationships
    character = relationship("Character", back_populates="reincarnation_history", foreign_keys=[character_id])

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'reincarnation_number': self.reincarnation_number,
            'timestamp': self.timestamp.isoformat(),
            'level_achieved': self.level_achieved,
            'kills': self.kills,
            'deaths': self.deaths,
            'damage_dealt': self.damage_dealt,
            'territories_captured': self.territories_captured,
            'playtime_seconds': self.playtime_seconds,
            'perks_earned': self.perks_earned,
            'reincarnation_score': self.reincarnation_score
        }


class Guild(Base):
    """Player guilds for territory control"""
    __tablename__ = 'guilds'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False, index=True)
    tag = Column(String(5), unique=True, nullable=False)
    leader_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Stats
    total_kills = Column(Integer, default=0, nullable=False)
    territories_controlled = Column(Integer, default=0, nullable=False)
    guild_level = Column(Integer, default=1, nullable=False)
    guild_points = Column(Integer, default=0, nullable=False)

    # Relationships
    members = relationship("Character", back_populates="guild", foreign_keys=[Character.guild_id])
    territories = relationship("Territory", back_populates="owner_guild")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'tag': self.tag,
            'leader_id': self.leader_id,
            'created_at': self.created_at.isoformat(),
            'total_kills': self.total_kills,
            'territories_controlled': self.territories_controlled,
            'guild_level': self.guild_level,
            'guild_points': self.guild_points,
            'member_count': len(self.members)
        }


class Territory(Base):
    """Territories that can be controlled for buffs (Conquer Online style)"""
    __tablename__ = 'territories'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), unique=True, nullable=False, index=True)
    zone = Column(String(64), nullable=False)

    # Position and size
    center_x = Column(Float, nullable=False)
    center_y = Column(Float, nullable=False)
    center_z = Column(Float, nullable=False)
    radius = Column(Float, nullable=False)

    # Ownership
    owner_guild_id = Column(Integer, ForeignKey('guilds.id'), nullable=True, index=True)
    captured_at = Column(DateTime, nullable=True)
    control_percentage = Column(Float, default=0.0, nullable=False)

    # Buffs provided
    buffs = Column(JSON, default=list, nullable=False)

    # State
    is_contested = Column(Boolean, default=False, nullable=False)
    next_battle_time = Column(DateTime, nullable=True)

    # Relationships
    owner_guild = relationship("Guild", back_populates="territories")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'zone': self.zone,
            'position': {
                'x': self.center_x,
                'y': self.center_y,
                'z': self.center_z,
                'radius': self.radius
            },
            'owner_guild_id': self.owner_guild_id,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None,
            'control_percentage': self.control_percentage,
            'buffs': self.buffs,
            'is_contested': self.is_contested,
            'next_battle_time': self.next_battle_time.isoformat() if self.next_battle_time else None
        }


class WorldState(Base):
    """Global world state and configuration"""
    __tablename__ = 'world_state'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat()
        }


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, connection_string: str, echo: bool = False):
        self.connection_string = connection_string
        self.engine = create_engine(
            connection_string,
            echo=echo,
            poolclass=QueuePool,
            pool_size=20,
            max_overflow=40,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        self.Session = scoped_session(sessionmaker(bind=self.engine))

    def create_all_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(self.engine)
        logger.info("Database tables created successfully")

    def drop_all_tables(self):
        """Drop all database tables (use with caution!)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(self.engine)
        logger.info("All database tables dropped")

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def close_session(self, session):
        """Close a database session"""
        session.close()

    def initialize_world_data(self):
        """Initialize default world data"""
        session = self.get_session()
        try:
            # Create default territories
            default_territories = [
                {
                    'name': 'Central Plaza',
                    'zone': 'main_city',
                    'center_x': 0.0,
                    'center_y': 0.0,
                    'center_z': 0.0,
                    'radius': 50.0,
                    'buffs': [
                        {'type': 'experience_bonus', 'value': 10},
                        {'type': 'drop_rate_bonus', 'value': 5}
                    ]
                },
                {
                    'name': 'Northern Fortress',
                    'zone': 'north_region',
                    'center_x': 500.0,
                    'center_y': 0.0,
                    'center_z': 500.0,
                    'radius': 75.0,
                    'buffs': [
                        {'type': 'attack_bonus', 'value': 15},
                        {'type': 'defense_bonus', 'value': 10}
                    ]
                },
                {
                    'name': 'Eastern Sanctuary',
                    'zone': 'east_region',
                    'center_x': 500.0,
                    'center_y': 0.0,
                    'center_z': -500.0,
                    'radius': 75.0,
                    'buffs': [
                        {'type': 'magic_power_bonus', 'value': 20},
                        {'type': 'mana_regen_bonus', 'value': 5}
                    ]
                },
                {
                    'name': 'Southern Outpost',
                    'zone': 'south_region',
                    'center_x': -500.0,
                    'center_y': 0.0,
                    'center_z': 0.0,
                    'radius': 60.0,
                    'buffs': [
                        {'type': 'health_bonus', 'value': 50},
                        {'type': 'health_regen_bonus', 'value': 3}
                    ]
                },
                {
                    'name': 'Western Arena',
                    'zone': 'west_region',
                    'center_x': 0.0,
                    'center_y': 0.0,
                    'center_z': 500.0,
                    'radius': 100.0,
                    'buffs': [
                        {'type': 'pvp_damage_bonus', 'value': 25},
                        {'type': 'kill_experience_bonus', 'value': 15}
                    ]
                }
            ]

            for territory_data in default_territories:
                existing = session.query(Territory).filter_by(name=territory_data['name']).first()
                if not existing:
                    territory = Territory(**territory_data)
                    session.add(territory)

            session.commit()
            logger.info("World data initialized successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"Error initializing world data: {e}")
            raise
        finally:
            self.close_session(session)
