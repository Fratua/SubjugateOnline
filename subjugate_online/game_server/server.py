"""
Game Server Implementation
Handles world simulation, combat, territory control, and player interactions
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from subjugate_online.shared.network import NetworkServer, NetworkSession
from subjugate_online.shared.protocol import (
    Packet, PacketType, PacketBuilder, PacketParser, CombatState
)
from subjugate_online.shared.database import DatabaseManager, Account, Character
from .world import WorldManager
from .entities import Vector3

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GameServer(NetworkServer):
    """Game server for handling world simulation and player interactions"""

    def __init__(self, host: str, port: int, db_manager: DatabaseManager):
        super().__init__(host, port, "GameServer")
        self.db_manager = db_manager
        self.world_manager = WorldManager(db_manager)

        # Map session_id to entity_id
        self.session_to_entity: Dict[str, int] = {}

        # Register packet handlers
        self.register_handler(PacketType.ENTER_WORLD, self._handle_enter_world)
        self.register_handler(PacketType.LEAVE_WORLD, self._handle_leave_world)
        self.register_handler(PacketType.MOVE_REQUEST, self._handle_move_request)
        self.register_handler(PacketType.ATTACK_REQUEST, self._handle_attack_request)
        self.register_handler(PacketType.REINCARNATE, self._handle_reincarnate)
        self.register_handler(PacketType.CHAT_MESSAGE, self._handle_chat_message)
        self.register_handler(PacketType.TERRITORY_INFO, self._handle_territory_info)
        self.register_handler(PacketType.PONG, self._handle_pong)

    async def start(self):
        """Start the game server"""
        # Initialize world
        self.world_manager.initialize()

        # Start world update loop
        asyncio.create_task(self._world_update_loop())

        # Start base server
        await super().start()

    async def _world_update_loop(self):
        """Main world update loop"""
        logger.info("Starting world update loop...")
        tick_interval = 1.0 / self.world_manager.tick_rate

        while self.running:
            try:
                loop_start = asyncio.get_event_loop().time()

                # Update world
                self.world_manager.update()

                # Broadcast world state to clients
                await self._broadcast_world_state()

                # Sleep until next tick
                elapsed = asyncio.get_event_loop().time() - loop_start
                sleep_time = max(0, tick_interval - elapsed)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in world update loop: {e}", exc_info=True)

        logger.info("World update loop stopped")

    async def _broadcast_world_state(self):
        """Broadcast world state updates to all players"""
        # Only broadcast every 10 ticks to reduce bandwidth
        if int(self.world_manager.last_tick * self.world_manager.tick_rate) % 10 != 0:
            return

        for session_id, entity_id in self.session_to_entity.items():
            session = self.sessions.get(session_id)
            if not session:
                continue

            player = self.world_manager.get_player_by_entity_id(entity_id)
            if not player:
                continue

            # Get nearby entities
            nearby = self.world_manager.get_nearby_entities(player.position, 100.0)

            # Build and send position updates for nearby players
            for nearby_player in nearby['players']:
                if nearby_player.entity_id != entity_id:  # Don't send own position
                    update_packet = PacketBuilder.move_update(
                        nearby_player.entity_id,
                        nearby_player.position.x,
                        nearby_player.position.y,
                        nearby_player.position.z,
                        nearby_player.rotation,
                        nearby_player.velocity.x,
                        nearby_player.velocity.y,
                        nearby_player.velocity.z
                    )
                    await session.send_packet(update_packet)

    async def _handle_enter_world(self, session: NetworkSession, packet: Packet):
        """Handle player entering the world"""
        try:
            # Parse enter world data
            data = json.loads(packet.payload.decode('utf-8'))
            session_token = data.get('session_token')
            character_id = data.get('character_id')

            logger.info(f"Enter world request from {session.remote_addr}: Character {character_id}")

            # Validate session token
            db_session = self.db_manager.get_session()
            try:
                account = db_session.query(Account).filter_by(
                    session_token=session_token
                ).first()

                if not account:
                    response = PacketBuilder.error_message(401, "Invalid session token")
                    await session.send_packet(response)
                    return

                # Load character
                character = db_session.query(Character).filter_by(
                    id=character_id,
                    account_id=account.id
                ).first()

                if not character:
                    response = PacketBuilder.error_message(404, "Character not found")
                    await session.send_packet(response)
                    return

                # Check if character is dead and needs reincarnation
                if character.is_dead:
                    response = PacketBuilder.error_message(400, "Character is dead. Must reincarnate first.")
                    await session.send_packet(response)
                    return

                # Add player to world
                player = self.world_manager.add_player(
                    character_id=character.id,
                    account_id=account.id,
                    name=character.name,
                    character_data=character.to_dict()
                )

                # Update session
                session.authenticated = True
                session.account_id = account.id
                session.character_id = character.id
                session.username = character.name
                player.session_id = session.session_id

                # Map session to entity
                self.session_to_entity[session.session_id] = player.entity_id

                # Mark character as online
                character.is_online = True
                db_session.commit()

                # Send success response with player data
                response_data = {
                    'success': True,
                    'entity_id': player.entity_id,
                    'player_data': player.to_dict(),
                    'world_stats': self.world_manager.get_world_stats()
                }
                response = Packet(PacketType.ENTER_WORLD,
                                json.dumps(response_data).encode('utf-8'))
                await session.send_packet(response)

                # Broadcast to other players
                await self._broadcast_player_joined(player, session.session_id)

                logger.info(f"Player {character.name} entered the world (Entity ID: {player.entity_id})")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling enter world: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_leave_world(self, session: NetworkSession, packet: Packet):
        """Handle player leaving the world"""
        if session.session_id in self.session_to_entity:
            entity_id = self.session_to_entity[session.session_id]
            player = self.world_manager.remove_player(entity_id)

            if player:
                # Save player state to database
                await self._save_player_state(player)

                # Broadcast to other players
                await self._broadcast_player_left(player, session.session_id)

            del self.session_to_entity[session.session_id]

    async def _handle_move_request(self, session: NetworkSession, packet: Packet):
        """Handle player movement request"""
        if session.session_id not in self.session_to_entity:
            return

        try:
            move_data = PacketParser.parse_move_update(packet)
            entity_id = self.session_to_entity[session.session_id]
            player = self.world_manager.get_player_by_entity_id(entity_id)

            if player:
                # Update player position
                player.position.x = move_data['position']['x']
                player.position.y = move_data['position']['y']
                player.position.z = move_data['position']['z']
                player.rotation = move_data['rotation']
                player.velocity.x = move_data['velocity']['x']
                player.velocity.y = move_data['velocity']['y']
                player.velocity.z = move_data['velocity']['z']

                # Broadcast to nearby players
                update_packet = PacketBuilder.move_update(
                    entity_id,
                    player.position.x,
                    player.position.y,
                    player.position.z,
                    player.rotation,
                    player.velocity.x,
                    player.velocity.y,
                    player.velocity.z
                )

                nearby = self.world_manager.get_nearby_entities(player.position, 100.0)
                for nearby_player in nearby['players']:
                    if nearby_player.entity_id != entity_id:
                        nearby_session = self._get_session_by_entity_id(nearby_player.entity_id)
                        if nearby_session:
                            await nearby_session.send_packet(update_packet)

        except Exception as e:
            logger.error(f"Error handling move request: {e}", exc_info=True)

    async def _handle_attack_request(self, session: NetworkSession, packet: Packet):
        """Handle player attack request"""
        if session.session_id not in self.session_to_entity:
            return

        try:
            target_id, skill_id = PacketParser.parse_attack_request(packet)
            attacker_id = self.session_to_entity[session.session_id]

            # Process attack
            result = self.world_manager.handle_player_attack(attacker_id, target_id, skill_id)

            # Send response to attacker
            response_data = {
                'success': result['success'],
                'damage': result.get('damage', 0),
                'is_critical': result.get('is_critical', False),
                'target_died': result.get('target_died', False)
            }
            response = Packet(PacketType.ATTACK_RESPONSE,
                            json.dumps(response_data).encode('utf-8'))
            await session.send_packet(response)

            if result['success']:
                # Broadcast damage to nearby players
                damage_packet = PacketBuilder.damage_dealt(
                    attacker_id,
                    target_id,
                    result['damage'],
                    result['is_critical'],
                    result['target_died']
                )

                attacker = self.world_manager.get_player_by_entity_id(attacker_id)
                if attacker:
                    nearby = self.world_manager.get_nearby_entities(attacker.position, 100.0)
                    for nearby_player in nearby['players']:
                        nearby_session = self._get_session_by_entity_id(nearby_player.entity_id)
                        if nearby_session:
                            await nearby_session.send_packet(damage_packet)

                # Handle death
                if result['target_died']:
                    target = self.world_manager.get_player_by_entity_id(target_id)
                    if target:
                        # Get reincarnation score from pending reincarnations
                        reincarnation_data = self.world_manager.pending_reincarnations.get(
                            target.character_id, {}
                        )
                        reincarnation_score = reincarnation_data.get('reincarnation_score', 0)

                        death_packet = PacketBuilder.player_died(
                            target_id,
                            attacker_id,
                            reincarnation_score
                        )

                        # Send to target
                        target_session = self._get_session_by_entity_id(target_id)
                        if target_session:
                            await target_session.send_packet(death_packet)

                        # Broadcast to nearby
                        for nearby_player in nearby['players']:
                            nearby_session = self._get_session_by_entity_id(nearby_player.entity_id)
                            if nearby_session:
                                await nearby_session.send_packet(death_packet)

        except Exception as e:
            logger.error(f"Error handling attack request: {e}", exc_info=True)

    async def _handle_reincarnate(self, session: NetworkSession, packet: Packet):
        """Handle player reincarnation request"""
        if not session.character_id:
            return

        try:
            # Process reincarnation
            result = self.world_manager.handle_reincarnation(session.character_id)

            if result['success']:
                # Get player
                entity_id = self.session_to_entity.get(session.session_id)
                if entity_id:
                    player = self.world_manager.get_player_by_entity_id(entity_id)
                    if player:
                        # Send reincarnation success with new perks
                        response = PacketBuilder.reincarnate(
                            entity_id,
                            result['new_perks']
                        )
                        await session.send_packet(response)

                        # Send updated player data
                        player_info = PacketBuilder.character_info(player.to_dict())
                        await session.send_packet(player_info)

                        logger.info(f"Player {player.name} successfully reincarnated")
            else:
                response = PacketBuilder.error_message(400, result.get('reason', 'Reincarnation failed'))
                await session.send_packet(response)

        except Exception as e:
            logger.error(f"Error handling reincarnation: {e}", exc_info=True)

    async def _handle_chat_message(self, session: NetworkSession, packet: Packet):
        """Handle chat message"""
        try:
            chat_data = PacketParser.parse_chat_message(packet)
            sender = session.username or "Unknown"

            logger.info(f"Chat [{chat_data['channel']}] {sender}: {chat_data['message']}")

            # Broadcast to all players
            broadcast_packet = PacketBuilder.chat_message(
                sender,
                chat_data['message'],
                chat_data['channel']
            )

            await self.broadcast_packet(broadcast_packet)

        except Exception as e:
            logger.error(f"Error handling chat message: {e}", exc_info=True)

    async def _handle_territory_info(self, session: NetworkSession, packet: Packet):
        """Handle territory info request"""
        try:
            world_stats = self.world_manager.get_world_stats()

            response_data = {
                'territories': world_stats['territories']
            }
            response = Packet(PacketType.TERRITORY_INFO,
                            json.dumps(response_data).encode('utf-8'))
            await session.send_packet(response)

        except Exception as e:
            logger.error(f"Error handling territory info: {e}", exc_info=True)

    async def _handle_pong(self, session: NetworkSession, packet: Packet):
        """Handle pong response"""
        session.last_activity = datetime.now().timestamp()

    def _get_session_by_entity_id(self, entity_id: int) -> Optional[NetworkSession]:
        """Get session by entity ID"""
        for session_id, eid in self.session_to_entity.items():
            if eid == entity_id:
                return self.sessions.get(session_id)
        return None

    async def _broadcast_player_joined(self, player, exclude_session: str):
        """Broadcast that a player joined"""
        join_data = {
            'entity_id': player.entity_id,
            'name': player.name,
            'position': player.position.to_dict()
        }
        packet = Packet(PacketType.ENTER_WORLD,
                       json.dumps(join_data).encode('utf-8'))

        for session_id, session in self.sessions.items():
            if session_id != exclude_session and session.authenticated:
                try:
                    await session.send_packet(packet)
                except Exception as e:
                    logger.error(f"Error broadcasting player join: {e}")

    async def _broadcast_player_left(self, player, exclude_session: str):
        """Broadcast that a player left"""
        leave_data = {
            'entity_id': player.entity_id,
            'name': player.name
        }
        packet = Packet(PacketType.LEAVE_WORLD,
                       json.dumps(leave_data).encode('utf-8'))

        for session_id, session in self.sessions.items():
            if session_id != exclude_session and session.authenticated:
                try:
                    await session.send_packet(packet)
                except Exception as e:
                    logger.error(f"Error broadcasting player leave: {e}")

    async def _save_player_state(self, player):
        """Save player state to database"""
        session = self.db_manager.get_session()
        try:
            character = session.query(Character).filter_by(id=player.character_id).first()
            if character:
                # Update character data
                character.level = player.stats.level
                character.experience = player.stats.experience
                character.health = player.stats.health
                character.max_health = player.stats.max_health
                character.mana = player.stats.mana
                character.max_mana = player.stats.max_mana

                character.strength = player.stats.strength
                character.dexterity = player.stats.dexterity
                character.intelligence = player.stats.intelligence
                character.vitality = player.stats.vitality
                character.attack_power = player.stats.attack_power
                character.defense = player.stats.defense
                character.magic_power = player.stats.magic_power
                character.magic_defense = player.stats.magic_defense

                character.position_x = player.position.x
                character.position_y = player.position.y
                character.position_z = player.position.z
                character.rotation = player.rotation

                character.total_kills = player.lifetime_kills
                character.total_deaths = player.lifetime_deaths
                character.lifetime_damage_dealt = player.lifetime_damage_dealt
                character.lifetime_damage_taken = player.lifetime_damage_taken
                character.current_killstreak = player.current_killstreak
                character.territory_captures = player.territory_captures

                character.is_online = False
                character.is_dead = not player.is_alive

                session.commit()
                logger.info(f"Saved player state for {player.name}")

        except Exception as e:
            logger.error(f"Error saving player state: {e}", exc_info=True)
            session.rollback()
        finally:
            self.db_manager.close_session(session)


async def main():
    """Main entry point for game server"""
    # Configuration
    config = {
        'host': '0.0.0.0',
        'port': 8889,
        'db_connection': 'postgresql://subjugate:subjugate123@localhost:5432/subjugate_online'
    }

    # Initialize database
    db_manager = DatabaseManager(config['db_connection'])

    # Create and start game server
    server = GameServer(config['host'], config['port'], db_manager)

    try:
        logger.info("=== Subjugate Online - Game Server ===")
        logger.info(f"Starting on {config['host']}:{config['port']}")
        await server.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
