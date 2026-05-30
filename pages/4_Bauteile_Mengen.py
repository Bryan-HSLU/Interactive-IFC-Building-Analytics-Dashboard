import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_material_volume_bar,
    create_element_material_stacked_bar,
    create_storey_material_heatmap,
)
from src.ui_helpers import apply_unit_conversion, unit_caption
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
    st.warning("Please upload an IFC file on **Page 1** first.")
    st.stop()

element_df = get_element_df(filtered=True)

if element_df is None or element_df.empty:
    st.title("Bauteile & Mengen")
    st.warning("Keine Bauteildaten verfügbar.")
    st.stop()

st.title("Bauteile & Mengen")

_u_area = st.session_state.get("unit_area", "m\u00b2")
_u_volume = st.session_state.get("unit_volume", "m\u00b3")
_u_mass = st.session_state.get("unit_mass", "kg")

# Cross filter resets
CF_KEYS = ["cf_page4_class", "cf_page4_material", "cf_page3_usage"]
render_cross_filter_reset("page4", CF_KEYS)

# ── Apply all cross-filters early so KPIs reflect the selection ───────────────

cf_usage = st.session_state.get("cf_page3_usage")
cf_class = st.session_state.get("cf_page4_class")
cf_mat = st.session_state.get("cf_page4_material")


# Helper to classify raw material name (must align with chart_factory.py)
def _get_grouped_material_name(name: str) -> str:
    name_lower = str(name).lower().strip()
    if "holz" in name_lower or "dachbekleidung" in name_lower:
        return "Holz"
    elif "allgemein" in name_lower or "unbekannt" in name_lower:
        return "Allgemein"
    else:
        return str(name).strip()


if "material" in element_df.columns:
    element_df["grouped_material"] = element_df["material"].apply(
        _get_grouped_material_name
    )

if cf_usage:
    if space_df_raw is not None and not space_df_raw.empty:
        valid_storeys = space_df_raw[space_df_raw["usage"] == cf_usage][
            "storey"
        ].unique()
        if len(valid_storeys) > 0:
            element_df = element_df[element_df["storey"].isin(valid_storeys)]
        else:
            element_df = pd.DataFrame()

# Keep an unfiltered-by-material copy for the volume bar chart
# (so user can always see & click ALL materials to toggle)
element_df_all = element_df.copy()

# Compute the top 5 grouped materials dynamically
top_mats = []
if not element_df_all.empty and "grouped_material" in element_df_all.columns:
    vol_col = "volume_m3" if _u_volume in ("m³", "m\u00b3") else "area_m2"
    if vol_col in element_df_all.columns:
        df_valid = element_df_all.dropna(subset=[vol_col])
        top_mats = (
            df_valid.groupby("grouped_material")[vol_col]
            .sum()
            .nlargest(5)
            .index.tolist()
        )
        
        # Dynamic caption
        agg_vol = df_valid.groupby("grouped_material")[vol_col].sum()
        tot_vol = agg_vol.sum()
        if tot_vol > 0:
            top_4 = agg_vol.nlargest(4)
            pct_top = (top_4.sum() / tot_vol) * 100
            st.caption(f"{len(top_4)} Materialien = {pct_top:.0f} % des Volumens")
        else:
            st.caption("Umfassende Materialzusammensetzung und Analyse der Mengenverteilung.")
    else:
        st.caption("Umfassende Materialzusammensetzung und Analyse der Mengenverteilung.")
else:
    st.caption("Umfassende Materialzusammensetzung und Analyse der Mengenverteilung.")

# Now apply material & class filter for KPIs, stacked bar, and table
if cf_class and "ifc_class" in element_df.columns:
    element_df = element_df[element_df["ifc_class"] == cf_class]
if cf_mat and "grouped_material" in element_df.columns:
    if cf_mat == "Andere":
        element_df = element_df[~element_df["grouped_material"].isin(top_mats)]
    else:
        element_df = element_df[element_df["grouped_material"] == cf_mat]

if element_df.empty:
    st.warning("Keine Elementdaten unter den aktiven Filtern verfügbar.")
    st.stop()

# Show active filter info
active_parts = []
if cf_usage:
    active_parts.append(f"Raumtyp: **{cf_usage}**")
if cf_class:
    active_parts.append(f"Klasse: **{cf_class}**")
if cf_mat:
    active_parts.append(f"Material: **{cf_mat}**")
if active_parts:
    st.info(
        "Aktiver Filter — "
        + " | ".join(active_parts)
        + "  (Button oben zum Zurücksetzen)"
    )

# -- KPI Cards (reflect the active material filter!) --------------------------
vol_sum = pd.to_numeric(
    element_df.get("volume_m3", pd.Series(dtype=float)), errors="coerce"
).sum(skipna=True)
area_sum = pd.to_numeric(
    element_df.get("area_m2", pd.Series(dtype=float)), errors="coerce"
).sum(skipna=True)
kpi = st.columns(4)
kpi[0].metric("IFC-Klassen", f"{element_df['ifc_class'].nunique()}")
kpi[1].metric("Bauelemente", f"{len(element_df):,}")
kpi[2].metric("Volumen total", f"{vol_sum:,.1f} m³")
kpi[3].metric(
    "Materialien",
    f"{element_df['material'].nunique()}" if "material" in element_df.columns else "–",
)

st.divider()

# -- Chart A (Insight 3): "Welche Materialien sind verbaut – und wie viel?" ----
# Always show ALL materials so the user can click to select/deselect

st.subheader("Mengen nach Materialgruppe")
st.caption(
    "Klicken Sie auf einen Balken, um nach diesem Material zu filtern. Zum Aufheben nutzen Sie den Button oben."
)
unit = st.session_state.get("unit_volume", "m³")
fig_mat = create_material_volume_bar(element_df_all, unit)
fig_mat.update_layout(height=500)

ev_mat = st.plotly_chart(
    fig_mat, on_select="rerun", key="p4_volume_bar_chart", use_container_width=True
)

# Stable click handling: only act when the clicked material DIFFERS from
# the current filter. This prevents the infinite rerun loop caused by
# Plotly's persistent widget selection state.
if ev_mat and ev_mat.selection and ev_mat.selection.points:
    pt = ev_mat.selection.points[0]
    clicked = pt.get("y") or pt.get("label") or None
    if clicked and clicked != st.session_state.get("cf_page4_material"):
        st.session_state.cf_page4_material = clicked
        st.rerun()

st.divider()

# -- Chart B (Insight 6): "Wie verteilen sich Materialien auf Wand, Boden, Decke?"

st.subheader("Materialanteil pro Bauteilgruppe")
st.caption(
    "100% Stacked Bar Chart zur vergleichenden Zusammensetzung (Decke, Boden, Wand, Fenster, Tür)."
)
fig_stacked = create_element_material_stacked_bar(element_df)
fig_stacked.update_layout(
    height=500,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.05,
        xanchor="center",
        x=0.5,
        font=dict(size=11),
    ),
    margin=dict(l=50, r=20, t=80, b=50),
)
st.plotly_chart(fig_stacked, use_container_width=True, key="p4_stacked_bar")

st.divider()
st.subheader("CO₂-Intensität pro Geschoss")
st.caption("Wärmekarte: Welches Material verursacht auf welchem Geschoss die meisten CO₂-Emissionen?")
fig_heatmap = create_storey_material_heatmap(element_df)
st.plotly_chart(fig_heatmap, use_container_width=True, key="p4_heatmap")

# -- Quantity Takeoff Table ----------------------------------------------------
st.divider()
st.subheader("Element-Mengenliste")
st.caption("Detaillierte Bauteilliste des Modells.")

table_df = element_df.copy()
search = st.text_input(
    "Suche (Bauteil-Typ oder Material)",
    key="search_elements",
    placeholder="z.B. Beton, Wand...",
)
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["type_name", "material", "ifc_class"]:
        if col_search in table_df.columns:
            mask |= (
                table_df[col_search]
                .astype(str)
                .str.contains(search, case=False, na=False)
            )
    table_df = table_df[mask]

display_cols = [
    "element_id",
    "ifc_class",
    "type_name",
    "material",
    "storey",
    "area_m2",
    "volume_m3",
    "length_m",
]
if mode == "umbau" and "status" in table_df.columns:
    display_cols.append("status")
display_cols = [c for c in display_cols if c in table_df.columns]

col_rename = {
    "element_id": "ID",
    "ifc_class": "IFC-Klasse",
    "type_name": "Typ",
    "material": "Material",
    "storey": "Geschoss",
    "area_m2": "Fläche (m²)",
    "volume_m3": "Volumen (m³)",
    "length_m": "Länge (m)",
    "status": "Status",
}
display_df = table_df[display_cols].rename(columns=col_rename)
for num_col in ["Fläche (m²)", "Volumen (m³)", "Länge (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(
            2
        )

display_df, _ = apply_unit_conversion(display_df, _u_area, _u_volume, _u_mass)
_cap = unit_caption(_u_area, _u_volume, _u_mass)
st.caption(f"{len(display_df):,} Elemente angezeigt" + (f" | {_cap}" if _cap else ""))
st.dataframe(display_df, use_container_width=True, hide_index=True)
