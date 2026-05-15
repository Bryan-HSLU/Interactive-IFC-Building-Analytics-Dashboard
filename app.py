import streamlit as st
from src.state_manager import init_session_state

st.set_page_config(
    page_title="IFC Building Analytics",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# Sidebar content when no file is loaded
if not st.session_state.get("ifc_parsed"):
    with st.sidebar:
        st.markdown("# IFC Analytics")
        st.info("Lade eine IFC-Datei auf **Seite 1** hoch, um zu beginnen.")

st.title("IFC Building Analytics Dashboard")
st.markdown("""
Willkommen beim IFC Building Analytics Dashboard.

**Erste Schritte:**
1. Gehe zu **1 Upload** in der Seitenleiste
2. Lade eine IFC-Datei hoch
3. Wähle den Projektmodus (Neubau / Umbau)
4. Klicke auf **Analyse starten**

Die Analyseergebnisse sind dann auf den weiteren Seiten verfügbar.
""")

if st.session_state.get("ifc_parsed"):
    metadata = st.session_state.get("model_metadata", {})
    mode = st.session_state.get("mode_project", "")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Projekt", metadata.get("project_name", "–"))
    with col2:
        st.metric("Elemente", f"{metadata.get('element_count', 0):,}")
    with col3:
        mode_label = "Neubau" if mode == "neubau" else "Umbau / Sanierung"
        st.metric("Modus", mode_label)
