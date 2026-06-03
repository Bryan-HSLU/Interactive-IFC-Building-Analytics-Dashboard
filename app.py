import streamlit as st
from src.state_manager import init_session_state

st.set_page_config(
    page_title="IFC Building Analytics Dashboard",
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
        st.markdown("# 🏗️ IFC Building Analytics Dashboard")
        st.info("Upload an IFC file on **Page 1** to get started.")

st.title("🏗️ IFC Building Analytics Dashboard")
st.markdown("""
The **IFC Building Analytics Dashboard** reads IFC building models and presents them in four analysis views —
from the model overview to quality checks.

| View | Content | Audience |
|---|---|---|
| 🏠 **Overview** | Elements, storeys, areas, status | All |
| 🧱 **Quantities** | Materials, volumes, component types | Planners, Estimation |
| 🌱 **Sustainability & Costs** | CO₂, grey energy, construction costs (KBOB) | LCA, Clients |
| ✅ **Quality** | Completeness of IFC attributes & Psets | BIM Coordination |

**Start:** Upload an IFC file on → **1 Upload**, choose project mode, and start the analysis.
""")

if st.session_state.get("ifc_parsed"):
    metadata = st.session_state.get("model_metadata", {})
    mode = st.session_state.get("mode_project", "")
    st.divider()
    st.subheader("Loaded Model")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project", metadata.get("project_name", "–"))
    with col2:
        st.metric("Elements", f"{metadata.get('element_count', 0):,}".replace(",", "'"))
    with col3:
        mode_label = "New Build" if mode == "neubau" else "Renovation"
        st.metric("Mode", mode_label)
    with col4:
        st.metric("IFC Schema", metadata.get("schema", "–"))
