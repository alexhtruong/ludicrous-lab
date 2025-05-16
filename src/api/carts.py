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
    character_class = new_cart.character_class
    with db.engine.begin() as connection:
        cart_id = connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO carts (customer_name, character_class)
                VALUES (:customer_name, :character_class)
                RETURNING cart_id
                """
            ),
            {
                "customer_name": customer_name,
                "character_class": character_class,
            }
        ).scalar_one()
    return CartCreateResponse(cart_id=cart_id)


class CartItem(BaseModel):
    quantity: int = Field(ge=1, description="Quantity must be at least 1")


@router.post("/{cart_id}/items/{item_sku}", status_code=status.HTTP_204_NO_CONTENT)
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    print(
        f"cart_id: {cart_id}, item_sku: {item_sku}, cart_item: {cart_item}"
    )
    with db.engine.connect().execution_options(isolation_level="SERIALIZABLE") as connection:
        with connection.begin():
            # lock the row with FOR UPDATE to prevent concurrent updates
            cart = connection.execute(
                sqlalchemy.text(
                    """
                    SELECT c.is_checked_out, p.sku 
                    FROM carts c
                    JOIN potions p ON p.sku = :sku
                    WHERE c.cart_id = :cart_id
                    FOR UPDATE
                    """
                ),
                {"cart_id": cart_id, "sku": item_sku}
            ).first()

            if cart is None:
                raise HTTPException(
                    status_code=404, 
                    detail="Cart not found or cart is locked"
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
                {
                    "cart_id": cart_id,
                    "sku": item_sku,
                    "quantity": cart_item.quantity,
                }
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
    with db.engine.begin() as connection:
        # check if cart exists and get totals
        cart_exists = connection.execute(
            sqlalchemy.text(
                """
                SELECT cart_id, character_class
                FROM carts 
                WHERE cart_id = :cart_id
                FOR UPDATE
                """
            ),
            {"cart_id": cart_id}
        ).first()

        if cart_exists is None:
            print("cart doesn't exist")
            return
        
        character_class = cart_exists.character_class

        # Then get totals
        cart_info = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    c.is_checked_out, 
                    COALESCE(SUM(ci.quantity), 0) as total_potions_bought,
                    COALESCE(SUM(ci.quantity * p.price), 0) as total_gold
                FROM carts c
                LEFT JOIN cart_items ci ON ci.cart_id = c.cart_id
                LEFT JOIN potions p ON p.sku = ci.sku
                WHERE c.cart_id = :cart_id
                GROUP BY c.cart_id, c.is_checked_out
                """
            ),
            {"cart_id": cart_id}
        ).first()

        # debugging
        if cart_info is None:
            print("no cart info available")
            return CheckoutResponse(
                total_potions_bought=0,
                total_gold_paid=0
            )
        
        if cart_info.total_potions_bought == 0:
            print("total potions in cart is 0")
            return CheckoutResponse(
                total_potions_bought=0,
                total_gold_paid=0
            )
        
        total_potions_bought = cart_info.total_potions_bought
        total_gold = cart_info.total_gold

        if cart_info.is_checked_out:
            print("cart is already checked out")
            return CheckoutResponse(
                total_potions_bought=total_potions_bought,
                total_gold_paid=total_gold
            )
        
        # check for sufficient inventory
        insufficient_inventory = connection.execute(
            sqlalchemy.text(
                """
                WITH cart_totals AS (
                    SELECT ci.sku, ci.quantity as requested_quantity
                    FROM cart_items ci
                    WHERE ci.cart_id = :cart_id
                )
                SELECT ct.sku, ct.requested_quantity, COALESCE(SUM(pl.quantity_delta), 0) as available_quantity
                FROM cart_totals ct
                LEFT JOIN potion_ledger pl ON pl.sku = ct.sku
                GROUP BY ct.sku, ct.requested_quantity
                HAVING COALESCE(SUM(pl.quantity_delta), 0) < ct.requested_quantity
                """
            ),
            {"cart_id": cart_id}
        ).all()

        if insufficient_inventory:
            print("insufficient inventory while checking out")
            return CheckoutResponse(
                total_potions_bought=0,
                total_gold_paid=0
            )
        
        # update gold and potion ledger, check out cart, and update sale analytics
        connection.execute(
            sqlalchemy.text(
                """
                WITH gold_update AS (
                    INSERT INTO gold_ledger 
                    (order_id, gold_delta, transaction_type)
                    VALUES (:cart_id, :gold_delta, 'POTION_SALE')
                ), cart_update AS (
                    UPDATE carts 
                    SET is_checked_out = true
                    WHERE cart_id = :cart_id
                ), potion_ledger_update AS (
                    INSERT INTO potion_ledger (order_id, line_item_id, sku, quantity_delta, transaction_type)
                    SELECT 
                        :cart_id,
                        ROW_NUMBER() OVER () as line_item_id,
                        sku,
                        -quantity, 
                        'POTION_SALE'
                    FROM cart_items
                    WHERE cart_id = :cart_id
                ), cur_time AS (
                    SELECT day_of_week, hour_of_day
                    FROM time_analytics
                    ORDER BY created_at DESC
                    LIMIT 1
                ), sale_analytics_update AS (
                    INSERT INTO sale_analytics 
                    (cart_id, customer_class, hour_of_day, day_of_week, total_gold, potion_count)
                    SELECT 
                        :cart_id,
                        :character_class,
                        hour_of_day,
                        day_of_week,
                        :gold_delta,
                        :potion_count
                    FROM cur_time
                )
                SELECT 1
                """
            ),
            {
                "cart_id": cart_id,
                "gold_delta": total_gold,
                "character_class": character_class,
                "potion_count": total_potions_bought
            }
        )
        
    return CheckoutResponse(
        total_potions_bought=total_potions_bought, total_gold_paid=total_gold
    )