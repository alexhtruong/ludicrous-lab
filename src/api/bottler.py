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


@router.post("/deliver/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_deliver_bottles(potions_delivered: List[PotionMixes], order_id: int):
    """
    Delivery of potions requested after plan. order_id is a unique value representing
    a single delivery; the call is idempotent based on the order_id.
    """
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    
    potion_types = [
        [100, 0, 0, 0], # pure red
        [0, 100, 0, 0], # pure green
        [0, 0, 100, 0], # pure blue
    ]
    potion_quantities = [0, 0, 0]
    for delivered_potion in potions_delivered:
        for i, potion in enumerate(potion_types):
            if delivered_potion.potion_type == potion_types[i]:
                potion_quantities[i] = delivered_potion.quantity
    
    red_potions, green_potions, blue_potions = potion_quantities
    red_ml = red_potions * 100
    green_ml = green_potions * 100
    blue_ml = blue_potions * 100
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(
                """
                UPDATE global_inventory SET
                red_potions = red_potions + :red_potions,
                green_potions = green_potions + :green_potions,
                blue_potions = blue_potions + :blue_potions,
                red_ml = red_ml - :red_ml,
                green_ml = green_ml - :green_ml,
                blue_ml = blue_ml - :blue_ml
                """
            ), 
            [{
                "red_potions": red_potions,
                "green_potions": green_potions,
                "blue_potions": blue_potions,
                "red_ml": red_ml,
                "green_ml": green_ml,
                "blue_ml": blue_ml,
            }]
        )


def create_bottle_plan(
    red_ml: int,
    green_ml: int,
    blue_ml: int,
    dark_ml: int,
    maximum_potion_capacity: int,
    current_potion_inventory: List[PotionMixes],
) -> List[PotionMixes]:
    color_ml = [red_ml, green_ml, blue_ml]
    potion_types = [
        [100, 0, 0, 0], # pure red
        [0, 100, 0, 0], # pure green
        [0, 0, 100, 0], # pure blue
    ]

    plans = []
    for i, ml in enumerate(color_ml):
        if ml >= 100:
            quantity = ml // 100
            plans.append(
                PotionMixes(
                    potion_type=potion_types[i],
                    quantity=quantity,
                )
            )
    
    return plans


@router.post("/plan", response_model=List[PotionMixes])
def get_bottle_plan():
    """
    Gets the plan for bottling potions.
    Each bottle has a quantity of what proportion of red, green, blue, and dark potions to add.
    Colors are expressed in integers from 0 to 100 that must sum up to exactly 100.
    """
    with db.engine.begin() as connection:
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT red_potions, green_potions, blue_potions, red_ml, green_ml, blue_ml 
                FROM global_inventory
                """
            )
        ).one()
        # red_potions = row.red_potions
        # green_potions = row.green_potions
        # blue_potions = row.blue_potions
        red_ml = row.red_ml
        green_ml = row.green_ml
        blue_ml = row.blue_ml


    return create_bottle_plan(
        red_ml=red_ml,
        green_ml=green_ml,
        blue_ml=blue_ml,
        dark_ml=0,
        maximum_potion_capacity=50,
        current_potion_inventory=[],
    )


if __name__ == "__main__":
    print(get_bottle_plan())
