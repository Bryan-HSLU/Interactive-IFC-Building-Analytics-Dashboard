import streamlit as st
import pandas as pd
from src.state_manager import init_session_state, get_element_df, get_space_df, get_quality_data
from src.filters import render_sidebar
from src.chart_factory import create_room_treemap, create_ifc_class_bar, create_status_donut
from src.constants import COLORS
from src.ui_helpers import hero_kpi_card

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
    st.warning("Bitte zuerst eine IFC-Datei auf **Seite\u00a01** hochladen.")
    st.stop()

element_df = get_element_df(filtered=True)
space_df = get_space_df(filtered=True)
has_spaces = space_df is not None and not space_df.empty
metadata = st.session_state.get("model_metadata", {})

st.title("🏠 Gebäude-Cockpit")

# Dynamic caption
if has_spaces and "area_m2" in space_df.columns and space_df["area_m2"].sum() > 0:
    total_a = space_df["area_m2"].sum()
    agg_u = space_df.groupby("usage")["area_m2"].sum()
    if not agg_u.empty:
        dominant_usage = agg_u.idxmax()
        pct = (agg_u.max() / total_a) * 100
        st.caption(f"{len(space_df)} Räume auf {total_a:,.0f} m² — **{dominant_usage}** belegt {pct:.0f}\u00a0% der NFA".replace(",", "'"))
    else:
        st.caption("Schneller Überblick über Modellstruktur, Bauteiltypen und räumliche Verteilung.")
else:
    st.caption("Schneller Überblick über Modellstruktur, Bauteiltypen und räumliche Verteilung.")

with st.expander("ℹ️ Was zeigt diese Seite?", expanded=False):
    st.markdown("""
    Das **Gebäude-Cockpit** gibt einen strukturierten Üblick über das IFC-Modell:
    - **Modell-Tab**: Welche Bauteiltypen (IFC-Klassen wie Wand, Decke, Fenster…) sind wie häufig vorhanden? Metadaten wie Projektname und Schema-Version.
    - **Status-Tab**: Wie verteilt sich das Gebäude auf Bestand, Neubau und Abbruch?
    - **Räumlich-Tab**: Welche Nutzungstypen belegen wie viel Fläche (NFA)?

    Klicken Sie in Charts, um andere Seiten zu filtern.
    """)

# ── KPI Row (Modell-Cockpit: Elemente, Geschosse, Klassen, Qualität) ──
n_elements = len(element_df) if element_df is not None else 0
n_storeys = element_df["storey"].nunique() if element_df is not None and "storey" in element_df.columns else 0
n_classes = element_df["ifc_class"].nunique() if element_df is not None and "ifc_class" in element_df.columns else 0
_, quality_summary = get_quality_data()
quality_score = quality_summary.get("score", 0) if quality_summary else 0.0

kcols = st.columns(4)
with kcols[0]:
    hero_kpi_card("ELEMENTE", f"{n_elements:,}".replace(",", "'"), "Bauteile")
with kcols[1]:
    hero_kpi_card("GESCHOSSE", str(n_storeys), "Ebenen")
with kcols[2]:
    hero_kpi_card("IFC-KLASSEN", str(n_classes), "Typen")
with kcols[3]:
    hero_kpi_card("QUALITÄT", f"{quality_score:.0f}", "%")

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──
tab_modell, tab_status, tab_raeumlich = st.tabs(["🏗️ Modell", "🔄 Status", "🗺️ Räumlich"])

# ── Tab: Modell ──
with tab_modell:
    col_chart, col_meta = st.columns([2, 1])
    with col_chart:
        st.subheader("IFC-Klassen-Verteilung")
        st.caption("Anzahl Bauteile je IFC-Klasse — zeigt, welche Elementtypen im Modell dominieren.")
        if element_df is not None and "ifc_class" in element_df.columns:
            st.plotly_chart(create_ifc_class_bar(element_df), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Keine IFC-Klassendaten verfügbar.")
    with col_meta:
        st.subheader("Modell-Metadaten")
        st.caption("Technische Grunddaten des geladenen IFC-Modells.")
        meta_items = [
            ("Projektname", metadata.get("project_name", "–")),
            ("IFC-Schema", metadata.get("schema", "–")),
            ("Autorensoftware", metadata.get("authoring_tool", "–")),
            ("Elemente gesamt", f"{metadata.get('element_count', n_elements):,}".replace(",", "'")),
            ("Geschosse", str(n_storeys)),
            ("IFC-Klassen", str(n_classes)),
        ]
        for label, value in meta_items:
            st.markdown(
                f"""
                <div style="display:flex; justify-content:space-between; padding:6px 0;
                            border-bottom:1px solid #E8EBEF; font-size:14px;">
                    <span style="color:#6B7280;">{label}</span>
                    <span style="font-weight:600; color:#2D2D2D;">{value}</span>
                </div>""",
                unsafe_allow_html=True,
            )

# ── Tab: Status ──
with tab_status:
    st.subheader("Phasen- & Statusverteilung")
    st.caption(
        "Anteil von Bestand, Neubau, Abbruch und Temporär am Gesamtmodell (nach Elementanzahl). "
        "Relevant für Projektmanagement und Bauherrschaft."
    )
    with st.expander("ℹ️ Was bedeuten die Status-Kategorien?", expanded=False):
        st.markdown("""
        - **Bestand**: Vorhandene Bauteile, die erhalten bleiben.
        - **Neubau**: Neu erstellte oder geplante Bauteile.
        - **Abbruch**: Bauteile, die rückgebaut werden.
        - **Temporär**: Baubehelfe oder zeitlich begrenzte Elemente.

        Im Neubau-Modus sind alle Elemente als „Neubau“ klassiert.
        """)
    if element_df is not None and "status" in element_df.columns:
        st.plotly_chart(create_status_donut(element_df), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Keine Statusdaten verfügbar — möglicherweise kein Umbau-Modus gewählt.")

# ── Tab: Räumlich ──
with tab_raeumlich:
    st.subheader("Räumliche Flächenverteilung (NFA)")
    st.caption(
        "Proportionen der Raumtypen nach Netto-Geschössfläche (NFA). "
        "Klicken Sie auf einen Typ, um andere Seiten zu filtern."
    )
    with st.expander("ℹ️ Was ist die NFA?", expanded=False):
        st.markdown("""
        Die **Netto-Geschössfläche (NFA)** ist die nutzbare Innenfläche aller Geschosse — ohne Wände,
        Konstruktion und Installationsflächen. Die Flächen stammen aus den IfcSpace-Elementen des Modells.
        """)
    if has_spaces:
        fig_tree = create_room_treemap(space_df)
        ev_tree = st.plotly_chart(fig_tree, on_select="rerun", key="ov_treemap", use_container_width=True)
        if ev_tree and ev_tree.selection and ev_tree.selection.points:
            pt = ev_tree.selection.points[0]
            clicked = pt.get("label") or pt.get("id") or ""
            if clicked:
                clicked_clean = clicked.replace("<b>", "").replace("</b>", "").strip()
                if clicked_clean in ("Gesamt", "root", "Total"):
                    if st.session_state.get("cf_page3_usage") != "Gesamt":
                        st.session_state.cf_page3_usage = "Gesamt"
                        st.rerun()
                else:
                    if clicked_clean != st.session_state.get("cf_page3_usage"):
                        st.session_state.cf_page3_usage = clicked_clean
                        st.rerun()
    else:
        st.info("Dieses Modell enthält keine Räume (IfcSpace) für eine Treemap-Flächenverteilung.")
