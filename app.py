import streamlit as st
from pathlib import Path

from utils.data import load_reports

st.set_page_config(
    page_title="Compute Reports Dashboard",
    page_icon="📦",
    layout="wide",
)

st.title("Compute Reports Dashboard")
st.caption("Streamlit + Python version of the ecrdash report dashboard")

reports = load_reports(Path("."), source="remote")
data_source = str(reports.attrs.get("source", "unknown"))

st.markdown(
    """
This app ingests JSON execution reports and provides a dashboard focused on run volume,
runtime, memory, infra usage, and recent run details.

Use the sidebar to open each page:
- **Overview** for summary cards and core charts
- **Reports Explorer** for searchable run history
- **Location Map** for country-level run distribution
"""
)

col1, col2, col3 = st.columns(3)
col1.metric("Reports Loaded", int(reports.shape[0]))
col2.metric("Unique Tools", int(reports["tool_name"].nunique()))
col3.metric("Infra Targets", int(reports.explode("infra")["infra"].dropna().nunique()))

with st.expander("Quick Start"):
    st.code(
        "# reads reports from ghoshted/ecrdash/reports_output_dir by default\n"
        "# then start the dashboard\n"
        "streamlit run app.py",
        language="bash",
    )

if data_source == "remote":
    st.success("Using report files from https://github.com/ghoshted/ecrdash/tree/main/reports_output_dir")
elif data_source == "local":
    st.warning("Remote reports unavailable. Using local reports_output_dir files instead.")
else:
    st.warning("Remote and local reports unavailable. Using synthetic fallback data.")
