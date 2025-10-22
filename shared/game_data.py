"""
Subjugate Online - Game Data
Complete game data including skills, items, NPCs, and territories
"""

from shared.constants import (
    SkillType, ItemType, ItemRarity, EquipSlot, DamageType,
    NPCType, TerritoryType, ATTACK_RANGE_MELEE, ATTACK_RANGE_RANGED,
    ATTACK_RANGE_MAGIC
)

# ============================================================================
# COMPLETE SKILL DATABASE
# ============================================================================
SKILL_DATABASE = {
    # === MELEE SKILLS ===
    SkillType.SLASH: {
        'id': SkillType.SLASH,
        'name': 'Slash',
        'description': 'A quick slash attack',
        'damage_multiplier': 1.5,
        'mp_cost': 10,
        'cooldown': 3.0,
        'range': ATTACK_RANGE_MELEE,
        'damage_type': DamageType.PHYSICAL,
        'required_level': 1
    },
    SkillType.THRUST: {
        'id': SkillType.THRUST,
        'name': 'Thrust',
        'description': 'A powerful forward thrust',
        'damage_multiplier': 2.0,
        'mp_cost': 15,
        'cooldown': 4.0,
        'range': ATTACK_RANGE_MELEE * 1.5,
        'damage_type': DamageType.PHYSICAL,
        'required_level': 10
    },
    SkillType.CLEAVE: {
        'id': SkillType.CLEAVE,
        'name': 'Cleave',
        'description': 'Area attack hitting multiple enemies',
        'damage_multiplier': 1.8,
        'mp_cost': 25,
        'cooldown': 6.0,
        'range': ATTACK_RANGE_MELEE,
        'damage_type': DamageType.PHYSICAL,
        'aoe_radius': 3.0,
        'required_level': 20
    },

    # === RANGED SKILLS ===
    SkillType.POWER_SHOT: {
        'id': SkillType.POWER_SHOT,
        'name': 'Power Shot',
        'description': 'A powerful arrow shot',
        'damage_multiplier': 2.2,
        'mp_cost': 12,
        'cooldown': 3.5,
        'range': ATTACK_RANGE_RANGED,
        'damage_type': DamageType.PHYSICAL,
        'required_level': 1
    },
    SkillType.MULTI_SHOT: {
        'id': SkillType.MULTI_SHOT,
        'name': 'Multi Shot',
        'description': 'Fire multiple arrows at once',
        'damage_multiplier': 1.2,
        'mp_cost': 20,
        'cooldown': 5.0,
        'range': ATTACK_RANGE_RANGED,
        'damage_type': DamageType.PHYSICAL,
        'projectile_count': 5,
        'required_level': 15
    },
    SkillType.SNIPE: {
        'id': SkillType.SNIPE,
        'name': 'Snipe',
        'description': 'Extreme range precision shot',
        'damage_multiplier': 3.0,
        'mp_cost': 30,
        'cooldown': 8.0,
        'range': ATTACK_RANGE_RANGED * 2,
        'damage_type': DamageType.PHYSICAL,
        'required_level': 30
    },

    # === MAGIC SKILLS ===
    SkillType.FIREBALL: {
        'id': SkillType.FIREBALL,
        'name': 'Fireball',
        'description': 'Launch a ball of fire',
        'damage_multiplier': 2.5,
        'mp_cost': 20,
        'cooldown': 4.0,
        'range': ATTACK_RANGE_MAGIC,
        'damage_type': DamageType.MAGICAL,
        'required_level': 1
    },
    SkillType.ICE_LANCE: {
        'id': SkillType.ICE_LANCE,
        'name': 'Ice Lance',
        'description': 'Pierce enemy with ice, slowing them',
        'damage_multiplier': 2.0,
        'mp_cost': 18,
        'cooldown': 4.5,
        'range': ATTACK_RANGE_MAGIC,
        'damage_type': DamageType.MAGICAL,
        'slow_duration': 3.0,
        'required_level': 8
    },
    SkillType.LIGHTNING_BOLT: {
        'id': SkillType.LIGHTNING_BOLT,
        'name': 'Lightning Bolt',
        'description': 'Strike with lightning',
        'damage_multiplier': 2.8,
        'mp_cost': 25,
        'cooldown': 5.0,
        'range': ATTACK_RANGE_MAGIC * 1.2,
        'damage_type': DamageType.MAGICAL,
        'required_level': 18
    },
    SkillType.HEAL: {
        'id': SkillType.HEAL,
        'name': 'Heal',
        'description': 'Restore health',
        'heal_amount': 100,
        'mp_cost': 30,
        'cooldown': 10.0,
        'range': ATTACK_RANGE_MAGIC,
        'required_level': 12
    },

    # === ULTIMATE SKILLS ===
    SkillType.ULTIMATE_SLASH: {
        'id': SkillType.ULTIMATE_SLASH,
        'name': 'Ultimate Slash',
        'description': 'Devastating melee attack',
        'damage_multiplier': 5.0,
        'mp_cost': 50,
        'cooldown': 30.0,
        'range': ATTACK_RANGE_MELEE,
        'damage_type': DamageType.TRUE,
        'required_level': 50
    },
    SkillType.ULTIMATE_ARROW: {
        'id': SkillType.ULTIMATE_ARROW,
        'name': 'Ultimate Arrow',
        'description': 'Pierce through all enemies',
        'damage_multiplier': 4.5,
        'mp_cost': 50,
        'cooldown': 30.0,
        'range': ATTACK_RANGE_RANGED * 1.5,
        'damage_type': DamageType.TRUE,
        'piercing': True,
        'required_level': 50
    },
    SkillType.METEOR: {
        'id': SkillType.METEOR,
        'name': 'Meteor',
        'description': 'Call down a meteor',
        'damage_multiplier': 6.0,
        'mp_cost': 60,
        'cooldown': 40.0,
        'range': ATTACK_RANGE_MAGIC,
        'damage_type': DamageType.MAGICAL,
        'aoe_radius': 10.0,
        'required_level': 60
    }
}

# ============================================================================
# ITEM DATABASE
# ============================================================================
ITEM_DATABASE = {
    # === WEAPONS ===
    1001: {
        'id': 1001,
        'name': 'Iron Sword',
        'type': ItemType.WEAPON,
        'rarity': ItemRarity.COMMON,
        'slot': EquipSlot.WEAPON,
        'attack': 15,
        'required_level': 1,
        'description': 'A basic iron sword'
    },
    1002: {
        'id': 1002,
        'name': 'Steel Sword',
        'type': ItemType.WEAPON,
        'rarity': ItemRarity.UNCOMMON,
        'slot': EquipSlot.WEAPON,
        'attack': 30,
        'required_level': 10,
        'description': 'A sturdy steel sword'
    },
    1003: {
        'id': 1003,
        'name': 'Legendary Blade',
        'type': ItemType.WEAPON,
        'rarity': ItemRarity.LEGENDARY,
        'slot': EquipSlot.WEAPON,
        'attack': 150,
        'required_level': 80,
        'description': 'A blade of legends'
    },
    1010: {
        'id': 1010,
        'name': 'Short Bow',
        'type': ItemType.WEAPON,
        'rarity': ItemRarity.COMMON,
        'slot': EquipSlot.WEAPON,
        'attack': 12,
        'required_level': 1,
        'description': 'A simple bow'
    },
    1020: {
        'id': 1020,
        'name': 'Magic Staff',
        'type': ItemType.WEAPON,
        'rarity': ItemRarity.UNCOMMON,
        'slot': EquipSlot.WEAPON,
        'attack': 25,
        'required_level': 1,
        'description': 'A staff imbued with magic'
    },

    # === ARMOR ===
    2001: {
        'id': 2001,
        'name': 'Leather Helmet',
        'type': ItemType.ARMOR,
        'rarity': ItemRarity.COMMON,
        'slot': EquipSlot.HEAD,
        'defense': 5,
        'required_level': 1,
        'description': 'Basic head protection'
    },
    2002: {
        'id': 2002,
        'name': 'Iron Chestplate',
        'type': ItemType.ARMOR,
        'rarity': ItemRarity.COMMON,
        'slot': EquipSlot.CHEST,
        'defense': 20,
        'required_level': 5,
        'description': 'Solid iron protection'
    },
    2003: {
        'id': 2003,
        'name': 'Steel Greaves',
        'type': ItemType.ARMOR,
        'rarity': ItemRarity.UNCOMMON,
        'slot': EquipSlot.LEGS,
        'defense': 15,
        'required_level': 10,
        'description': 'Steel leg armor'
    },

    # === ACCESSORIES ===
    3001: {
        'id': 3001,
        'name': 'Ring of Strength',
        'type': ItemType.ACCESSORY,
        'rarity': ItemRarity.RARE,
        'slot': EquipSlot.RING_1,
        'attack': 10,
        'required_level': 20,
        'description': 'Increases attack power'
    },
    3002: {
        'id': 3002,
        'name': 'Amulet of Defense',
        'type': ItemType.ACCESSORY,
        'rarity': ItemRarity.RARE,
        'slot': EquipSlot.NECKLACE,
        'defense': 15,
        'required_level': 20,
        'description': 'Increases defense'
    },

    # === CONSUMABLES ===
    4001: {
        'id': 4001,
        'name': 'Health Potion',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect': 'heal',
        'value': 100,
        'description': 'Restores 100 HP'
    },
    4002: {
        'id': 4002,
        'name': 'Mana Potion',
        'type': ItemType.CONSUMABLE,
        'rarity': ItemRarity.COMMON,
        'effect': 'restore_mp',
        'value': 50,
        'description': 'Restores 50 MP'
    },
}

# ============================================================================
# NPC/MONSTER DATABASE
# ============================================================================
NPC_DATABASE = {
    # === BASIC MONSTERS ===
    5001: {
        'id': 5001,
        'name': 'Slime',
        'type': NPCType.MONSTER,
        'level': 1,
        'hp': 50,
        'attack': 5,
        'defense': 2,
        'xp_reward': 10,
        'loot_table': [4001],  # Health potion
        'aggro_range': 5.0,
        'model': 'slime'
    },
    5002: {
        'id': 5002,
        'name': 'Wolf',
        'type': NPCType.MONSTER,
        'level': 5,
        'hp': 150,
        'attack': 15,
        'defense': 8,
        'xp_reward': 50,
        'loot_table': [4001, 1001],
        'aggro_range': 8.0,
        'model': 'wolf'
    },
    5003: {
        'id': 5003,
        'name': 'Orc Warrior',
        'type': NPCType.MONSTER,
        'level': 15,
        'hp': 500,
        'attack': 35,
        'defense': 20,
        'xp_reward': 150,
        'loot_table': [1002, 2002, 4001],
        'aggro_range': 10.0,
        'model': 'orc'
    },

    # === BOSSES ===
    6001: {
        'id': 6001,
        'name': 'Dragon Lord',
        'type': NPCType.BOSS,
        'level': 50,
        'hp': 10000,
        'attack': 200,
        'defense': 100,
        'xp_reward': 5000,
        'loot_table': [1003, 3001, 3002],
        'aggro_range': 20.0,
        'skills': [SkillType.FIREBALL, SkillType.METEOR],
        'model': 'dragon'
    },
    6002: {
        'id': 6002,
        'name': 'Phoenix Guardian',
        'type': NPCType.BOSS,
        'level': 75,
        'hp': 25000,
        'attack': 350,
        'defense': 150,
        'xp_reward': 10000,
        'loot_table': [1003, 3001, 3002],
        'aggro_range': 25.0,
        'skills': [SkillType.FIREBALL, SkillType.METEOR, SkillType.HEAL],
        'respawn_time': 3600,  # 1 hour
        'model': 'phoenix'
    }
}

# ============================================================================
# TERRITORY DATABASE
# ============================================================================
TERRITORY_DATABASE = {
    TerritoryType.PHOENIX_CASTLE: {
        'id': TerritoryType.PHOENIX_CASTLE,
        'name': 'Phoenix Castle',
        'position': (500.0, 0.0, 500.0),
        'radius': 50.0,
        'capture_points_required': 1000,
        'default_controller': None
    },
    TerritoryType.TWIN_CITY: {
        'id': TerritoryType.TWIN_CITY,
        'name': 'Twin City',
        'position': (200.0, 0.0, 200.0),
        'radius': 40.0,
        'capture_points_required': 750,
        'default_controller': None
    },
    TerritoryType.DESERT_CITY: {
        'id': TerritoryType.DESERT_CITY,
        'name': 'Desert City',
        'position': (800.0, 0.0, 300.0),
        'radius': 35.0,
        'capture_points_required': 600,
        'default_controller': None
    },
    TerritoryType.APE_CITY: {
        'id': TerritoryType.APE_CITY,
        'name': 'Ape City',
        'position': (300.0, 0.0, 700.0),
        'radius': 35.0,
        'capture_points_required': 600,
        'default_controller': None
    },
    TerritoryType.BIRD_ISLAND: {
        'id': TerritoryType.BIRD_ISLAND,
        'name': 'Bird Island',
        'position': (700.0, 0.0, 700.0),
        'radius': 30.0,
        'capture_points_required': 500,
        'default_controller': None
    }
}

# ============================================================================
# LOOT TABLES
# ============================================================================
def get_loot_table(npc_id: int) -> list:
    """Get loot table for an NPC"""
    npc_data = NPC_DATABASE.get(npc_id)
    if not npc_data:
        return []
    return npc_data.get('loot_table', [])

def get_skill_data(skill_id: int) -> dict:
    """Get skill data by ID"""
    return SKILL_DATABASE.get(skill_id, {})

def get_item_data(item_id: int) -> dict:
    """Get item data by ID"""
    return ITEM_DATABASE.get(item_id, {})

def get_npc_data(npc_id: int) -> dict:
    """Get NPC data by ID"""
    return NPC_DATABASE.get(npc_id, {})

def get_territory_data(territory_id: int) -> dict:
    """Get territory data by ID"""
    return TERRITORY_DATABASE.get(territory_id, {})
