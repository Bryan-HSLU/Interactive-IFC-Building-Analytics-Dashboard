import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.constants import COLORS, SIA_416_MAP, SIA_416_DEFAULT

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

space_df = get_space_df(filtered=True)

if space_df is None or space_df.empty:
    st.title("🏠 Rooms & Areas")
    st.info("This model contains no rooms (IfcSpace) for detailed analysis.")
    st.stop()

st.title("🏠 Rooms & Areas")
st.caption("📐 Area analysis and quantitative breakdown of rooms by SIA-416 categories.")

with st.expander("ℹ️ What does this page show?", expanded=False):
    st.markdown("""
    This page analyses the **rooms and areas** of the building based on IfcSpace elements:
    - **SIA-416 Area Distribution**: Total area per SIA-416 category (HNF, NNF, VF, FF, KF).
    - **Room Size Distribution**: Histogram of individual room areas.
    - **Rooms per Storey**: Stacked bar showing room counts by usage type per storey.
    - **HNF/NF Ratio**: Key metric for primary use area proportion.
    - **Room Table**: Searchable overview with area, volume and height.
    - **Height Distribution**: Distribution of room heights (if available).

    **IfcSpace** = room object in the IFC model (exported by ArchiCAD/Revit when rooms are modelled).
    """)

# Apply master filter from Overview Treemap
CF_KEYS = ["cf_page3_usage"]
render_cross_filter_reset("page3", CF_KEYS)

cf_usage = st.session_state.get("cf_page3_usage")
if cf_usage:
    if cf_usage in ("Total", "Total Building"):
        st.info("Active filter (from Overview): **Entire Building** (all rooms shown)")
    else:
        st.info(f"Active filter (from Overview): Rooms filtered by usage **{cf_usage}**")
        space_df = space_df[space_df["usage"] == cf_usage]

if space_df.empty:
    st.warning("No rooms match the active filter.")
    st.stop()


def _map_usage_to_sia(usage_str):
    u = str(usage_str).lower()
    for keyword, group in SIA_416_MAP.items():
        if keyword in u:
            return group
    return SIA_416_DEFAULT


# Add SIA category
space_df = space_df.copy()
space_df["sia_group"] = space_df["usage"].apply(_map_usage_to_sia)
space_df["area_m2"] = pd.to_numeric(space_df["area_m2"], errors="coerce")

# ── KPI: HNF/NF Ratio ──────────────────────────────────────────────────────────
total_area = space_df["area_m2"].sum(skipna=True)
hnf_area = space_df[space_df["sia_group"] == "HNF"]["area_m2"].sum(skipna=True)
hnf_ratio = (hnf_area / total_area * 100) if total_area > 0 else 0.0

kpi_cols = st.columns(4)
kpi_cols[0].metric("Total Rooms", f"{len(space_df):,}".replace(",", "'"))
kpi_cols[1].metric("Total Area (m²)", f"{total_area:,.1f}".replace(",", "'"))
kpi_cols[2].metric("HNF Area (m²)", f"{hnf_area:,.1f}".replace(",", "'"))
kpi_cols[3].metric("HNF / NF Ratio", f"{hnf_ratio:.1f}%")

st.divider()

# ── SIA-416 Area Distribution ──────────────────────────────────────────────────
st.subheader("📊 SIA-416 Area Distribution")
st.caption("Total area per SIA-416 category — HNF (primary use), NNF (secondary), VF (circulation), FF (functional), KF (construction).")

sia_agg = space_df.groupby("sia_group")["area_m2"].sum().reset_index()
sia_agg = sia_agg[sia_agg["area_m2"] > 0].sort_values("area_m2", ascending=False)

SIA_COLORS = {"HNF": "#2E86AB", "NNF": "#8D6E63", "VF": "#5C8A6E", "FF": "#7B5EA7", "KF": "#C44536"}

if not sia_agg.empty:
    fig_sia = go.Figure(go.Bar(
        x=sia_agg["sia_group"],
        y=sia_agg["area_m2"],
        marker_color=[SIA_COLORS.get(g, "#CCCCCC") for g in sia_agg["sia_group"]],
        text=[f"{v:,.1f} m²".replace(",", "'") for v in sia_agg["area_m2"]],
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Area: %{y:,.1f} m²<extra></extra>",
    ))
    fig_sia.update_layout(
        template="plotly_white",
        xaxis_title="SIA-416 Category",
        yaxis_title="Area (m²)",
        showlegend=False,
        margin=dict(l=40, r=20, t=30, b=40),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_sia, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No area data available.")

st.divider()

# ── Room Size Distribution ────────────────────────────────────────────────────
st.subheader("📐 Room Size Distribution")
st.caption("Histogram of individual room areas (m²).")

valid_areas = space_df["area_m2"].dropna()
valid_areas = valid_areas[valid_areas > 0]

if not valid_areas.empty:
    fig_hist = go.Figure(go.Histogram(
        x=valid_areas,
        nbinsx=20,
        marker_color=COLORS["primary"],
        opacity=0.8,
        hovertemplate="Area: %{x:.1f} m²<br>Count: %{y}<extra></extra>",
    ))
    fig_hist.update_layout(
        template="plotly_white",
        xaxis_title="Room Area (m²)",
        yaxis_title="Number of Rooms",
        showlegend=False,
        margin=dict(l=40, r=20, t=30, b=40),
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("No valid room areas available.")

st.divider()

# ── Rooms per Storey ──────────────────────────────────────────────────────────
if "storey" in space_df.columns:
    st.subheader("🏢 Rooms per Storey")
    st.caption("Number of rooms per storey, broken down by usage type.")

    storey_usage = space_df.groupby(["storey", "usage"]).size().reset_index(name="count")
    storeys = sorted(storey_usage["storey"].unique())
    usages = sorted(storey_usage["usage"].unique())

    fig_storey = go.Figure()
    for usage in usages:
        sub = storey_usage[storey_usage["usage"] == usage]
        storey_counts = {row["storey"]: row["count"] for _, row in sub.iterrows()}
        fig_storey.add_trace(go.Bar(
            name=usage,
            x=storeys,
            y=[storey_counts.get(s, 0) for s in storeys],
            hovertemplate=f"<b>{usage}</b><br>Storey: %{{x}}<br>Count: %{{y}}<extra></extra>",
        ))
    fig_storey.update_layout(
        template="plotly_white",
        barmode="stack",
        xaxis_title="Storey",
        yaxis_title="Number of Rooms",
        margin=dict(l=40, r=20, t=30, b=40),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.25, xanchor="center", x=0.5),
    )
    st.plotly_chart(fig_storey, use_container_width=True, config={"displayModeBar": False})
    st.divider()

# ── Room Table ────────────────────────────────────────────────────────────────
st.subheader("📋 Room Details")
st.caption("Searchable room list with area, volume and height.")

search = st.text_input("🔎 Search (room name)", key="search_rooms", placeholder="e.g. Office, Corridor...")

table_df = space_df.copy()
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["name", "usage", "sia_group"]:
        if col_search in table_df.columns:
            mask |= table_df[col_search].astype(str).str.contains(search, case=False, na=False)
    table_df = table_df[mask]

# Build display columns — include height_m if available
display_col_map = {
    "name": "Room Name",
    "usage": "Usage Type",
    "sia_group": "SIA-416",
    "area_m2": "Area (m²)",
    "volume_m3": "Volume (m³)",
}
if "height_m" in table_df.columns:
    display_col_map["height_m"] = "Height (m)"
if "storey" in table_df.columns:
    display_col_map["storey"] = "Storey"

avail_cols = [c for c in display_col_map if c in table_df.columns]
display_df = table_df[avail_cols].rename(columns=display_col_map)

for num_col in ["Area (m²)", "Volume (m³)", "Height (m)"]:
    if num_col in display_df.columns:
        display_df[num_col] = pd.to_numeric(display_df[num_col], errors="coerce").round(2)

st.caption(f"🏠 {len(display_df):,} rooms shown".replace(",", "'"))
st.dataframe(display_df, use_container_width=True, hide_index=True)

# ── Height Distribution ───────────────────────────────────────────────────────
if "height_m" in space_df.columns:
    st.divider()
    st.subheader("📏 Height Distribution")
    st.caption("Distribution of room heights (m).")
    valid_heights = pd.to_numeric(space_df["height_m"], errors="coerce").dropna()
    valid_heights = valid_heights[valid_heights > 0]
    if not valid_heights.empty:
        fig_hh = go.Figure(go.Histogram(
            x=valid_heights,
            nbinsx=15,
            marker_color=COLORS.get("neutral", "#B8BFC7"),
            opacity=0.8,
            hovertemplate="Height: %{x:.2f} m<br>Count: %{y}<extra></extra>",
        ))
        fig_hh.update_layout(
            template="plotly_white",
            xaxis_title="Room Height (m)",
            yaxis_title="Number of Rooms",
            showlegend=False,
            margin=dict(l=40, r=20, t=30, b=40),
            height=280,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_hh, use_container_width=True, config={"displayModeBar": False})
