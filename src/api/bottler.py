from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
from src.api import auth
from src import database as db
import sqlalchemy

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
    
    # update potions_ledger, liquid_ledger
    with db.engine.begin() as connection:
        existing_order = connection.execute(
            sqlalchemy.text(
                """
                SELECT 1 
                FROM (
                    SELECT order_id FROM potion_ledger WHERE order_id = :order_id AND transaction_type = 'POTION_DELIVERY'
                    UNION
                    SELECT order_id FROM liquid_ledger WHERE order_id = :order_id AND transaction_type = 'POTION_DELIVERY' 
                ) AS combined_ledgers
                """
            ),
            {
                "order_id": order_id,
            }
        ).first()

        if existing_order:
            print("ORDER ALREADY EXISTS IN POTION LEDGER AND/OR LIQUID_LEDGER")
            return
        
        ml_used = {"red_ml": 0, "green_ml": 0, "blue_ml": 0, "dark_ml": 0}
        line_item_id = 1
        for potion in potions_delivered:
            calculate_liquid_used(ml_used, potion)

            # grab corresponding potion sku
            sku = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT sku
                    FROM potions
                    WHERE red_ml = :red_ml 
                    AND green_ml = :green_ml 
                    AND blue_ml = :blue_ml 
                    AND dark_ml = :dark_ml
                    """
                ),
                {
                    "red_ml": potion.potion_type[0],
                    "green_ml": potion.potion_type[1],
                    "blue_ml": potion.potion_type[2],
                    "dark_ml": potion.potion_type[3],
                }
            ).scalar_one()

            # insert into potion_ledger
            connection.execute(
                sqlalchemy.text(
                    """
                    INSERT INTO potion_ledger
                    (order_id, line_item_id, sku, quantity_delta, transaction_type)
                    VALUES (:order_id, :line_item_id, :sku, :quantity_delta, :transaction_type)
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
    plans: List[PotionMixes] = []
    current_potion_count = sum([potion.quantity for potion in current_potion_inventory])
    remaining_potion_count = maximum_potion_capacity - current_potion_count

    if remaining_potion_count <= 0:
        print(f"max potion capacity reached - current total: {current_potion_count}, Max: {maximum_potion_capacity}")
        return []
    
    available_liquids = {
        "red_ml": red_ml,
        "green_ml": green_ml,
        "blue_ml": blue_ml,
        "dark_ml": dark_ml
    }
    
    with db.engine.begin() as connection:
        all_potion_quantities = connection.execute(
            sqlalchemy.text(
                """
                SELECT COALESCE(SUM(pl.quantity_delta), 0) as total_existing
                FROM potions p
                LEFT JOIN potion_ledger pl ON pl.sku = p.sku
                """
            )
        ).scalar()

        active_potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT p.sku, 
                    p.red_ml, 
                    p.green_ml, 
                    p.blue_ml, 
                    p.dark_ml,
                    COALESCE(SUM(pl.quantity_delta), 0) as total_quantity
                FROM potions p
                LEFT JOIN potion_ledger pl ON pl.sku = p.sku
                WHERE p.is_active = true
                GROUP BY p.sku, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml
                """
            )
        ).all()

        if len(active_potions) == 0:
            return []
        
        # evenly divide so that they have a equal max cap
        remaining_space = maximum_potion_capacity - all_potion_quantities
        target_quantity = remaining_space // len(active_potions)
        for potion in active_potions:
            needed_quantity = target_quantity - potion.total_quantity
            if needed_quantity <= 0:
                continue

            required_red = (potion.red_ml / 100) * needed_quantity
            required_green = (potion.green_ml / 100) * needed_quantity
            required_blue = (potion.blue_ml / 100) * needed_quantity
            required_dark = (potion.dark_ml / 100) * needed_quantity

            # check if we have enough liquid
            if (required_red > available_liquids["red_ml"] or
                required_green > available_liquids["green_ml"] or
                required_blue > available_liquids["blue_ml"] or
                required_dark > available_liquids["dark_ml"]):
                
                # calculate max amount possible based on available liquids
                # the minimium will be the limiting factor
                possible_quantity = min(
                    available_liquids["red_ml"] // potion.red_ml if potion.red_ml > 0 else float('inf'),
                    available_liquids["green_ml"] // potion.green_ml if potion.green_ml > 0 else float('inf'),
                    available_liquids["blue_ml"] // potion.blue_ml if potion.blue_ml > 0 else float('inf'),
                    available_liquids["dark_ml"] // potion.dark_ml if potion.dark_ml > 0 else float('inf')
                )
                
                if possible_quantity <= 0:
                    continue
                
                needed_quantity = min(needed_quantity, possible_quantity)

            recipe = [
                potion.red_ml,
                potion.green_ml,
                potion.blue_ml,
                potion.dark_ml
            ]
            
            available_liquids["red_ml"] -= recipe[0] * needed_quantity
            available_liquids["green_ml"] -= recipe[1] * needed_quantity
            available_liquids["blue_ml"] -= recipe[2] * needed_quantity
            available_liquids["dark_ml"] -= recipe[3] * needed_quantity

            plans.append(
                PotionMixes(
                    potion_type=recipe,
                    quantity=needed_quantity
                )
            )
        
        print(f"bottle_plan: {plans}")
        print(f"remaining liquids: {available_liquids}")
        plans_potion_count = sum(potion.quantity for potion in plans)
        if plans_potion_count + current_potion_count > maximum_potion_capacity:
            return []
        return plans

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
                    SELECT 
                        p.sku,
                        COALESCE(SUM(pl.quantity_delta), 0) AS quantity,
                        p.red_ml,
                        p.green_ml, 
                        p.blue_ml, 
                        p.dark_ml
                    FROM potions p
                    LEFT JOIN potion_ledger pl ON p.sku = pl.sku
                    GROUP BY p.sku, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml
                    HAVING COALESCE(SUM(pl.quantity_delta), 0) > 0
                """
            )
        ).all()
        for potion in potions:
            quantity = potion.quantity
            r = potion.red_ml
            g = potion.green_ml
            b = potion.blue_ml
            d = potion.dark_ml
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
