import streamlit as st
import pandas as pd


def render_sidebar(element_df: pd.DataFrame, space_df: pd.DataFrame, mode: str):
    with st.sidebar:
        st.markdown("# IFC Analytics")

        if mode:
            if mode == "neubau":
                st.markdown("**Modus:** Neubau")
            else:
                st.markdown("**Modus:** Umbau / Sanierung")

        quality_summary = st.session_state.get("quality_summary", {})
        if quality_summary:
            error_counts = quality_summary.get("error_counts", {})
            total_errors = sum(error_counts.values())
            score = quality_summary.get("score", 0)
            if total_errors == 0:
                st.markdown(f"**Qualit\u00e4t:** OK \u2014 {score:.0f}%")
            elif total_errors <= 10:
                st.markdown(f"**Qualit\u00e4t:** Warnung \u2014 {total_errors} Fehler ({score:.0f}%)")
            else:
                st.markdown(f"**Qualit\u00e4t:** Kritisch \u2014 {total_errors} Fehler ({score:.0f}%)")

        st.divider()

        if element_df is not None and not element_df.empty:
            st.subheader("Filter")

            if "storey" in element_df.columns:
                all_storeys = sorted(element_df["storey"].dropna().unique().tolist())
                selected_storeys = st.multiselect(
                    "Geschoss",
                    options=all_storeys,
                    default=st.session_state.get("filter_storeys", []),
                    key="sidebar_storeys",
                )
                st.session_state.filter_storeys = selected_storeys

            if "ifc_class" in element_df.columns:
                all_classes = sorted(element_df["ifc_class"].dropna().unique().tolist())
                selected_classes = st.multiselect(
                    "IFC-Klasse",
                    options=all_classes,
                    default=st.session_state.get("filter_classes", []),
                    key="sidebar_classes",
                )
                st.session_state.filter_classes = selected_classes

            if "status" in element_df.columns:
                all_statuses = ["Alle"] + sorted(element_df["status"].dropna().unique().tolist())
                current = st.session_state.get("filter_status", "Alle")
                if current not in all_statuses:
                    current = "Alle"
                selected_status = st.selectbox(
                    "Element-Status",
                    options=all_statuses,
                    index=all_statuses.index(current),
                    key="sidebar_status",
                )
                st.session_state.filter_status = selected_status

        active = []
        if st.session_state.get("filter_storeys"):
            active.append(f"Geschoss: {', '.join(st.session_state.filter_storeys)}")
        if st.session_state.get("filter_classes"):
            active.append(f"Klasse: {', '.join(st.session_state.filter_classes)}")
        if st.session_state.get("filter_status") and st.session_state.get("filter_status") != "Alle":
            active.append(f"Status: {st.session_state.filter_status}")
        if active:
            st.sidebar.info("Aktive Filter:\n" + "\n".join(f"- {a}" for a in active))

        st.divider()

        st.subheader("Einheiten")
        # fix #7: Hinweis dass Einheiten auf Tabellenwerte wirken
        st.caption("Wirkt auf Tabellenwerte (nicht Charts)")
        st.session_state.unit_area = st.selectbox("Fl\u00e4che", ["m\u00b2", "cm\u00b2"], index=0, key="unit_area_sel")
        st.session_state.unit_volume = st.selectbox("Volumen", ["m\u00b3", "cm\u00b3"], index=0, key="unit_vol_sel")
        st.session_state.unit_mass = st.selectbox("Masse", ["kg", "t"], index=0, key="unit_mass_sel")


def render_cross_filter_reset(page_key: str, filter_keys: list):
    active = any(st.session_state.get(k) for k in filter_keys)
    if active:
        key_labels = {
            "cf_page3_usage":        "Nutzung",
            "cf_page3_storey":       "Geschoss",
            "cf_page3_size_bin":     "Gr\u00f6ssenklasse",
            "cf_page3_room":         "Raum",
            "cf_page4_class":        "IFC-Klasse",
            "cf_page4_material":     "Material",
            "cf_page5_material":     "Material",
            "cf_page5_treemap":      "Kategorie",
            "cf_page5_heatmap":      "W\u00e4rmekarte",
            "cf_page6_error_cat":    "Fehlerkategorie",
            "cf_page6_status_class": "Statusklasse",
            "overview_storey":       "Geschoss (Overview)",
        }
        active_labels = []
        for k in filter_keys:
            val = st.session_state.get(k)
            if val:
                label = key_labels.get(k, k)
                if k == "cf_page3_size_bin" and isinstance(val, tuple):
                    display_val = f"~{val[0]:.0f} m\u00b2"
                else:
                    display_val = val
                active_labels.append(f"{label}: **{display_val}**")

        st.info(f"Aktiver Filter \u2014 {' | '.join(active_labels)}")
        if st.button("Filter zur\u00fccksetzen", key=f"reset_{page_key}"):
            for k in filter_keys:
                st.session_state[k] = None
            st.rerun()


def get_active_filters() -> dict:
    return {
        "storeys": st.session_state.get("filter_storeys", []),
        "classes": st.session_state.get("filter_classes", []),
        "status": st.session_state.get("filter_status", "Alle"),
    }
