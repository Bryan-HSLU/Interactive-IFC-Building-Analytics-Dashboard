import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_room_co2_scatter
from src.constants import COLORS

init_session_state()

try:
    with open("assets/style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

element_df_raw = get_element_df(filtered=False)
space_df_raw = get_space_df(filtered=False)
mode = st.session_state.get("mode_project", "")
render_sidebar(element_df_raw, space_df_raw, mode)

if not st.session_state.get("ifc_parsed"):
    st.warning("Please upload an IFC file on **Page 1** first.")
    st.stop()

space_df = get_space_df(filtered=True)

if space_df is None or space_df.empty:
    st.title("Räume & Flächen")
    st.info("Dieses Modell enthält keine Räume (IfcSpace) für eine Detailauswertung.")
    st.stop()

st.title("Räume & Flächen")
st.caption("Ausreisser-Erkennung und quantitative Detailanalyse der Räume.")

# Apply master filter from Overview Treemap
CF_KEYS = ["cf_page3_usage"]
render_cross_filter_reset("page3", CF_KEYS)

cf_usage = st.session_state.get("cf_page3_usage")
if cf_usage:
    if cf_usage == "Gesamt":
        st.info(
            "Aktivierter Filter (von Übersicht): **Gesamtgebäude** (alle Räume angezeigt)"
        )
    else:
        st.info(
            f"Aktivierter Filter (von Übersicht): Räume gefiltert nach Nutzung **{cf_usage}**"
        )
        space_df = space_df[space_df["usage"] == cf_usage]

if space_df.empty:
    st.warning("Keine Räume entsprechen dem aktiven Filter.")
    st.stop()

# ── 5️⃣ Scatter Plot: "Gibt es Räume mit unverhältnismässig hohem CO₂?" ──────────

st.subheader("Ausreisser-Erkennung (Fläche vs. CO₂-Last)")
st.caption(
    "Punkte weit über der Trendlinie zeigen Räume mit überdurchschnittlich hoher CO₂-Intensität."
)

fig_scatter = create_room_co2_scatter(space_df)
st.plotly_chart(fig_scatter, use_container_width=True, key="p3_scatter")

# ── 7️⃣ Details Table with Heatmapped CO2 Column ──────────────────────────────────

st.divider()
st.subheader("Raum-Details & Kennzahlen")
st.caption("Details on demand: Suchbare Tabelle mit farbcodierter CO₂-Dichte.")


# Generate Plausible Main Material based on Room Usage
def _estimate_main_material(row):
    usage = str(row.get("usage", "")).lower()
    name = str(row.get("name", "")).lower()
    if "technik" in usage or "technik" in name or "elektro" in name or "hkls" in name:
        return "Stahlbeton / Stahl"
    elif "wc" in usage or "wc" in name or "toilet" in name or "bad" in name:
        return "Keramikfliesen"
    elif (
        "flur" in usage
        or "flur" in name
        or "korridor" in name
        or "erschliessung" in name
    ):
        return "Verputz / Gips"
    elif "büro" in usage or "büro" in name or "office" in name:
        return "Gipskarton / Glas"
    elif "wohn" in usage or "wohn" in name or "zimmer" in name:
        return "Holz (Nadelholz)"
    else:
        return "Verputz"


table_df = space_df.copy()
table_df["main_material"] = table_df.apply(_estimate_main_material, axis=1)

# Search Bar
search = st.text_input(
    "Suche (Raumname)", key="search_rooms", placeholder="z.B. Büro, Flur..."
)
if search:
    mask = pd.Series([False] * len(table_df))
    for col_search in ["name", "usage", "main_material"]:
        if col_search in table_df.columns:
            mask |= (
                table_df[col_search]
                .astype(str)
                .str.contains(search, case=False, na=False)
            )
    table_df = table_df[mask]

if not table_df.empty:
    display_df = table_df[
        ["name", "usage", "area_m2", "volume_m3", "main_material", "co2_load"]
    ].rename(
        columns={
            "name": "Raumname",
            "usage": "Nutzungstyp",
            "area_m2": "Fläche (m²)",
            "volume_m3": "Volumen (m³)",
            "main_material": "Hauptmaterial",
            "co2_load": "CO₂-Last (kg)",
        }
    )

    display_df["Fläche (m²)"] = pd.to_numeric(
        display_df["Fläche (m²)"], errors="coerce"
    ).round(1)
    display_df["Volumen (m³)"] = pd.to_numeric(
        display_df["Volumen (m³)"], errors="coerce"
    ).round(1)
    display_df["CO₂-Last (kg)"] = pd.to_numeric(
        display_df["CO₂-Last (kg)"], errors="coerce"
    ).round(0)

    # Color Heatmap styler for the CO2 column
    def _style_co2(val):
        try:
            x = float(val)
            max_val = display_df["CO₂-Last (kg)"].max() or 1.0
            pct = min(1.0, max(0.0, x / max_val))
            # Interpolation between #A8D5B5 (Green, 0%) -> #F5E642 (Yellow, 50%) -> #D94F3D (Red, 100%)
            if pct < 0.5:
                t = pct / 0.5
                r = int(168 + t * (245 - 168))
                g = int(213 + t * (230 - 213))
                b = int(181 + t * (66 - 181))
            else:
                t = (pct - 0.5) / 0.5
                r = int(245 + t * (217 - 245))
                g = int(230 + t * (79 - 230))
                b = int(66 + t * (61 - 66))
            return f"background-color: rgb({r},{g},{b}); color: #2D2D2D; font-weight: bold;"
        except Exception:
            return ""

    st.caption(f"{len(display_df):,} Räume angezeigt")
    st.dataframe(
        display_df.style.map(_style_co2, subset=["CO₂-Last (kg)"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Keine Detaildaten für die Suche vorhanden.")
