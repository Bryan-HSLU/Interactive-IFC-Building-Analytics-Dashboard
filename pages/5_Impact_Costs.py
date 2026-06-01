import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_co2_pareto,
    create_sia_gauge,
    create_renovation_waterfall,
    create_circularity_donut,
    create_cost_co2_scatter,
    create_cost_breakdown_bar,
    _classify_material_group,
    _MATERIAL_GROUP_COLORS,
)
from src.ui_helpers import hero_kpi_card, scenario_card, fmt_co2, fmt_chf
from src.impact_calculator import get_match_coverage, get_unmatched_materials
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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite\u00a01** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)

st.title("🌱 Nachhaltigkeit & Kosten")

with st.expander("ℹ️ Was zeigt diese Seite?", expanded=False):
    st.markdown("""
    Diese Seite bewertet den **Ökologischen und wirtschaftlichen Fussabdruck** des Gebäudes:
    - **Klima**: CO\u2082-Emissionen (Grau-Energie) der Baustoffe nach KBOB-Faktoren. Vergleich mit SIA\u00a02032-Grenzwert (11\u00a0kg\u00a0CO\u2082e/m\u00b2\u00b7a).
    - **Kosten**: Baukosten nach Materialgruppe aus KBOB-Einheitspreisen.
    - **Umbau & Zirkularität**: Netto-CO\u2082-Bilanz des Umbaus, Anteil erhaltener Bausubstanz.

    **KBOB** = Koordinationskonferenz der Bau- und Liegenschaftsorgane der öffentlichen Bauherren (Schweizer LCA-Datenbasis).
    **SIA\u00a02032** = Schweizer Norm für den Grenz-CO\u2082-Wert von Gebäuden.
    """)

# ── Base Metrics ──
total_co2 = pd.to_numeric(element_df.get("co2e_total", pd.Series(dtype=float)), errors="coerce").sum()
total_cost = pd.to_numeric(element_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce").sum()
total_grey_energy = pd.to_numeric(element_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce").sum()
total_area = space_df_raw["area_m2"].sum() if space_df_raw is not None and "area_m2" in space_df_raw.columns else 0.0
co2_per_m2 = (total_co2 / total_area) if total_area > 0 else 0.0
energy_per_m2 = (total_grey_energy / total_area) if total_area > 0 else 0.0
_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0

# Dynamic caption
if total_co2 > 0 and "material" in element_df.columns:
    _df_m = element_df.dropna(subset=["co2e_total"]).copy()
    _df_m["co2_n"] = pd.to_numeric(_df_m["co2e_total"], errors="coerce")
    _df_m["mat_grp"] = _df_m["material"].apply(_classify_material_group)
    _agg = _df_m.groupby("mat_grp")["co2_n"].sum()
    if not _agg.empty:
        _top = _agg.idxmax()
        _pct = (_agg.max() / total_co2) * 100
        st.caption(f"**{_top}** verursacht {_pct:.0f}\u00a0% der CO\u2082-Last \u2014 grösster Hebel für SIA\u00a02032")
    else:
        st.caption("CO\u2082-Fussabdruck, Graue Energie und Kosten der Baustoffe.")
else:
    st.caption("CO\u2082-Fussabdruck, Graue Energie und Kosten der Baustoffe.")

CF_KEYS = ["cf_page5_material", "cf_page3_usage"]
render_cross_filter_reset("page5", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten unter den aktiven Filtern verfügbar.")
    st.stop()

st.markdown("<br>", unsafe_allow_html=True)

# ── Hero KPI Row (above tabs, always visible) ──
col1, col2, col3, col4 = st.columns(4)
with col1:
    hero_kpi_card("CO\u2082 TOTAL", f"{total_co2:,.0f}".replace(",", "'"), "kg")
with col2:
    hero_kpi_card("CO\u2082 / NGF", f"{co2_per_m2:,.1f}".replace(",", "'") if total_area > 0 else "\u2013", "kg/m\u00b2")
with col3:
    hero_kpi_card("KOSTEN", f"{total_cost:,.0f}".replace(",", "'"), "CHF")
with col4:
    hero_kpi_card("QUALITÄT", f"{quality_score:.0f}", "%")

st.markdown("<br>", unsafe_allow_html=True)

# KBOB Coverage warning
coverage = get_match_coverage(element_df)
if coverage < 100:
    unmatched = get_unmatched_materials(element_df)
    if unmatched:
        with st.expander(f"⚠️ {100 - coverage:.0f}\u00a0% der Elemente ohne KBOB-Zuweisung ({len(unmatched)} Materialien)", expanded=False):
            st.dataframe(pd.DataFrame(unmatched, columns=["Nicht zugeordnete Materialien"]), use_container_width=True, hide_index=True)

# ── Tabs ──
tabs = ["\ud83c\udf31 Klima", "\ud83d\udcb0 Kosten"]
if mode == "umbau":
    tabs.append("\ud83d\udd04 Umbau & Zirkularität")
tabs.append("\ud83d\udcca Daten")

tab_objects = st.tabs(tabs)
tab_klima = tab_objects[0]
tab_kosten = tab_objects[1]
tab_umbau = tab_objects[2] if mode == "umbau" else None
tab_daten = tab_objects[-1]

# ── Tab: Klima ──
with tab_klima:
    with st.expander("ℹ️ Wie wird CO\u2082 berechnet?", expanded=False):
        st.markdown("""
        Die CO\u2082-Werte stammen entweder direkt aus dem IFC-Modell (ArchiCAD-Attribute) oder werden
        aus **KBOB-Faktoren** (kg\u00a0CO\u2082e pro m\u00b3 Material) multipliziert mit dem Volumen des Bauteils berechnet.
        Der **SIA\u00a02032-Grenzwert** von 11\u00a0kg\u00a0CO\u2082e/m\u00b2\u00b7a ist der Schweizer Zielwert für
        den embodied carbon von Gebäuden (Grau-Energie-bezogene Emissionen).
        """)
    col_pareto, col_gauge = st.columns([2, 1])
    with col_pareto:
        st.subheader("CO\u2082-Treiber")
        st.caption("Welche Materialgruppen verursachen den grössten Anteil? (absteigend, mit kumulierter Linie)")
        st.plotly_chart(create_co2_pareto(element_df), use_container_width=True, config={"displayModeBar": False})
    with col_gauge:
        st.subheader("SIA\u00a02032 Ziel")
        st.caption("Ist-Wert vs. Grenzwert 11\u00a0kg\u00a0CO\u2082e/m\u00b2\u00b7a")
        if total_area > 0:
            st.plotly_chart(create_sia_gauge(co2_per_m2), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Keine NGF verfügbar — SIA-Gauge benötigt Raumdaten (IfcSpace).")

    st.markdown("<br>", unsafe_allow_html=True)

    # Graue Energie (C6) — KPI neben CO2 wenn kein signifikanter Unterschied, sonst eigenes Chart
    _ge_series = pd.to_numeric(element_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce")
    _ge_has_data = _ge_series.notna().any() and _ge_series.sum() > 0
    if _ge_has_data:
        st.subheader("Graue Energie")
        with st.expander("ℹ️ Was ist Graue Energie?", expanded=False):
            st.markdown("""
            **Graue Energie** bezeichnet die gesamte Energie, die für Herstellung, Transport und
            Entsorgung der Baustoffe aufgewendet wird — nicht die Betriebsenergie. Einheit: kWh.
            Quelle: KBOB-Faktoren (kWh\u00a0primclär pro m\u00b3).
            """)
        col_ge1, col_ge2, col_ge_bar = st.columns([1, 1, 3])
        with col_ge1:
            hero_kpi_card("GRAUE ENERGIE", f"{total_grey_energy:,.0f}".replace(",", "'"), "kWh")
        with col_ge2:
            hero_kpi_card("ENERGIE / NGF", f"{energy_per_m2:,.1f}".replace(",", "'") if energy_per_m2 > 0 else "\u2013", "kWh/m\u00b2")
        with col_ge_bar:
            _df_ge = element_df.dropna(subset=["grey_energy_kwh"]).copy()
            _df_ge["ge_num"] = pd.to_numeric(_df_ge["grey_energy_kwh"], errors="coerce").fillna(0)
            _df_ge["mat_group"] = _df_ge["material"].apply(_classify_material_group)
            _agg_ge = _df_ge.groupby("mat_group")["ge_num"].sum().reset_index()
            _agg_ge.columns = ["Materialgruppe", "kWh"]
            _agg_ge = _agg_ge[_agg_ge["kWh"] > 0]
            _is_and = _agg_ge["Materialgruppe"] == "Andere"
            _agg_ge = pd.concat([_agg_ge[_is_and], _agg_ge[~_is_and].sort_values("kWh", ascending=True)], ignore_index=True)
            _colors_ge = [_MATERIAL_GROUP_COLORS.get(m, "#C9CDD3") for m in _agg_ge["Materialgruppe"]]
            _max_ge = _agg_ge["kWh"].max() if not _agg_ge.empty else 1
            fig_ge = go.Figure(go.Bar(
                x=_agg_ge["kWh"], y=_agg_ge["Materialgruppe"], orientation="h",
                marker_color=_colors_ge,
                text=[f"{v:,.0f}\u00a0kWh".replace(",", "'") for v in _agg_ge["kWh"]],
                textposition="outside", cliponaxis=False,
                hovertemplate="<b>%{y}</b><br>Graue Energie: %{x:,.0f}\u00a0kWh<extra></extra>",
            ))
            fig_ge.update_layout(
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
                xaxis=dict(title="kWh", range=[0, _max_ge * 1.35], gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
                yaxis=dict(title=""), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, margin=dict(l=10, r=70, t=20, b=30), height=220,
            )
            st.plotly_chart(fig_ge, use_container_width=True, config={"displayModeBar": False})

# ── Tab: Kosten ──
with tab_kosten:
    with st.expander("ℹ️ Wie werden Kosten berechnet?", expanded=False):
        st.markdown("""
        Baukosten werden aus **KBOB-Einheitspreisen** (CHF\u00a0pro\u00a0m\u00b3) multipliziert mit dem Bauteilvolumen
        berechnet. Dies sind Richtwerte für die Frühphase; keine verbindliche Kostenschatzung.
        """)
    col_cb, col_sc = st.columns([1, 2])
    with col_cb:
        st.subheader("Kosten nach Material")
        st.caption("Gesamtkosten je Materialgruppe (KBOB-Richtwerte, CHF)")
        st.plotly_chart(create_cost_breakdown_bar(element_df), use_container_width=True, config={"displayModeBar": False})
    with col_sc:
        st.subheader("Kosten vs. CO\u2082")
        st.caption("Trade-off: teuer und CO\u2082-intensiv vs. kosteneffizient und klimafreundlich (Punkt-Grösse\u00a0= Volumen)")
        st.plotly_chart(create_cost_co2_scatter(element_df), use_container_width=True, config={"displayModeBar": False})

# ── Tab: Umbau & Zirkularität (nur Umbau-Modus) ──
if mode == "umbau" and tab_umbau is not None:
    with tab_umbau:
        with st.expander("ℹ️ Was zeigt die Umbau-Bilanz?", expanded=False):
            st.markdown("""
            - **Waterfall**: CO\u2082-Bilanz des Umbaus — Bestand (erhalten), Abbruch (verloren), Neubau (hinzugefügt), Netto.
            - **Szenario-Vergleich**: Umbau vs. Ersatzneubau — wie viel CO\u2082 wird durch den Erhalt gespart?
            - **Zirkularität**: Anteil der erhaltenen Bausubstanz am Gesamtvolumen — Massstab für Rückbaubarkeit.
            """)
        col_w, col_s, col_d = st.columns([2, 1, 1])
        with col_w:
            st.subheader("Umbau-CO\u2082-Bilanz")
            st.plotly_chart(create_renovation_waterfall(element_df), use_container_width=True, config={"displayModeBar": False})
        with col_s:
            st.subheader("Szenario-Vergleich")
            df_nb = element_df[element_df["status"] == "Neubau"]
            avg_nb_m3 = (df_nb["co2e_total"].sum() / df_nb["volume_m3"].sum()) if not df_nb.empty and df_nb["volume_m3"].sum() > 0 else 250.0
            total_vol = pd.to_numeric(element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").sum()
            co2_ersatz = total_vol * avg_nb_m3
            scenario_card("Szenario A (Erhalt)", total_co2, fmt_co2)
            st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)
            scenario_card("Szenario B (Ersatzneubau)", co2_ersatz, fmt_co2)
            if co2_ersatz > total_co2:
                delta_pct = (1 - total_co2 / co2_ersatz) * 100
                st.success(f"Einsparung: **{delta_pct:.0f}\u00a0%** durch Umbau")
        with col_d:
            st.subheader("Zirkularität")
            st.caption("Anteil erhaltener Bausubstanz (Volumen)")
            st.plotly_chart(create_circularity_donut(element_df), use_container_width=True, config={"displayModeBar": False})

# ── Tab: Daten ──
with tab_daten:
    st.subheader("Element-Details")
    st.caption("Vollständige Liste aller Bauteile mit berechneten Werten.")
    table_df = element_df.copy()
    display_cols = [c for c in ["element_id", "ifc_class", "material", "volume_m3", "cost_chf", "co2e_total", "grey_energy_kwh", "status"] if c in table_df.columns]
    rename_map = {
        "element_id": "Element ID", "ifc_class": "Typ", "material": "Material",
        "volume_m3": "Volumen (m\u00b3)", "cost_chf": "Kosten (CHF)",
        "co2e_total": "CO\u2082 (kg)", "grey_energy_kwh": "Graue Energie (kWh)", "status": "Status",
    }
    if display_cols:
        shown = table_df[display_cols].rename(columns=rename_map)
        shown = shown.loc[:, ~shown.columns.duplicated()]
        def _co2_style(v):
            try:
                x = float(v)
                if x > 5000: return "background-color: #D62828; color: white; font-weight: bold;"
                elif x > 1000: return "background-color: #FCA311; color: #2D2D2D;"
                return ""
            except Exception: return ""
        if "CO\u2082 (kg)" in shown.columns:
            st.dataframe(shown.style.map(_co2_style, subset=["CO\u2082 (kg)"]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(shown, use_container_width=True, hide_index=True)
