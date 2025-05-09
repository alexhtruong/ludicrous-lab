from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


class InventoryAudit(BaseModel):
    number_of_potions: int
    ml_in_barrels: int
    gold: int



class CapacityPlan(BaseModel):
    potion_capacity: int = Field(
        ge=0, le=10, description="Potion capacity units, max 10"
    )
    ml_capacity: int = Field(ge=0, le=10, description="ML capacity units, max 10")


@router.get("/audit", response_model=InventoryAudit)
def get_inventory():
    """
    Returns an audit of the current inventory. Any discrepancies between
    what is reported here and my source of truth will be posted
    as errors on potion exchange.
    """

    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text(
            """
            SELECT 
                (SELECT SUM(gold_delta) FROM gold_ledger) as gold,
                (SELECT SUM(quantity_delta) FROM potion_ledger) as number_of_potions,
                (SELECT 
                    SUM(red_ml_delta) + SUM(green_ml_delta) + 
                    SUM(blue_ml_delta) + SUM(dark_ml_delta) 
                FROM liquid_ledger) as ml_in_barrels
            """
            )
        ).one()

        gold = result.gold
        number_of_potions = result.number_of_potions
        ml_in_barrels = result.ml_in_barrels

    return InventoryAudit(number_of_potions=number_of_potions, ml_in_barrels=ml_in_barrels, gold=gold)


@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():
    """
    Provides a daily capacity purchase plan.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        inventory = connection.execute(
            sqlalchemy.text(
            """
            SELECT 
                (SELECT SUM(gold_delta) FROM gold_ledger) as gold,
                (SELECT SUM(quantity_delta) FROM potion_ledger) as total_potions_in_inventory,
                (SELECT 
                    SUM(red_ml_delta) + SUM(green_ml_delta) + 
                    SUM(blue_ml_delta) + SUM(dark_ml_delta) 
                FROM liquid_ledger) as ml_in_barrels,
                (SELECT max_potion_capacity FROM global_inventory) as max_potion_capacity,
                (SELECT max_barrel_capacity FROM global_inventory) as max_barrel_capacity
            """
            )
        ).one()
        gold = inventory.gold
        max_potion_capacity = inventory.max_potion_capacity
        max_barrel_capacity = inventory.max_barrel_capacity
        total_liquid_in_inventory = inventory.ml_in_barrels
        total_potions_in_inventory = inventory.total_potions_in_inventory

        if max_potion_capacity <= 300:
            return CapacityPlan(potion_capacity=3, ml_capacity=0)
        
        liquid_utilization = total_liquid_in_inventory / max_barrel_capacity
        potion_utilization = total_potions_in_inventory / max_potion_capacity

        ml_capacity = 0
        potion_capacity = 0
        if gold >= 3000 and liquid_utilization >= 0.8 and potion_utilization >= 0.8:
            ml_capacity = 1
            potion_capacity = 1
        elif gold >= 1000:
            if liquid_utilization > potion_utilization and liquid_utilization >= 0.8:
                ml_capacity = 1
            elif potion_utilization >= 0.65:
                potion_capacity = 1
        print(f"potion_capacity: {potion_capacity}, ml_capacity: {ml_capacity}")
    return CapacityPlan(potion_capacity=potion_capacity, ml_capacity=ml_capacity)


# NOTE: once a day
@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def deliver_capacity_plan(capacity_purchase: CapacityPlan, order_id: int):
    """
    Processes the delivery of the planned capacity purchase. order_id is a
    unique value representing a single delivery; the call is idempotent.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    print(f"capacity delivered: {capacity_purchase} order_id: {order_id}")
    
    potion_capacity_increase = capacity_purchase.potion_capacity * 50
    ml_capacity_increase = capacity_purchase.ml_capacity * 10000
    gold_delta = -(capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000

    with db.engine.begin() as connection:
        existing_order = connection.execute(
            sqlalchemy.text(
                """
                SELECT 1 FROM capacity_order_ledger WHERE :order_id = order_id
                """
            ), 
            {
                "order_id": order_id,
            }
        ).first()

        if existing_order:
            return

        connection.execute(
            sqlalchemy.text(
                """
                WITH capacity_insert AS (
                    INSERT INTO capacity_order_ledger
                    (order_id, potion_capacity_increase, ml_capacity_increase, gold_delta)
                    VALUES (:order_id, :potion_capacity_increase, :ml_capacity_increase, :gold_delta)
                )
                INSERT INTO gold_ledger 
                (order_id, gold_delta, transaction_type)
                VALUES (:order_id, :gold_delta, 'INVENTORY_UPGRADE')
                """
            ), 
            {
                "order_id": order_id,
                "potion_capacity_increase": potion_capacity_increase,
                "ml_capacity_increase": ml_capacity_increase,
                "gold_delta": gold_delta
            }
        )

        print(f"updating capacity in db: potion_capacity_increase: {potion_capacity_increase}, ml_capacity_increase: {ml_capacity_increase}, gold_consumed: {gold_delta}")