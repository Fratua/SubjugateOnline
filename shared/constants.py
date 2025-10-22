"""
Subjugate Online - Game Constants
All game-wide constants and configuration values
"""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================
LOGIN_SERVER_HOST = "127.0.0.1"
LOGIN_SERVER_PORT = 5000
GAME_SERVER_HOST = "127.0.0.1"
GAME_SERVER_PORT = 5001
MAX_PACKET_SIZE = 65535
TICK_RATE = 20  # Server updates per second
NETWORK_UPDATE_RATE = 10  # Network sync rate per second

# ============================================================================
# GAME MODES
# ============================================================================
class GameMode:
    HARDCORE_IRONMAN = 0  # Default: solo progression, can bank
    ULTIMATE_IRONMAN = 1  # Cannot use bank, inventory only

# ============================================================================
# PLAYER CONFIGURATION
# ============================================================================
MAX_LEVEL = 150
BASE_HP = 100
BASE_MP = 50
BASE_ATTACK = 10
BASE_DEFENSE = 10
BASE_SPEED = 5.0

# Starting stats
STARTING_LEVEL = 1
STARTING_HP = 100
STARTING_MP = 50

# Inventory
MAX_INVENTORY_SLOTS = 40
MAX_BANK_SLOTS = 200  # Only for Hardcore Ironman

# ============================================================================
# COMBAT SYSTEM
# ============================================================================
ATTACK_RANGE_MELEE = 2.0
ATTACK_RANGE_RANGED = 15.0
ATTACK_RANGE_MAGIC = 20.0
ATTACK_COOLDOWN = 1.5  # seconds
RESPAWN_TIME = 5.0  # seconds after death

class CombatStyle:
    MELEE = 0
    RANGED = 1
    MAGIC = 2

class DamageType:
    PHYSICAL = 0
    MAGICAL = 1
    TRUE = 2  # Ignores defense

# ============================================================================
# REINCARNATION SYSTEM
# ============================================================================
REINCARNATION_LEVEL_REQUIREMENT = 100  # Min level to reincarnate
MAX_REINCARNATIONS = 10

# Success metrics for perk calculation
class SuccessMetrics:
    LEVEL_WEIGHT = 0.3
    KILLS_WEIGHT = 0.2
    TERRITORY_WEIGHT = 0.25
    BOSS_KILLS_WEIGHT = 0.15
    PLAYTIME_WEIGHT = 0.1

# Perk bonuses per reincarnation (stacking)
PERK_HP_BONUS = 50
PERK_MP_BONUS = 25
PERK_ATTACK_BONUS = 5
PERK_DEFENSE_BONUS = 5
PERK_SPEED_BONUS = 0.5
PERK_XP_MULTIPLIER = 0.1  # 10% per reincarnation

# ============================================================================
# TERRITORY CONTROL SYSTEM (Conquer Online inspired)
# ============================================================================
TERRITORY_UPDATE_INTERVAL = 300  # 5 minutes
TERRITORY_CAPTURE_TIME = 60  # seconds to capture
MIN_PLAYERS_TO_CAPTURE = 1

class TerritoryType:
    PHOENIX_CASTLE = 0
    TWIN_CITY = 1
    DESERT_CITY = 2
    APE_CITY = 3
    BIRD_ISLAND = 4

# Territory buffs (applied to controlling guild/players)
TERRITORY_BUFFS = {
    TerritoryType.PHOENIX_CASTLE: {
        'hp_bonus': 500,
        'attack_bonus': 50,
        'defense_bonus': 50,
        'xp_bonus': 0.5
    },
    TerritoryType.TWIN_CITY: {
        'hp_bonus': 300,
        'attack_bonus': 30,
        'xp_bonus': 0.3
    },
    TerritoryType.DESERT_CITY: {
        'hp_bonus': 200,
        'attack_bonus': 25,
        'xp_bonus': 0.2
    },
    TerritoryType.APE_CITY: {
        'hp_bonus': 200,
        'defense_bonus': 25,
        'xp_bonus': 0.2
    },
    TerritoryType.BIRD_ISLAND: {
        'hp_bonus': 150,
        'attack_bonus': 20,
        'xp_bonus': 0.15
    }
}

# ============================================================================
# WORLD CONFIGURATION
# ============================================================================
WORLD_SIZE = 1000.0  # World is 1000x1000 units
CHUNK_SIZE = 50.0  # Spatial partitioning chunk size
VIEW_DISTANCE = 100.0  # Player view distance

# Map zones
class ZoneType:
    SAFE_ZONE = 0  # No PVP
    PVP_ZONE = 1  # Open PVP
    TERRITORY_ZONE = 2  # Territory control area
    DUNGEON = 3

# ============================================================================
# NPC & MONSTER CONFIGURATION
# ============================================================================
class NPCType:
    MONSTER = 0
    BOSS = 1
    VENDOR = 2
    QUEST_GIVER = 3

# Monster difficulty scaling
MONSTER_HP_SCALE = 1.5
MONSTER_DAMAGE_SCALE = 1.2
BOSS_HP_SCALE = 5.0
BOSS_DAMAGE_SCALE = 2.0

# ============================================================================
# SKILLS & ABILITIES
# ============================================================================
MAX_SKILL_LEVEL = 10

class SkillType:
    # Melee
    SLASH = 0
    THRUST = 1
    CLEAVE = 2

    # Ranged
    POWER_SHOT = 10
    MULTI_SHOT = 11
    SNIPE = 12

    # Magic
    FIREBALL = 20
    ICE_LANCE = 21
    LIGHTNING_BOLT = 22
    HEAL = 23

    # Ultimate
    ULTIMATE_SLASH = 30
    ULTIMATE_ARROW = 31
    METEOR = 32

SKILL_DATA = {
    SkillType.SLASH: {
        'name': 'Slash',
        'damage': 1.5,
        'mp_cost': 10,
        'cooldown': 3.0,
        'range': ATTACK_RANGE_MELEE,
        'type': DamageType.PHYSICAL
    },
    SkillType.FIREBALL: {
        'name': 'Fireball',
        'damage': 2.0,
        'mp_cost': 20,
        'cooldown': 4.0,
        'range': ATTACK_RANGE_MAGIC,
        'type': DamageType.MAGICAL
    },
    # ... More skills defined in game_data.py
}

# ============================================================================
# ITEM SYSTEM
# ============================================================================
class ItemType:
    WEAPON = 0
    ARMOR = 1
    ACCESSORY = 2
    CONSUMABLE = 3
    MATERIAL = 4
    QUEST = 5

class ItemRarity:
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    EPIC = 3
    LEGENDARY = 4
    MYTHIC = 5

# Equipment slots
class EquipSlot:
    WEAPON = 0
    HEAD = 1
    CHEST = 2
    LEGS = 3
    BOOTS = 4
    GLOVES = 5
    RING_1 = 6
    RING_2 = 7
    NECKLACE = 8

# ============================================================================
# PACKET TYPES
# ============================================================================
class PacketType:
    # Auth packets (0-99)
    LOGIN_REQUEST = 0
    LOGIN_RESPONSE = 1
    REGISTER_REQUEST = 2
    REGISTER_RESPONSE = 3
    CHARACTER_LIST_REQUEST = 4
    CHARACTER_LIST_RESPONSE = 5
    CHARACTER_CREATE_REQUEST = 6
    CHARACTER_CREATE_RESPONSE = 7
    CHARACTER_SELECT_REQUEST = 8
    CHARACTER_SELECT_RESPONSE = 9

    # Game server connection (100-199)
    GAME_SERVER_CONNECT = 100
    GAME_SERVER_HANDSHAKE = 101

    # Player movement (200-299)
    PLAYER_MOVE = 200
    PLAYER_POSITION_UPDATE = 201
    PLAYER_SPAWN = 202
    PLAYER_DESPAWN = 203

    # Combat (300-399)
    ATTACK_REQUEST = 300
    ATTACK_RESPONSE = 301
    SKILL_USE = 302
    DAMAGE_DEALT = 303
    PLAYER_DEATH = 304
    PLAYER_RESPAWN = 305

    # Stats & Inventory (400-499)
    STATS_UPDATE = 400
    INVENTORY_UPDATE = 401
    EQUIPMENT_UPDATE = 402
    ITEM_USE = 403
    ITEM_DROP = 404
    ITEM_PICKUP = 405

    # Reincarnation (500-599)
    REINCARNATION_REQUEST = 500
    REINCARNATION_RESPONSE = 501
    PERK_UPDATE = 502

    # Territory Control (600-699)
    TERRITORY_STATUS = 600
    TERRITORY_CAPTURE_START = 601
    TERRITORY_CAPTURE_PROGRESS = 602
    TERRITORY_CAPTURED = 603
    BUFF_UPDATE = 604

    # Chat & Social (700-799)
    CHAT_MESSAGE = 700
    WHISPER_MESSAGE = 701
    GUILD_MESSAGE = 702

    # World & NPCs (800-899)
    NPC_SPAWN = 800
    NPC_DESPAWN = 801
    NPC_UPDATE = 802
    WORLD_STATE = 803

    # Error & System (900-999)
    ERROR = 900
    HEARTBEAT = 901
    DISCONNECT = 902

# ============================================================================
# ERROR CODES
# ============================================================================
class ErrorCode:
    SUCCESS = 0
    INVALID_CREDENTIALS = 1
    ACCOUNT_EXISTS = 2
    INVALID_SESSION = 3
    CHARACTER_EXISTS = 4
    INVALID_CHARACTER = 5
    SERVER_FULL = 6
    MAINTENANCE = 7
    BANNED = 8
    INVALID_PACKET = 9
    NOT_ENOUGH_RESOURCES = 10
    INVALID_ACTION = 11
    COOLDOWN_ACTIVE = 12
    OUT_OF_RANGE = 13
    INSUFFICIENT_LEVEL = 14
    IRONMAN_RESTRICTION = 15

# ============================================================================
# DATABASE
# ============================================================================
DB_PATH = "data/subjugate_online.db"
SESSION_EXPIRY = 3600  # 1 hour

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
