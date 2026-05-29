import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import (
    init_session_state,
    get_element_df,
    get_space_df,
    get_quality_data,
)
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_pset_lollipop_chart
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
total_errors = sum(error_counts.values())


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", "'")


col_kpi, col_bar = st.columns([1, 2])

# ── KPI-Card ──────────────────────────────────────────────────────────────────
with col_kpi:
    bar_width = max(0.0, min(float(score), 100.0))
    bar_color = (
        "#2E86AB" if bar_width >= 80 else ("#F39C12" if bar_width >= 50 else "#D94F3D")
    )
    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #E8E8E8;
            border-radius: 12px;
            padding: 28px 24px 22px 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            text-align: center;
            height: 480px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <div style="color: #888; font-size: 13px; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 8px;">
                MODELLQUALITÄT
            </div>
            <div style="font-size: 72px; font-weight: 800; color: #1A1A2E; line-height: 1.0; margin-bottom: 24px;">
                {score:.1f}<span style="font-size: 34px; font-weight: 600; color: #888;">%</span>
            </div>
            <div style="background: #F0F0F0; border-radius: 999px; height: 14px; width: 100%; overflow: hidden;">
                <div style="
                    background: {bar_color};
                    width: {bar_width}%;
                    height: 100%;
                    border-radius: 999px;
                "></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 6px;">
                <span style="font-size: 11px; color: #AAA;">0%</span>
                <span style="font-size: 11px; color: #AAA;">100%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Horizontales Balkendiagramm ───────────────────────────────────────────────
with col_bar:
    st.subheader("Qualitätsindikatoren")
    st.caption("Anzahl Elemente mit fehlenden Datenfeldern, nach Schweregrad.")

    INDICATOR_CONFIG = [
        ("missing_material", "Ohne Material", "critical"),
        ("missing_quantity", "Ohne Mengen", "warning"),
        ("missing_usage", "Räume ohne Nutzung", "warning"),
        ("missing_storey", "Ohne Geschoss", "critical"),
    ]
    if mode == "umbau":
        INDICATOR_CONFIG.append(("missing_status", "Ohne Status", "warning"))

    COLOR_MAP = {"critical": "#E07B39", "warning": "#D4A017", "ok": "#A8D5B5"}

    rows = [
        {"label": lbl, "value": error_counts.get(key, 0), "severity": sev}
        for key, lbl, sev in INDICATOR_CONFIG
    ]
    rows_sorted = sorted(rows, key=lambda r: r["value"], reverse=True)

    labels = [r["label"] for r in rows_sorted]
    values = [r["value"] for r in rows_sorted]
    colors = [
        COLOR_MAP[r["severity"]] if r["value"] > 0 else "#CCCCCC" for r in rows_sorted
    ]

    fig_hbar = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="outside",
            textfont=dict(size=13, color="#1A1A2E"),
            hovertemplate="<b>%{y}</b><br>%{x} Elemente<extra></extra>",
            cliponaxis=False,
        )
    )
    fig_hbar.update_layout(
        margin=dict(t=10, b=10, l=10, r=60),
        height=360,
        xaxis=dict(
            title="Anzahl Fehler", showgrid=True, gridcolor="#F0F0F0", zeroline=False
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.35,
    )
    st.plotly_chart(fig_hbar, use_container_width=True)

    if total_errors == 0:
        st.success(
            f"Modell vollständig – alle {_fmt(total_elements)} Elemente haben die Pflichtfelder befüllt."
        )
    else:
        st.warning(
            f"{_fmt(total_errors)} Probleme in {_fmt(total_elements)} Elementen gefunden."
        )

st.divider()

# ── Lollipop Chart + Interaktive KPI-Card ─────────────────────────────────────
if element_df is not None and not element_df.empty:
    pset_matrix = build_pset_matrix(element_df)
    if pset_matrix is not None and not pset_matrix.empty:
        total_psets = len(pset_matrix.columns)

        # Berechne Vollständigkeit pro Klasse für die KPI-Verknüpfung
        class_completeness = {}
        class_missing = {}
        for cls in pset_matrix.index:
            present = int((pset_matrix.loc[cls] > 0).sum())
            pct = present / total_psets * 100 if total_psets > 0 else 0
            class_completeness[cls] = round(pct, 1)
            class_missing[cls] = total_psets - present

        # Session State initialisieren
        if "selected_klasse" not in st.session_state:
            st.session_state["selected_klasse"] = None

        col_lollipop_kpi, col_lollipop_chart = st.columns([1, 2])

        # ── Interaktive KPI-Card (links) ──
        with col_lollipop_kpi:
            selected = st.session_state.get("selected_klasse")

            if selected and selected in class_completeness:
                kpi_title = f"PSET-QUALITÄT: {selected}"
                kpi_value = class_completeness[selected]
                kpi_missing = class_missing[selected]
                kpi_subtitle = f"{kpi_missing} von {total_psets} Psets fehlen"
            else:
                kpi_title = "PSET-QUALITÄT (GESAMT)"
                overall = (
                    sum(class_completeness.values()) / len(class_completeness)
                    if class_completeness
                    else 0
                )
                kpi_value = round(overall, 1)
                kpi_subtitle = f"Ø über {len(class_completeness)} IFC-Klassen"

            kpi_bar_width = max(0.0, min(float(kpi_value), 100.0))
            kpi_bar_color = "#2E86AB" if kpi_value >= 50 else "#E07B39"

            st.markdown(
                f"""
                <div style="
                    background: #FFFFFF;
                    border: 1px solid #E8E8E8;
                    border-radius: 12px;
                    padding: 28px 24px 22px 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
                    text-align: center;
                    min-height: 320px;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                ">
                    <div style="color: #888; font-size: 12px; font-weight: 600; letter-spacing: 0.05em; margin-bottom: 8px; word-break: break-word;">
                        {kpi_title}
                    </div>
                    <div style="font-size: 64px; font-weight: 800; color: #1A1A2E; line-height: 1.0; margin-bottom: 16px;">
                        {kpi_value:.1f}<span style="font-size: 30px; font-weight: 600; color: #888;">%</span>
                    </div>
                    <div style="background: #F0F0F0; border-radius: 999px; height: 12px; width: 100%; overflow: hidden;">
                        <div style="
                            background: {kpi_bar_color};
                            width: {kpi_bar_width}%;
                            height: 100%;
                            border-radius: 999px;
                            transition: width 0.3s ease;
                        "></div>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin-top: 6px;">
                        <span style="font-size: 11px; color: #AAA;">0%</span>
                        <span style="font-size: 11px; color: #AAA;">100%</span>
                    </div>
                    <div style="color: #999; font-size: 12px; margin-top: 12px;">
                        {kpi_subtitle}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if selected:
                if st.button(
                    "↩ Gesamtansicht",
                    key="reset_klasse",
                    use_container_width=True,
                ):
                    st.session_state["selected_klasse"] = None
                    st.rerun()

        # ── Lollipop Chart (rechts) ──
        with col_lollipop_chart:
            fig_lollipop = create_pset_lollipop_chart(pset_matrix)
            event = st.plotly_chart(
                fig_lollipop,
                use_container_width=True,
                on_select="rerun",
                key="lollipop_chart",
            )

            # Klick-Interaktion auswerten
            if event and hasattr(event, "selection") and event.selection:
                points = event.selection.get("points", [])
                if points:
                    point = points[0]
                    clicked_class = point.get("y")
                    if clicked_class and clicked_class in class_completeness:
                        if st.session_state.get("selected_klasse") != clicked_class:
                            st.session_state["selected_klasse"] = clicked_class
                            st.rerun()
    else:
        st.info("Keine Pset-Daten verfügbar.")
else:
    st.info("Keine Elementdaten verfügbar.")

# ── Fehlerdetail-Tabelle ──────────────────────────────────────────────────────
st.divider()
st.subheader("Fehlerdetails")

has_errors = error_df is not None and not error_df.empty
if has_errors:
    table_df = error_df.copy()
    cf_cat = st.session_state.get("cf_page6_error_cat")
    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]

    display_df = table_df.rename(
        columns={
            "element_id": "Element-ID",
            "ifc_class": "IFC-Klasse",
            "storey": "Geschoss",
            "error_type": "Fehlertyp",
            "severity": "Schweregrad",
            "description": "Beschreibung",
        }
    )

    def _color_severity(val):
        if val == "critical":
            return "color: #A04000; font-weight: bold"
        elif val == "warning":
            return "color: #E67E22"
        return ""

    if "Schweregrad" in display_df.columns:
        st.dataframe(
            display_df.style.map(_color_severity, subset=["Schweregrad"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.success("Keine Fehler gefunden – Ihr IFC-Modell ist vollständig.")
