# Unified Color Palette and Constants according to Course Guidelines

COLORS = {
    "neubau": "#2E86AB",         # Stahlblau (Akzentfarbe)
    "abbruch": "#D94F3D",        # Rot — Abbruch / hohe Belastung
    "bestand": "#8B8B8B",        # Mittelgrau — neutral, Bestand
    "temporaer": "#5C6E7E",      # Blaugrau
    "primary": "#2E86AB",        # Stahlblau — Akzentfarbe
    "neutral": "#CCCCCC",        # Hellgrau — Nicht-selektiert
    "unknown": "#CCCCCC",
    "error_ok": "#A8D5B5",       # Grün — kein Fehler
    "error_warning": "#F5E642",  # Gelb — Warnung
    "error_critical": "#D94F3D", # Rot — kritischer Fehler
    "text": "#2D2D2D",           # Dunkelgrau
    "text_light": "#8B8B8B",     # Mittelgrau
    "grid": "#EAEAEA",           # Sehr helles Grau für Gitternetzlinien
}

STATUS_COLORS = {
    "Neubau": "#2E86AB",
    "Abbruch": "#D94F3D",
    "Bestand": "#8B8B8B",
    "Temporär": "#5C6E7E",
    "Nicht gefunden": "#CCCCCC",
}

# Sequential scale for CO2: Low (Green) -> Mid (Yellow) -> High (Red)
CO2_SCALE = [
    "#A8D5B5",  # Niedrig
    "#F5E642",  # Mittel
    "#D94F3D",  # Hoch
]

# Consistent Room Type Palette
ROOM_COLORS = {
    "Büro": "#2E86AB",       # Stahlblau
    "Flur": "#8B8B8B",       # Mittelgrau
    "Korridor": "#8B8B8B",
    "Erschliessung": "#8B8B8B",
    "WC": "#C8A96E",         # Amber/Gold
    "Technik": "#5C6E7E",    # Blaugrau
    "Wohnen": "#A8D4E6",     # Hellblau
    "Andere": "#CCCCCC",     # Hellgrau
    "Sonstige": "#CCCCCC",
    "Unbekannt": "#CCCCCC",
}

# Consistent Material Palette
MATERIAL_COLORS = {
    "Stahlbeton": "#2E86AB",     # Stahlblau
    "Beton": "#2E86AB",
    "Stahl": "#5C6E7E",          # Blaugrau
    "Metall": "#5C6E7E",
    "Holz": "#C8A96E",           # Holz/Gold
    "Backstein": "#D94F3D",      # Ziegelrot
    "Ziegel": "#D94F3D",
    "Dämmung": "#A8D4E6",        # Hellblau
    "Glas": "#8B8B8B",           # Neutralgrau
    "Gips": "#CCCCCC",           # Hellgrau
    "Andere": "#CCCCCC",
    "Sonstige": "#CCCCCC",
    "Unbekannt": "#CCCCCC",
}

CATEGORICAL_COLORS = [
    "#2E86AB",  # Büro
    "#8B8B8B",  # Flur
    "#C8A96E",  # WC
    "#5C6E7E",  # Technik
    "#A8D4E6",  # Wohnen
    "#CCCCCC",  # Andere
]

CHART_DEFAULTS = {
    "font_family": "Inter, sans-serif",
    "font_size": 12,
    "font_color": "#2D2D2D",
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
