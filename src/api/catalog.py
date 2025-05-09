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
        #[(sku, name, ...), (sku, name, ...)]
        potions = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    p.sku,
                    p.name,
                    COALESCE(SUM(pl.quantity_delta), 0) AS quantity,
                    p.price, 
                    p.red_ml, 
                    p.green_ml, 
                    p.blue_ml, 
                    p.dark_ml
                FROM potions p
                LEFT JOIN potion_ledger pl ON pl.sku = p.sku
                WHERE is_active = TRUE
                GROUP BY p.sku, p.name, p.price, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml
                HAVING COALESCE(SUM(pl.quantity_delta), 0) > 0
                """
            )
        ).all()

        for potion in potions:
            sku = potion.sku
            name = potion.name
            quantity = potion.quantity
            price = potion.price
            potion_type = [potion.red_ml, potion.green_ml, potion.blue_ml, potion.dark_ml]  # [r, g, b, d]
            catalog.append(
                CatalogItem(
                    sku=sku,
                    name=name,
                    quantity=quantity,
                    price=price,
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
