"""Shared UI helper components for all pages."""
import streamlit as st
from src.constants import COLORS


def kpi_card(label: str, value: str, delta_text: str = "", delta_color: str = "") -> None:
    """Render a KPI card with optional delta line using custom Markdown.

    Used instead of st.metric so we can control delta colour freely
    (st.metric only supports 'normal' / 'inverse' / 'off').
    """
    delta_html = ""
    if delta_text:
        color = delta_color or COLORS["text_light"]
        delta_html = f'<div style="font-size:0.78rem;color:{color};margin-top:2px;">{delta_text}</div>'
    st.markdown(
        f'<div style="background:rgba(0,0,0,0.03);border-radius:8px;padding:10px 14px;margin-bottom:6px;">'
        f'<div style="font-size:0.8rem;color:{COLORS["text_light"]};">{label}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;color:{COLORS["text"]};">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )
