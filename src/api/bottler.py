from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
from src.api import auth
from src import database as db
import sqlalchemy
from src.api.potion_types import POTION_TYPES, POTION_COLUMNS, ML_COLUMNS

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)


class PotionMixes(BaseModel):
    potion_type: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d]",
    )
    quantity: int = Field(
        ..., ge=1, le=10000, description="Quantity must be between 1 and 10,000"
    )

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[int]) -> List[int]:
        if sum(potion_type) != 100:
            raise ValueError("Sum of potion_type values must be exactly 100")
        return potion_type

def calculate_liquid_used(ml_used: dict[str, int], potion: PotionMixes):
    red_used = potion.potion_type[0] * potion.quantity
    green_used = potion.potion_type[1] * potion.quantity
    blue_used = potion.potion_type[2] * potion.quantity
    dark_used = potion.potion_type[3] * potion.quantity
    ml_used["red_ml"] -= red_used
    ml_used["green_ml"] -= green_used
    ml_used["blue_ml"] -= blue_used
    ml_used["dark_ml"] -= dark_used

@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    """
    Delivery of potions requested after plan. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    # NOTE we are receiving bottles in exchange for liquid
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    
    # update potions_ledger, potions table, liquid_ledger, and liquids in global_inventory
    with db.engine.begin() as connection:
        existing_order = connection.execute(
            sqlalchemy.text(
                """
                SELECT 1 
                FROM (
                    SELECT order_id FROM potion_ledger WHERE order_id = :order_id
                ) AS combined_ledgers
                """
            ),
            {
                "order_id": order_id,
            }
        ).first()

        if existing_order:
            print("ORDER ALREADY EXISTS IN POTION LEDGER")
            return
        
        ml_used = {"red_ml": 0, "green_ml": 0, "blue_ml": 0, "dark_ml": 0}
        line_item_id = 1
        for potion in potions_delivered:
            calculate_liquid_used(ml_used, potion)

            sku = connection.execute(
                sqlalchemy.text(
                    """
                    UPDATE potions SET
                    quantity = quantity + :delivered_quantity
                    WHERE red_ml = :red_ml AND green_ml = :green_ml AND blue_ml = :blue_ml AND dark_ml = :dark_ml
                    RETURNING sku
                    """
                ),
                {
                    "delivered_quantity": potion.quantity,
                    "red_ml": potion.potion_type[0],
                    "green_ml": potion.potion_type[1],
                    "blue_ml": potion.potion_type[2],
                    "dark_ml": potion.potion_type[3],
                }
            ).scalar_one()

            # insert into potions_ledger
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO potions_ledger
                    (order_id, line_item_id, sku, quantity_delta, transaction_type)
                    VALUES (:order_id, :sku, :quantity_delta, :transaction_type)
                    """
                ),
                {
                    "order_id": order_id,
                    "line_item_id": line_item_id,
                    "sku": sku,
                    "quantity_delta": potion.quantity,
                    "transaction_type": "POTION_DELIVERY"
                }
            )
            line_item_id += 1
        
        print(f"ml_used: {ml_used}")
        # insert into liquid_ledger
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO liquid_ledger
                (order_id, red_ml_delta, green_ml_delta, blue_ml_delta, dark_ml_delta, transaction_type)
                VALUES (:order_id, :red_ml_delta, :green_ml_delta, :blue_ml_delta, :dark_ml_delta, :transaction_type)
                """
            ),
            {
                "order_id": order_id,
                "red_ml_delta": ml_used["red_ml"],
                "green_ml_delta": ml_used["green_ml"],
                "blue_ml_delta": ml_used["blue_ml"],
                "dark_ml_delta": ml_used["dark_ml"],
                "transaction_type": "POTION_DELIVERY",
            }
        )

def create_bottle_plan(
    red_ml: int,
    green_ml: int,
    blue_ml: int,
    dark_ml: int,
    maximum_potion_capacity: int,
    current_potion_inventory: List[PotionMixes],
) -> List[PotionMixes]:
    """
    Creates a plan for bottling potions based on available liquids,
    ensuring an even distribution for variety.
    """
    plans = []
    current_potion_count = sum([potion.quantity for potion in current_potion_inventory])
    remaining_potion_count = maximum_potion_capacity - current_potion_count

    if remaining_potion_count <= 0:
        print(f"max potion capacity reached - current total: {current_potion_count}, Max: {maximum_potion_capacity}")
        return []
    
    # Evenly distribute 50% of remaining capacity among potion types
    max_per_type = max(1, remaining_potion_count // (6 * 2))

    available_liquids = {
        "red_ml": red_ml,
        "green_ml": green_ml,
        "blue_ml": blue_ml,
        "dark_ml": dark_ml
    }

    for potion_name, recipe in POTION_TYPES.items():
        # calculate how many potions we can make with current inventory
        max_possible = calculate_max_potions(available_liquids, recipe)
        if max_possible <= 0:
            print(f"Skipping {potion_name} - not enough ingredients")
            continue

        quantity = min(max_possible, max_per_type)
        
        # subtract the used liquids from available inventory
        for i, amount in enumerate(recipe):
            if amount > 0:
                color_ml = ML_COLUMNS[i]
                used_amount = amount * 100 * quantity
                available_liquids[color_ml] -= used_amount

        potion_type = [color * 100 for color in recipe]
        plans.append(
            PotionMixes(
                potion_type=potion_type,
                quantity=quantity,
            )
        )
    
    print(f"create_bottle_plan PLANS: {plans}")
    return plans

def calculate_max_potions(available: dict, recipe: List[float]) -> int:
    """Calculate maximum potions possible with given recipe and liquids."""
    possible_quantities = []
    # (0, [0.5, 0.5, 0, 0])...
    for i, amount in enumerate(recipe):
        if amount > 0: 
            color_ml = ML_COLUMNS[i] # "red_ml, green_ml, etc"
            possible = int(available[color_ml] / (amount * 100))
            possible_quantities.append(possible)
    
    if possible_quantities:
        return min(possible_quantities)
    
    return 0

@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    """
    Gets the plan for bottling potions.
    Each bottle has a quantity of what proportion of red, green, blue, and dark potions to add.
    Colors are expressed in integers from 0 to 100 that must sum up to exactly 100.
    """
    inventory = []
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    (SELECT max_potion_capacity FROM global_inventory),
                    SUM(red_ml_delta) as red_ml,
                    SUM(green_ml_delta) as green_ml,
                    SUM(blue_ml_delta) as blue_ml,
                    SUM(dark_ml_delta) as dark_ml
                FROM liquid_ledger
                """
            )
        ).one()
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml
        max_potion_capacity = row.max_potion_capacity

        # get all current potions in the form of [(sku, quantity, ...), (sku, quantity, ...)]
        potions = connection.execute(
            sqlalchemy.text(
                """
                    SELECT sku, quantity, red_ml, green_ml, blue_ml, dark_ml
                    FROM potions
                    WHERE is_active = TRUE AND quantity > 0
                """
            )
        ).all()
        for potion in potions:
            quantity = potion.quantity
            r = potion[2]
            g = potion[3]
            b = potion[4]
            d = potion[5]
            inventory.append(
                PotionMixes(
                    potion_type=[r, g, b, d],
                    quantity=quantity
                )
            )
    print(f"get_bottle_plan inventory: {inventory}")
    return create_bottle_plan(
        red_ml=red_ml,
        green_ml=green_ml,
        blue_ml=blue_ml,
        dark_ml=dark_ml,
        maximum_potion_capacity=max_potion_capacity,
        current_potion_inventory=inventory,
    )


if __name__ == "__main__":
    print(get_bottle_plan())
