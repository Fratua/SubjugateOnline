# Subjugate Online

**A hyper-advanced, production-ready 3D MMORPG built from scratch in Python**

Subjugate Online is a hardcore ironman MMORPG inspired by early Conquer Online 1.0, featuring:
- **Hardcore/Ultimate Ironman gameplay** - Everyone plays solo, no trading
- **Reincarnation system** - Gain permanent perks based on your success in previous lives
- **Territory control** - PVP to control territories and gain powerful buffs (Conquer Online style)
- **Full 3D world** - Real-time 3D graphics powered by Panda3D
- **Complete server architecture** - Separate login and game servers
- **Production-ready code** - Comprehensive systems with proper architecture

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1: Start login server
python run_login_server.py

# Terminal 2: Start game server
python run_game_server.py

# Terminal 3: Start client
python run_client.py
```

## Game Features

### Core Systems
- **Reincarnation** - Die and be reborn with permanent perks
- **Territory Control** - 5 territories with powerful buffs
- **Combat** - Melee, ranged, magic with 12+ skills
- **NPCs** - Dynamic AI with aggro, patrolling, combat
- **Progression** - Level 1-150, experience-based
- **Ironman Modes** - Hardcore (bank) or Ultimate (no bank)

### Technology Stack
- **3D Engine**: Panda3D
- **Networking**: asyncio + MessagePack binary protocol
- **Database**: SQLite + SQLAlchemy ORM
- **Architecture**: Separate login/game servers, spatial partitioning

## Documentation

See full documentation in README for:
- Complete feature list
- Technical architecture
- Database schema
- Network protocol
- Gameplay guide
- Development guide

**Welcome to Subjugate Online - Where death is just the beginning!**
