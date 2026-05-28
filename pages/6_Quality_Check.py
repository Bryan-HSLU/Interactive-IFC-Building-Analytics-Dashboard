import streamlit as st
import pandas as pd
from streamlit_plotly_events import plotly_events
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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite 1** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)
error_df, quality_summary = get_quality_data()

if not quality_summary:
    st.title("Quality Check")
    st.warning("Keine Qualitätsdaten verfügbar.")
    st.stop()

st.title("Quality Check")

# Cross-filter reset
CF_KEYS = ["cf_page6_error_cat", "cf_page6_status_class"]
render_cross_filter_reset("page6", CF_KEYS)

# ── Section A: Quality Score ──────────────────────────────────────────────
col_score, col_traffic = st.columns(2)

score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)
total_spaces = quality_summary.get("total_spaces", 0)

with col_score:
    fig_gauge = create_quality_gauge(score)
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_traffic:
    st.subheader("Quality Indicators")

    def _traffic_light(count: int, label: str, show_always: bool = True):
        if not show_always and count == 0:
            return
        if count == 0:
            badge = "OK"
            color = "#D6EAF8"
            weight = "600"
        elif count <= 10:
            badge = "Warning"
            color = "#FCF3CF"
            weight = "600"
        else:
            badge = "Critical"
            color = "#FDEBD0"
            weight = "700"
        st.markdown(
            f'<div style="background:{color};border-radius:6px;padding:8px 12px;margin:4px 0;">'
            f'<b style="font-weight:{weight};">[{badge}] {label}</b>: {count}</div>',
            unsafe_allow_html=True,
        )

    _traffic_light(error_counts.get("missing_material", 0), "Elements without material")
    _traffic_light(error_counts.get("missing_quantity", 0), "Elements without quantities")
    _traffic_light(error_counts.get("missing_usage", 0), "Spaces without usage assignment")
    _traffic_light(error_counts.get("missing_storey", 0), "Elements without storey assignment")
    if mode == "umbau":
        _traffic_light(error_counts.get("missing_status", 0), "Elements without status")

# ── Section B: Error Analysis ───────────────────────────────────────────────
st.divider()
col_err, col_status = st.columns(2)

with col_err:
    fig_err = create_error_bar(error_counts)
    sel_err = plotly_events(fig_err, click_event=True, key="cf_p6_error_bar", override_height=380)
    if sel_err:
        clicked = sel_err[0].get("x")
        label_map = {
            "Kein Material": "missing_material",
            "Keine Mengen": "missing_quantity",
            "Kein Geschoss": "missing_storey",
            "Keine Nutzung": "missing_usage",
            "Kein Status": "missing_status",
        }
        mapped = label_map.get(clicked, clicked)
        # Toggle off if same category clicked again
        if mapped != st.session_state.get("cf_page6_error_cat"):
            st.session_state.cf_page6_error_cat = mapped
            st.rerun()
        else:
            st.session_state.cf_page6_error_cat = None
            st.rerun()

with col_status:
    if mode == "umbau":
        fig_status = create_status_distribution(element_df)
        sel_status = plotly_events(fig_status, click_event=True, key="cf_p6_status_bar", override_height=380)
        if sel_status:
            clicked = sel_status[0].get("x")
            if clicked and clicked != st.session_state.get("cf_page6_status_class"):
                st.session_state.cf_page6_status_class = clicked
                st.rerun()
            elif clicked and clicked == st.session_state.get("cf_page6_status_class"):
                st.session_state.cf_page6_status_class = None
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

# ── Section C: UpSet Plot ───────────────────────────────────────────────────
st.divider()
st.subheader("Error Co-occurrence (UpSet Plot)")
st.caption(
    "Which error combinations appear together? "
    "Each column represents a combination of errors. "
    "The bars above show how many elements have that combination. "
    "The dots below indicate which error types are combined."
)
if error_df is not None and not error_df.empty:
    fig_upset = create_upset_plot(error_df)
    st.plotly_chart(fig_upset, use_container_width=True)
else:
    st.success("✅ No errors found — UpSet Plot not needed.")

# ── Section D: Pset Matrix ────────────────────────────────────────────────────
st.divider()
st.subheader("Pset Availability Matrix")
st.caption("Blue = Pset present · Gray = missing")

if not element_df.empty:
    pset_matrix = build_pset_matrix(element_df)
    if pset_matrix is not None and not pset_matrix.empty:
        if len(pset_matrix.columns) > 15:
            top_cols = pset_matrix.sum().nlargest(15).index
            pset_matrix = pset_matrix[top_cols]
        fig_pset = create_pset_matrix_heatmap(pset_matrix)
        st.plotly_chart(fig_pset, use_container_width=True)
    else:
        st.info("No Pset data available for matrix.")

# ── Section E: Error Detail Table ──────────────────────────────────────────────
st.divider()
st.subheader("Error Details")

if error_df is not None and not error_df.empty:
    table_df = error_df.copy()

    cf_cat = st.session_state.get("cf_page6_error_cat")
    cf_cls = st.session_state.get("cf_page6_status_class")

    if cf_cat and "error_type" in table_df.columns:
        table_df = table_df[table_df["error_type"] == cf_cat]
    if cf_cls and "ifc_class" in table_df.columns:
        table_df = table_df[table_df["ifc_class"] == cf_cls]

    col_rename = {
        "element_id": "Element ID",
        "ifc_class": "IFC Class",
        "storey": "Storey",
        "error_type": "Error Type",
        "severity": "Severity",
        "description": "Description",
    }
    display_df = table_df.rename(columns=col_rename)

    def _color_severity(val):
        if val == "critical":
            return "color: #A04000; font-weight: bold"
        elif val == "warning":
            return "color: #E67E22"
        return ""

    if "Severity" in display_df.columns:
        st.dataframe(
            display_df.style.applymap(_color_severity, subset=["Severity"]),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    if mode == "umbau" and error_counts.get("missing_status", 0) > 0:
        st.warning("⚠️ Calculations on Page 5 may be incomplete due to missing status data.")
else:
    st.success("✅ No errors found.")
