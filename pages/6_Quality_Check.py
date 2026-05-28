import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import (
    create_quality_gauge,
    create_error_bar,
    create_status_distribution, create_pset_matrix_heatmap,
    create_upset_plot,
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

CF_KEYS = ["cf_page6_error_cat", "cf_page6_status_class"]
render_cross_filter_reset("page6", CF_KEYS)

# -- Section A: Quality Score --------------------------------------------------
col_score, col_traffic = st.columns(2)

score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)

with col_score:
    fig_gauge = create_quality_gauge(score)
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_traffic:
    st.subheader("Quality Indicators")
    st.caption("Shows how many elements are missing key data fields.")

    def _traffic_light(count, label):
        if count == 0:
            badge, color, weight = "OK", "#D6EAF8", "600"
        elif count <= 10:
            badge, color, weight = "Warning", "#FCF3CF", "600"
        else:
            badge, color, weight = "Critical", "#FDEBD0", "700"
        st.markdown(
            f'<div style="background:{color};border-radius:6px;padding:8px 12px;margin:4px 0;">'
            f'<b style="font-weight:{weight};">[{badge}]</b> {label}: <b>{count}</b></div>',
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

# -- Section B: Error Analysis -------------------------------------------------
has_errors = error_df is not None and not error_df.empty
total_errors = sum(error_counts.values())

if total_errors == 0:
    st.success("No errors found -- your IFC model is complete!")
else:
    st.caption("Click a bar to filter the error table below. Click again to deselect.")
    col_err, col_status = st.columns(2)
    with col_err:
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
            if mapped == st.session_state.get("cf_page6_error_cat"):
                st.session_state.cf_page6_error_cat = None
            else:
                st.session_state.cf_page6_error_cat = mapped
            st.rerun()

    with col_status:
        if mode == "umbau":
            fig_status = create_status_distribution(element_df)
            ev_status = st.plotly_chart(fig_status, on_select="rerun", key="cf_p6_status_bar", use_container_width=True)
            if ev_status and ev_status.selection.points:
                pt = ev_status.selection.points[0]
                clicked = pt.get("x") or pt.get("y") or pt.get("label")
                if clicked == st.session_state.get("cf_page6_status_class"):
                    st.session_state.cf_page6_status_class = None
                else:
                    st.session_state.cf_page6_status_class = clicked
                st.rerun()
        else:
            st.subheader("Pset Completeness by IFC Class")
            if not element_df.empty and "psets" in element_df.columns:
                pset_counts = element_df.groupby("ifc_class")["psets"].apply(
                    lambda x: (x.apply(lambda p: len(p) > 0 if isinstance(p, dict) else False)).sum()
                ).reset_index()
                pset_counts.columns = ["IFC Class", "Elements with Psets"]
                total_per_class = element_df["ifc_class"].value_counts().reset_index()
                total_per_class.columns = ["IFC Class", "Total"]
                merged = pset_counts.merge(total_per_class, on="IFC Class")
                merged["Completeness (%)"] = (merged["Elements with Psets"] / merged["Total"] * 100).round(1)
                st.dataframe(merged, use_container_width=True, hide_index=True)
            else:
                st.info("No Pset data available.")

    st.divider()
    st.subheader("Error Co-occurrence")
    st.caption("Which error combinations appear together? Each column = one combination.")
    if has_errors:
        st.plotly_chart(create_upset_plot(error_df), use_container_width=True)

# -- Section C: Pset Matrix ----------------------------------------------------
st.divider()
st.subheader("Pset Availability Matrix")
st.caption("Blue = Pset present, Gray = missing. Shows which property sets are assigned to which elements.")

if element_df is not None and not element_df.empty:
    pset_matrix = build_pset_matrix(element_df)
    if pset_matrix is not None and not pset_matrix.empty:
        if len(pset_matrix.columns) > 15:
            top_cols = pset_matrix.sum().nlargest(15).index
            pset_matrix = pset_matrix[top_cols]
        st.plotly_chart(create_pset_matrix_heatmap(pset_matrix), use_container_width=True)
    else:
        st.info("No Pset data available for matrix.")

# -- Section D: Error Detail Table ---------------------------------------------
st.divider()
st.subheader("Error Details")

if has_errors:
    table_df = error_df.copy()
    cf_cat = st.session_state.get("cf_page6_error_cat")
    cf_cls = st.session_state.get("cf_page6_status_class")
    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]
    if cf_cls and "ifc_class" in table_df.columns:
        table_df = table_df[table_df["ifc_class"] == cf_cls]

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
