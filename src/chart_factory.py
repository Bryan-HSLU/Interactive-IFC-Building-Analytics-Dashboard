import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import re
import streamlit as st
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

def _get_room_color(usage: str, force_orange: bool = False) -> str:
    usage_lower = str(usage).lower().strip()
    
    # "Gesamt" (parent root) is ALWAYS orange as requested!
    if "gesamt" in usage_lower:
        return "#E67E22"  # Bright Orange
        
    if force_orange:
        # Beautiful shades of orange for the "Gesamt" clicked state
        if "veloraum" in usage_lower:
            return "#D35400"      # Dark Orange
        elif "bar" in usage_lower or "empfang" in usage_lower:
            return "#E67E22"      # Rich Orange
        elif "saal" in usage_lower:
            return "#F39C12"      # Amber Orange
        elif "restaurant" in usage_lower:
            return "#FF9800"      # Light Orange
        elif "warteraum" in usage_lower:
            return "#FFA726"      # Gold Orange
        else:
            return "#FFB74D"      # Soft Orange

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

    # Read active room filter to determine if we color the entire treemap orange
    cf_usage = st.session_state.get("cf_page3_usage")
    force_orange = (cf_usage == "Gesamt")

    # Parent labeled bold: "<b>Gesamt</b>"
    labels = ["<b>Gesamt</b>"]
    parents = [""]
    values = [agg["area_m2"].sum()]
    colors = [_get_room_color("<b>Gesamt</b>", force_orange)]

    for _, row in agg.iterrows():
        labels.append(row["usage"])
        parents.append("<b>Gesamt</b>")
        values.append(row["area_m2"])
        colors.append(_get_room_color(row["usage"], force_orange))

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>%{value:.1f} m²",
        hovertemplate="<b>%{label}</b><br>Fläche: %{value:.1f} m²<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(colors=colors, colorscale=None),
        textfont=dict(size=14, family="Inter, sans-serif"), # Larger text and numbers!
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

    # Grouping rules:
    # - all materials with "holz" or "dachbekleidung" in their name mapped to "Holz"
    # - all materials with "allgemein" or "unbekannt" mapped to "Allgemein"
    # - others kept as-is
    def _group_material_name(name: str) -> str:
        name_lower = str(name).lower().strip()
        if "holz" in name_lower or "dachbekleidung" in name_lower:
            return "Holz"
        elif "allgemein" in name_lower or "unbekannt" in name_lower:
            return "Allgemein"
        else:
            return str(name).strip()

    df["grouped_material"] = df["material"].apply(_group_material_name)

    # Aggregate by grouped material
    agg = df.groupby("grouped_material")[col].sum().reset_index()
    agg.columns = ["material", "quantity"]

    total_volume = agg["quantity"].sum()
    agg = agg.sort_values("quantity", ascending=False)

    # Keep top 5 materials, rest goes to Andere
    if len(agg) > 5:
        top_5 = agg.head(5)
        rest = agg.iloc[5:]
        rest_val = rest["quantity"].sum()
        if rest_val > 0:
            rest_row = pd.DataFrame([{"material": "Andere", "quantity": rest_val}])
            agg = pd.concat([top_5, rest_row], ignore_index=True)
        else:
            agg = top_5

    # Separate "Andere" to place it at the very bottom of the horizontal bar chart
    is_andere = agg["material"] == "Andere"
    andere_row = agg[is_andere]
    main_rows = agg[~is_andere].sort_values("quantity", ascending=True)

    if not andere_row.empty:
        agg = pd.concat([andere_row, main_rows], ignore_index=True)
    else:
        agg = main_rows

    # Use single accent color #2E86AB (Stahlblau)
    colors = [COLORS["primary"]] * len(agg)
    if "Andere" in agg["material"].values:
        andere_idx = agg[agg["material"] == "Andere"].index[0]
        colors[andere_idx] = "#BDC3C7" # Light gray for Andere

    fig = go.Figure(go.Bar(
        x=agg["quantity"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:,.1f}" for v in agg["quantity"]],
        textposition="outside",
        hovertemplate=f"<b>%{{y}}</b><br>Menge: %{{x:.1f}} {unit}<extra></extra>",
    ))

    # Add annotation for the dominant material
    if not main_rows.empty and total_volume > 0:
        max_row = main_rows.loc[main_rows["quantity"].idxmax()]
        max_material = max_row["material"]
        max_qty = max_row["quantity"]
        pct = (max_qty / total_volume) * 100

        fig.add_annotation(
            x=max_qty,
            y=max_material,
            text=f"macht {pct:.1f}% des Gesamtvolumens aus",
            showarrow=False, # Removed arrow
            xanchor="left",  # Align callout text to the left
            xshift=10,       # Shift it slightly to the right of the bar end
            font=dict(size=11, color="#2D2D2D", family="Inter, sans-serif"),
            bgcolor="#FDEDEC",
            bordercolor="#FADBD8",
            borderwidth=1,
            borderpad=4,
            align="left",
        )

    apply_default_layout(fig, f"Materialmengen im Gebäude ({unit})")
    
    # Expand X-axis range slightly to make sure the text and annotation fit without clipping
    max_val = agg["quantity"].max()
    fig.update_layout(
        title=dict(
            text=f"Materialmengen im Gebäude ({unit})",
            font=dict(size=14, color=COLORS["text"]),
            x=0.0,
            y=0.98,          # Positioned higher!
            yanchor="top",
            xanchor="left",
        ),
        xaxis_title=unit, 
        yaxis_title="",
        xaxis=dict(range=[0, max_val * 1.55]),
        margin=dict(t=80), # larger top margin for title
    )
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

    # Define room groups according to the user request
    RAUM_GRUPPEN = {
        "Veloraum":     ("Lager/Technik",  "#5C6E7E"),
        "Abstellkamer": ("Lager/Technik",  "#5C6E7E"),
        "Abstellraum":  ("Lager/Technik",  "#5C6E7E"),
        "Technik":      ("Lager/Technik",  "#5C6E7E"),
        "Saal":         ("Aufenthalt",     "#2E86AB"),
        "Restaurant":   ("Aufenthalt",     "#2E86AB"),
        "Bar/Empfang":  ("Aufenthalt",     "#2E86AB"),
        "Warteraum":    ("Aufenthalt",     "#2E86AB"),
        "Backstage":    ("Aufenthalt",     "#2E86AB"),
        "WC":           ("Sanitär",        "#C8A96E"),
        "WC Damen":     ("Sanitär",        "#C8A96E"),
        "WC Herren":    ("Sanitär",        "#C8A96E"),
        "Treppenhaus":  ("Verkehr",        "#F0C987"),
        "Vorraum":      ("Verkehr",        "#F0C987"),
    }

    def _group_room_usage(usage: str) -> tuple[str, str]:
        usage_clean = str(usage).strip()
        for key, (group, color) in RAUM_GRUPPEN.items():
            if key.lower() in usage_clean.lower():
                return group, color
        return "Andere", "#CCCCCC"

    df["grouped_usage"] = df["usage"].apply(lambda u: _group_room_usage(u)[0])
    df["group_color"] = df["usage"].apply(lambda u: _group_room_usage(u)[1])

    # Dynamic groups based on data
    group_order = ["Aufenthalt", "Lager/Technik", "Sanitär", "Verkehr", "Andere"]
    usages = [u for u in group_order if u in df["grouped_usage"].values]

    fig = go.Figure()

    # Track all data for regression
    all_x = df["area_m2"].tolist()
    all_y = df["co2_load"].tolist()

    # Plot grouped scatter points
    for usage in usages:
        sub = df[df["grouped_usage"] == usage]
        color = sub["group_color"].iloc[0]
        names = sub["name"].astype(str).tolist() if "name" in sub.columns else ["Raum"] * len(sub)
        
        fig.add_trace(go.Scatter(
            x=sub["area_m2"], y=sub["co2_load"],
            mode="markers", name=usage,
            # Significantly larger (size=14), more opaque (0.95), and with a distinct dark outline (#2D2D2D, width=1.5) to make points pop!
            marker=dict(color=color, size=14, opacity=0.95, line=dict(width=1.5, color="#2D2D2D")),
            text=names,
            customdata=sub["usage"].tolist(),
            hovertemplate="<b>%{text}</b><br>Kategorie: " + usage + "<br>Typ: %{customdata}<br>Fläche: %{x:.1f} m²<br>CO₂-Last: %{y:,.0f} kg<extra></extra>",
        ))

    # Add Regression/Trend Line
    m, c = 0, 0
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

    # Add Outlier Annotations
    if len(all_x) > 1 and m != 0:
        # Exclude WC and Technik completely from being annotated as outliers
        candidates = []
        for idx, row in df.iterrows():
            room_name = str(row.get("name", "")).lower()
            room_type = str(row.get("usage", "")).lower()
            if "wc" in room_name or "wc" in room_type or "technik" in room_name or "technik" in room_type:
                continue
            candidates.append(row)
            
        if candidates:
            cand_df = pd.DataFrame(candidates)
            cand_df["y_pred"] = m * cand_df["area_m2"] + c
            cand_df["residual"] = cand_df["co2_load"] - cand_df["y_pred"]
            
            annotated_ids = set()
            to_annotate = []
            
            # 1. Always annotate Veloraum (the absolute primary outlier)
            for idx, row in cand_df.iterrows():
                r_name = str(row.get("name", "")).lower()
                r_type = str(row.get("usage", "")).lower()
                if "veloraum" in r_name or "veloraum" in r_type:
                    to_annotate.append(row)
                    annotated_ids.add(row.name)
            
            # 2. Always annotate Aufenthaltsräume > 100 m² (like the Saal ~160 m²)
            for idx, row in cand_df.iterrows():
                if row.name in annotated_ids:
                    continue
                r_name = str(row.get("name", "")).lower()
                r_type = str(row.get("usage", "")).lower()
                area = float(row.get("area_m2", 0))
                # Check if it is a lounge room (Aufenthaltsraum)
                is_aufenthalt = any(k in r_name or k in r_type for k in ["saal", "restaurant", "bar", "empfang", "warteraum", "backstage"])
                if is_aufenthalt and area > 100:
                    to_annotate.append(row)
                    annotated_ids.add(row.name)
            
            # 3. Fallback: Add other highest residual positive outliers if we have less than 3 annotations
            if len(to_annotate) < 3:
                std_residual = df["residual"].std() if len(df) > 2 else 1.0
                if pd.isna(std_residual) or std_residual <= 0:
                    std_residual = 1.0
                    
                rem = cand_df[(cand_df["residual"] > 1.2 * std_residual) & (~cand_df.index.isin(annotated_ids))].sort_values("residual", ascending=False)
                for idx, row in rem.iterrows():
                    if len(to_annotate) >= 3:
                        break
                    to_annotate.append(row)
                    annotated_ids.add(row.name)
            
            # Annotate all selected outliers
            for row in to_annotate:
                room_name = row.get("name") or "Raum"
                room_type = row.get("usage") or ""
                label_text = f"{room_name} ({room_type})" if room_type else room_name
                
                fig.add_annotation(
                    x=row["area_m2"],
                    y=row["co2_load"],
                    text=label_text,
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#D94F3D",
                    arrowsize=1.0,
                    ax=60,   # offset slightly more to the right to avoid overlapping data points
                    ay=-40,  # offset slightly more upwards
                    font=dict(size=13, color="#2D2D2D", family="Inter, sans-serif"),
                    bgcolor="rgba(253, 237, 236, 0.95)",
                    bordercolor="#FADBD8",
                    borderwidth=1.5,
                    borderpad=5,
                )

    apply_default_layout(fig, "Raumfläche vs. CO₂-Last")
    fig.update_layout(
        font=dict(size=14, family="Inter, sans-serif"), # Globally larger font size for the scatter plot!
        title=dict(
            font=dict(size=16, color=COLORS["text"]),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=13, color=COLORS["text"]), # Larger legend font
        ),
        margin=dict(t=100, b=60, l=60, r=40), # larger top margin for title & legend
    )
    # Force larger font sizes directly on axes to override any layout defaults!
    fig.update_xaxes(
        autorange=True, # Let it scale naturally to show all rooms (up to 180m²+)
        title=dict(
            text="Raumfläche (m²)",
            font=dict(size=14, color=COLORS["text"])
        ),
        tickfont=dict(size=13, color=COLORS["text_light"])
    )
    fig.update_yaxes(
        title=dict(
            text="CO₂-Last (kg CO₂eq)",
            font=dict(size=14, color=COLORS["text"])
        ),
        tickfont=dict(size=13, color=COLORS["text_light"])
    )
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
    # Define standard categories and groups
    part_order = ["Wand", "Boden", "Decke"]
    group_order = ["Beton", "Holz", "Metall", "Dämmung", "Glas", "Andere"]

    if element_df.empty or "ifc_class" not in element_df.columns or "material" not in element_df.columns:
        # Return an empty-looking dataframe with correct static layout
        pivot_pct = pd.DataFrame(0.0, index=part_order, columns=group_order)
    else:
        df = element_df.copy()

        # Map IFC classes to standard German building parts (Wand, Boden, Decke)
        # Fenster and Tür are completely omitted from this stacked bar chart.
        # We classify IfcSlab elements as 'Decke' if their type_name contains Decke/Dach/Roof/Ceiling,
        # otherwise they are floor slabs (Boden).
        def _map_class_to_part(row):
            cls = row.get("ifc_class", "")
            type_name = str(row.get("type_name", "")).lower()
            
            if cls in ("IfcWall", "IfcWallStandardCase", "IfcCurtainWall"):
                return "Wand"
            elif cls == "IfcRoof":
                return "Decke"
            elif cls == "IfcSlab":
                if "decke" in type_name or "dach" in type_name or "roof" in type_name or "ceiling" in type_name:
                    return "Decke"
                else:
                    return "Boden"
            else:
                return "Sonstige"

        df["part"] = df.apply(_map_class_to_part, axis=1)
        df = df[df["part"] != "Sonstige"]

        if df.empty:
            pivot_pct = pd.DataFrame(0.0, index=part_order, columns=group_order)
        else:
            # Classify raw materials into semantic groups
            df["mat_group"] = df["material"].apply(_classify_material_group)

            # Group and calculate percentages
            pivot = df.pivot_table(index="part", columns="mat_group", aggfunc="size", fill_value=0)
            
            # Reindex to ensure Wand, Boden, Decke are ALWAYS present on the X-axis
            # and all 6 material groups are ALWAYS present in the legend in the exact same order
            pivot = pivot.reindex(index=part_order, columns=group_order, fill_value=0)
            
            # Normalize to 100%
            row_sums = pivot.sum(axis=1)
            # Avoid division by zero
            pivot_pct = pivot.div(row_sums.replace(0, 1), axis=0) * 100
            # If a row had 0 total elements, keep its percentage at 0
            pivot_pct.loc[row_sums == 0] = 0.0

    fig = go.Figure()
    for grp in group_order:
        color = _MATERIAL_GROUP_COLORS[grp]
        fig.add_trace(go.Bar(
            x=pivot_pct.index,
            y=pivot_pct[grp],
            name=grp,
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{grp}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(barmode="stack")
    # Apply default layout with a clean title
    apply_default_layout(fig, "Materialanteil pro Bauteilgruppe")
    fig.update_layout(
        title=dict(
            text="Materialanteil pro Bauteilgruppe",
            font=dict(size=14, color=COLORS["text"]),
            x=0.0,
            y=0.98,          # Positioned higher!
            yanchor="top",
            xanchor="left",
        ),
        xaxis_title="", yaxis_title="Materialanteil (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(t=80), # larger top margin for title
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
