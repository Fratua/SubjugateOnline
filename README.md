# Subjugate Online

A production-ready 3D MMORPG featuring hardcore ironman mechanics, reincarnation systems, and PVP-driven territory control.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

## Overview

**Subjugate Online** is a hardcore 3D MMORPG where every player is an ironman by default, with the option to play in ultimate hardcore ironman mode. The game features:

- **Permanent Death with Reincarnation**: When you die, you reincarnate with perks based on your achievements
- **Territory Control**: PVP-driven territorial warfare for powerful buffs (inspired by Conquer Online 1.0)
- **Hardcore Ironman**: Everyone is hardcore ironman - no trading, no group benefits
- **Ultimate Hardcore Ironman**: Extreme challenge mode - no banking allowed
- **Perk System**: Accumulate permanent perks through successful lives
- **Full 3D World**: OpenGL-based 3D rendering with real-time combat

## Features

### Core Game Systems

#### Reincarnation System
- Death is permanent but leads to reincarnation
- Earn perks based on:
  - Level achieved
  - PVP kills
  - Territory captures
  - Damage dealt
  - Time played
- Perks stack across lives for progressive power

#### Territory Control (Conquer Online Style)
- 5 major territories across the world
- Guilds fight for control
- Controlled territories provide powerful buffs:
  - Experience bonuses
  - Attack/defense bonuses
  - Magic power bonuses
  - Special PVP bonuses

#### Hardcore Ironman Modes
- **Hardcore Ironman** (Default):
  - Solo progression only
  - No trading
  - No group benefits
  - Death means reincarnation

- **Ultimate Hardcore Ironman** (Optional):
  - All hardcore ironman restrictions
  - No banking (inventory only)
  - Extra challenge for extra rewards

### Technical Features

#### Server Architecture
- **Login Server**: Account authentication and character management
- **Game Server**: World simulation, combat, and territory control
- **PostgreSQL Database**: Production-ready persistent storage
- **Async Networking**: High-performance async I/O with custom binary protocol

#### Client Features
- **3D OpenGL Rendering**: Full 3D world with dynamic camera
- **Real-time Combat**: Fast-paced action combat
- **Territory Visualization**: See territory control in real-time
- **Chat System**: Global and guild chat
- **HUD**: Comprehensive stats display

## Installation

### Requirements

- Python 3.8 or higher
- PostgreSQL 12 or higher
- OpenGL-compatible graphics card
- 4GB RAM minimum (8GB recommended)

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/subjugate-online.git
cd subjugate-online
```

2. **Run the installation script**
```bash
chmod +x deploy/install.sh
./deploy/install.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Set up the PostgreSQL database
- Create required directories

### Manual Installation

If you prefer manual installation:

1. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up PostgreSQL database**
```bash
chmod +x deploy/setup_database.sh
./deploy/setup_database.sh
```

4. **Install the package**
```bash
pip install -e .
```

## Running the Game

### Start Servers

**Option 1: Using convenience script**
```bash
./deploy/start_servers.sh
```

**Option 2: Manual start**
```bash
# Terminal 1 - Login Server
python -m subjugate_online.login_server.server

# Terminal 2 - Game Server
python -m subjugate_online.game_server.server
```

### Create Test Account

```bash
python deploy/create_test_account.py
```

This creates:
- Username: `testuser`
- Password: `password123`

### Start Client

**Option 1: Using convenience script**
```bash
./deploy/start_client.sh
```

**Option 2: Manual start**
```bash
python -m subjugate_online.client.client
```

### Stop Servers

```bash
./deploy/stop_servers.sh
```

## Game Controls

### Movement
- `W` - Move forward
- `S` - Move backward
- `A` - Move left
- `D` - Move right

### Camera
- `Right Mouse Button + Drag` - Rotate camera
- `Mouse Wheel` - Zoom in/out

### Combat
- `Space` - Attack nearest target
- `Tab` - Cycle targets (planned)

### UI
- `Enter` - Open chat
- `R` - Reincarnate (when dead)
- `ESC` - Quit game

## Architecture

### Directory Structure

```
subjugate_online/
├── shared/           # Shared code between client and servers
│   ├── protocol.py   # Network protocol definition
│   ├── network.py    # Async networking layer
│   ├── database.py   # Database models and ORM
│   └── utils.py      # Utility functions
├── login_server/     # Login server
│   └── server.py     # Authentication and character management
├── game_server/      # Game server
│   ├── server.py     # Main game server
│   ├── world.py      # World management
│   └── entities.py   # Player and NPC entities
├── client/           # 3D client
│   ├── client.py     # Main client application
│   ├── renderer.py   # 3D rendering engine
│   └── network_client.py  # Client networking
├── config/           # Configuration files
├── assets/           # Game assets
└── deploy/           # Deployment scripts
```

### Network Protocol

Custom binary packet-based protocol with:
- Efficient serialization
- Automatic compression for large payloads
- Checksum validation
- Sequence numbering
- Support for 999+ packet types

### Database Schema

- **Accounts**: User authentication
- **Characters**: Player characters with stats
- **Guilds**: Player guilds for territory control
- **Territories**: Controllable regions
- **ReincarnationHistory**: Track past lives
- **WorldState**: Global game state

## Game Design

### Progression System

1. **Start**: Level 1, no perks
2. **Level Up**: Gain stats, unlock abilities
3. **PVP**: Kill other players for experience
4. **Territory Control**: Capture territories for buffs
5. **Death**: Calculate reincarnation score
6. **Reincarnate**: Start over with new perks
7. **Repeat**: Each life makes you stronger

### Reincarnation Perks

Perks are earned based on reincarnation score:

**Tier 1 (Score 100-999)**
- Reincarnated Soul: +5% experience
- Battle Veteran: +10 max health

**Tier 2 (Score 1000-1999)**
- Warrior's Spirit: +5% attack power
- Iron Will: +5% defense

**Tier 3 (Score 2000-2999)**
- Legendary Hero: +10% all stats
- Immortal Essence: +15% experience

**Tier 4 (Score 3000+)**
- Ascended Being: +20% damage, +10% damage reduction
- Divine Champion: Start at level 10

### Territory Buffs

Each territory provides unique buffs:

- **Central Plaza**: +10% XP, +5% drop rate
- **Northern Fortress**: +15% attack, +10% defense
- **Eastern Sanctuary**: +20% magic power, +5% mana regen
- **Southern Outpost**: +50 max HP, +3% health regen
- **Western Arena**: +25% PVP damage, +15% kill XP

## Development

### Running Tests

```bash
pytest
```

### Code Style

```bash
black subjugate_online/
```

## Configuration

### Server Configuration

Edit `subjugate_online/config/server_config.json`:

```json
{
  "login_server": {
    "host": "0.0.0.0",
    "port": 8888
  },
  "game_server": {
    "host": "0.0.0.0",
    "port": 8889,
    "tick_rate": 20
  }
}
```

### Client Configuration

Edit `subjugate_online/config/client_config.json`:

```json
{
  "graphics": {
    "width": 1280,
    "height": 720,
    "fullscreen": false
  },
  "network": {
    "login_server": {
      "host": "localhost",
      "port": 8888
    }
  }
}
```

## Production Deployment

### Requirements

- Linux server (Ubuntu 20.04+ recommended)
- PostgreSQL 12+
- 2+ CPU cores
- 4GB+ RAM
- 10GB+ disk space

### Deployment Steps

1. **Install dependencies**
```bash
sudo apt-get update
sudo apt-get install python3.10 python3-pip postgresql
```

2. **Clone and setup**
```bash
git clone https://github.com/yourusername/subjugate-online.git
cd subjugate-online
./deploy/install.sh
```

3. **Configure for production**
- Update database credentials
- Set proper host addresses
- Configure firewall rules (ports 8888, 8889)

## Troubleshooting

### Connection Issues

**Problem**: Can't connect to server

**Solution**:
```bash
# Check if servers are running
ps aux | grep subjugate

# Check if ports are open
netstat -tulpn | grep -E '8888|8889'
```

### Database Issues

**Problem**: Database connection failed

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Verify database exists
psql -U postgres -c "\l" | grep subjugate_online
```

### Graphics Issues

**Problem**: Client crashes or black screen

**Solution**:
- Update graphics drivers
- Ensure OpenGL support: `glxinfo | grep OpenGL`

## License

MIT License - see LICENSE file for details

## Credits

- Inspired by Conquer Online 1.0 territory system
- Built with Python, PostgreSQL, OpenGL, and Pygame

---

**Built with ❤️ for hardcore MMORPG fans**
