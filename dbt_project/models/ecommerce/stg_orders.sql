/*
  Layer 1: Clean orders with all date features
  Source: raw_orders
*/
SELECT
    order_id,
    customer_id,
    order_status,

    -- Timestamps
    CAST(order_purchase_timestamp    AS TIMESTAMP) AS order_purchase_timestamp,
    CAST(order_approved_at           AS TIMESTAMP) AS order_approved_at,
    CAST(order_delivered_carrier_date AS TIMESTAMP) AS order_delivered_carrier_date,
    CAST(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
    CAST(order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date,

    -- Derived date parts
    YEAR(CAST(order_purchase_timestamp AS TIMESTAMP))  AS order_year,
    MONTH(CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_month,
    STRFTIME(CAST(order_purchase_timestamp AS TIMESTAMP),
             '%Y-%m')                                  AS order_yearmon,
    DAYNAME(CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_dow,
    HOUR(CAST(order_purchase_timestamp AS TIMESTAMP))  AS order_hour,

    -- Delivery metrics
    DATEDIFF('day',
        CAST(order_purchase_timestamp AS TIMESTAMP),
        CAST(order_delivered_customer_date AS TIMESTAMP)
    )                                                  AS delivery_days,

    -- Delivery delay (positive = late, negative = early)
    DATEDIFF('day',
        CAST(order_estimated_delivery_date AS TIMESTAMP),
        CAST(order_delivered_customer_date AS TIMESTAMP)
    )                                                  AS delivery_delay_days,

    -- Is late flag
    CASE
        WHEN CAST(order_delivered_customer_date AS TIMESTAMP) >
             CAST(order_estimated_delivery_date AS TIMESTAMP)
        THEN 1 ELSE 0
    END                                                AS is_late_delivery

FROM main.raw_orders
WHERE order_purchase_timestamp IS NOT NULL