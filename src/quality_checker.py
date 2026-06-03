import pandas as pd
import numpy as np
from src.constants import ERROR_SEVERITY_THRESHOLDS


def _check_zero_volume(df):
    """Elements with zero or negative volume."""
    col = "volume_m3"
    if col not in df.columns:
        return []
    bad = df[df[col] <= 0]
    return [{"element_id": r.get("element_id",""), "error_type": "zero_volume",
              "severity": "critical", "description": f"Volume ≤ 0: {r.get(col,0):.3f} m³"}
            for _, r in bad.iterrows()]

def _check_duplicate_guids(df):
    """Duplicate element GUIDs."""
    col = "element_id"
    if col not in df.columns:
        return []
    dupes = df[df.duplicated(col, keep=False)]
    return [{"element_id": r.get(col,""), "error_type": "duplicate_guid",
              "severity": "critical", "description": "Duplicate element GUID"}
            for _, r in dupes.iterrows()]

def _check_orphaned_elements(df):
    """Elements without storey assignment."""
    col = "storey"
    if col not in df.columns:
        return []
    orphans = df[df[col].isna() | (df[col] == "")]
    return [{"element_id": r.get("element_id",""), "error_type": "orphaned_element",
              "severity": "warning", "description": "No storey assignment"}
            for _, r in orphans.iterrows()]


def check_quality(element_df: pd.DataFrame, space_df: pd.DataFrame, mode: str):
    errors = []

    if element_df is not None and not element_df.empty:
        for _, row in element_df.iterrows():
            eid = row.get("element_id", "?")
            ifc_class = row.get("ifc_class", "Unknown")
            storey = row.get("storey", "Unassigned")

            if row.get("material", "Unknown") in ("Unbekannt", "Unknown", None, ""):
                errors.append(
                    {
                        "element_id": eid,
                        "ifc_class": ifc_class,
                        "storey": storey,
                        "error_type": "missing_material",
                        "severity": "warning",
                        "description": "No material assigned",
                    }
                )

            area = row.get("area_m2")
            volume = row.get("volume_m3")
            length = row.get("length_m")
            has_qty = any(
                v is not None and not (isinstance(v, float) and np.isnan(v))
                for v in [area, volume, length]
            )
            if not has_qty:
                errors.append(
                    {
                        "element_id": eid,
                        "ifc_class": ifc_class,
                        "storey": storey,
                        "error_type": "missing_quantity",
                        "severity": "critical",
                        "description": "No quantity data (area/volume/length)",
                    }
                )

            if storey in ("Nicht zugeordnet", "Unassigned", None, ""):
                errors.append(
                    {
                        "element_id": eid,
                        "ifc_class": ifc_class,
                        "storey": storey,
                        "error_type": "missing_storey",
                        "severity": "warning",
                        "description": "Not assigned to any storey",
                    }
                )

            if mode == "umbau":
                status = row.get("status", "Not found")
                if status in ("Nicht gefunden", "Not found", None, ""):
                    errors.append(
                        {
                            "element_id": eid,
                            "ifc_class": ifc_class,
                            "storey": storey,
                            "error_type": "missing_status",
                            "severity": "critical",
                            "description": "No renovation status found",
                        }
                    )

        # New checks
        errors.extend(_check_zero_volume(element_df))
        errors.extend(_check_duplicate_guids(element_df))
        errors.extend(_check_orphaned_elements(element_df))

    if space_df is not None and not space_df.empty:
        for _, row in space_df.iterrows():
            if row.get("usage", "Unknown") in ("Unbekannt", "Unknown", None, ""):
                errors.append(
                    {
                        "element_id": row.get("space_id", "?"),
                        "ifc_class": "IfcSpace",
                        "storey": row.get("storey", "Unassigned"),
                        "error_type": "missing_usage",
                        "severity": "warning",
                        "description": "No usage type assigned",
                    }
                )

    error_df = (
        pd.DataFrame(errors)
        if errors
        else pd.DataFrame(
            columns=[
                "element_id",
                "ifc_class",
                "storey",
                "error_type",
                "severity",
                "description",
            ]
        )
    )

    error_counts = {
        "missing_material": 0,
        "missing_quantity": 0,
        "missing_storey": 0,
        "missing_usage": 0,
        "missing_status": 0,
        "zero_volume": 0,
        "duplicate_guid": 0,
        "orphaned_element": 0,
    }
    if not error_df.empty:
        for etype in error_counts:
            error_counts[etype] = int((error_df["error_type"] == etype).sum())

    total_elements = len(element_df) if element_df is not None else 0
    total_spaces = len(space_df) if space_df is not None else 0

    summary = {
        "error_counts": error_counts,
        "total_elements": total_elements,
        "total_spaces": total_spaces,
        "mode": mode,
    }
    return error_df, summary


def build_pset_matrix(element_df: pd.DataFrame) -> pd.DataFrame:
    if element_df.empty or "psets" not in element_df.columns:
        return pd.DataFrame()

    rows = []
    for _, row in element_df.iterrows():
        ifc_class = row.get("ifc_class", "Unknown")
        psets = row.get("psets", {})
        if isinstance(psets, dict):
            for pset_name in psets:
                rows.append({"ifc_class": ifc_class, "pset_name": pset_name})

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    matrix = df.groupby(["ifc_class", "pset_name"]).size().unstack(fill_value=0)
    return matrix


def calculate_quality_score(summary: dict) -> float:
    total = summary.get("total_elements", 0)
    if total == 0:
        return 100.0

    error_counts = summary.get("error_counts", {})
    critical_errors = (
        error_counts.get("missing_quantity", 0)
        + error_counts.get("missing_status", 0)
        + error_counts.get("zero_volume", 0)
        + error_counts.get("duplicate_guid", 0)
    )
    warning_errors = (
        error_counts.get("missing_material", 0)
        + error_counts.get("missing_storey", 0)
        + error_counts.get("missing_usage", 0)
        + error_counts.get("orphaned_element", 0)
    )

    penalty = (critical_errors * 2 + warning_errors * 1) / (total * 3)
    score = max(0.0, min(100.0, (1 - penalty) * 100))
    return round(score, 1)
