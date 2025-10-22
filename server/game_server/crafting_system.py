"""
Subjugate Online - Crafting and Gathering System
Allows players to gather resources and craft items (ironman-compatible)
"""

from typing import Dict, List, Optional, Tuple
from shared.utils import Logger
from shared.game_data import get_item_data
import random
import time

logger = Logger.get_logger(__name__)


class GatheringNode:
    """Represents a gathering node in the world"""

    def __init__(
        self,
        node_id: int,
        node_type: str,
        position: Tuple[float, float, float],
        required_level: int = 1
    ):
        self.node_id = node_id
        self.node_type = node_type  # 'mining', 'herbalism', 'woodcutting', 'fishing'
        self.position = position
        self.required_level = required_level
        self.depleted = False
        self.respawn_time = 300.0  # 5 minutes
        self.last_gathered = 0.0

        # Loot table with (item_id, min_amount, max_amount, chance)
        self.loot_table = []

    def can_gather(self, current_time: float) -> bool:
        """Check if node can be gathered"""
        if not self.depleted:
            return True

        # Check if respawned
        if current_time - self.last_gathered >= self.respawn_time:
            self.depleted = False
            return True

        return False

    def gather(self, character_level: int, skill_level: int) -> Optional[List[Tuple[int, int]]]:
        """
        Gather from this node

        Returns:
            List of (item_id, amount) tuples or None if failed
        """
        if self.depleted:
            return None

        if character_level < self.required_level:
            return None

        # Roll for loot
        items_gathered = []
        for item_id, min_amt, max_amt, chance in self.loot_table:
            # Skill level affects success chance
            adjusted_chance = chance * (1.0 + (skill_level * 0.01))

            if random.random() < adjusted_chance:
                amount = random.randint(min_amt, max_amt)
                items_gathered.append((item_id, amount))

        # Mark as depleted
        self.depleted = True
        self.last_gathered = time.time()

        return items_gathered if items_gathered else None


class CraftingRecipe:
    """Represents a crafting recipe"""

    def __init__(
        self,
        recipe_id: int,
        name: str,
        profession: str,
        required_level: int,
        result_item_id: int,
        result_amount: int = 1
    ):
        self.recipe_id = recipe_id
        self.name = name
        self.profession = profession  # 'blacksmithing', 'alchemy', 'tailoring', 'cooking'
        self.required_level = required_level
        self.result_item_id = result_item_id
        self.result_amount = result_amount

        # Materials: {item_id: amount}
        self.materials: Dict[int, int] = {}

        # Crafting time in seconds
        self.craft_time = 5.0

    def add_material(self, item_id: int, amount: int):
        """Add required material"""
        self.materials[item_id] = amount

    def can_craft(self, inventory: Dict[int, int], skill_level: int) -> bool:
        """Check if can craft with current inventory and skill"""
        if skill_level < self.required_level:
            return False

        # Check materials
        for item_id, required_amount in self.materials.items():
            if inventory.get(item_id, 0) < required_amount:
                return False

        return True


class CraftingSystem:
    """Manages crafting and gathering"""

    def __init__(self):
        self.recipes: Dict[int, CraftingRecipe] = {}
        self.gathering_nodes: Dict[int, GatheringNode] = {}
        self.player_skills: Dict[int, Dict[str, int]] = {}  # character_id -> {skill: level}

        # Initialize recipes and nodes
        self._initialize_crafting_recipes()
        self._initialize_gathering_nodes()

        logger.info("Crafting system initialized")

    def _initialize_crafting_recipes(self):
        """Initialize crafting recipes"""
        # === BLACKSMITHING ===
        recipe = CraftingRecipe(
            recipe_id=1,
            name="Iron Sword",
            profession="blacksmithing",
            required_level=1,
            result_item_id=1001,  # Iron Sword
            result_amount=1
        )
        recipe.add_material(5001, 5)  # 5x Iron Ore
        recipe.add_material(5002, 2)  # 2x Coal
        self.recipes[1] = recipe

        recipe = CraftingRecipe(
            recipe_id=2,
            name="Steel Sword",
            profession="blacksmithing",
            required_level=10,
            result_item_id=1002,  # Steel Sword
            result_amount=1
        )
        recipe.add_material(5003, 10)  # 10x Steel Bar
        recipe.add_material(5004, 5)  # 5x Leather
        self.recipes[2] = recipe

        # === ALCHEMY ===
        recipe = CraftingRecipe(
            recipe_id=100,
            name="Health Potion",
            profession="alchemy",
            required_level=1,
            result_item_id=4001,  # Health Potion
            result_amount=3
        )
        recipe.add_material(5100, 2)  # 2x Healing Herb
        recipe.add_material(5101, 1)  # 1x Empty Bottle
        self.recipes[100] = recipe

        recipe = CraftingRecipe(
            recipe_id=101,
            name="Mana Potion",
            profession="alchemy",
            required_level=5,
            result_item_id=4002,  # Mana Potion
            result_amount=3
        )
        recipe.add_material(5102, 2)  # 2x Mana Flower
        recipe.add_material(5101, 1)  # 1x Empty Bottle
        self.recipes[101] = recipe

        logger.info(f"Loaded {len(self.recipes)} crafting recipes")

    def _initialize_gathering_nodes(self):
        """Initialize gathering nodes in the world"""
        # === MINING NODES ===
        node = GatheringNode(1, 'mining', (150.0, 0.0, 150.0), required_level=1)
        node.loot_table = [
            (5001, 1, 3, 0.8),  # Iron Ore
            (5002, 1, 2, 0.3),  # Coal
        ]
        self.gathering_nodes[1] = node

        node = GatheringNode(2, 'mining', (180.0, 0.0, 120.0), required_level=10)
        node.loot_table = [
            (5003, 1, 2, 0.6),  # Steel Bar
            (5005, 1, 1, 0.1),  # Rare Gem
        ]
        self.gathering_nodes[2] = node

        # === HERBALISM NODES ===
        node = GatheringNode(100, 'herbalism', (200.0, 0.0, 200.0), required_level=1)
        node.loot_table = [
            (5100, 1, 3, 0.9),  # Healing Herb
        ]
        self.gathering_nodes[100] = node

        node = GatheringNode(101, 'herbalism', (220.0, 0.0, 180.0), required_level=5)
        node.loot_table = [
            (5102, 1, 3, 0.7),  # Mana Flower
            (5103, 1, 1, 0.2),  # Rare Herb
        ]
        self.gathering_nodes[101] = node

        # === WOODCUTTING NODES ===
        node = GatheringNode(200, 'woodcutting', (250.0, 0.0, 250.0), required_level=1)
        node.loot_table = [
            (5200, 1, 5, 0.9),  # Oak Wood
        ]
        self.gathering_nodes[200] = node

        # === FISHING SPOTS ===
        node = GatheringNode(300, 'fishing', (100.0, 0.0, 100.0), required_level=1)
        node.loot_table = [
            (5300, 1, 1, 0.7),  # Common Fish
            (5301, 1, 1, 0.2),  # Rare Fish
        ]
        self.gathering_nodes[300] = node

        logger.info(f"Spawned {len(self.gathering_nodes)} gathering nodes")

    def gather_from_node(
        self,
        character_id: int,
        node_id: int,
        character_level: int
    ) -> Optional[List[Tuple[int, int]]]:
        """
        Gather from a node

        Returns:
            List of (item_id, amount) gathered or None if failed
        """
        node = self.gathering_nodes.get(node_id)
        if not node:
            return None

        # Get player's skill level for this profession
        skill_level = self._get_skill_level(character_id, node.node_type)

        # Attempt to gather
        items = node.gather(character_level, skill_level)

        if items:
            # Award skill XP
            self._add_skill_experience(character_id, node.node_type, 10)
            logger.info(f"Character {character_id} gathered from node {node_id}: {items}")

        return items

    def craft_item(
        self,
        character_id: int,
        recipe_id: int,
        inventory: Dict[int, int]
    ) -> Optional[Tuple[int, int]]:
        """
        Craft an item

        Args:
            character_id: Character ID
            recipe_id: Recipe ID
            inventory: Current inventory {item_id: amount}

        Returns:
            (result_item_id, amount) or None if failed
        """
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return None

        # Get player's skill level
        skill_level = self._get_skill_level(character_id, recipe.profession)

        # Check if can craft
        if not recipe.can_craft(inventory, skill_level):
            return None

        # Consume materials (this would be done in inventory system)
        # For now, just return the result

        # Award skill XP
        self._add_skill_experience(character_id, recipe.profession, 25)

        logger.info(f"Character {character_id} crafted {recipe.name}")

        return (recipe.result_item_id, recipe.result_amount)

    def _get_skill_level(self, character_id: int, skill: str) -> int:
        """Get player's skill level"""
        if character_id not in self.player_skills:
            self.player_skills[character_id] = {}

        return self.player_skills[character_id].get(skill, 1)

    def _add_skill_experience(self, character_id: int, skill: str, xp: int):
        """Add skill experience"""
        if character_id not in self.player_skills:
            self.player_skills[character_id] = {}

        if skill not in self.player_skills[character_id]:
            self.player_skills[character_id][skill] = 1

        # Simplified skill leveling
        current_level = self.player_skills[character_id][skill]
        if current_level < 99:
            # Every 100 XP = 1 level (simplified)
            # In production, this would use an experience table
            pass

    def get_recipes_for_profession(self, profession: str, skill_level: int) -> List[CraftingRecipe]:
        """Get available recipes for a profession"""
        return [
            r for r in self.recipes.values()
            if r.profession == profession and skill_level >= r.required_level
        ]

    def get_nearby_nodes(
        self,
        position: Tuple[float, float, float],
        radius: float
    ) -> List[GatheringNode]:
        """Get gathering nodes near a position"""
        from shared.utils import calculate_distance

        nearby = []
        for node in self.gathering_nodes.values():
            if calculate_distance(position, node.position) <= radius:
                nearby.append(node)

        return nearby

    def update_nodes(self, delta_time: float):
        """Update gathering nodes (respawn timer)"""
        current_time = time.time()

        for node in self.gathering_nodes.values():
            if node.depleted:
                if current_time - node.last_gathered >= node.respawn_time:
                    node.depleted = False

    def get_player_skills(self, character_id: int) -> Dict[str, int]:
        """Get player's skill levels"""
        return self.player_skills.get(character_id, {}).copy()
