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


def render_kpi(label: str, value: str):
    st.markdown(
        f'<div style="background:#FFFFFF; border-top: 4px solid #2E86AB; border-radius: 6px; '
        f'padding: 12px 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 12px; text-align: center;">'
        f'<div style="font-size: 0.8rem; color: #8B8B8B; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{label}</div>'
        f'<div style="font-size: 1.65rem; font-weight: 700; color: #2D2D2D; margin-top: 4px; white-space: nowrap;">{value}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


# Custom column weights to give wider cards (like Gesamtfläche and Total CO2) more horizontal room
kcols = st.columns([1.3, 1.2, 0.8, 0.8, 1.1])
with kcols[0]:
    render_kpi("Gesamtfläche", f"{total_area:,.1f} m²" if total_area > 0 else "–")
with kcols[1]:
    render_kpi("Anzahl Räume", f"{room_count:,}" if room_count > 0 else "–")
with kcols[2]:
    render_kpi("Fenster", f"{window_count:,}" if window_count > 0 else "–")
with kcols[3]:
    render_kpi("Türen", f"{door_count:,}" if door_count > 0 else "–")
with kcols[4]:
    render_kpi("Total CO₂", f"{total_co2:,.0f} kg" if total_co2 > 0 else "–")

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
