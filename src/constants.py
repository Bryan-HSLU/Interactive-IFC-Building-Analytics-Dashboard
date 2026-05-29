# Unified Color Palette and Constants according to Course Guidelines

COLORS = {
    "neubau": "#2E86AB",  # Stahlblau (Akzentfarbe)
    "abbruch": "#D94F3D",  # Rot — Abbruch / hohe Belastung
    "bestand": "#8B8B8B",  # Mittelgrau — neutral, Bestand
    "temporaer": "#5C6E7E",  # Blaugrau
    "primary": "#2E86AB",  # Stahlblau — Akzentfarbe
    "neutral": "#CCCCCC",  # Hellgrau — Nicht-selektiert
    "unknown": "#CCCCCC",
    "error_ok": "#A8D5B5",  # Grün — kein Fehler
    "error_warning": "#F5E642",  # Gelb — Warnung
    "error_critical": "#D94F3D",  # Rot — kritischer Fehler
    "text": "#2D2D2D",  # Dunkelgrau
    "text_light": "#8B8B8B",  # Mittelgrau
    "grid": "#EAEAEA",  # Sehr helles Grau für Gitternetzlinien
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
    "Veloraum": "#E07B39",  # Lager/Technik (Orange)
    "Abstellkamer": "#E07B39",
    "Abstellraum": "#E07B39",
    "Technik": "#E07B39",
    "Saal": "#2E86AB",  # Aufenthalt (Blau)
    "Restaurant": "#2E86AB",
    "Bar/Empfang": "#2E86AB",
    "Empfang": "#2E86AB",
    "Bar": "#2E86AB",
    "Warteraum": "#2E86AB",
    "WC": "#7B5EA7",  # Sanitär (Lila)
    "WC Damen": "#7B5EA7",
    "WC Herren": "#7B5EA7",
    "Treppenhaus": "#5C8A6E",  # Verkehr (Grün)
    "Vorraum": "#5C8A6E",
    "Andere": "#CCCCCC",  # Grau
    "Sonstige": "#CCCCCC",
    "Unbekannt": "#CCCCCC",
}

# Consistent Material Palette
MATERIAL_COLORS = {
    "Stahlbeton": "#2E86AB",  # Stahlblau
    "Beton": "#2E86AB",
    "Stahl": "#5C6E7E",  # Blaugrau
    "Metall": "#5C6E7E",
    "Holz": "#C8A96E",  # Holz/Gold
    "Backstein": "#D94F3D",  # Ziegelrot
    "Ziegel": "#D94F3D",
    "Dämmung": "#A8D4E6",  # Hellblau
    "Glas": "#8B8B8B",  # Neutralgrau
    "Gips": "#CCCCCC",  # Hellgrau
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

# --- Constants extracted from logic files (Magic Numbers) ---

IFC_STANDARD_CROSS_SECTIONS = {
    "IfcBeam": 0.006,
    "IfcColumn": 0.09,
    "IfcMember": 0.004,
    "IfcRailing": 0.001,
}

IFC_STANDARD_THICKNESSES = {
    "IfcWall": 0.25,
    "IfcWallStandardCase": 0.25,
    "IfcSlab": 0.30,
    "IfcRoof": 0.25,
    "IfcCovering": 0.02,
    "IfcCurtainWall": 0.05,
    "IfcDoor": 0.05,
    "IfcWindow": 0.03,
    "IfcPlate": 0.01,
}

USAGE_MULTIPLIERS = {
    "technik": 2.6,
    "wc": 1.9,
    "büro": 1.1,
    "wohn": 1.0,
    "flur": 0.5,
    "korridor": 0.5,
    "erschliessung": 0.5,
    "lager": 1.4,
}

MATERIAL_GROUP_RULES = [
    (
        [
            "beton",
            "concrete",
            "stahlbeton",
            "fundament",
            "ortbeton",
            "sichtbeton",
            "fertigteil",
        ],
        "Beton",
    ),
    (
        [
            "holz",
            "wood",
            "nadelholz",
            "laubholz",
            "fichte",
            "tanne",
            "buche",
            "eiche",
            "lärche",
        ],
        "Holz",
    ),
    (
        [
            "stahl",
            "steel",
            "eisen",
            "metall",
            "metal",
            "aluminium",
            "alu",
            "kupfer",
            "zink",
            "blech",
            "träger",
        ],
        "Metall",
    ),
    (
        [
            "dämmung",
            "dämm",
            "isolation",
            "mineralwolle",
            "steinwolle",
            "glaswolle",
            "eps",
            "pur",
            "pir",
            "styropor",
            "wärmedämm",
        ],
        "Dämmung",
    ),
    (["glas", "glass", "verglasung", "isolierglas", "esg", "vsg"], "Glas"),
]

MATERIAL_GROUP_COLORS = {
    "Holz": "#D35400",  # Warmes Rost-Orange (Dunkel)
    "Beton": "#E67E22",  # Leuchtendes Orange
    "Metall": "#F39C12",  # Edles Amber-Orange
    "Dämmung": "#F5B041",  # Weiches Sonnen-Orange
    "Glas": "#F8C471",  # Helles Pfirsich-Orange
    "Andere": "#BDC3C7",  # Neutrales Hellgrau
}

HOLZ_TRIGGERS = [
    "vollholz",
    "holzwerkstoff",
    "holz balken",
    "holzbalken",
    "holz fassade",
    "holzfassade",
    "fassade holz",
    "holz",
    "wood",
    "nadelholz",
    "laubholz",
    "fichte",
    "tanne",
    "buche",
    "eiche",
    "lärche",
    "föhre",
]

RAUM_GRUPPEN = {
    "Veloraum": ("Lager/Technik", "#E07B39"),
    "Abstellkamer": ("Lager/Technik", "#E07B39"),
    "Abstellraum": ("Lager/Technik", "#E07B39"),
    "Technik": ("Lager/Technik", "#E07B39"),
    "Saal": ("Aufenthalt", "#2E86AB"),
    "Restaurant": ("Aufenthalt", "#2E86AB"),
    "Bar/Empfang": ("Aufenthalt", "#2E86AB"),
    "Warteraum": ("Aufenthalt", "#2E86AB"),
    "Backstage": ("Aufenthalt", "#2E86AB"),
    "WC": ("Sanitär", "#7B5EA7"),
    "WC Damen": ("Sanitär", "#7B5EA7"),
    "WC Herren": ("Sanitär", "#7B5EA7"),
    "Treppenhaus": ("Verkehr", "#5C8A6E"),
    "Vorraum": ("Verkehr", "#5C8A6E"),
}
