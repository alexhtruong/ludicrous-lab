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


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    """
    Delivery of potions requested after plan. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    # NOTE we are receiving bottles in exchange for liquid
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    
    # potion_quantities = {red_potions: #, blue_potions: #, ...}
    potion_quantities = {col: 0 for col in POTION_COLUMNS}
    # ml_used = {red_ml: #, blue_ml: #, ...}
    ml_used = {ml: 0 for ml in ML_COLUMNS}
    for delivered_potion in potions_delivered:
        for potion_name, potion_type in POTION_TYPES.items():
            converted_potion_type = [color * 100 for color in potion_type]
            if delivered_potion.potion_type == converted_potion_type:
                potion_quantities[potion_name] = delivered_potion.quantity
        
        for i, color_percent in enumerate(delivered_potion.potion_type):
            color_ml = ML_COLUMNS[i]  # gets 'red_ml', 'green_ml', etc.
            ml_used[color_ml] += color_percent * delivered_potion.quantity
    print(f"post_deliver_bottles potion_quantities: {potion_quantities}")
    print(f"post_deliver_bottles ml_used: {ml_used}")
    with db.engine.begin() as connection:
        # subtracting ml_used 
        sql = f"""
            UPDATE global_inventory SET
            red_ml = red_ml - :red_ml,
            green_ml = green_ml - :green_ml,
            blue_ml = blue_ml - :blue_ml,
            dark_ml = dark_ml - :dark_ml
        """
        params = {col: ml_used[col] for col in ML_COLUMNS}
        connection.execute(
            sqlalchemy.text(sql), [params]
        )

        # updating potions
        for potion_name, quantity in potion_quantities.items():
            if quantity > 0:
                # upsert
                sql = f"""
                    INSERT INTO potions (sku, name, quantity, red_ml, green_ml, blue_ml, dark_ml)
                    VALUES (:sku, :name, :add_quantity, :red_ml, :green_ml, :blue_ml, :dark_ml)
                    ON CONFLICT (sku) DO UPDATE
                    SET quantity = potions.quantity + :add_quantity
                """
                potion_type = POTION_TYPES[potion_name] # [0.5, 0, 0.5, 0]... etc
                name = potion_name.replace("_potions", "").replace("_", " ")  # e.g. "red_potions" -> "red potion"
                params = {
                    "sku": f"{potion_name.upper()}_0",
                    "name" : name,
                    "add_quantity": quantity,
                    "red_ml": potion_type[0] * 100,
                    "green_ml": potion_type[1] * 100,
                    "blue_ml": potion_type[2] * 100,
                    "dark_ml": potion_type[3] * 100,
                }
                print(f"updating potions in db: {params}")
                connection.execute(
                    sqlalchemy.text(sql), [params]
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

    for potion_name, recipe in POTION_TYPES.items():
        potion_type = [color * 100 for color in recipe]
        plans.append(
            PotionMixes(
                potion_type=potion_type,
                quantity=max_per_type,
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
                SELECT red_ml, green_ml, blue_ml, dark_ml
                FROM global_inventory
                """
            )
        ).one()
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml

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
        maximum_potion_capacity=50,
        current_potion_inventory=inventory,
    )


if __name__ == "__main__":
    print(get_bottle_plan())
