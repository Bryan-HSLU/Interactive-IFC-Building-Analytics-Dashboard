import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_class_bar_horizontal,
    create_class_storey_stacked,
    create_material_quantity_bar,
)

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

st.title("Bauteile & Mengen")
st.caption("Analyse der IFC-Elementtypen und verbauten Materialmengen.")

CF_KEYS = ["cf_page4_class", "cf_page4_material"]
render_cross_filter_reset("page4", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

# ── KPI-Karten ────────────────────────────────────────────────────────────────
st.subheader("Kennzahlen")
total_el   = len(element_df)
n_classes  = element_df["ifc_class"].nunique() if "ifc_class" in element_df.columns else 0
n_mats     = element_df["material"].nunique()  if "material"  in element_df.columns else 0
total_vol  = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Elemente",       f"{total_el:,}")
c2.metric("IFC-Klassen",    f"{n_classes}")
c3.metric("Materialien",    f"{n_mats}")
c4.metric("Volumen total",  f"{total_vol:,.1f} m³" if total_vol > 0 else "–")

st.divider()

# ── Chart A: Horizontal Bar — Wie viele Elemente gibt es pro Typ? ─────────────
# Analytische Frage: "Welche IFC-Klassen dominieren das Gebäude?"
# → Horizontal Bar: Rangliste, Labels lesbar, Position = preattentive attribute
st.subheader("Elemente nach IFC-Klasse")
st.caption("Klick auf eine Klasse filtert Stacked Bar und Tabelle. Klick nochmal zum Deselektieren.")

cf_class = st.session_state.get("cf_page4_class")

if "ifc_class" in element_df.columns:
    chart_df = element_df.copy()
    counts   = chart_df["ifc_class"].value_counts().reset_index()
    counts.columns = ["ifc_class", "count"]
    counts = counts.sort_values("count", ascending=True)

    from src.constants import COLORS, CATEGORICAL_COLORS
    import plotly.graph_objects as go
    from src.chart_factory import apply_default_layout

    bar_colors = [
        COLORS["primary"] if (cf_class is None or row["ifc_class"] == cf_class)
        else COLORS["neutral"]
        for _, row in counts.iterrows()
    ]

    fig_class = go.Figure(go.Bar(
        x=counts["count"],
        y=counts["ifc_class"],
        orientation="h",
        marker_color=bar_colors,
        text=counts["count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Anzahl Elemente: %{x}<extra></extra>",
    ))
    apply_default_layout(fig_class, "Anzahl Elemente pro IFC-Klasse")
    fig_class.update_layout(xaxis_title="Anzahl Elemente", yaxis_title="IFC-Klasse")

    ev_class = st.plotly_chart(fig_class, on_select="rerun", key="cf_p4_class_bar", use_container_width=True)
    if ev_class and ev_class.selection.points:
        pt      = ev_class.selection.points[0]
        clicked = pt.get("y") or pt.get("label")
        st.session_state.cf_page4_class = (
            None if clicked == st.session_state.get("cf_page4_class") else clicked
        )
        st.rerun()
else:
    st.info("Keine IFC-Klassendaten verfügbar.")

st.divider()

# ── Chart B: Stacked Bar — Wie verteilen sich Klassen auf Geschosse? ──────────
# Analytische Frage: "Wie viele Elemente welchen Typs gibt es pro Geschoss?"
# → Stacked Bar: Teil-Ganzes über Kategorien
st.subheader("Elemente nach Geschoss und IFC-Klasse")

filter_df = element_df.copy()
if cf_class and "ifc_class" in filter_df.columns:
    filter_df = filter_df[filter_df["ifc_class"] == cf_class]

if not filter_df.empty:
    fig_stacked = create_class_storey_stacked(filter_df)
    st.plotly_chart(fig_stacked, use_container_width=True)
else:
    st.info("Keine Daten für die aktuelle Auswahl.")

st.divider()

# ── Chart C: Material Bar — Welche Materialien sind am meisten verbaut? ───────
# Analytische Frage: "Welche Materialien dominieren nach Volumen?"
# → Horizontal Bar: Rangliste sortiert nach Grösse
st.subheader("Verbautes Volumen nach Material")
st.caption("Klick auf ein Material filtert die Detailtabelle unten.")

cf_mat = st.session_state.get("cf_page4_material")

if "material" in element_df.columns and "volume_m3" in element_df.columns:
    fig_mat = create_material_quantity_bar(element_df)
    ev_mat  = st.plotly_chart(fig_mat, on_select="rerun", key="cf_p4_mat_bar", use_container_width=True)
    if ev_mat and ev_mat.selection.points:
        pt      = ev_mat.selection.points[0]
        clicked = pt.get("y") or pt.get("label")
        st.session_state.cf_page4_material = (
            None if clicked == st.session_state.get("cf_page4_material") else clicked
        )
        st.rerun()
else:
    st.info("Keine Materialdaten verfügbar.")

st.divider()

# ── Detailtabelle (Details on demand) ─────────────────────────────────────────
st.subheader("Elementdetails")

table_df = element_df.copy()
if cf_class and "ifc_class" in table_df.columns:
    table_df = table_df[table_df["ifc_class"] == cf_class]
if cf_mat and "material" in table_df.columns:
    table_df = table_df[table_df["material"] == cf_mat]

display_cols = [c for c in ["element_id", "ifc_class", "storey", "material", "volume_m3", "area_m2"] if c in table_df.columns]
if display_cols:
    rename_map = {
        "element_id": "Element ID", "ifc_class": "IFC-Klasse",
        "storey": "Geschoss", "material": "Material",
        "volume_m3": "Volumen (m³)", "area_m2": "Fläche (m²)",
    }
    st.dataframe(
        table_df[display_cols].rename(columns=rename_map),
        use_container_width=True, hide_index=True
    )
else:
    st.info("Keine Tabellendaten verfügbar.")
