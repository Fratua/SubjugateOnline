"""
Subjugate Online - Database Manager
Handles all database operations with SQLAlchemy
"""

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager

from server.database.models import (
    Base, Account, Session, Character, InventoryItem, Equipment,
    CharacterSkill, ActiveBuff, ReincarnationHistory, TerritoryControl,
    NPCInstance, GameLog
)
from shared.constants import DB_PATH, SESSION_EXPIRY, GameMode
from shared.utils import hash_password, verify_password, generate_session_token, Logger

logger = Logger.get_logger(__name__)


class DatabaseManager:
    """Singleton database manager"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        # Create engine and session factory
        self.engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

        # Create all tables
        Base.metadata.create_all(self.engine)

        logger.info(f"Database initialized at {DB_PATH}")
        self._initialized = True

    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    # ========================================================================
    # ACCOUNT OPERATIONS
    # ========================================================================

    def create_account(self, username: str, password: str, email: Optional[str] = None) -> Optional[Account]:
        """Create a new account"""
        with self.get_session() as session:
            # Check if username exists
            existing = session.query(Account).filter_by(username=username).first()
            if existing:
                logger.warning(f"Account creation failed: username '{username}' already exists")
                return None

            # Hash password
            password_hash, salt = hash_password(password)

            # Create account
            account = Account(
                username=username,
                password_hash=password_hash,
                password_salt=salt,
                email=email
            )

            session.add(account)
            session.flush()

            logger.info(f"Account created: {username} (ID: {account.id})")
            return account

    def authenticate_account(self, username: str, password: str) -> Optional[Account]:
        """Authenticate account credentials"""
        with self.get_session() as session:
            account = session.query(Account).filter_by(username=username).first()

            if not account:
                logger.warning(f"Authentication failed: username '{username}' not found")
                return None

            if account.is_banned:
                logger.warning(f"Authentication failed: account '{username}' is banned")
                return None

            if not verify_password(password, account.password_hash, account.password_salt):
                logger.warning(f"Authentication failed: invalid password for '{username}'")
                return None

            # Update last login
            account.last_login = datetime.utcnow()
            session.flush()

            logger.info(f"Account authenticated: {username}")
            return account

    def get_account_by_id(self, account_id: int) -> Optional[Account]:
        """Get account by ID"""
        with self.get_session() as session:
            return session.query(Account).filter_by(id=account_id).first()

    # ========================================================================
    # SESSION OPERATIONS
    # ========================================================================

    def create_session(self, account_id: int, ip_address: Optional[str] = None) -> Optional[Session]:
        """Create a new session for an account"""
        with self.get_session() as session:
            token = generate_session_token()
            expires_at = datetime.utcnow() + timedelta(seconds=SESSION_EXPIRY)

            db_session = Session(
                account_id=account_id,
                session_token=token,
                expires_at=expires_at,
                ip_address=ip_address
            )

            session.add(db_session)
            session.flush()

            logger.info(f"Session created for account ID {account_id}")
            return db_session

    def validate_session(self, session_token: str) -> Optional[Session]:
        """Validate a session token"""
        with self.get_session() as session:
            db_session = session.query(Session).filter_by(session_token=session_token).first()

            if not db_session:
                return None

            # Check expiry
            if db_session.expires_at < datetime.utcnow():
                session.delete(db_session)
                logger.info(f"Session expired and deleted: {session_token}")
                return None

            return db_session

    def delete_session(self, session_token: str):
        """Delete a session"""
        with self.get_session() as session:
            db_session = session.query(Session).filter_by(session_token=session_token).first()
            if db_session:
                session.delete(db_session)
                logger.info(f"Session deleted: {session_token}")

    def cleanup_expired_sessions(self):
        """Remove all expired sessions"""
        with self.get_session() as session:
            expired = session.query(Session).filter(Session.expires_at < datetime.utcnow()).all()
            count = len(expired)
            for s in expired:
                session.delete(s)
            logger.info(f"Cleaned up {count} expired sessions")

    # ========================================================================
    # CHARACTER OPERATIONS
    # ========================================================================

    def create_character(self, account_id: int, name: str, game_mode: int = GameMode.HARDCORE_IRONMAN) -> Optional[Character]:
        """Create a new character"""
        with self.get_session() as session:
            # Check if name exists
            existing = session.query(Character).filter_by(name=name).first()
            if existing:
                logger.warning(f"Character creation failed: name '{name}' already exists")
                return None

            from shared.constants import (
                STARTING_LEVEL, STARTING_HP, STARTING_MP,
                BASE_ATTACK, BASE_DEFENSE, BASE_SPEED
            )

            # Create character
            character = Character(
                account_id=account_id,
                name=name,
                game_mode=game_mode,
                level=STARTING_LEVEL,
                hp=STARTING_HP,
                max_hp=STARTING_HP,
                mp=STARTING_MP,
                max_mp=STARTING_MP,
                attack=BASE_ATTACK,
                defense=BASE_DEFENSE,
                speed=BASE_SPEED
            )

            session.add(character)
            session.flush()

            # Create equipment record
            equipment = Equipment(character_id=character.id)
            session.add(equipment)

            # Give starting items
            self._give_starting_items(session, character.id)

            logger.info(f"Character created: {name} (ID: {character.id})")
            return character

    def _give_starting_items(self, session, character_id: int):
        """Give starting items to a new character"""
        # Starting weapon (Iron Sword - ID 1001)
        session.add(InventoryItem(
            character_id=character_id,
            item_id=1001,
            quantity=1,
            slot_index=0
        ))

        # Starting health potions
        session.add(InventoryItem(
            character_id=character_id,
            item_id=4001,
            quantity=10,
            slot_index=1
        ))

    def get_characters_by_account(self, account_id: int) -> List[Character]:
        """Get all characters for an account"""
        with self.get_session() as session:
            return session.query(Character).filter_by(account_id=account_id).all()

    def get_character_by_id(self, character_id: int) -> Optional[Character]:
        """Get character by ID"""
        with self.get_session() as session:
            return session.query(Character).filter_by(id=character_id).first()

    def get_character_by_name(self, name: str) -> Optional[Character]:
        """Get character by name"""
        with self.get_session() as session:
            return session.query(Character).filter_by(name=name).first()

    def update_character_position(self, character_id: int, x: float, y: float, z: float, rotation: float):
        """Update character position"""
        with self.get_session() as session:
            character = session.query(Character).filter_by(id=character_id).first()
            if character:
                character.position_x = x
                character.position_y = y
                character.position_z = z
                character.rotation = rotation

    def update_character_stats(self, character_id: int, stats: Dict[str, Any]):
        """Update character stats"""
        with self.get_session() as session:
            character = session.query(Character).filter_by(id=character_id).first()
            if character:
                for key, value in stats.items():
                    if hasattr(character, key):
                        setattr(character, key, value)

    def set_character_online(self, character_id: int, online: bool):
        """Set character online/offline status"""
        with self.get_session() as session:
            character = session.query(Character).filter_by(id=character_id).first()
            if character:
                character.is_online = online
                if online:
                    character.last_played = datetime.utcnow()

    # ========================================================================
    # INVENTORY OPERATIONS
    # ========================================================================

    def get_inventory(self, character_id: int) -> List[InventoryItem]:
        """Get character inventory"""
        with self.get_session() as session:
            return session.query(InventoryItem).filter_by(character_id=character_id).all()

    def add_item(self, character_id: int, item_id: int, quantity: int = 1) -> bool:
        """Add item to character inventory"""
        with self.get_session() as session:
            # Find empty slot
            used_slots = [item.slot_index for item in session.query(InventoryItem).filter_by(character_id=character_id).all()]

            from shared.constants import MAX_INVENTORY_SLOTS
            for slot in range(MAX_INVENTORY_SLOTS):
                if slot not in used_slots:
                    item = InventoryItem(
                        character_id=character_id,
                        item_id=item_id,
                        quantity=quantity,
                        slot_index=slot
                    )
                    session.add(item)
                    return True

            logger.warning(f"Inventory full for character {character_id}")
            return False

    def remove_item(self, character_id: int, slot_index: int, quantity: int = 1) -> bool:
        """Remove item from inventory"""
        with self.get_session() as session:
            item = session.query(InventoryItem).filter_by(
                character_id=character_id,
                slot_index=slot_index
            ).first()

            if not item:
                return False

            if item.quantity <= quantity:
                session.delete(item)
            else:
                item.quantity -= quantity

            return True

    # ========================================================================
    # REINCARNATION OPERATIONS
    # ========================================================================

    def reincarnate_character(self, character_id: int, success_score: float, perks: Dict[str, Any]) -> bool:
        """Reincarnate a character"""
        with self.get_session() as session:
            character = session.query(Character).filter_by(id=character_id).first()
            if not character:
                return False

            # Save history
            history = ReincarnationHistory(
                character_id=character_id,
                reincarnation_number=character.reincarnation_count + 1,
                previous_level=character.level,
                previous_total_kills=character.total_kills,
                previous_boss_kills=character.boss_kills,
                previous_territory_time=character.territory_control_time,
                previous_playtime=character.playtime,
                success_score=success_score,
                perks_gained=perks
            )
            session.add(history)

            # Reset character
            from shared.constants import STARTING_LEVEL, STARTING_HP, STARTING_MP
            character.reincarnation_count += 1
            character.level = STARTING_LEVEL
            character.experience = 0
            character.hp = STARTING_HP
            character.max_hp = STARTING_HP
            character.mp = STARTING_MP
            character.max_mp = STARTING_MP
            character.total_kills = 0
            character.player_kills = 0
            character.boss_kills = 0
            character.territory_control_time = 0
            character.playtime = 0

            # Apply perks
            character.reincarnation_perks = perks

            logger.info(f"Character {character.name} reincarnated (count: {character.reincarnation_count})")
            return True

    # ========================================================================
    # TERRITORY OPERATIONS
    # ========================================================================

    def get_territory_control(self, territory_id: int) -> Optional[TerritoryControl]:
        """Get territory control status"""
        with self.get_session() as session:
            return session.query(TerritoryControl).filter_by(territory_id=territory_id).first()

    def set_territory_control(self, territory_id: int, character_id: Optional[int], character_name: Optional[str]):
        """Set territory controller"""
        with self.get_session() as session:
            territory = session.query(TerritoryControl).filter_by(territory_id=territory_id).first()

            if not territory:
                territory = TerritoryControl(territory_id=territory_id)
                session.add(territory)

            territory.controller_character_id = character_id
            territory.controller_name = character_name
            territory.captured_at = datetime.utcnow() if character_id else None
            territory.capture_points = 0

    # ========================================================================
    # LOGGING
    # ========================================================================

    def log_event(self, event_type: str, character_id: Optional[int] = None, details: Optional[Dict] = None):
        """Log a game event"""
        with self.get_session() as session:
            log = GameLog(
                event_type=event_type,
                character_id=character_id,
                details=details
            )
            session.add(log)
