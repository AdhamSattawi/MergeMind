"""
MergeMind — Hackathon Demo Dashboard

A premium, real-time Streamlit dashboard that visualizes the AI Arbitration Engine
in action. It reads directly from MongoDB to show live ledger updates.
"""

import os
import pandas as pd
import streamlit as st
import altair as alt
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Configure the page
st.set_page_config(
    page_title="MergeMind Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_resource
def get_db():
    uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/mergemind")
    client = MongoClient(uri)
    return client.get_database("mergemind")

db = get_db()

# Premium Custom CSS for dark theme polish
st.markdown(
    """
    <style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        font-family: 'Inter', sans-serif;
    }
    /* Headers */
    h1, h2, h3 {
        color: #38bdf8 !important;
        font-weight: 700 !important;
    }
    /* Metric Cards styling via Streamlit is limited, but we can target specific elements */
    [data-testid="stMetricValue"] {
        color: #10b981 !important;
        font-weight: 800 !important;
        font-size: 2.5rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 1.1rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #334155;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    /* Custom container borders */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 15px;
        border: 1px solid rgba(56, 189, 248, 0.2) !important;
        background: rgba(30, 41, 59, 0.5) !important;
        backdrop-filter: blur(10px);
        padding: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/GitLab_logo.svg/512px-GitLab_logo.svg.png", width=50)
    st.title("System Status")
    st.markdown("---")
    st.markdown("🟢 **Arbitration Agent:** `Active`")
    st.markdown("🟢 **GitLab Webhook:** `Connected`")
    st.markdown("🟢 **MongoDB Ledger:** `Synced`")
    st.markdown("🟢 **Elastic Indexer:** `Connected`")
    
    st.markdown("---")
    st.markdown("**Hackathon Demo Panel**")
    st.caption("Google Cloud Rapid Agent Hackathon 2026")

# Header
st.markdown("<h1 style='text-align: center; font-size: 3.5rem; margin-bottom: 0;'>🧠 MergeMind</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 1.5rem; color: #94a3b8; margin-bottom: 2rem;'>AI-Assisted Arbitration Engine & Programmable Ledger</p>", unsafe_allow_html=True)

# Main Dashboard Container (Auto-refreshes every 5 seconds)
@st.fragment(run_every="5s")
def live_dashboard():
    # Fetch Data
    ledger_docs = list(db.streaming_ledger.find().sort("timestamp", -1).limit(50))
    pool = db.budget_pools.find_one({"pool_id": "demo_pool_1"})
    
    col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
    
    with col_metrics1:
        total_evals = db.streaming_ledger.count_documents({})
        st.metric(label="Total MRs Evaluated", value=total_evals)
        
    with col_metrics2:
        if pool:
            st.metric(label="Current Escrow Budget", value=f"${pool.get('remaining_budget', 0):,.2f}")
        else:
            st.metric(label="Current Escrow Budget", value="Not Seeded")
            
    with col_metrics3:
        if ledger_docs:
            total_paid = sum(doc.get("payment_amount", 0) for doc in db.streaming_ledger.find())
            st.metric(label="Total Bounties Streamed", value=f"${total_paid:,.2f}")
        else:
            st.metric(label="Total Bounties Streamed", value="$0.00")

    st.markdown("---")
    
    col_main, col_side = st.columns([2.5, 1.5])
    
    with col_main:
        st.markdown("### 💸 Live Streaming Ledger")
        
        if ledger_docs:
            df = pd.DataFrame(ledger_docs)
            if "_id" in df.columns:
                df = df.drop(columns=["_id"])
            
            # Formatting the dataframe
            display_df = df.copy()
            if "timestamp" in display_df.columns:
                display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime('%Y-%m-%d %H:%M:%S')
            if "payment_amount" in display_df.columns:
                display_df["payment_amount"] = display_df["payment_amount"].apply(lambda x: f"${x:.2f}")
            
            # Select columns to show
            cols_to_show = ["timestamp", "merge_request_id", "author_username", "impact_score", "payment_amount"]
            cols_present = [c for c in cols_to_show if c in display_df.columns]
            
            st.dataframe(
                display_df[cols_present], 
                use_container_width=True,
                hide_index=True
            )
            
            # Add a visualization using Altair
            st.markdown("### 📈 Impact Score Trend")
            if "timestamp" in df.columns and "impact_score" in df.columns:
                chart_df = df[["timestamp", "impact_score"]].copy()
                chart_df["timestamp"] = pd.to_datetime(chart_df["timestamp"])
                chart_df = chart_df.sort_values("timestamp")
                
                chart = alt.Chart(chart_df).mark_area(
                    line={'color':'#38bdf8'},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#38bdf8', offset=0),
                               alt.GradientStop(color='rgba(56,189,248,0)', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('timestamp:T', title='Time'),
                    y=alt.Y('impact_score:Q', title='Impact Score', scale=alt.Scale(domain=[0, 100])),
                    tooltip=['timestamp', 'impact_score']
                ).properties(height=250)
                
                st.altair_chart(chart, use_container_width=True)
                
        else:
            st.info("No ledger transactions found yet. Waiting for AI evaluations...")

    with col_side:
        st.markdown("### 🔍 Latest AI Verdict")
        
        if ledger_docs:
            latest = ledger_docs[0]
            with st.container(border=True):
                st.markdown(f"<h3 style='margin-top:0;'>MR #{latest.get('merge_request_id', 'Unknown')}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Author:** `@{latest.get('author_username', 'developer')}`")
                
                score = latest.get('impact_score', 0)
                color = "#10b981" if score > 50 else "#f59e0b" if score > 20 else "#ef4444"
                
                st.markdown(f"""
                <div style='background: {color}20; padding: 15px; border-radius: 10px; border-left: 5px solid {color}; margin: 15px 0;'>
                    <h2 style='margin:0; color: {color} !important;'>Score: {score}/100</h2>
                    <h4 style='margin:0; color: #cbd5e1;'>Payment: ${latest.get('payment_amount', 0):.2f}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("**📝 Agent Reasoning:**")
                st.info(latest.get('evaluation_summary', 'No summary provided.'))
                
                trace_id = latest.get('trace_id')
                if trace_id:
                    st.caption(f"🛡️ Arize Trace ID: `{trace_id}`")
        else:
            st.warning("Waiting for the first evaluation payload to arrive...")

# Render the live fragment
live_dashboard()
