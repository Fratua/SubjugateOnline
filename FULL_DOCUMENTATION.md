# Subjugate Online - Complete Documentation

**A Hyper-Advanced, Production-Ready 3D MMORPG Built from Scratch in Python**

---

## Table of Contents
1. [Overview](#overview)
2. [Core Features](#core-features)
3. [Architecture](#architecture)
4. [Game Systems](#game-systems)
5. [Installation & Setup](#installation--setup)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [Admin Guide](#admin-guide)
9. [Development Guide](#development-guide)

---

## Overview

Subjugate Online is a complete, production-ready 3D MMORPG inspired by early Conquer Online 1.0, featuring hardcore ironman gameplay, territory control warfare, and a sophisticated reincarnation system.

### Key Highlights
- **Hardcore Ironman**: Every player plays solo with no trading
- **Ultimate Ironman**: Optional extreme difficulty mode with no banking
- **Reincarnation System**: Die and be reborn stronger with permanent perks
- **Territory Warfare**: PvP control points granting powerful buffs
- **Full 3D Graphics**: Real-time rendering with Panda3D
- **Production Architecture**: Separate login/game servers, robust networking
- **Comprehensive Systems**: Guilds, quests, crafting, achievements, world events

---

## Core Features

### 🎮 Game Modes
- **Hardcore Ironman** (Default)
  - Solo progression only
  - No trading with other players
  - Can use banking/storage
  - Permanent death (character deletion)

- **Ultimate Ironman** (Optional)
  - All Hardcore restrictions
  - Cannot use banks or storage
  - Limited to inventory space only
  - Maximum challenge mode

### 🔄 Reincarnation System
Players who die can reincarnate and gain permanent perks based on their achievements:

**Success Metrics:**
- Level reached (30% weight)
- Total kills (20% weight)
- Territory control time (25% weight)
- Boss kills (15% weight)
- Playtime (10% weight)

**Reincarnation Perks (Stacking):**
- +50 HP per reincarnation
- +25 MP per reincarnation
- +5 Attack per reincarnation
- +5 Defense per reincarnation
- +0.5 Speed per reincarnation
- +10% XP multiplier per reincarnation

**Max Reincarnations:** 10

### ⚔️ Territory Control System
5 territories inspired by Conquer Online:
1. **Phoenix Castle** - +500 HP, +50 ATK, +50 DEF, +50% XP
2. **Twin City** - +300 HP, +30 ATK, +30% XP
3. **Desert City** - +200 HP, +25 ATK, +20% XP
4. **Ape City** - +200 HP, +25 DEF, +20% XP
5. **Bird Island** - +150 HP, +20 ATK, +15% XP

**Capture Mechanics:**
- Stand in territory zone (60 seconds to capture)
- Hold territories for powerful buffs
- PvP battles for control
- Guild-based conquest

### 🏰 Guild/Clan System
- Create guilds with up to 50+ members (scales with guild level)
- Guild ranks: Leader, Officer, Member
- Guild progression system (XP and levels)
- Territory warfare (guilds control territories)
- Guild bonuses:
  - HP/Attack/Defense bonuses
  - XP multipliers
  - Max member slots increase
- Guild treasury and resources

### 🎯 Quest System
**Quest Types:**
- **Story Quests**: Main storyline progression
- **Daily Quests**: Repeatable quests that reset daily
- **Weekly Quests**: Larger challenges
- **Achievement Quests**: One-time accomplishments

**Dynamic Quest Objectives:**
- Kill specific monsters/bosses
- Collect items
- Reach certain levels
- Capture territories
- PvP victories
- Crafting objectives

**Quest Rewards:**
- Experience points
- Gold currency
- Items and equipment
- Legacy Points (for reincarnation perks)

### 🔨 Crafting & Gathering System
**Professions:**
- **Blacksmithing**: Weapons and armor
- **Alchemy**: Potions and consumables
- **Tailoring**: Cloth armor
- **Cooking**: Food buffs

**Gathering Skills:**
- **Mining**: Ore and gems
- **Herbalism**: Plants and herbs
- **Woodcutting**: Lumber
- **Fishing**: Fish and aquatic resources

**Features:**
- Skill leveling (1-99)
- Gathering nodes spawn throughout the world
- Resource respawn timers
- Crafting recipes unlock with skill level
- All ironman-compatible (self-sufficient)

### 🏆 Achievement & Leaderboard System
**Achievement Categories:**
- Combat (kills, boss defeats, PvP)
- Reincarnation milestones
- Territory control
- Progression (levels)
- Crafting & gathering
- Special/Hidden achievements

**Leaderboards:**
- Level ranking
- Total kills
- PvP kills
- Boss kills
- Reincarnation count
- Territory control time
- Achievement points
- Guild rankings

### 💬 Advanced Chat System
**Chat Channels:**
- **Global**: Server-wide communication
- **Local**: Nearby players only
- **Guild**: Guild members only
- **Trade**: Trading discussions (display only for ironman)
- **Whisper**: Private messages
- **System**: Server announcements
- **Help**: Player assistance

**Features:**
- Multi-channel support
- Private messaging (whispers)
- Guild chat
- Spam protection & cooldowns
- Profanity filtering
- Player muting (global & channel-specific)
- Message history

### 🌍 World Events System
Dynamic server-wide events that enhance gameplay:

1. **Double Experience** (30 min): 2x XP for all players
2. **Monster Invasion** (15 min): Increased spawns, harder monsters
3. **Meteor Shower** (10 min): Meteors drop rare resources
4. **Treasure Trove** (20 min): 2x loot from monsters
5. **King of the Hill** (30 min): Massive PvP territory battle
6. **World Boss Awakens** (60 min): Legendary boss spawns
7. **Blood Moon** (30 min): 1.5x monster damage/HP, 1.5x rewards

**Features:**
- Random event scheduling
- Event cooldowns
- Stacking event effects
- Admin-triggerable events

### 🌓 Day/Night Cycle & Weather
- Dynamic time of day (configurable cycle length)
- Light level changes based on time
- Weather system:
  - Clear
  - Cloudy
  - Rain
  - Storm
  - Fog
- Weather affects visibility and gameplay

### 🛠️ Admin Tools & Monitoring
**Admin Commands:**
- Ban/unban accounts
- Kick/mute players
- Teleport players
- Set player stats/levels
- Give items
- Spawn NPCs/bosses
- Trigger world events
- Reset territory control
- Maintenance mode

**Monitoring:**
- Real-time server metrics
- Player statistics
- Performance monitoring (CPU, RAM, tick times)
- Error tracking
- Network statistics
- Database statistics

---

## Architecture

### Server Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Login Server   │────▶│   Database       │
│  Port: 5000     │     │   SQLite/PostgreSQL
└────────┬────────┘     └──────────────────┘
         │                        ▲
         │ Session Token          │
         │                        │
    ┌────▼────────┐              │
    │   Client    │              │
    └────┬────────┘              │
         │                        │
         │ Connect with Token    │
         │                        │
┌────────▼────────┐              │
│  Game Server    │──────────────┘
│  Port: 5001     │
│                 │
│  ┌───────────┐  │
│  │World Mgr  │  │
│  ├───────────┤  │
│  │Combat Sys │  │
│  ├───────────┤  │
│  │Territory  │  │
│  ├───────────┤  │
│  │Reincarn.  │  │
│  ├───────────┤  │
│  │Guild Sys  │  │
│  ├───────────┤  │
│  │Quest Sys  │  │
│  ├───────────┤  │
│  │Craft Sys  │  │
│  ├───────────┤  │
│  │Events Sys │  │
│  └───────────┘  │
└─────────────────┘
```

### Technology Stack

**Server:**
- Python 3.10+
- asyncio (async I/O)
- SQLAlchemy (ORM)
- MessagePack (binary protocol)
- cryptography (security)

**Client:**
- Panda3D (3D engine)
- DirectGUI (UI)
- asyncio (networking)

**Database:**
- SQLite (development)
- PostgreSQL (production)

---

## Game Systems

### Combat System
- **Damage Types**: Physical, Magical, True
- **Combat Styles**: Melee, Ranged, Magic
- **Skills**: 12+ unique abilities
- **Cooldowns**: Skill-based cooldown system
- **Range**: Distance-based combat
- **PvP**: Full player-vs-player combat
- **Death**: Permanent for hardcore mode

### Character Progression
- **Level Range**: 1-150
- **Experience System**: Non-linear XP curve
- **Stats**: HP, MP, Attack, Defense, Speed
- **Equipment Slots**: 9 slots (weapon, armor, accessories)
- **Inventory**: 40 slots (200 bank slots for non-ultimate)
- **Skills**: Learn and level up skills

### NPC & Monster AI
- **States**: Idle, Patrolling, Chasing, Attacking
- **Aggro System**: Range-based aggression
- **Pathing**: Basic movement AI
- **Respawn**: Timed respawn system
- **Loot Tables**: Randomized drops
- **Boss Mechanics**: Enhanced AI for bosses

### World Manager
- **Spatial Partitioning**: Efficient entity management
- **Chunk System**: 50x50 unit chunks
- **View Distance**: 100 units
- **Player Synchronization**: Position and state updates
- **NPC Management**: Dynamic spawning and despawning

---

## Installation & Setup

### Prerequisites
```bash
# Python 3.10 or higher
python --version

# Virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from server.database.db_manager import DatabaseManager; DatabaseManager().create_tables()"
```

### Quick Start
```bash
# Terminal 1: Start Login Server
python run_login_server.py

# Terminal 2: Start Game Server
python run_game_server.py

# Terminal 3: Start Client
python run_client.py
```

---

## Configuration

### Server Configuration

**Login Server** (`shared/constants.py`):
```python
LOGIN_SERVER_HOST = "127.0.0.1"
LOGIN_SERVER_PORT = 5000
SESSION_EXPIRY = 3600  # 1 hour
```

**Game Server**:
```python
GAME_SERVER_HOST = "127.0.0.1"
GAME_SERVER_PORT = 5001
TICK_RATE = 20  # Updates per second
NETWORK_UPDATE_RATE = 10  # Network syncs per second
```

**Database**:
```python
DB_PATH = "data/subjugate_online.db"
```

### Game Balance

**Reincarnation**:
```python
REINCARNATION_LEVEL_REQUIREMENT = 100
MAX_REINCARNATIONS = 10
PERK_HP_BONUS = 50
PERK_ATTACK_BONUS = 5
```

**Territory Control**:
```python
TERRITORY_CAPTURE_TIME = 60  # seconds
MIN_PLAYERS_TO_CAPTURE = 1
```

---

## API Reference

### Network Protocol

**Packet Structure:**
```python
{
    'packet_type': int,
    'data': dict
}
```

**Packet Types:**
- 0-99: Authentication
- 100-199: Server connection
- 200-299: Player movement
- 300-399: Combat
- 400-499: Stats & Inventory
- 500-599: Reincarnation
- 600-699: Territory Control
- 700-799: Chat & Social
- 800-899: World & NPCs
- 900-999: System

### Database Models

**Account:**
```python
- id: Integer (PK)
- username: String (unique)
- password_hash: String
- email: String
- created_at: DateTime
- is_banned: Boolean
```

**Character:**
```python
- id: Integer (PK)
- account_id: ForeignKey
- name: String (unique)
- level: Integer
- hp, max_hp: Integer
- attack, defense: Integer
- position_x, position_y, position_z: Float
- reincarnation_count: Integer
- reincarnation_perks: JSON
- game_mode: Integer
```

---

## Admin Guide

### Starting the Admin Console
```python
from server.admin.admin_tools import AdminTools
from server.database.db_manager import DatabaseManager

admin = AdminTools(DatabaseManager())
```

### Common Admin Tasks

**Ban a Player:**
```python
admin.ban_account("username", "Reason for ban", "AdminName")
```

**Give Item:**
```python
admin.give_item(character_id=123, item_id=1001, amount=1)
```

**Trigger World Event:**
```python
from server.game_server.world_events import WorldEventsSystem
events.start_event(event_id=1)  # Start Double XP
```

**Server Status:**
```python
status = admin.get_server_status()
print(status)
```

---

## Development Guide

### Project Structure
```
subjugate-online/
├── server/
│   ├── login_server/        # Authentication server
│   ├── game_server/         # Main game logic
│   │   ├── combat_system.py
│   │   ├── reincarnation_system.py
│   │   ├── territory_system.py
│   │   ├── guild_system.py
│   │   ├── quest_system.py
│   │   ├── crafting_system.py
│   │   ├── achievement_system.py
│   │   ├── chat_system.py
│   │   ├── world_events.py
│   │   ├── npc_ai.py
│   │   └── world_manager.py
│   ├── database/            # Database models & manager
│   ├── network/             # Network protocol
│   └── admin/               # Admin tools
├── client/                  # 3D game client
│   ├── game_client.py       # Main client
│   ├── network_client.py    # Client networking
│   └── login_client.py      # Login UI
├── shared/                  # Shared code
│   ├── constants.py         # Game constants
│   ├── game_data.py         # Items, skills, NPCs
│   └── utils.py             # Utilities
└── run_*.py                 # Startup scripts
```

### Adding New Features

**1. Add a New Skill:**
```python
# In shared/game_data.py
SKILL_DATABASE[SkillType.NEW_SKILL] = {
    'name': 'New Skill',
    'damage_multiplier': 2.0,
    'mp_cost': 20,
    'cooldown': 5.0,
    'range': ATTACK_RANGE_MAGIC
}
```

**2. Add a New Quest:**
```python
# In server/game_server/quest_system.py
quest = Quest(
    quest_id=500,
    name="New Quest",
    description="Quest description",
    quest_type="story"
)
quest.add_objective(QuestObjective('kill', 'monster', 10))
quest.rewards['xp'] = 1000
```

**3. Add a New World Event:**
```python
# In server/game_server/world_events.py
event = WorldEvent(
    event_id=10,
    name="Custom Event",
    description="Description",
    duration=600.0
)
event.on_start = custom_handler
```

### Testing
```bash
# Run tests
pytest tests/

# Test with multiple clients
python run_client.py &
python run_client.py &
python run_client.py &
```

---

## Performance & Scalability

### Optimizations
- **Spatial Partitioning**: O(n) → O(k) entity queries
- **Async I/O**: Non-blocking network operations
- **Database Pooling**: Connection reuse
- **Message Packing**: Binary protocol (MessagePack)
- **View Distance Culling**: Only sync nearby entities

### Capacity
- **Recommended**: 100-500 concurrent players per server
- **Tick Rate**: 20 TPS (50ms per tick)
- **Network Rate**: 10 updates/sec per player

### Monitoring
```python
# Get server metrics
metrics = admin.metrics.get_summary()
print(f"Avg Tick Time: {metrics['performance']['avg_tick_time_ms']}ms")
print(f"Peak Players: {metrics['players']['peak_concurrent']}")
```

---

## Credits & License

**Developed by:** Subjugate Online Development Team
**Inspired by:** Conquer Online 1.0
**Engine:** Panda3D
**Language:** Python 3.10+

**License:** MIT License

---

## Support & Community

- **Documentation**: This file
- **Issues**: GitHub Issues
- **Wiki**: GitHub Wiki

---

**Welcome to Subjugate Online - Where Death is Just the Beginning!**
