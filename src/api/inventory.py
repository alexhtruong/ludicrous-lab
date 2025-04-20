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
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, red_ml, green_ml, blue_ml, dark_ml
                FROM global_inventory
                """
            )
        ).one()
        gold = row.gold
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml
        dark_ml = row.dark_ml

        number_of_potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT COALESCE(SUM(quantity), 0)
                from potions
                """
            )
        ).scalar()

        ml_in_barrels = red_ml + green_ml + blue_ml + dark_ml

    return InventoryAudit(number_of_potions=number_of_potions, ml_in_barrels=ml_in_barrels, gold=gold)


@router.post("/plan", response_model=CapacityPlan)
def get_capacity_plan():
    """
    Provides a daily capacity purchase plan.

    - Start with 1 capacity for 50 potions and 1 capacity for 10,000 ml of potion.
    - Each additional capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT gold, red_ml, green_ml, blue_ml, dark_ml, max_potion_capacity, max_barrel_capacity
                FROM global_inventory
                """
            )
        ).one()
        gold = row.gold
        max_potion_capacity = row.max_potion_capacity
        max_barrel_capacity = row.max_barrel_capacity
        total_liquid_in_inventory = row.red_ml + row.green_ml + row.blue_ml + row.dark_ml
        
        total_potions_in_inventory = connection.execute(
            sqlalchemy.text(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM potions
                """
            )
        ).scalar_one()
        
        liquid_utilization = total_liquid_in_inventory / max_barrel_capacity
        potion_utilization = total_potions_in_inventory / max_potion_capacity

        ml_capacity = 0
        potion_capacity = 0
        if gold >= 2000 and liquid_utilization >= 0.8 and potion_utilization >= 0.8:
            ml_capacity = 1
            potion_capacity = 1
        elif gold >= 1000:
            if liquid_utilization > potion_utilization and liquid_utilization >= 0.8:
                ml_capacity = 1
            elif potion_utilization >= 0.8:
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
    # TODO: to make this idempotent we make a new table with order_id, potion_capacity_increase, ml_capacity_increase, gold_consumed
    # TODO: check if order id already exists
    potion_capacity_increase = capacity_purchase.potion_capacity * 50
    ml_capacity_increase = capacity_purchase.ml_capacity * 10000
    gold_consumed = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000

    with db.engine.begin() as connection:
        print(f"updating capacity in db: potion_capacity_increase: {potion_capacity_increase}, ml_capacity_increase: {ml_capacity_increase}, gold_consumed: {gold_consumed}")
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory SET
                gold = gold - :gold,
                max_potion_capacity = max_potion_capacity + :potion_capacity_increase,
                max_barrel_capacity = max_barrel_capacity + :ml_capacity_increase
                """
            ),
            [{
                "gold": gold_consumed,
                "potion_capacity_increase": potion_capacity_increase,
                "ml_capacity_increase": ml_capacity_increase,
            }]
        )