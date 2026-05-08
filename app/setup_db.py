import os
import duckdb
import pandas as pd
import pyarrow

def setup():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    DB_PATH  = os.path.join(DATA_DIR, 'ecommerce.db')

    files = {
        'raw_orders'     : 'olist_orders_dataset.csv',
        'raw_items'      : 'olist_order_items_dataset.csv',
        'raw_payments'   : 'olist_order_payments_dataset.csv',
        'raw_reviews'    : 'olist_order_reviews_dataset.csv',
        'raw_customers'  : 'olist_customers_dataset.csv',
        'raw_products'   : 'olist_products_dataset.csv',
        'raw_sellers'    : 'olist_sellers_dataset.csv',
        'raw_category'   : 'product_category_name_translation.csv',
        'raw_geolocation': 'olist_geolocation_dataset.csv'
    }

    con = duckdb.connect(DB_PATH)

    # Load raw tables
    for table_name, filename in files.items():
        path = os.path.join(DATA_DIR, filename)
        df   = pd.read_csv(path)
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str)
        parquet = os.path.join(DATA_DIR, f'{table_name}.parquet')
        df.to_parquet(parquet, index=False)
        con.execute(f"DROP TABLE IF EXISTS {table_name}")
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_parquet('{parquet.replace(chr(92),'/')}')
        """)
        print(f"✅ {table_name}")

    # Build SQL models
    con.execute("""
    CREATE OR REPLACE TABLE stg_orders AS
    SELECT order_id, customer_id, order_status,
        TRY_CAST(order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
        TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
        TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date,
        YEAR(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_year,
        MONTH(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_month,
        STRFTIME(TRY_CAST(order_purchase_timestamp AS TIMESTAMP),'%Y-%m') AS order_yearmon,
        DAYNAME(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_dow,
        HOUR(TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS order_hour,
        DATEDIFF('day',
            TRY_CAST(order_purchase_timestamp AS TIMESTAMP),
            TRY_CAST(order_delivered_customer_date AS TIMESTAMP)) AS delivery_days,
        DATEDIFF('day',
            TRY_CAST(order_estimated_delivery_date AS TIMESTAMP),
            TRY_CAST(order_delivered_customer_date AS TIMESTAMP)) AS delivery_delay_days,
        CASE WHEN TRY_CAST(order_delivered_customer_date AS TIMESTAMP) >
                  TRY_CAST(order_estimated_delivery_date AS TIMESTAMP)
             THEN 1 ELSE 0 END AS is_late_delivery
    FROM raw_orders
    WHERE order_purchase_timestamp IS NOT NULL
    """)

    con.execute("""
    CREATE OR REPLACE TABLE stg_order_details AS
    WITH payments AS (
        SELECT order_id,
               SUM(payment_value) AS payment_value,
               FIRST(payment_type) AS payment_type,
               MAX(payment_installments) AS payment_installments
        FROM raw_payments GROUP BY order_id
    ),
    reviews AS (
        SELECT order_id, AVG(CAST(review_score AS DOUBLE)) AS review_score
        FROM raw_reviews GROUP BY order_id
    )
    SELECT o.order_id, o.customer_id,
           c.customer_unique_id, c.customer_city, c.customer_state,
           o.order_status, o.order_purchase_timestamp,
           o.order_yearmon, o.order_year, o.order_month,
           o.order_dow, o.order_hour,
           o.delivery_days, o.delivery_delay_days, o.is_late_delivery,
           i.product_id, i.seller_id,
           CAST(i.price AS DOUBLE) AS price,
           CAST(i.freight_value AS DOUBLE) AS freight_value,
           p.payment_value, p.payment_type, p.payment_installments,
           r.review_score
    FROM stg_orders o
    LEFT JOIN raw_items i     ON o.order_id = i.order_id
    LEFT JOIN payments p      ON o.order_id = p.order_id
    LEFT JOIN reviews r       ON o.order_id = r.order_id
    LEFT JOIN raw_customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
    """)

    con.execute("""
    CREATE OR REPLACE TABLE stg_products AS
    SELECT p.product_id, p.product_category_name,
           COALESCE(c.product_category_name_english,
                    p.product_category_name) AS category_english
    FROM raw_products p
    LEFT JOIN raw_category c
           ON p.product_category_name = c.product_category_name
    """)

    con.execute("""
    CREATE OR REPLACE TABLE customer_rfm AS
    WITH stats AS (
        SELECT customer_unique_id, customer_state, customer_city,
               DATEDIFF('day', MAX(order_purchase_timestamp),
                   (SELECT MAX(order_purchase_timestamp) FROM stg_order_details)
               ) AS recency_days,
               COUNT(DISTINCT order_id) AS frequency,
               SUM(payment_value) AS monetary,
               AVG(payment_value) AS avg_order_value,
               AVG(review_score)  AS avg_review_score
        FROM stg_order_details
        GROUP BY customer_unique_id, customer_state, customer_city
    ),
    scored AS (
        SELECT *,
            NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
            NTILE(5) OVER (ORDER BY frequency ASC)     AS f_score,
            NTILE(5) OVER (ORDER BY monetary ASC)      AS m_score
        FROM stats
    )
    SELECT *,
        (r_score + f_score + m_score) AS rfm_total,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
            WHEN r_score >= 3 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score <= 2
             AND m_score >= 3               THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2
             AND m_score <= 2               THEN 'Lost'
            ELSE                                 'Need Attention'
        END AS rfm_segment
    FROM scored
    """)

    con.execute("""
    CREATE OR REPLACE TABLE product_performance AS
    SELECT p.product_id, p.category_english AS category,
           COUNT(DISTINCT d.order_id)           AS total_orders,
           SUM(d.payment_value)                 AS total_revenue,
           AVG(d.price)                         AS avg_price,
           AVG(d.freight_value)                 AS avg_freight,
           AVG(d.review_score)                  AS avg_rating,
           AVG(d.is_late_delivery) * 100        AS late_delivery_pct
    FROM stg_order_details d
    LEFT JOIN stg_products p ON d.product_id = p.product_id
    WHERE d.product_id IS NOT NULL
    GROUP BY p.product_id, p.category_english
    """)

    con.execute("""
    CREATE OR REPLACE TABLE executive_summary AS
    SELECT COUNT(DISTINCT order_id)          AS total_orders,
           COUNT(DISTINCT customer_unique_id) AS total_customers,
           SUM(payment_value)                AS total_revenue,
           AVG(payment_value)                AS avg_order_value,
           MAX(payment_value)                AS max_order_value,
           AVG(review_score)                 AS avg_review_score,
           AVG(delivery_days)                AS avg_delivery_days,
           AVG(is_late_delivery) * 100       AS late_delivery_pct,
           MIN(order_purchase_timestamp)     AS first_order_date,
           MAX(order_purchase_timestamp)     AS last_order_date
    FROM stg_order_details
    """)
# Build co-purchase rules
    from itertools import combinations
    from collections import Counter

    print("Building co-purchase rules...")

    # Load order + product data
    df = con.execute("""
        SELECT d.order_id, p.category_english AS category
        FROM stg_order_details d
        LEFT JOIN stg_products p ON d.product_id = p.product_id
        WHERE p.category_english IS NOT NULL
          AND p.category_english != 'unknown'
    """).df()

    # Find multi-item orders
    order_cats   = df.groupby('order_id')['category'].apply(list)
    multi_orders = order_cats[order_cats.apply(len) >= 2]

    # Count pairs
    pair_counts = Counter()
    for cats in multi_orders:
        for pair in combinations(sorted(set(cats)), 2):
            pair_counts[pair] += 1

    total_orders = len(order_cats)
    cat_counts   = df.groupby('category')['order_id'].nunique()

    pairs_list = []
    for (a, b), count in pair_counts.most_common():
        if count >= 10:
            p_a  = cat_counts.get(a, 1) / total_orders
            p_b  = cat_counts.get(b, 1) / total_orders
            p_ab = count / total_orders
            pairs_list.append({
                'category_a'  : a,
                'category_b'  : b,
                'co_purchases': count,
                'support_pct' : round(p_ab * 100, 3),
                'confidence'  : round(count / cat_counts.get(a, 1), 4),
                'lift'        : round(p_ab / (p_a * p_b), 4)
            })

    pairs_df = pd.DataFrame(pairs_list)

    # Save to parquet then DuckDB
    parquet = os.path.join(DATA_DIR, 'copurchase_rules.parquet')
    pairs_df.to_parquet(parquet, index=False)

    con.execute("DROP TABLE IF EXISTS copurchase_rules")
    con.execute(f"""
        CREATE TABLE copurchase_rules AS
        SELECT * FROM read_parquet('{parquet.replace(chr(92),'/')}')
    """)
    print(f"✅ copurchase_rules — {len(pairs_df)} pairs")
    
    # Cohort retention
    from itertools import combinations
    import importlib
    pd = importlib.import_module('pandas')
    print("Building cohort retention...")
    df_cohort = con.execute("""
        SELECT customer_unique_id,
               order_id,
               order_purchase_timestamp,
               payment_value
        FROM stg_order_details
        WHERE order_purchase_timestamp IS NOT NULL
    """).df()

    df_cohort['order_purchase_timestamp'] = pd.to_datetime(
        df_cohort['order_purchase_timestamp']
    )
    df_cohort['order_month'] = (
        df_cohort['order_purchase_timestamp']
        .dt.to_period('M')
    )

    first_purchase = (
        df_cohort.groupby('customer_unique_id')['order_month']
        .min()
        .reset_index()
    )
    first_purchase.columns = ['customer_unique_id','cohort_month']

    df_cohort = df_cohort.merge(first_purchase, on='customer_unique_id')
    df_cohort['cohort_index'] = (
        df_cohort['order_month'] - df_cohort['cohort_month']
    ).apply(lambda x: x.n)

    cohort_pivot = (
        df_cohort.groupby(['cohort_month','cohort_index'])
        ['customer_unique_id'].nunique()
        .reset_index()
    )
    cohort_matrix = cohort_pivot.pivot(
        index='cohort_month',
        columns='cohort_index',
        values='customer_unique_id'
    ).iloc[:-3]

    cohort_size   = cohort_matrix[0]
    retention_pct = (
        cohort_matrix.divide(cohort_size, axis=0).round(3) * 100
    )

    cohort_save = retention_pct.reset_index()
    cohort_save['cohort_month'] = cohort_save['cohort_month'].astype(str)

    parquet = os.path.join(DATA_DIR, 'cohort_retention.parquet')
    cohort_save.to_parquet(parquet, index=False)

    con.execute("DROP TABLE IF EXISTS cohort_retention")
    con.execute(f"""
        CREATE TABLE cohort_retention AS
        SELECT * FROM read_parquet('{parquet.replace(chr(92),'/')}')
    """)
    print(f"✅ cohort_retention — {len(cohort_save)} cohorts")
    con.close()
    print("✅ All tables built successfully")

if __name__ == "__main__":
    setup()