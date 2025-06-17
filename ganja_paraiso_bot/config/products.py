"""
Product definitions for the Ganja Paraiso bot.
"""
from ganja_paraiso_bot.config.emoji import EMOJI

# Product definitions
PRODUCTS = {
    "buds": {
        "name": "Premium Buds",
        "emoji": EMOJI["buds"],
        "description": "High-quality cannabis flowers",
        "min_order": 1,
        "unit": "grams",
        "tag": "buds",
        "requires_strain_selection": True
    },
    "local": {
        "name": "Local (BG)",
        "emoji": EMOJI["local"],
        "description": "Local budget-friendly option",
        "min_order": 10,
        "unit": "grams",
        "tag": "local",
        "price_per_unit": 1000
    },
    "carts": {
        "name": "Carts/Disposables",
        "emoji": EMOJI["carts"],
        "description": "Pre-filled vape cartridges",
        "min_order": 1,
        "unit": "units",
        "tag": "carts",
        "browse_options": ["brand", "weight"]
    },
    "edibles": {
        "name": "Edibles",
        "emoji": EMOJI["edibles"],
        "description": "Cannabis-infused food products",
        "min_order": 1,
        "unit": "packs",
        "tag": "edibs",
        "requires_strain_selection": True
    }
}