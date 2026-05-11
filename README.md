# IFC Building Analytics Dashboard

Interactive Streamlit dashboard for MEP planners and BIM coordinators to analyze IFC building models.

## Features

- **Upload & Mode Selection** — Load IFC files, choose Neubau or Umbau mode
- **3D Model Explorer** — Interactive 3D viewer with color modes
- **Rooms & Areas** — Room structure and floor area analysis
- **Components & Quantities** — IFC class analysis and quantity takeoff
- **Impact & Costs** — CO2e, grey energy, and cost calculations
- **Quality Check** — Model data quality assessment

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Requirements

- Python 3.10+
- An IFC file (IFC2x3 or IFC4) for analysis

## Project Structure

See `CLAUDE.md` for detailed architecture documentation.
