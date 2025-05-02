from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import sqlalchemy
from src.api import auth
from enum import Enum
from typing import List, Optional
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)


class SearchSortOptions(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class SearchSortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class LineItem(BaseModel):
    line_item_id: int
    item_sku: str
    customer_name: str
    line_item_total: int
    timestamp: str


class SearchResponse(BaseModel):
    previous: Optional[str] = None
    next: Optional[str] = None
    results: List[LineItem]


@router.get("/search/", response_model=SearchResponse, tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: SearchSortOptions = SearchSortOptions.timestamp,
    sort_order: SearchSortOrder = SearchSortOrder.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.
    """
    return SearchResponse(
        previous=None,
        next=None,
        results=[
            LineItem(
                line_item_id=1,
                item_sku="1 oblivion potion",
                customer_name="Scaramouche",
                line_item_total=50,
                timestamp="2021-01-01T00:00:00Z",
            )
        ],
    )


class Customer(BaseModel):
    customer_id: str
    customer_name: str
    character_class: str
    level: int = Field(ge=1, le=20)


@router.post("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def post_visits(visit_id: int, customers: List[Customer]):
    """
    Shares the customers that visited the store on that tick.
    """
    print(customers)
    pass


class CartCreateResponse(BaseModel):
    cart_id: int


@router.post("/", response_model=CartCreateResponse)
def create_cart(new_cart: Customer):
    """
    Creates a new cart for a specific customer.
    """
    customer_name = new_cart.customer_name
    with db.engine.begin() as connection:
        cart_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO carts (customer_name)
                VALUES (:customer_name)
                RETURNING cart_id
                """
            ),
            [{
                "customer_name": customer_name
            }]
        ).scalar_one()
    return CartCreateResponse(cart_id=cart_id)


class CartItem(BaseModel):
    quantity: int = Field(ge=1, description="Quantity must be at least 1")


@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    print(
        f"cart_id: {cart_id}, item_sku: {item_sku}, cart_item: {cart_item}"
    )
    with db.engine.begin() as connection:
        # check if cart hasn't been checked out, then we can proceed
        cart_exists = connection.execute(
            sqlalchemy.text("""
                SELECT EXISTS(
                    SELECT 1 FROM carts 
                    WHERE cart_id = :cart_id 
                    AND is_checked_out = false
                )
            """),
            [{"cart_id": cart_id}]
        ).scalar_one()

        if not cart_exists:
            raise HTTPException(
                status_code=404, 
                detail="Cart not found or already checked out"
            )
        
        # upsert
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO cart_items (cart_id, sku, quantity)
                VALUES (:cart_id, :sku, :quantity)
                ON CONFLICT (cart_id, sku) DO UPDATE
                SET quantity = cart_items.quantity + :quantity
                """
            ), 
            [{
                "cart_id": cart_id,
                "sku": item_sku,
                "quantity": cart_item.quantity,
            }]
        )
    return status.HTTP_204_NO_CONTENT


class CheckoutResponse(BaseModel):
    total_potions_bought: int
    total_gold_paid: int


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout", response_model=CheckoutResponse)
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """
    Handles the checkout process for a specific cart.
    """
    #gold_ledger table
    with db.engine.begin() as connection:
        # check for non checked out cart, then proceed
        cart_exists = connection.execute(
            sqlalchemy.text(
                """
                SELECT EXISTS(
                    SELECT 1 FROM carts 
                    WHERE cart_id = :cart_id 
                    AND is_checked_out = false
                )
                """
            ),
            [{"cart_id": cart_id}]
        ).scalar_one()
        
        if not cart_exists:
            raise HTTPException(
                status_code=404, 
                detail="Cart not found or already checked out"
            )
        
        total_potions_bought = connection.execute(
            sqlalchemy.text(
                """
                SELECT COALESCE(SUM(quantity), 0)
                FROM cart_items
                WHERE cart_id = :cart_id
                """
            ),
            [{
                "cart_id": cart_id
            }]
        ).scalar_one()

        if total_potions_bought == 0:
            raise HTTPException(
                status_code=400,
                detail="Cart is empty"
            )

        total_gold_paid = total_potions_bought * 50  # TODO: assuming each potion costs 50 gold
        connection.execute(
            sqlalchemy.text(
                """
                WITH cart_update AS (
                    UPDATE carts 
                    SET is_checked_out = true
                    WHERE cart_id = :cart_id
                    RETURNING cart_id
                ), inventory_update AS (
                    UPDATE potions
                    SET quantity = potions.quantity - c.quantity
                    FROM cart_items c
                    WHERE c.cart_id = :cart_id AND c.sku = potions.sku
                    RETURNING potions.sku
                )
                UPDATE global_inventory
                SET gold = gold + :total_gold_paid
                RETURNING gold;
                """
            ),
            [{
                "total_gold_paid": total_gold_paid,
                "cart_id": cart_id
            }]
        )

    return CheckoutResponse(
        total_potions_bought=total_potions_bought, total_gold_paid=total_gold_paid
    )
