"""Shared UI helper components for all pages."""
import streamlit as st
import pandas as pd
from src.constants import COLORS


def kpi_card(label: str, value: str, delta_text: str = "", delta_color: str = "") -> None:
    """Render a KPI card with optional delta line using custom Markdown.

    Used instead of st.metric so we can control delta colour freely
    (st.metric only supports 'normal' / 'inverse' / 'off').
    """
    delta_html = ""
    if delta_text:
        color = delta_color or COLORS["text_light"]
        delta_html = f'<div style="font-size:0.78rem;color:{color};margin-top:2px;">{delta_text}</div>'
    st.markdown(
        f'<div style="background:rgba(0,0,0,0.03);border-radius:8px;padding:10px 14px;margin-bottom:6px;">'
        f'<div style="font-size:0.8rem;color:{COLORS["text_light"]};">{label}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;color:{COLORS["text"]};">{value}</div>'
        f'{delta_html}</div>',
        unsafe_allow_html=True,
    )


# ── Unit conversion factors ───────────────────────────────────────────────────
_AREA_FACTORS = {"m\u00b2": 1.0, "cm\u00b2": 10_000.0}
_VOLUME_FACTORS = {"m\u00b3": 1.0, "cm\u00b3": 1_000_000.0}
_MASS_FACTORS = {"kg": 1.0, "t": 0.001}


def apply_unit_conversion(
    display_df: pd.DataFrame,
    unit_area: str = "m\u00b2",
    unit_volume: str = "m\u00b3",
    unit_mass: str = "kg",
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Convert numeric columns in a display DataFrame to the chosen units.

    Looks for column names that contain the patterns below (case-insensitive)
    and scales them by the appropriate factor.  Returns the converted DataFrame
    and a rename mapping so callers can update column headers.

    Detected column patterns:
      - area  : columns whose name contains "m\u00b2" or "fl\u00e4che"
      - volume: columns whose name contains "m\u00b3" or "volumen"
      - mass  : columns whose name contains "(kg)" or "masse"
    """
    df = display_df.copy()
    rename: dict[str, str] = {}

    area_factor = _AREA_FACTORS.get(unit_area, 1.0)
    vol_factor = _VOLUME_FACTORS.get(unit_volume, 1.0)
    mass_factor = _MASS_FACTORS.get(unit_mass, 1.0)

    for col in df.columns:
        col_lower = col.lower()
        # Area columns
        if "m\u00b2" in col or "fl\u00e4che" in col_lower:
            if area_factor != 1.0:
                df[col] = pd.to_numeric(df[col], errors="coerce") * area_factor
                new_name = col.replace("m\u00b2", unit_area)
                rename[col] = new_name
        # Volume columns
        elif "m\u00b3" in col or "volumen" in col_lower:
            if vol_factor != 1.0:
                df[col] = pd.to_numeric(df[col], errors="coerce") * vol_factor
                new_name = col.replace("m\u00b3", unit_volume)
                rename[col] = new_name
        # Mass columns  (co2e is kg but should NOT be converted – only explicit mass cols)
        elif "(kg)" in col and "co2" not in col_lower:
            if mass_factor != 1.0:
                df[col] = pd.to_numeric(df[col], errors="coerce") * mass_factor
                new_name = col.replace("(kg)", f"({unit_mass})")
                rename[col] = new_name

    if rename:
        df = df.rename(columns=rename)

    return df, rename


def unit_caption(unit_area: str, unit_volume: str, unit_mass: str) -> str:
    """Return a short caption string describing the active units."""
    parts = []
    if unit_area != "m\u00b2":
        parts.append(f"Fl\u00e4che in {unit_area}")
    if unit_volume != "m\u00b3":
        parts.append(f"Volumen in {unit_volume}")
    if unit_mass != "kg":
        parts.append(f"Masse in {unit_mass}")
    return " | ".join(parts) if parts else ""
