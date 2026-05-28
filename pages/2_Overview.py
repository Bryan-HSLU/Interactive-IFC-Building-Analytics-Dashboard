import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import (
    create_room_sunburst,
    create_room_bubble,
    create_co2_treemap,
    create_status_distribution,
    create_material_quantity_bar,
    create_class_bar_horizontal,
)
from src.impact_calculator import get_impact_summary
from src.ui_helpers import kpi_card
from src.constants import SIA_2032_LIMIT, COLORS, STATUS_COLORS

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
has_spaces = space_df is not None and not space_df.empty

# -- Mode Badge ----------------------------------------------------------------
if mode == "neubau":
    mode_label, mode_bg, mode_border = "New Build", "#D5EEF0", COLORS["neubau"]
else:
    mode_label, mode_bg, mode_border = "Renovation", "#EDE3D5", COLORS["abbruch"]

st.markdown(
    f'<div style="display:inline-block;background:{mode_bg};border-left:4px solid {mode_border};'
    f'border-radius:4px;padding:4px 14px;font-weight:600;margin-bottom:8px;font-size:14px;">'
    f'{mode_label}</div>', unsafe_allow_html=True,
)
st.title("Overview")

# -- KPI Row -------------------------------------------------------------------
_, quality_summary = get_quality_data()
summary = get_impact_summary(element_df, space_df, mode)
score = quality_summary.get("score", 0) if quality_summary else 0
co2_per_m2 = summary.get("co2e_per_m2") if summary else None

kpi = st.columns(5)
with kpi[0]: kpi_card("Elements", f"{len(element_df):,}" if element_df is not None else "\u2013")
with kpi[1]: kpi_card("Rooms", f"{len(space_df):,}" if has_spaces else "n/a")
with kpi[2]:
    kpi_card("Storeys", f"{element_df['storey'].nunique():,}" if element_df is not None and "storey" in element_df.columns else "\u2013")
with kpi[3]:
    if co2_per_m2:
        diff = co2_per_m2 - SIA_2032_LIMIT
        d_color = COLORS["error_ok"] if diff <= 0 else COLORS["error_warning"]
        d_text = f"{'below' if diff<=0 else 'above'} SIA 2032 limit"
        kpi_card("CO\u2082e / m\u00b2 NFA", f"{co2_per_m2:.1f} kg/m\u00b2", d_text, d_color)
    else:
        kpi_card("CO\u2082e / m\u00b2 NFA", "\u2013", f"Limit: {SIA_2032_LIMIT:.0f} kg/m\u00b2", COLORS["text_light"])
with kpi[4]:
    q_color = COLORS["error_ok"] if score >= 80 else COLORS["error_warning"] if score >= 50 else COLORS["error_critical"]
    kpi_card("Model Quality", f"{score:.0f}%", delta_color=q_color)

st.divider()

# -- Row 1: Main Charts --------------------------------------------------------
col_left, col_right = st.columns(2)

if has_spaces:
    with col_left:
        fig_sun = create_room_sunburst(space_df)
        ev_sun = st.plotly_chart(fig_sun, on_select="rerun", key="ov_sunburst", use_container_width=True)
        if ev_sun and ev_sun.selection.points:
            pt = ev_sun.selection.points[0]
            clicked_label = pt.get("label") or pt.get("id") or ""
            known_storeys = space_df["storey"].dropna().unique().tolist() if "storey" in space_df.columns else []
            if clicked_label in known_storeys:
                prev = st.session_state.get("overview_storey")
                st.session_state.overview_storey = None if clicked_label == prev else clicked_label
                st.rerun()
    with col_right:
        sel_storey = st.session_state.get("overview_storey")
        df_bubble = space_df[space_df["storey"] == sel_storey] if sel_storey and "storey" in space_df.columns else space_df
        if sel_storey:
            st.caption(f"Filtered: Storey **{sel_storey}**")
        st.plotly_chart(create_room_bubble(df_bubble), use_container_width=True, key="ov_bubble")
    if st.session_state.get("overview_storey"):
        if st.button("Reset storey filter", key="ov_reset"):
            st.session_state.overview_storey = None
            st.rerun()
else:
    with col_left:
        st.subheader("Materials by Volume")
        if element_df is not None and not element_df.empty:
            st.plotly_chart(create_material_quantity_bar(element_df, "m\u00b3"), use_container_width=True, key="ov_mat_bar")
        else:
            st.info("No element data available.")
    with col_right:
        st.subheader("Elements by IFC Class")
        if element_df is not None and not element_df.empty:
            st.plotly_chart(create_class_bar_horizontal(element_df), use_container_width=True, key="ov_cls_bar")
        else:
            st.info("No element data available.")

st.divider()

# -- Row 2: CO2 Treemap + Status Donut -----------------------------------------
if mode == "umbau" and element_df is not None and "status" in element_df.columns:
    col_tree, col_donut = st.columns([3, 2])
else:
    col_tree = st.container()
    col_donut = None

with col_tree:
    if element_df is not None and not element_df.empty:
        st.subheader("CO\u2082 Impact by Material")
        st.plotly_chart(create_co2_treemap(element_df), use_container_width=True, key="ov_co2tree")
    else:
        st.info("No CO\u2082 data available.")

if col_donut is not None:
    with col_donut:
        status_counts = element_df["status"].value_counts()
        total_el = len(element_df)
        fig_donut = go.Figure(go.Pie(
            labels=status_counts.index.tolist(),
            values=status_counts.values.tolist(),
            hole=0.58,
            marker=dict(colors=[STATUS_COLORS.get(s, COLORS["neutral"]) for s in status_counts.index], line=dict(color="white", width=2)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            title=dict(text="Status Distribution", font=dict(size=16, color=COLORS["text"]), x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<b>{total_el:,}</b><br><span style='font-size:11px;color:{COLORS['text_light']}'>Elements</span>",
                x=0.5, y=0.5, font_size=18, showarrow=False, font_color=COLORS["text"],
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True, key="ov_donut")

if mode == "umbau" and element_df is not None and "status" in element_df.columns:
    st.divider()
    st.plotly_chart(create_status_distribution(element_df), use_container_width=True, key="ov_status_dist")
