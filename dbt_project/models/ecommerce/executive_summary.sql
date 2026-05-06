/*
  Layer 6: Top level KPIs for dashboard home page
  Single row summary of entire business
*/
SELECT
    -- Volume
    COUNT(DISTINCT order_id)                    AS total_orders,
    COUNT(DISTINCT customer_unique_id)          AS total_customers,

    -- Revenue
    ROUND(SUM(payment_value), 2)                AS total_revenue,
    ROUND(AVG(payment_value), 2)                AS avg_order_value,
    ROUND(MAX(payment_value), 2)                AS max_order_value,

    -- Satisfaction
    ROUND(AVG(review_score), 2)                 AS avg_review_score,

    -- Delivery
    ROUND(AVG(delivery_days), 1)                AS avg_delivery_days,
    ROUND(AVG(is_late_delivery) * 100, 2)       AS late_delivery_pct,

    -- Time range
    MIN(order_purchase_timestamp)               AS first_order_date,
    MAX(order_purchase_timestamp)               AS last_order_date

FROM {{ ref('stg_order_details') }}