COLORS = {
    "neubau": "#2980B9",    # Blue — construction/future
    "abbruch": "#E67E22",   # Orange — demolition/warning
    "bestand": "#95A5A6",   # Gray — existing/unchanged
    "temporaer": "#8E44AD", # Purple — temporary/special
    "primary": "#2980B9",
    "neutral": "#BDC3C7",
    "unknown": "#95A5A6",
    "error_ok": "#2980B9",      # Blue (was green — red/green removed)
    "error_warning": "#E67E22", # Orange
    "error_critical": "#E67E22",# Orange bold (differentiated by text weight)
    "text": "#2C3E50",
    "text_light": "#7F8C8D",
    "grid": "#ECF0F1",
}

STATUS_COLORS = {
    "Neubau": "#2980B9",        # Blue
    "Abbruch": "#E67E22",       # Orange
    "Bestand": "#95A5A6",       # Gray
    "Temporär": "#8E44AD",      # Purple
    "Nicht gefunden": "#BDC3C7",
}

# Max 7 distinct categories (Unterrichtsprinzip)
CATEGORICAL_COLORS = [
    "#5DADE2",  # Light blue (distinct from primary #2980B9)
    "#E67E22",  # Orange
    "#A569BD",  # Purple
    "#1ABC9C",  # Teal
    "#F4D03F",  # Yellow
    "#EC407A",  # Pink
    "#95A5A6",  # Gray (Sonstige/Unbekannt)
]

CHART_DEFAULTS = {
    "font_family": "Inter, sans-serif",
    "font_size": 12,
    "font_color": "#2C3E50",
    "margin": dict(l=60, r=20, t=50, b=50),
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
}

UNITS = {
    "area": "m²",
    "volume": "m³",
    "mass": "kg",
    "energy": "kWh",
    "cost": "CHF",
    "co2": "kg CO2e",
}

IFC_CLASS_LABELS = {
    "IfcWall": "Wand",
    "IfcWallStandardCase": "Wand",
    "IfcSlab": "Decke/Boden",
    "IfcColumn": "Stütze",
    "IfcBeam": "Balken",
    "IfcDoor": "Tür",
    "IfcWindow": "Fenster",
    "IfcRoof": "Dach",
    "IfcStair": "Treppe",
    "IfcStairFlight": "Treppenlauf",
    "IfcRailing": "Geländer",
    "IfcCovering": "Bekleidung",
    "IfcCurtainWall": "Vorhangfassade",
    "IfcPlate": "Platte",
    "IfcMember": "Bauteil",
    "IfcBuildingElementProxy": "Sonstiges",
    "IfcFlowSegment": "Rohrleitung",
    "IfcFlowTerminal": "Anschlussgerät",
    "IfcFlowFitting": "Rohrverbindung",
    "IfcEnergyConversionDevice": "Energiegerät",
}

ERROR_SEVERITY_THRESHOLDS = {
    "ok": 0,
    "warning": 1,
    "critical": 10,
}

SIA_2032_LIMIT = 11.0  # kg CO2e/m²·a

KBOB_CSV_PATH = "data/kbob_factors.csv"
