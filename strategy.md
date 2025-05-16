# Lex's Ludicrous Lab Strategy Document

## Step 1: Strategic Hypotheses

### 1. Customer Class Optimization

**Hypothesis**: We can significantly increase profitability by optimizing our potion mix to target the most profitable customer classes.

**Rationale**:

- Different character classes have specific potion preferences
- Building recognition with specific classes leads to increased trust and repeat business
- Some classes may have higher spending power or purchase frequency
- Focusing inventory on high-value customers could increase profit margins

### 2. Time-Based Inventory Management

**Hypothesis**: Adjusting our inventory strategy based on day/time patterns will improve sell-through rates and reduce waste.

**Rationale**:
- The game operates on a 7-day cycle with 12 ticks per day
- Different customer classes may shop at different times
- Inventory levels affect our ability to capture sales
- Excess inventory during low-demand periods ties up capital
- Optimal barrel purchasing timing could reduce costs

**Metrics**:
- Sales rate by time period (tick/day)
- Current inventory levels by potion type
- Barrel purchase timing vs. usage
- Customer visit patterns
- Gold earned per time period

**Success Criteria**:
- 25% reduction in excess inventory during low periods
- 20% improvement in inventory turnover rate
- 15% increase in sales during peak periods
- Optimal barrel purchasing timing could reduce costs

### 3. Price Optimization by Potion Mix

**Hypothesis**: Creating optimal potion mixes with dynamic pricing will maximize profit margins while maintaining competitive quality scores.

**Rationale**:

- We can create over 100,000 possible potion combinations
- Different potion mixes have different production costs
- Customer willingness to pay varies by potion type and class
- Finding the optimal price-mix balance could significantly impact margins

## Step 2: Experiment Design

### 1. Customer Class Analysis

**Metrics**:

- Sales volume by customer class
- Average transaction value by class
- Potion preference patterns by class
- Customer return rate by class
- Gold earned per customer class
- Time of day/week patterns by class

**Success Criteria**:

- 20% increase in repeat customers from target classes
- 15% increase in average transaction value

### 2. Time-Based Analysis

**Metrics**:

- Sales rate by time period (tick/day)
- Stock-out frequency by time period
- Inventory holding time
- Barrel purchase timing vs. usage
- Customer visit patterns
- Gold earned per time period

**Success Criteria**:

- 30% reduction in stock-outs during peak periods
- 25% reduction in excess inventory during low periods
- 20% improvement in inventory turnover rate

### 3. Potion Mix Analysis

**Metrics**:

- Profit margin by potion mix
- Sales volume by potion composition
- Customer satisfaction by potion type
- Production cost vs. sale price ratio
- Competition price analysis
- Value score trends

**Success Criteria**:

- 25% increase in average profit margin per potion
- 15% improvement in value scores
- 20% increase in overall shop profitability

## Step 3: Analytics Implementation

### New Analytics Tables

To support my experiments, I'm implementing three new analytics tables through Alembic migrations. Here's the Python/SQLAlchemy schema definition:

```python
# Sale Analytics Table - Tracks individual transactions
op.create_table(
    'sale_analytics',
    sa.Column('transaction_id', sa.Integer, primary_key=True),
    sa.Column('order_id', sa.Integer, nullable=False),
    sa.Column('customer_class', sa.String, nullable=False),
    sa.Column('hour_of_day', sa.Integer, nullable=False),
    sa.Column('day_of_week', sa.String, nullable=False),
    sa.Column('total_gold', sa.Float, nullable=False),
    sa.Column('potion_count', sa.Integer, nullable=False),
    sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
)

# Potion Performance Analytics Table - Tracks metrics per potion type
op.create_table(
    'potion_analytics',
    sa.Column('sku', sa.String, primary_key=True),
    sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
    sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
    sa.Column('avg_sale_price', sa.Float, nullable=False, server_default='0'),
    sa.Column('profit_margin', sa.Float, nullable=False, server_default='0'),
    sa.Column('last_updated', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.ForeignKeyConstraint(['sku'], ['potions.sku'], ondelete='CASCADE')
)

# Time Series Analytics Table - Tracks patterns
op.create_table(
    'time_analytics',
    sa.Column('tick_id', sa.Integer, primary_key=True),
    sa.Column('day_of_week', sa.String, nullable=False),
    sa.Column('hour_of_day', sa.Integer, nullable=False),
    sa.Column('total_sales', sa.Integer, nullable=False, server_default='0'),
    sa.Column('total_gold', sa.Float, nullable=False, server_default='0'),
    sa.Column('visitor_count', sa.Integer, nullable=False, server_default='0'),
    sa.Column('created_at', sa.DateTime, server_default=sa.text('CURRENT_TIMESTAMP'))
)
```

## Step 4: Analytics Queries

### Customer Class Analysis

```sql
-- Top performing customer classes
SELECT
    sa.customer_class,
    COUNT(DISTINCT sa.order_id) as total_orders,
    SUM(sa.total_gold) as total_revenue,
    AVG(sa.total_gold) as avg_order_value,
    COUNT(DISTINCT CASE WHEN sa.potion_count > 1 THEN sa.order_id END) as multi_item_orders
FROM sale_analytics sa
GROUP BY sa.customer_class
ORDER BY total_revenue DESC;

-- Customer class preferences
SELECT
    sa.customer_class,
    p.red_ml, p.green_ml, p.blue_ml, p.dark_ml,
    COUNT(*) as purchase_count,
    AVG(gl.gold_delta) as avg_sale_price
FROM sale_analytics sa
JOIN potion_ledger pl ON sa.order_id = pl.order_id
JOIN potions p ON pl.sku = p.sku
JOIN gold_ledger gl ON sa.order_id = gl.order_id
GROUP BY sa.customer_class, p.red_ml, p.green_ml, p.blue_ml, p.dark_ml
HAVING COUNT(*) > 5
ORDER BY purchase_count DESC;
```

### Time-Based Analysis

```sql
-- Peak sales periods
SELECT
    ta.day_of_week,
    ta.tick_of_day,
    AVG(ta.total_sales) as avg_sales,
    AVG(ta.total_gold) as avg_revenue,
    AVG(ta.visitor_count) as avg_visitors
FROM time_analytics ta
GROUP BY ta.day_of_week, ta.tick_of_day
ORDER BY avg_revenue DESC;

-- Inventory efficiency
SELECT
    ta.day_of_week,
    AVG(ta.visitor_count) as avg_visitors,
    SUM(ta.total_gold) as total_revenue,
    COUNT(DISTINCT CASE WHEN ta.total_sales = 0 AND ta.visitor_count > 0 THEN ta.hour_of_day END) as potential_stockout_hours
FROM time_analytics ta
GROUP BY ta.day_of_week
ORDER BY ta.day_of_week;
```

### Potion Mix Performance

```sql
-- Most profitable potion combinations
SELECT
    p.sku,
    p.red_ml, p.green_ml, p.blue_ml, p.dark_ml,
    pa.total_sales,
    pa.total_gold,
    pa.profit_margin
FROM potion_analytics pa
JOIN potions p ON pa.sku = p.sku
WHERE pa.total_sales > 10
ORDER BY pa.profit_margin DESC;

-- Price sensitivity analysis
SELECT
    p.sku,
    WIDTH_BUCKET(gl.gold_delta,
        MIN(gl.gold_delta),
        MAX(gl.gold_delta),
        5) as price_bucket,
    COUNT(*) as sales_count,
    AVG(gl.gold_delta) as avg_price
FROM potion_ledger pl
JOIN gold_ledger gl ON pl.order_id = gl.order_id
JOIN potions p ON pl.sku = p.sku
GROUP BY p.sku, price_bucket
ORDER BY p.sku, price_bucket;
```

These analytics will provide the data needed to validate our hypotheses and make data-driven decisions to optimize the shop's profitability.
