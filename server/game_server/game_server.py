"""
Subjugate Online - Game Server
Main game server handling world simulation, combat, and player interactions
"""

import asyncio
import signal
import time
from typing import Dict, Optional
from shared.constants import (
    GAME_SERVER_HOST, GAME_SERVER_PORT, TICK_RATE, NETWORK_UPDATE_RATE,
    PacketType, ErrorCode, RESPAWN_TIME
)
from shared.utils import Logger, get_spawn_position
from server.network.protocol import (
    Packet, PacketBuffer, create_player_spawn, create_player_despawn,
    create_player_position_update, create_stats_update, create_damage_dealt,
    create_player_death, create_reincarnation_response, create_territory_status,
    create_territory_captured, create_chat_message, create_npc_spawn,
    create_npc_update, create_error_packet
)
from server.database.db_manager import DatabaseManager
from server.game_server.world_manager import WorldManager, PlayerEntity
from server.game_server.combat_system import CombatSystem
from server.game_server.reincarnation_system import ReincarnationSystem
from server.game_server.territory_system import TerritorySystem
from server.game_server.npc_ai import NPCAISystem

logger = Logger.get_logger(__name__)


class GameClientConnection:
    """Represents a client connection to game server"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, address):
        self.reader = reader
        self.writer = writer
        self.address = address
        self.buffer = PacketBuffer()
        self.character_id: Optional[int] = None
        self.session_token: Optional[str] = None
        self.last_heartbeat = time.time()

    async def send_packet(self, packet: Packet):
        """Send a packet to the client"""
        try:
            data = packet.serialize()
            self.writer.write(data)
            await self.writer.drain()
        except Exception as e:
            logger.error(f"Failed to send packet to {self.address}: {e}")

    async def receive_packet(self) -> Optional[Packet]:
        """Receive a packet from the client"""
        try:
            data = await self.reader.read(4096)
            if not data:
                return None

            self.buffer.add_data(data)

            if self.buffer.has_complete_packet():
                return self.buffer.get_packet()

            return None

        except Exception as e:
            logger.error(f"Failed to receive packet from {self.address}: {e}")
            return None

    def close(self):
        """Close the connection"""
        try:
            self.writer.close()
        except:
            pass


class GameServer:
    """Main game server"""

    def __init__(self, host: str = GAME_SERVER_HOST, port: int = GAME_SERVER_PORT):
        self.host = host
        self.port = port

        # Initialize managers
        self.db = DatabaseManager()
        self.world = WorldManager()
        self.combat = CombatSystem(self.world)
        self.reincarnation = ReincarnationSystem(self.db)
        self.territory = TerritorySystem(self.world, self.db)
        self.npc_ai = NPCAISystem(self.world)

        # Client connections
        self.clients: Dict[str, GameClientConnection] = {}
        self.character_to_client: Dict[int, str] = {}  # character_id -> client_id

        # Server state
        self.running = False
        self.server = None
        self.tick_time = 1.0 / TICK_RATE
        self.network_update_time = 1.0 / NETWORK_UPDATE_RATE

        # Respawn queue
        self.respawn_queue: Dict[int, float] = {}  # {character_id: respawn_time}

    async def start(self):
        """Start the game server"""
        self.running = True

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Spawn initial NPCs
        self.npc_ai.spawn_initial_npcs()

        # Start server
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        logger.info(f"Game Server started on {self.host}:{self.port}")

        # Start game loops
        asyncio.create_task(self.game_loop())
        asyncio.create_task(self.network_sync_loop())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the game server"""
        logger.info("Shutting down game server...")
        self.running = False

        # Save all player states
        for character_id in list(self.character_to_client.keys()):
            await self.handle_player_disconnect(character_id)

        # Close all client connections
        for client in list(self.clients.values()):
            client.close()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("Game server stopped")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new client connection"""
        address = writer.get_extra_info('peername')
        logger.info(f"New game client connection from {address}")

        client = GameClientConnection(reader, writer, address)
        client_id = f"{address[0]}:{address[1]}"
        self.clients[client_id] = client

        try:
            while self.running:
                packet = await client.receive_packet()

                if packet is None:
                    if reader.at_eof():
                        break
                    continue

                # Handle packet
                await self.handle_packet(client, client_id, packet)

        except Exception as e:
            logger.error(f"Error handling game client {address}: {e}")

        finally:
            # Cleanup
            if client.character_id:
                await self.handle_player_disconnect(client.character_id)

            client.close()
            if client_id in self.clients:
                del self.clients[client_id]

            logger.info(f"Game client disconnected: {address}")

    async def handle_packet(self, client: GameClientConnection, client_id: str, packet: Packet):
        """Handle incoming packet from client"""
        try:
            if packet.packet_type == PacketType.GAME_SERVER_CONNECT:
                await self.handle_game_connect(client, client_id, packet)

            elif packet.packet_type == PacketType.PLAYER_MOVE:
                await self.handle_player_move(client, packet)

            elif packet.packet_type == PacketType.ATTACK_REQUEST:
                await self.handle_attack_request(client, packet)

            elif packet.packet_type == PacketType.SKILL_USE:
                await self.handle_skill_use(client, packet)

            elif packet.packet_type == PacketType.REINCARNATION_REQUEST:
                await self.handle_reincarnation_request(client, packet)

            elif packet.packet_type == PacketType.CHAT_MESSAGE:
                await self.handle_chat_message(client, packet)

            elif packet.packet_type == PacketType.HEARTBEAT:
                client.last_heartbeat = time.time()

            else:
                logger.warning(f"Unknown packet type: {packet.packet_type}")

        except Exception as e:
            logger.error(f"Error handling packet {packet.packet_type}: {e}")
            await client.send_packet(create_error_packet(ErrorCode.INVALID_PACKET, str(e)))

    async def handle_game_connect(self, client: GameClientConnection, client_id: str, packet: Packet):
        """Handle game server connection/handshake"""
        session_token = packet.data.get('session_token', '')
        character_id = packet.data.get('character_id', 0)

        # Validate session
        session = self.db.validate_session(session_token)
        if not session:
            await client.send_packet(create_error_packet(
                ErrorCode.INVALID_SESSION,
                "Invalid session"
            ))
            client.close()
            return

        # Get character
        character = self.db.get_character_by_id(character_id)
        if not character or character.account_id != session.account_id:
            await client.send_packet(create_error_packet(
                ErrorCode.INVALID_CHARACTER,
                "Invalid character"
            ))
            client.close()
            return

        # Store client info
        client.character_id = character_id
        client.session_token = session_token
        self.character_to_client[character_id] = client_id

        # Add player to world
        character_data = {
            'character_id': character.id,
            'name': character.name,
            'level': character.level,
            'hp': character.hp,
            'max_hp': character.max_hp,
            'mp': character.mp,
            'max_mp': character.max_mp,
            'attack': character.attack,
            'defense': character.defense,
            'speed': character.speed,
            'position_x': character.position_x,
            'position_y': character.position_y,
            'position_z': character.position_z,
            'rotation': character.rotation,
            'game_mode': character.game_mode,
            'reincarnation_count': character.reincarnation_count,
            'reincarnation_perks': character.reincarnation_perks or {}
        }

        player = self.world.add_player(character_id, character_data)

        # Apply reincarnation perks
        if character.reincarnation_perks:
            self.reincarnation.apply_reincarnation_perks_to_player(player, character.reincarnation_perks)

        # Apply territory buffs
        self.territory.apply_territory_buffs_to_player(player, character_id)

        # Mark online in database
        self.db.set_character_online(character_id, True)

        logger.info(f"Player joined game: {character.name} (ID: {character_id})")

        # Send spawn to joining player (self)
        await client.send_packet(create_player_spawn(character_id, player.get_stats()))

        # Send existing players to joining player
        for existing_player in self.world.get_visible_players(character_id):
            if existing_player.character_id != character_id:
                await client.send_packet(create_player_spawn(
                    existing_player.character_id,
                    existing_player.get_stats()
                ))

        # Send existing NPCs to joining player
        for npc in self.world.get_visible_npcs(character_id):
            await client.send_packet(create_npc_spawn(npc.instance_id, npc.get_data()))

        # Send territory status
        await client.send_packet(create_territory_status(self.territory.get_territory_status()))

        # Broadcast spawn to other players
        await self.broadcast_to_nearby(character_id, create_player_spawn(character_id, player.get_stats()))

    async def handle_player_move(self, client: GameClientConnection, packet: Packet):
        """Handle player movement"""
        if not client.character_id:
            return

        x = packet.data.get('x', 0.0)
        y = packet.data.get('y', 0.0)
        z = packet.data.get('z', 0.0)
        rotation = packet.data.get('rotation', 0.0)

        # Update position in world
        self.world.update_player_position(client.character_id, x, y, z, rotation)

    async def handle_attack_request(self, client: GameClientConnection, packet: Packet):
        """Handle basic attack request"""
        if not client.character_id:
            return

        target_id = packet.data.get('target_id', 0)
        target_type = packet.data.get('target_type', 'npc')

        # Execute attack
        result = self.combat.basic_attack(client.character_id, target_id, target_type)

        if result:
            # Broadcast damage
            damage_packet = create_damage_dealt(
                result['attacker_id'],
                result['target_id'],
                result['damage'],
                result['target_hp']
            )

            await self.broadcast_to_nearby(client.character_id, damage_packet)

            # Handle death
            if result['target_died']:
                if target_type == 'npc':
                    death_data = self.npc_ai.handle_npc_death(target_id, client.character_id)

                    # Grant XP
                    if death_data:
                        self.combat.grant_experience(client.character_id, death_data['xp_reward'])

                        # Update player stats
                        player = self.world.get_player(client.character_id)
                        if player:
                            # Update kill count in database
                            self.db.update_character_stats(client.character_id, {
                                'total_kills': player.level  # Simplified
                            })

                elif target_type == 'player':
                    await self.handle_player_death_event(target_id, client.character_id)

    async def handle_skill_use(self, client: GameClientConnection, packet: Packet):
        """Handle skill use"""
        if not client.character_id:
            return

        skill_id = packet.data.get('skill_id', 0)
        target_id = packet.data.get('target_id')
        target_type = packet.data.get('target_type', 'npc')

        # Use skill
        result = self.combat.use_skill(client.character_id, skill_id, target_id, target_type)

        if result:
            # Handle different skill results
            if 'heal_amount' in result:
                # Healing skill
                await client.send_packet(create_stats_update(
                    client.character_id,
                    {'hp': result['caster_hp'], 'mp': result.get('caster_mp', 0)}
                ))
            else:
                # Damage skill
                for target_data in result.get('targets_hit', []):
                    target_id, damage, target_hp, target_died = target_data

                    damage_packet = create_damage_dealt(
                        client.character_id,
                        target_id,
                        damage,
                        target_hp
                    )

                    await self.broadcast_to_nearby(client.character_id, damage_packet)

                    if target_died and target_type == 'npc':
                        death_data = self.npc_ai.handle_npc_death(target_id, client.character_id)
                        if death_data:
                            self.combat.grant_experience(client.character_id, death_data['xp_reward'])

    async def handle_reincarnation_request(self, client: GameClientConnection, packet: Packet):
        """Handle reincarnation request"""
        if not client.character_id:
            return

        # Perform reincarnation
        result = self.reincarnation.perform_reincarnation(client.character_id)

        if result:
            # Send success
            await client.send_packet(create_reincarnation_response(
                success=True,
                perks=result['total_perks'],
                message=f"Reincarnation {result['reincarnation_count']} complete!"
            ))

            # Remove player from world and reload
            self.world.remove_player(client.character_id)

            # Reload character
            character = self.db.get_character_by_id(client.character_id)
            character_data = {
                'character_id': character.id,
                'name': character.name,
                'level': character.level,
                'hp': character.hp,
                'max_hp': character.max_hp,
                'mp': character.mp,
                'max_mp': character.max_mp,
                'attack': character.attack,
                'defense': character.defense,
                'speed': character.speed,
                'position_x': character.position_x,
                'position_y': character.position_y,
                'position_z': character.position_z,
                'rotation': character.rotation,
                'game_mode': character.game_mode,
                'reincarnation_count': character.reincarnation_count,
                'reincarnation_perks': character.reincarnation_perks or {}
            }

            player = self.world.add_player(client.character_id, character_data)
            self.reincarnation.apply_reincarnation_perks_to_player(player, character.reincarnation_perks)

        else:
            await client.send_packet(create_reincarnation_response(
                success=False,
                error_code=ErrorCode.INSUFFICIENT_LEVEL,
                message="Cannot reincarnate"
            ))

    async def handle_chat_message(self, client: GameClientConnection, packet: Packet):
        """Handle chat message"""
        if not client.character_id:
            return

        message = packet.data.get('message', '')
        player = self.world.get_player(client.character_id)

        if player:
            chat_packet = create_chat_message(player.name, message)
            await self.broadcast_to_all(chat_packet)

    async def handle_player_death_event(self, character_id: int, killer_id: Optional[int] = None):
        """Handle player death event"""
        death_data = self.combat.handle_player_death(character_id, killer_id)

        # Broadcast death
        death_packet = create_player_death(character_id, killer_id)
        await self.broadcast_to_all(death_packet)

        # Queue respawn
        self.respawn_queue[character_id] = time.time() + RESPAWN_TIME

        # Log event
        self.db.log_event('player_death', character_id, {'killer_id': killer_id})

    async def handle_player_disconnect(self, character_id: int):
        """Handle player disconnect"""
        player = self.world.get_player(character_id)
        if player:
            # Save character state
            self.db.update_character_position(
                character_id,
                player.position[0],
                player.position[1],
                player.position[2],
                player.rotation
            )

            self.db.update_character_stats(character_id, {
                'hp': player.hp,
                'mp': player.mp
            })

            self.db.set_character_online(character_id, False)

            # Remove from world
            self.world.remove_player(character_id)

            # Broadcast despawn
            await self.broadcast_to_all(create_player_despawn(character_id))

            logger.info(f"Player left game: {player.name} (ID: {character_id})")

        # Remove from tracking
        if character_id in self.character_to_client:
            del self.character_to_client[character_id]

    async def game_loop(self):
        """Main game loop - handles game logic updates"""
        logger.info("Game loop started")

        last_time = time.time()

        while self.running:
            current_time = time.time()
            delta_time = current_time - last_time
            last_time = current_time

            try:
                # Update NPC AI
                self.npc_ai.update(delta_time)

                # Update territory system
                self.territory.update(delta_time)

                # Handle respawns
                await self.handle_respawns(current_time)

            except Exception as e:
                logger.error(f"Error in game loop: {e}")

            # Sleep to maintain tick rate
            await asyncio.sleep(self.tick_time)

    async def network_sync_loop(self):
        """Network synchronization loop - broadcasts state updates"""
        logger.info("Network sync loop started")

        while self.running:
            try:
                # Broadcast player positions
                for player in self.world.get_all_players():
                    position_packet = create_player_position_update(
                        player.character_id,
                        player.position[0],
                        player.position[1],
                        player.position[2],
                        player.rotation
                    )

                    await self.broadcast_to_nearby(player.character_id, position_packet, exclude_self=True)

                # Broadcast NPC updates
                for npc in self.world.get_all_npcs():
                    if npc.hp <= 0:
                        continue

                    npc_packet = create_npc_update(npc.instance_id, npc.get_data())

                    # Send to all nearby players
                    nearby_players = self.world.get_nearby_players(npc.position, 100.0)
                    for player in nearby_players:
                        client_id = self.character_to_client.get(player.character_id)
                        if client_id and client_id in self.clients:
                            await self.clients[client_id].send_packet(npc_packet)

            except Exception as e:
                logger.error(f"Error in network sync loop: {e}")

            await asyncio.sleep(self.network_update_time)

    async def handle_respawns(self, current_time: float):
        """Handle player respawns"""
        respawned = []

        for character_id, respawn_time in self.respawn_queue.items():
            if current_time >= respawn_time:
                spawn_pos = get_spawn_position(0)
                if self.combat.respawn_player(character_id, spawn_pos):
                    respawned.append(character_id)

                    # Broadcast respawn
                    player = self.world.get_player(character_id)
                    if player:
                        await self.broadcast_to_all(create_player_spawn(character_id, player.get_stats()))

        # Remove from queue
        for character_id in respawned:
            del self.respawn_queue[character_id]

    async def broadcast_to_nearby(self, character_id: int, packet: Packet, exclude_self: bool = False):
        """Broadcast packet to nearby players"""
        player = self.world.get_player(character_id)
        if not player:
            return

        nearby_players = self.world.get_visible_players(character_id)

        for nearby_player in nearby_players:
            if exclude_self and nearby_player.character_id == character_id:
                continue

            client_id = self.character_to_client.get(nearby_player.character_id)
            if client_id and client_id in self.clients:
                await self.clients[client_id].send_packet(packet)

    async def broadcast_to_all(self, packet: Packet):
        """Broadcast packet to all connected players"""
        for client in self.clients.values():
            if client.character_id:
                await client.send_packet(packet)


async def main():
    """Main entry point"""
    server = GameServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == '__main__':
    asyncio.run(main())
