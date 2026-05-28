COLORS = {
    "neubau": "#1A7F8E",     # Petrol/Teal — neu, frisch, konstruktiv
    "abbruch": "#A0522D",    # Warm-Braun — erdig, "wegräumen", kein Rot/Orange
    "bestand": "#7F8C8D",    # Mittelgrau — neutral, "schon da"
    "temporaer": "#7D3C98",  # Violett — besonders, selten
    "primary": "#34495E",    # Schiefer-Blau — dunkel, seriös
    "neutral": "#BDC3C7",
    "unknown": "#95A5A6",
    "error_ok": "#1A7F8E",       # Petrol — kein Problem (konsistent mit Neubau)
    "error_warning": "#D4A017",  # Amber — Aufmerksamkeit, kein Orange
    "error_critical": "#7B3F00", # Dunkelbraun — ernst, schwer, kein Rot
    "text": "#2C3E50",
    "text_light": "#7F8C8D",
    "grid": "#ECF0F1",
}

STATUS_COLORS = {
    "Neubau": "#1A7F8E",         # Petrol
    "Abbruch": "#A0522D",        # Warm-Braun
    "Bestand": "#7F8C8D",        # Grau
    "Temporär": "#7D3C98",       # Violett
    "Nicht gefunden": "#BDC3C7",
}

# Max 7 distinct categories (cognitive load principle)
CATEGORICAL_COLORS = [
    "#1A7F8E",  # Petrol (Hauptfarbe)
    "#A0522D",  # Warm-Braun
    "#7D3C98",  # Violett
    "#D4A017",  # Amber
    "#2E86AB",  # Stahlblau (distinct von Petrol)
    "#6C8EBF",  # Blaugrau
    "#95A5A6",  # Grau (Sonstige/Unbekannt)
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
