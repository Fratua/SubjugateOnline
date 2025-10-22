"""
Subjugate Online - Advanced Chat System
Multi-channel chat with private messages, guild chat, and moderation
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from shared.utils import Logger

logger = Logger.get_logger(__name__)


class ChatMessage:
    """Represents a chat message"""

    def __init__(
        self,
        sender_id: int,
        sender_name: str,
        message: str,
        channel: str
    ):
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.message = message
        self.channel = channel
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'sender_id': self.sender_id,
            'sender_name': self.sender_name,
            'message': self.message,
            'channel': self.channel,
            'timestamp': self.timestamp.isoformat()
        }


class ChatChannel:
    """Represents a chat channel"""

    def __init__(self, name: str, channel_type: str, color: str = "#FFFFFF"):
        self.name = name
        self.channel_type = channel_type  # 'global', 'local', 'guild', 'party', 'trade', 'system'
        self.color = color  # Color for UI display

        # Message history (last 100 messages)
        self.messages: List[ChatMessage] = []
        self.max_history = 100

        # Channel members (for private channels)
        self.members: Set[int] = set()

        # Moderation
        self.muted_players: Set[int] = set()
        self.banned_words: Set[str] = set()

    def add_message(self, message: ChatMessage):
        """Add a message to the channel"""
        self.messages.append(message)

        # Keep only last N messages
        if len(self.messages) > self.max_history:
            self.messages.pop(0)

    def get_recent_messages(self, count: int = 50) -> List[ChatMessage]:
        """Get recent messages"""
        return self.messages[-count:]

    def is_member(self, character_id: int) -> bool:
        """Check if character is a member"""
        return character_id in self.members

    def is_muted(self, character_id: int) -> bool:
        """Check if character is muted"""
        return character_id in self.muted_players


class ChatSystem:
    """Manages all chat functionality"""

    def __init__(self):
        self.channels: Dict[str, ChatChannel] = {}
        self.private_conversations: Dict[str, ChatChannel] = {}  # "id1_id2" -> channel

        # Player state
        self.player_active_channels: Dict[int, Set[str]] = {}  # character_id -> channel names
        self.player_mute_status: Dict[int, datetime] = {}  # character_id -> mute_end_time

        # Spam protection
        self.message_cooldowns: Dict[int, datetime] = {}  # character_id -> last_message_time
        self.message_cooldown = 1.0  # Seconds between messages

        # Initialize default channels
        self._initialize_channels()

        logger.info("Chat system initialized")

    def _initialize_channels(self):
        """Initialize default chat channels"""
        # Global channel (everyone can see)
        self.channels['global'] = ChatChannel('Global', 'global', '#00FF00')

        # Local channel (nearby players only)
        self.channels['local'] = ChatChannel('Local', 'local', '#FFFFFF')

        # Trade channel
        self.channels['trade'] = ChatChannel('Trade', 'trade', '#FFD700')

        # System announcements
        self.channels['system'] = ChatChannel('System', 'system', '#FF0000')

        # Help channel
        self.channels['help'] = ChatChannel('Help', 'help', '#00FFFF')

        logger.info(f"Initialized {len(self.channels)} default channels")

    def send_message(
        self,
        sender_id: int,
        sender_name: str,
        channel_name: str,
        message: str
    ) -> bool:
        """
        Send a message to a channel

        Returns:
            True if message was sent, False if failed
        """
        # Check if player is muted
        if self._is_player_muted(sender_id):
            return False

        # Check cooldown
        if not self._check_cooldown(sender_id):
            return False

        # Get channel
        channel = self.channels.get(channel_name)
        if not channel:
            return False

        # Check if player is muted in this channel
        if channel.is_muted(sender_id):
            return False

        # Filter message
        filtered_message = self._filter_message(message, channel)

        # Create message
        chat_message = ChatMessage(sender_id, sender_name, filtered_message, channel_name)

        # Add to channel
        channel.add_message(chat_message)

        # Update cooldown
        self.message_cooldowns[sender_id] = datetime.utcnow()

        logger.debug(f"[{channel_name}] {sender_name}: {filtered_message}")

        return True

    def whisper(
        self,
        sender_id: int,
        sender_name: str,
        recipient_id: int,
        recipient_name: str,
        message: str
    ) -> bool:
        """
        Send a private message

        Returns:
            True if message was sent
        """
        # Check if player is muted
        if self._is_player_muted(sender_id):
            return False

        # Get or create private channel
        channel_key = self._get_private_channel_key(sender_id, recipient_id)

        if channel_key not in self.private_conversations:
            channel = ChatChannel(f"Private: {sender_name} <-> {recipient_name}", 'whisper', '#FF00FF')
            channel.members.add(sender_id)
            channel.members.add(recipient_id)
            self.private_conversations[channel_key] = channel

        channel = self.private_conversations[channel_key]

        # Create message
        chat_message = ChatMessage(sender_id, sender_name, message, 'whisper')
        channel.add_message(chat_message)

        logger.debug(f"[Whisper] {sender_name} -> {recipient_name}: {message}")

        return True

    def send_guild_message(
        self,
        sender_id: int,
        sender_name: str,
        guild_id: int,
        message: str
    ) -> bool:
        """Send a message to guild chat"""
        # Get or create guild channel
        channel_name = f"guild_{guild_id}"

        if channel_name not in self.channels:
            self.channels[channel_name] = ChatChannel(f"Guild {guild_id}", 'guild', '#FFA500')

        channel = self.channels[channel_name]

        # Create message
        chat_message = ChatMessage(sender_id, sender_name, message, channel_name)
        channel.add_message(chat_message)

        logger.debug(f"[Guild {guild_id}] {sender_name}: {message}")

        return True

    def system_message(self, message: str, channel_name: str = 'system'):
        """Send a system message"""
        channel = self.channels.get(channel_name)
        if not channel:
            return

        chat_message = ChatMessage(0, 'System', message, channel_name)
        channel.add_message(chat_message)

    def get_channel_messages(
        self,
        channel_name: str,
        count: int = 50
    ) -> List[ChatMessage]:
        """Get recent messages from a channel"""
        channel = self.channels.get(channel_name)
        if not channel:
            return []

        return channel.get_recent_messages(count)

    def get_private_messages(
        self,
        character_id1: int,
        character_id2: int,
        count: int = 50
    ) -> List[ChatMessage]:
        """Get private messages between two players"""
        channel_key = self._get_private_channel_key(character_id1, character_id2)

        channel = self.private_conversations.get(channel_key)
        if not channel:
            return []

        return channel.get_recent_messages(count)

    def _check_cooldown(self, character_id: int) -> bool:
        """Check if player is off cooldown"""
        if character_id not in self.message_cooldowns:
            return True

        last_message = self.message_cooldowns[character_id]
        time_since = (datetime.utcnow() - last_message).total_seconds()

        return time_since >= self.message_cooldown

    def _is_player_muted(self, character_id: int) -> bool:
        """Check if player is globally muted"""
        if character_id not in self.player_mute_status:
            return False

        mute_end = self.player_mute_status[character_id]

        # Check if mute expired
        if datetime.utcnow() >= mute_end:
            del self.player_mute_status[character_id]
            return False

        return True

    def _filter_message(self, message: str, channel: ChatChannel) -> str:
        """Filter message for profanity and spam"""
        filtered = message

        # Filter banned words
        for banned_word in channel.banned_words:
            if banned_word.lower() in filtered.lower():
                filtered = filtered.replace(banned_word, '*' * len(banned_word))

        # Limit length
        max_length = 500
        if len(filtered) > max_length:
            filtered = filtered[:max_length]

        return filtered

    def _get_private_channel_key(self, id1: int, id2: int) -> str:
        """Get unique key for private channel"""
        # Always use lower ID first for consistency
        lower, higher = (id1, id2) if id1 < id2 else (id2, id1)
        return f"{lower}_{higher}"

    # ========================================================================
    # MODERATION
    # ========================================================================

    def mute_player(self, character_id: int, duration_seconds: int):
        """Mute a player globally"""
        mute_end = datetime.utcnow() + timedelta(seconds=duration_seconds)
        self.player_mute_status[character_id] = mute_end

        logger.info(f"Player {character_id} muted for {duration_seconds} seconds")

    def unmute_player(self, character_id: int):
        """Unmute a player"""
        if character_id in self.player_mute_status:
            del self.player_mute_status[character_id]

        logger.info(f"Player {character_id} unmuted")

    def mute_in_channel(self, character_id: int, channel_name: str):
        """Mute a player in a specific channel"""
        channel = self.channels.get(channel_name)
        if channel:
            channel.muted_players.add(character_id)

    def unmute_in_channel(self, character_id: int, channel_name: str):
        """Unmute a player in a specific channel"""
        channel = self.channels.get(channel_name)
        if channel:
            channel.muted_players.discard(character_id)

    def add_banned_word(self, channel_name: str, word: str):
        """Add a banned word to a channel"""
        channel = self.channels.get(channel_name)
        if channel:
            channel.banned_words.add(word.lower())

    def remove_banned_word(self, channel_name: str, word: str):
        """Remove a banned word from a channel"""
        channel = self.channels.get(channel_name)
        if channel:
            channel.banned_words.discard(word.lower())
