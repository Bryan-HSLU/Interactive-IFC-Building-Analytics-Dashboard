import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_material_volume_bar,
    create_element_material_stacked_bar,
)
from src.ui_helpers import apply_unit_conversion, unit_caption
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

if element_df is None or element_df.empty:
    st.title("Bauteile & Mengen")
    st.warning("Keine Bauteildaten verfügbar.")
    st.stop()

st.title("Bauteile & Mengen")
st.caption("Umfassende Materialzusammensetzung und Analyse der Mengenverteilung.")

_u_area   = st.session_state.get("unit_area",   "m\u00b2")
_u_volume = st.session_state.get("unit_volume", "m\u00b3")
_u_mass   = st.session_state.get("unit_mass",   "kg")

# Cross filter resets
# Support cross-filtering by Room Usage (from Page 2 Treemap), Material and Class
CF_KEYS = ["cf_page4_class", "cf_page4_material", "cf_page3_usage"]
render_cross_filter_reset("page4", CF_KEYS)

cf_usage = st.session_state.get("cf_page3_usage")
cf_class = st.session_state.get("cf_page4_class")
cf_mat   = st.session_state.get("cf_page4_material")

if cf_usage:
    st.info(f"Aktivierter Filter (von Übersicht): Elemente gefiltert nach Räumen vom Typ **{cf_usage}**")
    if space_df_raw is not None and not space_df_raw.empty:
        valid_storeys = space_df_raw[space_df_raw["usage"] == cf_usage]["storey"].unique()
        if len(valid_storeys) > 0:
            element_df = element_df[element_df["storey"].isin(valid_storeys)]
        else:
            element_df = pd.DataFrame()

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten unter den aktiven Filtern verfügbar.")
    st.stop()

def _apply_cf(df):
    cf_c = st.session_state.get("cf_page4_class")
    cf_m = st.session_state.get("cf_page4_material")
    if cf_c and "ifc_class" in df.columns:
        df = df[df["ifc_class"] == cf_c]
    if cf_m and "material" in df.columns:
        df = df[df["material"] == cf_m]
    return df

# -- KPI Cards -----------------------------------------------------------------
vol_sum = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum(skipna=True)
kpi = st.columns(4)
kpi[0].metric("IFC-Klassen", f"{element_df['ifc_class'].nunique()}")
kpi[1].metric("Bauelemente", f"{len(element_df):,}")
kpi[2].metric("Volumen total", f"{vol_sum:,.1f} m³")
kpi[3].metric("Materialien", f"{element_df['material'].nunique()}" if "material" in element_df.columns else "–")

st.divider()

# -- Chart A (Insight 3): "Welche Materialien sind verbaut – und wie viel?" ----

st.subheader("Mengen nach Materialgruppe")
st.caption("Einheitliche Akzentfarbe #2E86AB (Stahlblau). Absteigend nach Volumen sortiert. Klicken Sie auf einen Balken zum Filtern.")
unit = st.session_state.get("unit_volume", "m³")
fig_mat = create_material_volume_bar(element_df, unit)
fig_mat.update_layout(height=500)

ev_mat = st.plotly_chart(fig_mat, on_select="rerun", key="p4_volume_bar_chart", use_container_width=True)
if ev_mat and ev_mat.selection.points:
    pt = ev_mat.selection.points[0]
    clicked = pt.get("y") or pt.get("label") or ""
    if clicked:
        prev = st.session_state.get("cf_page4_material")
        st.session_state.cf_page4_material = None if clicked == prev else clicked
        st.rerun()

st.divider()

# -- Chart B (Insight 6): "Wie verteilen sich Materialien auf Wand, Boden, Decke?"

st.subheader("Materialanteil pro Bauteilgruppe")
st.caption("100% Stacked Bar Chart zur vergleichenden Zusammensetzung (Decke, Boden, Wand, Fenster, Tür).")
fig_stacked = create_element_material_stacked_bar(element_df)
fig_stacked.update_layout(
    height=500,
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="center",
        x=0.5,
        font=dict(size=11),
    ),
    margin=dict(l=50, r=20, t=50, b=100),
)
st.plotly_chart(fig_stacked, use_container_width=True, key="p4_stacked_bar")

# -- Quantity Takeoff Table ----------------------------------------------------
st.divider()
st.subheader("Element-Mengenliste")
st.caption("Detaillierte Bauteilliste des Modells.")

table_df = _apply_cf(element_df.copy())
search = st.text_input("Suche (Bauteil-Typ oder Material)", key="search_elements", placeholder="z.B. Beton, Wand...")
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["type_name", "material", "ifc_class"]:
        if col_search in table_df.columns:
            mask |= table_df[col_search].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

display_cols = ["element_id", "ifc_class", "type_name", "material", "storey", "area_m2", "volume_m3", "length_m"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "element_id": "ID", "ifc_class": "IFC-Klasse", "type_name": "Typ",
    "material": "Material", "storey": "Geschoss",
    "area_m2": "Fläche (m²)", "volume_m3": "Volumen (m³)", "length_m": "Länge (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Fläche (m²)", "Volumen (m³)", "Länge (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"{len(display_df):,} Elemente angezeigt" + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
