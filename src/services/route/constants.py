"""
Route Service Constants

Trade hub definitions and regional mappings for EVE Online.
"""

from typing import Dict

# Trade hub system IDs
TRADE_HUB_SYSTEMS: Dict[str, int] = {
    'jita': 30000142,
    'amarr': 30002187,
    'rens': 30002510,
    'dodixie': 30002659,
    'hek': 30002053,
    'isikemi': 30001365,  # Home base for Minimal Industries
}

# Reverse lookup: System ID to hub name
SYSTEM_ID_TO_HUB: Dict[int, str] = {v: k for k, v in TRADE_HUB_SYSTEMS.items()}

# Region to hub mapping
REGION_TO_HUB: Dict[str, str] = {
    'the_forge': 'jita',
    'domain': 'amarr',
    'heimatar': 'rens',
    'sinq_laison': 'dodixie',
    'metropolis': 'hek',
}
