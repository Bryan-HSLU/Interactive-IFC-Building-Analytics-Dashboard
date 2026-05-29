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
space_df = get_space_df(filtered=True)

from src.quality_checker import check_quality, calculate_quality_score
error_df, quality_summary = check_quality(element_df, space_df, mode)
quality_summary["score"] = calculate_quality_score(quality_summary)

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


# ── Session State für Fehler-Selektion ────────────────────────────────────────
if "selected_fehler" not in st.session_state:
    st.session_state["selected_fehler"] = None

# ── Indicator Config ──────────────────────────────────────────────────────────
INDICATOR_CONFIG = [
    ("missing_storey", "Ohne Geschoss", "critical"),
    ("missing_material", "Ohne Material", "critical"),
    ("missing_quantity", "Ohne Mengen", "warning"),
    ("missing_usage", "Räume ohne Nutzung", "warning"),
]
if mode == "umbau":
    INDICATOR_CONFIG.append(("missing_status", "Ohne Status", "warning"))

SEVERITY_COLORS = {"critical": "#E07B39", "warning": "#D4A017", "ok": "#A8D5B5"}
SEVERITY_LABELS = {"critical": "Critical", "warning": "Warning", "ok": "OK"}

# Baue ein Lookup: Label → (key, value, severity, color)
indicator_lookup = {}
for key, lbl, sev in INDICATOR_CONFIG:
    val = error_counts.get(key, 0)
    effective_sev = sev if val > 0 else "ok"
    indicator_lookup[lbl] = {
        "key": key,
        "value": val,
        "severity": sev,
        "effective_severity": effective_sev,
        "color": SEVERITY_COLORS[sev] if val > 0 else "#CCCCCC",
    }

# Sortiere absteigend nach Wert
rows_sorted = sorted(indicator_lookup.items(), key=lambda r: r[1]["value"], reverse=True)
labels = [r[0] for r in rows_sorted]
values = [r[1]["value"] for r in rows_sorted]

selected_fehler = st.session_state.get("selected_fehler")

# ── Farben berechnen (Highlight-Logik) ────────────────────────────────────────
bar_colors = []
for lbl in labels:
    info = indicator_lookup[lbl]
    if selected_fehler is None:
        # Kein Filter aktiv → Originalfarben
        bar_colors.append(info["color"])
    elif lbl == selected_fehler:
        # Dieser Balken ist selektiert → Originalfarbe
        bar_colors.append(info["color"])
    else:
        # Alle anderen → Grau
        bar_colors.append("#CCCCCC")

# ── Layout: KPI links, Balkendiagramm rechts ──────────────────────────────────
col_kpi, col_bar = st.columns([1, 2])

# ── KPI-Card (dynamisch) ─────────────────────────────────────────────────────
with col_kpi:
    if selected_fehler and selected_fehler in indicator_lookup:
        fehler_info = indicator_lookup[selected_fehler]
        fehler_count = fehler_info["value"]
        kpi_title = f"QUALITÄT OHNE<br>{selected_fehler.upper()}"
        kpi_value = round((total_elements - fehler_count) / total_elements * 100, 1) if total_elements > 0 else 0
        kpi_subtitle = f"(Gesamt: {score:.1f}%)"
    else:
        kpi_title = "MODELLQUALITÄT"
        kpi_value = score
        kpi_subtitle = ""

    kpi_bar_width = max(0.0, min(float(kpi_value), 100.0))
    kpi_bar_color = "#2E86AB" if kpi_value >= 80 else "#E07B39"

    subtitle_html = ""
    if kpi_subtitle:
        subtitle_html = f'<div style="color: #999; font-size: 12px; margin-top: 12px;">{kpi_subtitle}</div>'

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
                {kpi_title}
            </div>
            <div style="font-size: 72px; font-weight: 800; color: #1A1A2E; line-height: 1.0; margin-bottom: 24px;">
                {kpi_value:.1f}<span style="font-size: 34px; font-weight: 600; color: #888;">%</span>
            </div>
            <div style="background: #F0F0F0; border-radius: 999px; height: 14px; width: 100%; overflow: hidden;">
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
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Horizontales Balkendiagramm (interaktiv) ──────────────────────────────────
with col_bar:
    st.subheader("Qualitätsindikatoren")
    st.caption("Anzahl Elemente mit fehlenden Datenfeldern, nach Schweregrad.")

    # Erweiterte Tooltips mit Schweregrad und Anteil
    hover_texts = []
    for lbl in labels:
        info = indicator_lookup[lbl]
        val = info["value"]
        pct = round(val / total_elements * 100, 1) if total_elements > 0 else 0
        sev_label = SEVERITY_LABELS.get(info["effective_severity"], "OK")
        hover_texts.append(
            f"<b>{lbl}</b><br>"
            f"Anzahl: {val} Elemente<br>"
            f"Anteil: {pct}% der {_fmt(total_elements)} Gesamtelemente<br>"
            f"Schweregrad: {sev_label}"
        )

    fig_hbar = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=bar_colors, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="outside",
            textfont=dict(size=13, color="#1A1A2E"),
            hovertext=hover_texts,
            hoverinfo="text",
            cliponaxis=False,
        )
    )
    max_val = max(values) if values else 1
    fig_hbar.update_layout(
        margin=dict(t=10, b=10, l=10, r=60),
        height=360,
        xaxis=dict(
            title="Anzahl Fehler",
            showgrid=True,
            gridcolor="#F0F0F0",
            zeroline=False,
            range=[0, max_val * 1.35],
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        bargap=0.35,
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
    )

    event_bar = st.plotly_chart(
        fig_hbar,
        use_container_width=True,
        on_select="rerun",
        key="quality_bar_chart",
    )

    # Klick-Interaktion auswerten
    if event_bar and hasattr(event_bar, "selection") and event_bar.selection:
        points = event_bar.selection.get("points", [])
        if points:
            clicked_label = points[0].get("y")
            if clicked_label and clicked_label in indicator_lookup:
                if selected_fehler == clicked_label:
                    # Gleicher Balken erneut geklickt → Selektion aufheben
                    st.session_state["selected_fehler"] = None
                    st.rerun()
                else:
                    st.session_state["selected_fehler"] = clicked_label
                    st.rerun()

    if total_errors == 0:
        st.success(
            f"Modell vollständig – alle {_fmt(total_elements)} Elemente haben die Pflichtfelder befüllt."
        )
    else:
        st.warning(
            f"{_fmt(total_errors)} Probleme in {_fmt(total_elements)} Elementen gefunden."
        )

# ── Detailtabelle bei Fehler-Selektion (volle Breite) ─────────────────────────
if selected_fehler and selected_fehler in indicator_lookup:
    fehler_info = indicator_lookup[selected_fehler]
    fehler_key = fehler_info["key"]
    fehler_count = fehler_info["value"]

    st.divider()

    if fehler_count == 0:
        st.success(f"✓ Keine betroffenen Elemente gefunden für «{selected_fehler}».")
    else:
        st.markdown(f"#### 🔍 Betroffene Elemente – {selected_fehler}")

        if error_df is not None and not error_df.empty:
            filtered_errors = error_df[error_df["error_type"] == fehler_key].copy()

            display_cols = {}
            if "element_id" in filtered_errors.columns:
                display_cols["element_id"] = "Element-ID"
            if "ifc_class" in filtered_errors.columns:
                display_cols["ifc_class"] = "IFC-Klasse"
            if "storey" in filtered_errors.columns:
                display_cols["storey"] = "Geschoss"
            if "description" in filtered_errors.columns:
                display_cols["description"] = "Fehlertyp"

            display_df = filtered_errors.rename(columns=display_cols)
            show_cols = [c for c in display_cols.values() if c in display_df.columns]

            st.dataframe(
                display_df[show_cols],
                use_container_width=True,
                hide_index=True,
            )

    if st.button("✕ Auswahl aufheben", key="reset_fehler", use_container_width=True):
        st.session_state["selected_fehler"] = None
        st.rerun()

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
                lollipop_kpi_title = f"PSET-QUALITÄT: {selected}"
                lollipop_kpi_value = class_completeness[selected]
                lollipop_kpi_missing = class_missing[selected]
                lollipop_kpi_subtitle = f"{lollipop_kpi_missing} von {total_psets} Psets fehlen"
            else:
                lollipop_kpi_title = "PSET-QUALITÄT (GESAMT)"
                overall = (
                    sum(class_completeness.values()) / len(class_completeness)
                    if class_completeness
                    else 0
                )
                lollipop_kpi_value = round(overall, 1)
                lollipop_kpi_subtitle = f"Ø über {len(class_completeness)} IFC-Klassen"

            lollipop_bar_width = max(0.0, min(float(lollipop_kpi_value), 100.0))
            lollipop_bar_color = "#2E86AB" if lollipop_kpi_value >= 50 else "#E07B39"

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
                        {lollipop_kpi_title}
                    </div>
                    <div style="font-size: 64px; font-weight: 800; color: #1A1A2E; line-height: 1.0; margin-bottom: 16px;">
                        {lollipop_kpi_value:.1f}<span style="font-size: 30px; font-weight: 600; color: #888;">%</span>
                    </div>
                    <div style="background: #F0F0F0; border-radius: 999px; height: 12px; width: 100%; overflow: hidden;">
                        <div style="
                            background: {lollipop_bar_color};
                            width: {lollipop_bar_width}%;
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
                        {lollipop_kpi_subtitle}
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
            event_lollipop = st.plotly_chart(
                fig_lollipop,
                use_container_width=True,
                on_select="rerun",
                key="lollipop_chart",
            )

            # Klick-Interaktion auswerten
            if event_lollipop and hasattr(event_lollipop, "selection") and event_lollipop.selection:
                points = event_lollipop.selection.get("points", [])
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
