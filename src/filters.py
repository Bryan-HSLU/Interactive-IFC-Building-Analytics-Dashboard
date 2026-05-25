import streamlit as st
import pandas as pd


def render_sidebar(element_df: pd.DataFrame, space_df: pd.DataFrame, mode: str):
    with st.sidebar:
        st.markdown("# IFC Analytics")

        # Mode badge
        if mode:
            if mode == "neubau":
                st.markdown("**Modus:** Neubau")
            else:
                st.markdown("**Modus:** Umbau / Sanierung")

        # Quality badge
        quality_summary = st.session_state.get("quality_summary", {})
        if quality_summary:
            error_counts = quality_summary.get("error_counts", {})
            total_errors = sum(error_counts.values())
            score = quality_summary.get("score", 0)
            if total_errors == 0:
                st.markdown(f"**Qualität:** OK — {score:.0f}%")
            elif total_errors <= 10:
                st.markdown(f"**Qualität:** Warnung — {total_errors} Fehler ({score:.0f}%)")
            else:
                st.markdown(f"**Qualität:** Kritisch — {total_errors} Fehler ({score:.0f}%)")

        st.divider()

        # Global filters
        if element_df is not None and not element_df.empty:
            st.subheader("Filter")

            # Storey filter
            if "storey" in element_df.columns:
                all_storeys = sorted(element_df["storey"].dropna().unique().tolist())
                selected_storeys = st.multiselect(
                    "Geschoss",
                    options=all_storeys,
                    default=st.session_state.get("filter_storeys", []),
                    key="sidebar_storeys",
                )
                st.session_state.filter_storeys = selected_storeys

            # IFC class filter
            if "ifc_class" in element_df.columns:
                all_classes = sorted(element_df["ifc_class"].dropna().unique().tolist())
                selected_classes = st.multiselect(
                    "IFC-Klasse",
                    options=all_classes,
                    default=st.session_state.get("filter_classes", []),
                    key="sidebar_classes",
                )
                st.session_state.filter_classes = selected_classes

            # Status filter
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

        # Active global filter summary
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

        # Unit settings
        st.subheader("Einheiten")
        st.session_state.unit_area = st.selectbox("Fläche", ["m²", "cm²"], index=0, key="unit_area_sel")
        st.session_state.unit_volume = st.selectbox("Volumen", ["m³", "cm³"], index=0, key="unit_vol_sel")
        st.session_state.unit_mass = st.selectbox("Masse", ["kg", "t"], index=0, key="unit_mass_sel")


def render_cross_filter_reset(page_key: str, filter_keys: list):
    active = any(st.session_state.get(k) for k in filter_keys)
    if active:
        active_labels = []
        key_labels = {
            "cf_page3_usage": "Nutzung",
            "cf_page3_storey": "Geschoss",
            "cf_page3_size_bin": "Grössenklasse",
            "cf_page4_class": "IFC-Klasse",
            "cf_page4_material": "Material",
            "cf_page5_material": "Material",
            "cf_page5_treemap": "Kategorie",
            "cf_page6_error_cat": "Fehlerkategorie",
            "cf_page6_status_class": "Statusklasse",
        }
        for k in filter_keys:
            val = st.session_state.get(k)
            if val:
                label = key_labels.get(k, k)
                active_labels.append(f"{label}: **{val}**")

        st.info(f"Aktiver Filter — {' | '.join(active_labels)}")
        if st.button("Filter zurücksetzen", key=f"reset_{page_key}"):
            for k in filter_keys:
                st.session_state[k] = None
            st.rerun()


def get_active_filters() -> dict:
    return {
        "storeys": st.session_state.get("filter_storeys", []),
        "classes": st.session_state.get("filter_classes", []),
        "status": st.session_state.get("filter_status", "Alle"),
    }
