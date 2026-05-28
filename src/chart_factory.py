import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import re
from src.constants import COLORS, STATUS_COLORS, ROOM_COLORS, MATERIAL_COLORS, CO2_SCALE


def apply_default_layout(fig: go.Figure, title: str = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        title=dict(
            text=title,
            font=dict(size=14, color=COLORS["text"]),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=50, r=20, t=50 if title else 20, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
    )
    fig.update_xaxes(gridcolor=COLORS["grid"], gridwidth=1, tickfont=dict(size=11, color=COLORS["text_light"]))
    fig.update_yaxes(gridcolor=COLORS["grid"], gridwidth=1, tickfont=dict(size=11, color=COLORS["text_light"]))
    return fig


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color=COLORS["text_light"]),
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20),
    )
    return fig


# ── 1️⃣ Helper to resolve consistent Room Colors ─────────────────────────────────

def _get_room_color(usage: str) -> str:
    usage_lower = str(usage).lower().strip()
    for key, color in ROOM_COLORS.items():
        if key.lower() in usage_lower:
            return color
    return ROOM_COLORS["Andere"]


# ── 2️⃣ Treemap: "Welcher Raumtyp nimmt wie viel Fläche ein?" ──────────────────

def create_room_treemap(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten für Treemap verfügbar")

    df = space_df.copy()
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce").fillna(0)
    df = df[df["area_m2"] > 0]

    if df.empty:
        return _empty_fig("Keine positiven Raumflächen")

    # Group by room type (usage)
    agg = df.groupby("usage")["area_m2"].sum().reset_index()
    agg = agg.sort_values("area_m2", ascending=False)

    # Max 6 room types, rest goes to 'Andere'
    if len(agg) > 5:
        top = agg.head(5)
        rest_val = agg.iloc[5:]["area_m2"].sum()
        rest_row = pd.DataFrame([{"usage": "Andere", "area_m2": rest_val}])
        agg = pd.concat([top, rest_row], ignore_index=True)

    labels = ["Gesamt"]
    parents = [""]
    values = [agg["area_m2"].sum()]
    colors = ["#F5F5F5"]

    for _, row in agg.iterrows():
        labels.append(row["usage"])
        parents.append("Gesamt")
        values.append(row["area_m2"])
        colors.append(_get_room_color(row["usage"]))

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>Fläche: %{value:.1f} m²<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(colors=colors, colorscale=None),
    ))
    apply_default_layout(fig, "Raumfläche nach Nutzungstyp (NFA)")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


# ── 3️⃣ Horizontal Bar Chart: "Welche Materialien sind verbaut?" ────────────────

def create_material_volume_bar(element_df: pd.DataFrame, unit: str = "m³") -> go.Figure:
    if element_df.empty:
        return _empty_fig("Keine Elementdaten verfügbar")

    col = "volume_m3" if unit in ("m³", "m\u00b3") else "area_m2"
    df = element_df.dropna(subset=[col]).copy()
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df[col] > 0]

    if df.empty:
        return _empty_fig("Keine Mengendaten verfügbar")

    agg = df.groupby("material")[col].sum().reset_index()
    agg.columns = ["material", "quantity"]
    agg = agg.sort_values("quantity", ascending=True)

    # Use single accent color #2E86AB (Stahlblau)
    colors = [COLORS["primary"]] * len(agg)

    fig = go.Figure(go.Bar(
        x=agg["quantity"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:,.1f}" for v in agg["quantity"]],
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>Menge: %{{x:.1f}} {unit}<extra></extra>",
    ))
    apply_default_layout(fig, f"Materialmengen im Gebäude ({unit})")
    fig.update_layout(xaxis_title=unit, yaxis_title="")
    return fig


# ── 4️⃣ Horizontal Bar Chart: "Welches Material verursacht am meisten CO2?" ─────

def create_material_co2_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO₂-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]

    if df.empty:
        return _empty_fig("Keine CO₂-Werte vorhanden")

    agg = df.groupby("material")["co2e_total"].sum().reset_index()
    agg.columns = ["material", "co2"]
    agg = agg.sort_values("co2", ascending=True)

    avg_val = agg["co2"].mean()

    # Sequential scale from low (Green) -> mid (Yellow) -> high (Red)
    # Map each value to a color based on its position in the values range
    vals = agg["co2"].tolist()
    min_v, max_v = min(vals), max(vals)
    span = (max_v - min_v) if max_v != min_v else 1.0

    colors = []
    for v in vals:
        # Scale value from 0 to 1
        scaled = (v - min_v) / span
        # Simple interpolation between low (#A8D5B5) -> mid (#F5E642) -> high (#D94F3D)
        if scaled < 0.5:
            # Interpolate low to mid
            t = scaled / 0.5
            r = int(168 + t * (245 - 168))
            g = int(213 + t * (230 - 213))
            b = int(181 + t * (66 - 181))
        else:
            # Interpolate mid to high
            t = (scaled - 0.5) / 0.5
            r = int(245 + t * (217 - 245))
            g = int(230 + t * (79 - 230))
            b = int(66 + t * (61 - 66))
        colors.append(f"rgb({r},{g},{b})")

    fig = go.Figure(go.Bar(
        x=agg["co2"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:,.0f} kg" for v in agg["co2"]],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>CO₂e-Last: %{x:,.0f} kg<extra></extra>",
    ))

    # Add Reference Line at the average
    fig.add_vline(
        x=avg_val,
        line_dash="dash",
        line_color=COLORS["text_light"],
        line_width=1.5,
        annotation_text="⌀ Durchschnitt",
        annotation_position="top right",
        annotation_font=dict(size=11, color=COLORS["text_light"]),
    )

    apply_default_layout(fig, "CO₂-Fussabdruck nach Materialgruppe")
    fig.update_layout(xaxis_title="kg CO₂eq", yaxis_title="")
    return fig


# ── 5️⃣ Scatter Plot: "Gibt es Räume mit unverhältnismässig hohem CO2?" ──────────

def create_room_co2_scatter(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns or "co2_load" not in space_df.columns:
        return _empty_fig("Keine ausreichenden Raumdaten für Scatter Plot verfügbar")

    df = space_df.dropna(subset=["area_m2", "co2_load"]).copy()
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["co2_load"] = pd.to_numeric(df["co2_load"], errors="coerce")
    df = df[(df["area_m2"] > 0) & (df["co2_load"] >= 0)]

    if df.empty:
        return _empty_fig("Keine quantitativen Werte für Scatter Plot")

    usages = sorted(df["usage"].unique(), key=lambda x: (x in ("Andere", "Unbekannt", "Sonstige"), x))
    fig = go.Figure()

    # Track data to calculate regression line
    all_x = df["area_m2"].tolist()
    all_y = df["co2_load"].tolist()

    # Scatter points by room type with consistent colors
    for usage in usages:
        sub = df[df["usage"] == usage]
        color = _get_room_color(usage)
        names = sub["name"].astype(str).tolist() if "name" in sub.columns else ["Raum"] * len(sub)
        fig.add_trace(go.Scatter(
            x=sub["area_m2"], y=sub["co2_load"],
            mode="markers", name=usage,
            marker=dict(color=color, size=9, opacity=0.85, line=dict(width=0.5, color="white")),
            text=names,
            hovertemplate="<b>%{text}</b><br>Nutzung: " + usage + "<br>Fläche: %{x:.1f} m²<br>CO₂-Last: %{y:,.0f} kg<extra></extra>",
        ))

    # Add Regression/Trend Line
    if len(all_x) > 1:
        try:
            m, c = np.polyfit(all_x, all_y, 1)
            x_range = np.linspace(min(all_x), max(all_x), 100)
            y_range = m * x_range + c
            fig.add_trace(go.Scatter(
                x=x_range, y=y_range,
                mode="lines", name="Trendlinie",
                line=dict(color=COLORS["text_light"], width=1.5, dash="dot"),
                hoverinfo="skip"
            ))
        except Exception:
            pass

    apply_default_layout(fig, "Raumfläche vs. CO₂-Last")
    fig.update_layout(xaxis_title="Raumfläche (m²)", yaxis_title="CO₂-Last (kg CO₂eq)")
    return fig


# ── 6️⃣ Stacked Bar Chart 100%: "Bauteil-Material-Verteilung" ──────────────────

# Semantic material groups with fixed colors
_MATERIAL_GROUP_RULES = [
    # (list of substrings to match, group name)
    (["beton", "concrete", "stahlbeton", "fundament", "ortbeton", "sichtbeton", "fertigteil"], "Beton"),
    (["holz", "wood", "nadelholz", "laubholz", "fichte", "tanne", "buche", "eiche", "lärche"], "Holz"),
    (["stahl", "steel", "eisen", "metall", "metal", "aluminium", "alu", "kupfer", "zink", "blech", "träger"], "Metall"),
    (["dämmung", "dämm", "isolation", "mineralwolle", "steinwolle", "glaswolle", "eps", "pur", "pir", "styropor", "wärmedämm"], "Dämmung"),
    (["glas", "glass", "verglasung", "isolierglas", "esg", "vsg"], "Glas"),
]

_MATERIAL_GROUP_COLORS = {
    "Beton":   "#909497",  # Grau
    "Holz":    "#8E6F54",  # Braun
    "Metall":  "#616A6B",  # Blaugrau/Slate
    "Dämmung": "#F4D03F",  # Gelb
    "Glas":    "#A9CCE3",  # Hellblau
    "Andere":  "#BDC3C7",  # Hellgrau
}

def _classify_material_group(material_name: str) -> str:
    """Classify a raw material name into one of 6 semantic groups."""
    name = str(material_name).lower().strip()
    for triggers, group in _MATERIAL_GROUP_RULES:
        for t in triggers:
            if t in name:
                return group
    return "Andere"


def create_element_material_stacked_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "ifc_class" not in element_df.columns or "material" not in element_df.columns:
        return _empty_fig("Keine Elementdaten für Bauteilverteilung verfügbar")

    df = element_df.copy()

    # Map IFC classes to standard German building parts
    def _map_class_to_part(cls):
        if cls in ("IfcWall", "IfcWallStandardCase", "IfcCurtainWall"):
            return "Wand"
        elif cls == "IfcRoof":
            return "Decke"
        elif cls == "IfcSlab":
            return "Boden"
        elif cls == "IfcWindow":
            return "Fenster"
        elif cls == "IfcDoor":
            return "Tür"
        else:
            return "Sonstige"

    df["part"] = df["ifc_class"].apply(_map_class_to_part)
    df = df[df["part"] != "Sonstige"]

    if df.empty:
        return _empty_fig("Keine Wände, Böden, Decken oder Öffnungen vorhanden")

    # Classify raw materials into semantic groups
    df["mat_group"] = df["material"].apply(_classify_material_group)

    # Group and calculate percentages
    pivot = df.pivot_table(index="part", columns="mat_group", aggfunc="size", fill_value=0)
    if pivot.empty:
        return _empty_fig("Keine Zuordnung möglich")

    # Drop building parts (rows) with zero total elements
    pivot = pivot.loc[pivot.sum(axis=1) > 0]
    if pivot.empty:
        return _empty_fig("Keine Bauteilgruppen mit Daten")

    # Drop "Fenster" and "Tür" if they are "leer" (i.e., they only have "Andere" material or no known materials)
    for part in ["Fenster", "Tür"]:
        if part in pivot.index:
            known_sum = pivot.loc[part, [c for c in pivot.columns if c != "Andere"]].sum()
            if known_sum == 0:
                pivot = pivot.drop(index=part)

    if pivot.empty:
        return _empty_fig("Keine Bauteilgruppen mit ausreichenden Materialdaten")

    # Normalize to 100%
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    # Consistent order of parts on X-Axis, only those with data
    part_order = ["Wand", "Boden", "Decke", "Fenster", "Tür"]
    pivot_pct = pivot_pct.reindex([p for p in part_order if p in pivot_pct.index])

    # Consistent order of material groups in legend
    group_order = ["Beton", "Holz", "Metall", "Dämmung", "Glas", "Andere"]
    ordered_groups = [g for g in group_order if g in pivot_pct.columns]

    fig = go.Figure()
    for grp in ordered_groups:
        color = _MATERIAL_GROUP_COLORS[grp]
        fig.add_trace(go.Bar(
            x=pivot_pct.index,
            y=pivot_pct[grp],
            name=grp,
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{grp}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Materialverteilung nach Bauteilgruppe")
    fig.update_layout(
        xaxis_title="", yaxis_title="Materialanteil (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
    )
    return fig


# ── Page 6 Quality Charts ──────────────────────────────────────────────────────

def create_quality_gauge(score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": COLORS["primary"]},
            "steps": [
                {"range": [0, 50], "color": "#FADBD8"},
                {"range": [50, 80], "color": "#FDEBD0"},
                {"range": [80, 100], "color": "#D5F5E3"},
            ],
            "threshold": {
                "line": {"color": COLORS["error_warning"], "width": 4},
                "thickness": 0.75,
                "value": score,
            },
        },
        title={"text": "Modellqualität", "font": {"size": 16, "weight": "bold"}},
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        height=280,
    )
    return fig


def create_error_bar(error_counts: dict) -> go.Figure:
    labels = {
        "missing_material": "Kein Material",
        "missing_quantity": "Keine Mengen",
        "missing_storey": "Kein Geschoss",
        "missing_usage": "Keine Nutzung",
        "missing_status": "Kein Status",
    }
    cats = [labels[k] for k in labels if k in error_counts]
    vals = [error_counts.get(k, 0) for k in labels if k in error_counts]

    colors = []
    for v in vals:
        if v == 0:
            colors.append(COLORS["error_ok"])
        elif v <= 10:
            colors.append(COLORS["error_warning"])
        else:
            colors.append(COLORS["error_critical"])

    fig = go.Figure(go.Bar(
        x=cats,
        y=vals,
        marker_color=colors,
        text=vals,
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Anzahl: %{y}<extra></extra>",
    ))
    apply_default_layout(fig, "Fehler nach Kategorie")
    fig.update_layout(xaxis_title="Fehlertyp", yaxis_title="Anzahl", showlegend=False)
    return fig


def create_pset_matrix_heatmap(pset_matrix: pd.DataFrame) -> go.Figure:
    if pset_matrix is None or pset_matrix.empty:
        return _empty_fig("Keine Pset-Daten verfügbar")

    z = (pset_matrix > 0).astype(int).values

    fig = go.Figure(go.Heatmap(
        z=z,
        x=pset_matrix.columns.tolist(),
        y=pset_matrix.index.tolist(),
        colorscale=[[0, "#E5E7E9"], [1, "#2E86C1"]],
        showscale=False,
        hovertemplate="Klasse: %{y}<br>Pset: %{x}<br>%{text}<extra></extra>",
        text=[["Vorhanden" if v else "Fehlt" for v in row] for row in z],
    ))
    apply_default_layout(fig, "Pset-Verfügbarkeit nach IFC-Klasse")
    fig.update_layout(xaxis_title="Property Set", yaxis_title="IFC-Klasse")
    fig.update_xaxes(tickangle=45)
    return fig
