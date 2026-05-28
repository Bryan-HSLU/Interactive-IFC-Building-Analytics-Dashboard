import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_room_boxplot,
    create_room_stacked_bar,
)
from src.ui_helpers import kpi_card, apply_unit_conversion, unit_caption

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

element_df_raw = get_element_df(filtered=False)
space_df_raw = get_space_df(filtered=False)
mode = st.session_state.get("mode_project", "")
render_sidebar(element_df_raw, space_df_raw, mode)

if not st.session_state.get("ifc_parsed"):
    st.warning("Please upload an IFC file on **Page 1** first.")
    st.stop()

space_df = get_space_df(filtered=True)

if space_df is None or space_df.empty:
    st.title("Rooms & Areas")
    st.info(
        "This page is disabled for this project because the uploaded IFC model "
        "does not contain any room (IfcSpace) elements."
    )
    st.stop()

st.title("Rooms & Areas")

_u_area   = st.session_state.get("unit_area",   "m\u00b2")
_u_volume = st.session_state.get("unit_volume", "m\u00b3")
_u_mass   = st.session_state.get("unit_mass",   "kg")

CF_KEYS = ["cf_page3_usage", "cf_page3_storey"]
render_cross_filter_reset("page3", CF_KEYS)

cf_usage = st.session_state.get("cf_page3_usage")
cf_storey = st.session_state.get("cf_page3_storey")

if cf_usage or cf_storey:
    parts = []
    if cf_usage: parts.append(f"Usage: **{cf_usage}**")
    if cf_storey: parts.append(f"Storey: **{cf_storey}**")
    st.info("Active filter -- " + " | ".join(parts) + "  (click same segment again to deselect, or use reset above)")

def _apply_cf(df):
    cf_u = st.session_state.get("cf_page3_usage")
    cf_s = st.session_state.get("cf_page3_storey")
    if cf_u and "usage" in df.columns:
        df = df[df["usage"] == cf_u]
    if cf_s and "storey" in df.columns:
        df = df[df["storey"] == cf_s]
    return df

# -- KPI Cards -----------------------------------------------------------------
df_with_area = space_df.dropna(subset=["area_m2"]) if "area_m2" in space_df.columns else pd.DataFrame()
total_area = df_with_area["area_m2"].sum() if not df_with_area.empty else 0.0
avg_area = df_with_area["area_m2"].mean() if not df_with_area.empty else 0.0

kpi = st.columns(4)
with kpi[0]:
    kpi_card("Rooms Total", f"{len(space_df):,}")
with kpi[1]:
    kpi_card("Total NFA", f"{total_area:,.1f} m\u00b2")
with kpi[2]:
    kpi_card("Ø Room Size", f"{avg_area:,.1f} m\u00b2")
with kpi[3]:
    kpi_card("Usage Types", f"{space_df['usage'].nunique()}" if "usage" in space_df.columns else "\u2013")

st.divider()

# -- Chart A: Room Size Boxplot (interactive) ----------------------------------
# -- Chart B: Room Area per Storey Stacked Bar (interactive) -------------------
st.caption("Click a boxplot category or storey segment to filter all charts and the table below. Click again to deselect.")
col_left, col_right = st.columns(2)

storey_df = st.session_state.get("storey_df")
storey_order = None
if isinstance(storey_df, list) and storey_df:
    storey_order = [s["name"] for s in storey_df]
elif isinstance(storey_df, pd.DataFrame) and not storey_df.empty:
    storey_order = storey_df["name"].tolist() if "name" in storey_df.columns else None

with col_left:
    st.subheader("Room Size by Usage Type")
    fig_box = create_room_boxplot(space_df)
    ev_box = st.plotly_chart(fig_box, on_select="rerun", key="cf_p3_boxplot", use_container_width=True)
    if ev_box and ev_box.selection.points:
        pt = ev_box.selection.points[0]
        clicked = pt.get("y") or pt.get("x") or pt.get("label")
        if clicked:
            st.session_state.cf_page3_usage = None if clicked == st.session_state.get("cf_page3_usage") else clicked
            st.rerun()

with col_right:
    st.subheader("Room Area by Storey and Usage")
    fig_bar = create_room_stacked_bar(space_df, storey_order)
    ev_bar = st.plotly_chart(fig_bar, on_select="rerun", key="cf_p3_stacked_bar", use_container_width=True)
    if ev_bar and ev_bar.selection.points:
        pt = ev_bar.selection.points[0]
        clicked_storey = pt.get("x") or pt.get("y") or pt.get("label")
        if clicked_storey:
            st.session_state.cf_page3_storey = None if clicked_storey == st.session_state.get("cf_page3_storey") else clicked_storey
            st.rerun()

# -- Rooms List Table ----------------------------------------------------------
st.divider()
st.subheader("Room Details")

table_df = _apply_cf(space_df.copy())
search = st.text_input("Search (room name)", key="search_rooms", placeholder="e.g. Office, Corridor...")
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["name", "long_name", "usage"]:
        if col_search in table_df.columns:
            mask |= table_df[col_search].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

display_cols = ["name", "storey", "usage", "area_m2", "volume_m3", "height_m"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "name": "Room Name", "storey": "Storey", "usage": "Usage",
    "area_m2": "Area (m\u00b2)", "volume_m3": "Volume (m\u00b3)", "height_m": "Height (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Area (m\u00b2)", "Volume (m\u00b3)", "Height (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"{len(display_df):,} rooms shown" + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
