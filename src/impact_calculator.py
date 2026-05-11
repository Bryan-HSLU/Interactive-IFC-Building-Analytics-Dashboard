import pandas as pd
import numpy as np


MATERIAL_MATCH_KEYS = {
    "beton": "concrete",
    "stahlbeton": "reinforced_concrete",
    "stahl": "steel",
    "holz (nadelholz)": "wood_softwood",
    "holz (laubholz)": "wood_hardwood",
    "holz": "wood_softwood",
    "backstein": "brick",
    "ziegel": "brick",
    "glas": "glass",
    "dämmung eps": "insulation_eps",
    "dämmung mineralwolle": "insulation_mineral",
    "dämmung": "insulation_mineral",
    "gips": "gypsum",
    "aluminium": "aluminum",
    "kupfer": "copper",
    "pvc": "pvc",
    "keramik": "ceramic",
    "mörtel": "mortar",
    "bitumen": "bitumen",
    "unbekannt": "unknown",
}


def load_factors(csv_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "material_key", "material_label_de",
            "co2e_kg_per_m3", "grey_energy_kwh_per_m3",
            "cost_chf_per_m3", "density_kg_per_m3",
        ])


def _match_material(material_name: str, factors_df: pd.DataFrame):
    if factors_df.empty or not material_name:
        return None
    normalized = material_name.lower().strip()

    # Exact match on material_key
    exact = factors_df[factors_df["material_key"] == normalized]
    if not exact.empty:
        return exact.iloc[0]

    # Map via our lookup table
    for key, factor_key in MATERIAL_MATCH_KEYS.items():
        if key in normalized:
            match = factors_df[factors_df["material_key"] == factor_key]
            if not match.empty:
                return match.iloc[0]

    # Contains match on material_label_de
    for _, row in factors_df.iterrows():
        label = str(row.get("material_label_de", "")).lower()
        if label and label in normalized:
            return row

    return None


def calculate_impacts(element_df: pd.DataFrame, factors_df: pd.DataFrame) -> pd.DataFrame:
    if element_df.empty:
        return element_df

    df = element_df.copy()
    co2_list, energy_list, cost_list = [], [], []

    for _, row in df.iterrows():
        material = row.get("material", "Unbekannt")
        volume = row.get("volume_m3")
        factor = _match_material(material, factors_df)

        if factor is not None and volume is not None and not np.isnan(float(volume)):
            vol = float(volume)
            co2 = _safe_mul(factor.get("co2e_kg_per_m3"), vol)
            energy = _safe_mul(factor.get("grey_energy_kwh_per_m3"), vol)
            cost = _safe_mul(factor.get("cost_chf_per_m3"), vol)
        else:
            co2, energy, cost = None, None, None

        co2_list.append(co2)
        energy_list.append(energy)
        cost_list.append(cost)

    df["co2e_total"] = co2_list
    df["grey_energy_kwh"] = energy_list
    df["cost_chf"] = cost_list
    return df


def get_impact_summary(impact_df: pd.DataFrame, space_df: pd.DataFrame, mode: str) -> dict:
    summary = {
        "co2e_total": 0.0,
        "grey_energy_total": 0.0,
        "cost_total": 0.0,
        "co2e_per_m2": None,
        "cost_per_m2": None,
        "energy_per_m2": None,
        "coverage_pct": 0.0,
    }

    if impact_df.empty:
        return summary

    co2_vals = pd.to_numeric(impact_df["co2e_total"], errors="coerce")
    energy_vals = pd.to_numeric(impact_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce")
    cost_vals = pd.to_numeric(impact_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce")

    summary["co2e_total"] = float(co2_vals.sum(skipna=True))
    summary["grey_energy_total"] = float(energy_vals.sum(skipna=True))
    summary["cost_total"] = float(cost_vals.sum(skipna=True))

    # Coverage
    matched = co2_vals.notna().sum()
    total = len(impact_df)
    summary["coverage_pct"] = (matched / total * 100) if total > 0 else 0.0

    # Per m²
    ngf = 0.0
    if space_df is not None and not space_df.empty and "area_m2" in space_df.columns:
        ngf = float(pd.to_numeric(space_df["area_m2"], errors="coerce").sum(skipna=True))

    if ngf > 0:
        summary["co2e_per_m2"] = summary["co2e_total"] / ngf
        summary["cost_per_m2"] = summary["cost_total"] / ngf
        summary["energy_per_m2"] = summary["grey_energy_total"] / ngf

    return summary


def _safe_mul(factor_val, volume: float):
    try:
        if factor_val is None or (isinstance(factor_val, float) and np.isnan(factor_val)):
            return None
        return float(factor_val) * volume
    except Exception:
        return None
