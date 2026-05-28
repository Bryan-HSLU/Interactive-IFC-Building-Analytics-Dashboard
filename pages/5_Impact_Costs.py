import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_material_co2_bar,
    create_co2_treemap,
    create_cost_bar,
    create_waterfall_co2,
    create_sankey_material,
    create_slope_co2,
)
from src.ui_helpers import apply_unit_conversion, unit_caption
from src.constants import COLORS
from src.impact_calculator import get_match_coverage, get_unmatched_materials
import plotly.graph_objects as go

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
st.caption("CO₂-Fussabdruck der Baustoffe, Auswertung der Kosten und Ökobilanzierung.")

CF_KEYS = ["cf_page5_material"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

# ── KBOB Coverage & Unmatched Materials list ─────────────────────────────────
coverage = get_match_coverage(element_df)
if coverage < 100:
    unmatched = get_unmatched_materials(element_df)
    if unmatched:
        with st.expander(f"⚠️ {100 - coverage:.0f}% der Elemente ohne KBOB-Zuweisung ({len(unmatched)} Materialien)", expanded=False):
            st.write("Die folgenden Materialien aus Ihrem Modell konnten nicht zugeordnet werden und haben derzeit keinen CO₂-Wert:")
            st.dataframe(pd.DataFrame(unmatched, columns=["Nicht zugeordnete Materialien"]), use_container_width=True, hide_index=True)
            st.caption("Tipp: Fügen Sie diese Begriffe oder Teile davon der `MATERIAL_ALIASES`-Liste in `src/impact_calculator.py` hinzu.")

# KPIs
total_co2 = pd.to_numeric(element_df.get("co2e_total", pd.Series(dtype=float)), errors="coerce").sum()
total_vol = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()
co2_intensity = (total_co2 / total_vol) if total_vol > 0 else 0.0
total_cost = pd.to_numeric(element_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce").sum()

st.subheader("Kennzahlen")
k1, k2, k3 = st.columns(3)
k1.metric("CO₂e total", f"{total_co2:,.0f} kg" if total_co2 > 0 else "–")
k2.metric("CO₂e-Intensität", f"{co2_intensity:,.1f} kg/m³" if co2_intensity > 0 else "–")
k3.metric("Kosten total", f"CHF {total_cost:,.0f}" if total_cost > 0 else "–")

st.divider()

# ── 4️⃣ Material CO2 Chart: "Welches Material verursacht am meisten CO2?" ─────

st.subheader("Ökobilanz nach Materialgruppe")
st.caption("Farbkodierung: Grün (Niedrige Last) ➔ Gelb (Mittlere Last) ➔ Rot (Hohe Last). Die gestrichelte Linie markiert den Durchschnitt.")

cf_mat = st.session_state.get("cf_page5_material")
df_co2 = element_df.copy()
if cf_mat:
    df_co2 = df_co2[df_co2["material"] == cf_mat]

fig_co2 = create_material_co2_bar(df_co2)
st.plotly_chart(fig_co2, use_container_width=True, key="p5_co2_bar")

# ── Advanced Expanders ────────────────────────────────────────────────────────

with st.expander("Weitere Nachhaltigkeits-Analysen (Kosten, Treemap, Wasserfall, Sankey)", expanded=False):
    tab_cost, tab_tree, tab_water, tab_sankey = st.tabs(["Kosten", "Treemap", "Waterfall", "Sankey"])
    with tab_cost:
        if "cost_chf" in element_df.columns:
            fig_cost = create_cost_bar(element_df)
            st.plotly_chart(fig_cost, use_container_width=True)
    with tab_tree:
        fig_tree = create_co2_treemap(element_df)
        st.plotly_chart(fig_tree, use_container_width=True)
    with tab_water:
        fig_water = create_waterfall_co2(element_df)
        st.plotly_chart(fig_water, use_container_width=True)
    with tab_sankey:
        fig_sankey = create_sankey_material(element_df)
        st.plotly_chart(fig_sankey, use_container_width=True)

if mode == "umbau":
    with st.expander("Zirkularitäts- & Umbau-Analyse", expanded=False):
        fig_slope = create_slope_co2(element_df)
        st.plotly_chart(fig_slope, use_container_width=True)

# ── Detail Table ──────────────────────────────────────────────────────────────
st.divider()
st.subheader("Element-Details")
st.caption("Details on demand: Detaillierte Tabelle mit farblicher Hervorhebung hoher Emissionen.")

table_df = element_df.copy()
if cf_mat and "material" in table_df.columns:
    table_df = table_df[table_df["material"] == cf_mat]

display_cols = [c for c in ["element_id", "ifc_class", "material", "volume_m3", "co2e_total"] if c in table_df.columns]
rename_map = {
    "element_id": "Element ID", "ifc_class": "Typ", "material": "Material",
    "volume_m3": "Volumen (m³)", "co2e_total": "CO₂-Wert (kg)"
}
if display_cols:
    shown = table_df[display_cols].rename(columns=rename_map)
    shown = shown.loc[:, ~shown.columns.duplicated()]
    
    # Conditional formatting color-code cell background
    def _co2_style(v):
        try:
            x = float(v)
            if x > 5000:
                return "background-color: #FADBD8; color: #78281F; font-weight: bold;"
            elif x > 1000:
                return "background-color: #FDEBD0; color: #7E5109;"
            return ""
        except Exception:
            return ""
            
    if "CO₂-Wert (kg)" in shown.columns:
        st.dataframe(shown.style.map(_co2_style, subset=["CO₂-Wert (kg)"]), use_container_width=True, hide_index=True)
    else:
        st.dataframe(shown, use_container_width=True, hide_index=True)
else:
    st.info("Keine Detaildaten verfügbar.")
