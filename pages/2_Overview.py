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

# Mode badge
mode_label = "New Construction (Neubau)" if mode == "neubau" else "Renovation (Umbau / Sanierung)"
mode_color = "#D6EAF8" if mode == "neubau" else "#FDEBD0"
st.markdown(
    f'<div style="display:inline-block;background:{mode_color};border-radius:6px;'
    f'padding:4px 14px;font-weight:600;margin-bottom:8px;font-size:14px;": 