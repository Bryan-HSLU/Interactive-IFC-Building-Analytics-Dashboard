import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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

# ── Donut-Chart Daten ─────────────────────────────────────────────
INDICATOR_LABELS = {
    "missing_material": "Ohne Material",
    "missing_quantity": "Ohne Mengen",
    "missing_usage":    "Räume ohne Nutzung",
    "missing_storey":   "Ohne Geschoss",
    "missing_status":   "Ohne Status",
}
# Blaue Abstufungen: dunkel → hell
BLUE_SHADES = ["#1B3A6B", "#2E6BAD", "#4A9CC7", "#76C1E1", "#B0DFF0"]

donut_labels, donut_values, donut_colors = [], [], []
for i, (key, label) in enumerate(INDICATOR_LABELS.items()):
    if key == "missing_status" and mode != "umbau":
        continue
    val = error_counts.get(key, 0)
    if val > 0:
        donut_labels.append(label)
        donut_values.append(val)
        donut_colors.append(BLUE_SHADES[i % len(BLUE_SHADES)])

# Falls alles 0: kleinen Platzhalter "Kein Fehler"
if not donut_values:
    donut_labels = ["Kein Fehler"]
    donut_values = [1]
    donut_colors = ["#A8D5B5"]

total_errors = sum(error_counts.values())

# ── Layout: KPI-Card (links) | Donut-Chart (rechts) ────────────────────
col_kpi, col_donut = st.columns([1, 2])

with col_kpi:
    bar_width = max(0.0, min(float(score), 100.0))
    bar_color = "#2E86AB" if bar_width >= 80 else ("#F39C12" if bar_width >= 50 else "#D94F3D")

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E8E8E8;
            border-radius: 12px;
            padding: 28px 24px 22px 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            text-align: center;
            height: 340px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="color: #888; font-size: 13px; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 8px;">
                MODELLQUALITÄT
            </div>
            <div style="font-size: 64px; font-weight: 800; color: #1A1A2E; line-height: 1.0; margin-bottom: 20px;">
                {score:.1f}<span style="font-size: 30px; font-weight: 600; color: #888;">%</span>
            </div>
            <div style="background: #F0F0F0; border-radius: 999px; height: 12px; width: 100%; overflow: hidden;">
                <div style="
                    background: {bar_color};
                    width: {bar_width}%;
                    height: 100%;
                    border-radius: 999px;
                "></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                <span style="font-size: 11px; color: #AAA;">0%</span>
                <span style="font-size: 11px; color: #AAA;">100%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_donut:
    st.subheader("Qualitätsindikatoren")
    st.caption("Verteilung der fehlenden Datenfelder nach Typ.")

    fig_donut = go.Figure(go.Pie(
        labels=donut_labels,
        values=donut_values,
        hole=0.55,
        marker=dict(colors=donut_colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+value",
        textfont=dict(size=13),
        hovertemplate="<b>%{label}</b><br>%{value} Elemente<br>%{percent}<extra></extra>",
        direction="clockwise",
        sort=True,
    ))

    # Annotation in der Mitte
    center_text = "Kein Fehler" if total_errors == 0 else f"{total_errors}<br><span style='font-size:11px'>Probleme</span>"
    fig_donut.add_annotation(
        text=f"<b>{total_errors}</b><br>Probleme" if total_errors > 0 else "<b>✓</b><br>Kein Fehler",
        x=0.5, y=0.5,
        font=dict(size=16, color="#1A1A2E"),
        showarrow=False,
    )

    fig_donut.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        height=300,
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.02, y=0.5,
            font=dict(size=12),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig_donut, use_container_width=True)

    if total_errors == 0:
        st.success(f"Modell vollständig – alle {total_elements:,} Elemente haben die Pflichtfelder befüllt.")
    else:
        st.warning(f"{total_errors} Probleme in {total_elements:,} Elementen gefunden.")

st.divider()

if total_errors == 0:
    st.success("Keine Fehler gefunden – Ihr IFC-Modell ist vollständig!")
else:
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
        "element_id":  "Element-ID",
        "ifc_class":   "IFC-Klasse",
        "storey":      "Geschoss",
        "error_type":  "Fehlertyp",
        "severity":    "Schweregrad",
        "description": "Beschreibung",
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
