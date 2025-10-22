# Subjugate Online

**A Hyper-Advanced, Production-Ready 3D MMORPG Built from Scratch in Python**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Panda3D](https://img.shields.io/badge/Panda3D-1.10+-green.svg)](https://www.panda3d.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Subjugate Online is a complete, production-ready 3D MMORPG inspired by early Conquer Online 1.0, featuring hardcore ironman gameplay, sophisticated territory warfare, and an extensive reincarnation system.

---

## ✨ Core Features

### 🎮 Game Modes
- **Hardcore Ironman** (Default): Solo progression, permanent death, banking allowed
- **Ultimate Ironman**: Extreme mode - no banking, inventory-only survival

### 🔄 Reincarnation System
- Die and be reborn stronger with **permanent perks**
- Success metrics: Level, kills, territory control, boss kills, playtime
- Stacking bonuses: HP, MP, Attack, Defense, Speed, XP multipliers
- Up to **10 reincarnations** with exponential power growth

### ⚔️ Territory Control (Conquer Online Style)
- **5 Major Territories**: Phoenix Castle, Twin City, Desert City, Ape City, Bird Island
- PvP conquest mechanics (60-second capture)
- Powerful buffs for controlling territories
- Guild-based warfare

### 🏰 Guild System
- Create and manage guilds (50+ members)
- Guild leveling and progression
- Territory conquest with guild bonuses
- Guild treasury, ranks, and resources

### 🎯 Advanced Quest System
- **Story Quests**: Main storyline progression
- **Daily/Weekly Quests**: Repeatable challenges
- **Achievement Quests**: Special accomplishments
- Dynamic objectives: Kill, collect, craft, PvP, territory capture
- Rewards: XP, gold, items, legacy points

### 🔨 Crafting & Gathering
- **Professions**: Blacksmithing, Alchemy, Tailoring, Cooking
- **Gathering**: Mining, Herbalism, Woodcutting, Fishing
- Skill leveling (1-99)
- Resource nodes across the world
- Crafting recipes unlock with skill progression

### 🏆 Achievements & Leaderboards
- **40+ Achievements** across multiple categories
- Global leaderboards: Level, kills, PvP, reincarnations
- Achievement points and titles
- Hidden achievements for special accomplishments

### 💬 Advanced Chat System
- Multiple channels: Global, Local, Guild, Trade, Whisper, System, Help
- Private messaging
- Spam protection and moderation
- Profanity filtering

### 🌍 World Events
- **7 Dynamic Events**: Double XP, Monster Invasion, Meteor Shower, Treasure Trove, King of the Hill, World Boss, Blood Moon
- Random event scheduling with cooldowns
- Server-wide effects and rewards

### 🌓 Day/Night Cycle & Weather
- Dynamic time of day with light level changes
- Weather system: Clear, Cloudy, Rain, Storm, Fog
- Affects gameplay and visibility

### 🛠️ Admin Tools & Monitoring
- Comprehensive admin panel
- Real-time server metrics and performance monitoring
- Player management: Ban, kick, mute, teleport
- World control: Spawn NPCs, trigger events
- System monitoring: CPU, RAM, tick times, network stats

---

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd SubjugateOnline

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
python -c "from server.database.db_manager import DatabaseManager; DatabaseManager().create_tables()"
```

### Running the Game
```bash
# Terminal 1: Start Login Server (Port 5000)
python run_login_server.py

# Terminal 2: Start Game Server (Port 5001)
python run_game_server.py

# Terminal 3: Start Client
python run_client.py
```

### Creating an Account
1. Run the client
2. Click "Register" on the login screen
3. Enter username and password
4. Create your character
5. Choose your game mode: Hardcore or Ultimate Ironman

---

## 📚 Documentation

- **[FULL_DOCUMENTATION.md](FULL_DOCUMENTATION.md)** - Complete technical documentation
  - Architecture overview
  - All game systems explained
  - API reference
  - Admin guide
  - Development guide

---

## 🎮 Game Systems Overview

### Combat System
- **12+ Skills**: Melee, Ranged, Magic abilities
- **Damage Types**: Physical, Magical, True
- **PvP**: Full player-vs-player combat
- **Boss Mechanics**: Enhanced AI with special abilities

### Character Progression
- **Levels**: 1-150 with non-linear XP curve
- **Stats**: HP, MP, Attack, Defense, Speed
- **Equipment**: 9 slots (weapon, armor, accessories)
- **Inventory**: 40 slots (200 bank slots for Hardcore)

### NPC & Monster AI
- Intelligent AI: Idle, Patrolling, Chasing, Attacking
- Aggro-based engagement
- Dynamic spawning and respawn timers
- Randomized loot tables

---

## 🏗️ Architecture

### Technology Stack
- **Server**: Python 3.10+ with asyncio
- **Client**: Panda3D (3D engine)
- **Networking**: MessagePack binary protocol
- **Database**: SQLAlchemy ORM (SQLite/PostgreSQL)
- **Security**: Cryptography for password hashing

### Server Architecture
```
Login Server (Port 5000)
    ↓ Session Token
Game Server (Port 5001)
    ├── World Manager
    ├── Combat System
    ├── Territory System
    ├── Reincarnation System
    ├── Guild System
    ├── Quest System
    ├── Crafting System
    ├── Achievement System
    ├── Chat System
    ├── World Events System
    └── NPC AI System
```

### Performance
- **Tick Rate**: 20 TPS (50ms per tick)
- **Network Rate**: 10 updates/sec
- **Capacity**: 100-500 concurrent players (recommended)
- **Optimizations**: Spatial partitioning, async I/O, view distance culling

---

## 🎯 Game Balance

| System | Value |
|--------|-------|
| Max Level | 150 |
| Max Reincarnations | 10 |
| Reincarnation Level Req | 100 |
| Territories | 5 |
| Territory Capture Time | 60 seconds |
| Inventory Slots | 40 |
| Bank Slots (Hardcore) | 200 |
| Bank Slots (Ultimate) | 0 |
| Max Guild Members | 50+ (scales with level) |

---

## 🛠️ Development

### Project Structure
```
subjugate-online/
├── server/
│   ├── login_server/         # Authentication
│   ├── game_server/          # Core game logic
│   │   ├── combat_system.py
│   │   ├── reincarnation_system.py
│   │   ├── territory_system.py
│   │   ├── guild_system.py
│   │   ├── quest_system.py
│   │   ├── crafting_system.py
│   │   ├── achievement_system.py
│   │   ├── chat_system.py
│   │   ├── world_events.py
│   │   └── ...
│   ├── database/             # ORM models
│   ├── network/              # Protocol
│   └── admin/                # Admin tools
├── client/                   # 3D client
├── shared/                   # Shared code
└── FULL_DOCUMENTATION.md     # Complete docs
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📊 Features Checklist

✅ **Core Systems**
- [x] Separate Login/Game Servers
- [x] 3D Client (Panda3D)
- [x] Database (SQLAlchemy)
- [x] Network Protocol (MessagePack)

✅ **Gameplay**
- [x] Hardcore/Ultimate Ironman Modes
- [x] Reincarnation System with Perks
- [x] Territory Control (5 territories)
- [x] Combat System (12+ skills)
- [x] Character Progression (1-150)
- [x] NPC AI System

✅ **Advanced Features**
- [x] Guild/Clan System
- [x] Quest System (Story, Daily, Weekly)
- [x] Crafting & Gathering (4 professions, 4 gathering skills)
- [x] Achievement System (40+ achievements)
- [x] Leaderboards
- [x] Advanced Chat (Multi-channel)
- [x] World Events (7 events)
- [x] Day/Night Cycle & Weather
- [x] Admin Tools & Monitoring

---

## 🎮 Controls

### In-Game
- **WASD**: Movement
- **Space**: Basic Attack
- **T**: Target Nearest Enemy
- **R**: Request Reincarnation
- **ESC**: Quit Game

### Chat
- Type to open chat
- Multiple channels available

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Credits

**Inspired by**: Conquer Online 1.0
**Engine**: Panda3D
**Language**: Python 3.10+

---

## 🚀 Future Development

Potential features for future releases:
- Mobile client support
- Enhanced 3D graphics (shaders, particles)
- More professions and skills
- Additional territories
- Raid/dungeon instances
- Pet/companion system
- Player housing
- Auction house (view-only for ironman)

---

**⚔️ Welcome to Subjugate Online - Where Death is Just the Beginning! ⚔️**

For complete documentation, see [FULL_DOCUMENTATION.md](FULL_DOCUMENTATION.md)
