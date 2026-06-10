import streamlit as st
import tempfile
import os
from src.state_manager import init_session_state, store_parsed_data, get_quality_data

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("Upload & Project Mode")

# ── Section A: Upload & Mode Selection ────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload IFC file",
    type=["ifc"],
    help="Supported formats: IFC2x3, IFC4",
)

st.caption("— or —")
if st.button("📂 Use Sample File", key="btn_sample", help="Load the included sample building model (IFC Export)"):
    st.session_state["_use_sample_file"] = True
    st.rerun()

st.subheader("Project Mode")
col1, col2 = st.columns(2)

with col1:
    neubau_selected = st.session_state.get("mode_project") == "neubau"
    border_neubau = "2px solid #2980B9" if neubau_selected else "2px solid #e0e0e0"
    bg_neubau = "#EBF5FB" if neubau_selected else "#FAFAFA"
    st.markdown(
        f"""<div style="border:{border_neubau};border-radius:8px;padding:16px;background:{bg_neubau};cursor:pointer;">
        <h3 style="margin:0">New Build</h3>
        <p style="margin:8px 0 0 0;color:#555;">All elements are treated as new build.<br>No status evaluation from IFC psets.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Select New Build", key="btn_neubau", use_container_width=True):
        st.session_state.mode_project = "neubau"
        st.rerun()

with col2:
    umbau_selected = st.session_state.get("mode_project") == "umbau"
    border_umbau = "2px solid #E67E22" if umbau_selected else "2px solid #e0e0e0"
    bg_umbau = "#FDEBD0" if umbau_selected else "#FAFAFA"
    st.markdown(
        f"""<div style="border:{border_umbau};border-radius:8px;padding:16px;background:{bg_umbau};cursor:pointer;">
        <h3 style="margin:0">Renovation / Refurbishment</h3>
        <p style="margin:8px 0 0 0;color:#555;">Status is read from IFC psets.<br>Falls back to "Existing" when no data is available.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Select Renovation", key="btn_umbau", use_container_width=True):
        st.session_state.mode_project = "umbau"
        st.rerun()

# Pset configurator (Umbau only)
pset_config = {}
if st.session_state.get("mode_project") == "umbau":
    st.subheader("Pset Configuration")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        pset_name = st.text_input(
            "Pset name for status",
            value=st.session_state.get("mode_pset_name", ""),
            placeholder="Empty = search all psets",
            key="pset_name_input",
        )
        st.session_state.mode_pset_name = pset_name
    with pcol2:
        pset_prop = st.text_input(
            "Property name for status",
            value=st.session_state.get("mode_pset_property", "Renovation Status"),
            key="pset_prop_input",
        )
        st.session_state.mode_pset_property = pset_prop
    pset_config = {"pset_name": pset_name, "pset_property": pset_prop}
    st.info(
        "Expected values: **New** → New Build | **Existing** → Existing | **To Be Demolished** → Demolition\n\n"
        "Leave pset name empty = all psets are searched for `Renovation Status`. "
        "If no status is found, **Existing** applies."
    )
else:
    pset_config = {
        "pset_name": st.session_state.get("mode_pset_name", ""),
        "pset_property": st.session_state.get(
            "mode_pset_property", "Renovation Status"
        ),
    }

# Resolve sample file state
use_sample = st.session_state.get("_use_sample_file", False)
sample_path = "data/sample_building.ifc"
if use_sample and not os.path.exists(sample_path):
    st.error("Sample file not found at data/sample_building.ifc")
    use_sample = False
    st.session_state["_use_sample_file"] = False
if uploaded_file is not None:
    use_sample = False
    st.session_state["_use_sample_file"] = False
if use_sample:
    st.info("📂 Using sample file: **sample_building.ifc**")

# Start analysis button
mode_ready = st.session_state.get("mode_project") is not None
file_ready = uploaded_file is not None or use_sample

st.divider()
btn_disabled = not (file_ready and mode_ready)
if not file_ready:
    st.caption("Please upload an IFC file first.")
if not mode_ready:
    st.caption("Please select a project mode.")

if st.button(
    "Start Analysis",
    disabled=btn_disabled,
    type="primary",
    use_container_width=True,
):
    # ── Section B: Parsing Progress ────────────────────────────────────
    progress = st.progress(0)
    status_box = st.status("Starting analysis…", expanded=True)

    with status_box:
        warnings = []

        st.write("Reading file…")
        progress.progress(10)
        if use_sample:
            tmp_path = sample_path
        else:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

        try:
            st.write("Detecting IFC schema…")
            progress.progress(20)
            from src.ifc_parser import parse_ifc_file

            parsed_data = parse_ifc_file(tmp_path)

            schema = parsed_data.get("schema", "Unknown")
            st.write(f"Schema detected: **{schema}**")
            progress.progress(35)

            st.write("Extracting entities…")
            elem_count = len(parsed_data.get("elements", []))
            st.write(f"   → {elem_count} building elements found")
            progress.progress(50)

            st.write("Reading IfcSpace…")
            space_count = len(parsed_data.get("spaces", []))
            if space_count == 0:
                warnings.append(
                    "IfcSpace not found — Page 3 (Rooms & Areas) is not available for this model."
                )
            st.write(f"   → {space_count} rooms found")
            progress.progress(65)

            st.write("Calculating quantities & assigning status…")
            progress.progress(80)

            mode = st.session_state.get("mode_project", "neubau")
            store_parsed_data(parsed_data, mode, pset_config)
            st.session_state.ifc_file_path = tmp_path

            progress.progress(95)
            st.write("Quality check completed")
            progress.progress(100)
            status_box.update(label="Analysis completed", state="complete")

        except ValueError as e:
            status_box.update(label="Error during analysis", state="error")
            st.error(f"Error: {e}")
            if not use_sample and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            st.stop()
        except Exception as e:
            status_box.update(label="Unexpected error", state="error")
            st.error(f"Unexpected error: {e}")
            if not use_sample and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            st.stop()

    for w in warnings:
        st.warning(w)

    st.rerun()

# ── Section C: Model Metadata (after analysis) ────────────────────────────
if st.session_state.get("ifc_parsed"):
    st.divider()
    st.subheader("Model Overview")

    metadata = st.session_state.get("model_metadata", {})
    element_df = st.session_state.get("element_df")
    space_df = st.session_state.get("space_df")
    storey_df = st.session_state.get("storey_df")

    _mode = st.session_state.get("mode_project", "")
    _mode_label = "New Build" if _mode == "neubau" else "Renovation / Refurbishment"
    _mode_color = "#D6EAF8" if _mode == "neubau" else "#FDEBD0"
    st.markdown(
        f'<div style="display:inline-block;background:{_mode_color};border-radius:6px;'
        f'padding:4px 12px;font-weight:600;margin-bottom:8px;">{_mode_label}</div>',
        unsafe_allow_html=True,
    )

    _, _quality_summary = get_quality_data()
    _score = _quality_summary.get("score", 0) if _quality_summary else 0
    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        st.metric("Building Elements", f"{metadata.get('element_count', 0):,}")
    with kpi_cols[1]:
        st.metric("Rooms (IfcSpace)", f"{metadata.get('space_count', 0):,}")
    with kpi_cols[2]:
        st.metric("Storeys", f"{metadata.get('storey_count', 0):,}")
    with kpi_cols[3]:
        st.metric("IFC Schema", metadata.get("schema", "–"))
    with kpi_cols[4]:
        st.metric("Software", metadata.get("application", "–"))
    with kpi_cols[5]:
        st.metric("Model Quality", f"{_score:.0f}%")

    st.subheader("Project Information")
    import pandas as pd

    meta_rows = {
        "Project Name": metadata.get("project_name", "not provided in model"),
        "Author": metadata.get("author", "not provided in model"),
        "Organization": metadata.get("organization", "not provided in model"),
        "IFC Schema": metadata.get("schema", "–"),
        "Exporting Software": metadata.get(
            "application", "not provided in model"
        ),
    }
    st.table(pd.DataFrame.from_dict(meta_rows, orient="index", columns=["Value"]))

    mode = st.session_state.get("mode_project")
    if mode == "umbau" and element_df is not None and not element_df.empty:
        st.subheader("Status Distribution (Renovation Mode)")
        status_counts = element_df["status"].value_counts()
        scols = st.columns(len(status_counts))
        for i, (status, count) in enumerate(status_counts.items()):
            scols[i].metric(status, f"{count:,}")

        not_found = int((element_df["status"] == "Nicht gefunden").sum())
        if not_found > 0:
            st.warning(
                f"{not_found} elements without status data — check on Page 6."
            )

    from src.filters import render_sidebar

    render_sidebar(element_df, space_df, mode)
