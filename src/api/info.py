from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from src.api import auth
from src import database as db
import sqlalchemy

router = APIRouter(
    prefix="/info",
    tags=["info"],
    dependencies=[Depends(auth.get_api_key)],
)


class Timestamp(BaseModel):
    day: str
    hour: int


@router.post("/current_time", status_code=status.HTTP_204_NO_CONTENT)
def post_time(timestamp: Timestamp):
    """
    Shares what the latest time (in game time) is.
    Records analytics for the current tick.
    """
    with db.engine.begin() as connection:
        # get metrics from ledger tables for the previous tick until now(last 3 hours)
        sales_data = connection.execute(
            sqlalchemy.text(
                """
                SELECT 
                    COALESCE(COUNT(DISTINCT gl.order_id), 0) as total_sales,
                    COALESCE(SUM(gl.gold_delta), 0) as total_gold,
                    COALESCE(COUNT(DISTINCT c.cart_id), 0) as visitor_count
                FROM gold_ledger gl
                LEFT JOIN potion_ledger pl ON pl.order_id = gl.order_id
                LEFT JOIN carts c ON DATE(c.created_at) = CURRENT_DATE
                WHERE DATE(gl.created_at) = CURRENT_DATE
                    AND gl.created_at >= NOW() - INTERVAL '3 hours'
                    AND gl.transaction_type = 'POTION_SALE'
                """
            )
        ).first()

        # upsert time analytics for previous tick
        connection.execute(
            sqlalchemy.text(
                """
                INSERT INTO time_analytics (
                    day_of_week,
                    hour_of_day,
                    total_sales,
                    total_gold,
                    visitor_count
                ) VALUES (:day, :hour_of_day, :total_sales, :total_gold, :visitor_count)
                ON CONFLICT (day_of_week, hour_of_day) DO UPDATE SET
                    total_sales = :total_sales,
                    total_gold = :total_gold,
                    visitor_count = :visitor_count,
                    created_at = CURRENT_TIMESTAMP
                """
            ),
            {
                "day": timestamp.day,
                "hour_of_day": timestamp.hour,
                "total_sales": sales_data.total_sales,
                "total_gold": float(sales_data.total_gold or 0),
                "visitor_count": sales_data.visitor_count
            }
        )
