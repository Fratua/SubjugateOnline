"""
Subjugate Online - Territory Control System
Manages territory capture and buffs (Conquer Online inspired)
"""

import time
from typing import Dict, List, Optional, Tuple
from shared.constants import (
    TERRITORY_UPDATE_INTERVAL, TERRITORY_CAPTURE_TIME,
    MIN_PLAYERS_TO_CAPTURE, TERRITORY_BUFFS, TerritoryType
)
from shared.utils import calculate_distance, Logger
from shared.game_data import TERRITORY_DATABASE, get_territory_data

logger = Logger.get_logger(__name__)


class TerritoryState:
    """Represents the state of a territory"""

    def __init__(self, territory_id: int, territory_data: dict):
        self.territory_id = territory_id
        self.name = territory_data['name']
        self.position = territory_data['position']
        self.radius = territory_data['radius']
        self.capture_points_required = territory_data['capture_points_required']

        # Control state
        self.controller_id: Optional[int] = None
        self.controller_name: Optional[str] = None
        self.capture_points = 0
        self.last_capture_time = 0.0

        # Active capture attempt
        self.capturing_player_id: Optional[int] = None
        self.capture_start_time = 0.0

    def get_buffs(self) -> Dict[str, Any]:
        """Get buffs provided by this territory"""
        return TERRITORY_BUFFS.get(self.territory_id, {})

    def is_being_captured(self) -> bool:
        """Check if territory is currently being captured"""
        return self.capturing_player_id is not None

    def get_capture_progress(self, current_time: float) -> float:
        """Get capture progress (0.0 - 1.0)"""
        if not self.is_being_captured():
            return 0.0

        elapsed = current_time - self.capture_start_time
        return min(elapsed / TERRITORY_CAPTURE_TIME, 1.0)


class TerritorySystem:
    """Manages territory control"""

    def __init__(self, world_manager, db_manager):
        self.world = world_manager
        self.db = db_manager
        self.territories: Dict[int, TerritoryState] = {}

        # Initialize territories
        for territory_id, territory_data in TERRITORY_DATABASE.items():
            self.territories[territory_id] = TerritoryState(territory_id, territory_data)

        # Load territory control from database
        self._load_territory_control()

        logger.info(f"TerritorySystem initialized with {len(self.territories)} territories")

    def _load_territory_control(self):
        """Load territory control state from database"""
        for territory_id in self.territories.keys():
            control = self.db.get_territory_control(territory_id)
            if control and control.controller_character_id:
                territory = self.territories[territory_id]
                territory.controller_id = control.controller_character_id
                territory.controller_name = control.controller_name
                territory.capture_points = control.capture_points

    def update(self, delta_time: float):
        """
        Update territory system

        Args:
            delta_time: Time since last update in seconds
        """
        current_time = time.time()

        for territory in self.territories.values():
            # Check for players in territory
            players_in_territory = self._get_players_in_territory(territory)

            if len(players_in_territory) >= MIN_PLAYERS_TO_CAPTURE:
                # Check if any player is trying to capture
                for player in players_in_territory:
                    # Skip if player is already controller
                    if player.character_id == territory.controller_id:
                        continue

                    # Start capture if not already capturing
                    if not territory.is_being_captured():
                        territory.capturing_player_id = player.character_id
                        territory.capture_start_time = current_time
                        logger.info(f"{player.name} started capturing {territory.name}")

                    # Check if capture is complete
                    elif territory.capturing_player_id == player.character_id:
                        progress = territory.get_capture_progress(current_time)
                        if progress >= 1.0:
                            self._capture_territory(territory, player.character_id, player.name)

            else:
                # Reset capture attempt if not enough players
                if territory.is_being_captured():
                    logger.info(f"Capture of {territory.name} interrupted (not enough players)")
                    territory.capturing_player_id = None
                    territory.capture_start_time = 0.0

    def _get_players_in_territory(self, territory: TerritoryState) -> List:
        """Get all players currently in a territory"""
        players_in_territory = []

        for player in self.world.get_all_players():
            if player.is_dead:
                continue

            distance = calculate_distance(player.position, territory.position)
            if distance <= territory.radius:
                players_in_territory.append(player)

        return players_in_territory

    def _capture_territory(self, territory: TerritoryState, character_id: int, character_name: str):
        """
        Capture a territory

        Args:
            territory: Territory to capture
            character_id: Capturing player ID
            character_name: Capturing player name
        """
        old_controller = territory.controller_name

        territory.controller_id = character_id
        territory.controller_name = character_name
        territory.capture_points = territory.capture_points_required
        territory.last_capture_time = time.time()
        territory.capturing_player_id = None
        territory.capture_start_time = 0.0

        # Update database
        self.db.set_territory_control(territory.territory_id, character_id, character_name)

        # Log event
        self.db.log_event('territory_captured', character_id, {
            'territory_id': territory.territory_id,
            'territory_name': territory.name,
            'previous_controller': old_controller
        })

        logger.info(f"Territory captured! {territory.name} now controlled by {character_name}")

    def get_territory_buffs_for_player(self, character_id: int) -> Dict[str, int]:
        """
        Get all territory buffs for a player

        Args:
            character_id: Player character ID

        Returns:
            Dictionary of buff totals
        """
        total_buffs = {
            'hp_bonus': 0,
            'attack_bonus': 0,
            'defense_bonus': 0,
            'xp_bonus': 0.0
        }

        # Check each territory
        for territory in self.territories.values():
            if territory.controller_id == character_id:
                buffs = territory.get_buffs()
                total_buffs['hp_bonus'] += buffs.get('hp_bonus', 0)
                total_buffs['attack_bonus'] += buffs.get('attack_bonus', 0)
                total_buffs['defense_bonus'] += buffs.get('defense_bonus', 0)
                total_buffs['xp_bonus'] += buffs.get('xp_bonus', 0.0)

        return total_buffs

    def apply_territory_buffs_to_player(self, player_entity, character_id: int):
        """
        Apply territory buffs to a player entity

        Args:
            player_entity: PlayerEntity to apply buffs to
            character_id: Character ID to check territory control
        """
        buffs = self.get_territory_buffs_for_player(character_id)

        player_entity.max_hp += buffs['hp_bonus']
        player_entity.hp = min(player_entity.hp + buffs['hp_bonus'], player_entity.max_hp)
        player_entity.attack += buffs['attack_bonus']
        player_entity.defense += buffs['defense_bonus']

        if buffs['hp_bonus'] > 0 or buffs['attack_bonus'] > 0:
            logger.debug(f"Applied territory buffs to {player_entity.name}: {buffs}")

    def get_territory_status(self) -> List[Dict]:
        """Get status of all territories"""
        status = []

        for territory in self.territories.values():
            status.append({
                'territory_id': territory.territory_id,
                'name': territory.name,
                'controller_id': territory.controller_id,
                'controller_name': territory.controller_name,
                'capture_points': territory.capture_points,
                'is_being_captured': territory.is_being_captured(),
                'capture_progress': territory.get_capture_progress(time.time()) if territory.is_being_captured() else 0.0,
                'buffs': territory.get_buffs()
            })

        return status

    def get_territory_by_id(self, territory_id: int) -> Optional[TerritoryState]:
        """Get territory by ID"""
        return self.territories.get(territory_id)
