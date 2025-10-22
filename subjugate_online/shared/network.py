"""
Async Network Layer for Subjugate Online
Handles TCP connections, packet fragmentation, and session management
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Dict, Any
from collections import deque
import struct

from .protocol import Packet, PacketType, PacketBuilder


logger = logging.getLogger(__name__)


class NetworkSession:
    """Represents a network session with a client"""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                 session_id: str, remote_addr: tuple):
        self.reader = reader
        self.writer = writer
        self.session_id = session_id
        self.remote_addr = remote_addr
        self.authenticated = False
        self.account_id: Optional[int] = None
        self.character_id: Optional[int] = None
        self.username: Optional[str] = None
        self.connected_at = time.time()
        self.last_activity = time.time()
        self.packet_sequence = 0
        self.send_queue: deque = deque()
        self.receiving_buffer = b''
        self.is_closing = False

        # Stats
        self.packets_sent = 0
        self.packets_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0

    async def send_packet(self, packet: Packet):
        """Send a packet to the client"""
        if self.is_closing:
            return

        try:
            packet.sequence = self.packet_sequence
            self.packet_sequence = (self.packet_sequence + 1) % 0xFFFFFFFF

            data = packet.serialize()
            self.writer.write(data)
            await self.writer.drain()

            self.packets_sent += 1
            self.bytes_sent += len(data)
            self.last_activity = time.time()

            logger.debug(f"Sent packet {packet.packet_type} to {self.remote_addr}")

        except Exception as e:
            logger.error(f"Error sending packet to {self.remote_addr}: {e}")
            await self.close()

    async def receive_packet(self) -> Optional[Packet]:
        """Receive a packet from the client"""
        if self.is_closing:
            return None

        try:
            # Read header first
            if len(self.receiving_buffer) < Packet.HEADER_SIZE:
                data = await self.reader.read(Packet.HEADER_SIZE - len(self.receiving_buffer))
                if not data:
                    return None
                self.receiving_buffer += data

            # Parse header to get payload length
            header = self.receiving_buffer[:Packet.HEADER_SIZE]
            _, payload_length, _, _, _ = struct.unpack(Packet.HEADER_FORMAT, header)

            # Read full packet
            total_size = Packet.HEADER_SIZE + payload_length
            while len(self.receiving_buffer) < total_size:
                data = await self.reader.read(total_size - len(self.receiving_buffer))
                if not data:
                    return None
                self.receiving_buffer += data

            # Deserialize packet
            packet_data = self.receiving_buffer[:total_size]
            self.receiving_buffer = self.receiving_buffer[total_size:]

            packet = Packet.deserialize(packet_data)

            self.packets_received += 1
            self.bytes_received += len(packet_data)
            self.last_activity = time.time()

            logger.debug(f"Received packet {packet.packet_type} from {self.remote_addr}")

            return packet

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error receiving packet from {self.remote_addr}: {e}")
            await self.close()
            return None

    async def close(self):
        """Close the session"""
        if self.is_closing:
            return

        self.is_closing = True
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except Exception as e:
            logger.error(f"Error closing connection to {self.remote_addr}: {e}")

        logger.info(f"Session {self.session_id} closed. Stats - Sent: {self.packets_sent}/{self.bytes_sent}B, "
                   f"Received: {self.packets_received}/{self.bytes_received}B")

    def is_alive(self, timeout: float = 120.0) -> bool:
        """Check if session is still alive"""
        return not self.is_closing and (time.time() - self.last_activity) < timeout

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            'session_id': self.session_id,
            'remote_addr': f"{self.remote_addr[0]}:{self.remote_addr[1]}",
            'authenticated': self.authenticated,
            'account_id': self.account_id,
            'character_id': self.character_id,
            'username': self.username,
            'connected_duration': time.time() - self.connected_at,
            'last_activity': time.time() - self.last_activity,
            'packets_sent': self.packets_sent,
            'packets_received': self.packets_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received
        }


class NetworkServer:
    """Base network server for handling client connections"""

    def __init__(self, host: str, port: int, name: str = "Server"):
        self.host = host
        self.port = port
        self.name = name
        self.server: Optional[asyncio.Server] = None
        self.sessions: Dict[str, NetworkSession] = {}
        self.running = False
        self.packet_handlers: Dict[PacketType, Callable] = {}

        # Stats
        self.total_connections = 0
        self.total_packets_sent = 0
        self.total_packets_received = 0

    def register_handler(self, packet_type: PacketType, handler: Callable):
        """Register a packet handler"""
        self.packet_handlers[packet_type] = handler
        logger.info(f"Registered handler for {packet_type}")

    async def start(self):
        """Start the server"""
        self.running = True
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )

        addr = self.server.sockets[0].getsockname()
        logger.info(f"{self.name} started on {addr[0]}:{addr[1]}")

        # Start background tasks
        asyncio.create_task(self._cleanup_dead_sessions())
        asyncio.create_task(self._heartbeat_task())

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the server"""
        logger.info(f"Stopping {self.name}...")
        self.running = False

        # Close all sessions
        for session in list(self.sessions.values()):
            await session.close()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        logger.info(f"{self.name} stopped")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a new client connection"""
        remote_addr = writer.get_extra_info('peername')
        session_id = f"{remote_addr[0]}:{remote_addr[1]}:{time.time()}"

        session = NetworkSession(reader, writer, session_id, remote_addr)
        self.sessions[session_id] = session
        self.total_connections += 1

        logger.info(f"New connection from {remote_addr} (Total: {len(self.sessions)})")

        try:
            # Send handshake
            handshake = Packet(PacketType.HANDSHAKE, b'SUBJUGATE_ONLINE_V1')
            await session.send_packet(handshake)

            # Handle packets
            while self.running and session.is_alive():
                packet = await session.receive_packet()
                if packet is None:
                    break

                # Handle packet
                await self._handle_packet(session, packet)

        except asyncio.CancelledError:
            logger.info(f"Connection handler cancelled for {remote_addr}")
        except Exception as e:
            logger.error(f"Error handling client {remote_addr}: {e}", exc_info=True)
        finally:
            await session.close()
            if session_id in self.sessions:
                del self.sessions[session_id]
            logger.info(f"Client {remote_addr} disconnected (Remaining: {len(self.sessions)})")

    async def _handle_packet(self, session: NetworkSession, packet: Packet):
        """Handle a received packet"""
        try:
            handler = self.packet_handlers.get(packet.packet_type)
            if handler:
                await handler(session, packet)
            else:
                logger.warning(f"No handler for packet type {packet.packet_type}")

        except Exception as e:
            logger.error(f"Error handling packet {packet.packet_type}: {e}", exc_info=True)

    async def _cleanup_dead_sessions(self):
        """Periodically clean up dead sessions"""
        while self.running:
            await asyncio.sleep(30)

            dead_sessions = []
            for session_id, session in self.sessions.items():
                if not session.is_alive():
                    dead_sessions.append(session_id)

            for session_id in dead_sessions:
                session = self.sessions.get(session_id)
                if session:
                    logger.info(f"Cleaning up dead session {session_id}")
                    await session.close()
                    del self.sessions[session_id]

    async def _heartbeat_task(self):
        """Send periodic heartbeats to all clients"""
        while self.running:
            await asyncio.sleep(30)

            ping_packet = Packet(PacketType.PING, struct.pack('!d', time.time()))
            for session in list(self.sessions.values()):
                if session.authenticated:
                    try:
                        await session.send_packet(ping_packet)
                    except Exception as e:
                        logger.error(f"Error sending heartbeat to {session.remote_addr}: {e}")

    async def broadcast_packet(self, packet: Packet, exclude_session: Optional[str] = None):
        """Broadcast a packet to all connected sessions"""
        for session_id, session in self.sessions.items():
            if session_id != exclude_session and session.authenticated:
                try:
                    await session.send_packet(packet)
                except Exception as e:
                    logger.error(f"Error broadcasting to {session.remote_addr}: {e}")

    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)

    def get_authenticated_session_count(self) -> int:
        """Get number of authenticated sessions"""
        return sum(1 for s in self.sessions.values() if s.authenticated)

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        total_packets_sent = sum(s.packets_sent for s in self.sessions.values())
        total_packets_received = sum(s.packets_received for s in self.sessions.values())

        return {
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'running': self.running,
            'total_sessions': len(self.sessions),
            'authenticated_sessions': self.get_authenticated_session_count(),
            'total_connections': self.total_connections,
            'total_packets_sent': total_packets_sent,
            'total_packets_received': total_packets_received
        }
