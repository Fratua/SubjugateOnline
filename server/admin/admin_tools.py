"""
Subjugate Online - Admin Tools and Monitoring
Provides administrative tools for server management and monitoring
"""

import time
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from shared.utils import Logger
from server.database.db_manager import DatabaseManager

logger = Logger.get_logger(__name__)


class ServerMetrics:
    """Tracks server performance metrics"""

    def __init__(self):
        self.start_time = time.time()

        # Performance metrics
        self.total_packets_sent = 0
        self.total_packets_received = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0

        # Player metrics
        self.peak_concurrent_players = 0
        self.total_logins = 0
        self.total_disconnects = 0

        # Game metrics
        self.total_kills = 0
        self.total_deaths = 0
        self.total_reincarnations = 0
        self.total_quests_completed = 0

        # Error tracking
        self.total_errors = 0
        self.recent_errors: List[Dict] = []

        # Tick performance
        self.tick_times: List[float] = []
        self.max_tick_time = 0.0
        self.avg_tick_time = 0.0

    def record_tick_time(self, tick_time: float):
        """Record a tick time"""
        self.tick_times.append(tick_time)

        # Keep only last 100 ticks
        if len(self.tick_times) > 100:
            self.tick_times.pop(0)

        self.max_tick_time = max(self.max_tick_time, tick_time)
        self.avg_tick_time = sum(self.tick_times) / len(self.tick_times)

    def record_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Record an error"""
        self.total_errors += 1

        error_record = {
            'timestamp': datetime.utcnow(),
            'type': error_type,
            'message': message,
            'details': details or {}
        }

        self.recent_errors.append(error_record)

        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors.pop(0)

    def get_uptime(self) -> float:
        """Get server uptime in seconds"""
        return time.time() - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        uptime = self.get_uptime()

        return {
            'uptime_seconds': uptime,
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'network': {
                'packets_sent': self.total_packets_sent,
                'packets_received': self.total_packets_received,
                'bytes_sent': self.total_bytes_sent,
                'bytes_received': self.total_bytes_received
            },
            'players': {
                'peak_concurrent': self.peak_concurrent_players,
                'total_logins': self.total_logins,
                'total_disconnects': self.total_disconnects
            },
            'game': {
                'total_kills': self.total_kills,
                'total_deaths': self.total_deaths,
                'total_reincarnations': self.total_reincarnations,
                'quests_completed': self.total_quests_completed
            },
            'performance': {
                'avg_tick_time_ms': self.avg_tick_time * 1000,
                'max_tick_time_ms': self.max_tick_time * 1000,
                'total_errors': self.total_errors
            },
            'system': get_system_info()
        }


def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu_percent': cpu_percent,
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': memory.total / (1024 ** 3),
            'memory_used_gb': memory.used / (1024 ** 3),
            'memory_percent': memory.percent,
            'disk_total_gb': disk.total / (1024 ** 3),
            'disk_used_gb': disk.used / (1024 ** 3),
            'disk_percent': disk.percent
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {}


class AdminTools:
    """Administrative tools for server management"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.metrics = ServerMetrics()
        self.banned_ips: List[str] = []
        self.maintenance_mode = False

        logger.info("Admin tools initialized")

    # ========================================================================
    # PLAYER MANAGEMENT
    # ========================================================================

    def ban_account(self, username: str, reason: str, admin_name: str) -> bool:
        """Ban a player account"""
        success = self.db.ban_account(username, reason)

        if success:
            logger.warning(f"Account '{username}' banned by {admin_name}. Reason: {reason}")
            self.db.log_event('account_banned', None, {
                'username': username,
                'reason': reason,
                'admin': admin_name
            })

        return success

    def unban_account(self, username: str, admin_name: str) -> bool:
        """Unban a player account"""
        success = self.db.unban_account(username)

        if success:
            logger.info(f"Account '{username}' unbanned by {admin_name}")
            self.db.log_event('account_unbanned', None, {
                'username': username,
                'admin': admin_name
            })

        return success

    def kick_player(self, character_id: int, reason: str) -> bool:
        """Kick a player from the game"""
        # This would disconnect the player
        logger.info(f"Player {character_id} kicked. Reason: {reason}")
        return True

    def teleport_player(
        self,
        character_id: int,
        x: float,
        y: float,
        z: float
    ) -> bool:
        """Teleport a player to a location"""
        return self.db.update_character_position(character_id, x, y, z, 0.0)

    def set_player_level(self, character_id: int, level: int) -> bool:
        """Set a player's level"""
        return self.db.update_character_stats(character_id, {'level': level})

    def give_item(self, character_id: int, item_id: int, amount: int) -> bool:
        """Give an item to a player"""
        # This would add to inventory
        logger.info(f"Gave item {item_id} x{amount} to player {character_id}")
        return True

    # ========================================================================
    # SERVER MANAGEMENT
    # ========================================================================

    def enable_maintenance_mode(self, reason: str):
        """Enable maintenance mode"""
        self.maintenance_mode = True
        logger.warning(f"Maintenance mode enabled: {reason}")

    def disable_maintenance_mode(self):
        """Disable maintenance mode"""
        self.maintenance_mode = False
        logger.info("Maintenance mode disabled")

    def broadcast_message(self, message: str, message_type: str = 'info'):
        """Broadcast a message to all players"""
        # This would send to all connected clients
        logger.info(f"Broadcast [{message_type}]: {message}")

    def ban_ip(self, ip_address: str):
        """Ban an IP address"""
        if ip_address not in self.banned_ips:
            self.banned_ips.append(ip_address)
            logger.warning(f"IP banned: {ip_address}")

    def unban_ip(self, ip_address: str):
        """Unban an IP address"""
        if ip_address in self.banned_ips:
            self.banned_ips.remove(ip_address)
            logger.info(f"IP unbanned: {ip_address}")

    def is_ip_banned(self, ip_address: str) -> bool:
        """Check if an IP is banned"""
        return ip_address in self.banned_ips

    # ========================================================================
    # MONITORING
    # ========================================================================

    def get_online_players(self) -> List[Dict]:
        """Get list of online players"""
        # This would query from world manager
        return []

    def get_server_status(self) -> Dict[str, Any]:
        """Get comprehensive server status"""
        status = self.metrics.get_summary()
        status['maintenance_mode'] = self.maintenance_mode
        status['banned_ips_count'] = len(self.banned_ips)

        return status

    def get_player_info(self, character_id: int) -> Optional[Dict]:
        """Get detailed player information"""
        character = self.db.get_character_by_id(character_id)
        if not character:
            return None

        return {
            'id': character.id,
            'name': character.name,
            'level': character.level,
            'is_online': character.is_online,
            'is_dead': character.is_dead,
            'reincarnation_count': character.reincarnation_count,
            'total_kills': character.total_kills,
            'player_kills': character.player_kills,
            'deaths': character.deaths,
            'playtime_hours': character.playtime / 3600.0,
            'created_at': character.created_at,
            'last_played': character.last_played
        }

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent game events"""
        # This would query from game logs
        return []

    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        return {
            'total_accounts': self.db.get_account_count(),
            'total_characters': self.db.get_character_count(),
            'online_players': self.db.get_online_count(),
            'total_sessions': self.db.get_active_session_count()
        }

    # ========================================================================
    # WORLD MANAGEMENT
    # ========================================================================

    def spawn_npc(
        self,
        npc_id: int,
        x: float,
        y: float,
        z: float
    ) -> bool:
        """Spawn an NPC at a location"""
        logger.info(f"Admin spawned NPC {npc_id} at ({x}, {y}, {z})")
        return True

    def despawn_npc(self, instance_id: int) -> bool:
        """Despawn an NPC"""
        logger.info(f"Admin despawned NPC instance {instance_id}")
        return True

    def trigger_world_event(self, event_type: str) -> bool:
        """Trigger a world event"""
        logger.info(f"Admin triggered world event: {event_type}")
        return True

    def reset_territory_control(self):
        """Reset all territory control"""
        logger.warning("Admin reset all territory control")

    # ========================================================================
    # DEBUGGING
    # ========================================================================

    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information"""
        return {
            'metrics': self.metrics.get_summary(),
            'recent_errors': self.metrics.recent_errors[-10:],
            'system': get_system_info()
        }

    def clear_metrics(self):
        """Clear metrics"""
        self.metrics = ServerMetrics()
        logger.info("Metrics cleared")
