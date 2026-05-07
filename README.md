# 🛒 E-Commerce Revenue & Product Intelligence Dashboard

An end-to-end e-commerce analytics project built for a data analyst portfolio.
This project ingests 9 interconnected tables from Brazil's largest e-commerce
marketplace, builds a multi-layer SQL transformation pipeline using dbt, performs
RFM customer segmentation, co-purchase analysis, and surfaces insights through
an interactive 5-page Streamlit dashboard.

🔗 **[Live Dashboard →](https://ishant8113-ecommerce-analytics.streamlit.app)**
📁 **[GitHub Repo →](https://github.com/ishant8113/ecommerce-analytics)**

---

## 📊 Key Business Metrics

| Metric | Value |
|---|---|
| 💰 Total Revenue | R$ 19,776,160 |
| 📦 Total Orders | 96,478 delivered |
| 👥 Unique Customers | 93,358 |
| 🛍️ Unique Products | 32,951 |
| 🏪 Active Sellers | 3,095 |
| ⭐ Avg Review Score | 4.08 / 5.0 |
| 🚚 Avg Delivery Time | 12.4 days |
| ⚠️ Late Delivery Rate | 7.91% |
| 📅 Data Period | Sep 2016 — Aug 2018 |

---

## 🏗️ Project Architecture

```
9 CSV Files (Olist Dataset)
         ↓
   DuckDB Storage         ← 9 raw tables loaded via Python + PyArrow
         ↓
   dbt SQL Pipeline       ← 6 transformation models
         ↓
   Python Analytics       ← RFM segmentation + Co-purchase analysis
         ↓
   Streamlit Dashboard    ← 5-page interactive web app
         ↓
   Streamlit Cloud        ← Live public deployment
```

---

## 🗂️ Project Structure

```
ecommerce-analytics/
├── Data/
│   ├── olist_orders_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_customers_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   └── product_category_name_translation.csv
├── notebooks/
│   ├── 01_eda.ipynb                  ← Exploratory data analysis
│   ├── 02_duckdb_setup.ipynb         ← Database setup & loading
│   └── 03_market_basket.ipynb        ← Co-purchase analysis
├── dbt_project/
│   ├── dbt_project.yml               ← dbt configuration
│   └── models/ecommerce/
│       ├── stg_orders.sql            ← Layer 1: clean orders
│       ├── stg_order_details.sql     ← Layer 2: master order table
│       ├── stg_products.sql          ← Layer 3: products + categories
│       ├── customer_rfm.sql          ← Layer 4: RFM scoring
│       ├── product_performance.sql   ← Layer 5: product metrics
│       └── executive_summary.sql    ← Layer 6: top level KPIs
├── app/
│   ├── streamlit_app.py              ← Main dashboard (5 pages)
│   └── setup_db.py                   ← Auto database builder
└── requirements.txt
```

---

## 🔄 dbt SQL Pipeline — 6 Layers

This project uses dbt (data build tool) to transform raw CSV data into
analytics-ready tables inside DuckDB. Each model is a separate SQL file
with explicit dependencies resolved automatically by dbt.

### Layer 1 — `stg_orders.sql`
Cleans the orders table and extracts date features.
- Casts all timestamp columns to proper datetime types
- Extracts year, month, day of week, hour from purchase timestamp
- Calculates delivery days and delivery delay in days
- Flags late deliveries (delivered after estimated date)

### Layer 2 — `stg_order_details.sql`
Builds the master analytical table joining 5 raw tables.
- Joins orders + items + payments + reviews + customers
- Aggregates payments per order (sum of payment value)
- Filters to delivered orders only
- Single source of truth for all order-level analysis

### Layer 3 — `stg_products.sql`
Enriches product data with English category names.
- Joins products with category translation table
- Falls back to Portuguese name if English not available
- Calculates product volume from dimensions

### Layer 4 — `customer_rfm.sql`
Scores every customer on Recency, Frequency and Monetary value.
- Recency: days since last purchase vs max order date
- Frequency: number of distinct orders placed
- Monetary: total spend across all orders
- NTILE(5) scoring on each dimension
- 8 customer segments assigned based on RFM combination

### Layer 5 — `product_performance.sql`
Aggregates sales, pricing and satisfaction metrics per product.
- Revenue, order count, avg price per product
- Freight cost and freight as % of price
- Avg review score per product
- Late delivery rate per product

### Layer 6 — `executive_summary.sql`
Single-row business summary for dashboard KPI cards.
- Total orders, customers, revenue, AOV
- Avg review score and delivery performance
- Date range of the dataset

---

## 👥 RFM Customer Segmentation

RFM (Recency, Frequency, Monetary) is an industry-standard framework for
segmenting customers based on their purchase behaviour.

### How Scoring Works
Each customer receives a score of 1-5 on each dimension:
- **R Score** — 5 = purchased very recently, 1 = not purchased in a long time
- **F Score** — 5 = orders very frequently, 1 = rarely orders
- **M Score** — 5 = highest spender, 1 = lowest spender

### Segment Results

| Segment | Customers | Avg Spend | Avg Orders | Avg Recency |
|---|---|---|---|---|
| Champions | 22,176 | R$ 221.97 | 1.06 | 104 days |
| Loyal Customers | 19,524 | R$ 205.49 | 1.03 | 237 days |
| At Risk | 14,382 | R$ 233.60 | 1.07 | 353 days |
| Cant Lose Them | 13,250 | R$ 306.32 | 1.00 | 500 days |
| Lost | 9,757 | R$ 56.21 | 1.00 | 499 days |
| Recent Customers | 5,613 | R$ 207.77 | 1.00 | 203 days |
| Potential Loyalists | 5,071 | R$ 297.29 | 1.00 | 245 days |
| Need Attention | 3,698 | R$ 54.45 | 1.00 | 246 days |

### Key Insight
Champions (22,176 customers) represent the most valuable segment with
recent purchases and highest engagement. The Cant Lose Them segment
(13,250 customers) shows high average spend of R$ 306 but have not
purchased in over 500 days — prime reactivation targets.

---

## 🤝 Co-Purchase Analysis

### Methodology
Traditional Market Basket Analysis (Apriori algorithm) was attempted
but was not statistically viable because 90% of Olist orders are
single-category purchases — a meaningful finding in itself.

A manual co-purchase frequency analysis was implemented instead:
1. Filtered for multi-category orders (9,492 orders — 10% of total)
2. Generated all category pair combinations within each order
3. Counted co-occurrence frequency across all multi-item orders
4. Calculated support, confidence and lift for each pair

### Key Finding
> The 90% single-category purchase rate reveals significant untapped
> cross-sell potential. Olist customers rarely buy across categories
> in a single order, meaning bundling campaigns and cross-category
> recommendations have not been effectively implemented.

### Top Recommendations

| If Customer Buys | Recommend | Co-Purchases |
|---|---|---|
| bed_bath_table | furniture_decor | 70 |
| bed_bath_table | home_confort | 43 |
| furniture_decor | housewares | 24 |
| baby | toys | 19 |
| health_beauty | perfumery | 11 |

---

## 📱 Dashboard Pages

### 📈 Revenue Overview
- 5 KPI cards (revenue, orders, AOV, rating, late delivery rate)
- Monthly revenue trend with area chart
- Month-over-Month growth percentage
- Orders by day of week and hour of day
- Revenue and order share by payment type

### 👥 Customer Segments
- RFM segment KPI cards (Champions, Loyal, At Risk, Lost)
- Customer distribution pie chart by segment
- Avg spend per segment horizontal bar chart
- RFM scatter plot (Recency vs Monetary, sized by Frequency)
- Full segment summary statistics table

### 🛍️ Product Intelligence
- Top 15 categories by revenue and by orders
- Price vs Rating vs Revenue bubble chart (colored by late delivery %)
- Freight cost as % of price by category
- Category performance comparison

### 🤝 Recommendations
- Co-purchase analysis methodology explanation
- Top category pairs by co-purchase count
- Interactive category recommendation lookup
- Full co-purchase pairs table with metrics

### ⭐ Review Analytics
- Review score distribution
- Avg delivery days by review score (key correlation)
- Delivery delay distribution (early vs on-time vs late)
- Top 15 categories by avg rating
- Top 15 categories by late delivery rate

---

## 🔑 Key Insights

1. **November 2017 was peak revenue month** — aligns with Black Friday
   adoption in Brazil, generating highest single-month orders

2. **Late deliveries = low reviews** — categories with 15%+ late delivery
   rates score 0.5-1.0 points lower on average review scores

3. **Peak purchasing time is Monday at 16:00** — suggests targeted
   promotional campaigns on Monday afternoons could maximise conversion

4. **Credit card dominates at 73.9%** of all payments — instalment
   payment options are heavily used, suggesting price sensitivity

5. **bed_bath_table is the #1 revenue category** at R$ 1.69M — nearly
   double the second-place category

6. **90% single-category orders** — massive untapped cross-sell
   opportunity across the 73 product categories

---

## 🚀 Run Locally

### 1 — Clone the repo
```bash
git clone https://github.com/ishant8113/ecommerce-analytics.git
cd ecommerce-analytics
```

### 2 — Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### 4 — Download dataset
Download from [Kaggle — Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
and place all 9 CSV files inside the `Data/` folder.

### 5 — Run the app
```bash
streamlit run app/streamlit_app.py
```

The app automatically builds the database and all analytical tables
on first run (takes 2-3 minutes). Subsequent runs load instantly.

---

## 🛠️ Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| Data Storage | DuckDB | Embedded analytical database |
| SQL Pipeline | dbt-core + dbt-duckdb | Transformation models |
| Data Loading | Python + PyArrow | CSV → Parquet → DuckDB |
| EDA | Pandas, Matplotlib, Seaborn | Exploratory analysis |
| ML / Analytics | Scikit-learn, mlxtend | RFM + co-purchase |
| Dashboard | Streamlit + Plotly | Interactive web app |
| Deployment | Streamlit Cloud + GitHub | Live public URL |

---

## 📚 Dataset

**Olist Brazilian E-Commerce Public Dataset**
Real commercial data from Olist, the largest department store in
Brazilian marketplaces, containing 100,000 orders placed between
2016 and 2018 across multiple marketplaces in Brazil.

[View on Kaggle →](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

### Schema Relationships
```
orders ──────── customers     (customer_id)
orders ──────── items         (order_id)
orders ──────── payments      (order_id)
orders ──────── reviews       (order_id)
items  ──────── products      (product_id)
items  ──────── sellers       (seller_id)
products ─────── category     (product_category_name)
customers ────── geolocation  (zip_code_prefix)
```

---

## 👤 Author

**Ishant**
Data Analyst Portfolio Project
[GitHub →](https://github.com/ishant8113)