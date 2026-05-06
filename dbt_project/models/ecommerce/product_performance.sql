/*
  Layer 5: Product and category level performance
  Joins: stg_order_details + stg_products
*/
SELECT
    p.product_id,
    p.category_english                          AS category,
    p.product_volume_cm3,
    p.product_weight_g,
    p.product_photos_qty,

    -- Sales metrics
    COUNT(DISTINCT d.order_id)                  AS total_orders,
    SUM(d.payment_value)                        AS total_revenue,
    ROUND(AVG(d.price), 2)                      AS avg_price,
    ROUND(AVG(d.freight_value), 2)              AS avg_freight,
    ROUND(AVG(d.review_score), 2)               AS avg_rating,

    -- Freight as % of price
    ROUND(AVG(d.freight_value) /
          NULLIF(AVG(d.price), 0) * 100, 2)     AS freight_pct,

    -- Late delivery rate per product
    ROUND(AVG(d.is_late_delivery) * 100, 2)     AS late_delivery_pct

FROM {{ ref('stg_order_details') }}  d
LEFT JOIN {{ ref('stg_products') }}  p
       ON d.product_id = p.product_id
WHERE d.product_id IS NOT NULL
GROUP BY
    p.product_id,
    p.category_english,
    p.product_volume_cm3,
    p.product_weight_g,
    p.product_photos_qty