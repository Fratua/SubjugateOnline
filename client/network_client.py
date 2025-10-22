"""
Subjugate Online - Network Client
Handles network communication with login and game servers
"""

import asyncio
import threading
from typing import Optional, Callable, Dict
from queue import Queue
from shared.constants import PacketType
from shared.utils import Logger
from server.network.protocol import Packet, PacketBuffer

logger = Logger.get_logger(__name__)


class NetworkClient:
    """Asynchronous network client"""

    def __init__(self):
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.buffer = PacketBuffer()
        self.connected = False

        # Packet queues
        self.incoming_packets = Queue()
        self.outgoing_packets = Queue()

        # Packet handlers
        self.packet_handlers: Dict[int, Callable] = {}

        # Network thread
        self.network_thread = None
        self.loop = None

    def register_handler(self, packet_type: int, handler: Callable):
        """Register a packet handler"""
        self.packet_handlers[packet_type] = handler

    async def connect_async(self, host: str, port: int) -> bool:
        """Connect to server"""
        try:
            self.reader, self.writer = await asyncio.open_connection(host, port)
            self.connected = True
            logger.info(f"Connected to {host}:{port}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
            return False

    async def disconnect_async(self):
        """Disconnect from server"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass

        self.connected = False
        logger.info("Disconnected from server")

    async def send_packet_async(self, packet: Packet):
        """Send a packet to the server"""
        if not self.connected or not self.writer:
            return

        try:
            data = packet.serialize()
            self.writer.write(data)
            await self.writer.drain()

        except Exception as e:
            logger.error(f"Failed to send packet: {e}")
            self.connected = False

    async def receive_loop(self):
        """Receive packets from server"""
        while self.connected:
            try:
                if not self.reader:
                    break

                data = await self.reader.read(4096)

                if not data:
                    logger.info("Server closed connection")
                    self.connected = False
                    break

                self.buffer.add_data(data)

                while self.buffer.has_complete_packet():
                    packet = self.buffer.get_packet()
                    if packet:
                        # Add to incoming queue
                        self.incoming_packets.put(packet)

            except Exception as e:
                logger.error(f"Error receiving packets: {e}")
                self.connected = False
                break

    async def send_loop(self):
        """Send queued packets"""
        while self.connected:
            try:
                # Check outgoing queue
                if not self.outgoing_packets.empty():
                    packet = self.outgoing_packets.get()
                    await self.send_packet_async(packet)

                await asyncio.sleep(0.01)  # Small delay

            except Exception as e:
                logger.error(f"Error in send loop: {e}")
                break

    def connect(self, host: str, port: int) -> bool:
        """Connect to server (threaded)"""
        def run_event_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            # Connect
            connected = self.loop.run_until_complete(self.connect_async(host, port))

            if connected:
                # Start send/receive loops
                self.loop.create_task(self.receive_loop())
                self.loop.create_task(self.send_loop())

                # Run loop
                self.loop.run_forever()

        self.network_thread = threading.Thread(target=run_event_loop, daemon=True)
        self.network_thread.start()

        # Wait a bit for connection
        import time
        time.sleep(0.5)

        return self.connected

    def disconnect(self):
        """Disconnect from server (threaded)"""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.disconnect_async(), self.loop)

    def send_packet(self, packet: Packet):
        """Queue a packet to send"""
        self.outgoing_packets.put(packet)

    def process_incoming_packets(self):
        """Process incoming packets (call from main thread)"""
        while not self.incoming_packets.empty():
            packet = self.incoming_packets.get()

            # Call handler if registered
            handler = self.packet_handlers.get(packet.packet_type)
            if handler:
                try:
                    handler(packet)
                except Exception as e:
                    logger.error(f"Error in packet handler: {e}")
            else:
                logger.warning(f"No handler for packet type {packet.packet_type}")

    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
