import streamlit as st
import pandas as pd
import numpy as np
from streamlit_plotly_events import plotly_events
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_class_bar_horizontal, create_class_storey_stacked,
    create_material_quantity_bar, create_diverging_bar,
)

st.set_page_config(page_title="Bauteile & Mengen – IFC Analytics", page_icon="🧱", layout="wide")
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
    st.warning("⚠️ Bitte zuerst eine IFC-Datei auf **Seite 1** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)

if element_df is None or element_df.empty:
    st.title("🧱 Bauteile & Mengen")
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

st.title("🧱 Bauteile & Mengen")

# Cross-filter reset
CF_KEYS = ["cf_page4_class", "cf_page4_material"]
render_cross_filter_reset("page4", CF_KEYS)

# Apply cross-filters to working df
def _apply_cf(df):
    cf_class = st.session_state.get("cf_page4_class")
    cf_mat = st.session_state.get("cf_page4_material")
    if cf_class and "ifc_class" in df.columns:
        df = df[df["ifc_class"] == cf_class]
    if cf_mat and "material" in df.columns:
        df = df[df["material"] == cf_mat]
    return df

# ── Section A: KPI Cards ───────────────────────────────────────────────────
vol_sum = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum(skipna=True)

kpi = st.columns(4)
kpi[0].metric("IFC-Klassen", f"{element_df['ifc_class'].nunique()}")
kpi[1].metric("Elemente gesamt", f"{len(element_df):,}")
kpi[2].metric("Gesamtvolumen", f"{vol_sum:,.1f} m³")
kpi[3].metric("Materialien", f"{element_df['material'].nunique()}" if "material" in element_df.columns else "–")

# ── Section B: Class Analysis ──────────────────────────────────────────────
col_left, col_right = st.columns(2)

storey_df = st.session_state.get("storey_df")
storey_order = None
if isinstance(storey_df, list) and storey_df:
    storey_order = [s["name"] for s in storey_df]
elif isinstance(storey_df, pd.DataFrame) and not storey_df.empty:
    storey_order = storey_df["name"].tolist() if "name" in storey_df.columns else None

with col_left:
    fig_class_bar = create_class_bar_horizontal(element_df)
    sel_class = plotly_events(fig_class_bar, click_event=True, key="cf_p4_class_bar", override_height=380)
    if sel_class:
        clicked = sel_class[0].get("y") or sel_class[0].get("x")
        if clicked and clicked != st.session_state.get("cf_page4_class"):
            st.session_state.cf_page4_class = clicked
            st.rerun()

with col_right:
    fig_storey_stack = create_class_storey_stacked(element_df, storey_order)
    sel_storey = plotly_events(fig_storey_stack, click_event=True, key="cf_p4_storey_stack", override_height=380)

# ── Section C: Material Quantities ────────────────────────────────────────
col_mat, col_div = st.columns(2)

unit = st.session_state.get("unit_volume", "m³")

with col_mat:
    fig_mat = create_material_quantity_bar(element_df, unit)
    sel_mat = plotly_events(fig_mat, click_event=True, key="cf_p4_mat_bar", override_height=380)
    if sel_mat:
        clicked_mat = sel_mat[0].get("y") or sel_mat[0].get("x")
        if clicked_mat and clicked_mat != st.session_state.get("cf_page4_material"):
            st.session_state.cf_page4_material = clicked_mat
            st.rerun()

with col_div:
    if mode == "umbau":
        fig_div = create_diverging_bar(element_df)
    else:
        # Simple bar by material group (same as material quantity but by class)
        fig_div = create_material_quantity_bar(element_df, "m²" if "area_m2" in element_df.columns else unit)
        # Add title override
    plotly_events(fig_div, click_event=True, key="cf_p4_div_bar", override_height=380)

# ── Section D: Quantity Takeoff Table ─────────────────────────────────────
st.subheader("Mengenauswertung")

table_df = _apply_cf(element_df.copy())

# Search filter
search = st.text_input("🔍 Suche (Typ oder Material)", key="search_elements", placeholder="z.B. Beton, Wand…")
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["type_name", "material", "ifc_class"]:
        if col_search in table_df.columns:
            mask |= table_df[col_search].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

# Build display columns
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

st.caption(f"{len(display_df):,} Elemente angezeigt")
st.dataframe(display_df, use_container_width=True, hide_index=True)
