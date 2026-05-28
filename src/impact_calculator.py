import pandas as pd
import numpy as np
import re

# ── Aliases: ordered specific → general ──────────────────────────────────────
# Each entry: (list of substrings that trigger this key, material_key)
# First match wins → put specific patterns BEFORE general ones
MATERIAL_ALIASES = [
    # Concrete variants
    (["stahlbeton", "beton armiert", "beton bewehrt", "reinforced concrete", "rc beton", "stahlbet"], "reinforced_concrete"),
    (["leichtbeton", "lightweight concrete", "porenbeton", "ytong", "gasbeton"], "concrete_lightweight"),
    (["betonfertigteil", "betonstein", "precast", "fertigteil"], "precast_concrete"),
    (["beton", "concrete", "sichtbeton", "ortbeton", "fundament"], "concrete"),
    # Wood
    (["laubholz", "hardwood", "buche", "eiche", "esche", "ahorn"], "wood_hardwood"),
    (["nadelholz", "softwood", "fichte", "tanne", "kiefer", "lärche", "föhre", "holzwerkstoff", "holz"], "wood_softwood"),
    # Masonry
    (["backstein", "backsteinmauerwerk", "ziegel", "ziegelmauerwerk", "mauerziegel", "backsteinziegel"], "brick"),
    (["mauerwerk", "natursteinmauerwerk"], "brick"),
    # Insulation
    (["eps", "styropor", "polystyrol expandiert"], "insulation_eps"),
    (["pur", "pir", "polyurethan"], "insulation_pur"),
    (["mineralwolle", "steinwolle", "glaswolle", "mineral wool", "wärmedämmung", "dämmung", "dämmstoff", "isolation"], "insulation_mineral"),
    # Steel / Metal
    (["stahl", "steel", "eisen", "iron", "metal", "metall", "träger", "blech", "stahlprofil"], "steel"),
    (["aluminium", "aluminum", "alu "], "aluminum"),
    (["kupfer", "copper"], "copper"),
    (["zink", "zinc"], "zinc"),
    (["blei", "lead"], "lead"),
    # Glass
    (["glas", "glass", "verglasung", "isolierglas", "esg", "vsg"], "glass"),
    # Gypsum / plaster
    (["gipskarton", "gipsplatte", "rigips", "knauf"], "gypsum_board"),
    (["gips", "gypsum"], "gypsum"),
    (["verputz", "putz", "plaster", "rabitz", "bekleidung"], "plaster"),
    (["mörtel", "mortar", "unterlagsboden"], "mortar"),
    # Stone
    (["kalkstein", "limestone"], "limestone"),
    (["sandstein", "sandstone"], "sandstone"),
    (["naturstein", "natural stone", "granit", "marmor", "schiefer"], "natural_stone"),
    (["keramikfliesen", "fliesen", "tiles"], "ceramic_tile"),
    (["keramik", "ceramic", "terrakotta kachel"], "ceramic"),
    # Other
    (["bitumen", "dachpappe", "abdichtung"], "bitumen"),
    (["linoleum", "lino"], "linoleum"),
    (["pvc", "kunststoff", "plastik"], "pvc"),
    (["lehm", "clay", "stampflehm"], "clay"),
    (["kork", "cork"], "kork"),
    (["stroh", "straw"], "straw"),
    (["mineralfaser", "mineral fibre"], "mineral_fibre"),
    (["faserzement", "eternit", "fibre cement"], "fibre_cement"),
    (["gummi", "rubber", "kautschuk"], "rubber"),
    (["polyethylen", "pe ", "hdpe", "polyethylene"], "polyethylene"),
]


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


def _normalize(s: str) -> str:
    """Decode STEP ISO 10303 and ArchiCAD Unicode hex escapes, then lowercase, strip, and clean."""
    s = str(s).strip()

    # 1. Decode ArchiCAD hex escapes like \X\E4 -> \xe4 -> ä
    def repl_x(m):
        try:
            return bytes.fromhex(m.group(1)).decode('latin1')
        except Exception:
            return m.group(0)
    s = re.sub(r'\\X\\([0-9A-Fa-f]{2})', repl_x, s)

    # 2. Decode STEP ISO 10303 unicode escapes like \X2\00E4\X0\ -> ä
    def repl_x2(m):
        try:
            hex_str = m.group(1)
            chars = []
            for i in range(0, len(hex_str), 4):
                chars.append(chr(int(hex_str[i:i+4], 16)))
            return "".join(chars)
        except Exception:
            return m.group(0)
    s = re.sub(r'\\X2\\([0-9A-Fa-f]{4,})\\X0\\', repl_x2, s)

    s = s.lower()
    s = re.sub(r"[_\-/\\|,;:()]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()



def _match_material(material_name: str, factors_df: pd.DataFrame):
    if factors_df.empty or not material_name or str(material_name).strip() in ("", "nan"):
        return None

    normalized = _normalize(material_name)

    # 1. Direct exact match on material_key
    exact = factors_df[factors_df["material_key"] == normalized]
    if not exact.empty:
        return exact.iloc[0]

    # 2. Alias matching — specific before general, first match wins
    for triggers, key in MATERIAL_ALIASES:
        for trigger in triggers:
            if trigger in normalized:
                row = factors_df[factors_df["material_key"] == key]
                if not row.empty:
                    return row.iloc[0]

    # 3. Reverse: check if any KBOB label word appears in the normalized name
    for _, row in factors_df.iterrows():
        label = _normalize(str(row.get("material_label_de", "")))
        if label and len(label) > 3 and label in normalized:
            return row

    # 4. Word-level overlap: any significant word from KBOB label in IFC name
    for _, row in factors_df.iterrows():
        label = _normalize(str(row.get("material_label_de", "")))
        words = [w for w in label.split() if len(w) > 4]
        if words and all(w in normalized for w in words[:1]):
            return row

    return None


def calculate_impacts(element_df: pd.DataFrame, factors_df: pd.DataFrame) -> pd.DataFrame:
    if element_df.empty:
        return element_df

    df = element_df.copy()
    co2_list, energy_list, cost_list = [], [], []

    for _, row in df.iterrows():
        # ── 1. Use embedded ArchiCAD values if available (primary source) ──
        co2_archicad    = row.get("co2e_archicad")
        energy_archicad = row.get("grey_energy_archicad")

        co2_val    = _to_float(co2_archicad)
        energy_val = _to_float(energy_archicad)
        cost_val   = None  # ArchiCAD does not embed cost → always use KBOB

        # ── 2. KBOB fallback for missing values ────────────────────────────
        if co2_val is None or energy_val is None:
            material = str(row.get("material", "Unbekannt"))
            volume   = row.get("volume_m3")
            factor   = _match_material(material, factors_df)

            if factor is not None and volume is not None:
                try:
                    vol = float(volume)
                    if not np.isnan(vol) and vol > 0:
                        if co2_val is None:
                            co2_val    = _safe_mul(factor.get("co2e_kg_per_m3"), vol)
                        if energy_val is None:
                            energy_val = _safe_mul(factor.get("grey_energy_kwh_per_m3"), vol)
                        cost_val = _safe_mul(factor.get("cost_chf_per_m3"), vol)
                except Exception:
                    pass

        co2_list.append(co2_val)
        energy_list.append(energy_val)
        cost_list.append(cost_val)

    df["co2e_total"]      = co2_list
    df["grey_energy_kwh"] = energy_list
    df["cost_chf"]        = cost_list
    return df


def get_match_coverage(element_df: pd.DataFrame) -> float:
    """Returns percentage of elements with a CO2 value (ArchiCAD or KBOB)."""
    if element_df.empty or "co2e_total" not in element_df.columns:
        return 0.0
    matched = pd.to_numeric(element_df["co2e_total"], errors="coerce").notna().sum()
    return matched / len(element_df) * 100


def get_unmatched_materials(element_df: pd.DataFrame) -> list:
    """Returns list of unique material names that could not be matched."""
    if element_df.empty or "co2e_total" not in element_df.columns:
        return []
    mask = pd.to_numeric(element_df["co2e_total"], errors="coerce").isna()
    return sorted(element_df.loc[mask, "material"].dropna().unique().tolist())


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

    co2_vals    = pd.to_numeric(impact_df["co2e_total"], errors="coerce")
    energy_vals = pd.to_numeric(impact_df.get("grey_energy_kwh", pd.Series(dtype=float)), errors="coerce")
    cost_vals   = pd.to_numeric(impact_df.get("cost_chf", pd.Series(dtype=float)), errors="coerce")

    summary["co2e_total"]        = float(co2_vals.sum(skipna=True))
    summary["grey_energy_total"] = float(energy_vals.sum(skipna=True))
    summary["cost_total"]        = float(cost_vals.sum(skipna=True))

    matched = co2_vals.notna().sum()
    total   = len(impact_df)
    summary["coverage_pct"] = (matched / total * 100) if total > 0 else 0.0

    ngf = 0.0
    if space_df is not None and not space_df.empty and "area_m2" in space_df.columns:
        ngf = float(pd.to_numeric(space_df["area_m2"], errors="coerce").sum(skipna=True))

    if ngf > 0:
        summary["co2e_per_m2"]    = summary["co2e_total"] / ngf
        summary["cost_per_m2"]    = summary["cost_total"] / ngf
        summary["energy_per_m2"]  = summary["grey_energy_total"] / ngf

    return summary


def _to_float(val) -> float | None:
    """Safely convert a value to float, return None if not possible or NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _safe_mul(factor_val, volume: float):
    try:
        if factor_val is None or (isinstance(factor_val, float) and np.isnan(factor_val)):
            return None
        return float(factor_val) * volume
    except Exception:
        return None
