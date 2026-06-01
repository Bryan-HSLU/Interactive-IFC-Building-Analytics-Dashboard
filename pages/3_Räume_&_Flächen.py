import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_room_co2_scatter, create_room_co2_density_bar
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
    st.title("🏠 Räume & Flächen")
    st.info("Dieses Modell enthält keine Räume (IfcSpace) für eine Detailauswertung.")
    st.stop()

st.title("🏠 Räume & Flächen")
st.caption("📐 Ausreisser-Erkennung und quantitative Detailanalyse der Räume.")

with st.expander("ℹ️ Was zeigt diese Seite?", expanded=False):
    st.markdown("""
    Diese Seite analysiert die **Räume und Flächen** des Gebäudes auf Basis der IfcSpace-Elemente:
    - **Ausreisser-Erkennung**: Scatter Plot (Fläche vs. CO₂-Last) zeigt Räume mit ungewöhnlich hoher CO₂-Intensität.
    - **CO₂-Dichte pro Raum**: Ranking aller Räume nach kg\u00a0CO₂eq\u00a0/\u00a0m² — klickbar zur Detailansicht.
    - **Raum-Tabelle**: Suchbare Übersicht mit Fläche, Volumen, Hauptmaterial und farbcodierter CO₂-Last.

    **IfcSpace** = Raumobjekt im IFC-Modell (wird von ArchiCAD/Revit exportiert, wenn Räume modelliert sind).
    Die CO₂-Last pro Raum ergibt sich aus den angrenzenden Bauteilen und deren KBOB-Faktoren.
    """)

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

if "selected_raum" not in st.session_state:
    st.session_state["selected_raum"] = None

# ── Scatter Plot & CO₂-Dichte Chart ──────────────────────────────────────────

st.subheader("🔍 Ausreisser-Erkennung (Fläche vs. CO₂-Last)")
st.caption(
    "📈 Punkte weit über der Trendlinie zeigen Räume mit überdurchschnittlich hoher CO₂-Intensität."
)

selected_raum = st.session_state.get("selected_raum")
if selected_raum:
    st.info(f"📌 Ausgewählter Raum: **{selected_raum}** (im Scatter Plot hervorgehoben, andere halbtransparent)")
    if st.button("✕ Raumauswahl aufheben", key="reset_selected_raum_btn", use_container_width=True):
        st.session_state["selected_raum"] = None
        st.rerun()

fig_scatter = create_room_co2_scatter(space_df, selected_raum)
st.plotly_chart(fig_scatter, use_container_width=True, key="p3_scatter")

st.divider()

st.subheader("🌡️ CO₂-Intensität pro Raum (kg CO₂eq / m²)")
st.caption("🖱️ Klicken Sie auf einen Balken, um diesen Raum im Scatter Plot hervorzuheben.")

fig_density = create_room_co2_density_bar(space_df, selected_raum)
event_density = st.plotly_chart(
    fig_density,
    use_container_width=True,
    on_select="rerun",
    key="room_density_chart"
)

# Klick-Interaktion auswerten
if event_density and hasattr(event_density, "selection") and event_density.selection:
    points = event_density.selection.get("points", [])
    if points:
        clicked_room = points[0].get("y")
        if clicked_room:
            if selected_raum == clicked_room:
                st.session_state["selected_raum"] = None
                st.rerun()
            else:
                st.session_state["selected_raum"] = clicked_room
                st.rerun()

# ── Details Table with Heatmapped CO2 Column ──────────────────────────────────

st.divider()
st.subheader("📋 Raum-Details & Kennzahlen")
st.caption("🔎 Details on demand: Suchbare Tabelle mit farbcodierter CO₂-Dichte.")


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
    "🔎 Suche (Raumname)", key="search_rooms", placeholder="z.B. Büro, Flur..."
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
            if pct < 0.5:
                t = pct / 0.5
                r = int(255 + t * (252 - 255))
                g = int(243 + t * (163 - 243))
                b = int(176 + t * (17 - 176))
            else:
                t = (pct - 0.5) / 0.5
                r = int(252 + t * (214 - 252))
                g = int(163 + t * (40 - 163))
                b = int(17 + t * (40 - 17))
            return f"background-color: rgb({r},{g},{b}); color: #2D2D2D; font-weight: bold;"
        except Exception:
            return ""

    st.caption(f"🏠 {len(display_df):,} Räume angezeigt")
    st.dataframe(
        display_df.style.map(_style_co2, subset=["CO₂-Last (kg)"]),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Keine Detaildaten für die Suche vorhanden.")
