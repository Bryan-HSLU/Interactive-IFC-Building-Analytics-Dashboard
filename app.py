import streamlit as st
from src.state_manager import init_session_state

st.set_page_config(
    page_title="IFC Cockpit",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

if not st.session_state.get("ifc_parsed"):
    with st.sidebar:
        st.markdown("# 🏗️ IFC Cockpit")
        st.info("IFC-Datei auf **Seite 1** hochladen, um zu starten.")

st.title("🏗️ IFC Cockpit")
st.markdown("""
Das **IFC Cockpit** liest IFC-Gebäudemodelle aus und stellt sie in vier Analysesichten dar —
von der Modellübersicht bis zur Qualitätsprüfung.

| Sicht | Inhalt | Zielgruppe |
|---|---|---|
| 🏠 **Übersicht** | Elemente, Geschosse, Flächen, Status | Alle |
| 🧱 **Mengen** | Materialien, Volumen, Bauteiltypen | Planer, Kalkulation |
| 🌱 **Nachhaltigkeit & Kosten** | CO₂, Graue Energie, Baukosten (KBOB) | Ökobilanz, Bauherrschaft |
| ✅ **Qualität** | Vollständigkeit der IFC-Attribute & Psets | BIM-Koordination |

**Start:** IFC-Datei auf → **1 Upload** hochladen, Projektmodus wählen, Analyse starten.
""")

if st.session_state.get("ifc_parsed"):
    metadata = st.session_state.get("model_metadata", {})
    mode = st.session_state.get("mode_project", "")
    st.divider()
    st.subheader("Geladenes Modell")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Projekt", metadata.get("project_name", "–"))
    with col2:
        st.metric("Elemente", f"{metadata.get('element_count', 0):,}".replace(",", "'"))
    with col3:
        mode_label = "Neubau" if mode == "neubau" else "Umbau"
        st.metric("Modus", mode_label)
    with col4:
        st.metric("IFC-Schema", metadata.get("schema", "–"))
