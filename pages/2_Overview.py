import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import create_class_bar_horizontal, create_co2_bar, create_element_treemap
from src.impact_calculator import get_impact_summary
from src.constants import SIA_2032_LIMIT

st.set_page_config(page_title="Übersicht – IFC Analytics", page_icon=None, layout="wide")
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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite 1** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)
space_df = get_space_df(filtered=True)

# Mode badge
mode_label = "Neubau" if mode == "neubau" else "Umbau / Sanierung"
mode_color = "#D6EAF8" if mode == "neubau" else "#FDEBD0"
st.markdown(
    f'<div style="display:inline-block;background:{mode_color};border-radius:6px;'
    f'padding:4px 12px;font-weight:600;margin-bottom:8px;">{mode_label}</div>',
    unsafe_allow_html=True,
)

st.title("Übersicht")

# ── KPI Row ────────────────────────────────────────────────────────────────
_, quality_summary = get_quality_data()
summary = get_impact_summary(element_df, space_df, mode)

kpi = st.columns(5)
kpi[0].metric(
    "Bauelemente",
    f"{len(element_df):,}" if element_df is not None else "–"
)
kpi[1].metric(
    "Räume",
    f"{len(space_df):,}" if space_df is not None and not space_df.empty else "–"
)
kpi[2].metric(
    "Geschosse",
    f"{element_df['storey'].nunique():,}" if element_df is not None and "storey" in element_df.columns else "–"
)
kpi[3].metric(
    "CO2e / m² NGF",
    f"{summary['co2e_per_m2']:.1f} kg/m²" if summary.get("co2e_per_m2") else "–",
    delta=f"Limit: {SIA_2032_LIMIT:.0f} kg/m²·a",
    delta_color="off",
)
score = quality_summary.get("score", 0) if quality_summary else 0
kpi[4].metric("Modellqualität", f"{score:.0f}%")

st.divider()

# ── Charts Row ─────────────────────────────────────────────────────────────
col_class, col_co2 = st.columns(2)

with col_class:
    if element_df is not None and not element_df.empty:
        fig_class = create_class_bar_horizontal(element_df)
        st.plotly_chart(fig_class, use_container_width=True)
    else:
        st.info("Keine Elementdaten verfügbar.")

with col_co2:
    if element_df is not None and not element_df.empty:
        fig_co2 = create_co2_bar(element_df)
        st.plotly_chart(fig_co2, use_container_width=True)
    else:
        st.info("Keine CO2-Daten verfügbar.")

st.divider()

# ── Treemap ────────────────────────────────────────────────────────────────
if element_df is not None and not element_df.empty:
    fig_tree = create_element_treemap(element_df)
    st.plotly_chart(fig_tree, use_container_width=True)