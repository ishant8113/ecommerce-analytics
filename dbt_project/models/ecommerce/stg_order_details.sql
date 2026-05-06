/*
  Layer 2: Master order details
  Joins: orders + items + payments + reviews + customers
*/
WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    WHERE order_status = 'delivered'
),

items AS (
    SELECT
        order_id,
        product_id,
        seller_id,
        price,
        freight_value,
        (price + freight_value)         AS item_total
    FROM main.raw_items
),

payments AS (
    SELECT
        order_id,
        SUM(payment_value)              AS payment_value,
        MAX(payment_installments)       AS payment_installments,
        FIRST(payment_type)             AS payment_type
    FROM main.raw_payments
    GROUP BY order_id
),

reviews AS (
    SELECT
        order_id,
        AVG(review_score)               AS review_score
    FROM main.raw_reviews
    GROUP BY order_id
),

customers AS (
    SELECT
        customer_id,
        customer_unique_id,
        customer_city,
        customer_state
    FROM main.raw_customers
)

SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_yearmon,
    o.order_year,
    o.order_month,
    o.order_dow,
    o.order_hour,
    o.delivery_days,
    o.delivery_delay_days,
    o.is_late_delivery,
    i.product_id,
    i.seller_id,
    i.price,
    i.freight_value,
    i.item_total,
    p.payment_value,
    p.payment_type,
    p.payment_installments,
    r.review_score

FROM orders          o
LEFT JOIN items      i ON o.order_id  = i.order_id
LEFT JOIN payments   p ON o.order_id  = p.order_id
LEFT JOIN reviews    r ON o.order_id  = r.order_id
LEFT JOIN customers  c ON o.customer_id = c.customer_id