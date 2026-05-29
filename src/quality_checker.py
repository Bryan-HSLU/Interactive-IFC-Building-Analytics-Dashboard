import pandas as pd
import numpy as np
from src.constants import ERROR_SEVERITY_THRESHOLDS


def check_quality(element_df: pd.DataFrame, space_df: pd.DataFrame, mode: str):
    errors = []

    if element_df is not None and not element_df.empty:
        for _, row in element_df.iterrows():
            eid = row.get("element_id", "?")
            ifc_class = row.get("ifc_class", "Unbekannt")
            storey = row.get("storey", "Nicht zugeordnet")

            if row.get("material", "Unbekannt") in ("Unbekannt", None, ""):
                errors.append(
                    {
                        "element_id": eid,
                        "ifc_class": ifc_class,
                        "storey": storey,
                        "error_type": "missing_material",
                        "severity": "Warnung",
                        "description": "Kein Material zugewiesen",
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
                        "severity": "kritisch",
                        "description": "Keine Mengenangaben (Fläche/Volumen/Länge)",
                    }
                )

            if storey == "Nicht zugeordnet":
                errors.append(
                    {
                        "element_id": eid,
                        "ifc_class": ifc_class,
                        "storey": storey,
                        "error_type": "missing_storey",
                        "severity": "Warnung",
                        "description": "Keinem Geschoss zugeordnet",
                    }
                )

            if mode == "umbau":
                status = row.get("status", "Nicht gefunden")
                if status in ("Nicht gefunden", None, ""):
                    errors.append(
                        {
                            "element_id": eid,
                            "ifc_class": ifc_class,
                            "storey": storey,
                            "error_type": "missing_status",
                            "severity": "kritisch",
                            "description": "Kein Umbau-Status gefunden",
                        }
                    )

    if space_df is not None and not space_df.empty:
        for _, row in space_df.iterrows():
            if row.get("usage", "Unbekannt") in ("Unbekannt", None, ""):
                errors.append(
                    {
                        "element_id": row.get("space_id", "?"),
                        "ifc_class": "IfcSpace",
                        "storey": row.get("storey", "Nicht zugeordnet"),
                        "error_type": "missing_usage",
                        "severity": "Warnung",
                        "description": "Kein Nutzungstyp zugewiesen",
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
        ifc_class = row.get("ifc_class", "Unbekannt")
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
    critical_errors = error_counts.get("missing_quantity", 0) + error_counts.get(
        "missing_status", 0
    )
    warning_errors = (
        error_counts.get("missing_material", 0)
        + error_counts.get("missing_storey", 0)
        + error_counts.get("missing_usage", 0)
    )

    penalty = (critical_errors * 2 + warning_errors * 1) / (total * 3)
    score = max(0.0, min(100.0, (1 - penalty) * 100))
    return round(score, 1)
