"""
Cargo Service Constants

Ship cargo capacities and related constants
"""

from typing import Dict, Any


# Ship cargo capacities (m³)
SHIP_CARGO: Dict[str, Dict[str, Any]] = {
    'shuttle': {
        'capacity': 10,
        'name': 'Shuttle'
    },
    'frigate': {
        'capacity': 400,
        'name': 'Frigate'
    },
    'destroyer': {
        'capacity': 500,
        'name': 'Destroyer'
    },
    'cruiser': {
        'capacity': 500,
        'name': 'Cruiser'
    },
    'industrial': {
        'capacity': 5000,
        'name': 'Industrial (Nereus, etc.)'
    },
    'blockade_runner': {
        'capacity': 10000,
        'name': 'Blockade Runner'
    },
    'deep_space_transport': {
        'capacity': 60000,
        'name': 'Deep Space Transport'
    },
    'freighter': {
        'capacity': 1000000,
        'name': 'Freighter'
    },
    'jump_freighter': {
        'capacity': 350000,
        'name': 'Jump Freighter'
    },
}
