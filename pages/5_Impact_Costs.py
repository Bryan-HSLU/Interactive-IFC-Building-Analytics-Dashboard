import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_co2_pareto,
    create_sia_gauge,
    create_renovation_waterfall,
    create_circularity_donut,
    create_cost_co2_scatter,
    create_cost_breakdown_bar,
    create_room_co2_scatter,
    create_storey_material_heatmap,
    create_co2_diverging_bar,
    _classify_material_group,
    _MATERIAL_GROUP_COLORS,
)
from src.ui_helpers import hero_kpi_card, scenario_card, fmt_co2, fmt_chf
from src.impact_calculator import get_match_coverage, get_unmatched_materials
from src.constants import COLORS

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
space_df = get_space_df(filtered=True)

st.title("🌱 Sustainability & Costs")

with st.expander("ℹ️ What does this page show?", expanded=False):
    st.markdown("""
    This page evaluates the **ecological and economic footprint** of the building:
    - **Climate**: CO₂ emissions (grey energy) of materials based on KBOB factors. Comparison with SIA 2032 limit (11 kg CO₂e/m²·a).
    - **Costs**: Construction costs by material group from KBOB unit prices.
    - **Grey Energy**: Primary energy demand for production, transport and disposal of materials.
    - **Combined / Trade-off**: Renovation CO₂ balance (diverging bar), cost vs. CO₂ scatter.

    **KBOB** = Swiss coordination body for LCA data (Koordinationskonferenz der Bau- und Liegenschaftsorgane).
    **SIA 2032** = Swiss standard for the CO₂ limit of buildings.
    """)

# ── Base Metrics ──
total_co2 = pd.to_numeric(element_df.get("co2e_total", pd.Series(dtype=float)), errors="coerce").sum()
total_cost = pd.to_numeric(element_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce").sum()
total_grey_energy = pd.to_numeric(element_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce").sum()
total_area = space_df_raw["area_m2"].sum() if space_df_raw is not None and "area_m2" in space_df_raw.columns else 0.0
co2_per_m2 = (total_co2 / total_area) if total_area > 0 else 0.0
energy_per_m2 = (total_grey_energy / total_area) if total_area > 0 else 0.0
_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0

# Dynamic caption
if total_co2 > 0 and "material" in element_df.columns:
    _df_m = element_df.dropna(subset=["co2e_total"]).copy()
    _df_m["co2_n"] = pd.to_numeric(_df_m["co2e_total"], errors="coerce")
    _df_m["mat_grp"] = _df_m["material"].apply(_classify_material_group)
    _agg = _df_m.groupby("mat_grp")["co2_n"].sum()
    if not _agg.empty:
        _top = _agg.idxmax()
        _pct = (_agg.max() / total_co2) * 100
        st.caption(f"**{_top}** accounts for {_pct:.0f} % of the CO₂ load — biggest lever for SIA 2032")
    else:
        st.caption("CO₂ footprint, grey energy and material costs.")
else:
    st.caption("CO₂ footprint, grey energy and material costs.")

CF_KEYS = ["cf_page5_material", "cf_page3_usage"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("No element data available under the active filters.")
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# ── Hero KPI Row ──
col1, col2, col3, col4 = st.columns(4)
with col1:
    hero_kpi_card("CO₂ TOTAL", f"{total_co2:,.0f}".replace(",", "'"), "kg")
with col2:
    hero_kpi_card("CO₂ / NGF", f"{co2_per_m2:,.1f}".replace(",", "'") if total_area > 0 else "–", "kg/m²")
with col3:
    hero_kpi_card("COSTS", f"{total_cost:,.0f}".replace(",", "'"), "CHF")
with col4:
    hero_kpi_card("QUALITY", f"{quality_score:.0f}", "%")

st.markdown("<br>", unsafe_allow_html=True)

# KBOB Coverage warning
coverage = get_match_coverage(element_df)
if coverage < 100:
    unmatched = get_unmatched_materials(element_df)
    if unmatched:
        with st.expander(f"⚠️ {100 - coverage:.0f} % of elements without KBOB assignment ({len(unmatched)} materials)", expanded=False):
            st.dataframe(pd.DataFrame(unmatched, columns=["Unassigned Materials"]), use_container_width=True, hide_index=True)

# ── Tabs ──
tabs = st.tabs(["🌱 CO₂ Emissions", "💰 Costs", "⚡ Grey Energy", "🔄 Combined / Trade-off"])
tab_co2, tab_costs, tab_energy, tab_combined = tabs

# ── Tab: CO₂ Emissions ──
with tab_co2:
    with st.expander("ℹ️ How is CO₂ calculated?", expanded=False):
        st.markdown("""
        CO₂ values come either directly from the IFC model (ArchiCAD attributes) or are calculated
        from **KBOB factors** (kg CO₂e per m³ of material) multiplied by the component volume.
        The **SIA 2032 limit** of 11 kg CO₂e/m²·a is the Swiss target for embodied carbon (grey energy emissions).
        """)
    col_pareto, col_gauge = st.columns([2, 1])
    with col_pareto:
        st.subheader("CO₂ Drivers")
        st.caption("Which material groups cause the largest share? (descending, with cumulative line)")
        st.plotly_chart(create_co2_pareto(element_df), use_container_width=True, config={"displayModeBar": False})
    with col_gauge:
        st.subheader("SIA 2032 Target")
        st.caption("Actual value vs. limit of 11 kg CO₂e/m²·a")
        if total_area > 0:
            st.plotly_chart(create_sia_gauge(co2_per_m2), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No NGF available — SIA gauge requires room data (IfcSpace).")

    st.markdown("<br>", unsafe_allow_html=True)

    # CO₂ heatmap by storey
    st.subheader("CO₂ by Storey and Material")
    st.caption("Heatmap: where are CO₂-intensive materials concentrated by storey?")
    st.plotly_chart(create_storey_material_heatmap(element_df, value_col="co2e_total", title="CO₂ by Storey and Material (kg)"), use_container_width=True, config={"displayModeBar": False})

    # Room CO₂ scatter (if space data available)
    if space_df is not None and not space_df.empty and "area_m2" in space_df.columns and "co2_load" in space_df.columns:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Room Area vs. CO₂ Load")
        st.caption("Rooms far above the trend line have disproportionately high CO₂ intensity.")
        st.plotly_chart(create_room_co2_scatter(space_df), use_container_width=True, config={"displayModeBar": False})

# ── Tab: Costs ──
with tab_costs:
    with st.expander("ℹ️ How are costs calculated?", expanded=False):
        st.markdown("""
        Construction costs are calculated from **KBOB unit prices** (CHF per m³) multiplied by
        the component volume. These are indicative values for the early design phase — not binding cost estimates.
        """)
    col_cb, col_sc = st.columns([1, 2])
    with col_cb:
        st.subheader("Costs by Material")
        st.caption("Total costs per material group (KBOB reference values, CHF)")
        st.plotly_chart(create_cost_breakdown_bar(element_df), use_container_width=True, config={"displayModeBar": False})
    with col_sc:
        st.subheader("Costs vs. CO₂")
        st.caption("Trade-off: expensive and CO₂-intensive vs. cost-efficient and climate-friendly (dot size = volume)")
        st.plotly_chart(create_cost_co2_scatter(element_df), use_container_width=True, config={"displayModeBar": False})

    # Cost efficiency (CHF/m²) if both cost and area data available
    if total_cost > 0 and total_area > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        cost_per_m2 = total_cost / total_area
        st.metric("Cost Efficiency", f"CHF {cost_per_m2:,.0f} / m²".replace(",", "'"),
                  help="Total construction costs divided by net floor area (NGF)")

# ── Tab: Grey Energy ──
with tab_energy:
    _ge_series = pd.to_numeric(element_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce")
    _ge_has_data = _ge_series.notna().any() and _ge_series.sum() > 0
    if _ge_has_data:
        with st.expander("ℹ️ What is grey energy?", expanded=False):
            st.markdown("""
            **Grey energy** is the total energy required for production, transport and
            disposal of building materials — not operational energy. Unit: kWh.
            Source: KBOB factors (kWh primary energy per m³).
            """)
        col_ge1, col_ge2, col_ge_bar = st.columns([1, 1, 3])
        with col_ge1:
            hero_kpi_card("GREY ENERGY", f"{total_grey_energy:,.0f}".replace(",", "'"), "kWh")
        with col_ge2:
            hero_kpi_card("ENERGY / NGF", f"{energy_per_m2:,.1f}".replace(",", "'") if energy_per_m2 > 0 else "–", "kWh/m²")
        with col_ge_bar:
            _df_ge = element_df.dropna(subset=["grey_energy_kwh"]).copy()
            _df_ge["ge_num"] = pd.to_numeric(_df_ge["grey_energy_kwh"], errors="coerce").fillna(0)
            _df_ge["mat_group"] = _df_ge["material"].apply(_classify_material_group)
            _agg_ge = _df_ge.groupby("mat_group")["ge_num"].sum().reset_index()
            _agg_ge.columns = ["Material Group", "kWh"]
            _agg_ge = _agg_ge[_agg_ge["kWh"] > 0]
            _is_and = _agg_ge["Material Group"] == "Other"
            _agg_ge = pd.concat([_agg_ge[_is_and], _agg_ge[~_is_and].sort_values("kWh", ascending=True)], ignore_index=True)
            _colors_ge = [_MATERIAL_GROUP_COLORS.get(m, "#C9CDD3") for m in _agg_ge["Material Group"]]
            _max_ge = _agg_ge["kWh"].max() if not _agg_ge.empty else 1
            fig_ge = go.Figure(go.Bar(
                x=_agg_ge["kWh"], y=_agg_ge["Material Group"], orientation="h",
                marker_color=_colors_ge,
                text=[f"{v:,.0f} kWh".replace(",", "'") for v in _agg_ge["kWh"]],
                textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Grey Energy: %{x:,.0f} kWh<extra></extra>",
            ))
            fig_ge.update_layout(
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
                xaxis=dict(title="kWh", range=[0, _max_ge * 1.35], gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
                yaxis=dict(title=""), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, margin=dict(l=10, r=70, t=20, b=30), height=220,
            )
            st.plotly_chart(fig_ge, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No grey energy data available — KBOB factors may not be matched.")

# ── Tab: Combined / Trade-off ──
with tab_combined:
    if mode == "umbau":
        with st.expander("ℹ️ What does the renovation balance show?", expanded=False):
            st.markdown("""
            - **Waterfall**: CO₂ balance of the renovation — retained (existing), demolished (lost), new build (added), net.
            - **Diverging Bar**: Saved CO₂ (retained elements) vs. new emissions (new build) per material group.
            - **Circularity**: Share of retained building fabric as a proportion of total volume.
            """)
        col_w, col_s, col_d = st.columns([2, 1, 1])
        with col_w:
            st.subheader("Renovation CO₂ Balance")
            st.plotly_chart(create_renovation_waterfall(element_df), use_container_width=True, config={"displayModeBar": False})
        with col_s:
            st.subheader("Scenario Comparison")
            df_nb = element_df[element_df["status"] == "Neubau"]
            avg_nb_m3 = (df_nb["co2e_total"].sum() / df_nb["volume_m3"].sum()) if not df_nb.empty and df_nb["volume_m3"].sum() > 0 else 250.0
            total_vol = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()
            co2_ersatz = total_vol * avg_nb_m3
            scenario_card("Scenario A (Retention)", total_co2, fmt_co2)
            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
            scenario_card("Scenario B (Full Replacement)", co2_ersatz, fmt_co2)
            if co2_ersatz > total_co2:
                delta_pct = (1 - total_co2 / co2_ersatz) * 100
                st.success(f"Saving: **{delta_pct:.0f} %** through renovation")
        with col_d:
            st.subheader("Circularity")
            st.caption("Share of retained building fabric (volume)")
            st.plotly_chart(create_circularity_donut(element_df), use_container_width=True, config={"displayModeBar": False})

        st.divider()
        st.subheader("CO₂ Balance by Material Group")
        st.caption("Diverging bar: new emissions (Neubau) vs. savings from retained elements (Bestand) per material group.")
        st.plotly_chart(create_co2_diverging_bar(element_df), use_container_width=True, config={"displayModeBar": False})
    else:
        st.subheader("Cost vs. CO₂ Trade-off")
        st.caption("Bubble chart: trade-off between cost and CO₂ intensity per material group (size = volume).")
        st.plotly_chart(create_cost_co2_scatter(element_df), use_container_width=True, config={"displayModeBar": False})
        st.info("Switch to **Renovation mode** on Page 1 to see the CO₂ diverging bar and renovation balance.")

# ── Data Tab ──
with st.expander("📊 Raw Element Data", expanded=False):
    table_df = element_df.copy()
    display_cols = [c for c in ["element_id", "ifc_class", "material", "volume_m3", "cost_chf", "co2e_total", "grey_energy_kwh", "status"] if c in table_df.columns]
    rename_map = {
        "element_id": "Element ID", "ifc_class": "Type", "material": "Material",
        "volume_m3": "Volume (m³)", "cost_chf": "Cost (CHF)",
        "co2e_total": "CO₂ (kg)", "grey_energy_kwh": "Grey Energy (kWh)", "status": "Status",
    }
    if display_cols:
        shown = table_df[display_cols].rename(columns=rename_map)
        shown = shown.loc[:, ~shown.columns.duplicated()]
        def _co2_style(v):
            try:
                x = float(v)
                if x > 5000: return "background-color: #D62828; color: white; font-weight: bold;"
                elif x > 1000: return "background-color: #FCA311; color: #2D2D2D;"
                return ""
            except Exception: return ""
        if "CO₂ (kg)" in shown.columns:
            st.dataframe(shown.style.map(_co2_style, subset=["CO₂ (kg)"]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(shown, use_container_width=True, hide_index=True)
