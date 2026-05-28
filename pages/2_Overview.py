import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import (
    create_room_sunburst,
    create_room_bubble,
    create_co2_treemap,
    create_status_distribution,
)
from src.impact_calculator import get_impact_summary
from src.constants import SIA_2032_LIMIT, COLORS, STATUS_COLORS

st.set_page_config(page_title="Overview – IFC Analytics", page_icon=None, layout="wide")
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

# ── Helper: KPI-Card (konsistent mit Seite 5) ────────────────────────────
def _kpi_card(label: str, value: str, delta_text: str = "", delta_color: str = "") -> None:
    delta_html = ""
    if delta_text:
        color = delta_color or COLORS["text_light"]
        delta_html = f'<div style="font-size:0.78rem;color:{color};margin-top:2px;">{delta_text}</div>'
    st.markdown(
        f'<div style="background:rgba(0,0,0,0.03);border-radius:8px;padding:10px 14px;margin-bottom:6px;">'
        f'<div style="font-size:0.8rem;color:{COLORS["text_light"]};">{label}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;color:{COLORS["text"]};">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )

# ── Mode Badge ─────────────────────────────────────────────────────────────────
if mode == "neubau":
    mode_label = "Neubau"
    mode_bg = "#D5EEF0"       # helles Petrol
    mode_border = COLORS["neubau"]
else:
    mode_label = "Umbau / Sanierung"
    mode_bg = "#EDE3D5"       # helles Warm-Braun
    mode_border = COLORS["abbruch"]

st.markdown(
    f'<div style="display:inline-block;background:{mode_bg};border-left:4px solid {mode_border};'
    f'border-radius:4px;padding:4px 14px;font-weight:600;margin-bottom:8px;font-size:14px;">'
    f'{mode_label}</div>',
    unsafe_allow_html=True,
)
st.title("Overview")

# ── KPI Row ─────────────────────────────────────────────────────────────────
_, quality_summary = get_quality_data()
summary = get_impact_summary(element_df, space_df, mode)
score = quality_summary.get("score", 0) if quality_summary else 0
co2_per_m2 = summary.get("co2e_per_m2") if summary else None

kpi = st.columns(5)
with kpi[0]:
    _kpi_card("Bauelemente", f"{len(element_df):,}" if element_df is not None else "–")
with kpi[1]:
    _kpi_card("Räume", f"{len(space_df):,}" if space_df is not None and not space_df.empty else "–")
with kpi[2]:
    _kpi_card(
        "Geschosse",
        f"{element_df['storey'].nunique():,}" if element_df is not None and "storey" in element_df.columns else "–"
    )
with kpi[3]:
    if co2_per_m2:
        diff = co2_per_m2 - SIA_2032_LIMIT
        if diff <= 0:
            d_color = COLORS["error_ok"]
            d_text = f"↓ {abs(diff):.1f} unter SIA 2032"
        else:
            d_color = COLORS["error_warning"]
            d_text = f"↑ {diff:.1f} über SIA 2032"
        _kpi_card("CO₂e / m² NGF", f"{co2_per_m2:.1f} kg/m²", d_text, d_color)
    else:
        _kpi_card("CO₂e / m² NGF", "–", f"Limit: {SIA_2032_LIMIT:.0f} kg/m²·a", COLORS["text_light"])
with kpi[4]:
    q_color = COLORS["error_ok"] if score >= 80 else COLORS["error_warning"] if score >= 50 else COLORS["error_critical"]
    _kpi_card("Modellqualität", f"{score:.0f}%", delta_color=q_color)

st.divider()

# ── Row 1: Sunburst (Raumhierarchie) + Bubble Chart (Fläche × Höhe) ────────────
col_sun, col_bubble = st.columns(2)

with col_sun:
    if space_df is not None and not space_df.empty:
        fig_sun = create_room_sunburst(space_df)
        # Sunburst mit plotly_events – Klick filtert st.session_state.overview_storey
        sel_sun = plotly_events(fig_sun, click_event=True, key="ov_sunburst", override_height=420)
        if sel_sun:
            clicked_label = sel_sun[0].get("label") or sel_sun[0].get("id") or ""
            # Nur Geschoss-Ebene (kein root, kein Nutzungstyp-Leaf)
            known_storeys = space_df["storey"].dropna().unique().tolist() if "storey" in space_df.columns else []
            if clicked_label in known_storeys:
                prev = st.session_state.get("overview_storey")
                st.session_state.overview_storey = None if clicked_label == prev else clicked_label
                st.rerun()
    else:
        st.info("Keine Raumdaten verfügbar.")

with col_bubble:
    if space_df is not None and not space_df.empty:
        # Optionaler Storey-Filter via Sunburst-Klick
        sel_storey = st.session_state.get("overview_storey")
        df_bubble = space_df[space_df["storey"] == sel_storey] if sel_storey and "storey" in space_df.columns else space_df
        if sel_storey:
            st.caption(f"🔍 Gefiltert: Geschoss **{sel_storey}** — [zurücksetzen](?)")  # visual hint
        fig_bubble = create_room_bubble(df_bubble)
        st.plotly_chart(fig_bubble, use_container_width=True, key="ov_bubble")
    else:
        st.info("Keine Raumdaten für Bubble Chart verfügbar.")

# Reset-Button für Sunburst-Filter
if st.session_state.get("overview_storey"):
    if st.button("× Geschoss-Filter zurücksetzen", key="ov_reset"):
        st.session_state.overview_storey = None
        st.rerun()

st.divider()

# ── Row 2: CO2-Treemap (exklusiv hier als Überblick) + Status-Donut (Umbau) ──────
if mode == "umbau" and element_df is not None and "status" in element_df.columns:
    col_tree, col_donut = st.columns([3, 2])
else:
    col_tree = st.container()
    col_donut = None

with col_tree:
    if element_df is not None and not element_df.empty:
        fig_tree = create_co2_treemap(element_df)
        st.plotly_chart(fig_tree, use_container_width=True, key="ov_co2tree")
    else:
        st.info("Keine CO₂-Daten verfügbar.")

if col_donut is not None:
    with col_donut:
        status_counts = element_df["status"].value_counts()
        total_el = len(element_df)
        fig_donut = go.Figure(go.Pie(
            labels=status_counts.index.tolist(),
            values=status_counts.values.tolist(),
            hole=0.58,
            marker=dict(
                colors=[STATUS_COLORS.get(s, COLORS["neutral"]) for s in status_counts.index],
                line=dict(color="white", width=2),
            ),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Anzahl: %{value}<br>Anteil: %{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            title=dict(text="Statusverteilung", font=dict(size=16, color=COLORS["text"]), x=0),
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=20, t=50, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            annotations=[dict(
                text=f"<b>{total_el:,}</b><br><span style='font-size:11px;color:{COLORS['text_light']}'>Elemente</span>",
                x=0.5, y=0.5, font_size=18, showarrow=False, font_color=COLORS["text"],
            )],
        )
        st.plotly_chart(fig_donut, use_container_width=True, key="ov_donut")

# ── Row 3 (Umbau): Statusverteilung pro IFC-Klasse ─────────────────────────
if mode == "umbau" and element_df is not None and "status" in element_df.columns:
    st.divider()
    fig_status = create_status_distribution(element_df)
    st.plotly_chart(fig_status, use_container_width=True, key="ov_status_dist")
