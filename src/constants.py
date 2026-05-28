COLORS = {
    "neubau": "#4CAF93",     # Mintgrün — neu, wachsend, positiv
    "abbruch": "#D97B4F",    # Terrakotta — Rückbau, warm aber kein Alarm
    "bestand": "#8DA89E",    # Salbeigrau — neutral, natürlich, schon da
    "temporaer": "#A67DB8",  # Gedämpftes Violett — speziell, selten
    "primary": "#2E7D6B",    # Tannengrün — Nachhaltigkeit, BIM, Hauptfarbe
    "neutral": "#C8D5D2",
    "unknown": "#A8B8B4",
    "error_ok": "#4CAF93",       # Mintgrün — alles gut
    "error_warning": "#D4A017",  # Amber — Aufmerksamkeit
    "error_critical": "#C0492C", # Ziegelrot — ernst, klar lesbar
    "text": "#2C3E35",
    "text_light": "#6B8C85",
    "grid": "#EAF0EE",
}

STATUS_COLORS = {
    "Neubau": "#4CAF93",         # Mintgrün
    "Abbruch": "#D97B4F",        # Terrakotta
    "Bestand": "#8DA89E",        # Salbeigrau
    "Temporär": "#A67DB8",       # Gedämpftes Violett
    "Nicht gefunden": "#C8D5D2",
}

# Max 7 distinct categories — kohärentes Natur/Nachhaltigkeits-Schema
CATEGORICAL_COLORS = [
    "#2E7D6B",  # Tannengrün (Hauptfarbe)
    "#4CAF93",  # Mintgrün
    "#8DA89E",  # Salbeigrau
    "#D97B4F",  # Terrakotta
    "#D4A017",  # Amber/Sand
    "#A67DB8",  # Gedämpftes Violett
    "#A8B8B4",  # Grau (Sonstige/Unbekannt)
]

CHART_DEFAULTS = {
    "font_family": "Inter, sans-serif",
    "font_size": 12,
    "font_color": "#2C3E35",
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
    "co2": "kg CO₂e",
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
