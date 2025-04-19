from src.api.barrels import (
    calculate_barrel_summary,
    create_barrel_plan,
    Barrel,
    BarrelOrder,
)
from src.api.bottler import post_deliver_bottles, PotionMixes
from typing import List


def test_barrel_delivery() -> None:
    delivery: List[Barrel] = [
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_GREEN_BARREL",
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0, 0],
            price=150,
            quantity=5,
        ),
    ]

    delivery_summary = calculate_barrel_summary(delivery)

    assert delivery_summary.gold_paid == 1750


def test_buy_small_red_barrel_plan() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_GREEN_BARREL",
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0, 0],
            price=150,
            quantity=5,
        ),
        Barrel(
            sku="SMALL_BLUE_BARREL",
            ml_per_barrel=1000,
            potion_type=[0, 0, 1.0, 0],
            price=500,
            quantity=2,
        ),
    ]

    gold = 100
    max_barrel_capacity = 10000
    current_red_ml = 0
    current_green_ml = 1000
    current_blue_ml = 1000
    current_dark_ml = 1000

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        current_dark_ml,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0  # Ensure at least one order is generated
    assert barrel_orders[0].sku == "SMALL_RED_BARREL"  # Placeholder expected output
    assert barrel_orders[0].quantity == 1  # Placeholder quantity assertion

def test2_buy_small_red_barrel_plan() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=500,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_GREEN_BARREL",
            ml_per_barrel=500,
            potion_type=[0, 1.0, 0, 0],
            price=100,
            quantity=5,
        ),
        Barrel(
            sku="SMALL_BLUE_BARREL",
            ml_per_barrel=500,
            potion_type=[0, 0, 1.0, 0],
            price=120,
            quantity=2,
        ),
    ]

    gold = 500
    max_barrel_capacity = 10000
    current_red_ml = 0
    current_green_ml = 1000
    current_blue_ml = 1000
    current_dark_ml = 1000

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        current_dark_ml,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0  # Ensure at least one order is generated
    assert barrel_orders[0].sku == "SMALL_RED_BARREL"  # Placeholder expected output
    assert barrel_orders[0].quantity == 1  # Placeholder quantity assertion


def test_cant_afford_barrel_plan() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=1000,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_GREEN_BARREL",
            ml_per_barrel=1000,
            potion_type=[0, 1.0, 0, 0],
            price=150,
            quantity=5,
        ),
        Barrel(
            sku="SMALL_BLUE_BARREL",
            ml_per_barrel=1000,
            potion_type=[0, 0, 1.0, 0],
            price=500,
            quantity=2,
        ),
    ]

    gold = 50
    max_barrel_capacity = 10000
    current_red_ml = 0
    current_green_ml = 1000
    current_blue_ml = 1000
    current_dark_ml = 1000

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        current_dark_ml,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) == 0  # Ensure at least one order is generated

def test_barrel_options() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(
            sku="LARGE_RED_BARREL",
            ml_per_barrel=10000,
            potion_type=[1.0, 0, 0, 0],
            price=500,
            quantity=5,
        ),
        Barrel(
            sku="MEDIUM_RED_BARREL",
            ml_per_barrel=2500,
            potion_type=[1.0, 0, 0, 0],
            price=250,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_RED_BARREL",
            ml_per_barrel=500,
            potion_type=[1.0, 0, 0, 0],
            price=100,
            quantity=20,
        ),
        Barrel(
            sku="LARGE_GREEN_BARREL",
            ml_per_barrel=10000,
            potion_type=[0, 1.0, 0, 0],
            price=400,
            quantity=5,
        ),
        Barrel(
            sku="MEDIUM_GREEN_BARREL",
            ml_per_barrel=2500,
            potion_type=[0, 1.0, 0, 0],
            price=250,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_GREEN_BARREL",
            ml_per_barrel=500,
            potion_type=[0, 1.0, 0, 0],
            price=100,
            quantity=20,
        ),
        Barrel(
            sku="LARGE_BLUE_BARREL",
            ml_per_barrel=10000,
            potion_type=[0, 0, 1.0, 0],
            price=600,
            quantity=5,
        ),
        Barrel(
            sku="MEDIUM_BLUE_BARREL",
            ml_per_barrel=2500,
            potion_type=[0, 0, 1.0, 0],
            price=300,
            quantity=10,
        ),
        Barrel(
            sku="SMALL_BLUE_BARREL",
            ml_per_barrel=500,
            potion_type=[0, 0, 1.0, 0],
            price=120,
            quantity=20,
        ),
        Barrel(
            sku="LARGE_YELLOW_BARREL",
            ml_per_barrel=5000,  
            potion_type=[0.5, 0.5, 0, 0],  
            price=1000,
            quantity=3,
        ),
        Barrel(
            sku="LARGE_DARK_BARREL",
            ml_per_barrel=10000,
            potion_type=[0, 0, 0, 1.0],
            price=750,
            quantity=2,
        ),
    ]

    gold = 1000
    max_barrel_capacity = 20000
    current_red_ml = 0
    current_green_ml = 0
    current_blue_ml = 0
    current_dark_ml = 0

    barrel_orders = create_barrel_plan(
        gold,
        max_barrel_capacity,
        current_red_ml,
        current_green_ml,
        current_blue_ml,
        current_dark_ml,
        wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0
    assert barrel_orders[0].sku in ["LARGE_GREEN_BARREL", "MEDIUM_GREEN_BARREL"]
    assert barrel_orders[0].quantity == 1

def test_barrel_options_low_red() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(sku="LARGE_RED_BARREL", ml_per_barrel=10000, potion_type=[1.0, 0, 0, 0], price=500, quantity=5),
        Barrel(sku="MEDIUM_RED_BARREL", ml_per_barrel=2500, potion_type=[1.0, 0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_RED_BARREL", ml_per_barrel=500, potion_type=[1.0, 0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_GREEN_BARREL", ml_per_barrel=10000, potion_type=[0, 1.0, 0, 0], price=400, quantity=5),
        Barrel(sku="MEDIUM_GREEN_BARREL", ml_per_barrel=2500, potion_type=[0, 1.0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_GREEN_BARREL", ml_per_barrel=500, potion_type=[0, 1.0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_BLUE_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 1.0, 0], price=600, quantity=5),
        Barrel(sku="MEDIUM_BLUE_BARREL", ml_per_barrel=2500, potion_type=[0, 0, 1.0, 0], price=300, quantity=10),
        Barrel(sku="SMALL_BLUE_BARREL", ml_per_barrel=500, potion_type=[0, 0, 1.0, 0], price=120, quantity=20),
        Barrel(sku="LARGE_YELLOW_BARREL", ml_per_barrel=5000, potion_type=[0.5, 0.5, 0, 0], price=1000, quantity=3),
        Barrel(sku="LARGE_DARK_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 0, 1.0], price=750, quantity=2),
    ]

    gold = 1000
    max_barrel_capacity = 20000
    current_red_ml = 100  # Very low red
    current_green_ml = 5000  # Good amount of green
    current_blue_ml = 5000  # Good amount of blue
    current_dark_ml = 5000  # Good amount of dark

    barrel_orders = create_barrel_plan(
        gold, max_barrel_capacity, current_red_ml, current_green_ml, 
        current_blue_ml, current_dark_ml, wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0
    # Should choose LARGE_RED_BARREL (20 ml/gold) since red is low
    assert barrel_orders[0].sku == "LARGE_RED_BARREL"
    assert barrel_orders[0].quantity == 1

def test_barrel_options_low_blue() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(sku="LARGE_RED_BARREL", ml_per_barrel=10000, potion_type=[1.0, 0, 0, 0], price=500, quantity=5),
        Barrel(sku="MEDIUM_RED_BARREL", ml_per_barrel=2500, potion_type=[1.0, 0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_RED_BARREL", ml_per_barrel=500, potion_type=[1.0, 0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_GREEN_BARREL", ml_per_barrel=10000, potion_type=[0, 1.0, 0, 0], price=400, quantity=5),
        Barrel(sku="MEDIUM_GREEN_BARREL", ml_per_barrel=2500, potion_type=[0, 1.0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_GREEN_BARREL", ml_per_barrel=500, potion_type=[0, 1.0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_BLUE_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 1.0, 0], price=600, quantity=5),
        Barrel(sku="MEDIUM_BLUE_BARREL", ml_per_barrel=2500, potion_type=[0, 0, 1.0, 0], price=300, quantity=10),
        Barrel(sku="SMALL_BLUE_BARREL", ml_per_barrel=500, potion_type=[0, 0, 1.0, 0], price=120, quantity=20),
        Barrel(sku="LARGE_YELLOW_BARREL", ml_per_barrel=5000, potion_type=[0.5, 0.5, 0, 0], price=1000, quantity=3),
        Barrel(sku="LARGE_DARK_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 0, 1.0], price=750, quantity=2),
    ]

    gold = 1000
    max_barrel_capacity = 20000
    current_red_ml = 5000  
    current_green_ml = 5000  
    current_blue_ml = 100
    current_dark_ml = 5000  

    barrel_orders = create_barrel_plan(
        gold, max_barrel_capacity, current_red_ml, current_green_ml, 
        current_blue_ml, current_dark_ml, wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0
    assert barrel_orders[0].sku == "LARGE_BLUE_BARREL"
    assert barrel_orders[0].quantity == 1

# def test_barrel_options_low_red_and_green() -> None:
#     wholesale_catalog: List[Barrel] = [
#         # Red barrels
#         Barrel(sku="LARGE_RED_BARREL", ml_per_barrel=10000, potion_type=[1.0, 0, 0, 0], price=500, quantity=5),
#         Barrel(sku="MEDIUM_RED_BARREL", ml_per_barrel=2500, potion_type=[1.0, 0, 0, 0], price=250, quantity=10),
#         Barrel(sku="SMALL_RED_BARREL", ml_per_barrel=500, potion_type=[1.0, 0, 0, 0], price=100, quantity=20),
#         # Green barrels
#         Barrel(sku="LARGE_GREEN_BARREL", ml_per_barrel=10000, potion_type=[0, 1.0, 0, 0], price=400, quantity=5),
#         Barrel(sku="MEDIUM_GREEN_BARREL", ml_per_barrel=2500, potion_type=[0, 1.0, 0, 0], price=250, quantity=10),
#         Barrel(sku="SMALL_GREEN_BARREL", ml_per_barrel=500, potion_type=[0, 1.0, 0, 0], price=100, quantity=20),
#         # Blue barrels
#         Barrel(sku="LARGE_BLUE_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 1.0, 0], price=600, quantity=5),
#         Barrel(sku="MEDIUM_BLUE_BARREL", ml_per_barrel=2500, potion_type=[0, 0, 1.0, 0], price=300, quantity=10),
#         Barrel(sku="SMALL_BLUE_BARREL", ml_per_barrel=500, potion_type=[0, 0, 1.0, 0], price=120, quantity=20),
#         # Mixed barrel
#         Barrel(sku="LARGE_YELLOW_BARREL", ml_per_barrel=5000, potion_type=[0.5, 0.5, 0, 0], price=1000, quantity=3),
#         # Dark barrel
#         Barrel(sku="LARGE_DARK_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 0, 1.0], price=750, quantity=2),
#     ]

#     gold = 1000
#     max_barrel_capacity = 20000
#     current_red_ml = 100  # Very low red
#     current_green_ml = 100  # Very low green
#     current_blue_ml = 5000  # Good amount of blue
#     current_dark_ml = 5000  # Good amount of dark

#     barrel_orders = create_barrel_plan(
#         gold, max_barrel_capacity, current_red_ml, current_green_ml, 
#         current_blue_ml, current_dark_ml, wholesale_catalog,
#     )

#     assert isinstance(barrel_orders, list)
#     assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
#     assert len(barrel_orders) > 0
#     # Should choose LARGE_YELLOW_BARREL since both red and green are low (5 ml/gold but fills both needs)
#     assert barrel_orders[0].sku == "LARGE_YELLOW_BARREL"
#     assert barrel_orders[0].quantity == 1

def test_barrel_options_low_dark() -> None:
    wholesale_catalog: List[Barrel] = [
        Barrel(sku="LARGE_RED_BARREL", ml_per_barrel=10000, potion_type=[1.0, 0, 0, 0], price=500, quantity=5),
        Barrel(sku="MEDIUM_RED_BARREL", ml_per_barrel=2500, potion_type=[1.0, 0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_RED_BARREL", ml_per_barrel=500, potion_type=[1.0, 0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_GREEN_BARREL", ml_per_barrel=10000, potion_type=[0, 1.0, 0, 0], price=400, quantity=5),
        Barrel(sku="MEDIUM_GREEN_BARREL", ml_per_barrel=2500, potion_type=[0, 1.0, 0, 0], price=250, quantity=10),
        Barrel(sku="SMALL_GREEN_BARREL", ml_per_barrel=500, potion_type=[0, 1.0, 0, 0], price=100, quantity=20),
        Barrel(sku="LARGE_BLUE_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 1.0, 0], price=600, quantity=5),
        Barrel(sku="MEDIUM_BLUE_BARREL", ml_per_barrel=2500, potion_type=[0, 0, 1.0, 0], price=300, quantity=10),
        Barrel(sku="SMALL_BLUE_BARREL", ml_per_barrel=500, potion_type=[0, 0, 1.0, 0], price=120, quantity=20),
        Barrel(sku="LARGE_YELLOW_BARREL", ml_per_barrel=5000, potion_type=[0.5, 0.5, 0, 0], price=1000, quantity=3),
        Barrel(sku="LARGE_DARK_BARREL", ml_per_barrel=10000, potion_type=[0, 0, 0, 1.0], price=750, quantity=2),
    ]

    gold = 1000
    max_barrel_capacity = 20000
    current_red_ml = 5000  
    current_green_ml = 5000  
    current_blue_ml = 5000  
    current_dark_ml = 100  

    barrel_orders = create_barrel_plan(
        gold, max_barrel_capacity, current_red_ml, current_green_ml, 
        current_blue_ml, current_dark_ml, wholesale_catalog,
    )

    assert isinstance(barrel_orders, list)
    assert all(isinstance(order, BarrelOrder) for order in barrel_orders)
    assert len(barrel_orders) > 0
    # Should choose LARGE_DARK_BARREL (~13.3 ml/gold) since dark is low
    assert barrel_orders[0].sku == "LARGE_DARK_BARREL"
    assert barrel_orders[0].quantity == 1

# def test_barrel_options_value_vs_need() -> None:
#     wholesale_catalog: List[Barrel] = [
#         # High value but single color
#         Barrel(
#             sku="LARGE_GREEN_BARREL",
#             ml_per_barrel=10000,  # 25 ml/gold
#             potion_type=[0, 1.0, 0, 0],
#             price=400,
#             quantity=5,
#         ),
#         # Lower value but fills multiple needs
#         Barrel(
#             sku="LARGE_YELLOW_BARREL",
#             ml_per_barrel=5000,  # 5 ml/gold
#             potion_type=[0.5, 0.5, 0, 0],
#             price=1000,
#             quantity=3,
#         ),
#     ]

#     gold = 1000
#     max_barrel_capacity = 20000
#     current_red_ml = 100  # Very low red
#     current_green_ml = 100  # Very low green
#     current_blue_ml = 5000  # Good amount
#     current_dark_ml = 5000  # Good amount

#     barrel_orders = create_barrel_plan(
#         gold, max_barrel_capacity, current_red_ml, current_green_ml,
#         current_blue_ml, current_dark_ml, wholesale_catalog,
#     )

#     assert isinstance(barrel_orders, list)
#     assert len(barrel_orders) > 0
#     # Should choose YELLOW despite lower ml/gold because it fills multiple needs
#     assert barrel_orders[0].sku == "LARGE_YELLOW_BARREL"
#     assert barrel_orders[0].quantity == 1