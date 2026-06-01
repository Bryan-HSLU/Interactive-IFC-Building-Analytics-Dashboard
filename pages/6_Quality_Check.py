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
from src.constants import COLORS, STATUS_SHAPES

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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite\u00a01** hochladen.")
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

# Resolve metrics before any use
score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)
total_errors = sum(error_counts.values())

st.title("✅ Modellqualität")

with st.expander("ℹ️ Was prüft diese Seite?", expanded=False):
    st.markdown("""
    Die Qualitätsprüfung bewertet, wie vollständig und korrekt das IFC-Modell befüllt ist.
    Für Berechnungen (CO\u2082, Kosten, Mengen) sind bestimmte Attribute zwingend:
    - **Geschoss**: Jedem Bauteil muss eine Etage zugewiesen sein.
    - **Material**: Ohne Materialzuweisung keine KBOB-Berechnung möglich.
    - **Mengen**: Volumen oder Fläche benötigt für alle Mengennachweise.
    - **Psets** (Property Sets): Strukturierte IFC-Attribute, die Fachmodelle austauschen.

    **Qualitätsscore** = Anteil der Elemente ohne kritische Fehler (0\u2013100\u00a0%).
    """)

_MSG_MAP = {
    "missing_storey": "Elemente ohne Geschosszuweisung",
    "missing_material": "Elemente ohne Material",
    "missing_quantity": "Elemente ohne Mengenangaben",
    "missing_usage": "Räume ohne Nutzung",
    "missing_status": "Elemente ohne Status",
}
if total_errors > 0 and error_counts:
    worst_key = max(error_counts, key=error_counts.get)
    st.caption(f"{error_counts[worst_key]:,} {_MSG_MAP.get(worst_key, 'Fehler')} — Mengen unsicher".replace(",", "'"))
else:
    st.caption("Modell ist fehlerfrei und konsistent.")

CF_KEYS = ["cf_page6_error_cat"]
render_cross_filter_reset("page6", CF_KEYS)

def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", "'")

if "selected_fehler" not in st.session_state:
    st.session_state["selected_fehler"] = None

INDICATOR_CONFIG = [
    ("missing_storey", "Ohne Geschoss", "critical"),
    ("missing_material", "Ohne Material", "critical"),
    ("missing_quantity", "Ohne Mengen", "warning"),
    ("missing_usage", "Räume ohne Nutzung", "warning"),
]
if mode == "umbau":
    INDICATOR_CONFIG.append(("missing_status", "Ohne Status", "warning"))

SEVERITY_COLORS = {"critical": COLORS["error_critical"], "warning": COLORS["error_warning"], "ok": COLORS["error_ok"]}
SEVERITY_LABELS = {"critical": f"{STATUS_SHAPES['critical']} Critical", "warning": f"{STATUS_SHAPES['warning']} Warning", "ok": f"{STATUS_SHAPES['ok']} OK"}

indicator_lookup = {}
for key, lbl, sev in INDICATOR_CONFIG:
    val = error_counts.get(key, 0)
    effective_sev = sev if val > 0 else "ok"
    indicator_lookup[lbl] = {
        "key": key, "value": val, "severity": sev,
        "effective_severity": effective_sev,
        "color": SEVERITY_COLORS[sev] if val > 0 else "#CCCCCC",
    }

rows_sorted = sorted(indicator_lookup.items(), key=lambda r: r[1]["value"], reverse=True)
labels = [r[0] for r in rows_sorted]
values = [r[1]["value"] for r in rows_sorted]
selected_fehler = st.session_state.get("selected_fehler")

bar_colors = []
for lbl in labels:
    info = indicator_lookup[lbl]
    if selected_fehler is None or lbl == selected_fehler:
        bar_colors.append(info["color"])
    else:
        bar_colors.append("#CCCCCC")

# ── Tabs ──
tab_overview, tab_pset, tab_struktur = st.tabs(["📊 Übersicht", "📋 Pset-Abdeckung", "🔧 Struktur"])

# ── Tab: Übersicht ──
with tab_overview:
    col_kpi, col_bar = st.columns([1, 2])
    with col_kpi:
        selected = st.session_state.get("selected_fehler")
        if selected and selected in indicator_lookup:
            fe_info = indicator_lookup[selected]
            fe_count = fe_info["value"]
            kpi_title = f"QUALITÄT OHNE<br>{selected.upper()}"
            kpi_value = round((total_elements - fe_count) / total_elements * 100, 1) if total_elements > 0 else 0
            kpi_subtitle = f"(Gesamt: {score:.1f}%)"
        else:
            kpi_title = "MODELLQUALITÄT"
            kpi_value = score
            kpi_subtitle = ""

        kpi_bar_width = max(0.0, min(float(kpi_value), 100.0))
        kpi_bar_color = "#2E86AB" if kpi_value >= 80 else "#E07B39"
        subtitle_html = f'<div style="color:#999;font-size:12px;margin-top:12px;">{kpi_subtitle}</div>' if kpi_subtitle else ""
        st.markdown(
            f"""<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;
            padding:28px 24px 22px 24px;box-shadow:0 2px 8px rgba(0,0,0,0.06);
            text-align:center;height:480px;display:flex;flex-direction:column;justify-content:center;">
                <div style="color:#888;font-size:13px;font-weight:600;letter-spacing:0.05em;margin-bottom:8px;">{kpi_title}</div>
                <div style="font-size:72px;font-weight:800;color:#1A1A2E;line-height:1.0;margin-bottom:24px;">
                    {kpi_value:.1f}<span style="font-size:34px;font-weight:600;color:#888;">%</span></div>
                <div style="background:#F0F0F0;border-radius:999px;height:14px;width:100%;overflow:hidden;">
                    <div style="background:{kpi_bar_color};width:{kpi_bar_width}%;height:100%;border-radius:999px;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:6px;">
                    <span style="font-size:11px;color:#AAA;">0%</span>
                    <span style="font-size:11px;color:#AAA;">100%</span>
                </div>{subtitle_html}
            </div>""",
            unsafe_allow_html=True,
        )

    with col_bar:
        st.subheader("Qualitätsindikatoren")
        with st.expander("ℹ️ Was bedeuten die Indikatoren?", expanded=False):
            st.markdown("""
            | Indikator | Bedeutung | Auswirkung |
            |---|---|---|
            | **Ohne Geschoss** | Bauteil keiner Etage zugeordnet | CO\u2082-Verteilung per Geschoss unmöglich |
            | **Ohne Material** | Kein Materialname vorhanden | Keine KBOB-Berechnung (CO\u2082, Kosten) |
            | **Ohne Mengen** | Kein Volumen/Fläche angegeben | Mengenauswertung unvollständig |
            | **Räume ohne Nutzung** | IfcSpace ohne Nutzungstyp | NFA-Verteilung verfälscht |
            | **Ohne Status** | Kein Bestand/Neubau/Abbruch | Umbau-Bilanz nicht berechenbar |
            """)
        hover_texts = []
        for lbl in labels:
            info = indicator_lookup[lbl]
            val = info["value"]
            pct = round(val / total_elements * 100, 1) if total_elements > 0 else 0
            sev_label = SEVERITY_LABELS.get(info["effective_severity"], "OK")
            hover_texts.append(f"<b>{lbl}</b><br>Anzahl: {val}<br>Anteil: {pct}%<br>Schweregrad: {sev_label}")

        fig_hbar = go.Figure(go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color=bar_colors, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="outside", textfont=dict(size=13, color="#1A1A2E"),
            hovertext=hover_texts, hoverinfo="text", cliponaxis=False,
        ))
        max_val = max(values) if values else 1
        fig_hbar.update_layout(
            margin=dict(t=10, b=10, l=10, r=60), height=360,
            xaxis=dict(title="Anzahl Fehler", showgrid=True, gridcolor="#F0F0F0", zeroline=False, range=[0, max_val * 1.35]),
            yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, bargap=0.35,
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
        )
        event_bar = st.plotly_chart(fig_hbar, use_container_width=True, on_select="rerun", key="quality_bar_chart")
        if event_bar and hasattr(event_bar, "selection") and event_bar.selection:
            points = event_bar.selection.get("points", [])
            if points:
                clicked_label = points[0].get("y")
                if clicked_label and clicked_label in indicator_lookup:
                    if selected_fehler == clicked_label:
                        st.session_state["selected_fehler"] = None
                        st.rerun()
                    else:
                        st.session_state["selected_fehler"] = clicked_label
                        st.rerun()

        if total_errors == 0:
            st.success(f"Modell vollständig – alle {_fmt(total_elements)} Elemente haben die Pflichtfelder befüllt.")
        else:
            st.warning(f"{_fmt(total_errors)} Probleme in {_fmt(total_elements)} Elementen gefunden.")

    # Detail table on click
    if selected_fehler and selected_fehler in indicator_lookup:
        fe_info = indicator_lookup[selected_fehler]
        fe_key = fe_info["key"]
        fe_count = fe_info["value"]
        st.divider()
        if fe_count == 0:
            st.success(f"✓ Keine betroffenen Elemente für \u00ab{selected_fehler}\u00bb.")
        else:
            st.markdown(f"#### 🔍 Betroffene Elemente – {selected_fehler}")
            if error_df is not None and not error_df.empty:
                filtered_errors = error_df[error_df["error_type"] == fe_key].copy()
                display_cols = {}
                for c in ["element_id", "ifc_class", "storey", "description"]:
                    if c in filtered_errors.columns:
                        display_cols[c] = {"element_id": "Element-ID", "ifc_class": "IFC-Klasse", "storey": "Geschoss", "description": "Fehlertyp"}.get(c, c)
                display_df = filtered_errors.rename(columns=display_cols)
                show_cols = [v for v in display_cols.values() if v in display_df.columns]
                st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
        if st.button("✕ Auswahl aufheben", key="reset_fehler", use_container_width=True):
            st.session_state["selected_fehler"] = None
            st.rerun()

# ── Tab: Pset-Abdeckung ──
with tab_pset:
    with st.expander("ℹ️ Was sind Psets?", expanded=False):
        st.markdown("""
        **Property Sets (Psets)** sind strukturierte Attributgruppen in IFC, z.\u00a0B. `Pset_WallCommon`
        für Wände mit Attributen wie Feuerwiderstand, Wärmedurchgang usw.
        Vollständige Psets sind Voraussetzung für den Datenaustausch zwischen Fachmodellen (Tragwerk, Haustechnik).
        """)
    if element_df is not None and not element_df.empty:
        pset_matrix = build_pset_matrix(element_df)
        if pset_matrix is not None and not pset_matrix.empty:
            total_psets = len(pset_matrix.columns)
            class_completeness = {}
            class_missing = {}
            for cls in pset_matrix.index:
                present = int((pset_matrix.loc[cls] > 0).sum())
                pct = present / total_psets * 100 if total_psets > 0 else 0
                class_completeness[cls] = round(pct, 1)
                class_missing[cls] = total_psets - present

            if "selected_klasse" not in st.session_state:
                st.session_state["selected_klasse"] = None

            col_lkpi, col_lchrt = st.columns([1, 2])
            with col_lkpi:
                sel_cls = st.session_state.get("selected_klasse")
                if sel_cls and sel_cls in class_completeness:
                    lkpi_title = f"PSET: {sel_cls}"
                    lkpi_val = class_completeness[sel_cls]
                    lkpi_sub = f"{class_missing[sel_cls]} von {total_psets} Psets fehlen"
                else:
                    lkpi_title = "PSET-QUALITÄT (\u00d8)"
                    overall = sum(class_completeness.values()) / len(class_completeness) if class_completeness else 0
                    lkpi_val = round(overall, 1)
                    lkpi_sub = f"\u00d8 über {len(class_completeness)} IFC-Klassen"

                lkpi_bw = max(0.0, min(float(lkpi_val), 100.0))
                lkpi_bc = "#2E86AB" if lkpi_val >= 50 else "#E07B39"
                st.markdown(
                    f"""<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;
                    padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center;min-height:260px;
                    display:flex;flex-direction:column;justify-content:center;">
                        <div style="color:#888;font-size:12px;font-weight:600;margin-bottom:8px;word-break:break-word;">{lkpi_title}</div>
                        <div style="font-size:56px;font-weight:800;color:#1A1A2E;line-height:1.0;margin-bottom:16px;">
                            {lkpi_val:.1f}<span style="font-size:26px;color:#888;">%</span></div>
                        <div style="background:#F0F0F0;border-radius:999px;height:12px;width:100%;overflow:hidden;">
                            <div style="background:{lkpi_bc};width:{lkpi_bw}%;height:100%;border-radius:999px;"></div>
                        </div>
                        <div style="color:#999;font-size:12px;margin-top:10px;">{lkpi_sub}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if sel_cls:
                    if st.button("↩ Gesamtansicht", key="reset_klasse", use_container_width=True):
                        st.session_state["selected_klasse"] = None
                        st.rerun()

            with col_lchrt:
                fig_lollipop = create_pset_lollipop_chart(pset_matrix)
                event_lollipop = st.plotly_chart(fig_lollipop, use_container_width=True, on_select="rerun", key="lollipop_chart")
                if event_lollipop and hasattr(event_lollipop, "selection") and event_lollipop.selection:
                    pts = event_lollipop.selection.get("points", [])
                    if pts:
                        clicked_cls = pts[0].get("y")
                        if clicked_cls and clicked_cls in class_completeness:
                            if st.session_state.get("selected_klasse") != clicked_cls:
                                st.session_state["selected_klasse"] = clicked_cls
                                st.rerun()
        else:
            st.info("Keine Pset-Daten verfügbar.")
    else:
        st.info("Keine Elementdaten verfügbar.")

# ── Tab: Struktur ──
with tab_struktur:
    st.subheader("Strukturelle Vollständigkeit")
    with st.expander("ℹ️ Was wird hier geprüft?", expanded=False):
        st.markdown("""
        Zusätzliche Prüfungen, die über die Basis-Fehler hinausgehen:
        - **Ohne Geschoss-Zuordnung**: Elemente, bei denen `storey` fehlt oder nicht erkannt wurde.
        - **Ohne Bauteiltyp**: Elemente ohne `type_name` — erschwert die Filterung und Auswertung.
        - **Ohne Material**: Anteil Elemente ohne Materialzuweisung (separat nach IFC-Klasse).
        """)

    if element_df is not None and not element_df.empty:
        col_s1, col_s2, col_s3 = st.columns(3)

        # Check 1: ohne Geschoss
        with col_s1:
            if "storey" in element_df.columns:
                no_storey = element_df[element_df["storey"].isin(["", "nan", "Nicht zugeordnet", None]) | element_df["storey"].isna()]
                n_no_storey = len(no_storey)
                pct_ns = n_no_storey / len(element_df) * 100 if len(element_df) > 0 else 0
                color_ns = COLORS["error_critical"] if pct_ns > 10 else (COLORS["error_warning"] if pct_ns > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_ns};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">OHNE GESCHOSS</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_storey)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_ns:.1f}% der Elemente</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">Bauteil keiner Etage zugewiesen — CO₂-Verteilung per Geschoss unmöglich.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Spalte `storey` nicht verfügbar.")

        # Check 2: ohne type_name
        with col_s2:
            if "type_name" in element_df.columns:
                no_type = element_df[element_df["type_name"].isin(["", "nan", None]) | element_df["type_name"].isna()]
                n_no_type = len(no_type)
                pct_nt = n_no_type / len(element_df) * 100 if len(element_df) > 0 else 0
                color_nt = COLORS["error_critical"] if pct_nt > 20 else (COLORS["error_warning"] if pct_nt > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_nt};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">OHNE BAUTEILTYP</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_type)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_nt:.1f}% der Elemente</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">Kein `type_name` — erschwert Filterung und Bauteilklassifikation.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Spalte `type_name` nicht verfügbar.")

        # Check 3: ohne Material
        with col_s3:
            if "material" in element_df.columns:
                no_mat = element_df[element_df["material"].isin(["", "nan", "Unbekannt", None]) | element_df["material"].isna()]
                n_no_mat = len(no_mat)
                pct_nm = n_no_mat / len(element_df) * 100 if len(element_df) > 0 else 0
                color_nm = COLORS["error_critical"] if pct_nm > 15 else (COLORS["error_warning"] if pct_nm > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_nm};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">OHNE MATERIAL</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_mat)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_nm:.1f}% der Elemente</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">Keine KBOB-Berechnung (CO₂, Kosten) ohne Materialzuweisung möglich.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Spalte `material` nicht verfügbar.")

        # Material-Abdeckung je IFC-Klasse
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Materialabdeckung je IFC-Klasse")
        st.caption("Anteil Elemente mit Materialzuweisung pro IFC-Typ — zeigt, welche Klassen besonders lückenhaft modelliert sind.")
        if "ifc_class" in element_df.columns and "material" in element_df.columns:
            _df_mc = element_df.copy()
            _df_mc["has_material"] = ~(_df_mc["material"].isin(["", "nan", "Unbekannt", None]) | _df_mc["material"].isna())
            _mc_agg = _df_mc.groupby("ifc_class")["has_material"].agg(["sum", "count"]).reset_index()
            _mc_agg.columns = ["ifc_class", "with_mat", "total"]
            _mc_agg["pct"] = (_mc_agg["with_mat"] / _mc_agg["total"] * 100).round(1)
            _mc_agg = _mc_agg.sort_values("pct", ascending=True)
            _colors_mc = ["#2E86AB" if p >= 80 else ("#E07B39" if p >= 40 else "#C44536") for p in _mc_agg["pct"]]
            fig_mc = go.Figure(go.Bar(
                x=_mc_agg["pct"], y=_mc_agg["ifc_class"], orientation="h",
                marker_color=_colors_mc,
                text=[f"{p:.0f}%" for p in _mc_agg["pct"]],
                textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>%{x:.1f}% mit Material (%{customdata[0]} von %{customdata[1]})<extra></extra>",
                customdata=list(zip(_mc_agg["with_mat"], _mc_agg["total"])),
            ))
            fig_mc.update_layout(
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
                xaxis=dict(title="% mit Material", range=[0, 115], ticksuffix="%", gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
                yaxis=dict(title=""), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, margin=dict(l=10, r=50, t=20, b=30),
            )
            st.plotly_chart(fig_mc, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Keine Elementdaten verfügbar.")
