import streamlit as st
import pandas as pd


def init_session_state():
    st.session_state.setdefault("ifc_model", None)
    st.session_state.setdefault("ifc_file_path", None)
    st.session_state.setdefault("ifc_parsed", False)

    st.session_state.setdefault("mode_project", None)
    st.session_state.setdefault("mode_pset_name", "Pset_RevitElement")
    st.session_state.setdefault("mode_pset_property", "Phase Created")

    st.session_state.setdefault("element_df", None)
    st.session_state.setdefault("space_df", None)
    st.session_state.setdefault("storey_df", None)
    st.session_state.setdefault("impact_df", None)
    st.session_state.setdefault("error_df", None)
    st.session_state.setdefault("quality_summary", None)
    st.session_state.setdefault("model_metadata", None)

    st.session_state.setdefault("filter_storeys", [])
    st.session_state.setdefault("filter_classes", [])
    st.session_state.setdefault("filter_status", "Alle")

    st.session_state.setdefault("unit_area", "m²")
    st.session_state.setdefault("unit_volume", "m³")
    st.session_state.setdefault("unit_mass", "kg")

    st.session_state.setdefault("cf_page3_usage", None)
    st.session_state.setdefault("cf_page3_storey", None)
    st.session_state.setdefault("cf_page3_size_bin", None)
    st.session_state.setdefault("cf_page4_class", None)
    st.session_state.setdefault("cf_page4_material", None)
    st.session_state.setdefault("cf_page5_material", None)
    st.session_state.setdefault("cf_page5_treemap", None)
    st.session_state.setdefault("cf_page5_heatmap", None)
    st.session_state.setdefault("cf_page6_error_cat", None)
    st.session_state.setdefault("cf_page6_status_class", None)


def store_parsed_data(parsed_data: dict, mode: str, pset_config: dict):
    from src.data_processor import build_element_df, build_space_df
    from src.impact_calculator import load_factors, calculate_impacts
    from src.quality_checker import check_quality, calculate_quality_score
    from src.constants import KBOB_CSV_PATH

    element_df = build_element_df(parsed_data, mode, pset_config)
    space_df = build_space_df(parsed_data)

    factors_df = load_factors(KBOB_CSV_PATH)
    impact_df = calculate_impacts(element_df, factors_df)

    error_df, quality_summary = check_quality(impact_df, space_df, mode)
    quality_summary["score"] = calculate_quality_score(quality_summary)

    st.session_state.element_df = impact_df
    st.session_state.space_df = space_df
    st.session_state.storey_df = parsed_data.get("storeys", pd.DataFrame())
    st.session_state.impact_df = impact_df
    st.session_state.error_df = error_df
    st.session_state.quality_summary = quality_summary
    st.session_state.model_metadata = parsed_data.get("metadata", {})
    st.session_state.mode_project = mode
    st.session_state.ifc_parsed = True

    # Reset global filters when new file loaded
    st.session_state.filter_storeys = []
    st.session_state.filter_classes = []
    st.session_state.filter_status = "Alle"


def get_element_df(filtered: bool = True) -> pd.DataFrame:
    df = st.session_state.get("element_df")
    if df is None or df.empty:
        return pd.DataFrame()
    if filtered:
        df = apply_global_filters(df)
    return df


def get_space_df(filtered: bool = True) -> pd.DataFrame:
    df = st.session_state.get("space_df")
    if df is None or df.empty:
        return pd.DataFrame()
    if filtered:
        storeys = st.session_state.get("filter_storeys", [])
        if storeys:
            df = df[df["storey"].isin(storeys)]
    return df


def get_impact_df(filtered: bool = True) -> pd.DataFrame:
    return get_element_df(filtered)


def get_quality_data():
    return (
        st.session_state.get("error_df", pd.DataFrame()),
        st.session_state.get("quality_summary", {}),
    )


def apply_global_filters(df: pd.DataFrame) -> pd.DataFrame:
    storeys = st.session_state.get("filter_storeys", [])
    classes = st.session_state.get("filter_classes", [])
    status = st.session_state.get("filter_status", "Alle")

    if storeys and "storey" in df.columns:
        df = df[df["storey"].isin(storeys)]
    if classes and "ifc_class" in df.columns:
        df = df[df["ifc_class"].isin(classes)]
    if status != "Alle" and "status" in df.columns:
        df = df[df["status"] == status]
    return df
