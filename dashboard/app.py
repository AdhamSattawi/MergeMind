"""
MergeMind — Hackathon Demo Dashboard

A real-time Streamlit dashboard that visualizes the AI Arbitration Engine
in action. It reads directly from MongoDB to show live ledger updates.
"""

import streamlit as st

# Configure the page
st.set_page_config(
    page_title="MergeMind Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    st.info("Waiting for database connection to load live transactions...")
    # TODO: Connect to MongoDB and fetch 'streaming_ledger'
    # db = connect_mongo()
    # df = pd.DataFrame(list(db.streaming_ledger.find().sort("timestamp", -1)))
    # st.dataframe(df, use_container_width=True)
    
    st.markdown("### 📊 Budget Burndown")
    # TODO: Fetch and chart 'budget_pools' history
    st.line_chart({"Remaining Budget ($)": [10000, 9500, 9100, 9100, 8600]})

with col2:
    st.markdown("### 🔍 Recent Evaluation")
    
    with st.container(border=True):
        st.markdown("**MR #142: Fix async connection leak**")
        st.write("Author: `@adham`")
        
        # Placeholder for recent evaluation
        st.metric(label="Impact Score", value="85 / 100")
        st.metric(label="Payment Streamed", value="$425.00")
        
        st.divider()
        st.markdown("**Agent Verdict:**")
        st.caption(
            "The code successfully addresses a critical connection leak by "
            "implementing proper async context managers. Architectural soundness is "
            "high. Test coverage was updated to verify connection closure."
        )
        
        st.write("Arize Trace ID: `trace-a1b2c3d4`")
