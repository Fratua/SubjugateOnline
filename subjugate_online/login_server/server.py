"""
Login Server Implementation
Handles player authentication and character management
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from subjugate_online.shared.network import NetworkServer, NetworkSession
from subjugate_online.shared.protocol import Packet, PacketType, PacketBuilder, PacketParser
from subjugate_online.shared.database import DatabaseManager, Account, Character, GameMode
from subjugate_online.shared.utils import (
    hash_password, verify_password, generate_session_token,
    validate_username, validate_character_name, validate_email
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LoginServer(NetworkServer):
    """Login server for handling authentication and character selection"""

    def __init__(self, host: str, port: int, db_manager: DatabaseManager):
        super().__init__(host, port, "LoginServer")
        self.db_manager = db_manager

        # Register packet handlers
        self.register_handler(PacketType.LOGIN_REQUEST, self._handle_login)
        self.register_handler(PacketType.REGISTER_REQUEST, self._handle_register)
        self.register_handler(PacketType.CHARACTER_LIST_REQUEST, self._handle_character_list)
        self.register_handler(PacketType.CHARACTER_CREATE, self._handle_character_create)
        self.register_handler(PacketType.CHARACTER_DELETE, self._handle_character_delete)
        self.register_handler(PacketType.CHARACTER_SELECT, self._handle_character_select)
        self.register_handler(PacketType.PONG, self._handle_pong)

    async def _handle_login(self, session: NetworkSession, packet: Packet):
        """Handle login request"""
        try:
            username, password_hash, version = PacketParser.parse_login_request(packet)

            logger.info(f"Login attempt from {session.remote_addr}: {username}")

            # Validate input
            if not validate_username(username):
                response = PacketBuilder.login_response(False, "Invalid username format")
                await session.send_packet(response)
                return

            # Query database
            db_session = self.db_manager.get_session()
            try:
                account = db_session.query(Account).filter_by(username=username).first()

                if not account:
                    response = PacketBuilder.login_response(False, "Invalid username or password")
                    await session.send_packet(response)
                    return

                # Verify password
                if not verify_password(password_hash, account.password_hash):
                    response = PacketBuilder.login_response(False, "Invalid username or password")
                    await session.send_packet(response)
                    return

                # Check if banned
                if account.is_banned:
                    response = PacketBuilder.login_response(False, "Account is banned")
                    await session.send_packet(response)
                    return

                # Generate session token
                session_token = generate_session_token()
                account.session_token = session_token
                account.last_login = datetime.utcnow()
                db_session.commit()

                # Update session
                session.authenticated = True
                session.account_id = account.id
                session.username = username

                # Send success response
                response = PacketBuilder.login_response(True, "Login successful", session_token)
                await session.send_packet(response)

                logger.info(f"User {username} logged in successfully from {session.remote_addr}")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling login: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_register(self, session: NetworkSession, packet: Packet):
        """Handle registration request"""
        try:
            # Parse registration data
            data, _ = PacketParser.parse_json_payload(packet)
            username = data.get('username', '')
            password = data.get('password', '')
            email = data.get('email', '')

            logger.info(f"Registration attempt from {session.remote_addr}: {username}")

            # Validate input
            if not validate_username(username):
                response = PacketBuilder.error_message(400, "Invalid username format. Use 3-32 alphanumeric characters, _ or -")
                await session.send_packet(response)
                return

            if not password or len(password) < 6:
                response = PacketBuilder.error_message(400, "Password must be at least 6 characters")
                await session.send_packet(response)
                return

            if not validate_email(email):
                response = PacketBuilder.error_message(400, "Invalid email format")
                await session.send_packet(response)
                return

            # Create account
            db_session = self.db_manager.get_session()
            try:
                # Check if username exists
                existing = db_session.query(Account).filter_by(username=username).first()
                if existing:
                    response = PacketBuilder.error_message(409, "Username already exists")
                    await session.send_packet(response)
                    return

                # Check if email exists
                existing = db_session.query(Account).filter_by(email=email).first()
                if existing:
                    response = PacketBuilder.error_message(409, "Email already registered")
                    await session.send_packet(response)
                    return

                # Create new account
                password_hash = hash_password(password)
                account = Account(
                    username=username,
                    password_hash=password_hash,
                    email=email
                )
                db_session.add(account)
                db_session.commit()

                # Send success response
                response_data = {
                    'success': True,
                    'message': 'Account created successfully',
                    'account_id': account.id
                }
                response = Packet(PacketType.REGISTER_RESPONSE, Packet.pack_json(None, response_data))
                await session.send_packet(response)

                logger.info(f"New account created: {username} (ID: {account.id})")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling registration: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_character_list(self, session: NetworkSession, packet: Packet):
        """Handle character list request"""
        if not session.authenticated:
            response = PacketBuilder.error_message(401, "Not authenticated")
            await session.send_packet(response)
            return

        try:
            db_session = self.db_manager.get_session()
            try:
                characters = db_session.query(Character).filter_by(
                    account_id=session.account_id
                ).all()

                char_list = [char.to_dict() for char in characters]

                response_data = {
                    'characters': char_list
                }
                response = Packet(PacketType.CHARACTER_LIST_RESPONSE,
                                Packet.pack_json(None, response_data))
                await session.send_packet(response)

                logger.debug(f"Sent character list to {session.username}: {len(char_list)} characters")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling character list: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_character_create(self, session: NetworkSession, packet: Packet):
        """Handle character creation request"""
        if not session.authenticated:
            response = PacketBuilder.error_message(401, "Not authenticated")
            await session.send_packet(response)
            return

        try:
            # Parse character data
            data, _ = PacketParser.parse_json_payload(packet)
            char_name = data.get('name', '')
            game_mode = data.get('game_mode', 'hardcore_ironman')

            logger.info(f"Character creation attempt from {session.username}: {char_name}")

            # Validate input
            if not validate_character_name(char_name):
                response = PacketBuilder.error_message(400, "Invalid character name. Use 3-32 alphanumeric characters and spaces")
                await session.send_packet(response)
                return

            # Validate game mode
            try:
                game_mode_enum = GameMode[game_mode.upper()]
            except KeyError:
                response = PacketBuilder.error_message(400, "Invalid game mode")
                await session.send_packet(response)
                return

            # Create character
            db_session = self.db_manager.get_session()
            try:
                # Check if name exists
                existing = db_session.query(Character).filter_by(name=char_name).first()
                if existing:
                    response = PacketBuilder.error_message(409, "Character name already exists")
                    await session.send_packet(response)
                    return

                # Check character limit (max 5 per account)
                char_count = db_session.query(Character).filter_by(
                    account_id=session.account_id
                ).count()

                if char_count >= 5:
                    response = PacketBuilder.error_message(400, "Maximum 5 characters per account")
                    await session.send_packet(response)
                    return

                # Create new character
                character = Character(
                    account_id=session.account_id,
                    name=char_name,
                    game_mode=game_mode_enum
                )
                db_session.add(character)
                db_session.commit()

                # Send success response with character info
                response = PacketBuilder.character_info(character.to_dict())
                await session.send_packet(response)

                logger.info(f"Character created: {char_name} (ID: {character.id}) by {session.username}")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling character creation: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_character_delete(self, session: NetworkSession, packet: Packet):
        """Handle character deletion request"""
        if not session.authenticated:
            response = PacketBuilder.error_message(401, "Not authenticated")
            await session.send_packet(response)
            return

        try:
            # Parse character ID
            data, _ = PacketParser.parse_json_payload(packet)
            char_id = data.get('character_id')

            logger.info(f"Character deletion attempt from {session.username}: ID {char_id}")

            db_session = self.db_manager.get_session()
            try:
                character = db_session.query(Character).filter_by(
                    id=char_id,
                    account_id=session.account_id
                ).first()

                if not character:
                    response = PacketBuilder.error_message(404, "Character not found")
                    await session.send_packet(response)
                    return

                # Delete character
                char_name = character.name
                db_session.delete(character)
                db_session.commit()

                # Send success response
                response_data = {
                    'success': True,
                    'message': f'Character {char_name} deleted'
                }
                response = Packet(PacketType.CHARACTER_DELETE,
                                Packet.pack_json(None, response_data))
                await session.send_packet(response)

                logger.info(f"Character deleted: {char_name} (ID: {char_id}) by {session.username}")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling character deletion: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_character_select(self, session: NetworkSession, packet: Packet):
        """Handle character selection request"""
        if not session.authenticated:
            response = PacketBuilder.error_message(401, "Not authenticated")
            await session.send_packet(response)
            return

        try:
            # Parse character ID
            data, _ = PacketParser.parse_json_payload(packet)
            char_id = data.get('character_id')

            logger.info(f"Character selection from {session.username}: ID {char_id}")

            db_session = self.db_manager.get_session()
            try:
                character = db_session.query(Character).filter_by(
                    id=char_id,
                    account_id=session.account_id
                ).first()

                if not character:
                    response = PacketBuilder.error_message(404, "Character not found")
                    await session.send_packet(response)
                    return

                # Update session
                session.character_id = char_id

                # Send game server connection info
                response_data = {
                    'success': True,
                    'character': character.to_dict(),
                    'game_server_host': 'localhost',  # TODO: Load from config
                    'game_server_port': 8889,
                    'transfer_token': session.session_token
                }
                response = Packet(PacketType.CHARACTER_SELECT,
                                Packet.pack_json(None, response_data))
                await session.send_packet(response)

                logger.info(f"Character selected: {character.name} (ID: {char_id}) by {session.username}")

            finally:
                self.db_manager.close_session(db_session)

        except Exception as e:
            logger.error(f"Error handling character selection: {e}", exc_info=True)
            response = PacketBuilder.error_message(500, "Internal server error")
            await session.send_packet(response)

    async def _handle_pong(self, session: NetworkSession, packet: Packet):
        """Handle pong response"""
        session.last_activity = datetime.now().timestamp()


async def main():
    """Main entry point for login server"""
    # Configuration
    config = {
        'host': '0.0.0.0',
        'port': 8888,
        'db_connection': 'postgresql://subjugate:subjugate123@localhost:5432/subjugate_online'
    }

    # Initialize database
    db_manager = DatabaseManager(config['db_connection'])
    db_manager.create_all_tables()
    db_manager.initialize_world_data()

    # Create and start login server
    server = LoginServer(config['host'], config['port'], db_manager)

    try:
        logger.info("=== Subjugate Online - Login Server ===")
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
