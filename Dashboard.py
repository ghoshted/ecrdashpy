import streamlit as st
import altair as alt
from pathlib import Path

from utils.data import aggregate_reports, format_bytes, format_duration, load_reports

st.set_page_config(page_title="ECRDash", page_icon="📦", layout="wide")

st.markdown("## Compute Report Dashboard")

reports = load_reports(Path("."))
summary = aggregate_reports(reports)

tool_map = (
    reports[["tool_name", "tool_slug"]]
    .dropna(subset=["tool_name", "tool_slug"])
    .drop_duplicates()
)
name_to_slug = dict(zip(tool_map["tool_name"], tool_map["tool_slug"]))
slug_to_name = dict(zip(tool_map["tool_slug"], tool_map["tool_name"]))

totals = summary["totals"]
averages = summary["averages"]

cards_1 = st.columns(3)
cards_1[0].metric("Total Runs", totals["reports"])
cards_1[1].metric("Total Runtime", format_duration(totals["duration_seconds"]))
cards_1[2].metric("Input Size", format_bytes(totals["input_size_bytes"]))

cards_2 = st.columns(3)
cards_2[0].metric("Output Size", format_bytes(totals["output_size_bytes"]))
cards_2[1].metric("Avg Runtime", format_duration(averages["duration_seconds"]))
cards_2[2].metric("Avg Memory", f"{averages['memory_used_mb']:,} MB")

st.divider()

query_value = st.query_params.get("tool")
query_slug = query_value[0] if isinstance(query_value, list) and query_value else query_value
query_tool = slug_to_name.get(str(query_slug), "All tools") if query_slug else "All tools"

tool_filter = st.sidebar.selectbox(
    "Filter by tool",
    options=["All tools"] + sorted(reports["tool_name"].dropna().unique().tolist()),
    index=(["All tools"] + sorted(reports["tool_name"].dropna().unique().tolist())).index(query_tool)
    if query_tool in (["All tools"] + sorted(reports["tool_name"].dropna().unique().tolist()))
    else 0,
)
st.markdown(f"### Showing report runs for: **{tool_filter}**")

selected_slug = name_to_slug.get(tool_filter)
if tool_filter == "All tools":
    if "tool" in st.query_params:
        del st.query_params["tool"]
elif st.query_params.get("tool") != selected_slug:
    st.query_params["tool"] = selected_slug

filtered = reports if tool_filter == "All tools" else reports[reports["tool_name"] == tool_filter]
filtered_summary = aggregate_reports(filtered)

st.caption(f"Showing {filtered.shape[0]} report runs")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Report Runs Per Tool")
    by_tool = filtered_summary["by_tool"].head(20)
    tool_chart = (
        alt.Chart(by_tool)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
        .encode(
            x=alt.X("count:Q", title="Runs"),
            y=alt.Y("tool_name:N", sort="-x", title="Tool"),
            tooltip=["tool_name", "count", "total_duration_seconds"],
            color=alt.value("#1f6feb"),
        )
        .properties(height=350)
    )
    st.altair_chart(tool_chart, width="stretch")

with col_b:
    st.subheader("Runtime Trend (Minutes / Day)")
    by_day = filtered_summary["by_day"].copy()
    if not by_day.empty:
        by_day["duration_minutes"] = by_day["duration_seconds"] / 60.0
        day_chart = (
            alt.Chart(by_day)
            .mark_line(point=True, strokeWidth=2)
            .encode(
                x=alt.X("start_day:T", title="Day"),
                y=alt.Y("duration_minutes:Q", title="Runtime (min)"),
                tooltip=["start_day", "count", alt.Tooltip("duration_minutes:Q", format=".1f")],
                color=alt.value("#d97706"),
            )
            .properties(height=350)
        )
        st.altair_chart(day_chart, width="stretch")
    else:
        st.info("No day-level runtime data available.")

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Report Runs Per Infra")
    by_infra = filtered_summary["by_infra"].head(15)
    if by_infra.empty:
        st.info("No infrastructure metadata available.")
    else:
        infra_chart = (
            alt.Chart(by_infra)
            .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
            .encode(
                x=alt.X("count:Q", title="Runs"),
                y=alt.Y("name:N", sort="-x", title="Infra"),
                tooltip=["name", "count", "total_duration_seconds"],
                color=alt.value("#0f766e"),
            )
            .properties(height=320)
        )
        st.altair_chart(infra_chart, width="stretch")

with col_d:
    st.subheader("Total Memory Used By Tool Per Day")
    mem = filtered_summary["by_day_tool_memory"].copy()
    if mem.empty:
        st.info("No memory series data available.")
    else:
        mem_chart = (
            alt.Chart(mem)
            .mark_bar()
            .encode(
                x=alt.X("start_day:T", title="Day"),
                y=alt.Y("memory_used_mb:Q", title="Memory (MB)"),
                color=alt.Color("tool_name:N", title="Tool"),
                tooltip=["start_day", "tool_name", "memory_used_mb"],
            )
            .properties(height=320)
        )
        st.altair_chart(mem_chart, width="stretch")

st.subheader("Latest Report Runs")
latest = filtered.copy().head(50)
latest["start_time"] = latest["start_time"].fillna("-")
latest["duration_readable"] = latest["duration_seconds"].apply(format_duration)
latest["input_readable"] = latest["input_size_bytes"].apply(format_bytes)
latest["output_readable"] = latest["output_size_bytes"].apply(format_bytes)

st.dataframe(
    latest[
        [
            "start_time",
            "tool_name",
            "duration_readable",
            "input_readable",
            "output_readable",
            "cpu_cores_used",
            "gpu_cores_used",
        ]
    ].rename(
        columns={
            "start_time": "Start Time",
            "tool_name": "Tool",
            "duration_readable": "Duration",
            "input_readable": "Input",
            "output_readable": "Output",
            "cpu_cores_used": "CPU",
            "gpu_cores_used": "GPU",
        }
    ),
    width="stretch",
    hide_index=True,
)
