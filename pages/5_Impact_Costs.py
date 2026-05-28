import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_co2_bar,
    create_co2_treemap,
    create_cost_bar,
    create_waterfall_co2,
    create_sankey_material,
    create_slope_co2,
)
from src.impact_calculator import get_impact_summary
from src.ui_helpers import kpi_card, apply_unit_conversion, unit_caption
from src.constants import SIA_2032_LIMIT, COLORS

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

if element_df is None or element_df.empty:
    st.title("Impact & Costs")
    st.warning("No element data available.")
    st.stop()

st.title("Impact & Costs")

_u_area   = st.session_state.get("unit_area",   "m\u00b2")
_u_volume = st.session_state.get("unit_volume", "m\u00b3")
_u_mass   = st.session_state.get("unit_mass",   "kg")

CF_KEYS = ["cf_page5_material", "cf_page5_treemap"]
render_cross_filter_reset("page5", CF_KEYS)

summary = get_impact_summary(element_df, space_df, mode)

coverage = summary.get("coverage_pct", 0)
if coverage == 0:
    st.warning("No KBOB factors could be matched. Check material names in the model.")
elif coverage < 100:
    st.info(f"{coverage:.0f}% of elements matched to KBOB factors.")

cf_mat5  = st.session_state.get("cf_page5_material")
cf_tree5 = st.session_state.get("cf_page5_treemap")
if cf_mat5 or cf_tree5:
    active = cf_mat5 or cf_tree5
    st.info(f"Active filter -- Material: **{active}**  (use reset above to clear)")

def _apply_cf(df):
    cf_mat = st.session_state.get("cf_page5_material")
    cf_tree = st.session_state.get("cf_page5_treemap")
    if cf_mat and "material" in df.columns:
        df = df[df["material"] == cf_mat]
    elif cf_tree and "material" in df.columns:
        df = df[df["material"] == cf_tree]
    return df

# -- Tabs ----------------------------------------------------------------------
tab_co2, tab_cost, tab_zirk = st.tabs(["CO2 & Energy", "Costs", "Circularity"])

with tab_co2:
    kpi = st.columns(4)
    with kpi[0]:
        kpi_card("Total CO2e", f"{summary['co2e_total']:,.0f} kg" if summary["co2e_total"] else "\u2013")
    with kpi[1]:
        co2_m2 = summary.get("co2e_per_m2")
        if co2_m2:
            diff = co2_m2 - SIA_2032_LIMIT
            d_color = COLORS["error_ok"] if diff <= 0 else COLORS["error_warning"]
            d_text = f"{'below' if diff<=0 else 'above'} SIA 2032 ({SIA_2032_LIMIT:.0f} kg/m\u00b2)"
            kpi_card("CO2e per m\u00b2 NFA", f"{co2_m2:.1f} kg/m\u00b2", d_text, d_color)
        else:
            kpi_card("CO2e per m\u00b2 NFA", "\u2013")
    with kpi[2]:
        kpi_card("Embodied Energy", f"{summary['grey_energy_total']:,.0f} kWh" if summary["grey_energy_total"] else "\u2013")
    with kpi[3]:
        kpi_card("Embodied Energy/m\u00b2", f"{summary['energy_per_m2']:.1f} kWh/m\u00b2" if summary.get("energy_per_m2") else "\u2013")

    if summary.get("co2e_per_m2"):
        co2_m2 = summary["co2e_per_m2"]
        pct = co2_m2 / SIA_2032_LIMIT * 100
        sia_bg = "#D5EEF0" if co2_m2 <= SIA_2032_LIMIT else "#FDF3DC"
        sia_border = COLORS["error_ok"] if co2_m2 <= SIA_2032_LIMIT else COLORS["error_warning"]
        sia_status = "Within limit" if co2_m2 <= SIA_2032_LIMIT else "Limit exceeded"
        st.markdown(
            f'<div style="background:{sia_bg};border-left:4px solid {sia_border};'
            f'border-radius:4px;padding:8px 14px;margin:8px 0;">'
            f'<b>SIA 2032:</b> {sia_status} \u2014 '
            f'{co2_m2:.1f} / {SIA_2032_LIMIT:.0f} kg CO2e/m\u00b2\u00b7a = {pct:.0f}%</div>',
            unsafe_allow_html=True,
        )

    if mode == "umbau" and "status" in element_df.columns:
        sub = st.columns(2)
        co2_neubau = pd.to_numeric(
            element_df[element_df["status"] == "Neubau"].get("co2e_total", pd.Series(dtype=float)), errors="coerce"
        ).sum()
        co2_abbruch = pd.to_numeric(
            element_df[element_df["status"] == "Abbruch"].get("co2e_total", pd.Series(dtype=float)), errors="coerce"
        ).sum()
        with sub[0]: kpi_card("CO2e New Build", f"{co2_neubau:,.0f} kg")
        with sub[1]: kpi_card("CO2e Demolition", f"{co2_abbruch:,.0f} kg")

    st.divider()

    # -- Chart A: CO2 Bar (interactive, cross-filters treemap + table) ----------
    # -- Chart B: CO2 Treemap (interactive, cross-filters bar + table) ----------
    st.caption("Click a bar or treemap segment to filter the detail table below. Click again to deselect.")
    col_bar, col_tree = st.columns(2)

    with col_bar:
        st.subheader("CO\u2082e per Material")
        fig_co2_bar = create_co2_bar(element_df)
        ev_co2 = st.plotly_chart(fig_co2_bar, on_select="rerun", key="cf_p5_co2_bar", use_container_width=True)
        if ev_co2 and ev_co2.selection.points:
            pt = ev_co2.selection.points[0]
            clicked = pt.get("y") or pt.get("x") or pt.get("label")
            if clicked:
                st.session_state.cf_page5_material = None if clicked == st.session_state.get("cf_page5_material") else clicked
                st.session_state.cf_page5_treemap = None
                st.rerun()

    with col_tree:
        st.subheader("CO\u2082e Share by Material")
        fig_treemap = create_co2_treemap(element_df)
        ev_tree = st.plotly_chart(fig_treemap, on_select="rerun", key="cf_p5_treemap", use_container_width=True)
        if ev_tree and ev_tree.selection.points:
            pt = ev_tree.selection.points[0]
            clicked = pt.get("label") or pt.get("id") or pt.get("x")
            if clicked and clicked not in ("Gesamt", "root", "Total"):
                st.session_state.cf_page5_treemap = clicked
                st.session_state.cf_page5_material = clicked
                st.rerun()

with tab_cost:
    kpi_c = st.columns(3)
    with kpi_c[0]:
        kpi_card("Total Costs", f"CHF {summary['cost_total']:,.0f}" if summary["cost_total"] else "\u2013")
    with kpi_c[1]:
        kpi_card("Cost per m\u00b2", f"CHF {summary['cost_per_m2']:,.0f}/m\u00b2" if summary.get("cost_per_m2") else "\u2013")
    if mode == "umbau" and "status" in element_df.columns:
        cost_neubau = pd.to_numeric(
            element_df[element_df["status"] == "Neubau"].get("cost_chf", pd.Series(dtype=float)), errors="coerce"
        ).sum()
        with kpi_c[2]: kpi_card("New Build Costs", f"CHF {cost_neubau:,.0f}")
    st.divider()
    st.plotly_chart(create_cost_bar(element_df), use_container_width=True)

with tab_zirk:
    if mode != "umbau":
        st.info("This view is only available in Renovation mode.")
    else:
        st.plotly_chart(create_slope_co2(element_df), use_container_width=True)
        st.divider()
        if "status" in element_df.columns:
            total = len(element_df)
            bestand = (element_df["status"] == "Bestand").sum()
            abbruch = (element_df["status"] == "Abbruch").sum()
            reuse_pct = (bestand / total * 100) if total > 0 else 0
            deconstruct_pct = (abbruch / total * 100) if total > 0 else 0
            cost_bestand = pd.to_numeric(
                element_df[element_df["status"] == "Bestand"].get("cost_chf", pd.Series(dtype=float)), errors="coerce"
            ).sum()
            zk = st.columns(3)
            with zk[0]: kpi_card("Reuse Potential", f"{reuse_pct:.1f}%")
            with zk[1]: kpi_card("Deconstructable Elements", f"{deconstruct_pct:.1f}%")
            with zk[2]: kpi_card("Estimated Residual Value", f"CHF {cost_bestand:,.0f}")
            st.caption("Simplified estimate based on material types and status data.")
        else:
            st.warning("No status data available for circularity analysis.")

# -- Detail Table --------------------------------------------------------------
st.divider()
st.subheader("Element Details")

table_df = _apply_cf(element_df.copy())
display_cols = ["element_id", "ifc_class", "material", "volume_m3", "co2e_total", "grey_energy_kwh", "cost_chf"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]
col_rename = {
    "element_id": "ID", "ifc_class": "IFC Class", "material": "Material",
    "volume_m3": "Volume (m\u00b3)", "co2e_total": "CO2e (kg)",
    "grey_energy_kwh": "Embodied Energy (kWh)", "cost_chf": "Cost (CHF)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Volume (m\u00b3)", "CO2e (kg)", "Embodied Energy (kWh)", "Cost (CHF)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(1)
display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"{len(display_df):,} elements shown | Missing factors shown as empty" + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
