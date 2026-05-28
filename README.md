# IFC Building Analytics Dashboard

An interactive Streamlit dashboard for MEP planners and BIM coordinators to analyze IFC building models — supporting both new construction (Neubau) and renovation (Umbau/Sanierung) workflows.

> **Course project** — Data Visualization for AI and ML (I.BA_DVIZ_MM.F2601)  
> HSLU · Spring 2026 · Dr. Teresa Kubacka

---

## Live Demo

🌐 [interactive-ifc-building-analytics-dashboard.streamlit.app](https://interactive-ifc-building-analytics-dashboard.streamlit.app)

---

## Features

| Page | Description | Interactivity |
|---|---|---|
| **1 · Upload** | Load IFC file, select Neubau or Umbau mode, configure Psets | Mode toggle, Pset configurator |
| **2 · Overview** | KPI cards, class distribution, CO₂ summary, treemap | Global sidebar filters |
| **3 · Rooms & Areas** | Box plot, stacked bar, histogram, scatter by usage type | ✅ Cross-filtering between all charts |
| **4 · Components & Quantities** | IFC class bar, storey breakdown, material analysis, raincloud | ✅ Cross-filtering between all charts |
| **5 · Impact & Costs** | CO₂e, grey energy, cost (CHF), circularity (Umbau), SIA 2032 | ✅ Cross-filtering + SIA 2032 limit line |
| **6 · Quality Check** | Score gauge, error analysis, UpSet plot, Pset matrix heatmap | ✅ Cross-filtering by error category |

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

> Requires **Python 3.10+**

### 4. Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Test Data

A sample IFC file is included for testing:

```
data/sample_building.ifc
```

1. Open the app and go to **Page 1 · Upload**
2. Upload `data/sample_building.ifc`
3. Select project mode (**Neubau** or **Umbau**)
4. Navigate through all pages using the sidebar

> The dashboard supports **IFC2x3** and **IFC4** files. IFC4x3 is not yet supported.

---

## Project Structure

```
├── app.py                    # Streamlit entry point
├── pages/
│   ├── 1_Upload.py
│   ├── 2_Overview.py
│   ├── 3_Raeume_Flaechen.py
│   ├── 4_Bauteile_Mengen.py
│   ├── 5_Impact_Costs.py
│   └── 6_Quality_Check.py
├── src/
│   ├── chart_factory.py      # All Plotly chart functions
│   ├── constants.py          # Colors, units, IFC labels
│   ├── filters.py            # Sidebar + cross-filter UI
│   ├── ifc_parser.py         # ifcopenshell parsing logic
│   ├── impact_calculator.py  # CO₂e, grey energy, cost (KBOB)
│   ├── quality_checker.py    # Pset validation & error detection
│   └── state_manager.py      # st.session_state management
├── data/
│   ├── sample_building.ifc   # Sample IFC file for testing
│   └── kbob_factors.csv      # KBOB emission & cost factors
└── assets/
    └── style.css
```

---

## Data Visualization Design Decisions

This project applies the following principles from the course:

- **Max 7 categories rule** — `_group_small_categories()` automatically groups small categories into "Sonstige" to avoid visual overload
- **Accessibility colors** — No red/green color pairs; errors use orange (`#E67E22`) vs. blue (`#2980B9`) to be colorblind-safe
- **Cross-filtering** — Clicking on any chart filters all other charts on the page via `streamlit-plotly-events`, going beyond standard hover interaction
- **Intentional chart types** — Sankey diagram for material→class→CO₂ flow, Waterfall for cumulative contribution, UpSet plot for error co-occurrence, Raincloud for distribution + raw data combined
- **Contextual annotations** — SIA 2032 reference line (11 kg CO₂e/m²·a) on impact charts gives direct normative context without requiring external lookup
- **Consistent color encoding** — `Neubau=#2980B9`, `Abbruch=#E67E22`, `Bestand=#95A5A6`, `Temporär=#8E44AD` used consistently across all pages

---

## AI Tool Usage

This project was developed with AI assistance in compliance with HSLU guidelines.  
All prompts used are documented and submitted separately on ILIAS as required.

---

## Authors

- Bryan Lüscher ([@Bryan-HSLU](https://github.com/Bryan-HSLU))
- Genc Haxhija ([@GencHaxhija](https://github.com/GencHaxhija))

HSLU — Hochschule Luzern · I.BA_DVIZ_MM.F2601 · Spring 2026
