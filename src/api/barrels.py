from dataclasses import dataclass
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import random
import sqlalchemy
from src.api import auth
from src import database as db
from src.api.potion_types import POTION_TYPES, ML_COLUMNS, POTION_COLUMNS

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int = Field(gt=0, description="Must be greater than 0")
    potion_type: List[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d] that sum to 1.0",
    )
    price: int = Field(ge=0, description="Price must be non-negative")
    quantity: int = Field(ge=0, description="Quantity must be non-negative")

    @field_validator("potion_type")
    @classmethod
    def validate_potion_type(cls, potion_type: List[float]) -> List[float]:
        if len(potion_type) != 4:
            raise ValueError("potion_type must have exactly 4 elements: [r, g, b, d]")
        if not abs(sum(potion_type) - 1.0) < 1e-6:
            raise ValueError("Sum of potion_type values must be exactly 1.0")
        return potion_type


class BarrelOrder(BaseModel):
    sku: str
    quantity: int = Field(gt=0, description="Quantity must be greater than 0")


@dataclass
class BarrelSummary:
    gold_paid: int


def calculate_barrel_summary(barrels: List[Barrel]) -> BarrelSummary:
    return BarrelSummary(gold_paid=sum(b.price * b.quantity for b in barrels))


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    """
    Processes barrels delivered based on the provided order_id. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    # NOTE we are receiving barrels of liquids in exchange for gold
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    delivery = calculate_barrel_summary(barrels_delivered)
    ml_added = {col: 0 for col in ML_COLUMNS}
    # ML_COLUMNS: red, green, blue, dark
    for i, color_name in enumerate(ML_COLUMNS):
        total = 0
        # add all barrels by one color at a time
        for b in barrels_delivered:
            amount = b.ml_per_barrel * b.quantity * b.potion_type[i]
            total += amount
        ml_added[color_name] = total

    with db.engine.begin() as connection:
        sql = """
            UPDATE global_inventory SET
            gold = gold - :gold_paid,
            red_ml = red_ml + :red_ml,
            green_ml = green_ml + :green_ml,
            blue_ml = blue_ml + :blue_ml,
            dark_ml = dark_ml + :dark_ml
        """
        params = {"gold_paid": delivery.gold_paid}
        # {red_ml: #, green_ml: #, ...}
        params.update(ml_added)
        print(f"post_deliver_barrels ml added: {ml_added}")
        connection.execute(
            sqlalchemy.text(sql), [params]
        )


def create_barrel_plan(
    gold: int,
    max_barrel_capacity: int,
    current_red_ml: int,
    current_green_ml: int,
    current_blue_ml: int,
    current_dark_ml: int,
    wholesale_catalog: List[Barrel],
) -> List[BarrelOrder]:
    print(
        f"gold: {gold}, max_barrel_capacity: {max_barrel_capacity}, current_red_ml: {current_red_ml}, current_green_ml: {current_green_ml}, current_blue_ml: {current_blue_ml}, current_dark_ml: {current_dark_ml}, wholesale_catalog: {wholesale_catalog}"
    )

    def would_exceed_barrel_capacity(barrel: Barrel) -> bool:
        total_in_inventory = current_red_ml + current_green_ml + current_blue_ml + current_dark_ml
        new_amount = total_in_inventory + (barrel.ml_per_barrel) # TODO: configure for multiple quantity barrels  
        if new_amount > max_barrel_capacity:
            print(f"skipping - would exceed barrel capacity")
            return True
        return False
    
    # the goal of this function is to help spread out the purchasing of barrels such that we don't overstock on one certain liquid
    def calculate_balance_score(barrel: Barrel) -> float:
        current_levels = {
            "red": current_red_ml,
            "green": current_green_ml,
            "blue": current_blue_ml,
            "dark": current_dark_ml
        }
        avg_level = sum(current_levels.values()) / 4

        balance_improvement = 0
        for i, (color, amount) in enumerate(current_levels.items()):
            # how far is this color from the average levels of the current stock?
            deficit = avg_level - amount
            if deficit > 0:
                # if the color is below the average, then check how much it helps
                added_amount = barrel.ml_per_barrel * barrel.potion_type[i]
                if added_amount > 0:
                    # score higher if barrel adds to the colors we need
                    # we take the min here because:
                    # prevents overweighting: a barrel that provides 500ml when we only need 100ml isn't 5 times better than a barrel that provides exactly what we need
                    # normalization: keeps scores between 0 and 1 for each color, making them easier to compare and combine
                    balance_improvement += min(added_amount / deficit, 1.0)

        return balance_improvement

    with db.engine.begin() as connection:
        potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT sku, name, quantity, red_ml, green_ml, blue_ml, dark_ml
                FROM potions
                WHERE is_active = True and quantity < 5
                """
            )
        ).fetchall()
        print(f"BARREL PLAN POTIONS: {potions}")
        if not potions and current_red_ml >= 500 and current_green_ml >= 500 and current_blue_ml >= 500 and current_dark_ml >= 500:
            return []  # we have enough of everything


        valid_barrels = []
        for barrel in wholesale_catalog:
            print(f"evaluating barrel {barrel.sku}: price={barrel.price}, gold={gold}")
            if barrel.price > gold:
                print(f"skipping - too expensive")
                continue
            if barrel.sku.startswith('JUNK'):
                print(f"skipping - junk barrel")
                continue
            if would_exceed_barrel_capacity(barrel):
                continue
            value_score = barrel.ml_per_barrel / barrel.price
            balance_score = calculate_balance_score(barrel)
            total_score = value_score * balance_score
            print(f"total_score: {total_score}, value_score: {value_score}, balance_score: {balance_score}")
            if total_score > 0:
                valid_barrels.append((barrel, total_score))

        if not valid_barrels:
            # if no valid barrels based on scoring, try random selection from affordable ones
            affordable_barrels = [
                barrel for barrel in wholesale_catalog 
                if barrel.price <= gold 
                and not barrel.sku.startswith('JUNK')
                and not would_exceed_barrel_capacity(barrel)
            ]
            if affordable_barrels:
                random_barrel = random.choice(affordable_barrels)
                print(f"no optimal barrels found. randomly selected: {random_barrel.sku}")
                return [BarrelOrder(sku=random_barrel.sku, quantity=1)]
            return []
        print(valid_barrels)

        best_barrel, best_score = max(valid_barrels, key=lambda x: x[1]) # returns (Barrel, 0.8)
        print("BEST BARREL SKU: " + best_barrel.sku)
        return [
            BarrelOrder(
                sku=best_barrel.sku,
                quantity=1 # TODO: configure but for now we can just buy
            )
        ]

@router.post("/plan", response_model=List[BarrelOrder])
def get_wholesale_purchase_plan(wholesale_catalog: List[Barrel]):
    """
    Gets the plan for purchasing wholesale barrels. The call passes in a catalog of available barrels
    and the shop returns back which barrels they'd like to purchase and how many.
    """
    print(f"barrel catalog: {wholesale_catalog}")

    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, red_ml, green_ml, blue_ml, dark_ml, max_barrel_capacity
                FROM global_inventory
                """
            )
        ).one()
        
        gold = row.gold
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml
        max_barrel_capacity = row.max_barrel_capacity

    return create_barrel_plan(
        gold=gold,
        max_barrel_capacity=max_barrel_capacity,
        current_red_ml=red_ml,
        current_green_ml=green_ml,
        current_blue_ml=blue_ml,
        current_dark_ml=dark_ml,
        wholesale_catalog=wholesale_catalog,
    )
