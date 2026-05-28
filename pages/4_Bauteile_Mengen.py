import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_class_bar_horizontal, create_class_storey_stacked,
    create_material_quantity_bar, create_diverging_bar,
    create_grouped_bar, create_element_treemap,
    create_volume_violin, create_volume_histogram, create_raincloud_plot,
)
from src.ui_helpers import apply_unit_conversion, unit_caption

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

element_df = get_element_df(filtered=True)

if element_df is None or element_df.empty:
    st.title("Components & Quantities")
    st.warning("No element data available.")
    st.stop()

st.title("Components & Quantities")

_u_area   = st.session_state.get("unit_area",   "m\u00b2")
_u_volume = st.session_state.get("unit_volume", "m\u00b3")
_u_mass   = st.session_state.get("unit_mass",   "kg")

CF_KEYS = ["cf_page4_class", "cf_page4_material"]
render_cross_filter_reset("page4", CF_KEYS)

cf_class = st.session_state.get("cf_page4_class")
cf_mat   = st.session_state.get("cf_page4_material")
if cf_class or cf_mat:
    parts = []
    if cf_class: parts.append(f"Class: **{cf_class}**")
    if cf_mat:   parts.append(f"Material: **{cf_mat}**")
    st.info("Active filter -- " + " | ".join(parts) + "  (click same bar again to deselect, or use reset above)")

def _apply_cf(df):
    cf_c = st.session_state.get("cf_page4_class")
    cf_m = st.session_state.get("cf_page4_material")
    if cf_c and "ifc_class" in df.columns:
        df = df[df["ifc_class"] == cf_c]
    if cf_m and "material" in df.columns:
        df = df[df["material"] == cf_m]
    return df

# -- KPI Cards -----------------------------------------------------------------
vol_sum = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum(skipna=True)
kpi = st.columns(4)
kpi[0].metric("IFC Classes", f"{element_df['ifc_class'].nunique()}")
kpi[1].metric("Total Elements", f"{len(element_df):,}")
kpi[2].metric("Total Volume", f"{vol_sum:,.1f} m\u00b3")
kpi[3].metric("Materials", f"{element_df['material'].nunique()}" if "material" in element_df.columns else "\u2013")

# -- Section B: Class Analysis -------------------------------------------------
st.caption("Click a bar to filter all charts and the table below. Click the same bar again to deselect.")
col_left, col_right = st.columns(2)

storey_df = st.session_state.get("storey_df")
storey_order = None
if isinstance(storey_df, list) and storey_df:
    storey_order = [s["name"] for s in storey_df]
elif isinstance(storey_df, pd.DataFrame) and not storey_df.empty:
    storey_order = storey_df["name"].tolist() if "name" in storey_df.columns else None

with col_left:
    fig_class_bar = create_class_bar_horizontal(element_df)
    ev_class = st.plotly_chart(fig_class_bar, on_select="rerun", key="cf_p4_class_bar", use_container_width=True)
    if ev_class and ev_class.selection.points:
        pt = ev_class.selection.points[0]
        clicked = pt.get("y") or pt.get("x") or pt.get("label")
        if clicked:
            if clicked == st.session_state.get("cf_page4_class"):
                st.session_state.cf_page4_class = None
            else:
                st.session_state.cf_page4_class = clicked
            st.rerun()

with col_right:
    fig_storey_stack = create_class_storey_stacked(element_df, storey_order)
    ev_storey = st.plotly_chart(fig_storey_stack, on_select="rerun", key="cf_p4_storey_stack", use_container_width=True)
    if ev_storey and ev_storey.selection.points:
        pt = ev_storey.selection.points[0]
        clicked_val = pt.get("y") or pt.get("x") or pt.get("label")
        if clicked_val:
            if clicked_val == st.session_state.get("cf_page4_class"):
                st.session_state.cf_page4_class = None
            else:
                st.session_state.cf_page4_class = clicked_val
            st.rerun()

# -- Section C: Material Quantities --------------------------------------------
st.divider()
col_mat, col_div = st.columns(2)
unit = st.session_state.get("unit_volume", "m\u00b3")

with col_mat:
    fig_mat = create_material_quantity_bar(element_df, unit)
    ev_mat = st.plotly_chart(fig_mat, on_select="rerun", key="cf_p4_mat_bar", use_container_width=True)
    if ev_mat and ev_mat.selection.points:
        pt = ev_mat.selection.points[0]
        clicked_mat = pt.get("y") or pt.get("x") or pt.get("label")
        if clicked_mat:
            if clicked_mat == st.session_state.get("cf_page4_material"):
                st.session_state.cf_page4_material = None
            else:
                st.session_state.cf_page4_material = clicked_mat
            st.rerun()

with col_div:
    if mode == "umbau":
        fig_div = create_diverging_bar(element_df)
    else:
        fig_div = create_material_quantity_bar(element_df, "m\u00b2" if "area_m2" in element_df.columns else unit)
    st.plotly_chart(fig_div, use_container_width=True, key="cf_p4_div_bar")

# -- Section D: Hierarchy & Comparison ----------------------------------------
st.divider()
st.subheader("Hierarchy & Comparison")
col_tree4, col_grp = st.columns(2)
with col_tree4:
    st.plotly_chart(create_element_treemap(element_df), use_container_width=True)
with col_grp:
    st.plotly_chart(create_grouped_bar(element_df, mode), use_container_width=True)

# -- Section E: Volume Distribution -------------------------------------------
st.divider()
st.subheader("Volume Distribution")
tab_vio, tab_hist4, tab_rain = st.tabs(["Violin", "Histogram", "Raincloud"])
with tab_vio:
    st.plotly_chart(create_volume_violin(element_df), use_container_width=True)
with tab_hist4:
    st.plotly_chart(create_volume_histogram(element_df), use_container_width=True)
with tab_rain:
    st.plotly_chart(create_raincloud_plot(element_df), use_container_width=True)

# -- Section F: Quantity Takeoff Table ----------------------------------------
st.divider()
st.subheader("Quantity Takeoff")

table_df = _apply_cf(element_df.copy())
search = st.text_input("Search (type or material)", key="search_elements", placeholder="e.g. Concrete, Wall...")
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["type_name", "material", "ifc_class"]:
        if col_search in table_df.columns:
            mask |= table_df[col_search].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

display_cols = ["element_id", "ifc_class", "type_name", "material", "storey", "area_m2", "volume_m3", "length_m"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]
col_rename = {
    "element_id": "ID", "ifc_class": "IFC Class", "type_name": "Type",
    "material": "Material", "storey": "Storey",
    "area_m2": "Area (m\u00b2)", "volume_m3": "Volume (m\u00b3)", "length_m": "Length (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Area (m\u00b2)", "Volume (m\u00b3)", "Length (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"{len(display_df):,} elements shown" + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
