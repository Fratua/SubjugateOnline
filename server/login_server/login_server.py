"""
Subjugate Online - Login Server
Handles authentication, character creation, and session management
"""

import asyncio
import signal
from typing import Dict, Optional
from shared.constants import (
    LOGIN_SERVER_HOST, LOGIN_SERVER_PORT, GAME_SERVER_HOST,
    GAME_SERVER_PORT, PacketType, ErrorCode, GameMode
)
from shared.utils import Logger, validate_username, validate_password, validate_character_name
from server.network.protocol import (
    Packet, PacketBuffer, create_login_response, create_register_response,
    create_character_list_response, create_character_create_response,
    create_character_select_response, create_error_packet
)
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class ClientConnection:
    """Represents a client connection"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, address):
        self.reader = reader
        self.writer = writer
        self.address = address
        self.buffer = PacketBuffer()
        self.session_token: Optional[str] = None
        self.account_id: Optional[int] = None

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


class LoginServer:
    """Login server managing authentication and character selection"""

    def __init__(self, host: str = LOGIN_SERVER_HOST, port: int = LOGIN_SERVER_PORT):
        self.host = host
        self.port = port
        self.db = DatabaseManager()
        self.clients: Dict[str, ClientConnection] = {}
        self.running = False
        self.server = None

    async def start(self):
        """Start the login server"""
        self.running = True

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Start server
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )

        logger.info(f"Login Server started on {self.host}:{self.port}")

        # Start session cleanup task
        asyncio.create_task(self.session_cleanup_loop())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the login server"""
        logger.info("Shutting down login server...")
        self.running = False

        # Close all client connections
        for client in list(self.clients.values()):
            client.close()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info("Login server stopped")

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new client connection"""
        address = writer.get_extra_info('peername')
        logger.info(f"New connection from {address}")

        client = ClientConnection(reader, writer, address)
        client_id = f"{address[0]}:{address[1]}"
        self.clients[client_id] = client

        try:
            while self.running:
                packet = await client.receive_packet()

                if packet is None:
                    # Check if connection is closed
                    if reader.at_eof():
                        break
                    continue

                # Handle packet
                await self.handle_packet(client, packet)

        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")

        finally:
            # Cleanup
            client.close()
            if client_id in self.clients:
                del self.clients[client_id]
            logger.info(f"Client disconnected: {address}")

    async def handle_packet(self, client: ClientConnection, packet: Packet):
        """Handle incoming packet from client"""
        try:
            if packet.packet_type == PacketType.LOGIN_REQUEST:
                await self.handle_login(client, packet)

            elif packet.packet_type == PacketType.REGISTER_REQUEST:
                await self.handle_register(client, packet)

            elif packet.packet_type == PacketType.CHARACTER_LIST_REQUEST:
                await self.handle_character_list(client, packet)

            elif packet.packet_type == PacketType.CHARACTER_CREATE_REQUEST:
                await self.handle_character_create(client, packet)

            elif packet.packet_type == PacketType.CHARACTER_SELECT_REQUEST:
                await self.handle_character_select(client, packet)

            else:
                logger.warning(f"Unknown packet type: {packet.packet_type}")
                await client.send_packet(create_error_packet(
                    ErrorCode.INVALID_PACKET,
                    "Unknown packet type"
                ))

        except Exception as e:
            logger.error(f"Error handling packet {packet.packet_type}: {e}")
            await client.send_packet(create_error_packet(
                ErrorCode.INVALID_PACKET,
                str(e)
            ))

    async def handle_login(self, client: ClientConnection, packet: Packet):
        """Handle login request"""
        username = packet.data.get('username', '')
        password = packet.data.get('password', '')

        logger.info(f"Login attempt: {username}")

        # Authenticate
        account = self.db.authenticate_account(username, password)

        if not account:
            await client.send_packet(create_login_response(
                success=False,
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid username or password"
            ))
            return

        # Create session
        ip_address = client.address[0]
        session = self.db.create_session(account.id, ip_address)

        if not session:
            await client.send_packet(create_login_response(
                success=False,
                error_code=ErrorCode.INVALID_SESSION,
                message="Failed to create session"
            ))
            return

        # Update client state
        client.session_token = session.session_token
        client.account_id = account.id

        # Send success
        await client.send_packet(create_login_response(
            success=True,
            session_token=session.session_token,
            message="Login successful"
        ))

        logger.info(f"Login successful: {username}")

    async def handle_register(self, client: ClientConnection, packet: Packet):
        """Handle registration request"""
        username = packet.data.get('username', '')
        password = packet.data.get('password', '')
        email = packet.data.get('email')

        logger.info(f"Registration attempt: {username}")

        # Validate input
        if not validate_username(username):
            await client.send_packet(create_register_response(
                success=False,
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid username (3-16 alphanumeric characters)"
            ))
            return

        if not validate_password(password):
            await client.send_packet(create_register_response(
                success=False,
                error_code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid password (minimum 6 characters)"
            ))
            return

        # Create account
        account = self.db.create_account(username, password, email)

        if not account:
            await client.send_packet(create_register_response(
                success=False,
                error_code=ErrorCode.ACCOUNT_EXISTS,
                message="Username already exists"
            ))
            return

        # Send success
        await client.send_packet(create_register_response(
            success=True,
            message="Registration successful"
        ))

        logger.info(f"Registration successful: {username}")

    async def handle_character_list(self, client: ClientConnection, packet: Packet):
        """Handle character list request"""
        session_token = packet.data.get('session_token', '')

        # Validate session
        session = self.db.validate_session(session_token)
        if not session:
            await client.send_packet(create_error_packet(
                ErrorCode.INVALID_SESSION,
                "Invalid or expired session"
            ))
            return

        # Get characters
        characters = self.db.get_characters_by_account(session.account_id)

        # Build character list
        char_list = []
        for char in characters:
            char_list.append({
                'id': char.id,
                'name': char.name,
                'level': char.level,
                'game_mode': char.game_mode,
                'reincarnation_count': char.reincarnation_count,
                'is_dead': char.is_dead
            })

        await client.send_packet(create_character_list_response(char_list))

    async def handle_character_create(self, client: ClientConnection, packet: Packet):
        """Handle character creation request"""
        session_token = packet.data.get('session_token', '')
        character_name = packet.data.get('character_name', '')
        game_mode = packet.data.get('game_mode', GameMode.HARDCORE_IRONMAN)

        # Validate session
        session = self.db.validate_session(session_token)
        if not session:
            await client.send_packet(create_character_create_response(
                success=False,
                error_code=ErrorCode.INVALID_SESSION,
                message="Invalid or expired session"
            ))
            return

        # Validate name
        if not validate_character_name(character_name):
            await client.send_packet(create_character_create_response(
                success=False,
                error_code=ErrorCode.INVALID_CHARACTER,
                message="Invalid character name (3-16 alphanumeric characters)"
            ))
            return

        # Create character
        character = self.db.create_character(session.account_id, character_name, game_mode)

        if not character:
            await client.send_packet(create_character_create_response(
                success=False,
                error_code=ErrorCode.CHARACTER_EXISTS,
                message="Character name already exists"
            ))
            return

        # Send success
        await client.send_packet(create_character_create_response(
            success=True,
            character_id=character.id,
            message="Character created successfully"
        ))

        logger.info(f"Character created: {character_name} (ID: {character.id})")

    async def handle_character_select(self, client: ClientConnection, packet: Packet):
        """Handle character selection request"""
        session_token = packet.data.get('session_token', '')
        character_id = packet.data.get('character_id', 0)

        # Validate session
        session = self.db.validate_session(session_token)
        if not session:
            await client.send_packet(create_character_select_response(
                success=False,
                error_code=ErrorCode.INVALID_SESSION,
                message="Invalid or expired session"
            ))
            return

        # Get character
        character = self.db.get_character_by_id(character_id)

        if not character or character.account_id != session.account_id:
            await client.send_packet(create_character_select_response(
                success=False,
                error_code=ErrorCode.INVALID_CHARACTER,
                message="Invalid character"
            ))
            return

        # Build character data
        character_data = {
            'id': character.id,
            'name': character.name,
            'level': character.level,
            'experience': character.experience,
            'hp': character.hp,
            'max_hp': character.max_hp,
            'mp': character.mp,
            'max_mp': character.max_mp,
            'attack': character.attack,
            'defense': character.defense,
            'speed': character.speed,
            'position': [character.position_x, character.position_y, character.position_z],
            'rotation': character.rotation,
            'game_mode': character.game_mode,
            'reincarnation_count': character.reincarnation_count,
            'reincarnation_perks': character.reincarnation_perks,
            'session_token': session_token
        }

        # Send success with game server info
        await client.send_packet(create_character_select_response(
            success=True,
            character_data=character_data,
            game_server_host=GAME_SERVER_HOST,
            game_server_port=GAME_SERVER_PORT,
            message="Character selected"
        ))

        logger.info(f"Character selected: {character.name} (ID: {character.id})")

    async def session_cleanup_loop(self):
        """Periodically cleanup expired sessions"""
        while self.running:
            await asyncio.sleep(300)  # Every 5 minutes
            try:
                self.db.cleanup_expired_sessions()
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")


async def main():
    """Main entry point"""
    server = LoginServer()
    try:
        await server.start()
    except KeyboardInterrupt:
        await server.stop()


if __name__ == '__main__':
    asyncio.run(main())
