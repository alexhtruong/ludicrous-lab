from fastapi import APIRouter, Depends, status
import sqlalchemy
from src.api import auth
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text("DELETE FROM gold_ledger")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM potion_ledger")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM liquid_ledger")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM carts")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM cart_items")
        )
        connection.execute(
            sqlalchemy.text("DELETE FROM capacity_order_ledger")
        )
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO gold_ledger (order_id, gold_delta, transaction_type)
                VALUES (-1, 100, 'GAME_RESET')
                """
            )
        )
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO capacity_order_ledger 
                (order_id, potion_capacity_increase, ml_capacity_increase, gold_delta)
                VALUES (-1, 50, 10000, 0)
                """
            )
        )
    # TODO: Implement database write logic here
    pass
