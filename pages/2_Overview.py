import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import (
    create_class_bar_horizontal,
    create_co2_bar,
    create_element_treemap,
    create_room_sunburst,
)
from src.impact_calculator import get_impact_summary
from src.constants import SIA_2032_LIMIT, COLORS, STATUS_COLORS

st.set_page_config(page_title="Overview – IFC Analytics", page_icon=None, layout="wide")
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

# ── Mode Badge ─────────────────────────────────────────────────────────────
mode_label = "New Construction (Neubau)" if mode == "neubau" else "Renovation (Umbau / Sanierung)"
mode_color = "#D6EAF8" if mode == "neubau" else "#FDEBD0"
st.markdown(
    f'<div style="display:inline-block;background:{mode_color};border-radius:6px;'
    f'padding:4px 14px;font-weight:600;margin-bottom:8px;font-size:14px;">{mode_label}</div>',
    unsafe_allow_html=True,
)
st.title("Overview")

# ── KPI Row ────────────────────────────────────────────────────────────────
_, quality_summary = get_quality_data()
summary = get_impact_summary(element_df, space_df, mode)
score = quality_summary.get("score", 0) if quality_summary else 0

co2_per_m2 = summary.get("co2e_per_m2") if summary else None
if co2_per_m2 is not None:
    sia_delta = co2_per_m2 - SIA_2032_LIMIT
    sia_delta_str = f"{sia_delta:+.1f} kg/m² vs SIA 2032"
    sia_delta_color = "inverse" if sia_delta > 0 else "normal"
else:
    sia_delta_str = f"Limit: {SIA_2032_LIMIT:.0f} kg/m²·a"
    sia_delta_color = "off"

kpi = st.columns(5)
kpi[0].metric(
    "Building Elements",
    f"{len(element_df):,}" if element_df is not None else "–"
)
kpi[1].metric(
    "Spaces",
    f"{len(space_df):,}" if space_df is not None and not space_df.empty else "–"
)
kpi[2].metric(
    "Storeys",
    f"{element_df['storey'].nunique():,}" if element_df is not None and "storey" in element_df.columns else "–"
)
kpi[3].metric(
    "CO₂e / m² NFA",
    f"{co2_per_m2:.1f} kg/m²" if co2_per_m2 else "–",
    delta=sia_delta_str,
    delta_color=sia_delta_color,
)
kpi[4].metric("Model Quality", f"{score:.0f}%")

st.divider()

# ── Row 1: IFC Class Distribution + CO2 Overview ──────────────────────────
col_class, col_co2 = st.columns(2)

with col_class:
    if element_df is not None and not element_df.empty:
        fig_class = create_class_bar_horizontal(element_df)
        st.plotly_chart(fig_class, use_container_width=True)
    else:
        st.info("No element data available.")

with col_co2:
    if element_df is not None and not element_df.empty:
        fig_co2 = create_co2_bar(element_df)
        st.plotly_chart(fig_co2, use_container_width=True)
    else:
        st.info("No CO₂ data available.")

st.divider()

# ── Row 2: Treemap + Sunburst (+ Status Donut for Umbau) ──────────────────
if mode == "umbau" and element_df is not None and "status" in element_df.columns:
    col_tree, col_sun, col_donut = st.columns(3)
else:
    col_tree, col_sun = st.columns(2)
    col_donut = None

with col_tree:
    if element_df is not None and not element_df.empty:
        fig_tree = create_element_treemap(element_df)
        st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("No element data available.")

with col_sun:
    if space_df is not None and not space_df.empty:
        fig_sun = create_room_sunburst(space_df)
        st.plotly_chart(fig_sun, use_container_width=True)
    else:
        st.info("No space data available.")

if col_donut is not None:
    with col_donut:
        status_counts = element_df["status"].value_counts()
        fig_donut = go.Figure(go.Pie(
            labels=status_counts.index.tolist(),
            values=status_counts.values.tolist(),
            hole=0.55,
            marker=dict(
                colors=[STATUS_COLORS.get(s, COLORS["neutral"]) for s in status_counts.index]
            ),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            title=dict(text="Status Distribution", font=dict(size=16, color=COLORS["text"]), x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"{len(element_df)}<br><span style='font-size:11px'>elements</span>",
                x=0.5, y=0.5, font_size=18, showarrow=False, font_color=COLORS["text"]
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True)
