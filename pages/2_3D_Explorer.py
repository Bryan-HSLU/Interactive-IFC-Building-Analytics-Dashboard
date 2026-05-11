import streamlit as st
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar

st.set_page_config(page_title="3D Explorer – IFC Analytics", page_icon="🏗️", layout="wide")
init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

element_df = get_element_df(filtered=False)
space_df = get_space_df(filtered=False)
mode = st.session_state.get("mode_project", "")
render_sidebar(element_df, space_df, mode)

if not st.session_state.get("ifc_parsed"):
    st.warning("⚠️ Bitte zuerst eine IFC-Datei auf **Seite 1** hochladen.")
    st.stop()

st.title("🏗️ 3D Model Explorer")

col_viewer, col_panel = st.columns([7, 3])

with col_viewer:
    # Color mode selector
    color_mode = st.selectbox(
        "Farbmodus",
        options=["standard", "nach_geschoss", "nach_klasse", "nach_status", "nach_co2"],
        format_func=lambda x: {
            "standard": "Standard",
            "nach_geschoss": "Nach Geschoss",
            "nach_klasse": "Nach IFC-Klasse",
            "nach_status": "Nach Status (Umbau)",
            "nach_co2": "Nach CO2-Intensität",
        }[x],
        key="viewer_color_mode",
    )

    # Storey toggles
    storey_df = st.session_state.get("storey_df")
    import pandas as pd
    visible_storeys = []
    if storey_df is not None and not (isinstance(storey_df, pd.DataFrame) and storey_df.empty):
        if isinstance(storey_df, list) and storey_df:
            storey_names = [s["name"] for s in storey_df]
        elif isinstance(storey_df, pd.DataFrame):
            storey_names = storey_df["name"].tolist() if "name" in storey_df.columns else []
        else:
            storey_names = []

        if storey_names:
            st.caption("Geschosse ein-/ausblenden:")
            toggle_cols = st.columns(min(len(storey_names), 5))
            for i, s in enumerate(storey_names):
                with toggle_cols[i % min(len(storey_names), 5)]:
                    if st.checkbox(s, value=True, key=f"storey_toggle_{i}"):
                        visible_storeys.append(s)

    # Render viewer
    model_path = st.session_state.get("ifc_file_path")
    from components.ifc_viewer import render_viewer
    render_viewer(model_path, color_mode, visible_storeys)

with col_panel:
    st.subheader("Modell-Info")

    metadata = st.session_state.get("model_metadata", {})
    st.markdown(f"**Projekt:** {metadata.get('project_name', '–')}")
    st.markdown(f"**Schema:** {metadata.get('schema', '–')}")
    st.markdown(f"**Software:** {metadata.get('application', '–')}")

    st.divider()
    st.subheader("Statistik")

    if not element_df.empty:
        st.metric("Elemente gesamt", f"{len(element_df):,}")
        if "ifc_class" in element_df.columns:
            st.metric("IFC-Klassen", f"{element_df['ifc_class'].nunique()}")
        if "material" in element_df.columns:
            st.metric("Materialien", f"{element_df['material'].nunique()}")

    st.divider()
    st.subheader("Schnellauswahl")
    st.caption("Klicke auf ein Element im 3D-Viewer für Details.")
    st.info("3D-Viewer-Interaktion erfordert eine lokale Browser-Umgebung mit CORS-Support.")
