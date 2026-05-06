/*
  Layer 3: Products enriched with English category names
  Joins: products + category translation
*/
SELECT
    p.product_id,
    p.product_category_name,
    COALESCE(c.product_category_name_english,
             p.product_category_name)   AS category_english,
    p.product_name_lenght               AS product_name_length,
    p.product_description_lenght        AS product_desc_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm,

    -- Volume in cm3
    (p.product_length_cm *
     p.product_height_cm *
     p.product_width_cm)                AS product_volume_cm3

FROM main.raw_products   p
LEFT JOIN main.raw_category c
       ON p.product_category_name = c.product_category_name