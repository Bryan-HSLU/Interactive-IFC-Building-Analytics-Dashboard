import pandas as pd
import numpy as np
from pathlib import Path

STATUS_MAP = {
    "new": "Neubau", "neu": "Neubau", "neubau": "Neubau",
    "existing": "Bestand", "bestand": "Bestand", "exist": "Bestand",
    "demolished": "Abbruch", "abbruch": "Abbruch", "rückbau": "Abbruch",
    "demolish": "Abbruch", "demo": "Abbruch", "to be demolished": "Abbruch",
    "temporary": "Temporär", "temporär": "Temporär", "temp": "Temporär",
}

RENOVATION_STATUS_KEYS = ["Renovation Status", "renovation status", "RenovationStatus", "Status", "Phase"]

# Default thickness in metres per IFC class — used when volume_m3 is missing
DEFAULT_THICKNESS = {
    "IfcWall": 0.25,
    "IfcWallStandardCase": 0.25,
    "IfcSlab": 0.20,
    "IfcRoof": 0.20,
    "IfcColumn": 0.30,
    "IfcBeam": 0.20,
    "IfcCovering": 0.02,
    "IfcPlate": 0.01,
    "IfcMember": 0.10,
    "IfcCurtainWall": 0.10,
    "IfcDoor": 0.05,
    "IfcWindow": 0.02,
    "IfcStair": 0.20,
    "IfcStairFlight": 0.20,
    "IfcRailing": 0.05,
    "IfcBuildingElementProxy": 0.10,
    "IfcFlowSegment": 0.05,
    "IfcFlowTerminal": 0.05,
    "IfcFlowFitting": 0.05,
    "IfcEnergyConversionDevice": 0.10,
}
DEFAULT_THICKNESS_FALLBACK = 0.15


def build_element_df(parsed_data: dict, mode: str, pset_config: dict) -> pd.DataFrame:
    elements = parsed_data.get("elements", [])
    if not elements:
        return pd.DataFrame()

    df = pd.DataFrame(elements)
    df = assign_status(
        df, mode, pset_config.get("pset_name", ""), pset_config.get("pset_property", "")
    )
    df = normalize_materials(df)
    df = calculate_missing_quantities(df)

    for col in ["co2e_total", "grey_energy_kwh", "cost_chf", "load_bearing"]:
        if col not in df.columns:
            df[col] = None

    return df


def build_space_df(parsed_data: dict) -> pd.DataFrame:
    spaces = parsed_data.get("spaces", [])
    if not spaces:
        return pd.DataFrame()

    df = pd.DataFrame(spaces)
    if "usage" in df.columns:
        df["usage"] = df["usage"].fillna("Unbekannt").astype(str).str.strip()
        df.loc[df["usage"] == "", "usage"] = "Unbekannt"
    return df


def assign_status(
    df: pd.DataFrame, mode: str, pset_name: str, property_name: str
) -> pd.DataFrame:
    if mode == "neubau":
        df["status"] = "Neubau"
        return df

    def _get_status(row):
        psets = row.get("psets", {})
        if not isinstance(psets, dict):
            return "Bestand"

        # 1) Try configured pset + property
        status_value = None
        if pset_name:
            target_pset = psets.get(pset_name, {})
            if isinstance(target_pset, dict):
                status_value = target_pset.get(property_name)

        # 2) Scan all psets for known renovation status keys
        if status_value is None:
            for pset_data in psets.values():
                if not isinstance(pset_data, dict):
                    continue
                for key in RENOVATION_STATUS_KEYS:
                    if key in pset_data:
                        status_value = pset_data[key]
                        break
                if status_value is not None:
                    break

        if status_value is None:
            return "Bestand"
        normalized = str(status_value).strip().lower()
        return STATUS_MAP.get(normalized, "Bestand")

    df["status"] = df.apply(_get_status, axis=1)
    return df


def normalize_materials(df: pd.DataFrame) -> pd.DataFrame:
    """Keep original IFC material name — matching happens in impact_calculator.
    Only clean up obvious issues (None, empty, whitespace).
    """
    if "material" not in df.columns:
        return df
    df["material"] = df["material"].fillna("Unbekannt").astype(str).str.strip()
    df.loc[df["material"].isin(["", "None", "nan"]), "material"] = "Unbekannt"
    return df


def calculate_missing_quantities(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure numeric types and estimate volume_m3 from area * default thickness
    when volume is missing or zero.
    """
    for col in ["area_m2", "volume_m3", "length_m", "weight_kg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] <= 0, col] = np.nan

    # Estimate volume where missing
    if "volume_m3" in df.columns and "area_m2" in df.columns:
        missing_vol = df["volume_m3"].isna()
        if missing_vol.any():

            def _estimate_vol(row):
                area = row.get("area_m2")
                if pd.isna(area) or area <= 0:
                    return np.nan
                ifc_class = row.get("ifc_class", "")
                thickness = DEFAULT_THICKNESS.get(ifc_class, DEFAULT_THICKNESS_FALLBACK)
                return round(area * thickness, 4)

            estimated = df[missing_vol].apply(_estimate_vol, axis=1)
            df.loc[missing_vol, "volume_m3"] = estimated
            df["volume_estimated"] = False
            df.loc[missing_vol, "volume_estimated"] = True
        else:
            df["volume_estimated"] = False
    elif "area_m2" in df.columns:
        # volume_m3 column doesn't exist at all — create it from area
        def _estimate_vol_full(row):
            area = row.get("area_m2")
            if pd.isna(area) or area <= 0:
                return np.nan
            thickness = DEFAULT_THICKNESS.get(
                row.get("ifc_class", ""), DEFAULT_THICKNESS_FALLBACK
            )
            return round(area * thickness, 4)

        df["volume_m3"] = df.apply(_estimate_vol_full, axis=1)
        df["volume_estimated"] = True

    return df