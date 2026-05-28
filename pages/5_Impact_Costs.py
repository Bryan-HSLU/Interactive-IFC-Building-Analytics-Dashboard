import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_co2_treemap, create_cost_bar, create_waterfall_co2, create_sankey_material, create_slope_co2, apply_default_layout
from src.constants import COLORS
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
st.caption("CO₂-Emissionen nach Material und Detailansicht der Elemente.")

CF_KEYS = ["cf_page5_material"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

# KPIs
total_co2 = pd.to_numeric(element_df.get("co2e_total", pd.Series(dtype=float)), errors="coerce").sum()
total_vol = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()
co2_intensity = (total_co2 / total_vol) if total_vol > 0 else 0.0
total_cost = pd.to_numeric(element_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce").sum()

st.subheader("Kennzahlen")
k1, k2, k3 = st.columns(3)
k1.metric("CO₂e total", f"{total_co2:,.0f} kg" if total_co2 > 0 else "–")
k2.metric("CO₂e / m³", f"{co2_intensity:,.1f} kg/m³" if co2_intensity > 0 else "–")
k3.metric("Kosten total", f"CHF {total_cost:,.0f}" if total_cost > 0 else "–")

st.divider()

# Main CO2 material chart
st.subheader("CO₂ nach Material")
st.caption("Welche Materialien haben den höchsten CO₂-Ausstoss? Balkendiagramm als Chart-als-Filter.")

cf_mat = st.session_state.get("cf_page5_material")
df = element_df.dropna(subset=["co2e_total", "material"]).copy() if {"co2e_total", "material"}.issubset(element_df.columns) else pd.DataFrame()
if not df.empty:
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    agg = df.groupby("material")["co2e_total"].sum().reset_index()
    agg = agg[agg["co2e_total"] > 0].sort_values("co2e_total", ascending=False)
    top3 = set(agg.head(3)["material"].tolist())
    colors = []
    for mat in agg["material"]:
        if cf_mat is not None:
            colors.append(COLORS["abbruch"] if mat == cf_mat else COLORS["neutral"])
        else:
            colors.append(COLORS["abbruch"] if mat in top3 else COLORS["neutral"])
    fig_co2 = go.Figure(go.Bar(
        x=agg["co2e_total"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>CO₂e: %{x:,.0f} kg<extra></extra>",
    ))
    apply_default_layout(fig_co2, "CO₂e nach Material")
    fig_co2.update_layout(xaxis_title="CO₂e (kg)", yaxis_title="Material")
    fig_co2.update_xaxes(autorange="reversed")
    fig_co2.add_vline(
        x=11.0,
        line_dash="dash",
        line_color="#3B3B3B",
        line_width=2,
        annotation_text="Referenzwert",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#3B3B3B"),
    )
    ev_co2 = st.plotly_chart(fig_co2, on_select="rerun", key="cf_p5_mat_bar_new", use_container_width=True)
    if ev_co2 and ev_co2.selection.points:
        clicked = ev_co2.selection.points[0].get("y") or ev_co2.selection.points[0].get("label")
        st.session_state.cf_page5_material = None if clicked == st.session_state.get("cf_page5_material") else clicked
        st.rerun()
else:
    st.info("Keine CO₂-Daten verfügbar.")

st.divider()

# CO2 by element type treemap
st.subheader("CO₂ nach Elementtyp")
st.caption("Treemap: Fläche zeigt Anteil, Farbe zeigt Intensität. Kompakt für technisch affine Nutzer.")
if {"co2e_total", "ifc_class", "volume_m3"}.issubset(element_df.columns):
    fig_tree = create_co2_treemap(element_df)
    st.plotly_chart(fig_tree, use_container_width=True)
else:
    st.info("Keine ausreichenden Daten für Treemap verfügbar.")

st.divider()

# Detail table
st.subheader("Elementdetails")
st.caption("Details on demand: Tabelle mit Conditional Formatting für CO₂-Werte.")

table_df = element_df.copy()
if cf_mat and "material" in table_df.columns:
    table_df = table_df[table_df["material"] == cf_mat]

display_cols = [c for c in ["Name", "name", "element_id", "ifc_class", "material", "volume_m3", "co2e_total"] if c in table_df.columns]
rename_map = {
    "Name": "Name", "name": "Name", "element_id": "Element ID", "ifc_class": "Typ",
    "material": "Material", "volume_m3": "Volumen (m³)", "co2e_total": "CO₂-Wert (kg)"
}
if display_cols:
    shown = table_df[display_cols].rename(columns=rename_map)
    shown = shown.loc[:, ~shown.columns.duplicated()]
    def _co2_style(v):
        try:
            x = float(v)
            if x > 5000:
                return "background-color: #F7D9CC; color: #7A2E12"
            elif x > 1000:
                return "background-color: #FBEBDD; color: #8A4B1F"
            return ""
        except Exception:
            return ""
    if "CO₂-Wert (kg)" in shown.columns:
        st.dataframe(shown.style.map(_co2_style, subset=["CO₂-Wert (kg)"]), use_container_width=True, hide_index=True)
    else:
        st.dataframe(shown, use_container_width=True, hide_index=True)
else:
    st.info("Keine Detaildaten verfügbar.")

with st.expander("Weitere Analysen", expanded=False):
    tab_cost, tab_water, tab_sankey = st.tabs(["Kosten", "Waterfall", "Sankey"])
    with tab_cost:
        if "cost_chf" in element_df.columns:
            st.plotly_chart(create_cost_bar(element_df), use_container_width=True)
    with tab_water:
        st.plotly_chart(create_waterfall_co2(element_df), use_container_width=True)
    with tab_sankey:
        st.plotly_chart(create_sankey_material(element_df), use_container_width=True)

if mode == "umbau":
    with st.expander("Umbau-Analyse", expanded=False):
        st.plotly_chart(create_slope_co2(element_df), use_container_width=True)
