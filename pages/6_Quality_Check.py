import streamlit as st
import pandas as pd
from streamlit_plotly_events import plotly_events
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_quality_gauge, create_error_bar,
    create_status_distribution, create_pset_matrix_heatmap,
    create_upset_plot,
)
from src.quality_checker import build_pset_matrix

st.set_page_config(page_title="Quality Check – IFC Analytics", page_icon="✅", layout="wide")
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
error_df, quality_summary = get_quality_data()

if not quality_summary:
    st.title("✅ Quality Check")
    st.warning("Keine Qualitätsdaten verfügbar.")
    st.stop()

st.title("✅ Quality Check")

# Cross-filter reset
CF_KEYS = ["cf_page6_error_cat", "cf_page6_status_class"]
render_cross_filter_reset("page6", CF_KEYS)

# ── Section A: Quality Score ────────────────────────────────────────────────
col_gauge, col_traffic = st.columns(2)

score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)
total_spaces = quality_summary.get("total_spaces", 0)

with col_gauge:
    fig_gauge = create_quality_gauge(score)
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_traffic:
    st.subheader("Qualitätsindikatoren")

    def _traffic_light(count: int, label: str, show_always: bool = True):
        if not show_always and count == 0:
            return
        if count == 0:
            icon = "✅"
            color = "#D5F5E3"
        elif count <= 10:
            icon = "🟡"
            color = "#FCF3CF"
        else:
            icon = "🔴"
            color = "#FADBD8"
        st.markdown(
            f'<div style="background:{color};border-radius:6px;padding:8px 12px;margin:4px 0;">'
            f'<b>{icon} {label}</b>: {count}</div>',
            unsafe_allow_html=True,
        )

    _traffic_light(error_counts.get("missing_material", 0), "Elemente ohne Material")
    _traffic_light(error_counts.get("missing_quantity", 0), "Elemente ohne Mengenangaben")
    _traffic_light(error_counts.get("missing_usage", 0), "Räume ohne Nutzungszuweisung")
    _traffic_light(error_counts.get("missing_storey", 0), "Elemente ohne Geschoss-Zuordnung")
    if mode == "umbau":
        _traffic_light(error_counts.get("missing_status", 0), "Elemente ohne Status")

# ── Section B: Error Analysis ───────────────────────────────────────────────
st.divider()
col_err, col_status = st.columns(2)

with col_err:
    fig_err = create_error_bar(error_counts)
    sel_err = plotly_events(fig_err, click_event=True, key="cf_p6_error_bar", override_height=380)
    if sel_err:
        clicked = sel_err[0].get("x")
        label_map = {
            "Kein Material": "missing_material",
            "Keine Mengen": "missing_quantity",
            "Kein Geschoss": "missing_storey",
            "Keine Nutzung": "missing_usage",
            "Kein Status": "missing_status",
        }
        if clicked and label_map.get(clicked) != st.session_state.get("cf_page6_error_cat"):
            st.session_state.cf_page6_error_cat = label_map.get(clicked, clicked)
            st.rerun()

with col_status:
    if mode == "umbau":
        fig_status = create_status_distribution(element_df)
        sel_status = plotly_events(fig_status, click_event=True, key="cf_p6_status_bar", override_height=380)
        if sel_status:
            clicked = sel_status[0].get("x")
            if clicked and clicked != st.session_state.get("cf_page6_status_class"):
                st.session_state.cf_page6_status_class = clicked
                st.rerun()
    else:
        # Neubau mode: Pset completeness per class as simple metric
        st.subheader("Pset-Vollständigkeit nach IFC-Klasse")
        if not element_df.empty and "psets" in element_df.columns:
            pset_counts = element_df.groupby("ifc_class")["psets"].apply(
                lambda x: (x.apply(lambda p: len(p) > 0 if isinstance(p, dict) else False)).sum()
            ).reset_index()
            pset_counts.columns = ["IFC-Klasse", "Elemente mit Psets"]
            total_per_class = element_df["ifc_class"].value_counts().reset_index()
            total_per_class.columns = ["IFC-Klasse", "Gesamt"]
            merged = pset_counts.merge(total_per_class, on="IFC-Klasse")
            merged["Vollständigkeit (%)"] = (merged["Elemente mit Psets"] / merged["Gesamt"] * 100).round(1)
            st.dataframe(merged, use_container_width=True, hide_index=True)
        else:
            st.info("Keine Pset-Daten verfügbar.")

# ── Section C: UpSet Plot ───────────────────────────────────────────────────
st.divider()
st.subheader("Fehler-Schnittmengen (UpSet Plot)")
st.caption("Welche Fehlerkombinationen treten gemeinsam auf?")
if error_df is not None and not error_df.empty:
    fig_upset = create_upset_plot(error_df)
    st.plotly_chart(fig_upset, use_container_width=True)
else:
    st.success("✅ Keine Fehler — UpSet Plot nicht notwendig.")

# ── Section D: Pset Matrix ──────────────────────────────────────────────────
st.divider()
st.subheader("Pset-Verfügbarkeitsmatrix")
st.caption("Grün = Pset vorhanden, Rot = fehlt")

if not element_df.empty:
    pset_matrix = build_pset_matrix(element_df)
    if pset_matrix is not None and not pset_matrix.empty:
        # Limit columns for readability
        if len(pset_matrix.columns) > 15:
            top_cols = pset_matrix.sum().nlargest(15).index
            pset_matrix = pset_matrix[top_cols]
        fig_pset = create_pset_matrix_heatmap(pset_matrix)
        st.plotly_chart(fig_pset, use_container_width=True)
    else:
        st.info("Keine Pset-Daten für Matrix verfügbar.")

# ── Section D: Error Detail Table ──────────────────────────────────────────
st.divider()
st.subheader("Fehlerdetails")

if error_df is not None and not error_df.empty:
    table_df = error_df.copy()

    # Apply cross-filters
    cf_cat = st.session_state.get("cf_page6_error_cat")
    cf_cls = st.session_state.get("cf_page6_status_class")

    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]
    if cf_cls and "ifc_class" in table_df.columns:
        table_df = table_df[table_df["ifc_class"] == cf_cls]

    col_rename = {
        "element_id": "Element-ID",
        "ifc_class": "IFC-Klasse",
        "storey": "Geschoss",
        "error_type": "Fehlertyp",
        "severity": "Schweregrad",
        "description": "Beschreibung",
    }
    display_df = table_df.rename(columns=col_rename)

    def _color_severity(val):
        if val == "kritisch":
            return "color: #C0392B; font-weight: bold"
        elif val == "Warnung":
            return "color: #E67E22"
        return ""

    if "Schweregrad" in display_df.columns:
        st.dataframe(
            display_df.style.applymap(_color_severity, subset=["Schweregrad"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Warning if status data missing (Umbau mode)
    if mode == "umbau" and error_counts.get("missing_status", 0) > 0:
        st.warning("⚠️ Berechnungen auf Seite 5 sind möglicherweise unvollständig da Statusdaten fehlen.")
else:
    st.success("✅ Keine Fehler gefunden.")
