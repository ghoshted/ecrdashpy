import streamlit as st
from pathlib import Path

from utils.data import format_bytes, format_duration, load_reports

st.title("Reports Explorer")

reports = load_reports(Path("."))

tool_options = ["All tools"] + sorted(reports["tool_name"].dropna().unique().tolist())
selected_tool = st.selectbox("Tool", options=tool_options, index=0)

infra_options = sorted(
    reports.explode("infra")["infra"].dropna().astype(str).unique().tolist()
)
selected_infra = st.multiselect("Infra", options=infra_options)

min_duration, max_duration = int(reports["duration_seconds"].min()), int(reports["duration_seconds"].max())
duration = st.slider("Duration range (seconds)", min_value=min_duration, max_value=max_duration, value=(min_duration, max_duration))

filtered = reports.copy()
if selected_tool != "All tools":
    filtered = filtered[filtered["tool_name"] == selected_tool]

if selected_infra:
    selected = set(selected_infra)
    filtered = filtered[filtered["infra"].apply(lambda v: bool(set(v or []) & selected))]

filtered = filtered[
    (filtered["duration_seconds"] >= duration[0]) &
    (filtered["duration_seconds"] <= duration[1])
].copy()

filtered = filtered.sort_values("start_time", ascending=False)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
summary_col1.metric("Visible Runs", int(filtered.shape[0]))
summary_col2.metric("Unique Tools", int(filtered["tool_name"].nunique()))
summary_col3.metric("Total Runtime", format_duration(int(filtered["duration_seconds"].sum())))
summary_col4.metric("Avg Memory", f"{int(filtered['memory_used_mb'].mean() if not filtered.empty else 0):,} MB")

prepared = filtered.copy()
prepared["duration"] = prepared["duration_seconds"].apply(format_duration)
prepared["input"] = prepared["input_size_bytes"].apply(format_bytes)
prepared["output"] = prepared["output_size_bytes"].apply(format_bytes)
prepared["infra"] = prepared["infra"].apply(lambda v: ", ".join(v or []))

st.dataframe(
    prepared[
        [
            "start_time",
            "tool_name",
            "tool_version",
            "duration",
            "input",
            "output",
            "memory_used_mb",
            "cpu_cores_used",
            "gpu_cores_used",
            "infra",
            "address_country",
            "file_name",
        ]
    ].rename(
        columns={
            "start_time": "Start Time",
            "tool_name": "Tool",
            "tool_version": "Version",
            "memory_used_mb": "Memory (MB)",
            "cpu_cores_used": "CPU",
            "gpu_cores_used": "GPU",
            "address_country": "Country",
            "file_name": "Report File",
            "infra": "Infra",
            "duration": "Duration",
            "input": "Input",
            "output": "Output",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.download_button(
    label="Download filtered CSV",
    data=filtered.to_csv(index=False),
    file_name="inventory_filtered.csv",
    mime="text/csv",
)
