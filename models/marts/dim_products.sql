with products as (
    select * from {{ ref('stg_shop__products') }}
),

sales as (
    select
        product_id,
        count(distinct order_id) as orders,
        sum(quantity) filter (where not is_reversed) as units_sold,
        sum(net_revenue) as net_revenue,
        sum(gross_margin) as gross_margin,
        count(*) filter (where order_status = 'returned') as returned_lines,
        count(*) filter (where order_status in ('delivered', 'returned')) as delivered_lines,
        min(placed_at) as first_sold_at,
        max(placed_at) as last_sold_at
    from {{ ref('fct_order_items') }}
    group by product_id
)

select
    products.product_id,
    products.sku,
    products.product_name,
    products.category,
    products.unit_price,
    products.unit_cost,
    cast(products.unit_price - products.unit_cost as decimal(12, 2)) as unit_margin,
    products.is_active,
    products.created_at,
    coalesce(sales.orders, 0) as orders,
    coalesce(sales.units_sold, 0) as units_sold,
    cast(coalesce(sales.net_revenue, 0) as decimal(12, 2)) as net_revenue,
    cast(coalesce(sales.gross_margin, 0) as decimal(12, 2)) as gross_margin,
    {{ safe_divide('sales.returned_lines', 'sales.delivered_lines') }} as return_rate,
    sales.first_sold_at,
    sales.last_sold_at
from products
left join sales on products.product_id = sales.product_id
