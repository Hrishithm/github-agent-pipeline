import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "issues.db"
LOG_PATH = "pipeline.log"

st.set_page_config(
    page_title="GitHub Agent Pipeline | Observability",
    page_icon="🤖",
    layout="wide",
)

# ----------------------------------------------------
# DATABASE QUERIES
# ----------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_issues_data() -> pd.DataFrame:
    """Loads all issue records from issues.db into a DataFrame."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    
    conn = get_db_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM issues ORDER BY issue_number DESC", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# ----------------------------------------------------
# DASHBOARD HEADER & REFRESH
# ----------------------------------------------------
st.title("🤖 Agentic GitHub Issue Response Pipeline")
st.caption("Real-Time Operational Metrics, State Tracking & DLQ Observability")

col_head1, col_head2 = st.columns([6, 1])
with col_head2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

df_issues = load_issues_data()

if df_issues.empty:
    st.warning("No issue data found in `issues.db`. Run `ingest_issues.py` or `pipeline.py` first.")
    st.stop()

# Ensure error_message column exists if missing
if "error_message" not in df_issues.columns:
    df_issues["error_message"] = None

# ----------------------------------------------------
# KPI METRICS
# ----------------------------------------------------
total_issues = len(df_issues)
resolved_count = len(df_issues[df_issues["status"] == "RESOLVED"])
rejected_count = len(df_issues[df_issues["status"] == "REJECTED"])
dlq_count = len(df_issues[df_issues["status"] == "FAILED_DLQ"])
new_count = len(df_issues[df_issues["status"] == "NEW"])

resolution_rate = (resolved_count / total_issues * 100) if total_issues > 0 else 0.0

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric("Total Issues", total_issues)
kpi2.metric("Resolved", resolved_count, f"{resolution_rate:.1f}% rate")
kpi3.metric("Rejected", rejected_count)
kpi4.metric("DLQ Failures", dlq_count, delta_color="inverse")
kpi5.metric("Pending (NEW)", new_count)

st.divider()

# ----------------------------------------------------
# MAIN CONTENT: STATUS BREAKDOWN & ISSUE TABLE
# ----------------------------------------------------
col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader("Lifecycle Status Distribution")
    status_counts = df_issues["status"].value_counts()
    st.bar_chart(status_counts)

with col_right:
    st.subheader("All Ingested Issues")
    display_cols = ["issue_number", "title", "author", "status", "created_at"]
    st.dataframe(
        df_issues[[c for c in display_cols if c in df_issues.columns]],
        use_container_width=True,
        hide_index=True,
    )

# ----------------------------------------------------
# DEAD-LETTER QUEUE (DLQ) INSPECTOR
# ----------------------------------------------------
st.divider()
st.subheader("🚨 Dead-Letter Queue (DLQ) Inspector")

dlq_issues = df_issues[df_issues["status"] == "FAILED_DLQ"]

if dlq_issues.empty:
    st.success("✨ Dead-Letter Queue is clean. Zero unhandled failures detected.")
else:
    st.error(f"Found {len(dlq_issues)} issue(s) trapped in FAILED_DLQ state.")
    for _, row in dlq_issues.iterrows():
        with st.expander(f"Issue #{row['issue_number']}: {row['title']}"):
            st.write(f"**Author:** `{row.get('author', 'Unknown')}`")
            st.write(f"**Issue Body:**\n> {row.get('body', 'No body provided')}")
            st.write("**Error Trace / Reason:**")
            st.code(row.get("error_message") or "No explicit error trace recorded.", language="text")

# ----------------------------------------------------
# LIVE LOG STREAMER
# ----------------------------------------------------
st.divider()
st.subheader("📜 Live Pipeline Log (`pipeline.log`)")

if os.path.exists(LOG_PATH):
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        log_lines = f.readlines()
    
    recent_logs = "".join(log_lines[-40:]) if log_lines else "Log file is currently empty."
    st.text_area(
        label="Showing latest 40 entries:",
        value=recent_logs,
        height=220,
        disabled=True,
    )
else:
    st.info("No `pipeline.log` found yet. Run `pipeline.py` to generate structured logs.")