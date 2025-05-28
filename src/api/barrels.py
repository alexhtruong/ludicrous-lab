from dataclasses import dataclass
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator
from typing import List
import random
import sqlalchemy
from src.api import auth
from src import database as db

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
    red_ml: int
    green_ml: int
    blue_ml: int
    dark_ml: int


def calculate_barrel_summary(barrels: List[Barrel]) -> BarrelSummary:
    red_ml = sum(barrel.ml_per_barrel * barrel.potion_type[0] * barrel.quantity for barrel in barrels)
    green_ml = sum(barrel.ml_per_barrel * barrel.potion_type[1] * barrel.quantity for barrel in barrels)
    blue_ml = sum(barrel.ml_per_barrel * barrel.potion_type[2] * barrel.quantity for barrel in barrels)
    dark_ml = sum(barrel.ml_per_barrel * barrel.potion_type[3] * barrel.quantity for barrel in barrels)
    gold_paid = sum(b.price * b.quantity for b in barrels)

    return BarrelSummary(gold_paid=gold_paid,
                        red_ml=red_ml,
                        blue_ml=blue_ml,
                        green_ml=green_ml,
                        dark_ml=dark_ml)


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_barrels(barrels_delivered: List[Barrel], order_id: int):
    """
    Processes barrels delivered based on the provided order_id. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    # NOTE we are receiving barrels of liquids in exchange for gold
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    summary = calculate_barrel_summary(barrels_delivered)
    with db.engine.begin() as connection:
        # check if order already exists
        existing_order = connection.execute(
            sqlalchemy.text(
                """
                SELECT 1 
                FROM (
                    SELECT order_id FROM liquid_ledger WHERE order_id = :order_id AND transaction_type = 'BARREL_DELIVERY'
                    UNION
                    SELECT order_id FROM gold_ledger WHERE order_id = :order_id AND transaction_type = 'BARREL_PURCHASE'
                ) AS orders
                """
            ),
            {
                "order_id": order_id
            }
        ).first()

        if existing_order:
            return

        # insert into ledger with data
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
                "red_ml_delta": summary.red_ml,
                "green_ml_delta": summary.green_ml,
                "blue_ml_delta": summary.blue_ml,
                "dark_ml_delta": summary.dark_ml,
                "transaction_type": "BARREL_DELIVERY"
            }
        )

        # insert into gold ledger
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO gold_ledger
                (order_id, gold_delta, transaction_type)
                VALUES (:order_id, :gold_delta, :transaction_type)
                """
            ),
            {
                "order_id": order_id,
                "gold_delta": -summary.gold_paid,  # negative because we're paying
                "transaction_type": "BARREL_PURCHASE"
            }
        )

def calculate_max_quantity(barrel: Barrel, gold: int, remaining_capacity: int) -> int:
    max_by_gold = gold // barrel.price
    max_by_capacity = remaining_capacity // barrel.ml_per_barrel
    max_by_availability = barrel.quantity
    return min(max_by_gold, max_by_capacity, max_by_availability)

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
    # Get time-based demand data
    #demand_data = get_time_based_demand()
    #print(demand_data)
    
    current_levels = {
        "red": current_red_ml,
        "green": current_green_ml,
        "blue": current_blue_ml,
        "dark": current_dark_ml
    }
    target_per_liquid = max_barrel_capacity / 4
    dark_preference_multiplier = 1.5
    def compute_deficit():
        return {
            "red": max(0, target_per_liquid - current_levels["red"]),
            "green": max(0, target_per_liquid - current_levels["green"]),
            "blue": max(0, target_per_liquid - current_levels["blue"]),
            "dark": max(0, target_per_liquid * dark_preference_multiplier - current_levels["dark"])
        }

    def calculate_balance_score(barrel: Barrel) -> float:
        deficit = compute_deficit()
        colors = ["red", "green", "blue", "dark"]
        score = 0
        for idx, color in enumerate(colors):
            multiplier = dark_preference_multiplier if color == "dark" else 1.0
            score += barrel.potion_type[idx] * deficit[color] * barrel.ml_per_barrel * multiplier
        return score

    # def would_exceed_barrel_capacity(barrel: Barrel) -> bool:
    #     total_in_inventory = current_red_ml + current_green_ml + current_blue_ml + current_dark_ml
    #     new_amount = total_in_inventory + (barrel.ml_per_barrel) # TODO: configure for multiple quantity barrels  
    #     if new_amount > max_barrel_capacity:
    #         print(f"skipping - would exceed barrel capacity")
    #         return True
    #     return False
    
    remaining_gold = gold
    remaining_capacity = max_barrel_capacity - (current_red_ml + current_green_ml + current_blue_ml + current_dark_ml)
    valid_barrels = []
    affordable_barrels = [
        barrel for barrel in wholesale_catalog 
        if barrel.price <= remaining_gold 
        and not barrel.sku.startswith('JUNK')
    ]
    affordable_barrels = [
        barrel for barrel in wholesale_catalog
        if barrel.price <= remaining_gold
        and barrel.potion_type[3] > 0
    ]

    for barrel in affordable_barrels:
        max_quantity = calculate_max_quantity(barrel, remaining_gold, remaining_capacity)
        if max_quantity == 0:
            continue

        balance_score = calculate_balance_score(barrel)
        total_score = balance_score * max_quantity
        if total_score > 0:
            valid_barrels.append((barrel, total_score, max_quantity))

    if not valid_barrels:
        if affordable_barrels:
            random_barrel = random.choice(affordable_barrels)
            max_quantity = calculate_max_quantity(random_barrel, remaining_gold, remaining_capacity)
            return [BarrelOrder(sku=random_barrel.sku, quantity=max_quantity or 1)]
        return []

    # sort barrels by score in descending order
    valid_barrels.sort(key=lambda x: x[1], reverse=True)
    orders = []
    
    # take top 2 barrels and calculate optimal quantities
    for barrel, score, max_qty in valid_barrels[:2]:
        if remaining_gold >= barrel.price and max_qty > 0:
            # calculate total liquid after this order
            total_liquid = (current_red_ml + current_green_ml + 
                          current_blue_ml + current_dark_ml + 
                          (barrel.ml_per_barrel * max_qty))
            
            # skip if this would exceed capacity
            if total_liquid > max_barrel_capacity:
                print(f"Skipping order - would exceed max capacity of {max_barrel_capacity}")
                continue

            orders.append(BarrelOrder(
                sku=barrel.sku,
                quantity=max_qty
            ))
            remaining_gold -= barrel.price * max_qty
            remaining_capacity -= barrel.ml_per_barrel * max_qty
            
            # update current levels for next iteration
            current_red_ml += barrel.ml_per_barrel * max_qty * barrel.potion_type[0]
            current_green_ml += barrel.ml_per_barrel * max_qty * barrel.potion_type[1]
            current_blue_ml += barrel.ml_per_barrel * max_qty * barrel.potion_type[2]
            current_dark_ml += barrel.ml_per_barrel * max_qty * barrel.potion_type[3]
    return orders

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
                SELECT 
                    (SELECT COALESCE(SUM(gold_delta), 0) FROM gold_ledger) as gold,
                    (SELECT COALESCE(SUM(ml_capacity_increase), 0) FROM capacity_order_ledger) as max_barrel_capacity,
                    COALESCE(SUM(red_ml_delta), 0) as red_ml,
                    COALESCE(SUM(green_ml_delta), 0) as green_ml,
                    COALESCE(SUM(blue_ml_delta), 0) as blue_ml,
                    COALESCE(SUM(dark_ml_delta), 0) as dark_ml
                FROM liquid_ledger
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

def get_time_based_demand() -> dict:
    # analyzes historical sales data to determine demand patterns by time period.
    # returns a score indicating the relative importance of stocking up now.
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
                """
                WITH current_time AS (
                    SELECT day_of_week, hour_of_day
                    FROM time_analytics
                    ORDER BY created_at DESC
                    LIMIT 1
                ),
                next_hours AS (
                    SELECT hour_of_day 
                    FROM time_analytics 
                    WHERE day_of_week = (SELECT day_of_week FROM current_time)
                    AND hour_of_day > (SELECT hour_of_day FROM current_time)
                    UNION
                    SELECT hour_of_day 
                    FROM time_analytics 
                    WHERE day_of_week = CASE 
                        WHEN (SELECT day_of_week FROM current_time) = 'Soulday' THEN 'Edgeday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Edgeday' THEN 'Bloomday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Bloomday' THEN 'Aracanaday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Aracanaday' THEN 'Hearthday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Hearthday' THEN 'Crownday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Crownday' THEN 'Blesseday'
                        WHEN (SELECT day_of_week FROM current_time) = 'Blesseday' THEN 'Soulday'
                    END
                    AND hour_of_day <= (SELECT hour_of_day FROM current_time)
                )
                SELECT 
                    COALESCE(AVG(total_sales), 0) as avg_upcoming_sales,
                    COALESCE(AVG(CASE WHEN total_sales = 0 AND visitor_count > 0 THEN 1 ELSE 0 END), 0) as stockout_risk
                FROM time_analytics ta
                WHERE (ta.day_of_week, ta.hour_of_day) IN (
                    SELECT ct.day_of_week, nh.hour_of_day 
                    FROM current_time ct
                    CROSS JOIN next_hours nh
                )
                """
            )
        ).first()
        
        return {
            'avg_upcoming_sales': float(result.avg_upcoming_sales),
            'stockout_risk': float(result.stockout_risk)
        }
