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
            red_ml = red_ml - :red_ml,
            green_ml = green_ml - :green_ml,
            blue_ml = blue_ml - :blue_ml,
            dark_ml = dark_ml - :dark_ml
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
        if not potions:
            return []
        
        valid_barrels = []
        for barrel in wholesale_catalog:
            # skip invalid barrels
            if barrel.price > gold or barrel.sku.startswith('JUNK'):
                continue
            value_score = barrel.ml_per_barrel / barrel.price

            # track low colors and their corresponding needs
            low_colors = []
            if current_red_ml < 500:
                low_colors.append((0, "red"))
            if current_green_ml < 500:
                low_colors.append((1, "green"))
            if current_blue_ml < 5000:
                low_colors.append((2, "blue"))
            if current_dark_ml < 500:
                low_colors.append((3, "dark"))
            
            print(f"LOW COLORS: {low_colors}")
            if low_colors:
                # calculate how well this barrel matches our needs
                color_match_score = 0
                for color_index, color_name in low_colors:
                    color_match_score += barrel.potion_type[color_index]
                print(f"COLOR MATCH SCORE: {color_match_score}")
                if color_match_score > 0:
                    valid_barrels.append(
                        (barrel, value_score * color_match_score)
                    )

        if not valid_barrels:
            return []
        
        best_barrel, best_score = max(valid_barrels, key=lambda x: x[1]) # returns (Barrel, 0.8)
        print("BEST BARREL SKU: " + best_barrel.sku)
        return [
            BarrelOrder(
                sku=best_barrel.sku,
                quantity=1 # TODO: configure but for now we can just buy
            )
        ]

# called one per day
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
                SELECT gold, red_ml, green_ml, blue_ml 
                FROM global_inventory
                """
            )
        ).one()

        gold = row.gold
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml

    return create_barrel_plan(
        gold=gold,
        max_barrel_capacity=10000,
        current_red_ml=red_ml,
        current_green_ml=green_ml,
        current_blue_ml=blue_ml,
        current_dark_ml=0,
        wholesale_catalog=wholesale_catalog,
    )
