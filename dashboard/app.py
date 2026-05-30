"""
MergeMind — Hackathon Demo Dashboard

A real-time Streamlit dashboard that visualizes the AI Arbitration Engine
in action. It reads directly from MongoDB to show live ledger updates.
"""

import os
import pandas as pd
import streamlit as st
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

# Custom CSS for dark theme polish
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.title("🧠 MergeMind")
st.subheader("AI-Assisted Arbitration Engine & Programmable Ledger")

# Sidebar
with st.sidebar:
    st.header("System Status")
    st.success("🟢 Arbitration Agent Active")
    st.success("🟢 GitLab Webhook Connected")
    st.success("🟢 MongoDB Ledger Synced")
    
    st.divider()
    st.write("**Hackathon Demo Panel**")
    st.caption("Google Cloud Rapid Agent Hackathon 2026")
    
    # TODO: Add interactive trigger for fake webhooks if needed

# Main Dashboard
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 💸 Live Streaming Ledger")
    
    # Fetch recent ledger entries
    ledger_docs = list(db.streaming_ledger.find().sort("timestamp", -1).limit(20))
    if ledger_docs:
        df = pd.DataFrame(ledger_docs)
        # Drop _id for cleaner display
        if "_id" in df.columns:
            df = df.drop(columns=["_id"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No ledger transactions found yet. Waiting for evaluations...")
    
    st.markdown("### 📊 Budget Burndown")
    # Fetch budget pool history (simplified for hackathon to show current remaining)
    pool = db.budget_pools.find_one({"pool_id": "demo_pool_1"})
    if pool:
        st.metric(label="Current Remaining Budget", value=f"${pool.get('remaining_budget', 0):,.2f}")
        # In a real app we'd query history, here we just show the snapshot
    else:
        st.warning("Budget pool not seeded. Run `python scripts/seed_budget.py`")

with col2:
    st.markdown("### 🔍 Recent Evaluation")
    
    if ledger_docs:
        latest = ledger_docs[0]
        with st.container(border=True):
            st.markdown(f"**MR #{latest.get('merge_request_id', 'Unknown')}**")
            st.write(f"Author: `@user`")
            
            st.metric(label="Impact Score", value=f"{latest.get('impact_score', 0)} / 100")
            st.metric(label="Payment Streamed", value=f"${latest.get('payment_amount', 0):.2f}")
            
            st.divider()
            st.markdown("**Agent Verdict:**")
            st.caption(latest.get('evaluation_summary', 'No summary provided.'))
            
            trace_id = latest.get('trace_id')
            if trace_id:
                st.write(f"Arize Trace ID: `{trace_id}`")
    else:
        st.info("Waiting for first evaluation...")
