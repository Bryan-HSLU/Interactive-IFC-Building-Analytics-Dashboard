import streamlit as st
import pandas as pd
from src.state_manager import (
    init_session_state,
    get_element_df,
    get_space_df,
)
from src.filters import render_sidebar
from src.chart_factory import create_room_treemap
from src.constants import COLORS
from src.ui_helpers import hero_kpi_card
from src.state_manager import get_quality_data

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

st.title("Gebäude-Übersicht")

if has_spaces and "area_m2" in space_df.columns and space_df["area_m2"].sum() > 0:
    total_a = space_df["area_m2"].sum()
    agg = space_df.groupby("usage")["area_m2"].sum()
    if not agg.empty:
        dominant_usage = agg.idxmax()
        pct = (agg.max() / total_a) * 100
        st.caption(f"{len(space_df)} Räume auf {total_a:,.0f} m² — **{dominant_usage}** belegt {pct:.0f} % der NFA")
    else:
        st.caption("Schneller Überblick und räumliche NFA-Verteilung des Gebäudes.")
else:
    st.caption("Schneller Überblick und räumliche NFA-Verteilung des Gebäudes.")

# ── 1️⃣ KPI Cards: "Wie gross ist das Gebäude insgesamt – und was enthält es?" ──

total_area = (
    space_df["area_m2"].sum() if has_spaces and "area_m2" in space_df.columns else 0.0
)
room_count = len(space_df) if has_spaces else 0
window_count = (
    int((element_df["ifc_class"].isin(["IfcWindow", "IfcCurtainWall"])).sum())
    if element_df is not None
    else 0
)
door_count = (
    int((element_df["ifc_class"] == "IfcDoor").sum()) if element_df is not None else 0
)
total_co2 = (
    pd.to_numeric(element_df["co2e_total"], errors="coerce").sum()
    if element_df is not None and "co2e_total" in element_df.columns
    else 0.0
)

_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0
total_cost = (
    pd.to_numeric(element_df["cost_chf"], errors="coerce").sum()
    if element_df is not None and "cost_chf" in element_df.columns
    else 0.0
)
co2_per_m2 = (total_co2 / total_area) if total_area > 0 else 0.0

kcols = st.columns(4)
with kcols[0]:
    hero_kpi_card("CO₂ TOTAL", f"{total_co2:,.0f}".replace(",", "'"), "kg")
with kcols[1]:
    if total_area > 0:
        hero_kpi_card("CO₂ / NGF", f"{co2_per_m2:,.1f}".replace(",", "'"), "kg/m²")
    else:
        hero_kpi_card("CO₂ / NGF", "–", "kg/m²")
with kcols[2]:
    hero_kpi_card("KOSTEN", f"{total_cost:,.0f}".replace(",", "'"), "CHF")
with kcols[3]:
    hero_kpi_card("QUALITÄT", f"{quality_score:.0f}", "%")

st.divider()

# ── 2️⃣ Treemap: "Welcher Raumtyp nimmt wie viel Fläche ein?" ──────────────────

st.subheader("Räumliche Flächenverteilung")
st.caption(
    "Proportionen der Raumtypen nach Netto-Geschossfläche (NFA). Klicken Sie auf einen Typ, um andere Seiten zu filtern."
)

if has_spaces:
    fig_tree = create_room_treemap(space_df)
    ev_tree = st.plotly_chart(
        fig_tree, on_select="rerun", key="ov_treemap", use_container_width=True
    )

    # Master filter logic — only act when the clicked type DIFFERS from
    # the current filter to prevent infinite rerun loops.
    if ev_tree and ev_tree.selection and ev_tree.selection.points:
        pt = ev_tree.selection.points[0]
        clicked = pt.get("label") or pt.get("id") or ""
        if clicked:
            # Clean HTML tags like <b> from the label to get raw string
            clicked_clean = clicked.replace("<b>", "").replace("</b>", "").strip()
            if clicked_clean in ("Gesamt", "root", "Total"):
                if st.session_state.get("cf_page3_usage") != "Gesamt":
                    st.session_state.cf_page3_usage = "Gesamt"
                    st.rerun()
            else:
                if clicked_clean != st.session_state.get("cf_page3_usage"):
                    st.session_state.cf_page3_usage = clicked_clean
                    st.rerun()
else:
    st.info(
        "Dieses Modell enthält keine Räume (IfcSpace) für eine Treemap-Flächenverteilung."
    )
