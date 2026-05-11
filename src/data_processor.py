import pandas as pd
import numpy as np


STATUS_MAP = {
    "new": "Neubau", "neu": "Neubau", "neubau": "Neubau",
    "existing": "Bestand", "bestand": "Bestand", "exist": "Bestand",
    "demolished": "Abbruch", "abbruch": "Abbruch", "rückbau": "Abbruch",
    "demolish": "Abbruch", "demo": "Abbruch",
    "temporary": "Temporär", "temporär": "Temporär", "temp": "Temporär",
}


def build_element_df(parsed_data: dict, mode: str, pset_config: dict) -> pd.DataFrame:
    elements = parsed_data.get("elements", [])
    if not elements:
        return pd.DataFrame()

    df = pd.DataFrame(elements)
    df = assign_status(df, mode, pset_config.get("pset_name", ""), pset_config.get("pset_property", ""))
    df = normalize_materials(df)
    df = calculate_missing_quantities(df)

    # Ensure required columns exist
    for col in ["co2e_total", "grey_energy_kwh", "cost_chf"]:
        if col not in df.columns:
            df[col] = None

    return df


def build_space_df(parsed_data: dict) -> pd.DataFrame:
    spaces = parsed_data.get("spaces", [])
    if not spaces:
        return pd.DataFrame()

    df = pd.DataFrame(spaces)

    # Normalize usage: strip whitespace, empty → "Unbekannt"
    if "usage" in df.columns:
        df["usage"] = df["usage"].fillna("Unbekannt").astype(str).str.strip()
        df.loc[df["usage"] == "", "usage"] = "Unbekannt"

    return df


def assign_status(df: pd.DataFrame, mode: str, pset_name: str, property_name: str) -> pd.DataFrame:
    if mode == "neubau":
        df["status"] = "Neubau"
        return df

    # Umbau mode: read from psets
    def _get_status(row):
        psets = row.get("psets", {})
        if not isinstance(psets, dict):
            return "Nicht gefunden"
        target_pset = psets.get(pset_name, {})
        if not isinstance(target_pset, dict):
            return "Nicht gefunden"
        status_value = target_pset.get(property_name)
        if status_value is None:
            # Try common alternative Psets
            for alt_pset in ["Pset_BuildingElementCommon", "Pset_WallCommon", "Pset_SlabCommon"]:
                alt = psets.get(alt_pset, {})
                if isinstance(alt, dict) and "Status" in alt:
                    status_value = alt["Status"]
                    break
        if status_value is None:
            return "Nicht gefunden"
        normalized = str(status_value).strip().lower()
        return STATUS_MAP.get(normalized, "Nicht gefunden")

    df["status"] = df.apply(_get_status, axis=1)
    return df


def normalize_materials(df: pd.DataFrame) -> pd.DataFrame:
    if "material" not in df.columns:
        return df

    MATERIAL_NORMALIZE = {
        "beton": "Beton",
        "stahlbeton": "Stahlbeton",
        "stahl": "Stahl",
        "holz": "Holz",
        "holz (nadelholz)": "Holz (Nadelholz)",
        "holz (laubholz)": "Holz (Laubholz)",
        "ziegel": "Backstein",
        "backstein": "Backstein",
        "glas": "Glas",
        "dämmung": "Dämmung",
        "gips": "Gips",
        "aluminium": "Aluminium",
        "kupfer": "Kupfer",
        "pvc": "PVC",
        "keramik": "Keramik",
        "mörtel": "Mörtel",
        "bitumen": "Bitumen",
    }

    def _normalize(mat: str) -> str:
        if not mat or mat == "Unbekannt":
            return "Unbekannt"
        lower = mat.lower()
        for key, val in MATERIAL_NORMALIZE.items():
            if key in lower:
                return val
        return mat

    df["material"] = df["material"].apply(_normalize)
    return df


def calculate_missing_quantities(df: pd.DataFrame) -> pd.DataFrame:
    # If volume is missing but area and a typical thickness can be estimated, skip for now
    # Just ensure types are correct
    for col in ["area_m2", "volume_m3", "length_m", "weight_kg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[df[col] <= 0, col] = np.nan
    return df
