"""Shared UI helper components for all pages."""

import streamlit as st
import pandas as pd
from src.constants import COLORS


def kpi_card(
    label: str, value: str, delta_text: str = "", delta_color: str = ""
) -> None:
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
        f"{delta_html}</div>",
        unsafe_allow_html=True,
    )

def fmt_co2(val: float) -> str:
    return f"{val:,.0f}".replace(",", "'") + " kg CO₂e"

def fmt_chf(val: float) -> str:
    return "CHF " + f"{val:,.0f}".replace(",", "'")

def fmt_area(val: float) -> str:
    return f"{val:,.1f}".replace(",", "'") + " m²"

def hero_kpi_card(label: str, value: str, unit: str = "", delta: str = "") -> None:
    unit_html = f'<span style="font-size:0.9rem;font-weight:400;color:{COLORS["text_light"]};margin-left:4px;">{unit}</span>' if unit else ""
    delta_html = f'<div style="font-size:0.85rem;color:{COLORS["error_ok"]};margin-top:4px;">{delta}</div>' if delta else ""
    st.markdown(
        f'<div style="background:#FFFFFF;border-top:4px solid {COLORS["primary"]};border-radius:6px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,0.1);margin-bottom:12px;">'
        f'<div style="font-size:0.85rem;color:{COLORS["text_light"]};text-transform:uppercase;letter-spacing:0.5px;">{label}</div>'
        f'<div style="font-size:2rem;font-weight:700;color:{COLORS["text"]};margin-top:4px;line-height:1.1;">{value}{unit_html}</div>'
        f"{delta_html}</div>",
        unsafe_allow_html=True,
    )

def scenario_card(title: str, value: float, fmt_func) -> None:
    val_str = fmt_func(value)
    st.markdown(
        f'<div style="background:#F7F9FB;border-radius:6px;padding:12px;border:1px solid {COLORS["grid"]};">'
        f'<div style="font-size:0.85rem;color:{COLORS["text_light"]};">{title}</div>'
        f'<div style="font-size:1.4rem;font-weight:600;color:{COLORS["text"]};">{val_str}</div>'
        f'</div>',
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
