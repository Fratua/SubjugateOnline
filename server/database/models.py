"""
Subjugate Online - Database Models
SQLAlchemy ORM models for all database tables
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

# ============================================================================
# ACCOUNT MODELS
# ============================================================================

class Account(Base):
    """User account table"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(16), unique=True, nullable=False, index=True)
    password_hash = Column(String(64), nullable=False)
    password_salt = Column(String(64), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False)

    # Relationships
    characters = relationship("Character", back_populates="account", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="account", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Account(id={self.id}, username='{self.username}')>"


class Session(Base):
    """Active session table for login server"""
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    session_token = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String(45), nullable=True)  # Support IPv6

    # Relationships
    account = relationship("Account", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, account_id={self.account_id})>"


# ============================================================================
# CHARACTER MODELS
# ============================================================================

class Character(Base):
    """Player character table"""
    __tablename__ = 'characters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    name = Column(String(16), unique=True, nullable=False, index=True)

    # Game mode
    game_mode = Column(Integer, default=0)  # 0 = Hardcore Ironman, 1 = Ultimate Ironman

    # Base stats
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    hp = Column(Integer, default=100)
    max_hp = Column(Integer, default=100)
    mp = Column(Integer, default=50)
    max_mp = Column(Integer, default=50)
    attack = Column(Integer, default=10)
    defense = Column(Integer, default=10)
    speed = Column(Float, default=5.0)

    # Position
    position_x = Column(Float, default=100.0)
    position_y = Column(Float, default=0.0)
    position_z = Column(Float, default=100.0)
    rotation = Column(Float, default=0.0)

    # Reincarnation
    reincarnation_count = Column(Integer, default=0)
    reincarnation_perks = Column(JSON, default={})  # Store perk bonuses as JSON

    # Statistics for current life
    total_kills = Column(Integer, default=0)
    player_kills = Column(Integer, default=0)
    boss_kills = Column(Integer, default=0)
    deaths = Column(Integer, default=0)
    territory_control_time = Column(Integer, default=0)  # Seconds
    playtime = Column(Integer, default=0)  # Seconds

    # Status
    is_online = Column(Boolean, default=False)
    is_dead = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_played = Column(DateTime, default=datetime.utcnow)

    # Relationships
    account = relationship("Account", back_populates="characters")
    inventory = relationship("InventoryItem", back_populates="character", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="character", uselist=False, cascade="all, delete-orphan")
    skills = relationship("CharacterSkill", back_populates="character", cascade="all, delete-orphan")
    reincarnation_history = relationship("ReincarnationHistory", back_populates="character", cascade="all, delete-orphan")
    active_buffs = relationship("ActiveBuff", back_populates="character", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Character(id={self.id}, name='{self.name}', level={self.level})>"


class InventoryItem(Base):
    """Character inventory items"""
    __tablename__ = 'inventory_items'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    item_id = Column(Integer, nullable=False)  # References game_data.ITEM_DATABASE
    quantity = Column(Integer, default=1)
    slot_index = Column(Integer, nullable=False)

    # Relationships
    character = relationship("Character", back_populates="inventory")

    def __repr__(self):
        return f"<InventoryItem(character_id={self.character_id}, item_id={self.item_id}, qty={self.quantity})>"


class Equipment(Base):
    """Character equipped items"""
    __tablename__ = 'equipment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), unique=True, nullable=False)

    # Equipment slots (item IDs, null if empty)
    weapon = Column(Integer, nullable=True)
    head = Column(Integer, nullable=True)
    chest = Column(Integer, nullable=True)
    legs = Column(Integer, nullable=True)
    boots = Column(Integer, nullable=True)
    gloves = Column(Integer, nullable=True)
    ring_1 = Column(Integer, nullable=True)
    ring_2 = Column(Integer, nullable=True)
    necklace = Column(Integer, nullable=True)

    # Relationships
    character = relationship("Character", back_populates="equipment")

    def __repr__(self):
        return f"<Equipment(character_id={self.character_id})>"


class CharacterSkill(Base):
    """Character learned skills and levels"""
    __tablename__ = 'character_skills'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    skill_id = Column(Integer, nullable=False)  # References game_data.SKILL_DATABASE
    skill_level = Column(Integer, default=1)

    # Relationships
    character = relationship("Character", back_populates="skills")

    def __repr__(self):
        return f"<CharacterSkill(character_id={self.character_id}, skill_id={self.skill_id}, level={self.skill_level})>"


class ActiveBuff(Base):
    """Active buffs on characters"""
    __tablename__ = 'active_buffs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    buff_type = Column(String(50), nullable=False)  # 'territory', 'reincarnation', etc.
    buff_data = Column(JSON, nullable=False)  # Buff stats as JSON
    expires_at = Column(DateTime, nullable=True)  # Null for permanent buffs

    # Relationships
    character = relationship("Character", back_populates="active_buffs")

    def __repr__(self):
        return f"<ActiveBuff(character_id={self.character_id}, type='{self.buff_type}')>"


# ============================================================================
# REINCARNATION MODELS
# ============================================================================

class ReincarnationHistory(Base):
    """History of character reincarnations"""
    __tablename__ = 'reincarnation_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    reincarnation_number = Column(Integer, nullable=False)

    # Previous life stats
    previous_level = Column(Integer, nullable=False)
    previous_total_kills = Column(Integer, default=0)
    previous_boss_kills = Column(Integer, default=0)
    previous_territory_time = Column(Integer, default=0)
    previous_playtime = Column(Integer, default=0)

    # Calculated values
    success_score = Column(Float, default=0.0)
    perks_gained = Column(JSON, nullable=False)  # Perk bonuses gained

    reincarnated_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    character = relationship("Character", back_populates="reincarnation_history")

    def __repr__(self):
        return f"<ReincarnationHistory(character_id={self.character_id}, number={self.reincarnation_number})>"


# ============================================================================
# WORLD STATE MODELS
# ============================================================================

class TerritoryControl(Base):
    """Current territory control state"""
    __tablename__ = 'territory_control'

    id = Column(Integer, primary_key=True, autoincrement=True)
    territory_id = Column(Integer, unique=True, nullable=False)  # References game_data.TERRITORY_DATABASE
    controller_character_id = Column(Integer, ForeignKey('characters.id'), nullable=True)
    controller_name = Column(String(16), nullable=True)
    captured_at = Column(DateTime, nullable=True)
    capture_points = Column(Integer, default=0)

    def __repr__(self):
        return f"<TerritoryControl(territory_id={self.territory_id}, controller='{self.controller_name}')>"


class NPCInstance(Base):
    """Spawned NPC instances in the world"""
    __tablename__ = 'npc_instances'

    id = Column(Integer, primary_key=True, autoincrement=True)
    npc_id = Column(Integer, nullable=False)  # References game_data.NPC_DATABASE

    # Current state
    hp = Column(Integer, nullable=False)
    max_hp = Column(Integer, nullable=False)
    position_x = Column(Float, nullable=False)
    position_y = Column(Float, nullable=False)
    position_z = Column(Float, nullable=False)

    # AI state
    target_character_id = Column(Integer, ForeignKey('characters.id'), nullable=True)
    state = Column(String(20), default='idle')  # idle, patrolling, chasing, attacking

    spawned_at = Column(DateTime, default=datetime.utcnow)
    last_respawn = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<NPCInstance(id={self.id}, npc_id={self.npc_id}, hp={self.hp}/{self.max_hp})>"


# ============================================================================
# ADMIN & LOGS
# ============================================================================

class GameLog(Base):
    """Game event logs for admin monitoring"""
    __tablename__ = 'game_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False, index=True)  # login, death, kill, reincarnation, etc.
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=True)
    details = Column(JSON, nullable=True)  # Additional event data
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<GameLog(id={self.id}, type='{self.event_type}', timestamp={self.timestamp})>"
