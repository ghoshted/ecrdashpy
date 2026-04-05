import streamlit as st
from pathlib import Path
import pydeck as pdk

from utils.data import load_reports, map_points_from_reports

st.title("Location Map")

reports = load_reports(Path("."))
points = map_points_from_reports(reports)

if points.empty:
    st.info("No mappable country data found in reports.")
else:
    view_state = pdk.ViewState(
        latitude=float(points["lat"].mean()),
        longitude=float(points["lon"].mean()),
        zoom=3,
        pitch=0,
    )

    points = points.copy()
    points["radius"] = points["count"].astype(float) * 12000

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position="[lon, lat]",
        get_radius="radius",
        get_fill_color=[31, 111, 235, 170],
        pickable=True,
    )

    st.pydeck_chart(
        pdk.Deck(
            map_style="light",
            initial_view_state=view_state,
            layers=[layer],
            tooltip={"text": "{country}: {count} report runs"},
        ),
        width="stretch",
    )

    st.subheader("Country Summary")
    st.dataframe(points[["country", "count"]], width="stretch", hide_index=True)
