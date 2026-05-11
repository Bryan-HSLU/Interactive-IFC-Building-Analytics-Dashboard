COLORS = {
    "neubau": "#2ECC71",
    "abbruch": "#E74C3C",
    "bestand": "#95A5A6",
    "temporaer": "#F39C12",
    "primary": "#2980B9",
    "neutral": "#BDC3C7",
    "unknown": "#95A5A6",
    "error_ok": "#27AE60",
    "error_warning": "#E67E22",
    "error_critical": "#C0392B",
    "text": "#2C3E50",
    "text_light": "#7F8C8D",
    "grid": "#ECF0F1",
}

STATUS_COLORS = {
    "Neubau": "#2ECC71",
    "Abbruch": "#E74C3C",
    "Bestand": "#95A5A6",
    "Temporär": "#F39C12",
    "Nicht gefunden": "#BDC3C7",
}

CATEGORICAL_COLORS = [
    "#2980B9",
    "#E74C3C",
    "#2ECC71",
    "#F39C12",
    "#9B59B6",
    "#1ABC9C",
    "#E67E22",
    "#95A5A6",
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
