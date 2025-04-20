from typing import List, Dict

#TODO: potion types should not be hard coded, data-driven

POTION_TYPES: Dict[str, List[float]] = {
    "red_potions": [1.0, 0.0, 0.0, 0.0],
    "green_potions": [0.0, 1.0, 0.0, 0.0],
    "blue_potions": [0.0, 0.0, 1.0, 0.0],
    "dark_potions": [0.0, 0.0, 0.0, 1.0],
    "purple_potions": [0.7, 0.0, 0.3, 0.0],  # red + blue
    "turquoise_potions": [0.0, 0.7, 0.3, 0.0],  # green + blue
}
    # "shadow_potions": [0.3, 0.0, 0.3, 0.4],  # red + blue + dark
    # "amber_potions": [0.6, 0.4, 0.0, 0.0],  # red + green
    # "emerald_potions": [0.0, 0.8, 0.0, 0.2],  # green + dark
    # "midnight_potions": [0.0, 0.0, 0.7, 0.3],  # blue + dark
    # "rainbow_potions": [0.25, 0.25, 0.25, 0.25] 


ML_COLUMNS = ["red_ml", "green_ml", "blue_ml", "dark_ml"]
POTION_COLUMNS = list(POTION_TYPES.keys())