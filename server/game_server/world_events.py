"""
Subjugate Online - World Events System
Dynamic server-wide events that affect gameplay
"""

import random
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from shared.utils import Logger

logger = Logger.get_logger(__name__)


class WorldEvent:
    """Represents a world event"""

    def __init__(
        self,
        event_id: int,
        name: str,
        description: str,
        duration: float,  # seconds
        cooldown: float = 3600.0  # 1 hour default
    ):
        self.event_id = event_id
        self.name = name
        self.description = description
        self.duration = duration
        self.cooldown = cooldown

        self.is_active = False
        self.start_time = 0.0
        self.last_activation = 0.0

        # Event effects
        self.effects: Dict[str, Any] = {}

        # Event callbacks
        self.on_start: Optional[Callable] = None
        self.on_end: Optional[Callable] = None
        self.on_update: Optional[Callable] = None

    def start(self):
        """Start the event"""
        if self.is_active:
            return

        self.is_active = True
        self.start_time = time.time()
        self.last_activation = time.time()

        if self.on_start:
            self.on_start()

        logger.info(f"World Event Started: {self.name}")

    def update(self, delta_time: float) -> bool:
        """
        Update the event

        Returns:
            True if event should end
        """
        if not self.is_active:
            return False

        if self.on_update:
            self.on_update(delta_time)

        # Check if duration expired
        elapsed = time.time() - self.start_time
        if elapsed >= self.duration:
            return True

        return False

    def end(self):
        """End the event"""
        if not self.is_active:
            return

        self.is_active = False

        if self.on_end:
            self.on_end()

        logger.info(f"World Event Ended: {self.name}")

    def can_activate(self) -> bool:
        """Check if event can be activated"""
        if self.is_active:
            return False

        # Check cooldown
        if self.last_activation > 0:
            time_since = time.time() - self.last_activation
            if time_since < self.cooldown:
                return False

        return True

    def get_time_remaining(self) -> float:
        """Get time remaining in seconds"""
        if not self.is_active:
            return 0.0

        elapsed = time.time() - self.start_time
        return max(0, self.duration - elapsed)


class WorldEventsSystem:
    """Manages world events"""

    def __init__(self, world_manager, npc_ai_system):
        self.world = world_manager
        self.npc_ai = npc_ai_system

        self.events: Dict[int, WorldEvent] = {}
        self.active_events: List[WorldEvent] = []

        # Event scheduling
        self.next_random_event_time = time.time() + random.uniform(1800, 3600)  # 30-60 min

        # Initialize events
        self._initialize_events()

        logger.info(f"World Events System initialized with {len(self.events)} events")

    def _initialize_events(self):
        """Initialize world events"""
        # === DOUBLE XP EVENT ===
        event = WorldEvent(
            event_id=1,
            name="Double Experience",
            description="All players gain 2x experience!",
            duration=1800.0,  # 30 minutes
            cooldown=7200.0  # 2 hour cooldown
        )
        event.effects['xp_multiplier'] = 2.0
        event.on_start = lambda: logger.info("Double XP event started!")
        self.events[1] = event

        # === MONSTER INVASION ===
        event = WorldEvent(
            event_id=2,
            name="Monster Invasion",
            description="Powerful monsters invade the world!",
            duration=900.0,  # 15 minutes
            cooldown=5400.0  # 90 min cooldown
        )
        event.effects['monster_spawn_rate'] = 3.0
        event.effects['monster_difficulty'] = 1.5
        event.on_start = lambda: self._spawn_invasion_monsters()
        event.on_end = lambda: self._cleanup_invasion_monsters()
        self.events[2] = event

        # === METEOR SHOWER ===
        event = WorldEvent(
            event_id=3,
            name="Meteor Shower",
            description="Meteors rain from the sky, bringing rare resources!",
            duration=600.0,  # 10 minutes
            cooldown=3600.0  # 1 hour cooldown
        )
        event.on_update = lambda dt: self._spawn_meteor(dt)
        self.events[3] = event

        # === BONUS LOOT ===
        event = WorldEvent(
            event_id=4,
            name="Treasure Trove",
            description="Monsters drop bonus loot!",
            duration=1200.0,  # 20 minutes
            cooldown=4800.0  # 80 min cooldown
        )
        event.effects['loot_multiplier'] = 2.0
        self.events[4] = event

        # === KING OF THE HILL ===
        event = WorldEvent(
            event_id=5,
            name="King of the Hill",
            description="Massive PvP battle for the central territory!",
            duration=1800.0,  # 30 minutes
            cooldown=10800.0  # 3 hour cooldown
        )
        event.effects['pvp_zone'] = True
        event.effects['territory_rewards_multiplier'] = 3.0
        event.on_start = lambda: self._announce_koth()
        self.events[5] = event

        # === WORLD BOSS SPAWN ===
        event = WorldEvent(
            event_id=6,
            name="World Boss Awakens",
            description="A legendary world boss has spawned!",
            duration=3600.0,  # 1 hour
            cooldown=14400.0  # 4 hour cooldown
        )
        event.on_start = lambda: self._spawn_world_boss()
        event.on_end = lambda: self._cleanup_world_boss()
        self.events[6] = event

        # === BLOOD MOON ===
        event = WorldEvent(
            event_id=7,
            name="Blood Moon",
            description="The Blood Moon rises... Danger lurks everywhere!",
            duration=1800.0,  # 30 minutes
            cooldown=7200.0  # 2 hour cooldown
        )
        event.effects['monster_damage'] = 1.5
        event.effects['monster_hp'] = 2.0
        event.effects['xp_multiplier'] = 1.5
        event.effects['loot_multiplier'] = 1.5
        self.events[7] = event

    def update(self, delta_time: float):
        """Update world events"""
        current_time = time.time()

        # Update active events
        for event in list(self.active_events):
            should_end = event.update(delta_time)

            if should_end:
                event.end()
                self.active_events.remove(event)

        # Check for random event trigger
        if current_time >= self.next_random_event_time:
            self._trigger_random_event()
            self.next_random_event_time = current_time + random.uniform(1800, 3600)

    def start_event(self, event_id: int) -> bool:
        """Start a specific event"""
        event = self.events.get(event_id)
        if not event:
            return False

        if not event.can_activate():
            return False

        event.start()
        self.active_events.append(event)

        return True

    def stop_event(self, event_id: int) -> bool:
        """Stop a specific event"""
        event = self.events.get(event_id)
        if not event or not event.is_active:
            return False

        event.end()
        if event in self.active_events:
            self.active_events.remove(event)

        return True

    def get_active_events(self) -> List[WorldEvent]:
        """Get all active events"""
        return self.active_events.copy()

    def get_event_effects(self) -> Dict[str, Any]:
        """Get combined effects from all active events"""
        combined_effects = {}

        for event in self.active_events:
            for effect_name, effect_value in event.effects.items():
                if effect_name in combined_effects:
                    # Multiply multipliers
                    if 'multiplier' in effect_name:
                        combined_effects[effect_name] *= effect_value
                    else:
                        combined_effects[effect_name] = max(combined_effects[effect_name], effect_value)
                else:
                    combined_effects[effect_name] = effect_value

        return combined_effects

    def _trigger_random_event(self):
        """Trigger a random event"""
        # Get events that can be activated
        available_events = [e for e in self.events.values() if e.can_activate()]

        if not available_events:
            return

        # Random selection
        event = random.choice(available_events)
        self.start_event(event.event_id)

    # ========================================================================
    # EVENT-SPECIFIC HANDLERS
    # ========================================================================

    def _spawn_invasion_monsters(self):
        """Spawn monsters for invasion event"""
        # Spawn 50 monsters across the map
        for i in range(50):
            x = random.uniform(100, 900)
            z = random.uniform(100, 900)

            # Spawn high-level monsters
            npc_id = random.choice([5003, 6001])  # Orc or Dragon
            self.npc_ai.spawn_npc(npc_id, (x, 0.0, z))

        logger.info("Invasion monsters spawned!")

    def _cleanup_invasion_monsters(self):
        """Clean up invasion monsters"""
        # In production, would remove invasion-specific monsters
        logger.info("Invasion monsters despawning...")

    def _spawn_meteor(self, delta_time: float):
        """Spawn meteors during meteor shower"""
        # Spawn a meteor every 5 seconds
        if random.random() < delta_time / 5.0:
            x = random.uniform(100, 900)
            z = random.uniform(100, 900)

            # Create meteor impact (would spawn loot)
            logger.debug(f"Meteor impact at ({x}, {z})")

    def _announce_koth(self):
        """Announce King of the Hill event"""
        logger.info("KING OF THE HILL EVENT! Battle for the central territory!")

    def _spawn_world_boss(self):
        """Spawn a world boss"""
        # Spawn at center of map
        boss_id = 6002  # Phoenix Guardian
        self.npc_ai.spawn_npc(boss_id, (500.0, 0.0, 500.0))

        logger.info("WORLD BOSS SPAWNED: Phoenix Guardian at center of the map!")

    def _cleanup_world_boss(self):
        """Clean up world boss if still alive"""
        logger.info("World boss event ended")


class DayNightCycle:
    """Manages day/night cycle and weather"""

    def __init__(self, cycle_duration: float = 3600.0):  # 1 hour real-time = 1 day
        self.cycle_duration = cycle_duration
        self.start_time = time.time()

        self.current_weather = 'clear'
        self.weather_change_interval = 600.0  # 10 minutes
        self.last_weather_change = time.time()

    def update(self, delta_time: float):
        """Update day/night cycle and weather"""
        # Check for weather change
        if time.time() - self.last_weather_change >= self.weather_change_interval:
            self._change_weather()
            self.last_weather_change = time.time()

    def get_time_of_day(self) -> float:
        """Get time of day (0.0 - 1.0)"""
        elapsed = time.time() - self.start_time
        return (elapsed % self.cycle_duration) / self.cycle_duration

    def is_night(self) -> bool:
        """Check if it's night time"""
        time_of_day = self.get_time_of_day()
        return time_of_day < 0.25 or time_of_day > 0.75  # Night from 6pm-6am

    def get_light_level(self) -> float:
        """Get ambient light level (0.0 - 1.0)"""
        time_of_day = self.get_time_of_day()

        # Noon = 1.0, Midnight = 0.3
        if time_of_day < 0.5:
            return 0.3 + (time_of_day * 2) * 0.7
        else:
            return 1.0 - ((time_of_day - 0.5) * 2) * 0.7

    def _change_weather(self):
        """Change weather randomly"""
        weathers = ['clear', 'cloudy', 'rain', 'storm', 'fog']
        self.current_weather = random.choice(weathers)

        logger.info(f"Weather changed to: {self.current_weather}")

    def get_weather(self) -> str:
        """Get current weather"""
        return self.current_weather
