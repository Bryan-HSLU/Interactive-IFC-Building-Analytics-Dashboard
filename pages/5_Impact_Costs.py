import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_co2_pareto,
    create_sia_gauge,
    create_renovation_waterfall,
    create_circularity_donut,
    create_cost_co2_scatter,
    create_cost_breakdown_bar,
)
from src.ui_helpers import hero_kpi_card, scenario_card, fmt_co2, fmt_chf
from src.impact_calculator import get_match_coverage, get_unmatched_materials

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

st.title("Impact & Kosten")

# Calculate base metrics
total_co2 = pd.to_numeric(element_df.get("co2e_total", pd.Series(dtype=float)), errors="coerce").sum()
total_cost = pd.to_numeric(element_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce").sum()
total_area = space_df_raw["area_m2"].sum() if space_df_raw is not None and "area_m2" in space_df_raw.columns else 0.0
co2_per_m2 = (total_co2 / total_area) if total_area > 0 else 0.0

_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0

# Dynamic Title
if total_co2 > 0 and "material" in element_df.columns:
    df_m = element_df.dropna(subset=["co2e_total"]).copy()
    df_m["co2_numeric"] = pd.to_numeric(df_m["co2e_total"], errors="coerce")
    agg_co2 = df_m.groupby("material")["co2_numeric"].sum()
    if not agg_co2.empty:
        max_mat = agg_co2.idxmax()
        pct_max = (agg_co2.max() / total_co2) * 100
        st.caption(f"**{max_mat}** verursacht {pct_max:.0f} % der CO₂-Last — grösster Hebel für SIA 2032")
    else:
        st.caption("CO₂-Fussabdruck der Baustoffe, Auswertung der Kosten und Ökobilanzierung.")
else:
    st.caption("CO₂-Fussabdruck der Baustoffe, Auswertung der Kosten und Ökobilanzierung.")

# Support cross-filtering
CF_KEYS = ["cf_page5_material", "cf_page3_usage"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten unter den aktiven Filtern verfügbar.")
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# 1. Hero KPI Row
col1, col2, col3, col4 = st.columns(4)
with col1:
    hero_kpi_card("CO₂ TOTAL", f"{total_co2:,.0f}".replace(",", "'"), "kg")
with col2:
    if total_area > 0:
        hero_kpi_card("CO₂ / NGF", f"{co2_per_m2:,.1f}".replace(",", "'"), "kg/m²")
    else:
        hero_kpi_card("CO₂ / NGF", "–", "kg/m²")
with col3:
    hero_kpi_card("KOSTEN", f"{total_cost:,.0f}".replace(",", "'"), "CHF")
with col4:
    hero_kpi_card("QUALITÄT", f"{quality_score:.0f}", "%")

st.markdown("<br>", unsafe_allow_html=True)

# KBOB Coverage Warnung
coverage = get_match_coverage(element_df)
if coverage < 100:
    unmatched = get_unmatched_materials(element_df)
    if unmatched:
        with st.expander(f"⚠️ {100 - coverage:.0f}% der Elemente ohne KBOB-Zuweisung ({len(unmatched)} Materialien)", expanded=False):
            st.dataframe(pd.DataFrame(unmatched, columns=["Nicht zugeordnete Materialien"]), use_container_width=True, hide_index=True)

# 2. Main Analytics
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("CO₂-Treiber (Pareto)")
    st.plotly_chart(create_co2_pareto(element_df), use_container_width=True, config={"displayModeBar": False})

with col_right:
    st.subheader("SIA 2032 Ziel")
    if total_area > 0:
        st.plotly_chart(create_sia_gauge(co2_per_m2), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Keine Raumdaten für SIA-Normierung verfügbar.")

st.markdown("<br>", unsafe_allow_html=True)

# 3. Umbau-Szenario & Zirkularität
if mode == "umbau":
    st.subheader("Umbau-Bilanz & Zirkularität")
    col_w, col_s, col_d = st.columns([2, 1, 1])
    
    with col_w:
        st.caption("Netto-CO₂-Bilanz des Umbaus")
        st.plotly_chart(create_renovation_waterfall(element_df), use_container_width=True, config={"displayModeBar": False})
        
    with col_s:
        st.caption("Szenario-Vergleich (CO₂)")
        co2_umbau = total_co2
        # Ersatzneubau (alle Volumen * Neubau-Faktor)
        # Approximate by replacing Bestand/Abbruch with Neubau, or simply take entire volume * average neubau intensity
        # For simplicity, let's assume Ersatzneubau = all elements as Neubau. We can approximate this by ignoring status if we stored it, 
        # or just taking a simple factor. Let's use total_vol * avg neubau co2/m3 if possible.
        # Alternatively, we just show a static example or basic sum.
        df_neubau = element_df[element_df["status"] == "Neubau"]
        avg_neubau_m3 = (df_neubau["co2e_total"].sum() / df_neubau["volume_m3"].sum()) if not df_neubau.empty and df_neubau["volume_m3"].sum() > 0 else 250.0
        total_vol = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()
        co2_ersatz = total_vol * avg_neubau_m3
        
        scenario_card("Szenario A (Erhalt)", co2_umbau, fmt_co2)
        st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
        scenario_card("Szenario B (Ersatzneubau)", co2_ersatz, fmt_co2)
        
        if co2_ersatz > co2_umbau:
            delta_pct = (1 - co2_umbau/co2_ersatz) * 100
            st.success(f"Einsparung: **{delta_pct:.0f}%** durch Umbau")
            
    with col_d:
        st.caption("Zirkularität (Volumen)")
        st.plotly_chart(create_circularity_donut(element_df), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

# 4. Kosten-Analyse
st.subheader("Kosten & CO₂ Trade-offs")
col_c1, col_c2 = st.columns([2, 1])

with col_c1:
    st.caption("Verhältnis von Baukosten zu CO₂-Emissionen (Grösse = Volumen)")
    st.plotly_chart(create_cost_co2_scatter(element_df), use_container_width=True, config={"displayModeBar": False})

with col_c2:
    st.caption("Kosten nach Material")
    st.plotly_chart(create_cost_breakdown_bar(element_df), use_container_width=True, config={"displayModeBar": False})

# Detail Table at the bottom
st.divider()
st.subheader("Element-Details")
with st.expander("Tabelle anzeigen", expanded=False):
    table_df = element_df.copy()
    display_cols = [c for c in ["element_id", "ifc_class", "material", "volume_m3", "cost_chf", "co2e_total", "status"] if c in table_df.columns]
    rename_map = {
        "element_id": "Element ID",
        "ifc_class": "Typ",
        "material": "Material",
        "volume_m3": "Volumen (m³)",
        "cost_chf": "Kosten (CHF)",
        "co2e_total": "CO₂-Wert (kg)",
        "status": "Status"
    }
    if display_cols:
        shown = table_df[display_cols].rename(columns=rename_map)
        shown = shown.loc[:, ~shown.columns.duplicated()]

        def _co2_style(v):
            try:
                x = float(v)
                if x > 5000:
                    return "background-color: #D62828; color: white; font-weight: bold;"
                elif x > 1000:
                    return "background-color: #FCA311; color: #2D2D2D;"
                return ""
            except Exception:
                return ""

        if "CO₂-Wert (kg)" in shown.columns:
            st.dataframe(shown.style.map(_co2_style, subset=["CO₂-Wert (kg)"]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(shown, use_container_width=True, hide_index=True)
