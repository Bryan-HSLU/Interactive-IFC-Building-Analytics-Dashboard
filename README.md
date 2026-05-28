# IFC Building Analytics Dashboard

An interactive Streamlit dashboard for architects and BIM managers to analyze IFC building models — supporting both new construction (Neubau) and renovation (Umbau/Sanierung) workflows.

> **Course project** — Data Visualization for AI and ML (I.BA_DVIZ_MM.F2601)  
> HSLU · Spring 2026 · Dr. Teresa Kubacka

---

## Features

| Page | Description | Interactivity |
|---|---|---|
| **1 · Upload** | Load IFC file, select Neubau or Umbau mode, configure Psets | Mode toggle, Pset configurator |
| **2 · Overview** | KPI cards, CO₂ summary, treemap, storey sunburst, status donut | Sunburst → Bubble Chart cross-filter, global sidebar filters |
| **3 · Rooms & Areas** | ⚠️ Disabled — the project model contains no IfcSpace elements | — |
| **4 · Components & Quantities** | IFC class bar, storey stacked bar, material analysis, violin / histogram / raincloud | ✅ Cross-filtering between class and material charts |
| **5 · Impact & Costs** | CO₂e, grey energy, cost (CHF), circularity (Umbau only), SIA 2032 comparison | ✅ Cross-filtering CO₂ bar ↔ treemap |
| **6 · Quality Check** | Score gauge, traffic-light indicators, UpSet plot, Pset matrix heatmap | ✅ Cross-filtering by error category and IFC class |

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
3. Select a project mode — **Neubau** (new construction) or **Umbau** (renovation)
4. Navigate through all pages using the sidebar

> The dashboard supports **IFC2x3** and **IFC4** files.  
> IFC4x3 is not currently supported.

---

## Project Structure

```
├── app.py                    # Streamlit entry point & page config
├── pages/
│   ├── 1_Upload.py           # IFC upload, mode selection, metadata display
│   ├── 2_Overview.py         # KPI summary, sunburst, CO₂ treemap
│   ├── 3_Raeume_Flaechen.py  # Disabled (no IfcSpace in project model)
│   ├── 4_Bauteile_Mengen.py  # Element quantities & material analysis
│   ├── 5_Impact_Costs.py     # CO₂e, grey energy, cost, circularity
│   └── 6_Quality_Check.py    # Model quality score & error analysis
├── src/
│   ├── chart_factory.py      # All Plotly chart functions
│   ├── constants.py          # Colors, units, IFC class labels, KBOB path
│   ├── filters.py            # Sidebar filters + cross-filter reset UI
│   ├── ifc_parser.py         # ifcopenshell parsing logic
│   ├── impact_calculator.py  # CO₂e, grey energy, cost (KBOB factors)
│   ├── quality_checker.py    # Pset validation & error detection
│   └── state_manager.py      # st.session_state management
├── data/
│   ├── sample_building.ifc   # Sample IFC file for testing
│   └── kbob_factors.csv      # KBOB emission & cost factors (Switzerland)
└── assets/
    └── style.css             # Custom CSS styling
```

---

## Data Visualization Design Decisions

This project applies the following principles from the course:

- **Max 7 categories rule** — `_group_small_categories()` automatically merges small categories into "Sonstige" to avoid visual overload
- **Colorblind-safe palette** — No red/green pairs; status colors use teal (`#1A7F8E` Neubau), warm brown (`#A0522D` Abbruch), mid-grey (`#7F8C8D` Bestand) — consistently applied across all pages
- **Cross-filtering beyond hover** — Clicking any chart filters all other charts on the same page via `streamlit-plotly-events`; clicking the same element again toggles the filter off
- **Intentional chart types** — Sankey for material→class→CO₂ flow, Waterfall for cumulative contribution, UpSet plot for error co-occurrence patterns, Raincloud (violin + strip) for distribution + individual data points
- **Contextual annotation** — SIA 2032 limit line (11 kg CO₂e/m²·a) provides normative reference directly in the chart without requiring external lookup
- **Two project modes** — Neubau and Umbau/Sanierung propagated throughout the entire app; mode-specific charts (status donut, circularity tab, diverging bar) only rendered when relevant

---

## AI Tool Usage

This project was developed with AI assistance in compliance with HSLU guidelines.  
All prompts used are documented and submitted separately as required.

---

## Live Demo

🌐 [interactive-ifc-building-analytics-dashboard.streamlit.app](https://interactive-ifc-building-analytics-dashboard.streamlit.app)

---

## Authors

- Bryan Lüscher ([@Bryan-HSLU](https://github.com/Bryan-HSLU))
- Genc Haxhija ([@GencHaxhija](https://github.com/GencHaxhija))

HSLU — Hochschule Luzern · I.BA_DVIZ_MM.F2601 · Spring 2026
