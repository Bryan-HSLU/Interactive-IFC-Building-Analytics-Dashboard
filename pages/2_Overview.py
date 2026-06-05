import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import create_room_treemap, create_ifc_class_bar, create_status_donut
from src.constants import COLORS, CATEGORICAL_COLORS, IFC_CLASS_LABELS, SIA_COLORS, SIA_416_DESCRIPTIONS, STATUS_COLORS

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
space_df = get_space_df(filtered=True)
has_spaces = space_df is not None and not space_df.empty
metadata = st.session_state.get("model_metadata", {})

st.title("🏠 Building Overview")

# Dynamic caption
if has_spaces and "area_m2" in space_df.columns and space_df["area_m2"].sum() > 0:
    total_a = space_df["area_m2"].sum()
    agg_u = space_df.groupby("usage")["area_m2"].sum()
    if not agg_u.empty:
        dominant_usage = agg_u.idxmax()
        pct = (agg_u.max() / total_a) * 100
        st.caption(f"{len(space_df)} rooms over {total_a:,.0f} m² — **{dominant_usage}** occupies {pct:.0f} % of NFA".replace(",", "'"))
    else:
        st.caption("Quick overview of model structure, component types and spatial distribution.")
else:
    st.caption("Quick overview of model structure, component types and spatial distribution.")

with st.expander("ℹ️ What does this page show?", expanded=False):
    st.markdown("""
    The **Building Overview** gives a structured overview of the IFC model:
    - **Model Tab**: Which component types (IFC classes like wall, slab, window…) are present and how often? Metadata like project name and schema version.
    - **Status Tab**: How are elements distributed across existing, new build and demolition?
    - **Spatial Tab**: Which usage types occupy how much area (NFA)?

    Click in charts to filter other pages.
    """)

# ── KPI Row ──
n_elements = len(element_df) if element_df is not None else 0
n_storeys = element_df["storey"].nunique() if element_df is not None and "storey" in element_df.columns else 0
n_classes = element_df["ifc_class"].nunique() if element_df is not None and "ifc_class" in element_df.columns else 0
_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0

from src.ui_helpers import hero_kpi_card
kcols = st.columns(4)
with kcols[0]:
    hero_kpi_card("ELEMENTS", f"{n_elements:,}".replace(",", "'"), "Components")
with kcols[1]:
    hero_kpi_card("STOREYS", str(n_storeys), "Levels")
with kcols[2]:
    hero_kpi_card("IFC CLASSES", str(n_classes), "Types")
with kcols[3]:
    hero_kpi_card("QUALITY", f"{quality_score:.0f}", "%")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──
tab_modell, tab_status, tab_raeumlich = st.tabs(["🏗️ Model", "🔄 Status", "🗺️ Spatial"])

# ── Tab: Model ──
with tab_modell:
    col_chart, col_meta = st.columns([2, 1])
    with col_chart:
        st.subheader("IFC Class Distribution")
        st.caption("Number of components per IFC class — shows which element types dominate the model.")
        if element_df is not None and "ifc_class" in element_df.columns:
            st.plotly_chart(create_ifc_class_bar(element_df), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No IFC class data available.")
    with col_meta:
        st.subheader("Model Metadata")
        st.caption("Technical details of the loaded IFC model.")
        meta_items = [
            ("Project Name", metadata.get("project_name", "–")),
            ("IFC Schema", metadata.get("schema", "–")),
            ("Authoring Tool", metadata.get("authoring_tool", "–")),
            ("Total Elements", f"{metadata.get('element_count', n_elements):,}".replace(",", "'")),
            ("Storeys", str(n_storeys)),
            ("IFC Classes", str(n_classes)),
        ]
        for label, value in meta_items:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; padding:6px 0;
                            border-bottom:1px solid #E8EBEF; font-size:14px;">
                    <span style="color:#6B7280;">{label}</span>
                    <span style="font-weight:600; color:#2D2D2D;">{value}</span>
                </div>""",
                unsafe_allow_html=True,
            )

# ── Tab: Status ──
with tab_status:
    st.subheader("Phase & Status Distribution")
    st.caption(
        "Share of existing, new build, demolition and temporary elements in the total model (by element count). "
        "Relevant for project management and clients."
    )
    with st.expander("ℹ️ What do the status categories mean?", expanded=False):
        st.markdown("""
        - **Bestand**: Existing components that are retained.
        - **Neubau**: Newly created or planned components.
        - **Abbruch**: Components to be demolished.
        - **Temporär**: Temporary structures or time-limited elements.

        In new build mode all elements are classified as "Neubau".
        """)
    if element_df is not None and "status" in element_df.columns:
        _dcol1, _dcol2 = st.columns(2)
        with _dcol1:
            st.caption("**Element Count** by status")
            st.plotly_chart(create_status_donut(element_df), use_container_width=True, config={"displayModeBar": False})
        with _dcol2:
            st.caption("**Volume (m³)** by status")
            if "volume_m3" in element_df.columns:
                _vdf = element_df.dropna(subset=["volume_m3", "status"]).copy()
                _vdf["volume_m3"] = pd.to_numeric(_vdf["volume_m3"], errors="coerce").fillna(0)
                _vol_by_status = _vdf[_vdf["volume_m3"] > 0].groupby("status")["volume_m3"].sum()
                if not _vol_by_status.empty:
                    _total_sv = _vol_by_status.sum()
                    _fig_sv = go.Figure(go.Pie(
                        labels=_vol_by_status.index.tolist(),
                        values=_vol_by_status.values.tolist(),
                        hole=0.58,
                        marker=dict(colors=[STATUS_COLORS.get(s, "#C9CDD3") for s in _vol_by_status.index]),
                        textinfo="label+percent",
                        sort=False,
                        hovertemplate="<b>%{label}</b><br>Volume: %{value:,.1f} m³<br>Share: %{percent}<extra></extra>",
                    ))
                    _fig_sv.add_annotation(
                        text=f"<b>{_total_sv:,.0f}</b><br><span style='font-size:12px;'>m³</span>".replace(",", "'"),
                        x=0.5, y=0.5,
                        font=dict(size=22, family="Inter, sans-serif", color=COLORS["text"]),
                        showarrow=False,
                    )
                    _fig_sv.update_layout(
                        template="plotly_white",
                        showlegend=True,
                        legend=dict(orientation="h", y=-0.08, xanchor="center", x=0.5, font=dict(size=12)),
                        margin=dict(l=20, r=20, t=20, b=40),
                        height=340,
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(_fig_sv, use_container_width=True, config={"displayModeBar": False}, key="ov_vol_status_donut")
                else:
                    st.info("No volume data by status.")
            else:
                st.info("No volume data available.")
    else:
        st.info("No status data available — renovation mode may not be selected.")

# ── Tab: Spatial ──
with tab_raeumlich:
    st.subheader("Spatial Area Distribution (NFA)")
    st.caption(
        "Proportions of room types by net floor area (NFA). "
        "Click on a type to filter other pages."
    )
    with st.expander("ℹ️ What is NFA?", expanded=False):
        st.markdown("""
        The **Net Floor Area (NFA)** is the usable interior area across all storeys — excluding walls,
        structure and service areas. The areas come from the IfcSpace elements in the model.
        The treemap uses **SIA-416** categories: HNF (primary use), NNF (secondary), VF (circulation), FF (functional), KF (construction).
        """)
    if has_spaces:
        fig_tree = create_room_treemap(space_df)
        ev_tree = st.plotly_chart(fig_tree, on_select="rerun", key="ov_treemap", use_container_width=True)
        if ev_tree and ev_tree.selection and ev_tree.selection.points:
            pt = ev_tree.selection.points[0]
            usage_val = pt.get("customdata") if pt.get("customdata") else ""
            clicked_id = pt.get("id") or ""
            if clicked_id.startswith("sia::") or clicked_id == "root":
                pass
            elif usage_val:
                clicked_clean = str(usage_val).strip()
                if clicked_clean and clicked_clean != st.session_state.get("cf_page3_usage"):
                    st.session_state.cf_page3_usage = clicked_clean
                    st.rerun()
            else:
                clicked = pt.get("label") or pt.get("id") or ""
                clicked_clean = clicked.replace("<b>", "").replace("</b>", "").strip()
                if clicked_clean in ("Total Building", "Total", "root"):
                    if st.session_state.get("cf_page3_usage") != "Total":
                        st.session_state.cf_page3_usage = "Total"
                        st.rerun()
                elif clicked_clean:
                    if clicked_clean != st.session_state.get("cf_page3_usage"):
                        st.session_state.cf_page3_usage = clicked_clean
                        st.rerun()

        # SIA-416 color legend
        with st.expander("🎨 SIA-416 Legend", expanded=False):
            for abbr, desc in SIA_416_DESCRIPTIONS.items():
                color = SIA_COLORS.get(abbr, "#CCCCCC")
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:4px 0;">'
                    f'<div style="width:18px;height:18px;border-radius:3px;background:{color};flex-shrink:0;"></div>'
                    f'<span style="font-weight:600;min-width:36px;">{abbr}</span>'
                    f'<span style="color:#6B7280;">{desc}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("This model contains no rooms (IfcSpace) for a treemap area distribution.")
