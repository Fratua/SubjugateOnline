"""
Client-side networking for Subjugate Online
"""

import socket
import threading
import queue
import logging
import time
from typing import Optional, Callable, Dict, Any
import struct

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from subjugate_online.shared.protocol import Packet, PacketType, PacketBuilder

logger = logging.getLogger(__name__)


class NetworkClient:
    """Client-side network handler"""

    def __init__(self):
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False

        self.receive_thread: Optional[threading.Thread] = None
        self.packet_queue: queue.Queue = queue.Queue()

        self.packet_handlers: Dict[PacketType, Callable] = {}

        self.sequence = 0
        self.last_ping = 0

    def connect(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """Connect to server"""
        try:
            logger.info(f"Connecting to {host}:{port}...")

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            self.socket.connect((host, port))
            self.socket.settimeout(None)  # Remove timeout after connecting

            self.connected = True
            self.running = True

            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()

            logger.info(f"Connected to {host}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from server"""
        logger.info("Disconnecting...")
        self.running = False
        self.connected = False

        if self.socket:
            try:
                self.socket.close()
            except:
                pass

        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)

        logger.info("Disconnected")

    def send_packet(self, packet: Packet) -> bool:
        """Send a packet to server"""
        if not self.connected or not self.socket:
            return False

        try:
            packet.sequence = self.sequence
            self.sequence = (self.sequence + 1) % 0xFFFFFFFF

            data = packet.serialize()
            self.socket.sendall(data)

            logger.debug(f"Sent packet: {packet.packet_type}")
            return True

        except Exception as e:
            logger.error(f"Error sending packet: {e}")
            self.connected = False
            return False

    def _receive_loop(self):
        """Background thread for receiving packets"""
        buffer = b''

        while self.running and self.connected:
            try:
                # Receive data
                data = self.socket.recv(4096)
                if not data:
                    logger.info("Server closed connection")
                    self.connected = False
                    break

                buffer += data

                # Process complete packets
                while len(buffer) >= Packet.HEADER_SIZE:
                    # Parse header to get packet size
                    header = buffer[:Packet.HEADER_SIZE]
                    _, payload_length, _, _, _ = struct.unpack(Packet.HEADER_FORMAT, header)

                    total_size = Packet.HEADER_SIZE + payload_length

                    # Check if we have complete packet
                    if len(buffer) < total_size:
                        break

                    # Extract and deserialize packet
                    packet_data = buffer[:total_size]
                    buffer = buffer[total_size:]

                    try:
                        packet = Packet.deserialize(packet_data)
                        self.packet_queue.put(packet)
                        logger.debug(f"Received packet: {packet.packet_type}")

                    except Exception as e:
                        logger.error(f"Error deserializing packet: {e}")

            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}")
                    self.connected = False
                break

        logger.info("Receive loop stopped")

    def register_handler(self, packet_type: PacketType, handler: Callable):
        """Register a packet handler"""
        self.packet_handlers[packet_type] = handler

    def process_packets(self):
        """Process received packets (call from main thread)"""
        while not self.packet_queue.empty():
            try:
                packet = self.packet_queue.get_nowait()
                handler = self.packet_handlers.get(packet.packet_type)

                if handler:
                    handler(packet)
                else:
                    logger.warning(f"No handler for packet type: {packet.packet_type}")

            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error processing packet: {e}", exc_info=True)

    def send_ping(self):
        """Send ping to server"""
        if time.time() - self.last_ping < 30:
            return

        ping_packet = Packet(PacketType.PING, struct.pack('!d', time.time()))
        if self.send_packet(ping_packet):
            self.last_ping = time.time()
