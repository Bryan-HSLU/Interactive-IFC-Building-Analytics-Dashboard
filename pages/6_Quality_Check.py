import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_error_bar,
    create_pset_matrix_heatmap,
)
from src.quality_checker import build_pset_matrix

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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite 1** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)
error_df, quality_summary = get_quality_data()

if not quality_summary:
    st.title("Qualitätsprüfung")
    st.warning("Keine Qualitätsdaten verfügbar.")
    st.stop()

st.title("Qualitätsprüfung")
st.caption("Analysiert wie vollständig und konsistent die IFC-Modelldaten sind.")

CF_KEYS = ["cf_page6_error_cat"]
render_cross_filter_reset("page6", CF_KEYS)

score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)

# ── 1. KPI-Card: Modellqualität (ersetzt Gauge-Chart) ───────────────────────
col_kpi, col_traffic = st.columns([1, 2])

with col_kpi:
    bar_width = max(0.0, min(float(score), 100.0))
    # Farbe des Balkens je nach Score
    if bar_width >= 80:
        bar_color = "#2E86AB"
    elif bar_width >= 50:
        bar_color = "#F39C12"
    else:
        bar_color = "#D94F3D"

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E8E8E8;
            border-radius: 12px;
            padding: 28px 24px 22px 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            text-align: center;
            min-height: 160px;
        ">
            <div style="color: #888; font-size: 13px; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 6px;">
                MODELLQUALITÄT
            </div>
            <div style="font-size: 56px; font-weight: 800; color: #1A1A2E; line-height: 1.1; margin-bottom: 16px;">
                {score:.1f}<span style="font-size: 28px; font-weight: 600; color: #888;">%</span>
            </div>
            <div style="background: #F0F0F0; border-radius: 999px; height: 10px; width: 100%; overflow: hidden;">
                <div style="
                    background: {bar_color};
                    width: {bar_width}%;
                    height: 100%;
                    border-radius: 999px;
                    transition: width 0.4s ease;
                "></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 4px;">
                <span style="font-size: 11px; color: #AAA;">0%</span>
                <span style="font-size: 11px; color: #AAA;">100%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── 2. Qualitätsindikatoren mit farbigen Badges ───────────────────────────
with col_traffic:
    st.subheader("Qualitätsindikatoren")
    st.caption("Zeigt wie viele Elemente wichtige Datenfelder nicht befüllt haben.")

    def _traffic_light(count, label):
        if count == 0:
            badge_text  = "OK"
            badge_bg    = "#A8D5B5"
            badge_color = "#2D2D2D"
            row_bg      = "#EAF6EE"
        elif count <= 10:
            badge_text  = "Warning"
            badge_bg    = "#F5E642"
            badge_color = "#2D2D2D"
            row_bg      = "#FCF9D6"
        else:
            badge_text  = "Critical"
            badge_bg    = "#D94F3D"
            badge_color = "#FFFFFF"
            row_bg      = "#FDEBD0"

        st.markdown(
            f'<div style="background:{row_bg};border-radius:8px;padding:10px 14px;margin:5px 0;'
            f'display:flex;align-items:center;gap:10px;">'
            f'<span style="background:{badge_bg};color:{badge_color};font-size:11px;font-weight:700;'
            f'padding:3px 9px;border-radius:999px;white-space:nowrap;">{badge_text}</span>'
            f'<span style="color:#2D2D2D;flex:1;">{label}</span>'
            f'<span style="font-weight:700;color:#1A1A2E;font-size:15px;">{count}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    _traffic_light(error_counts.get("missing_material", 0), "Elemente ohne Material")
    _traffic_light(error_counts.get("missing_quantity", 0), "Elemente ohne Mengen")
    _traffic_light(error_counts.get("missing_usage",    0), "Räume ohne Nutzung")
    _traffic_light(error_counts.get("missing_storey",   0), "Elemente ohne Geschoss")
    if mode == "umbau":
        _traffic_light(error_counts.get("missing_status", 0), "Elemente ohne Status")

    total_errors = sum(error_counts.values())
    if total_errors == 0:
        st.success(f"Modell vollständig – alle {total_elements:,} Elemente haben die Pflichtfelder befüllt.")
    else:
        st.warning(f"{total_errors} Probleme in {total_elements:,} Elementen gefunden.")

st.divider()

total_errors = sum(error_counts.values())

if total_errors == 0:
    st.success("Keine Fehler gefunden – Ihr IFC-Modell ist vollständig!")
else:
    # ── Chart A: Fehlerbalken | Chart B: Pset-Heatmap ────────────────────────
    st.caption("Auf einen Balken klicken um die Fehlertabelle unten zu filtern. Nochmals klicken zum Zurücksetzen.")
    col_err, col_pset = st.columns(2)

    with col_err:
        st.subheader("Fehler nach Typ")
        fig_err = create_error_bar(error_counts)
        ev_err = st.plotly_chart(fig_err, on_select="rerun", key="cf_p6_error_bar", use_container_width=True)
        if ev_err and ev_err.selection and ev_err.selection.points:
            pt = ev_err.selection.points[0]
            clicked = pt.get("x") or pt.get("y") or pt.get("label")
            label_map = {
                "Kein Material":  "missing_material",
                "Keine Mengen":   "missing_quantity",
                "Kein Geschoss":  "missing_storey",
                "Keine Nutzung":  "missing_usage",
                "Kein Status":    "missing_status",
            }
            mapped = label_map.get(clicked, clicked)
            if mapped and mapped != st.session_state.get("cf_page6_error_cat"):
                st.session_state.cf_page6_error_cat = mapped
                st.rerun()

    with col_pset:
        st.subheader("Pset-Verfügbarkeit nach IFC-Klasse")
        st.caption("Blau = vorhanden, Grau = fehlend.")
        if element_df is not None and not element_df.empty:
            pset_matrix = build_pset_matrix(element_df)
            if pset_matrix is not None and not pset_matrix.empty:
                if len(pset_matrix.columns) > 15:
                    top_cols = pset_matrix.sum().nlargest(15).index
                    pset_matrix = pset_matrix[top_cols]
                st.plotly_chart(create_pset_matrix_heatmap(pset_matrix), use_container_width=True)
            else:
                st.info("Keine Pset-Daten verfügbar.")
        else:
            st.info("Keine Elementdaten verfügbar.")

# ── Fehlerdetail-Tabelle ────────────────────────────────────────────────────────
st.divider()
st.subheader("Fehlerdetails")

has_errors = error_df is not None and not error_df.empty
if has_errors:
    table_df = error_df.copy()
    cf_cat = st.session_state.get("cf_page6_error_cat")
    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]

    display_df = table_df.rename(columns={
        "element_id": "Element-ID",
        "ifc_class":  "IFC-Klasse",
        "storey":     "Geschoss",
        "error_type": "Fehlertyp",
        "severity":   "Schweregrad",
        "description":"Beschreibung",
    })

    def _color_severity(val):
        if val == "critical": return "color: #A04000; font-weight: bold"
        elif val == "warning": return "color: #E67E22"
        return ""

    if "Schweregrad" in display_df.columns:
        st.dataframe(display_df.style.map(_color_severity, subset=["Schweregrad"]), use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.success("Keine Fehler gefunden – Ihr IFC-Modell ist vollständig.")
