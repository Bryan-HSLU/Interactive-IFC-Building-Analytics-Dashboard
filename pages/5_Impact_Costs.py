import streamlit as st
import pandas as pd
import numpy as np
from streamlit_plotly_events import plotly_events
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_co2_bar, create_co2_treemap, create_cost_bar,
    create_waterfall_co2, create_sankey_material, create_slope_co2,
)
from src.impact_calculator import get_impact_summary
from src.ui_helpers import kpi_card
from src.constants import SIA_2032_LIMIT, COLORS

st.set_page_config(page_title="Impact & Costs – IFC Analytics", page_icon=None, layout="wide")
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

if element_df is None or element_df.empty:
    st.title("Impact & Costs")
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

st.title("Impact & Costs")

# Cross-filter reset
CF_KEYS = ["cf_page5_material", "cf_page5_treemap"]
render_cross_filter_reset("page5", CF_KEYS)

# Impact summary
summary = get_impact_summary(element_df, space_df, mode)

# Coverage info
coverage = summary.get("coverage_pct", 0)
if coverage == 0:
    st.warning("Keine KBOB-Faktoren konnten zugeordnet werden. Überprüfen Sie die Materialnamen im Modell.")
elif coverage < 100:
    st.info(f"{coverage:.0f}% der Elemente konnten KBOB-Faktoren zugeordnet werden.")


def _apply_cf(df):
    cf_mat = st.session_state.get("cf_page5_material")
    cf_tree = st.session_state.get("cf_page5_treemap")
    if cf_mat and "material" in df.columns:
        df = df[df["material"] == cf_mat]
    elif cf_tree and "material" in df.columns:
        df = df[df["material"] == cf_tree]
    return df


# ── Tabs ────────────────────────────────────────────────────────────────────────
tab_co2, tab_cost, tab_zirk = st.tabs(["CO2 & Energie", "Kosten", "Zirkularität"])

with tab_co2:
    kpi = st.columns(4)
    with kpi[0]:
        kpi_card(
            "CO2e gesamt",
            f"{summary['co2e_total']:,.0f} kg" if summary["co2e_total"] else "–"
        )
    with kpi[1]:
        co2_m2 = summary.get("co2e_per_m2")
        if co2_m2:
            diff = co2_m2 - SIA_2032_LIMIT
            if diff <= 0:
                d_color = COLORS["error_ok"]
                d_text = f"↓ {abs(diff):.1f} unter SIA 2032 ({SIA_2032_LIMIT:.0f} kg/m²)"
            else:
                d_color = COLORS["error_warning"]
                d_text = f"↑ {diff:.1f} über SIA 2032 ({SIA_2032_LIMIT:.0f} kg/m²)"
            kpi_card("CO2e pro m² NGF", f"{co2_m2:.1f} kg/m²", d_text, d_color)
        else:
            kpi_card("CO2e pro m² NGF", "–")
    with kpi[2]:
        kpi_card(
            "Graue Energie",
            f"{summary['grey_energy_total']:,.0f} kWh" if summary["grey_energy_total"] else "–"
        )
    with kpi[3]:
        kpi_card(
            "Graue Energie/m²",
            f"{summary['energy_per_m2']:.1f} kWh/m²" if summary.get("energy_per_m2") else "–"
        )

    if summary.get("co2e_per_m2"):
        co2_m2 = summary["co2e_per_m2"]
        pct = co2_m2 / SIA_2032_LIMIT * 100
        if co2_m2 <= SIA_2032_LIMIT:
            sia_bg = "#D5EEF0"
            sia_border = COLORS["error_ok"]
            sia_status = "Innerhalb des Grenzwerts"
        else:
            sia_bg = "#FDF3DC"
            sia_border = COLORS["error_warning"]
            sia_status = "Überschreitung des Grenzwerts"
        st.markdown(
            f'<div style="background:{sia_bg};border-left:4px solid {sia_border};'
            f'border-radius:4px;padding:8px 14px;margin:8px 0;">'
            f'<b>SIA 2032:</b> {sia_status} — '
            f'{co2_m2:.1f} / {SIA_2032_LIMIT:.0f} kg CO2e/m²·a = {pct:.0f}%</div>',
            unsafe_allow_html=True,
        )

    if mode == "umbau" and "status" in element_df.columns:
        sub = st.columns(2)
        co2_neubau = pd.to_numeric(
            element_df[element_df["status"] == "Neubau"].get("co2e_total", pd.Series(dtype=float)),
            errors="coerce"
        ).sum()
        co2_abbruch = pd.to_numeric(
            element_df[element_df["status"] == "Abbruch"].get("co2e_total", pd.Series(dtype=float)),
            errors="coerce"
        ).sum()
        with sub[0]:
            kpi_card("CO2e Neubau", f"{co2_neubau:,.0f} kg")
        with sub[1]:
            kpi_card("CO2e Abbruch", f"{co2_abbruch:,.0f} kg")

    st.divider()
    col_bar, col_tree = st.columns(2)

    with col_bar:
        fig_co2_bar = create_co2_bar(element_df)
        sel_co2 = plotly_events(fig_co2_bar, click_event=True, key="cf_p5_co2_bar", override_height=400)
        if sel_co2:
            clicked = sel_co2[0].get("y") or sel_co2[0].get("x")
            if clicked and clicked != st.session_state.get("cf_page5_material"):
                st.session_state.cf_page5_material = clicked
                st.session_state.cf_page5_treemap = None
                st.rerun()

    with col_tree:
        fig_treemap = create_co2_treemap(element_df)
        sel_tree = plotly_events(fig_treemap, click_event=True, key="cf_p5_treemap", override_height=400)
        if sel_tree:
            clicked = sel_tree[0].get("label") or sel_tree[0].get("id")
            if clicked and clicked not in ("Gesamt", "root"):
                st.session_state.cf_page5_treemap = clicked
                st.session_state.cf_page5_material = clicked
                st.rerun()

    st.divider()
    col_wf, col_sankey = st.columns(2)
    with col_wf:
        fig_wf = create_waterfall_co2(element_df)
        st.plotly_chart(fig_wf, use_container_width=True)
    with col_sankey:
        fig_sankey = create_sankey_material(element_df)
        st.plotly_chart(fig_sankey, use_container_width=True)

with tab_cost:
    kpi_c = st.columns(3)
    with kpi_c[0]:
        kpi_card(
            "Gesamtkosten",
            f"CHF {summary['cost_total']:,.0f}" if summary["cost_total"] else "–"
        )
    with kpi_c[1]:
        kpi_card(
            "Kosten pro m²",
            f"CHF {summary['cost_per_m2']:,.0f}/m²" if summary.get("cost_per_m2") else "–"
        )
    if mode == "umbau" and "status" in element_df.columns:
        cost_neubau = pd.to_numeric(
            element_df[element_df["status"] == "Neubau"].get("cost_chf", pd.Series(dtype=float)),
            errors="coerce"
        ).sum()
        with kpi_c[2]:
            kpi_card("Kosten Neubau", f"CHF {cost_neubau:,.0f}")

    st.divider()
    fig_cost_bar = create_cost_bar(element_df)
    st.plotly_chart(fig_cost_bar, use_container_width=True)

with tab_zirk:
    if mode != "umbau":
        st.info("Diese Ansicht ist nur im Umbau-Modus verfügbar.")
    else:
        fig_slope = create_slope_co2(element_df)
        st.plotly_chart(fig_slope, use_container_width=True)
        st.divider()
        if "status" in element_df.columns:
            total = len(element_df)
            bestand = (element_df["status"] == "Bestand").sum()
            abbruch = (element_df["status"] == "Abbruch").sum()
            neubau = (element_df["status"] == "Neubau").sum()

            reuse_pct = (bestand / total * 100) if total > 0 else 0
            deconstruct_pct = (abbruch / total * 100) if total > 0 else 0

            cost_bestand = pd.to_numeric(
                element_df[element_df["status"] == "Bestand"].get("cost_chf", pd.Series(dtype=float)),
                errors="coerce"
            ).sum()

            zk = st.columns(3)
            with zk[0]:
                kpi_card("Wiederverwendungspotenzial", f"{reuse_pct:.1f}%")
            with zk[1]:
                kpi_card("Anteil rückbaubarer Elemente", f"{deconstruct_pct:.1f}%")
            with zk[2]:
                kpi_card("Geschätzter Residualwert", f"CHF {cost_bestand:,.0f}")

            st.caption("Vereinfachte Schätzung auf Basis von Materialtypen und Statusangaben.")
        else:
            st.warning("Keine Statusdaten für Zirkularitätsanalyse verfügbar.")

# ── Section D: Detail Table ─────────────────────────────────────────────────────
st.divider()
st.subheader("Elementdetails")

table_df = _apply_cf(element_df.copy())

display_cols = ["element_id", "ifc_class", "material", "volume_m3", "co2e_total", "grey_energy_kwh", "cost_chf"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "element_id": "ID", "ifc_class": "IFC-Klasse", "material": "Material",
    "volume_m3": "Volumen (m³)", "co2e_total": "CO2e (kg)",
    "grey_energy_kwh": "Graue Energie (kWh)", "cost_chf": "Kosten (CHF)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)

for num_col in ["Volumen (m³)", "CO2e (kg)", "Graue Energie (kWh)", "Kosten (CHF)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(1)

st.caption(f"{len(display_df):,} Elemente angezeigt | Fehlende Faktoren werden als leer dargestellt")
st.dataframe(display_df, use_container_width=True, hide_index=True)
