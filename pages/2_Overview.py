import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_room_stacked_bar, create_co2_treemap

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

element_df_raw = get_element_df(filtered=False)
space_df_raw   = get_space_df(filtered=False)
mode           = st.session_state.get("mode_project", "")
render_sidebar(element_df_raw, space_df_raw, mode)

if not st.session_state.get("ifc_parsed"):
    st.warning("Please upload an IFC file on **Page 1** first.")
    st.stop()

element_df = get_element_df(filtered=True)
space_df   = get_space_df(filtered=True)

st.title("Overview")
st.caption("Gesamtübersicht des Gebäudemodells — Overview first, dann Details.")

CF_KEYS = ["cf_page2_storey", "cf_page2_material"]
render_cross_filter_reset("page2", CF_KEYS)

# ── 1. KPI-Karten (Overview first — Shneiderman's Mantra) ─────────────────────
st.subheader("Kennzahlen")

total_elements = len(element_df) if element_df is not None and not element_df.empty else 0
total_spaces   = len(space_df)   if space_df   is not None and not space_df.empty   else 0

n_doors   = 0
n_windows = 0
n_open    = 0
if element_df is not None and not element_df.empty and "ifc_class" in element_df.columns:
    n_doors   = int((element_df["ifc_class"].str.contains("Door",   case=False, na=False)).sum())
    n_windows = int((element_df["ifc_class"].str.contains("Window", case=False, na=False)).sum())
    n_open    = n_doors + n_windows

total_co2 = 0.0
if element_df is not None and not element_df.empty and "co2e_total" in element_df.columns:
    total_co2 = pd.to_numeric(element_df["co2e_total"], errors="coerce").sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Elemente total",   f"{total_elements:,}")
col2.metric("Räume / Zonen",    f"{total_spaces:,}")
col3.metric("Türen",            f"{n_doors:,}")
col4.metric("Fenster",          f"{n_windows:,}")
col5.metric("Total Öffnungen",  f"{n_open:,}")

if total_co2 > 0:
    st.metric("Graue Energie (CO₂e total)", f"{total_co2:,.0f} kg")

st.divider()

# ── 2. Zoom & Filter: Stacked Bar (Räume nach Geschoss × Nutzung) ─────────────
# Analytische Frage: "Wie verteilt sich die Raumfläche über Geschosse und Nutzungstypen?"
# → Stacked Bar: Teil-Ganzes über Kategorien, Längen direkt vergleichbar

st.subheader("Raumfläche nach Geschoss und Nutzung")
st.caption("Klick auf ein Geschoss filtert die gesamte Seite. Klick nochmal zum Deselektieren.")

if space_df is not None and not space_df.empty:
    storey_order = (
        space_df["storey"].value_counts().index.tolist()
        if "storey" in space_df.columns else None
    )
    fig_bar = create_room_stacked_bar(space_df, storey_order=storey_order)
    ev_bar  = st.plotly_chart(fig_bar, on_select="rerun", key="cf_p2_storey_bar", use_container_width=True)

    if ev_bar and ev_bar.selection.points:
        pt      = ev_bar.selection.points[0]
        clicked = pt.get("x") or pt.get("label")
        st.session_state.cf_page2_storey = (
            None if clicked == st.session_state.get("cf_page2_storey") else clicked
        )
        st.rerun()
else:
    st.info("Keine Raumdaten verfügbar.")

st.divider()

# ── 3. CO₂-Überblick: Treemap als sekundäres Detail-Chart ─────────────────────
# Analytische Frage: "Wie verteilt sich der CO₂-Ausstoss auf Materialgruppen?"
# → Treemap: Anteil + Grösse gleichzeitig, für technisch affine Nutzer
if element_df is not None and not element_df.empty and "co2e_total" in element_df.columns:
    st.subheader("CO₂e-Verteilung nach Material")
    st.caption("Flächengrösse = CO₂e-Anteil. Klick auf Material filtert Material-Filter auf Page 5.")

    fig_co2 = create_co2_treemap(element_df)
    ev_co2  = st.plotly_chart(fig_co2, on_select="rerun", key="cf_p2_co2_treemap", use_container_width=True)

    if ev_co2 and ev_co2.selection.points:
        pt      = ev_co2.selection.points[0]
        clicked = pt.get("label") or pt.get("id", "")
        if "__" in str(clicked):
            clicked = clicked.split("__")[0]
        st.session_state.cf_page2_material = (
            None if clicked == st.session_state.get("cf_page2_material") else clicked
        )
        st.rerun()
