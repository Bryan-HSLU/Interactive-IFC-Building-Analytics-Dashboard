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
from src.constants import COLORS, CATEGORICAL_COLORS, IFC_CLASS_LABELS

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
    - **Quantities by Material Group**: Which materials are used — and how much (m³)? Use the slider to filter small groups.
    - **Material Volume per Component Group**: Absolute volume (m³) per material in each component category.
    - **Components per Storey**: How many elements of each IFC type per storey?
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

# Compute top materials for "Other" filter logic
top_mats = []
if not element_df_all.empty and "grouped_material" in element_df_all.columns:
    vol_col = "volume_m3"
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

# Apply class filter for KPIs (material filter applied after chart A)
if cf_class and "ifc_class" in element_df.columns:
    element_df = element_df[element_df["ifc_class"] == cf_class]

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

# ── Material View Toggle ──────────────────────────────────────────────────────
_prev_view = st.session_state.get("_p4_prev_mat_view", "grouped")
mat_view = st.radio(
    "Material view",
    ["Grouped (6 categories)", "Individual raw materials"],
    index=0,
    horizontal=True,
    key="p4_mat_view",
)
_mat_individual = mat_view.startswith("Individual")
# Reset cross-filter when switching view to avoid stale filter
if _mat_individual != (_prev_view == "individual"):
    st.session_state["cf_page4_material"] = None
st.session_state["_p4_prev_mat_view"] = "individual" if _mat_individual else "grouped"

# Top-N slider for individual mode
_top_n = 20
if _mat_individual:
    _top_n = st.slider("Show top N materials by volume", min_value=5, max_value=50, value=20, step=5)

# Re-read cf_mat after possible reset
cf_mat = st.session_state.get("cf_page4_material")

# -- Chart A: Quantities by Material Group / Individual -------------------------
st.subheader("📦 Quantities by Material Group")
if _mat_individual:
    st.caption("Showing all individual raw materials (top N by volume). 🖱️ Click a bar to filter.")
else:
    st.caption("🖱️ Click a bar to filter by this material. Use the slider to hide small groups.")

if _mat_individual:
    # Build individual material volume bar inline
    from src.constants import MATERIAL_GROUP_COLORS as _MGC, CATEGORICAL_COLORS as _CAT
    _idf = element_df_all.copy()
    if "volume_m3" in _idf.columns:
        _idf["volume_m3"] = pd.to_numeric(_idf["volume_m3"], errors="coerce").fillna(0)
        _idf = _idf[_idf["volume_m3"] > 0]
        if "material" in _idf.columns:
            _mat_agg = _idf.groupby("material")["volume_m3"].sum().nlargest(_top_n).sort_values(ascending=True)
            _pal = _CAT * (len(_mat_agg) // len(_CAT) + 1)
            fig_mat = go.Figure(go.Bar(
                x=_mat_agg.values,
                y=_mat_agg.index,
                orientation="h",
                marker_color=_pal[:len(_mat_agg)],
                text=[f"{v:,.1f}".replace(",", "'") for v in _mat_agg.values],
                textposition="outside",
                cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Volume: %{x:,.1f} m³<extra></extra>",
            ))
            fig_mat.update_layout(
                template="plotly_white", xaxis_title="m³", yaxis_title="",
                margin=dict(l=10, r=80, t=20, b=30), height=max(300, len(_mat_agg) * 28),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
            )
        else:
            fig_mat = go.Figure()
    else:
        fig_mat = go.Figure()
else:
    unit = st.session_state.get("unit_volume", "m³")
    fig_mat = create_material_volume_bar(element_df_all, unit, min_volume=0.0)

fig_mat.update_layout(height=max(fig_mat.layout.height or 400, 400))

ev_mat = st.plotly_chart(
    fig_mat, on_select="rerun", key="p4_volume_bar_chart", use_container_width=True
)

if ev_mat and ev_mat.selection and ev_mat.selection.points:
    pt = ev_mat.selection.points[0]
    clicked = pt.get("y") or pt.get("label") or None
    if clicked and clicked != st.session_state.get("cf_page4_material"):
        st.session_state.cf_page4_material = clicked
        st.rerun()

# Apply individual-material filter if in individual mode
if _mat_individual and cf_mat and "material" in element_df.columns:
    element_df = element_df[element_df["material"] == cf_mat]
elif not _mat_individual and cf_mat and "grouped_material" in element_df.columns:
    if cf_mat == "Other":
        element_df = element_df[~element_df["grouped_material"].isin(top_mats)]
    else:
        element_df = element_df[element_df["grouped_material"] == cf_mat]

if element_df.empty:
    st.warning("No element data available under the active filters.")
    st.stop()

st.divider()

# -- Chart B: Material Volume per Component Group ------------------------------
st.subheader("🏗️ Material Volume per Component Group")
_b_view = st.radio(
    "Component-group material view",
    ["Grouped (6 categories)", "Individual raw materials"],
    index=0, horizontal=True, key="p4_stacked_view",
)
_b_individual = _b_view.startswith("Individual")
if _b_individual:
    st.caption("📊 Absolute volume (m³) per individual material per component category. Toggle materials via the legend.")
else:
    st.caption("📊 Absolute volume (m³) per material group per component category. Toggle materials via the legend.")
fig_stacked = create_element_material_stacked_bar(element_df, individual=_b_individual)
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

# -- Chart C: Components per Storey --------------------------------------------
st.subheader("🏢 Components per Storey")
st.caption("Number of elements per IFC class per storey — shows how composition changes across floors.")

if "ifc_class" in element_df.columns and "storey" in element_df.columns:
    storey_class = element_df.groupby(["storey", "ifc_class"]).size().reset_index(name="count")
    storeys = sorted(storey_class["storey"].unique())
    classes = storey_class.groupby("ifc_class")["count"].sum().sort_values(ascending=False).index.tolist()

    _palette = CATEGORICAL_COLORS * (len(classes) // len(CATEGORICAL_COLORS) + 1)
    fig_comp_storey = go.Figure()
    for i, cls in enumerate(classes):
        sub = storey_class[storey_class["ifc_class"] == cls]
        cls_counts = {row["storey"]: row["count"] for _, row in sub.iterrows()}
        label = IFC_CLASS_LABELS.get(cls, cls)
        fig_comp_storey.add_trace(go.Bar(
            name=label,
            x=storeys,
            y=[cls_counts.get(s, 0) for s in storeys],
            marker_color=_palette[i],
            hovertemplate=f"<b>{label}</b><br>Storey: %{{x}}<br>Count: %{{y}}<extra></extra>",
        ))
    fig_comp_storey.update_layout(
        template="plotly_white",
        barmode="stack",
        xaxis_title="Storey",
        yaxis_title="Number of Elements",
        margin=dict(l=40, r=20, t=30, b=60),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.3, xanchor="center", x=0.5, font=dict(size=10)),
    )
    st.plotly_chart(fig_comp_storey, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No storey or class data available.")

st.divider()

# -- Chart D: Volume Matrix (Storey × Material) --------------------------------
st.subheader("🌡️ Volume Matrix (Storey × Material)")
st.caption("🗺️ Heatmap: which material concentrates on which storey (by volume).")
fig_heatmap = create_storey_material_heatmap(element_df, value_col="volume_m3", title="Volume by Storey and Material (m³)")
st.plotly_chart(fig_heatmap, use_container_width=True, key="p4_heatmap")

st.divider()

# -- Chart E: Material Flow (Sankey) -------------------------------------------
st.subheader("🔀 Material Flow (Sankey)")
_s_view = st.radio(
    "Sankey material view",
    ["Grouped (6 categories)", "Individual raw materials"],
    index=0, horizontal=True, key="p4_sankey_view",
)
_s_individual = _s_view.startswith("Individual")
st.caption("Flow from material group to element type by volume — shows which materials dominate which element types.")
fig_sankey = create_material_flow_sankey(element_df, individual=_s_individual)
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
