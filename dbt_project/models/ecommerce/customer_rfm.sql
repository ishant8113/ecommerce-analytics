/*
  Layer 4: RFM scoring per customer
  R = Recency   (days since last order)
  F = Frequency (number of orders)
  M = Monetary  (total spend)
*/
WITH reference_date AS (
    -- Use max order date as reference point
    SELECT MAX(order_purchase_timestamp) AS ref_date
    FROM {{ ref('stg_orders') }}
),

customer_stats AS (
    SELECT
        d.customer_unique_id,
        d.customer_state,
        d.customer_city,

        -- Recency: days since last purchase
        DATEDIFF('day',
            MAX(d.order_purchase_timestamp),
            (SELECT ref_date FROM reference_date)
        )                                           AS recency_days,

        -- Frequency: number of orders
        COUNT(DISTINCT d.order_id)                  AS frequency,

        -- Monetary: total spend
        ROUND(SUM(d.payment_value), 2)              AS monetary,

        -- Extra metrics
        ROUND(AVG(d.payment_value), 2)              AS avg_order_value,
        ROUND(AVG(d.review_score), 2)               AS avg_review_score,
        MIN(d.order_purchase_timestamp)             AS first_order_date,
        MAX(d.order_purchase_timestamp)             AS last_order_date

    FROM {{ ref('stg_order_details') }} d
    GROUP BY
        d.customer_unique_id,
        d.customer_state,
        d.customer_city
),

rfm_scores AS (
    SELECT
        *,
        -- R Score: 5 = most recent, 1 = least recent
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        -- F Score: 5 = most frequent
        NTILE(5) OVER (ORDER BY frequency ASC)      AS f_score,
        -- M Score: 5 = highest spender
        NTILE(5) OVER (ORDER BY monetary ASC)       AS m_score
    FROM customer_stats
),

rfm_segments AS (
    SELECT
        *,
        -- Combined RFM score
        (r_score + f_score + m_score)               AS rfm_total,

        -- Customer segment based on RFM
        CASE
            WHEN r_score >= 4 AND f_score >= 4
                                                    THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3
                                                    THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2
                                                    THEN 'Recent Customers'
            WHEN r_score >= 3 AND m_score >= 3
                                                    THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 3
                                                    THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2
             AND m_score >= 3
                                                    THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2
             AND m_score <= 2
                                                    THEN 'Lost'
            ELSE                                         'Need Attention'
        END                                         AS rfm_segment

    FROM rfm_scores
)

SELECT * FROM rfm_segments