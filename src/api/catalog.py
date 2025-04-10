from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Annotated
from src import database as db
import sqlalchemy

router = APIRouter()


class CatalogItem(BaseModel):
    sku: Annotated[str, Field(pattern=r"^[a-zA-Z0-9_]{1,20}$")]
    name: str
    quantity: Annotated[int, Field(ge=1, le=10000)]
    price: Annotated[int, Field(ge=1, le=500)]
    potion_type: List[int] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="Must contain exactly 4 elements: [r, g, b, d]",
    )


def create_catalog() -> List[CatalogItem]:
    catalog = []
    with db.engine.begin() as connection: 
        row = connection.execute(
            sqlalchemy.text(
                """
                SELECT red_potions, green_potions, blue_potions
                FROM global_inventory
                """
            )
        ).one()

        potion_configs = [
            ("RED", row.red_potions, [100, 0, 0, 0]),
            ("GREEN", row.green_potions, [0, 100, 0, 0]),
            ("BLUE", row.blue_potions, [0, 0, 100, 0])
        ]

        for color, quantity, potion_type in potion_configs:
            if quantity > 0:
                catalog.append(
                    CatalogItem(
                        sku=f"{color}_POTION_0",
                        name=f"{color.lower()} potion",
                        quantity=quantity,
                        price=50,
                        potion_type=potion_type
                    )
                )
    
    return catalog


@router.get("/catalog/", tags=["catalog"], response_model=List[CatalogItem])
def get_catalog() -> List[CatalogItem]:
    """
    Retrieves the catalog of items. Each unique item combination should have only a single price.
    You can have at most 6 potion SKUs offered in your catalog at one time.
    """
    return create_catalog()
