import streamlit as st
import pandas as pd
import numpy as np
from streamlit_plotly_events import plotly_events
from src.state_manager import init_session_state, get_space_df, get_element_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_room_boxplot, create_room_stacked_bar, create_room_histogram,
    create_room_scatter,
)
from src.ui_helpers import kpi_card
from src.constants import COLORS

st.set_page_config(page_title="Räume & Flächen – IFC Analytics", page_icon=None, layout="wide")
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

space_df = get_space_df(filtered=True)

if space_df is None or space_df.empty:
    st.title("Räume & Flächen")
    st.warning("Keine Räume (IfcSpace) im Modell gefunden. Diese Seite ist nicht verfügbar.")
    st.stop()

st.title("Räume & Flächen")


# ── Helper: Raumname aus plotly_events-Scatter-Klick rekonstruieren ──────────────────
def _room_name_from_scatter_event(event: dict, df: pd.DataFrame) -> str | None:
    """
    plotly_events gibt bei Scatter-Klick {curveNumber, pointNumber, x, y} zurueck.
    create_room_scatter baut Traces in alphabetischer Reihenfolge der Nutzungstypen
    ("Unbekannt" zuletzt). Wir replizieren diese Reihenfolge und lesen den
    Raumnamen via pointNumber aus dem jeweiligen Trace-Subset.
    """
    if df is None or df.empty or "area_m2" not in df.columns:
        return None

    y_col = next(
        (c for c in ["height_m", "volume_m3"] if c in df.columns and df[c].notna().any()),
        None,
    )
    if y_col is None:
        return None

    sub = df.dropna(subset=["area_m2", y_col]).copy()
    sub["usage"] = sub["usage"].fillna("Unbekannt") if "usage" in sub.columns else "Unbekannt"

    usages = sorted(sub["usage"].unique(), key=lambda x: (x == "Unbekannt", x))

    curve_number = event.get("curveNumber", 0)
    point_number = event.get("pointNumber", 0)

    if curve_number >= len(usages):
        return None

    usage = usages[curve_number]
    trace_rows = sub[sub["usage"] == usage].reset_index(drop=True)

    if point_number >= len(trace_rows):
        return None

    row = trace_rows.iloc[point_number]
    return str(row["name"]) if "name" in trace_rows.columns else None


# ── Cross-filter reset ─────────────────────────────────────────────────────────
CF_KEYS = ["cf_page3_usage", "cf_page3_storey", "cf_page3_size_bin", "cf_page3_room"]
render_cross_filter_reset("page3", CF_KEYS)

# ── Section A: KPI Cards ──────────────────────────────────────────────────────────
df_with_area = space_df.dropna(subset=["area_m2"]) if "area_m2" in space_df.columns else pd.DataFrame()
rooms_without_area = len(space_df) - len(df_with_area)

kpi = st.columns(5)
with kpi[0]:
    kpi_card("Räume gesamt", f"{len(space_df):,}")
with kpi[1]:
    kpi_card("Gesamtfläche (NGF)", f"{df_with_area['area_m2'].sum():,.1f} m²" if not df_with_area.empty else "–")
with kpi[2]:
    kpi_card("Ø Raumgrösse", f"{df_with_area['area_m2'].mean():,.1f} m²" if not df_with_area.empty else "–")
with kpi[3]:
    kpi_card("Geschosse", f"{space_df['storey'].nunique():,}" if "storey" in space_df.columns else "–")
with kpi[4]:
    kpi_card("Nutzungstypen", f"{space_df['usage'].nunique():,}" if "usage" in space_df.columns else "–")

if rooms_without_area > 0:
    st.caption(f"{rooms_without_area} Räume ohne Flächenangabe (nicht in Charts dargestellt)")

# ── Section B: Distribution Analysis ──────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    fig_box = create_room_boxplot(space_df)
    selected_box = plotly_events(fig_box, click_event=True, key="cf_p3_boxplot", override_height=380)
    if selected_box:
        clicked_usage = selected_box[0].get("x") or selected_box[0].get("y")
        if clicked_usage and clicked_usage != st.session_state.get("cf_page3_usage"):
            st.session_state.cf_page3_usage = clicked_usage
            st.session_state.cf_page3_room = None
            st.rerun()

with col_right:
    storey_df = st.session_state.get("storey_df")
    storey_order = None
    if isinstance(storey_df, list) and storey_df:
        storey_order = [s["name"] for s in storey_df]
    elif isinstance(storey_df, pd.DataFrame) and not storey_df.empty:
        storey_order = storey_df["name"].tolist() if "name" in storey_df.columns else None

    fig_bar = create_room_stacked_bar(space_df, storey_order)
    selected_bar = plotly_events(fig_bar, click_event=True, key="cf_p3_stacked", override_height=380)
    if selected_bar:
        clicked_storey = selected_bar[0].get("x") or selected_bar[0].get("y")
        if clicked_storey and clicked_storey != st.session_state.get("cf_page3_storey"):
            st.session_state.cf_page3_storey = clicked_storey
            st.session_state.filter_storeys = [clicked_storey]
            st.session_state.cf_page3_room = None
            st.rerun()

# ── Section C: Histogram ───────────────────────────────────────────────────────
fig_hist = create_room_histogram(space_df)
selected_hist = plotly_events(fig_hist, click_event=True, key="cf_p3_histogram", override_height=320)
if selected_hist:
    bin_x = selected_hist[0].get("x")
    if bin_x is not None:
        bin_width = (
            (df_with_area["area_m2"].max() - df_with_area["area_m2"].min()) / 20
            if not df_with_area.empty else 10.0
        )
        bin_width = max(bin_width, 1.0)
        new_bin = (float(bin_x), float(bin_width))
        if new_bin != st.session_state.get("cf_page3_size_bin"):
            st.session_state.cf_page3_size_bin = new_bin
            st.session_state.cf_page3_room = None
            st.rerun()

# ── Section D: Scatter ────────────────────────────────────────────────────────────
st.divider()
st.subheader("Räumliche Analyse")

cf_room = st.session_state.get("cf_page3_room")

if cf_room:
    st.markdown(
        f'<div style="background:#D5EEF0;border-left:4px solid {COLORS["error_ok"]};'
        f'border-radius:4px;padding:6px 14px;margin-bottom:8px;">'
        f'📌 Ausgewählter Raum: <b>{cf_room}</b></div>',
        unsafe_allow_html=True,
    )

fig_scatter = create_room_scatter(space_df)
sel_scatter = plotly_events(fig_scatter, click_event=True, key="cf_p3_scatter", override_height=420)

if sel_scatter:
    clicked_name = _room_name_from_scatter_event(sel_scatter[0], space_df)

    if clicked_name and clicked_name != cf_room:
        st.session_state.cf_page3_room = clicked_name
        if "usage" in space_df.columns:
            matched = space_df[space_df["name"].astype(str) == clicked_name]
            if not matched.empty:
                st.session_state.cf_page3_usage = matched.iloc[0]["usage"]
        st.rerun()
    elif clicked_name and clicked_name == cf_room:
        st.session_state.cf_page3_room = None
        st.rerun()

# ── Section E: Detail Table ───────────────────────────────────────────────────────
st.subheader("Raumdetails")

table_df = space_df.copy()

cf_usage   = st.session_state.get("cf_page3_usage")
cf_storey  = st.session_state.get("cf_page3_storey")
cf_size_bin = st.session_state.get("cf_page3_size_bin")

if cf_usage and "usage" in table_df.columns:
    table_df = table_df[table_df["usage"] == cf_usage]
if cf_storey and "storey" in table_df.columns:
    table_df = table_df[table_df["storey"] == cf_storey]
if cf_size_bin and "area_m2" in table_df.columns:
    bin_center, bin_width = cf_size_bin
    table_df = table_df[
        (table_df["area_m2"] >= bin_center - bin_width / 2) &
        (table_df["area_m2"] <  bin_center + bin_width / 2)
    ]

search = st.text_input("Suche (Raumname)", key="search_rooms", placeholder="z.B. Büro, Flur…")
if search:
    mask = table_df.get("name", pd.Series(dtype=str)).astype(str).str.contains(search, case=False, na=False)
    if "long_name" in table_df.columns:
        mask |= table_df["long_name"].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

table_df = table_df.copy()
if cf_room and "name" in table_df.columns:
    table_df.insert(0, "", table_df["name"].astype(str).apply(
        lambda n: "🟡" if n == cf_room else ""
    ))

display_cols = ["name", "storey", "usage", "area_m2", "volume_m3", "height_m"]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
if cf_room and "" in table_df.columns:
    display_cols = [""] + display_cols
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "name": "Raumname", "storey": "Geschoss", "usage": "Nutzung",
    "area_m2": "Fläche (m²)", "volume_m3": "Volumen (m³)", "height_m": "Höhe (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Fläche (m²)", "Volumen (m³)", "Höhe (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

if cf_room and "Raumname" in display_df.columns:
    is_selected = display_df["Raumname"].astype(str) == cf_room
    display_df = pd.concat([display_df[is_selected], display_df[~is_selected]], ignore_index=True)

st.caption(
    f"{len(display_df)} Räume angezeigt"
    + (f" — 🟡 = ausgewählter Raum" if cf_room else "")
)
st.dataframe(display_df, use_container_width=True, hide_index=True)

if cf_room:
    if st.button("× Raum-Auswahl aufheben", key="reset_scatter_room"):
        st.session_state.cf_page3_room = None
        st.rerun()
