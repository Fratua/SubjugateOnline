"""
World Manager - Handles game world simulation, entities, and game logic
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta

from subjugate_online.shared.protocol import PacketBuilder
from subjugate_online.shared.utils import (
    calculate_reincarnation_score,
    calculate_reincarnation_perks,
    apply_perks_to_stats,
    is_in_territory
)
from .entities import Player, NPC, Vector3, Stats

logger = logging.getLogger(__name__)


class TerritoryController:
    """Manages territory control and buffs"""

    def __init__(self, territory_id: int, name: str, center: Vector3, radius: float,
                 buffs: List[Dict]):
        self.territory_id = territory_id
        self.name = name
        self.center = center
        self.radius = radius
        self.buffs = buffs
        self.owner_guild_id: Optional[int] = None
        self.control_percentage = 0.0
        self.is_contested = False
        self.players_in_territory: Set[int] = set()
        self.guild_presence: Dict[int, int] = defaultdict(int)  # guild_id -> player count

    def update(self, players: Dict[int, Player]):
        """Update territory state based on player presence"""
        # Reset presence
        self.players_in_territory.clear()
        self.guild_presence.clear()

        # Check which players are in territory
        for player_id, player in players.items():
            if is_in_territory(
                player.position.to_dict(),
                self.center.to_dict(),
                self.radius
            ):
                self.players_in_territory.add(player_id)
                if player.guild_id:
                    self.guild_presence[player.guild_id] += 1

        # Determine control
        if len(self.guild_presence) == 0:
            # No guild presence - slowly lose control
            self.control_percentage = max(0, self.control_percentage - 1.0)
            self.is_contested = False
        elif len(self.guild_presence) == 1:
            # Single guild - gain control
            guild_id = list(self.guild_presence.keys())[0]
            if guild_id == self.owner_guild_id:
                # Strengthen control
                self.control_percentage = min(100, self.control_percentage + 2.0)
                self.is_contested = False
            else:
                # New guild taking over
                self.control_percentage = max(0, self.control_percentage - 3.0)
                if self.control_percentage <= 0:
                    self.owner_guild_id = guild_id
                    self.control_percentage = 10.0
                self.is_contested = True
        else:
            # Multiple guilds - contested
            self.is_contested = True

    def get_active_buffs(self) -> List[Dict]:
        """Get active buffs if territory is controlled"""
        if self.owner_guild_id and self.control_percentage > 50:
            return self.buffs
        return []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'territory_id': self.territory_id,
            'name': self.name,
            'center': self.center.to_dict(),
            'radius': self.radius,
            'owner_guild_id': self.owner_guild_id,
            'control_percentage': self.control_percentage,
            'is_contested': self.is_contested,
            'players_in_territory': len(self.players_in_territory),
            'buffs': self.get_active_buffs()
        }


class WorldManager:
    """Manages the game world, entities, and game logic"""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.players: Dict[int, Player] = {}  # entity_id -> Player
        self.npcs: Dict[int, NPC] = {}  # entity_id -> NPC
        self.territories: Dict[int, TerritoryController] = {}  # territory_id -> TerritoryController

        self.next_entity_id = 1
        self.running = False
        self.tick_rate = 20  # ticks per second
        self.last_tick = time.time()

        # Pending reincarnations
        self.pending_reincarnations: Dict[int, Dict] = {}  # character_id -> death_info

        # Stats
        self.total_players_online = 0
        self.total_pvp_kills = 0
        self.total_reincarnations = 0

    def initialize(self):
        """Initialize world data from database"""
        logger.info("Initializing world...")

        # Load territories from database
        session = self.db_manager.get_session()
        try:
            from subjugate_online.shared.database import Territory

            territories = session.query(Territory).all()
            for territory in territories:
                territory_controller = TerritoryController(
                    territory_id=territory.id,
                    name=territory.name,
                    center=Vector3(territory.center_x, territory.center_y, territory.center_z),
                    radius=territory.radius,
                    buffs=territory.buffs
                )
                territory_controller.owner_guild_id = territory.owner_guild_id
                territory_controller.control_percentage = territory.control_percentage
                self.territories[territory.id] = territory_controller

            logger.info(f"Loaded {len(self.territories)} territories")

            # Spawn NPCs
            self._spawn_default_npcs()

        finally:
            self.db_manager.close_session(session)

    def _spawn_default_npcs(self):
        """Spawn default NPCs in the world"""
        npc_spawns = [
            {'name': 'Training Dummy', 'type': 'dummy', 'level': 1, 'pos': (0, 0, 10)},
            {'name': 'Goblin Scout', 'type': 'goblin', 'level': 5, 'pos': (50, 0, 50)},
            {'name': 'Orc Warrior', 'type': 'orc', 'level': 10, 'pos': (100, 0, 100)},
            {'name': 'Dark Knight', 'type': 'knight', 'level': 20, 'pos': (200, 0, 200)},
        ]

        for spawn in npc_spawns:
            npc = NPC(
                entity_id=self._get_next_entity_id(),
                name=spawn['name'],
                position=Vector3(*spawn['pos']),
                npc_type=spawn['type'],
                level=spawn['level']
            )
            self.npcs[npc.entity_id] = npc

        logger.info(f"Spawned {len(self.npcs)} NPCs")

    def _get_next_entity_id(self) -> int:
        """Get next available entity ID"""
        entity_id = self.next_entity_id
        self.next_entity_id += 1
        return entity_id

    def add_player(self, character_id: int, account_id: int, name: str,
                   character_data: Dict) -> Player:
        """Add a player to the world"""
        # Create player entity from character data
        position = Vector3(
            character_data.get('position', {}).get('x', 0.0),
            character_data.get('position', {}).get('y', 0.0),
            character_data.get('position', {}).get('z', 0.0)
        )

        stats_data = character_data.get('stats', {})
        stats = Stats(
            level=character_data.get('level', 1),
            experience=character_data.get('experience', 0),
            health=character_data.get('health', 100),
            max_health=character_data.get('max_health', 100),
            mana=character_data.get('mana', 50),
            max_mana=character_data.get('max_mana', 50),
            strength=stats_data.get('strength', 10),
            dexterity=stats_data.get('dexterity', 10),
            intelligence=stats_data.get('intelligence', 10),
            vitality=stats_data.get('vitality', 10),
            attack_power=stats_data.get('attack_power', 10),
            defense=stats_data.get('defense', 5),
            magic_power=stats_data.get('magic_power', 5),
            magic_defense=stats_data.get('magic_defense', 5)
        )

        player = Player(
            entity_id=self._get_next_entity_id(),
            character_id=character_id,
            account_id=account_id,
            name=name,
            position=position,
            stats=stats,
            game_mode=character_data.get('game_mode', 'hardcore_ironman')
        )

        # Apply reincarnation perks
        reincarnation_data = character_data.get('reincarnation', {})
        player.reincarnation_count = reincarnation_data.get('count', 0)
        player.reincarnation_perks = reincarnation_data.get('perks', [])
        player.lifetime_kills = reincarnation_data.get('total_kills', 0)
        player.lifetime_deaths = reincarnation_data.get('total_deaths', 0)

        # Apply perks to stats
        stats_dict = apply_perks_to_stats(player.stats.to_dict(), player.reincarnation_perks)
        for key, value in stats_dict.items():
            if hasattr(player.stats, key):
                setattr(player.stats, key, value)

        # PVP stats
        pvp_data = character_data.get('pvp', {})
        player.current_killstreak = pvp_data.get('killstreak', 0)
        player.territory_captures = pvp_data.get('territory_captures', 0)

        # Guild
        player.guild_id = character_data.get('guild_id')

        self.players[player.entity_id] = player
        self.total_players_online += 1

        logger.info(f"Player {name} (ID: {player.entity_id}) joined the world")

        return player

    def remove_player(self, entity_id: int) -> Optional[Player]:
        """Remove a player from the world"""
        player = self.players.pop(entity_id, None)
        if player:
            self.total_players_online -= 1
            logger.info(f"Player {player.name} (ID: {entity_id}) left the world")
        return player

    def get_player_by_entity_id(self, entity_id: int) -> Optional[Player]:
        """Get player by entity ID"""
        return self.players.get(entity_id)

    def get_player_by_character_id(self, character_id: int) -> Optional[Player]:
        """Get player by character ID"""
        for player in self.players.values():
            if player.character_id == character_id:
                return player
        return None

    def handle_player_attack(self, attacker_id: int, target_id: int, skill_id: int = 0) -> Dict:
        """Handle a player attack"""
        attacker = self.players.get(attacker_id)
        target = self.players.get(target_id)

        if not attacker or not target:
            return {'success': False, 'reason': 'Invalid entities'}

        if not attacker.is_alive or not target.is_alive:
            return {'success': False, 'reason': 'Dead entity'}

        # Perform attack
        result = attacker.perform_attack(target, skill_id)

        if result['success']:
            # Grant experience for damage dealt
            exp_gained = result['damage'] // 2
            attacker.gain_experience(exp_gained)

            # Handle death
            if result['target_died']:
                self._handle_player_death(target, attacker)

        return result

    def _handle_player_death(self, victim: Player, killer: Player):
        """Handle player death and prepare reincarnation"""
        logger.info(f"Player {victim.name} was killed by {killer.name}")

        # Update stats
        victim.lifetime_deaths += 1
        killer.lifetime_kills += 1
        self.total_pvp_kills += 1

        # Grant experience to killer
        exp_reward = victim.stats.level * 100
        killer.gain_experience(exp_reward)

        # Calculate reincarnation score
        playtime_seconds = time.time() - victim.login_time
        reincarnation_score = calculate_reincarnation_score({
            'level': victim.stats.level,
            'kills': victim.lifetime_kills,
            'deaths': victim.lifetime_deaths,
            'territories_captured': victim.territory_captures,
            'damage_dealt': victim.lifetime_damage_dealt,
            'playtime_seconds': playtime_seconds
        })

        # Calculate new perks
        new_perks = calculate_reincarnation_perks(reincarnation_score)

        # Store reincarnation data
        self.pending_reincarnations[victim.character_id] = {
            'victim': victim,
            'killer_id': killer.character_id,
            'reincarnation_score': reincarnation_score,
            'new_perks': new_perks,
            'timestamp': datetime.utcnow()
        }

        logger.info(f"Reincarnation prepared for {victim.name}: Score={reincarnation_score}, Perks={len(new_perks)}")

    def handle_reincarnation(self, character_id: int) -> Dict:
        """Handle player reincarnation"""
        if character_id not in self.pending_reincarnations:
            return {'success': False, 'reason': 'No pending reincarnation'}

        reincarnation_data = self.pending_reincarnations.pop(character_id)
        victim = reincarnation_data['victim']

        # Update player for reincarnation
        victim.reincarnation_count += 1
        victim.reincarnation_perks.extend(reincarnation_data['new_perks'])

        # Reset character to level 1 but keep perks
        victim.stats = Stats()
        victim.stats.level = 1
        victim.stats.experience = 0
        victim.stats.health = 100
        victim.stats.max_health = 100

        # Apply all accumulated perks
        stats_dict = apply_perks_to_stats(victim.stats.to_dict(), victim.reincarnation_perks)
        for key, value in stats_dict.items():
            if hasattr(victim.stats, key):
                setattr(victim.stats, key, value)

        # Reset position to spawn
        victim.position = Vector3(0, 0, 0)
        victim.is_alive = True
        victim.is_in_combat = False

        # Store to database
        self._save_reincarnation_to_database(victim, reincarnation_data)

        self.total_reincarnations += 1

        logger.info(f"Player {victim.name} reincarnated (Count: {victim.reincarnation_count})")

        return {
            'success': True,
            'reincarnation_count': victim.reincarnation_count,
            'new_perks': reincarnation_data['new_perks'],
            'reincarnation_score': reincarnation_data['reincarnation_score']
        }

    def _save_reincarnation_to_database(self, player: Player, reincarnation_data: Dict):
        """Save reincarnation to database"""
        session = self.db_manager.get_session()
        try:
            from subjugate_online.shared.database import Character, ReincarnationHistory

            # Update character
            character = session.query(Character).filter_by(id=player.character_id).first()
            if character:
                character.level = player.stats.level
                character.experience = player.stats.experience
                character.health = player.stats.health
                character.max_health = player.stats.max_health
                character.position_x = player.position.x
                character.position_y = player.position.y
                character.position_z = player.position.z
                character.reincarnation_count = player.reincarnation_count
                character.reincarnation_perks = player.reincarnation_perks
                character.total_kills = player.lifetime_kills
                character.total_deaths = player.lifetime_deaths
                character.is_dead = False

                # Create reincarnation history entry
                history = ReincarnationHistory(
                    character_id=player.character_id,
                    reincarnation_number=player.reincarnation_count,
                    level_achieved=reincarnation_data['victim'].stats.level,
                    kills=player.lifetime_kills,
                    deaths=player.lifetime_deaths,
                    damage_dealt=player.lifetime_damage_dealt,
                    territories_captured=player.territory_captures,
                    playtime_seconds=int(time.time() - player.login_time),
                    killed_by_character_id=reincarnation_data['killer_id'],
                    perks_earned=reincarnation_data['new_perks'],
                    reincarnation_score=reincarnation_data['reincarnation_score']
                )
                session.add(history)

                session.commit()

        except Exception as e:
            logger.error(f"Error saving reincarnation: {e}", exc_info=True)
            session.rollback()
        finally:
            self.db_manager.close_session(session)

    def update(self):
        """Update world state"""
        current_time = time.time()
        delta_time = current_time - self.last_tick
        self.last_tick = current_time

        # Update players
        for player in list(self.players.values()):
            player.update(delta_time)

        # Update territories
        for territory in self.territories.values():
            territory.update(self.players)

        # Apply territory buffs to players
        self._apply_territory_buffs()

        # Update NPCs
        for npc in list(self.npcs.values()):
            if npc.is_alive:
                npc.update(delta_time)

    def _apply_territory_buffs(self):
        """Apply territory buffs to players in controlled territories"""
        # First, remove all territory buffs
        for player in self.players.values():
            player.remove_buff('territory')

        # Then apply new buffs based on current territory control
        for territory in self.territories.values():
            if territory.owner_guild_id and territory.control_percentage > 50:
                for player_id in territory.players_in_territory:
                    player = self.players.get(player_id)
                    if player and player.guild_id == territory.owner_guild_id:
                        for buff in territory.get_active_buffs():
                            player.apply_buff({**buff, 'source': 'territory'})

    def get_nearby_entities(self, position: Vector3, radius: float) -> Dict[str, List]:
        """Get entities near a position"""
        nearby_players = []
        nearby_npcs = []

        pos_dict = position.to_dict()

        for player in self.players.values():
            if is_in_territory(player.position.to_dict(), pos_dict, radius):
                nearby_players.append(player)

        for npc in self.npcs.values():
            if is_in_territory(npc.position.to_dict(), pos_dict, radius):
                nearby_npcs.append(npc)

        return {
            'players': nearby_players,
            'npcs': nearby_npcs
        }

    def get_world_stats(self) -> Dict:
        """Get world statistics"""
        return {
            'total_players_online': self.total_players_online,
            'total_entities': len(self.players) + len(self.npcs),
            'total_territories': len(self.territories),
            'total_pvp_kills': self.total_pvp_kills,
            'total_reincarnations': self.total_reincarnations,
            'territories': [t.to_dict() for t in self.territories.values()]
        }
