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
from src.constants import SIA_2032_LIMIT

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

st.title("Impact & Kosten")
st.caption("CO₂-Emissionen und Kosten nach Material und Elementtyp.")

CF_KEYS = ["cf_page5_material"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

# ── KPI-Karten ────────────────────────────────────────────────────────────────
st.subheader("Kennzahlen")

total_co2 = 0.0
total_vol = 0.0
if "co2e_total" in element_df.columns:
    total_co2 = pd.to_numeric(element_df["co2e_total"], errors="coerce").sum()
if "volume_m3" in element_df.columns:
    total_vol = pd.to_numeric(element_df["volume_m3"], errors="coerce").sum()
co2_intensity = (total_co2 / total_vol) if total_vol > 0 else 0.0

total_cost = 0.0
if "cost_chf" in element_df.columns:
    total_cost = pd.to_numeric(element_df["cost_chf"], errors="coerce").sum()

cols = st.columns(4)
cols[0].metric("CO₂e total",       f"{total_co2:,.0f} kg"  if total_co2 > 0 else "–")
cols[1].metric("CO₂e / m³",        f"{co2_intensity:,.1f} kg/m³" if co2_intensity > 0 else "–")
cols[2].metric("Volumen total",     f"{total_vol:,.1f} m³"  if total_vol > 0 else "–")
cols[3].metric("Kosten total",      f"CHF {total_cost:,.0f}" if total_cost > 0 else "–")

st.divider()

# ── Chart A: CO₂-Intensität Bar (Hauptchart, interaktiv) ──────────────────────
# Analytische Frage: "Welche Materialien haben den höchsten CO₂-Ausstoss pro m³?"
# → Horizontal Bar: Rangliste, Labels lesbar, Farbe codiert Intensität (preattentive)
# SIA 380/1 Referenzlinie gibt sofort Kontext ohne zusätzliche Komplexität
st.subheader("CO₂-Intensität nach Material")
st.caption(
    "kg CO₂e pro m³ verbautes Volumen — zeigt welches Material klimaschädlicher ist, "
    "unabhängig von der verbauten Menge. Klick filtert die Tabelle."
)

cf_mat = st.session_state.get("cf_page5_material")

if "co2e_total" in element_df.columns and "volume_m3" in element_df.columns:
    fig_co2 = create_co2_bar(element_df)
    ev_co2  = st.plotly_chart(fig_co2, on_select="rerun", key="cf_p5_co2_bar", use_container_width=True)
    if ev_co2 and ev_co2.selection.points:
        pt      = ev_co2.selection.points[0]
        clicked = pt.get("y") or pt.get("label")
        st.session_state.cf_page5_material = (
            None if clicked == st.session_state.get("cf_page5_material") else clicked
        )
        st.rerun()
else:
    st.info("Keine CO₂-Daten verfügbar — KBOB-Faktoren prüfen.")

# ── CO₂-Anteil Treemap als Drilldown (Details on demand) ──────────────────────
# Analytische Frage: "Wie verteilt sich der absolute CO₂-Ausstoss auf Materialgruppen?"
# → Treemap als sekundäres Detail-Chart, nicht gleichrangig mit dem Hauptchart
if "co2e_total" in element_df.columns:
    with st.expander("▶ CO₂e-Anteile als Treemap (Drilldown)", expanded=False):
        st.caption("Flächengrösse = absoluter CO₂e-Anteil. Material → IFC-Klasse.")
        fig_tree = create_co2_treemap(element_df)
        st.plotly_chart(fig_tree, use_container_width=True)

st.divider()

# ── Detailtabelle mit Conditional Formatting (Details on demand) ───────────────
st.subheader("Elementdetails")
st.caption("Farbkodierung: Rot = hoher CO₂e-Wert. Tabellen sind explizit Visualisierungen (Modul-Grundsatz).")

table_df = element_df.copy()
if cf_mat and "material" in table_df.columns:
    table_df = table_df[table_df["material"] == cf_mat]

display_cols = [c for c in ["element_id", "ifc_class", "storey", "material", "volume_m3", "co2e_total", "cost_chf"] if c in table_df.columns]
if display_cols:
    rename_map = {
        "element_id": "Element ID", "ifc_class": "IFC-Klasse",
        "storey": "Geschoss", "material": "Material",
        "volume_m3": "Volumen (m³)", "co2e_total": "CO₂e (kg)", "cost_chf": "Kosten (CHF)",
    }
    disp = table_df[display_cols].rename(columns=rename_map)

    def _co2_color(val):
        try:
            v = float(val)
            if v > 5000:   return "background-color: #FDECEA; color: #C0392B"
            elif v > 1000: return "background-color: #FEF9E7; color: #D4A017"
            return ""
        except Exception:
            return ""

    if "CO₂e (kg)" in disp.columns:
        st.dataframe(
            disp.style.map(_co2_color, subset=["CO₂e (kg)"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.dataframe(disp, use_container_width=True, hide_index=True)
else:
    st.info("Keine Detaildaten verfügbar.")

st.divider()

# ── Zusatz-Charts (für vertiefende Analyse) ────────────────────────────────────
with st.expander("▶ Weitere Analysen: Kosten, Waterfall, Sankey", expanded=False):
    tab_cost, tab_wf, tab_sankey = st.tabs(["Kosten", "Waterfall", "Sankey"])

    with tab_cost:
        st.caption("Kostentreiber nach Material.")
        if "cost_chf" in element_df.columns:
            st.plotly_chart(create_cost_bar(element_df), use_container_width=True)
        else:
            st.info("Keine Kostendaten.")

    with tab_wf:
        st.caption("CO₂e-Beitrag als Waterfall — zeigt kumulativen Aufbau.")
        st.plotly_chart(create_waterfall_co2(element_df), use_container_width=True)

    with tab_sankey:
        st.caption("Materialflüsse: Material → IFC-Klasse → CO₂-Intensitätsklasse.")
        st.plotly_chart(create_sankey_material(element_df), use_container_width=True)

if mode == "umbau":
    with st.expander("▶ Umbau-Analyse: Bestand vs. Neubau", expanded=False):
        st.plotly_chart(create_slope_co2(element_df), use_container_width=True)
