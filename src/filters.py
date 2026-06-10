import streamlit as st
import pandas as pd


def render_sidebar(element_df: pd.DataFrame, space_df: pd.DataFrame, mode: str):
    with st.sidebar:
        st.markdown("# IFC Analytics")

        if mode:
            if mode == "neubau":
                st.markdown("**Mode:** New Build")
            else:
                st.markdown("**Mode:** Renovation")

        quality_summary = st.session_state.get("quality_summary", {})
        if quality_summary:
            error_counts = quality_summary.get("error_counts", {})
            total_errors = sum(error_counts.values())
            score = quality_summary.get("score", 0)
            if score == 100:
                st.markdown(f"**Quality:** Excellent — {score:.0f}%")
            elif score >= 95:
                st.markdown(f"**Quality:** Very Good — {score:.0f}%")
            elif score >= 91:
                st.markdown(f"**Quality:** Good — {score:.0f}%")
            elif score >= 80:
                st.markdown(f"**Quality:** Sufficient — {score:.0f}%")
            else:
                st.markdown(f"**Quality:** Critical — {score:.0f}%")

        st.divider()

        if element_df is not None and not element_df.empty:
            st.subheader("Filters")

            if "storey" in element_df.columns:
                all_storeys = sorted(element_df["storey"].dropna().unique().tolist())
                selected_storeys = st.multiselect(
                    "Storey",
                    options=all_storeys,
                    default=st.session_state.get("filter_storeys", []),
                    key="sidebar_storeys",
                )
                st.session_state.filter_storeys = selected_storeys

            if "ifc_class" in element_df.columns:
                all_classes = sorted(element_df["ifc_class"].dropna().unique().tolist())
                selected_classes = st.multiselect(
                    "IFC Class",
                    options=all_classes,
                    default=st.session_state.get("filter_classes", []),
                    key="sidebar_classes",
                )
                st.session_state.filter_classes = selected_classes

            if "status" in element_df.columns:
                all_statuses = ["All"] + sorted(
                    element_df["status"].dropna().unique().tolist()
                )
                current = st.session_state.get("filter_status", "All")
                if current not in all_statuses:
                    current = "All"
                selected_status = st.selectbox(
                    "Element Status",
                    options=all_statuses,
                    index=all_statuses.index(current),
                    key="sidebar_status",
                )
                st.session_state.filter_status = selected_status

        active = []
        if st.session_state.get("filter_storeys"):
            active.append(f"Storey: {', '.join(st.session_state.filter_storeys)}")
        if st.session_state.get("filter_classes"):
            active.append(f"Class: {', '.join(st.session_state.filter_classes)}")
        if (
            st.session_state.get("filter_status")
            and st.session_state.get("filter_status") != "All"
        ):
            active.append(f"Status: {st.session_state.filter_status}")
        if active:
            st.sidebar.info("Active Filters:\n" + "\n".join(f"- {a}" for a in active))
            try:
                from src.state_manager import get_element_df
                df_f = get_element_df(filtered=True)
                if df_f is not None and element_df is not None:
                    st.sidebar.caption(f"Showing: {len(df_f):,} of {len(element_df):,} elements")
            except Exception:
                pass

        st.divider()

        st.subheader("Units")
        st.caption("Applies to table values (not charts)")
        st.session_state.unit_area = st.selectbox(
            "Area", ["m²", "cm²"], index=0, key="unit_area_sel"
        )
        st.session_state.unit_volume = st.selectbox(
            "Volume", ["m³", "cm³"], index=0, key="unit_vol_sel"
        )
        st.session_state.unit_mass = st.selectbox(
            "Mass", ["kg", "t"], index=0, key="unit_mass_sel"
        )


def render_cross_filter_reset(page_key: str, filter_keys: list):
    active = any(st.session_state.get(k) for k in filter_keys)
    if active:
        key_labels = {
            "cf_page3_usage": "Usage",
            "cf_page3_storey": "Storey",
            "cf_page3_size_bin": "Size Class",
            "cf_page3_room": "Room",
            "cf_page4_class": "IFC Class",
            "cf_page4_material": "Material",
            "cf_page5_material": "Material",
            "cf_page5_treemap": "Category",
            "cf_page5_heatmap": "Heatmap",
            "cf_page6_error_cat": "Error Category",
            "cf_page6_status_class": "Status Class",
            "overview_storey": "Storey (Overview)",
        }
        active_labels = []
        for k in filter_keys:
            val = st.session_state.get(k)
            if val:
                label = key_labels.get(k, k)
                if k == "cf_page3_size_bin" and isinstance(val, tuple):
                    display_val = f"~{val[0]:.0f} m²"
                else:
                    display_val = val
                active_labels.append(f"{label}: **{display_val}**")

        st.info(f"Active Filter — {' | '.join(active_labels)}")
        if st.button("Reset Filter", key=f"reset_{page_key}"):
            for k in filter_keys:
                st.session_state[k] = None
            st.rerun()


def get_active_filters() -> dict:
    return {
        "storeys": st.session_state.get("filter_storeys", []),
        "classes": st.session_state.get("filter_classes", []),
        "status": st.session_state.get("filter_status", "All"),
    }
