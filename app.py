import streamlit as st
from src.state_manager import init_session_state

st.set_page_config(
    page_title="IFC Building Analytics",
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

# Sidebar content when no file is loaded
if not st.session_state.get("ifc_parsed"):
    with st.sidebar:
        st.markdown("# IFC Analytics")
        st.info("Upload an IFC file on **Page 1** to get started.")

st.title("IFC Building Analytics Dashboard")
st.markdown("""
Welcome to the IFC Building Analytics Dashboard.

**Getting started:**
1. Go to **1 Upload** in the sidebar
2. Upload an IFC file
3. Select the project mode (New Build / Renovation)
4. Click **Start Analysis**

The analysis results will then be available on the other pages.
""")

if st.session_state.get("ifc_parsed"):
    metadata = st.session_state.get("model_metadata", {})
    mode = st.session_state.get("mode_project", "")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Project", metadata.get("project_name", "–"))
    with col2:
        st.metric("Elements", f"{metadata.get('element_count', 0):,}")
    with col3:
        mode_label = "New Build" if mode == "neubau" else "Renovation"
        st.metric("Mode", mode_label)
    with col4:
        st.metric("Authors", "Bryan Wiederkehr · Genc Haxhija")
