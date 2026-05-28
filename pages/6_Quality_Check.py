import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_quality_gauge,
    create_error_bar,
    create_pset_matrix_heatmap,
)
from src.quality_checker import build_pset_matrix

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
error_df, quality_summary = get_quality_data()

if not quality_summary:
    st.title("Quality Check")
    st.warning("No quality data available.")
    st.stop()

st.title("Quality Check")
st.caption("Analyses how complete and consistent your IFC model data is.")

CF_KEYS = ["cf_page6_error_cat"]
render_cross_filter_reset("page6", CF_KEYS)

score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)

# -- Quality Score KPI (static, compact) ---------------------------------------
col_gauge, col_traffic = st.columns([1, 2])

with col_gauge:
    st.plotly_chart(create_quality_gauge(score), use_container_width=True)

with col_traffic:
    st.subheader("Quality Indicators")
    st.caption("Shows how many elements are missing key data fields.")

    def _traffic_light(count, label):
        if count == 0:
            badge, color = "OK", "#D6EAF8"
        elif count <= 10:
            badge, color = "Warning", "#FCF3CF"
        else:
            badge, color = "Critical", "#FDEBD0"
        st.markdown(
            f'<div style="background:{color};border-radius:6px;padding:8px 12px;margin:4px 0;">'
            f'<b>[{badge}]</b> {label}: <b>{count}</b></div>',
            unsafe_allow_html=True,
        )

    _traffic_light(error_counts.get("missing_material", 0), "Elements without material")
    _traffic_light(error_counts.get("missing_quantity", 0), "Elements without quantities")
    _traffic_light(error_counts.get("missing_usage", 0), "Spaces without usage")
    _traffic_light(error_counts.get("missing_storey", 0), "Elements without storey")
    if mode == "umbau":
        _traffic_light(error_counts.get("missing_status", 0), "Elements without status")

    total_errors = sum(error_counts.values())
    if total_errors == 0:
        st.success(f"Model complete -- all {total_elements:,} elements have required fields.")
    else:
        st.warning(f"{total_errors} issue(s) found across {total_elements:,} elements.")

st.divider()

total_errors = sum(error_counts.values())

if total_errors == 0:
    st.success("No errors found -- your IFC model is complete!")
else:
    # -- Chart A: Error Bar (interactive, filters error table below) -----------
    # -- Chart B: Pset Heatmap (shows property set completeness per IFC class) -
    st.caption("Click a bar to filter the error table below. Click again to deselect.")
    col_err, col_pset = st.columns(2)

    with col_err:
        st.subheader("Errors by Type")
        fig_err = create_error_bar(error_counts)
        ev_err = st.plotly_chart(fig_err, on_select="rerun", key="cf_p6_error_bar", use_container_width=True)
        if ev_err and ev_err.selection.points:
            pt = ev_err.selection.points[0]
            clicked = pt.get("x") or pt.get("y") or pt.get("label")
            label_map = {
                "Kein Material": "missing_material",
                "Keine Mengen": "missing_quantity",
                "Kein Geschoss": "missing_storey",
                "Keine Nutzung": "missing_usage",
                "Kein Status": "missing_status",
            }
            mapped = label_map.get(clicked, clicked)
            st.session_state.cf_page6_error_cat = None if mapped == st.session_state.get("cf_page6_error_cat") else mapped
            st.rerun()

    with col_pset:
        st.subheader("Pset Availability by IFC Class")
        st.caption("Blue = present, Gray = missing.")
        if element_df is not None and not element_df.empty:
            pset_matrix = build_pset_matrix(element_df)
            if pset_matrix is not None and not pset_matrix.empty:
                if len(pset_matrix.columns) > 15:
                    top_cols = pset_matrix.sum().nlargest(15).index
                    pset_matrix = pset_matrix[top_cols]
                st.plotly_chart(create_pset_matrix_heatmap(pset_matrix), use_container_width=True)
            else:
                st.info("No Pset data available.")
        else:
            st.info("No element data available.")

# -- Error Detail Table --------------------------------------------------------
st.divider()
st.subheader("Error Details")

has_errors = error_df is not None and not error_df.empty
if has_errors:
    table_df = error_df.copy()
    cf_cat = st.session_state.get("cf_page6_error_cat")
    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]

    display_df = table_df.rename(columns={
        "element_id": "Element ID", "ifc_class": "IFC Class",
        "storey": "Storey", "error_type": "Error Type",
        "severity": "Severity", "description": "Description",
    })

    def _color_severity(val):
        if val == "critical": return "color: #A04000; font-weight: bold"
        elif val == "warning": return "color: #E67E22"
        return ""

    if "Severity" in display_df.columns:
        st.dataframe(display_df.style.map(_color_severity, subset=["Severity"]), use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.success("No errors found -- your IFC model is complete.")
