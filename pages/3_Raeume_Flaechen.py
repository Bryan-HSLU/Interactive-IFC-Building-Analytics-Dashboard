import streamlit as st
from src.state_manager import init_session_state, get_space_df, get_element_df
from src.filters import render_sidebar

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

st.title("Räume & Flächen")

st.info(
    "Diese Seite ist für dieses Projekt deaktiviert, "
    "da das verwendete IFC-Modell keine IfcSpace-Elemente enthält.\n\n"
    "Die Raumauswertung steht zur Verfügung, sobald ein Modell mit "
    "definierten Räumen (IfcSpace) hochgeladen wird."
)
