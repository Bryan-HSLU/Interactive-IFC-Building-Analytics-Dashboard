import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import create_room_treemap, create_ifc_class_bar, create_status_donut
from src.constants import COLORS
from src.ui_helpers import hero_kpi_card

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
    st.warning("Please upload an IFC file on **Page 1** first.")
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
        st.caption(f"{len(space_df)} rooms over {total_a:,.0f} m² — **{dominant_usage}** occupies {pct:.0f} % of NFA".replace(",", "'"))
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
        st.plotly_chart(create_status_donut(element_df), use_container_width=True, config={"displayModeBar": False})
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
            # Use customdata for the raw usage value (leaf nodes have non-empty customdata)
            usage_val = pt.get("customdata") if pt.get("customdata") else ""
            clicked_id = pt.get("id") or ""
            # Only filter on leaf (usage-level) clicks; SIA group clicks do nothing
            if clicked_id.startswith("sia::") or clicked_id == "root":
                pass  # SIA group or root click — no filtering
            elif usage_val:
                clicked_clean = str(usage_val).strip()
                if clicked_clean and clicked_clean != st.session_state.get("cf_page3_usage"):
                    st.session_state.cf_page3_usage = clicked_clean
                    st.rerun()
            else:
                # Fallback: use label
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
    else:
        st.info("This model contains no rooms (IfcSpace) for a treemap area distribution.")
