# IFC Building Analytics Dashboard

An interactive Streamlit dashboard for architects and BIM managers to analyse IFC building models — supporting both new construction (Neubau) and renovation (Umbau/Sanierung) workflows.

> **Course project** — Data Visualization for AI and ML (I.BA_DVIZ_MM.F2601)  
> HSLU · Spring 2026 · Dr. Teresa Kubacka

---

## Features

| Page | Description | Interactivity |
|---|---|---|
| **1 · Upload** | Load IFC file, select Neubau or Umbau mode | Mode toggle, project info display |
| **2 · Overview** | KPI cards (elements, storeys, IFC classes, quality), treemap, status & volume donuts, SIA-416 legend | Treemap → cross-filter Rooms & Areas page |
| **3 · Rooms & Areas** | SIA-416 area distribution, room areas with slider, rooms per storey (SIA colors), avg room height, room table | Room count slider, search filter |
| **4 · Components & Quantities** | Material volume (grouped / individual), stacked component bar, components per storey, volume heatmap, Sankey flow | Material view toggle, top-N sliders, click-to-filter |
| **5 · Environmental & Cost Analysis** | CO₂ drivers + intensity (KBOB), cost breakdown + per-m³ reference, grey energy per m² NRF + KBOB reference, renovation balance (Umbau), cost vs. CO₂ scatter | Global material view toggle (grouped / individual), tabs |
| **6 · Quality Check** | Quality score, error indicators (click-to-drill-down), errors per storey, Pset lollipop, attribute heatmap, material coverage (stacked bar) | Click error category → detail table |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Bryan-HSLU/Interactive-IFC-Building-Analytics-Dashboard.git
cd Interactive-IFC-Building-Analytics-Dashboard
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> Requires **Python 3.10 or higher**.

> ⚠️ `ifcopenshell` ships platform-specific binaries. If `pip install` fails, download the correct wheel for your OS and Python version from [ifcopenshell.org/python](https://ifcopenshell.org/python).

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Test Data

A sample IFC file is included in the `data/` folder for testing purposes.

**To get started:**
1. Open the app and navigate to **Page 1 · Upload**
2. Drag and drop the included sample IFC file (or any IFC file of your own)
3. Select a project mode — **New Build** or **Renovation**
4. Navigate through all pages using the sidebar

> The dashboard supports **IFC2x3** and **IFC4** files.  
> IFC4x3 is not currently supported.

---

## Project Structure

```
├── app.py                              # Streamlit entry point & page config
├── pages/
│   ├── 1_Upload.py                     # IFC upload, mode selection, metadata display
│   ├── 2_Overview.py                   # KPI tiles, treemap, status/volume donuts
│   ├── 3_Rooms_Areas.py               # SIA-416 area analysis, room slider, storey breakdown
│   ├── 4_Components_Quantities.py      # Material quantities, Sankey, heatmap
│   └── 5_Environmental_Cost_Analysis.py # CO₂, costs, grey energy, renovation balance
│   └── 6_Quality_Check.py             # Quality score, Pset coverage, structure checks
├── src/
│   ├── chart_factory.py               # All Plotly chart functions
│   ├── constants.py                   # Colors, SIA_COLORS, IFC labels, KBOB path, fixed costs
│   ├── filters.py                     # Sidebar filters + cross-filter reset UI
│   ├── ifc_parser.py                  # ifcopenshell parsing logic
│   ├── impact_calculator.py           # CO₂e, grey energy, cost (KBOB + fixed fallback costs)
│   ├── quality_checker.py             # Pset validation & error detection
│   ├── state_manager.py               # st.session_state management
│   └── ui_helpers.py                  # KPI card, scenario card, unit conversion helpers
├── data/
│   ├── sample_building.ifc            # Sample IFC file for testing
│   └── kbob_factors.csv               # KBOB emission & cost factors (Switzerland, 37 materials)
└── assets/
    └── style.css                      # Custom CSS styling
```

---

## SIA-416 Room Categories

Rooms (IfcSpace elements) are classified according to the Swiss SIA-416 standard:

| Category | Code | Color | Description |
|---|---|---|---|
| Hauptnutzfläche | **HNF** | 🔴 `#E3001B` | Primary use area (offices, living, dining) |
| Nebennutzfläche | **NNF** | 🟠 `#F7901E` | Secondary use area (storage, archives) |
| Verkehrsfläche | **VF** | 🟡 `#FFE600` | Circulation (corridors, stairs, lifts) |
| Funktionsfläche | **FF** | 🔵 `#00A0D2` | Functional/services (WC, HVAC, showers) |
| Konstruktionsfläche | **KF** | ⬜ `#9CA3AF` | Construction area (walls, columns) |

---

## KBOB Impact Factors

Environmental and cost data comes from the Swiss **KBOB** coordination body (Koordinationskonferenz der Bau- und Liegenschaftsorgane). The file `data/kbob_factors.csv` contains 37 material entries with:

- `co2e_kg_per_m3` — embodied carbon (kg CO₂e per m³)
- `grey_energy_kwh_per_m3` — primary energy demand (kWh per m³)
- `cost_chf_per_m3` — reference construction cost (CHF per m³)
- `density_kg_per_m3` — material density

**Fixed per-unit fallback costs** are applied for elements without material assignment:

| IFC Class | Fallback Cost |
|---|---|
| IfcDoor | CHF 1'800 per unit |
| IfcWindow | CHF 1'500 per unit |
| IfcStair / IfcStairFlight | CHF 6'000 per unit |

---

## Design Decisions

- **Official SIA-416 colors** — HNF/NNF/VF/FF/KF use the official Swiss standard palette, consistently applied across treemap, bar charts, and legends
- **Grouped / Individual material view** — All material charts support switching between 6 semantic groups (Concrete, Wood, Metal, Insulation, Glass, Other) and individual raw material strings from the IFC model
- **Cross-filtering** — Clicking charts on Overview sets filters for Rooms & Areas; clicking materials on Components sets filters downstream; all filters show a reset button
- **Colorblind-safe palette** — No red/green pairs in quality indicators; `missing_material` uses purple (`#7B5EA7`), distinct from orange and red used for other error types
- **KBOB reference charts** — Vertical bar charts in each environmental tab show material intensity per m³ for direct comparison with building-level results; linked to the global material view toggle
- **Two project modes** — Neubau and Umbau propagate throughout the app; renovation-specific charts (status donut, waterfall, diverging bar, circularity) only render when Umbau mode is active

---

## AI Tool Usage

This project was developed with AI assistance in compliance with HSLU guidelines.  
All prompts used are documented and submitted separately as required.

---

## Live Demo

🌐 [interactive-ifc-building-analytics-dashboard.streamlit.app](https://interactive-ifc-building-analytics-dashboard.streamlit.app)

---

## Authors

- Bryan Wiederkehr ([@Bryan-HSLU](https://github.com/Bryan-HSLU))
- Genc Haxhija ([@GencHaxhija](https://github.com/GencHaxhija))

HSLU — Hochschule Luzern · I.BA_DVIZ_MM.F2601 · Spring 2026
