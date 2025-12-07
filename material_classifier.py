"""
EVE Co-Pilot Material Classifier
Categorizes materials by source and determines blueprint manufacturability
"""

from typing import Dict, List, Set, Tuple
from database import get_db_connection, get_item_info


# Material source categories
class MaterialSource:
    """Enum-like class for material sources"""
    MINERAL = "mineral"              # Basic ores -> minerals (Tritanium, etc.)
    PI = "planetary"                 # Planetary Interaction
    ICE = "ice"                      # Ice products
    MOON = "moon"                    # Moon materials
    SALVAGE = "salvage"              # Salvaged materials
    ANCIENT_SALVAGE = "ancient"      # Sleeper/Ancient salvage (wormhole)
    EXPLORATION = "exploration"       # Exploration loot (decryptors, datacores)
    COMPONENT = "component"          # Manufactured components (T2, T3, Capital)
    REACTION = "reaction"            # Reaction products
    COMMODITY = "commodity"          # Trade goods, special items
    ABYSSAL = "abyssal"              # Abyssal materials
    DRONE = "drone"                  # Rogue drone components
    SPECIAL = "special"              # Event items, unobtainable


# Group IDs for classification
MATERIAL_GROUPS = {
    # Minerals (groupID 18) - the most common
    18: MaterialSource.MINERAL,

    # Planetary commodities
    1042: MaterialSource.PI,  # Basic - Tier 1
    1034: MaterialSource.PI,  # Refined - Tier 2
    1040: MaterialSource.PI,  # Specialized - Tier 3
    1041: MaterialSource.PI,  # Advanced - Tier 4

    # Ice products
    423: MaterialSource.ICE,

    # Moon materials
    427: MaterialSource.MOON,
    428: MaterialSource.MOON,  # Intermediate Materials

    # Composites (from reactions)
    429: MaterialSource.REACTION,

    # Salvage
    754: MaterialSource.SALVAGE,

    # Ancient/Sleeper salvage
    966: MaterialSource.ANCIENT_SALVAGE,

    # Exploration/Hacking loot
    732: MaterialSource.EXPLORATION,  # Decryptors - Sleepers
    733: MaterialSource.EXPLORATION,  # Decryptors - Yan Jung
    734: MaterialSource.EXPLORATION,  # Decryptors - Takmahl
    735: MaterialSource.EXPLORATION,  # Decryptors - Talocan
    1141: MaterialSource.EXPLORATION,  # Research Data / Datacores
    528: MaterialSource.EXPLORATION,  # Artifacts and Prototypes

    # Commodities - exploration/special loot (group 526)
    526: MaterialSource.EXPLORATION,

    # Construction Components
    334: MaterialSource.COMPONENT,  # Standard components
    873: MaterialSource.COMPONENT,  # Capital components
    913: MaterialSource.COMPONENT,  # Advanced Capital components
    964: MaterialSource.COMPONENT,  # Hybrid Tech components
    536: MaterialSource.COMPONENT,  # Structure components

    # Hybrid Polymers (T3)
    974: MaterialSource.REACTION,

    # Biochemicals
    712: MaterialSource.REACTION,

    # Abyssal materials
    1996: MaterialSource.ABYSSAL,

    # Rogue Drone components
    886: MaterialSource.DRONE,

    # Named/Special components
    1676: MaterialSource.SPECIAL,
    1314: MaterialSource.SPECIAL,  # Unknown Components

    # Fuel blocks
    1136: MaterialSource.ICE,

    # Materials and Compounds (group 530) - often exploration loot
    530: MaterialSource.EXPLORATION,

    # Molecular-Forged Materials (group 4096)
    4096: MaterialSource.SPECIAL,
}


# Difficulty ratings for material sources
SOURCE_DIFFICULTY = {
    MaterialSource.MINERAL: 1,       # Easy - just buy on market
    MaterialSource.PI: 2,            # Medium - need PI setup or buy
    MaterialSource.ICE: 2,           # Medium - need ice mining or buy
    MaterialSource.MOON: 3,          # Harder - moon mining or buy (expensive)
    MaterialSource.SALVAGE: 2,       # Medium - mission running or buy
    MaterialSource.ANCIENT_SALVAGE: 4,  # Hard - wormholes only
    MaterialSource.EXPLORATION: 4,   # Hard - exploration only
    MaterialSource.COMPONENT: 2,     # Medium - manufactured, check recursively
    MaterialSource.REACTION: 3,      # Harder - reaction chains
    MaterialSource.ABYSSAL: 4,       # Hard - abyssal deadspace only
    MaterialSource.DRONE: 3,         # Harder - drone regions
    MaterialSource.SPECIAL: 5,       # Very hard - events, limited sources
    MaterialSource.COMMODITY: 3,     # Variable
}


class MaterialClassifier:
    """Classifies materials and determines blueprint manufacturability"""

    def __init__(self):
        self._group_cache: Dict[int, int] = {}  # type_id -> group_id
        self._category_cache: Dict[int, int] = {}  # type_id -> category_id

    def get_material_group(self, type_id: int) -> int:
        """Get the groupID for a material"""
        if type_id in self._group_cache:
            return self._group_cache[type_id]

        info = get_item_info(type_id)
        if info:
            group_id = info.get("groupID", 0)
            self._group_cache[type_id] = group_id
            return group_id
        return 0

    def classify_material(self, type_id: int) -> str:
        """Classify a material by its source"""
        group_id = self.get_material_group(type_id)

        if group_id in MATERIAL_GROUPS:
            return MATERIAL_GROUPS[group_id]

        # Check category for broader classification
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT ig."categoryID"
                    FROM "invTypes" it
                    JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                    WHERE it."typeID" = %s
                ''', (type_id,))
                result = cur.fetchone()
                if result:
                    category_id = result[0]
                    # Planetary
                    if category_id == 43:
                        return MaterialSource.PI
                    # Commodity
                    if category_id == 17:
                        return MaterialSource.COMMODITY
                    # Material
                    if category_id == 4:
                        return MaterialSource.MINERAL  # Default for category 4

        return MaterialSource.COMMODITY  # Default

    def classify_bom(self, bom: Dict[int, int]) -> Dict[str, List[Dict]]:
        """
        Classify all materials in a Bill of Materials.

        Returns dict grouped by source type:
        {
            "mineral": [{"type_id": 34, "name": "Tritanium", "quantity": 1000}, ...],
            "planetary": [...],
            ...
        }
        """
        result: Dict[str, List[Dict]] = {}

        for type_id, quantity in bom.items():
            source = self.classify_material(type_id)
            info = get_item_info(type_id)
            name = info.get("typeName", "Unknown") if info else "Unknown"

            if source not in result:
                result[source] = []

            result[source].append({
                "type_id": type_id,
                "name": name,
                "quantity": quantity
            })

        return result

    def get_manufacturability_score(self, bom: Dict[int, int]) -> Dict:
        """
        Calculate a manufacturability score for a blueprint.

        Returns:
            {
                "score": 1-5 (1=easy, 5=hard/impossible),
                "sources": {"mineral": 5, "pi": 2, ...},
                "warnings": ["Requires ancient salvage", ...],
                "is_market_only": True/False
            }
        """
        if not bom:
            return {"score": 5, "sources": {}, "warnings": ["No BOM found"], "is_market_only": False}

        classified = self.classify_bom(bom)
        sources: Dict[str, int] = {}
        warnings: List[str] = []
        max_difficulty = 1

        for source, materials in classified.items():
            count = len(materials)
            sources[source] = count
            difficulty = SOURCE_DIFFICULTY.get(source, 3)

            if difficulty > max_difficulty:
                max_difficulty = difficulty

            # Add warnings for difficult sources
            if source == MaterialSource.ANCIENT_SALVAGE:
                warnings.append(f"Requires ancient salvage ({count} types) - wormhole only")
            elif source == MaterialSource.EXPLORATION:
                warnings.append(f"Requires exploration loot ({count} types) - not on market")
            elif source == MaterialSource.ABYSSAL:
                warnings.append(f"Requires abyssal materials ({count} types)")
            elif source == MaterialSource.SPECIAL:
                warnings.append(f"Requires special/event materials ({count} types)")
            elif source == MaterialSource.DRONE:
                warnings.append(f"Requires rogue drone components ({count} types)")

        # Check if all materials are easily available on market
        easy_sources = {MaterialSource.MINERAL, MaterialSource.PI, MaterialSource.ICE,
                        MaterialSource.SALVAGE, MaterialSource.COMPONENT}
        is_market_only = all(s in easy_sources for s in classified.keys())

        return {
            "score": max_difficulty,
            "sources": sources,
            "warnings": warnings,
            "is_market_only": is_market_only
        }

    def is_manufacturable(self, bom: Dict[int, int], max_difficulty: int = 2) -> bool:
        """
        Quick check if a blueprint is easily manufacturable.

        Args:
            bom: Bill of Materials
            max_difficulty: Maximum acceptable difficulty (default 2 = minerals + PI + ice)
        """
        result = self.get_manufacturability_score(bom)
        return result["score"] <= max_difficulty


# Global classifier instance
material_classifier = MaterialClassifier()
