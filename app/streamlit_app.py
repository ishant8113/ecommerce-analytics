import os
import sys
import duckdb
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'data', 'ecommerce.db')
# Auto setup if DB doesn't exist
# ─────────────────────────────────────────
# AUTO SETUP — checks all tables exist
# ─────────────────────────────────────────
def needs_setup():
    if not os.path.exists(DB_PATH):
        return True
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        tables = con.execute("SHOW TABLES").df()['name'].tolist()
        con.close()
        required = ['executive_summary', 'stg_order_details',
                    'customer_rfm', 'product_performance', 'copurchase_rules', 'cohort_retention']
        return not all(t in tables for t in required)
    except:
        return True

if needs_setup():
    st.info("⏳ Setting up database — takes 2-3 minutes...")
    os.makedirs(os.path.join(BASE_DIR, 'data'), exist_ok=True)
    sys.path.insert(0, BASE_DIR)
    try:
        from app.setup_db import setup
        setup()
        st.success("✅ Setup complete!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Setup failed: {e}")
        st.stop()
    
st.set_page_config(
    page_title = "E-Commerce Analytics",
    page_icon  = "🛒",
    layout     = "wide"
)

# ─────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────
@st.cache_data
def load_data():
    con = duckdb.connect(DB_PATH, read_only=True)
    try:
        exec_df   = con.execute("SELECT * FROM executive_summary").df()
        orders_df = con.execute("SELECT * FROM stg_order_details").df()
        rfm_df    = con.execute("SELECT * FROM customer_rfm").df()
        prod_df   = con.execute("SELECT * FROM product_performance").df()
        pairs_df  = con.execute("SELECT * FROM copurchase_rules").df()
    except Exception as e:
        # Show which tables exist
        tables = con.execute("SHOW TABLES").df()
        st.error(f"Missing table error: {e}")
        st.write("Tables that exist:", tables)
        con.close()
        st.stop()
    con.close()
    return exec_df, orders_df, rfm_df, prod_df, pairs_df

exec_df, orders_df, rfm_df, prod_df, pairs_df = load_data()

# ─────────────────────────────────────────
#  LOAD COHORT
# ─────────────────────────────────────────
@st.cache_data
def load_cohort():
    con = duckdb.connect(DB_PATH, read_only=True)
    df  = con.execute("SELECT * FROM cohort_retention").df()
    con.close()
    return df
cohort_df = load_cohort() 
# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
st.sidebar.image(
    "https://img.icons8.com/fluency/96/shopping-cart.png", width=60
)
st.sidebar.title("E-Commerce Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigate",
    [
        "📈 Revenue Overview",
        "👥 Customer Segments",
        "🛍️ Product Intelligence",
        "🤝 Recommendations",
        "⭐ Review Analytics",
        "🔄 Cohort Retention",         
        "💡 Business Recommendations" 
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"""
**Dataset:** Olist Brazilian E-Commerce
**Orders:** {exec_df['total_orders'].iloc[0]:,}
**Revenue:** R$ {exec_df['total_revenue'].iloc[0]:,.0f}
**Period:** Sep 2016 — Aug 2018
""")

# ─────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────
def kpi(label, value, delta=None, color="#5C9BD4"):
    st.markdown(
        f"""
        <div style="background:#f8f9fa;border-left:5px solid {color};
                    padding:16px 20px;border-radius:8px;margin-bottom:8px">
            <div style="font-size:12px;color:#666">{label}</div>
            <div style="font-size:26px;font-weight:700;color:#222">{value}</div>
            {"<div style='font-size:11px;color:#888'>"+delta+"</div>" if delta else ""}
        </div>
        """,
        unsafe_allow_html=True
    )

# ═══════════════════════════════════════════════════════
# PAGE 1 — REVENUE OVERVIEW
# ═══════════════════════════════════════════════════════
if page == "📈 Revenue Overview":
    st.title("📈 Revenue Overview")
    st.markdown("Full picture of revenue trends, order volumes and growth patterns.")
    st.markdown("---")

    # KPIs
    col1,col2,col3,col4,col5 = st.columns(5)
    with col1: kpi("Total Revenue",
                   f"R$ {exec_df['total_revenue'].iloc[0]:,.0f}",
                   color="#5C9BD4")
    with col2: kpi("Total Orders",
                   f"{exec_df['total_orders'].iloc[0]:,}",
                   color="#5CB85C")
    with col3: kpi("Avg Order Value",
                   f"R$ {exec_df['avg_order_value'].iloc[0]:,.2f}",
                   color="#F0AD4E")
    with col4: kpi("Avg Review Score",
                   f"{exec_df['avg_review_score'].iloc[0]:.2f} / 5.0",
                   color="#9B59B6")
    with col5: kpi("Late Deliveries",
                   f"{exec_df['late_delivery_pct'].iloc[0]:.1f}%",
                   color="#E07B54")

    st.markdown("---")

    # Monthly revenue trend
    st.subheader("Monthly Revenue Trend")

    orders_df['order_purchase_timestamp'] = pd.to_datetime(
        orders_df['order_purchase_timestamp'], errors='coerce'
    )
    orders_df['order_yearmon'] = (
        orders_df['order_purchase_timestamp']
        .dt.to_period('M').astype(str)
    )

    monthly = (
        orders_df.groupby('order_yearmon')
        .agg(revenue=('payment_value','sum'),
             orders =('order_id','nunique'))
        .reset_index()
        .sort_values('order_yearmon')
        .iloc[1:-1]   # remove incomplete months
    )
    monthly['mom_growth'] = monthly['revenue'].pct_change() * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly['order_yearmon'],
        y=monthly['revenue'],
        mode='lines+markers',
        name='Revenue',
        line=dict(color='#5C9BD4', width=2.5),
        fill='tozeroy',
        fillcolor='rgba(92,155,212,0.1)'
    ))
    fig.update_layout(
        height=380,
        xaxis_title='Month',
        yaxis_title='Revenue (R$)',
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # MoM growth + Orders per month
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Month-over-Month Growth %")
        colors = ['#5CB85C' if x >= 0 else '#E07B54'
                  for x in monthly['mom_growth'].fillna(0)]
        fig = go.Figure(go.Bar(
            x=monthly['order_yearmon'],
            y=monthly['mom_growth'].fillna(0),
            marker_color=colors
        ))
        fig.update_layout(height=320,
                          xaxis_tickangle=-45,
                          yaxis_title='MoM Growth %')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Orders per Month")
        fig = px.bar(
            monthly, x='order_yearmon', y='orders',
            color='orders',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=320,
                          xaxis_tickangle=-45,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Orders by day and hour
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Orders by Day of Week")
        dow_order = ['Monday','Tuesday','Wednesday',
                     'Thursday','Friday','Saturday','Sunday']
        dow = (orders_df['order_dow']
               .value_counts()
               .reindex(dow_order)
               .reset_index())
        dow.columns = ['day','count']
        fig = px.bar(dow, x='day', y='count',
                     color='count',
                     color_continuous_scale='Blues')
        fig.update_layout(height=320,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Orders by Hour of Day")
        orders_df['order_hour'] = pd.to_datetime(
            orders_df['order_purchase_timestamp'], errors='coerce'
        ).dt.hour
        hour = (orders_df['order_hour']
                .value_counts()
                .sort_index()
                .reset_index())
        hour.columns = ['hour','count']
        fig = px.bar(hour, x='hour', y='count',
                     color='count',
                     color_continuous_scale='Oranges')
        fig.update_layout(height=320,
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    # Payment methods
    st.subheader("Revenue by Payment Type")
    pay = (
        orders_df.groupby('payment_type')
        .agg(revenue=('payment_value','sum'),
             orders =('order_id','nunique'))
        .reset_index()
        .sort_values('revenue', ascending=False)
    )
    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(pay, names='payment_type', values='orders',
                     hole=0.4, title='Orders by Payment Type',
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig = px.bar(pay, x='payment_type', y='revenue',
                     color='revenue',
                     color_continuous_scale='Blues',
                     title='Revenue by Payment Type')
        fig.update_layout(height=350, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════
# PAGE 2 — CUSTOMER SEGMENTS
# ═══════════════════════════════════════════════════════
elif page == "👥 Customer Segments":
    st.title("👥 Customer Segments — RFM Analysis")
    st.markdown("Customers segmented by Recency, Frequency and Monetary value.")
    st.markdown("---")

    # Segment KPIs
    seg_counts = rfm_df['rfm_segment'].value_counts()
    total_custs = len(rfm_df)

    col1,col2,col3,col4 = st.columns(4)
    with col1:
        n = seg_counts.get('Champions', 0)
        kpi("Champions", f"{n:,}",
            f"{n/total_custs*100:.1f}% of customers", "#5CB85C")
    with col2:
        n = seg_counts.get('Loyal Customers', 0)
        kpi("Loyal Customers", f"{n:,}",
            f"{n/total_custs*100:.1f}% of customers", "#5C9BD4")
    with col3:
        n = seg_counts.get('At Risk', 0)
        kpi("At Risk", f"{n:,}",
            f"{n/total_custs*100:.1f}% of customers", "#F0AD4E")
    with col4:
        n = seg_counts.get('Lost', 0)
        kpi("Lost", f"{n:,}",
            f"{n/total_custs*100:.1f}% of customers", "#E07B54")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Customer Distribution by Segment")
        seg_df = rfm_df['rfm_segment'].value_counts().reset_index()
        seg_df.columns = ['Segment','Customers']
        fig = px.pie(
            seg_df, names='Segment', values='Customers',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Avg Spend by Segment")
        seg_spend = (
            rfm_df.groupby('rfm_segment')
            .agg(avg_spend   =('monetary',  'mean'),
                 avg_orders  =('frequency', 'mean'),
                 customers   =('customer_unique_id','count'))
            .reset_index()
            .sort_values('avg_spend', ascending=True)
        )
        fig = px.bar(
            seg_spend, x='avg_spend', y='rfm_segment',
            orientation='h',
            color='avg_spend',
            color_continuous_scale='Greens',
            text='avg_spend'
        )
        fig.update_traces(texttemplate='R$ %{text:.0f}',
                          textposition='outside')
        fig.update_layout(height=420,
                          coloraxis_showscale=False,
                          xaxis_title='Avg Spend (R$)',
                          yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

    # RFM scatter
    st.subheader("RFM Map — Recency vs Monetary (by Segment)")
    sample = rfm_df.sample(min(3000, len(rfm_df)), random_state=42)
    fig = px.scatter(
        sample,
        x='recency_days',
        y='monetary',
        color='rfm_segment',
        size='frequency',
        hover_data=['customer_state', 'frequency'],
        color_discrete_sequence=px.colors.qualitative.Set2,
        labels={
            'recency_days':'Days Since Last Order',
            'monetary'    :'Total Spend (R$)',
            'rfm_segment' :'Segment'
        }
    )
    fig.update_layout(height=480)
    st.plotly_chart(fig, use_container_width=True)

    # Segment stats table
    st.subheader("Segment Summary Table")
    seg_table = (
        rfm_df.groupby('rfm_segment')
        .agg(
            customers      =('customer_unique_id','count'),
            avg_spend      =('monetary',          'mean'),
            avg_orders     =('frequency',         'mean'),
            avg_recency    =('recency_days',      'mean'),
            total_revenue  =('monetary',          'sum')
        )
        .round(2)
        .reset_index()
        .sort_values('avg_spend', ascending=False)
    )
    seg_table.columns = ['Segment','Customers','Avg Spend',
                         'Avg Orders','Avg Recency Days','Total Revenue']
    st.dataframe(seg_table, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════
# PAGE 3 — PRODUCT INTELLIGENCE
# ═══════════════════════════════════════════════════════
elif page == "🛍️ Product Intelligence":
    st.title("🛍️ Product Intelligence")
    st.markdown("Category performance, pricing, freight and review analysis.")
    st.markdown("---")

    # Category aggregation
    cat_df = (
        prod_df.groupby('category')
        .agg(
            total_orders   =('total_orders',   'sum'),
            total_revenue  =('total_revenue',  'sum'),
            avg_price      =('avg_price',      'mean'),
            avg_freight    =('avg_freight',    'mean'),
            avg_rating     =('avg_rating',     'mean'),
            late_pct       =('late_delivery_pct','mean')
        )
        .reset_index()
        .dropna(subset=['category'])
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top 15 Categories by Revenue")
        top_rev = cat_df.nlargest(15, 'total_revenue')
        fig = px.bar(
            top_rev.sort_values('total_revenue'),
            x='total_revenue', y='category',
            orientation='h',
            color='total_revenue',
            color_continuous_scale='Blues',
            text='total_revenue'
        )
        fig.update_traces(
            texttemplate='R$ %{text:,.0f}',
            textposition='outside'
        )
        fig.update_layout(height=520,
                          coloraxis_showscale=False,
                          xaxis_title='Revenue (R$)',
                          yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Top 15 Categories by Orders")
        top_ord = cat_df.nlargest(15, 'total_orders')
        fig = px.bar(
            top_ord.sort_values('total_orders'),
            x='total_orders', y='category',
            orientation='h',
            color='total_orders',
            color_continuous_scale='Oranges',
            text='total_orders'
        )
        fig.update_traces(texttemplate='%{text:,}',
                          textposition='outside')
        fig.update_layout(height=520,
                          coloraxis_showscale=False,
                          xaxis_title='Number of Orders',
                          yaxis_title='')
        st.plotly_chart(fig, use_container_width=True)

    # Price vs Rating bubble chart
    st.subheader("Price vs Rating vs Revenue — Category Bubble Chart")
    bubble = cat_df[cat_df['total_orders'] >= 100].dropna()
    fig = px.scatter(
        bubble,
        x='avg_price',
        y='avg_rating',
        size='total_revenue',
        color='late_pct',
        hover_name='category',
        color_continuous_scale='RdYlGn_r',
        labels={
            'avg_price' :'Avg Price (R$)',
            'avg_rating':'Avg Review Score',
            'late_pct'  :'Late Delivery %'
        }
    )
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

    # Freight analysis
    st.subheader("Freight Cost as % of Price — Top 15 Categories")
    freight_df = cat_df.copy()
    freight_df['freight_pct'] = (
        freight_df['avg_freight'] /
        freight_df['avg_price'] * 100
    ).round(1)
    top_freight = freight_df.nlargest(15, 'freight_pct')

    fig = px.bar(
        top_freight.sort_values('freight_pct'),
        x='freight_pct', y='category',
        orientation='h',
        color='freight_pct',
        color_continuous_scale='Reds',
        text='freight_pct'
    )
    fig.update_traces(texttemplate='%{text:.1f}%',
                      textposition='outside')
    fig.update_layout(height=500,
                      coloraxis_showscale=False,
                      xaxis_title='Freight as % of Price',
                      yaxis_title='')
    st.plotly_chart(fig, use_container_width=True)

# ═══════════════════════════════════════════════════════
# PAGE 4 — RECOMMENDATIONS
# ═══════════════════════════════════════════════════════
elif page == "🤝 Recommendations":
    st.title("🤝 Product Recommendations")
    st.markdown("Co-purchase analysis — categories frequently bought together.")
    st.markdown("---")

    # Key finding callout
    st.info(
        "💡 **Key Finding:** 90% of Olist orders are single-category purchases. "
        "This analysis identifies the 10% of multi-category orders to surface "
        "cross-sell opportunities. Low lift scores confirm significant untapped "
        "bundling potential across the platform."
    )

    # KPIs
    col1, col2, col3 = st.columns(3)
    with col1: kpi("Total Orders Analysed",
                   f"{95146:,}", color="#5C9BD4")
    with col2: kpi("Multi-Category Orders",
                   "9,492 (10%)",
                   "Cross-sell opportunity", "#F0AD4E")
    with col3: kpi("Co-Purchase Pairs Found",
                   f"{len(pairs_df):,}",
                   "Recommendable category pairs", "#5CB85C")

    st.markdown("---")

    # Top pairs bar chart
    st.subheader("Top Category Pairs by Co-Purchase Count")
    top_pairs = pairs_df.head(15).copy()
    top_pairs['pair'] = (top_pairs['category_a'] +
                         ' + ' +
                         top_pairs['category_b'])

    fig = px.bar(
        top_pairs.sort_values('co_purchases'),
        x='co_purchases', y='pair',
        orientation='h',
        color='co_purchases',
        color_continuous_scale='Blues',
        text='co_purchases',
        labels={'co_purchases':'Co-Purchase Count',
                'pair'        :'Category Pair'}
    )
    fig.update_traces(texttemplate='%{text:,}',
                      textposition='outside')
    fig.update_layout(height=500,
                      coloraxis_showscale=False,
                      yaxis_title='')
    st.plotly_chart(fig, use_container_width=True)

    # Interactive recommendation lookup
    st.subheader("🔍 Category Recommendation Lookup")
    st.markdown("Select a category to see what customers also buy:")

    all_cats = sorted(pairs_df['category_a'].unique().tolist())
    selected = st.selectbox("Select a product category:", all_cats)

    recs = pairs_df[
        pairs_df['category_a'] == selected
    ].sort_values('co_purchases', ascending=False)

    if len(recs) > 0:
        st.markdown(f"**Customers who buy `{selected}` also buy:**")
        for _, row in recs.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"🛍️ **{row['category_b']}**")
            with col2:
                st.metric("Co-Purchases", f"{int(row['co_purchases']):,}")
            with col3:
                st.metric("Confidence", f"{row['confidence']*100:.1f}%")
    else:
        st.warning(f"No co-purchase data found for `{selected}`")

    # Full pairs table
    st.subheader("All Co-Purchase Pairs")
    display_df = pairs_df.copy()
    display_df.columns = ['If Customer Buys','Recommend',
                          'Co-Purchases','Support %',
                          'Confidence','Lift']
    st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True
)

# ═══════════════════════════════════════════════════════
# PAGE 5 — REVIEW ANALYTICS
# ═══════════════════════════════════════════════════════
elif page == "⭐ Review Analytics":
    st.title("⭐ Review Analytics")
    st.markdown("Customer satisfaction, delivery performance and rating patterns.")
    st.markdown("---")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1: kpi("Avg Review Score",
                   f"{exec_df['avg_review_score'].iloc[0]:.2f} / 5.0",
                   color="#5CB85C")
    with col2: kpi("Avg Delivery Days",
                   f"{exec_df['avg_delivery_days'].iloc[0]:.1f} days",
                   color="#5C9BD4")
    with col3: kpi("Late Delivery Rate",
                   f"{exec_df['late_delivery_pct'].iloc[0]:.1f}%",
                   color="#E07B54")
    with col4:
        five_star = (
            orders_df['review_score'] == 5
        ).sum() / orders_df['review_score'].notna().sum() * 100
        kpi("5-Star Reviews",
            f"{five_star:.1f}%", color="#F0AD4E")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Review Score Distribution")
        score_counts = (
            orders_df['review_score']
            .value_counts()
            .sort_index()
            .reset_index()
        )
        score_counts.columns = ['score','count']
        fig = px.bar(
            score_counts, x='score', y='count',
            color='score',
            color_continuous_scale='RdYlGn',
            text='count'
        )
        fig.update_traces(texttemplate='%{text:,}',
                          textposition='outside')
        fig.update_layout(height=380,
                          coloraxis_showscale=False,
                          xaxis_title='Review Score',
                          yaxis_title='Number of Reviews')
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Avg Delivery Days by Review Score")
        del_by_score = (
            orders_df.groupby('review_score')['delivery_days']
            .mean()
            .reset_index()
        )
        del_by_score.columns = ['score','avg_delivery_days']
        fig = px.bar(
            del_by_score, x='score', y='avg_delivery_days',
            color='avg_delivery_days',
            color_continuous_scale='RdYlGn_r',
            text='avg_delivery_days'
        )
        fig.update_traces(texttemplate='%{text:.1f}d',
                          textposition='outside')
        fig.update_layout(height=380,
                          coloraxis_showscale=False,
                          xaxis_title='Review Score',
                          yaxis_title='Avg Delivery Days')
        st.plotly_chart(fig, use_container_width=True)

    # Delivery delay distribution
    st.subheader("Delivery Delay Distribution")
    delay_data = orders_df['delivery_delay_days'].dropna().clip(-10, 30)
    fig = px.histogram(
        delay_data, nbins=50,
        color_discrete_sequence=['#5C9BD4'],
        labels={'value':'Delay (days)'},
        title='Negative = Early | Zero = On Time | Positive = Late'
    )
    fig.add_vline(x=0, line_color='red',
                  line_dash='dash', line_width=2,
                  annotation_text='On Time')
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

    # Rating by category
    st.subheader("Review Score by Top 15 Categories")
    cat_rating = (
        prod_df.groupby('category')['avg_rating']
        .mean()
        .reset_index()
        .dropna()
        .nlargest(15, 'avg_rating')
        .sort_values('avg_rating')
    )
    fig = px.bar(
        cat_rating,
        x='avg_rating', y='category',
        orientation='h',
        color='avg_rating',
        color_continuous_scale='RdYlGn',
        text='avg_rating',
        range_x=[3.5, 5.0]
    )
    fig.update_traces(texttemplate='%{text:.2f}',
                      textposition='outside')
    fig.update_layout(height=500,
                      coloraxis_showscale=False,
                      xaxis_title='Avg Review Score',
                      yaxis_title='')
    st.plotly_chart(fig, use_container_width=True)

    # Late delivery by category
    st.subheader("Late Delivery Rate by Category (Top 15 Worst)")
    late_cat = (
        prod_df.groupby('category')['late_delivery_pct']
        .mean()
        .reset_index()
        .dropna()
        .nlargest(15, 'late_delivery_pct')
        .sort_values('late_delivery_pct')
    )
    fig = px.bar(
        late_cat,
        x='late_delivery_pct', y='category',
        orientation='h',
        color='late_delivery_pct',
        color_continuous_scale='Reds',
        text='late_delivery_pct'
    )
    fig.update_traces(texttemplate='%{text:.1f}%',
                      textposition='outside')
    fig.update_layout(height=500,
                      coloraxis_showscale=False,
                      xaxis_title='Late Delivery %',
                      yaxis_title='')
    st.plotly_chart(fig, use_container_width=True)
    
    
# ═══════════════════════════════════════════════════════
# PAGE 5 — COHORT RETENTION
# ═══════════════════════════════════════════════════════
elif page == "🔄 Cohort Retention":
    st.title("🔄 Cohort Retention Analysis")
    st.markdown("Track what % of customers return month after month.")
    st.markdown("---")

    cohort_df = load_cohort()

    st.info(
        "📌 Each row = group of customers who made their **first purchase** "
        "in that month. Each column = % who came back N months later."
    )

    st.subheader("Monthly Retention Heatmap")
    numeric_cols = [c for c in cohort_df.columns if c != 'cohort_month']
    display_cols = [c for c in numeric_cols if int(c) <= 12]

    plot_df = cohort_df.set_index('cohort_month')[display_cols]

    fig = px.imshow(
        plot_df,
        color_continuous_scale='YlOrRd_r',
        text_auto='.1f',
        aspect='auto',
        labels={'color':'Retention %',
                'x':'Months Since First Purchase',
                'y':'Cohort Month'}
    )
    fig.update_layout(height=550)
    st.plotly_chart(fig, use_container_width=True)

    # Avg retention curve
    st.subheader("Average Retention Curve")
    avg_ret = plot_df.mean().reset_index()
    avg_ret.columns = ['month','retention_pct']
    avg_ret['month'] = avg_ret['month'].astype(int)

    fig = px.line(
        avg_ret, x='month', y='retention_pct',
        markers=True,
        color_discrete_sequence=['#E07B54'],
        labels={'month':'Months Since First Purchase',
                'retention_pct':'Avg Retention %'}
    )
    fig.update_layout(height=380)
    st.plotly_chart(fig, use_container_width=True)

    # Key stats
    col1, col2, col3 = st.columns(3)
    with col1:
        kpi("Month 1 Retention",
            f"{plot_df['1'].mean():.1f}%",
            "Avg across all cohorts", "#E07B54")
    with col2:
        kpi("Month 3 Retention",
            f"{plot_df['3'].mean():.1f}%",
            "Avg across all cohorts", "#F0AD4E")
    with col3:
        kpi("Month 6 Retention",
            f"{plot_df['6'].mean():.1f}%",
            "Avg across all cohorts", "#5C9BD4")

# ═══════════════════════════════════════════════════════
# PAGE 5 — BUSINESS RECOMMENDATIONS
# ═══════════════════════════════════════════════════════
elif page == "💡 Business Recommendations":
    st.title("💡 Business Recommendations")
    st.markdown(
        "Data-driven actions for Olist based on analysis findings."
    )
    st.markdown("---")

    recs = [
        {
            "icon"    : "🚚",
            "title"   : "Reduce Late Deliveries to Protect Revenue",
            "finding" : "7.91% late delivery rate. 1-star reviews average 21 days delivery vs 10 days for 5-star reviews.",
            "action"  : "Identify top 20 seller-carrier combinations driving most delays. Implement SLA penalties for carriers exceeding 15-day delivery. Target: reduce late rate from 7.91% to under 5%.",
            "impact"  : "Protecting ~7,600 customer relationships per year. Each saved customer worth avg R$ 200 LTV = R$ 1.52M revenue protected.",
            "color"   : "#E07B54"
        },
        {
            "icon"    : "🎯",
            "title"   : "Reactivate Cant Lose Them Segment",
            "finding" : "13,250 high-value customers (avg R$ 306 spend) inactive for 500+ days.",
            "action"  : "Launch personalised email campaign with 15% discount and 30-day expiry. A/B test 3 variants: discount only vs discount + loyalty points vs free shipping.",
            "impact"  : "Even 10% reactivation = 1,325 customers × R$ 306 = R$ 405,450 recovered revenue.",
            "color"   : "#F0AD4E"
        },
        {
            "icon"    : "🛍️",
            "title"   : "Launch Cross-Category Bundling Campaign",
            "finding" : "90% of orders are single-category. Only 9,492 of 95,146 orders (10%) contain multiple categories.",
            "action"  : "Create product bundles for top co-purchase pairs: bed_bath_table + furniture_decor, baby + toys, health_beauty + perfumery. Offer 5-10% bundle discount at checkout.",
            "impact"  : "Increasing multi-category rate from 10% to 15% = 4,757 additional cross-sell orders at avg R$ 200 = R$ 951,400 additional revenue.",
            "color"   : "#5CB85C"
        },
        {
            "icon"    : "📅",
            "title"   : "Maximise Monday Afternoon Promotions",
            "finding" : "Peak order time is Monday at 16:00. Highest order volume day is Monday.",
            "action"  : "Schedule flash sales, push notifications and email campaigns to land Monday between 14:00-17:00. Avoid Friday/weekend promotions which show lowest conversion.",
            "impact"  : "Shifting 5% of off-peak orders to peak windows = better inventory planning and potentially 3-5% conversion uplift.",
            "color"   : "#9B59B6"
        },
        {
            "icon"    : "⭐",
            "title"   : "Invest in High-Revenue Low-Rating Categories",
            "finding" : "bed_bath_table generates R$ 1.69M revenue but avg rating of only 3.90 — below platform average of 4.08.",
            "action"  : "Audit top 50 sellers in bed_bath_table category. Implement seller quality score. Remove sellers with 3+ consecutive months below 3.5 rating. Incentivise top-rated sellers with lower commission.",
            "impact"  : "Improving bed_bath_table rating from 3.90 to 4.10 (platform avg) would likely reduce churn in this category and protect R$ 1.69M revenue base.",
            "color"   : "#5C9BD4"
        },
    ]

    for rec in recs:
        st.markdown(
            f"""
            <div style="border-left: 5px solid {rec['color']};
                        background: #f8f9fa;
                        padding: 16px 20px;
                        border-radius: 8px;
                        margin-bottom: 16px">
                <div style="font-size:18px;font-weight:700;
                            color:#222;margin-bottom:8px">
                    {rec['icon']} {rec['title']}
                </div>
                <div style="font-size:13px;color:#555;
                            margin-bottom:6px">
                    <b>📊 Finding:</b> {rec['finding']}
                </div>
                <div style="font-size:13px;color:#555;
                            margin-bottom:6px">
                    <b>🎯 Action:</b> {rec['action']}
                </div>
                <div style="font-size:13px;color:#2E7D32;
                            font-weight:600">
                    💰 Impact: {rec['impact']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )