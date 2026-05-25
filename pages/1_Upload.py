import streamlit as st
import tempfile
import os
from src.state_manager import init_session_state, store_parsed_data, get_quality_data

st.set_page_config(page_title="Upload – IFC Analytics", page_icon=None, layout="wide")
init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

st.title("Upload & Projektmodus")

# ── Section A: Upload & Mode Selection ────────────────────────────────────
uploaded_file = st.file_uploader(
    "IFC-Datei hochladen",
    type=["ifc"],
    help="Unterstützte Formate: IFC2x3, IFC4",
)

st.subheader("Projektmodus")
col1, col2 = st.columns(2)

with col1:
    neubau_selected = st.session_state.get("mode_project") == "neubau"
    border_neubau = "2px solid #2980B9" if neubau_selected else "2px solid #e0e0e0"
    bg_neubau = "#EBF5FB" if neubau_selected else "#FAFAFA"
    st.markdown(
        f"""<div style="border:{border_neubau};border-radius:8px;padding:16px;background:{bg_neubau};cursor:pointer;">
        <h3 style="margin:0">Neubau</h3>
        <p style="margin:8px 0 0 0;color:#555;">Alle Elemente werden als Neubau behandelt.<br>Keine Statusauswertung aus IFC-Psets.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Neubau wählen", key="btn_neubau", use_container_width=True):
        st.session_state.mode_project = "neubau"
        st.rerun()

with col2:
    umbau_selected = st.session_state.get("mode_project") == "umbau"
    border_umbau = "2px solid #E67E22" if umbau_selected else "2px solid #e0e0e0"
    bg_umbau = "#FDEBD0" if umbau_selected else "#FAFAFA"
    st.markdown(
        f"""<div style="border:{border_umbau};border-radius:8px;padding:16px;background:{bg_umbau};cursor:pointer;">
        <h3 style="margin:0">Umbau / Sanierung</h3>
        <p style="margin:8px 0 0 0;color:#555;">Status wird aus IFC-Psets gelesen.<br>Fallback auf "Bestand" wenn keine Daten vorhanden.</p>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("Umbau wählen", key="btn_umbau", use_container_width=True):
        st.session_state.mode_project = "umbau"
        st.rerun()

# Pset configurator (Umbau only)
pset_config = {}
if st.session_state.get("mode_project") == "umbau":
    st.subheader("Pset-Konfiguration")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        pset_name = st.text_input(
            "Pset-Name für Status",
            value=st.session_state.get("mode_pset_name", "Pset_RevitElement"),
            key="pset_name_input",
        )
        st.session_state.mode_pset_name = pset_name
    with pcol2:
        pset_prop = st.text_input(
            "Property-Name für Status",
            value=st.session_state.get("mode_pset_property", "Phase Created"),
            key="pset_prop_input",
        )
        st.session_state.mode_pset_property = pset_prop
    pset_config = {"pset_name": pset_name, "pset_property": pset_prop}
    st.info("Wenn keine Statusdaten gefunden werden, werden alle Elemente als **Bestand** behandelt.")
else:
    pset_config = {
        "pset_name": st.session_state.get("mode_pset_name", "Pset_RevitElement"),
        "pset_property": st.session_state.get("mode_pset_property", "Phase Created"),
    }

# Analyse starten button
mode_ready = st.session_state.get("mode_project") is not None
file_ready = uploaded_file is not None

st.divider()
btn_disabled = not (file_ready and mode_ready)
if not file_ready:
    st.caption("Bitte zuerst eine IFC-Datei hochladen.")
if not mode_ready:
    st.caption("Bitte einen Projektmodus wählen.")

if st.button(
    "Analyse starten",
    disabled=btn_disabled,
    type="primary",
    use_container_width=True,
):
    # ── Section B: Parsing Progress ────────────────────────────────────
    progress = st.progress(0)
    status_box = st.status("Analyse wird gestartet…", expanded=True)

    with status_box:
        warnings = []

        # Save to temp file
        st.write("Datei lesen…")
        progress.progress(10)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        try:
            st.write("IFC-Schema erkennen…")
            progress.progress(20)
            from src.ifc_parser import parse_ifc_file
            parsed_data = parse_ifc_file(tmp_path)

            schema = parsed_data.get("schema", "Unbekannt")
            st.write(f"Schema erkannt: **{schema}**")
            progress.progress(35)

            st.write("Entities extrahieren…")
            elem_count = len(parsed_data.get("elements", []))
            st.write(f"   → {elem_count} Bauelemente gefunden")
            progress.progress(50)

            st.write("IfcSpace auslesen…")
            space_count = len(parsed_data.get("spaces", []))
            if space_count == 0:
                warnings.append("IfcSpace nicht gefunden — Raumseite (Seite 3) wird eingeschränkt verfügbar sein.")
            st.write(f"   → {space_count} Räume gefunden")
            progress.progress(65)

            st.write("Mengen berechnen & Status zuweisen…")
            progress.progress(80)

            mode = st.session_state.get("mode_project", "neubau")
            store_parsed_data(parsed_data, mode, pset_config)
            st.session_state.ifc_file_path = tmp_path

            progress.progress(95)
            st.write("Qualitätsprüfung abgeschlossen")
            progress.progress(100)
            status_box.update(label="Analyse abgeschlossen", state="complete")

        except ValueError as e:
            status_box.update(label="Fehler bei der Analyse", state="error")
            st.error(f"Fehler: {e}")
            os.unlink(tmp_path)
            st.stop()
        except Exception as e:
            status_box.update(label="Unerwarteter Fehler", state="error")
            st.error(f"Unerwarteter Fehler: {e}")
            os.unlink(tmp_path)
            st.stop()

    for w in warnings:
        st.warning(w)

    st.rerun()

# ── Section C: Model Metadata (after analysis) ────────────────────────────
if st.session_state.get("ifc_parsed"):
    st.divider()
    st.subheader("Modell-Übersicht")

    metadata = st.session_state.get("model_metadata", {})
    element_df = st.session_state.get("element_df")
    space_df = st.session_state.get("space_df")
    storey_df = st.session_state.get("storey_df")

    # Mode badge
    _mode = st.session_state.get("mode_project", "")
    _mode_label = "Neubau" if _mode == "neubau" else "Umbau / Sanierung"
    _mode_color = "#D6EAF8" if _mode == "neubau" else "#FDEBD0"
    st.markdown(
        f'<div style="display:inline-block;background:{_mode_color};border-radius:6px;'
        f'padding:4px 12px;font-weight:600;margin-bottom:8px;">{_mode_label}</div>',
        unsafe_allow_html=True,
    )

    # KPI cards
    _, _quality_summary = get_quality_data()
    _score = _quality_summary.get("score", 0) if _quality_summary else 0
    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        st.metric("Bauelemente", f"{metadata.get('element_count', 0):,}")
    with kpi_cols[1]:
        st.metric("Räume (IfcSpace)", f"{metadata.get('space_count', 0):,}")
    with kpi_cols[2]:
        st.metric("Geschosse", f"{metadata.get('storey_count', 0):,}")
    with kpi_cols[3]:
        st.metric("IFC-Schema", metadata.get("schema", "–"))
    with kpi_cols[4]:
        st.metric("Software", metadata.get("application", "–"))
    with kpi_cols[5]:
        st.metric("Modellqualität", f"{_score:.0f}%")

    # Metadata table
    st.subheader("Projektinformationen")
    import pandas as pd
    meta_rows = {
        "Projektname": metadata.get("project_name", "nicht im Modell hinterlegt"),
        "Autor": metadata.get("author", "nicht im Modell hinterlegt"),
        "Organisation": metadata.get("organization", "nicht im Modell hinterlegt"),
        "IFC-Schema": metadata.get("schema", "–"),
        "Exportierende Software": metadata.get("application", "nicht im Modell hinterlegt"),
    }
    st.table(pd.DataFrame.from_dict(meta_rows, orient="index", columns=["Wert"]))

    # Umbau: status overview
    mode = st.session_state.get("mode_project")
    if mode == "umbau" and element_df is not None and not element_df.empty:
        st.subheader("Statusverteilung (Umbau-Modus)")
        status_counts = element_df["status"].value_counts()
        scols = st.columns(len(status_counts))
        for i, (status, count) in enumerate(status_counts.items()):
            scols[i].metric(status, f"{count:,}")

        not_found = int((element_df["status"] == "Nicht gefunden").sum())
        if not_found > 0:
            st.warning(
                f"{not_found} Elemente ohne Statusdaten — auf Seite 6 überprüfen."
            )

    # Sidebar
    from src.filters import render_sidebar
    render_sidebar(element_df, space_df, mode)
