import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_material_volume_bar,
    create_element_material_stacked_bar,
    create_storey_material_heatmap,
    create_material_flow_sankey,
    _classify_material_group,
)
from src.ui_helpers import apply_unit_conversion, unit_caption
from src.constants import COLORS, IFC_CLASS_LABELS

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
    st.title("🧱 Components & Quantities")
    st.warning("No component data available.")
    st.stop()

st.title("🧱 Components & Quantities")

_u_area = st.session_state.get("unit_area", "m²")
_u_volume = st.session_state.get("unit_volume", "m³")
_u_mass = st.session_state.get("unit_mass", "kg")

with st.expander("ℹ️ What does this page show?", expanded=False):
    st.markdown("""
    This page provides a **quantitative overview of all components and materials** in the model:
    - **Quantities by Material Group**: Which materials are used — and how much (m³)?
    - **Material Share per Component Group**: Composition of wall, ceiling, floor etc. in a 100% comparison.
    - **Volume by Element Type**: Bar chart of total volume per IFC class.
    - **Volume Matrix (Storey × Material)**: Heatmap showing where materials are concentrated by storey.
    - **Material Flow (Sankey)**: Flow diagram from material group to element type by volume.
    - **Element Quantity List**: Complete, searchable component list with area, volume and length.

    Quantities come directly from the IFC model. Units can be adjusted in the sidebar.
    """)

# Cross filter resets
CF_KEYS = ["cf_page4_class", "cf_page4_material", "cf_page3_usage"]
render_cross_filter_reset("page4", CF_KEYS)

cf_usage = st.session_state.get("cf_page3_usage")
cf_class = st.session_state.get("cf_page4_class")
cf_mat = st.session_state.get("cf_page4_material")

# Use _classify_material_group from chart_factory (consistent classification)
if "material" in element_df.columns:
    element_df["grouped_material"] = element_df["material"].apply(_classify_material_group)

if cf_usage:
    if space_df_raw is not None and not space_df_raw.empty:
        valid_storeys = space_df_raw[space_df_raw["usage"] == cf_usage]["storey"].unique()
        if len(valid_storeys) > 0:
            element_df = element_df[element_df["storey"].isin(valid_storeys)]
        else:
            element_df = pd.DataFrame()

# Keep an unfiltered-by-material copy for the volume bar chart
element_df_all = element_df.copy()

# Compute the top 5 grouped materials dynamically
top_mats = []
if not element_df_all.empty and "grouped_material" in element_df_all.columns:
    vol_col = "volume_m3" if _u_volume in ("m³", "m³") else "area_m2"
    if vol_col in element_df_all.columns:
        df_valid = element_df_all.dropna(subset=[vol_col])
        top_mats = (
            df_valid.groupby("grouped_material")[vol_col]
            .sum()
            .nlargest(5)
            .index.tolist()
        )

        agg_vol = df_valid.groupby("grouped_material")[vol_col].sum()
        tot_vol = agg_vol.sum()
        if tot_vol > 0:
            top_4 = agg_vol.nlargest(4)
            pct_top = (top_4.sum() / tot_vol) * 100
            st.caption(f"📦 {len(top_4)} materials = {pct_top:.0f}% of total volume")
        else:
            st.caption("📦 Comprehensive material composition and quantity distribution analysis.")
    else:
        st.caption("📦 Comprehensive material composition and quantity distribution analysis.")
else:
    st.caption("📦 Comprehensive material composition and quantity distribution analysis.")

# Apply material & class filter for KPIs, stacked bar, and table
if cf_class and "ifc_class" in element_df.columns:
    element_df = element_df[element_df["ifc_class"] == cf_class]
if cf_mat and "grouped_material" in element_df.columns:
    if cf_mat == "Other":
        element_df = element_df[~element_df["grouped_material"].isin(top_mats)]
    else:
        element_df = element_df[element_df["grouped_material"] == cf_mat]

if element_df.empty:
    st.warning("No element data available under the active filters.")
    st.stop()

# Show active filter info
active_parts = []
if cf_usage:
    active_parts.append(f"Usage Type: **{cf_usage}**")
if cf_class:
    active_parts.append(f"Class: **{cf_class}**")
if cf_mat:
    active_parts.append(f"Material: **{cf_mat}**")
if active_parts:
    st.info("🔽 Active Filter — " + " | ".join(active_parts) + "  (use button above to reset)")

# -- KPI Cards -----------------------------------------------------------------
vol_sum = pd.to_numeric(
    element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce"
).sum(skipna=True)
area_sum = pd.to_numeric(
    element_df.get("area_m2", pd.Series(dtype=float)), errors="coerce"
).sum(skipna=True)
kpi = st.columns(4)
kpi[0].metric("🗂️ IFC Classes", f"{element_df['ifc_class'].nunique()}")
kpi[1].metric("🧱 Elements", f"{len(element_df):,}".replace(",", "'"))
kpi[2].metric("📦 Total Volume", f"{vol_sum:,.1f} m³".replace(",", "'"))
kpi[3].metric(
    "🎨 Materials",
    f"{element_df['material'].nunique()}" if "material" in element_df.columns else "–",
)

st.divider()

# -- Chart A: Quantities by Material Group -------------------------------------
st.subheader("📦 Quantities by Material Group")
st.caption("🖱️ Click a bar to filter by this material. Use the reset button above to clear.")
unit = st.session_state.get("unit_volume", "m³")
fig_mat = create_material_volume_bar(element_df_all, unit)
fig_mat.update_layout(height=500)

ev_mat = st.plotly_chart(
    fig_mat, on_select="rerun", key="p4_volume_bar_chart", use_container_width=True
)

if ev_mat and ev_mat.selection and ev_mat.selection.points:
    pt = ev_mat.selection.points[0]
    clicked = pt.get("y") or pt.get("label") or None
    if clicked and clicked != st.session_state.get("cf_page4_material"):
        st.session_state.cf_page4_material = clicked
        st.rerun()

st.divider()

# -- Chart B: Material Share per Component Group -------------------------------
st.subheader("🏗️ Material Share per Component Group")
st.caption("📊 100% Stacked Bar Chart for comparative composition (Ceiling, Floor, Wall, etc.).")
fig_stacked = create_element_material_stacked_bar(element_df)
fig_stacked.update_layout(
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5,
        font=dict(size=11),
    ),
    margin=dict(l=50, r=20, t=80, b=50),
)
st.plotly_chart(fig_stacked, use_container_width=True, key="p4_stacked_bar")

st.divider()

# -- Chart C: Volume by Element Type ------------------------------------------
st.subheader("📊 Volume by Element Type")
st.caption("Total volume per IFC class — shows which element types dominate by volume.")

if "ifc_class" in element_df.columns and "volume_m3" in element_df.columns:
    vol_by_class = element_df.groupby("ifc_class")["volume_m3"].sum().reset_index()
    vol_by_class["vol"] = pd.to_numeric(vol_by_class["volume_m3"], errors="coerce").fillna(0)
    vol_by_class = vol_by_class[vol_by_class["vol"] > 0].sort_values("vol", ascending=True)
    vol_by_class["label"] = vol_by_class["ifc_class"].map(IFC_CLASS_LABELS).fillna(vol_by_class["ifc_class"])

    fig_vol_type = go.Figure(go.Bar(
        x=vol_by_class["vol"],
        y=vol_by_class["label"],
        orientation="h",
        marker_color=COLORS["primary"],
        text=[f"{v:,.1f}".replace(",", "'") for v in vol_by_class["vol"]],
        textposition="outside",
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Volume: %{x:,.1f} m³<extra></extra>",
    ))
    fig_vol_type.update_layout(
        template="plotly_white",
        xaxis_title="Volume (m³)",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=10, r=60, t=20, b=30),
        height=max(260, len(vol_by_class) * 32),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_vol_type, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No volume or class data available.")

st.divider()

# -- Chart D: Volume Matrix (Storey × Material) --------------------------------
st.subheader("🌡️ Volume Matrix (Storey × Material)")
st.caption("🗺️ Heatmap: which material concentrates on which storey (by volume).")
fig_heatmap = create_storey_material_heatmap(element_df, value_col="volume_m3", title="Volume by Storey and Material (m³)")
st.plotly_chart(fig_heatmap, use_container_width=True, key="p4_heatmap")

st.divider()

# -- Chart E: Material Flow (Sankey) -------------------------------------------
st.subheader("🔀 Material Flow (Sankey)")
st.caption("Flow from material group to element type by volume — shows which materials dominate which element types.")
fig_sankey = create_material_flow_sankey(element_df)
st.plotly_chart(fig_sankey, use_container_width=True, key="p4_sankey")

# -- Quantity Takeoff Table ----------------------------------------------------
st.divider()
st.subheader("📋 Element Quantity List")
st.caption("🔎 Detailed component list of the model.")

table_df = element_df.copy()
search = st.text_input(
    "🔎 Search (component type or material)",
    key="search_elements",
    placeholder="e.g. Concrete, Wall...",
)
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["type_name", "material", "ifc_class"]:
        if col_search in table_df.columns:
            mask |= (
                table_df[col_search]
                .astype(str)
                .str.contains(search, case=False, na=False)
            )
    table_df = table_df[mask]

display_cols = [
    "element_id",
    "ifc_class",
    "type_name",
    "material",
    "storey",
    "area_m2",
    "volume_m3",
    "length_m",
]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "element_id": "ID",
    "ifc_class": "IFC Class",
    "type_name": "Type",
    "material": "Material",
    "storey": "Storey",
    "area_m2": "Area (m²)",
    "volume_m3": "Volume (m³)",
    "length_m": "Length (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Area (m²)", "Volume (m³)", "Length (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"🧱 {len(display_df):,} elements shown".replace(",", "'") + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
