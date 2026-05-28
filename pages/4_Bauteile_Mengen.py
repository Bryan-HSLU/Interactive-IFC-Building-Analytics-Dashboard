import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.constants import COLORS, CATEGORICAL_COLORS
from src.chart_factory import apply_default_layout

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
    st.warning("Please upload an IFC file on **Page 1** first.")
    st.stop()

element_df = get_element_df(filtered=True)

st.title("Bauteile & Mengen")
st.caption("Overview first: Kennzahlen und Elementverteilung. Danach Filter und Details.")

CF_KEYS = ["cf_page4_class", "cf_page4_material"]
render_cross_filter_reset("page4", CF_KEYS)

if element_df is None or element_df.empty:
    st.warning("Keine Elementdaten verfügbar.")
    st.stop()

# Overview KPIs
st.subheader("Kennzahlen")
total_el = len(element_df)
n_doors = int((element_df.get("ifc_class", pd.Series(dtype=str)).astype(str).str.contains("Door", case=False, na=False)).sum())
n_windows = int((element_df.get("ifc_class", pd.Series(dtype=str)).astype(str).str.contains("Window", case=False, na=False)).sum())
n_open = n_doors + n_windows
c1, c2, c3, c4 = st.columns(4)
c1.metric("Gesamtelemente", f"{total_el:,}")
c2.metric("Türen", f"{n_doors:,}")
c3.metric("Fenster", f"{n_windows:,}")
c4.metric("Öffnungen total", f"{n_open:,}")

st.divider()

# Overview + Zoom&Filter
st.subheader("Elementverteilung und Typen")
col_left, col_right = st.columns([1, 1.15])

with col_left:
    st.caption("Welche Elementtypen dominieren das Gebäude?")
    counts = element_df["ifc_class"].fillna("Unbekannt").value_counts().reset_index()
    counts.columns = ["ifc_class", "count"]
    if len(counts) > 7:
        top = counts.head(6)
        rest = counts.iloc[6:]["count"].sum()
        counts = pd.concat([top, pd.DataFrame([{"ifc_class": "Sonstige", "count": rest}])], ignore_index=True)
    donut_colors = [CATEGORICAL_COLORS[i % len(CATEGORICAL_COLORS)] if c != "Sonstige" else COLORS["neutral"] for i, c in enumerate(counts["ifc_class"])]
    fig_donut = go.Figure(go.Pie(
        labels=counts["ifc_class"],
        values=counts["count"],
        hole=0.48,
        marker=dict(colors=donut_colors, line=dict(color="white", width=2)),
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>Anzahl Elemente: %{value}<br>Anteil: %{percent}<extra></extra>",
        sort=False,
    ))
    fig_donut.add_annotation(
        text=f"<b>{counts['count'].sum():,}</b><br><span style='font-size:11px;color:{COLORS['text_light']}'>Elemente</span>",
        x=0.5, y=0.5, showarrow=False, font=dict(size=16, color=COLORS["text"])
    )
    apply_default_layout(fig_donut, "Elementverteilung nach Typ")
    fig_donut.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=True)
    st.plotly_chart(fig_donut, use_container_width=True)

with col_right:
    st.caption("Wie viele Elemente gibt es pro Typ? Klick auf einen Balken filtert die Details unten.")
    cf_class = st.session_state.get("cf_page4_class")
    bar_counts = element_df["ifc_class"].fillna("Unbekannt").value_counts().reset_index()
    bar_counts.columns = ["ifc_class", "count"]
    bar_counts = bar_counts.sort_values("count", ascending=True)
    top3 = set(bar_counts.nlargest(3, "count")["ifc_class"].tolist())
    bar_colors = []
    for cls in bar_counts["ifc_class"]:
        if cf_class is not None:
            bar_colors.append(COLORS["primary"] if cls == cf_class else COLORS["neutral"])
        else:
            bar_colors.append(COLORS["primary"] if cls in top3 else COLORS["neutral"])
    fig_bar = go.Figure(go.Bar(
        x=bar_counts["count"],
        y=bar_counts["ifc_class"],
        orientation="h",
        marker_color=bar_colors,
        text=bar_counts["count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Anzahl Elemente: %{x}<extra></extra>",
    ))
    apply_default_layout(fig_bar, "Anzahl Elemente pro IFC-Klasse")
    fig_bar.update_layout(xaxis_title="Anzahl Elemente", yaxis_title="IFC-Klasse")
    ev_bar = st.plotly_chart(fig_bar, on_select="rerun", key="cf_p4_class_bar_new", use_container_width=True)
    if ev_bar and ev_bar.selection.points:
        clicked = ev_bar.selection.points[0].get("y") or ev_bar.selection.points[0].get("label")
        st.session_state.cf_page4_class = None if clicked == st.session_state.get("cf_page4_class") else clicked
        st.rerun()

st.divider()

# Details on demand
st.subheader("Elementdetails")
st.caption("Tabelle mit allen Elementen und ihren Eigenschaften.")

table_df = element_df.copy()
cf_class = st.session_state.get("cf_page4_class")
cf_mat = st.session_state.get("cf_page4_material")
if cf_class and "ifc_class" in table_df.columns:
    table_df = table_df[table_df["ifc_class"] == cf_class]
if cf_mat and "material" in table_df.columns:
    table_df = table_df[table_df["material"] == cf_mat]

display_cols = [c for c in ["Name", "name", "element_id", "ifc_class", "material", "volume_m3", "co2e_total"] if c in table_df.columns]
rename_map = {
    "Name": "Name", "name": "Name", "element_id": "Element ID", "ifc_class": "Typ",
    "material": "Material", "volume_m3": "Volumen (m³)", "co2e_total": "CO₂-Wert (kg)"
}
if display_cols:
    shown = table_df[display_cols].rename(columns=rename_map)
    shown = shown.loc[:, ~shown.columns.duplicated()]
    st.dataframe(shown, use_container_width=True, hide_index=True)
else:
    st.info("Keine Tabellendaten verfügbar.")
