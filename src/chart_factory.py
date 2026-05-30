import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import re
import streamlit as st
from src.constants import (
    COLORS,
    STATUS_COLORS,
    ROOM_COLORS,
    MATERIAL_COLORS,
    CO2_SCALE,
    MATERIAL_GROUP_RULES as _MATERIAL_GROUP_RULES,
    MATERIAL_GROUP_COLORS as _MATERIAL_GROUP_COLORS,
    HOLZ_TRIGGERS as _HOLZ_TRIGGERS,
    RAUM_GRUPPEN,
)


def _classify_material_group(material_name: str) -> str:
    """Classify a raw material name into one of 6 semantic groups."""
    name = str(material_name).lower().strip()
    for triggers, group in _MATERIAL_GROUP_RULES:
        for t in triggers:
            if t in name:
                return group
    return "Andere"


def apply_default_layout(fig: go.Figure, title: str = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        title=(
            dict(
                text=title,
                font=dict(size=14, color=COLORS["text"]),
                x=0,
                xanchor="left",
            )
            if title
            else None
        ),
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
    fig.update_xaxes(
        gridcolor=COLORS["grid"],
        gridwidth=1,
        tickfont=dict(size=11, color=COLORS["text_light"]),
    )
    fig.update_yaxes(
        gridcolor=COLORS["grid"],
        gridwidth=1,
        tickfont=dict(size=11, color=COLORS["text_light"]),
    )
    return fig


def _empty_fig(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
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


# ── Helper to resolve consistent Room Colors ─────────────────────────────────


def _get_room_color(usage: str) -> str:
    usage_lower = str(usage).lower().strip()

    if "gesamt" in usage_lower or "root" in usage_lower or "total" in usage_lower:
        return "#1B3A5B"  # Brand Tiefblau für Gesamt

    # Try mapping to RAUM_GRUPPEN first
    for key, (group, color) in RAUM_GRUPPEN.items():
        if key.lower() in usage_lower:
            return color

    for key, color in ROOM_COLORS.items():
        if key.lower() in usage_lower:
            return color
    return ROOM_COLORS.get("Andere", "#C9CDD3")


# ── Treemap: "Welcher Raumtyp nimmt wie viel Fläche ein?" ──────────────────


def create_room_treemap(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten für Treemap verfügbar")

    df = space_df.copy()
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce").fillna(0)
    df = df[df["area_m2"] > 0]

    if df.empty:
        return _empty_fig("Keine positiven Raumflächen")

    agg = df.groupby("usage")["area_m2"].sum().reset_index()
    agg = agg.sort_values("area_m2", ascending=False)

    if len(agg) > 5:
        top = agg.head(5)
        rest_val = agg.iloc[5:]["area_m2"].sum()
        rest_row = pd.DataFrame([{"usage": "Andere", "area_m2": rest_val}])
        agg = pd.concat([top, rest_row], ignore_index=True)

    labels = ["<b>Gesamt</b>"]
    parents = [""]
    values = [agg["area_m2"].sum()]
    colors = [_get_room_color("<b>Gesamt</b>")]

    for _, row in agg.iterrows():
        labels.append(row["usage"])
        parents.append("<b>Gesamt</b>")
        values.append(row["area_m2"])
        colors.append(_get_room_color(row["usage"]))

    fig = go.Figure(
        go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            textinfo="label+value",
            texttemplate="<b>%{label}</b><br>%{value:.1f} m²",
            hovertemplate="<b>%{label}</b><br>Fläche: %{value:.1f} m²<br>Anteil: %{percentRoot:.1%}<extra></extra>",
            marker=dict(colors=colors, colorscale=None),
            textfont=dict(size=14, family="Inter, sans-serif"),
        )
    )
    apply_default_layout(fig, "Raumfläche nach Nutzungstyp (NFA)")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


# ── Horizontal Bar Chart: "Welche Materialien sind verbaut?" ────────────────


def create_material_volume_bar(element_df: pd.DataFrame, unit: str = "m³") -> go.Figure:
    if element_df.empty:
        return _empty_fig("Keine Elementdaten verfügbar")

    col = "volume_m3" if unit in ("m³", "m\u00b3") else "area_m2"
    df = element_df.dropna(subset=[col]).copy()
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df[df[col] > 0]

    if df.empty:
        return _empty_fig("Keine Mengendaten verfügbar")

    df["grouped_material"] = df["material"].apply(_classify_material_group)
    agg = df.groupby("grouped_material")[col].sum().reset_index()
    agg.columns = ["material", "quantity"]
    total_volume = agg["quantity"].sum()

    is_andere = agg["material"] == "Andere"
    andere_row = agg[is_andere]
    main_rows = agg[~is_andere].sort_values("quantity", ascending=True)

    if not andere_row.empty:
        agg = pd.concat([andere_row, main_rows], ignore_index=True)
    else:
        agg = main_rows

    colors = [_MATERIAL_GROUP_COLORS.get(m, "#BDC3C7") for m in agg["material"]]

    fig = go.Figure(
        go.Bar(
            x=agg["quantity"],
            y=agg["material"],
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.1f}" for v in agg["quantity"]],
            textposition="outside",
            hovertemplate=f"<b>%{{y}}</b><br>Menge: %{{x:.1f}} {unit}<extra></extra>",
        )
    )

    if not main_rows.empty and total_volume > 0:
        max_row = main_rows.loc[main_rows["quantity"].idxmax()]
        max_material = max_row["material"]
        max_qty = max_row["quantity"]
        pct = (max_qty / total_volume) * 100

        fig.add_annotation(
            x=max_qty,
            y=max_material,
            text=f"macht {pct:.1f}% des Gesamtvolumens aus",
            showarrow=False,
            xanchor="left",
            xshift=65,
            font=dict(size=11, color="#2D2D2D", family="Inter, sans-serif"),
            bgcolor="#FDEDEC",
            bordercolor="#FADBD8",
            borderwidth=1,
            borderpad=4,
            align="left",
        )

    apply_default_layout(fig, f"Materialmengen im Gebäude ({unit})")
    max_val = agg["quantity"].max()
    fig.update_layout(
        title=dict(
            text=f"Materialmengen im Gebäude ({unit})",
            font=dict(size=14, color=COLORS["text"]),
            x=0.0,
            y=0.98,
            yanchor="top",
            xanchor="left",
        ),
        xaxis_title=unit,
        yaxis_title="",
        xaxis=dict(range=[0, max_val * 1.55]),
        margin=dict(t=80),
    )
    return fig


# ── Horizontal Bar Chart: "Welches Material verursacht am meisten CO2?" ─────


def create_material_co2_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO₂-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]

    if df.empty:
        return _empty_fig("Keine CO₂-Werte vorhanden")

    def _normalize_to_holz(material_name: str) -> str:
        name = str(material_name).lower().strip()
        for trigger in _HOLZ_TRIGGERS:
            if trigger in name:
                return "Holz"
        return material_name

    df["material_grouped"] = df["material"].apply(_normalize_to_holz)
    agg = df.groupby("material_grouped")["co2e_total"].sum().reset_index()
    agg.columns = ["material", "co2"]

    SCHWELLENWERT_KG = 200
    mask_klein = agg["co2"] < SCHWELLENWERT_KG
    andere_co2 = agg.loc[mask_klein, "co2"].sum()
    agg_haupt = agg[~mask_klein].copy()

    if andere_co2 > 0:
        andere_row = pd.DataFrame([{"material": "Andere", "co2": andere_co2}])
        if "Andere" in agg_haupt["material"].values:
            agg_haupt.loc[agg_haupt["material"] == "Andere", "co2"] += andere_co2
        else:
            agg_haupt = pd.concat([andere_row, agg_haupt], ignore_index=True)

    agg = agg_haupt.copy()
    is_andere = agg["material"] == "Andere"
    andere_rows = agg[is_andere]
    haupt_rows = agg[~is_andere].sort_values("co2", ascending=True)
    agg = pd.concat([andere_rows, haupt_rows], ignore_index=True)

    avg_val = agg["co2"].mean()
    vals = agg["co2"].tolist()
    min_v, max_v = min(vals), max(vals)
    span = (max_v - min_v) if max_v != min_v else 1.0

    final_colors = [
        _MATERIAL_GROUP_COLORS.get(mat, "#C9CDD3")
        for mat in agg["material"].tolist()
    ]

    fig = go.Figure(
        go.Bar(
            x=agg["co2"],
            y=agg["material"],
            orientation="h",
            marker_color=final_colors,
            text=[f"{v:,.0f} kg" for v in agg["co2"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>CO₂e-Last: %{x:,.0f} kg<extra></extra>",
        )
    )

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


# ── Scatter Plot: "Gibt es Räume mit unverhältnismässig hohem CO2?" ──────────


def create_room_co2_scatter(space_df: pd.DataFrame, selected_raum: str = None) -> go.Figure:
    if (
        space_df.empty
        or "area_m2" not in space_df.columns
        or "co2_load" not in space_df.columns
    ):
        return _empty_fig("Keine ausreichenden Raumdaten für Scatter Plot verfügbar")

    df = space_df.dropna(subset=["area_m2", "co2_load"]).copy()
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["co2_load"] = pd.to_numeric(df["co2_load"], errors="coerce")
    df = df[(df["area_m2"] > 0) & (df["co2_load"] >= 0)]

    if "raum_nr" not in df.columns:
        df["raum_nr"] = df["name"]
    if "raumname" not in df.columns:
        df["raumname"] = df["usage"]
    df["label"] = df["raum_nr"].astype(str) + " – " + df["raumname"]

    if df.empty:
        return _empty_fig("Keine quantitativen Werte für Scatter Plot")

    def _group_room_usage(usage: str) -> tuple[str, str]:
        usage_clean = str(usage).strip()
        for key, (group, color) in RAUM_GRUPPEN.items():
            if key.lower() in usage_clean.lower():
                return group, color
        return "Andere", "#CCCCCC"

    df["grouped_usage"] = df["usage"].apply(lambda u: _group_room_usage(u)[0])
    df["group_color"] = df["usage"].apply(lambda u: _group_room_usage(u)[1])

    group_order = ["Aufenthalt", "Lager/Technik", "Sanitär", "Verkehr", "Andere"]
    usages = [u for u in group_order if u in df["grouped_usage"].values]

    fig = go.Figure()
    all_x = df["area_m2"].tolist()
    all_y = df["co2_load"].tolist()

    def hex_to_rgba(hex_str, opacity):
        hex_str = hex_str.lstrip('#')
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return f"rgba({r},{g},{b},{opacity})"

    for usage in usages:
        sub = df[df["grouped_usage"] == usage]
        base_color = sub["group_color"].iloc[0]

        marker_colors = []
        marker_sizes = []
        line_colors = []
        line_widths = []

        for idx, row in sub.iterrows():
            rlabel = row.get("label", "")
            if selected_raum:
                if rlabel == selected_raum:
                    marker_colors.append(hex_to_rgba(base_color, 1.0))
                    marker_sizes.append(20)
                    line_colors.append("rgba(0,0,0,1.0)")
                    line_widths.append(3.0)
                else:
                    marker_colors.append(hex_to_rgba(base_color, 0.3))
                    marker_sizes.append(14)
                    line_colors.append("rgba(45,45,45,0.3)")
                    line_widths.append(1.5)
            else:
                marker_colors.append(hex_to_rgba(base_color, 0.95))
                marker_sizes.append(14)
                line_colors.append("rgba(45,45,45,0.95)")
                line_widths.append(1.5)

        fig.add_trace(
            go.Scatter(
                x=sub["area_m2"],
                y=sub["co2_load"],
                mode="markers",
                name=usage,
                marker=dict(
                    color=marker_colors,
                    size=marker_sizes,
                    line=dict(width=line_widths, color=line_colors),
                ),
                text=sub["label"].tolist(),
                customdata=sub["usage"].tolist(),
                hovertemplate="<b>%{text}</b><br>Kategorie: "
                + usage
                + "<br>Typ: %{customdata}<br>Fläche: %{x:.1f} m²<br>CO₂-Last: %{y:,.0f} kg<extra></extra>",
            )
        )

    m, c = 0, 0
    if len(all_x) > 1:
        try:
            m, c = np.polyfit(all_x, all_y, 1)
            x_range = np.linspace(min(all_x), max(all_x), 100)
            y_range = m * x_range + c
            fig.add_trace(
                go.Scatter(
                    x=x_range,
                    y=y_range,
                    mode="lines",
                    name="Trendlinie",
                    line=dict(color=COLORS["text_light"], width=1.5, dash="dot"),
                    hoverinfo="skip",
                )
            )
        except Exception:
            pass

    if len(all_x) > 1 and m != 0:
        candidates = []
        for idx, row in df.iterrows():
            room_name = str(row.get("name", "")).lower()
            room_type = str(row.get("usage", "")).lower()
            if (
                "wc" in room_name
                or "wc" in room_type
                or "technik" in room_name
                or "technik" in room_type
            ):
                continue
            candidates.append(row)

        if candidates:
            cand_df = pd.DataFrame(candidates)
            cand_df["y_pred"] = m * cand_df["area_m2"] + c
            cand_df["residual"] = cand_df["co2_load"] - cand_df["y_pred"]

            annotated_ids = set()
            to_annotate = []

            for idx, row in cand_df.iterrows():
                r_name = str(row.get("name", "")).lower()
                r_type = str(row.get("usage", "")).lower()
                if "veloraum" in r_name or "veloraum" in r_type:
                    to_annotate.append(row)
                    annotated_ids.add(row.name)

            for idx, row in cand_df.iterrows():
                if row.name in annotated_ids:
                    continue
                r_name = str(row.get("name", "")).lower()
                r_type = str(row.get("usage", "")).lower()
                area = float(row.get("area_m2", 0))
                is_aufenthalt = any(
                    k in r_name or k in r_type
                    for k in [
                        "saal",
                        "restaurant",
                        "bar",
                        "empfang",
                        "warteraum",
                        "backstage",
                    ]
                )
                if is_aufenthalt and area > 100:
                    to_annotate.append(row)
                    annotated_ids.add(row.name)

            if len(to_annotate) < 3:
                std_residual = df["residual"].std() if len(df) > 2 else 1.0
                if pd.isna(std_residual) or std_residual <= 0:
                    std_residual = 1.0
                rem = cand_df[
                    (cand_df["residual"] > 1.2 * std_residual)
                    & (~cand_df.index.isin(annotated_ids))
                ].sort_values("residual", ascending=False)
                for idx, row in rem.iterrows():
                    if len(to_annotate) >= 3:
                        break
                    to_annotate.append(row)
                    annotated_ids.add(row.name)

            for row in to_annotate:
                room_name = row.get("name") or "Raum"
                room_type = row.get("usage") or ""
                label_text = f"{room_name} ({room_type})" if room_type else room_name
                ax_offset, ay_offset = 60, -40
                r_name_lower = str(room_name).lower()
                r_type_lower = str(room_type).lower()
                if (
                    "bar" in r_name_lower
                    or "empfang" in r_name_lower
                    or "bar" in r_type_lower
                    or "empfang" in r_type_lower
                ):
                    ax_offset, ay_offset = -40, 45
                elif "saal" in r_name_lower or "saal" in r_type_lower:
                    ax_offset, ay_offset = -60, -40
                elif "veloraum" in r_name_lower or "veloraum" in r_type_lower:
                    ax_offset, ay_offset = 60, -45

                fig.add_annotation(
                    x=row["area_m2"],
                    y=row["co2_load"],
                    text=label_text,
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#D94F3D",
                    arrowsize=1.0,
                    ax=ax_offset,
                    ay=ay_offset,
                    font=dict(size=13, color="#2D2D2D", family="Inter, sans-serif"),
                    bgcolor="rgba(253, 237, 236, 0.95)",
                    bordercolor="#FADBD8",
                    borderwidth=1.5,
                    borderpad=5,
                )

    apply_default_layout(fig, "Raumfläche vs. CO₂-Last")
    fig.update_layout(
        font=dict(size=14, family="Inter, sans-serif"),
        title=dict(font=dict(size=16, color=COLORS["text"])),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=13, color=COLORS["text"]),
        ),
        margin=dict(t=100, b=60, l=60, r=40),
    )
    fig.update_xaxes(
        autorange=True,
        title=dict(text="Raumfläche (m²)", font=dict(size=14, color=COLORS["text"])),
        tickfont=dict(size=13, color=COLORS["text_light"]),
    )
    fig.update_yaxes(
        title=dict(
            text="CO₂-Last (kg CO₂eq)", font=dict(size=14, color=COLORS["text"])
        ),
        tickfont=dict(size=13, color=COLORS["text_light"]),
    )
    return fig


# ── Stacked Bar Chart 100%: "Bauteil-Material-Verteilung" ──────────────────


def create_element_material_stacked_bar(element_df: pd.DataFrame) -> go.Figure:
    part_order = ["Wand", "Boden", "Decke"]
    group_order = ["Beton", "Holz", "Metall", "Dämmung", "Glas", "Andere"]

    if (
        element_df.empty
        or "ifc_class" not in element_df.columns
        or "material" not in element_df.columns
    ):
        pivot_pct = pd.DataFrame(0.0, index=part_order, columns=group_order)
    else:
        df = element_df.copy()

        def _map_class_to_part(row):
            cls = row.get("ifc_class", "")
            type_name = str(row.get("type_name", "")).lower()
            if cls in ("IfcWall", "IfcWallStandardCase", "IfcCurtainWall"):
                return "Wand"
            elif cls == "IfcRoof":
                return "Decke"
            elif cls == "IfcSlab":
                if (
                    "decke" in type_name
                    or "dach" in type_name
                    or "roof" in type_name
                    or "ceiling" in type_name
                ):
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
            df["mat_group"] = df["material"].apply(_classify_material_group)
            pivot = df.pivot_table(
                index="part", columns="mat_group", aggfunc="size", fill_value=0
            )
            pivot = pivot.reindex(index=part_order, columns=group_order, fill_value=0)
            row_sums = pivot.sum(axis=1)
            pivot_pct = pivot.div(row_sums.replace(0, 1), axis=0) * 100
            pivot_pct.loc[row_sums == 0] = 0.0

    fig = go.Figure()
    for grp in group_order:
        color = _MATERIAL_GROUP_COLORS[grp]
        fig.add_trace(
            go.Bar(
                x=pivot_pct.index,
                y=pivot_pct[grp],
                name=grp,
                marker_color=color,
                hovertemplate=f"<b>%{{x}}</b><br>{grp}: %{{y:.1f}}%<extra></extra>",
            )
        )

    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Materialanteil pro Bauteilgruppe")
    fig.update_layout(
        title=dict(
            text="Materialanteil pro Bauteilgruppe",
            font=dict(size=14, color=COLORS["text"]),
            x=0.0,
            y=0.98,
            yanchor="top",
            xanchor="left",
        ),
        xaxis_title="",
        yaxis_title="Materialanteil (%)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.05,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        margin=dict(t=80),
    )
    return fig


# ── Page 6 Quality Charts ──────────────────────────────────────────────────────


def create_quality_gauge(score: float) -> go.Figure:
    fig = go.Figure(
        go.Indicator(
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
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=60, b=20),
        height=280,
    )
    return fig


def create_error_bar(error_counts: dict) -> go.Figure:
    """Horizontales Balkendiagramm: Fehlertypen absteigend sortiert, Farben nach Schweregrad."""
    LABEL_MAP = {
        "missing_storey": "Kein Geschoss",
        "missing_material": "Kein Material",
        "missing_quantity": "Keine Mengen",
        "missing_usage": "Keine Nutzung",
        "missing_status": "Kein Status",
    }
    SEVERITY_COLOR = {
        "missing_storey": "#E07B39",
        "missing_material": "#E07B39",
        "missing_quantity": "#D4A017",
        "missing_usage": "#2E86AB",
        "missing_status": "#2E86AB",
    }

    rows = [
        {
            "key": k,
            "label": LABEL_MAP[k],
            "value": error_counts.get(k, 0),
            "color": SEVERITY_COLOR[k],
        }
        for k in LABEL_MAP
        if k in error_counts or error_counts.get(k, 0) == 0
    ]
    rows_sorted = sorted(rows, key=lambda r: r["value"], reverse=True)

    labels = [r["label"] for r in rows_sorted]
    values = [r["value"] for r in rows_sorted]
    colors = [r["color"] if r["value"] > 0 else "#CCCCCC" for r in rows_sorted]

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="outside",
            textfont=dict(size=12, color="#1A1A2E"),
            hovertemplate="<b>%{y}</b><br>Anzahl: %{x}<extra></extra>",
            cliponaxis=False,
        )
    )

    apply_default_layout(fig, "Fehler nach Kategorie")
    max_val = max(values) if values else 1
    fig.update_layout(
        xaxis=dict(
            title="Anzahl",
            range=[0, max_val * 1.25],
            showgrid=True,
            gridcolor="#F0F0F0",
            zeroline=False,
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=12),
        ),
        showlegend=False,
        bargap=0.35,
        margin=dict(l=10, r=50, t=40, b=40),
    )
    return fig


def create_pset_matrix_heatmap(pset_matrix: pd.DataFrame) -> go.Figure:
    """Heatmap: Psets auf Y-Achse (alphabetisch), IFC-Klassen auf X-Achse (nach Vollständigkeit desc).
    Blau = vorhanden (#2E86AB), Orange = fehlend (#E07B39).
    """
    if pset_matrix is None or pset_matrix.empty:
        return _empty_fig("Keine Pset-Daten verfügbar")

    # pset_matrix: index = IFC-Klassen, columns = Psets
    psets_sorted = sorted(pset_matrix.columns.tolist())
    completeness = (pset_matrix[psets_sorted] > 0).sum(axis=1)
    classes_sorted = completeness.sort_values(ascending=False).index.tolist()

    df_sorted = pset_matrix.loc[classes_sorted, psets_sorted]

    # Transponieren: Zeilen = Psets (Y-Achse), Spalten = IFC-Klassen (X-Achse)
    z = (df_sorted.T > 0).astype(int).values
    hover_text = [["Vorhanden" if v else "Fehlt" for v in row] for row in z]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=classes_sorted,
            y=psets_sorted,
            colorscale=[[0, "#FFFFFF"], [1, "#2E86AB"]],
            showscale=False,
            hovertemplate="Klasse: %{x}<br>Pset: %{y}<br>%{text}<extra></extra>",
            text=hover_text,
            zmin=0,
            zmax=1,
        )
    )

    apply_default_layout(fig, "Pset-Verfügbarkeit nach IFC-Klasse")
    fig.update_layout(
        xaxis=dict(title="IFC-Klasse", tickangle=0, tickfont=dict(size=11)),
        yaxis=dict(
            title="Property Set",
            tickangle=0,
            tickfont=dict(size=11),
            autorange="reversed",
        ),
        margin=dict(l=20, r=20, t=50, b=60),
    )
    return fig


def create_pset_lollipop_chart(pset_matrix: pd.DataFrame) -> go.Figure:
    """Lollipop Chart: Pset-Vollständigkeit (%) pro IFC-Klasse.
    Farbe: Orange (#E07B39) unter 50%, Blau (#2E86AB) ab 50%.
    """
    if pset_matrix is None or pset_matrix.empty:
        return _empty_fig("Keine Pset-Daten verfügbar")

    total_psets = len(pset_matrix.columns)
    if total_psets == 0:
        return _empty_fig("Keine Psets gefunden")

    # Berechne Vollständigkeit pro IFC-Klasse
    completeness = (pset_matrix > 0).sum(axis=1) / total_psets * 100
    completeness = completeness.sort_values(ascending=False)  # Schlechteste oben

    classes = completeness.index.tolist()
    values = completeness.values.tolist()
    missing_counts = [total_psets - int((pset_matrix.loc[c] > 0).sum()) for c in classes]

    COLOR_GOOD = "#2E86AB"
    COLOR_BAD = "#E07B39"

    fig = go.Figure()

    # Horizontale Linien (Stiele)
    for i, (cls, val) in enumerate(zip(classes, values)):
        color = COLOR_GOOD if val >= 50 else COLOR_BAD
        fig.add_shape(
            type="line",
            x0=0, x1=val, y0=cls, y1=cls,
            line=dict(color=color, width=3),
        )

    # Punkte am Ende
    colors = [COLOR_GOOD if v >= 50 else COLOR_BAD for v in values]
    hover_texts = [
        f"{cls}: {val:.0f}% vollständig – {miss} Psets fehlen"
        for cls, val, miss in zip(classes, values, missing_counts)
    ]

    fig.add_trace(go.Scatter(
        x=values,
        y=classes,
        mode="markers+text",
        marker=dict(
            size=18,
            color=colors,
            line=dict(color="white", width=2),
        ),
        text=[f"{v:.0f}%" for v in values],
        textposition="middle right",
        textfont=dict(size=12, color="#2D2D2D", family="Inter, sans-serif"),
        hovertext=hover_texts,
        hoverinfo="text",
        customdata=list(zip(classes, values, missing_counts)),
    ))

    # 50%-Schwelle
    fig.add_vline(
        x=50, line_dash="dash", line_color="#999999", line_width=1.5,
        annotation_text="50% Schwelle",
        annotation_position="top right",
        annotation_font=dict(size=11, color="#999999"),
    )

    fig.update_layout(
        title=dict(
            text="Pset-Vollständigkeit nach IFC-Klasse<br>"
                 "<span style='font-size:12px;color:#888'>Orange = unter 50% (kritisch) | Blau = über 50%</span>",
            font=dict(size=14, color=COLORS["text"], family="Inter, sans-serif"),
            x=0, xanchor="left",
        ),
        xaxis=dict(
            title="Vollständigkeit",
            range=[0, 110],
            ticksuffix="%",
            showgrid=True,
            gridcolor="#EAEAEA",
            zeroline=False,
            tickfont=dict(size=12, color=COLORS["text_light"]),
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=12, color=COLORS["text"]),
            autorange="reversed",
        ),
        paper_bgcolor="white",
        plot_bgcolor="#F5F5F5",
        showlegend=False,
        margin=dict(l=10, r=40, t=70, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
    )

    return fig


def create_room_co2_density_bar(space_df: pd.DataFrame, selected_raum: str = None) -> go.Figure:
    """Horizontal bar chart showing CO2 density (co2_load / area_m2) for each room,
    sorted by density descending.
    Click-interaction highlights the selected room and fades others.
    """
    if (
        space_df.empty
        or "area_m2" not in space_df.columns
        or "co2_load" not in space_df.columns
    ):
        return _empty_fig("Keine ausreichenden Raumdaten für CO₂-Dichte-Chart verfügbar")

    df = space_df.dropna(subset=["area_m2", "co2_load"]).copy()
    df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    df["co2_load"] = pd.to_numeric(df["co2_load"], errors="coerce")
    df = df[(df["area_m2"] > 0) & (df["co2_load"] >= 0)]

    if "raum_nr" not in df.columns:
        df["raum_nr"] = df["name"]
    if "raumname" not in df.columns:
        df["raumname"] = df["usage"]
    df["label"] = df["raum_nr"].astype(str) + " – " + df["raumname"]

    if df.empty:
        return _empty_fig("Keine quantitativen Werte für CO₂-Dichte-Chart")

    # Berechne CO2-Dichte
    df["co2_dichte"] = df["co2_load"] / df["area_m2"]
    
    # Sortieren nach Dichte aufsteigend, da Plotly horizontal bar chart von unten nach oben rendert.
    # So steht der höchste Dichtewert ganz oben!
    df = df.sort_values("co2_dichte", ascending=True)

    def _group_room_usage(usage: str) -> tuple[str, str]:
        usage_clean = str(usage).strip()
        for key, (group, color) in RAUM_GRUPPEN.items():
            if key.lower() in usage_clean.lower():
                return group, color
        return "Andere", "#CCCCCC"

    df["grouped_usage"] = df["usage"].apply(lambda u: _group_room_usage(u)[0])
    df["group_color"] = df["usage"].apply(lambda u: _group_room_usage(u)[1])

    # Styling auf Basis von selected_raum
    bar_colors = []
    line_colors = []
    line_widths = []

    def hex_to_rgba(hex_str, opacity):
        hex_str = hex_str.lstrip('#')
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return f"rgba({r},{g},{b},{opacity})"

    for idx, row in df.iterrows():
        rlabel = row.get("label", "")
        base_color = row.get("group_color", "#CCCCCC")
        if selected_raum:
            if rlabel == selected_raum:
                # Hervorgehoben: Volle Opazität + dicke schwarze Kontur
                bar_colors.append(hex_to_rgba(base_color, 1.0))
                line_colors.append("rgba(0,0,0,1.0)")
                line_widths.append(3.0)
            else:
                # Verblasst: Niedrige Opazität
                bar_colors.append(hex_to_rgba(base_color, 0.3))
                line_colors.append("rgba(45,45,45,0.3)")
                line_widths.append(0.0)
        else:
            # Standard: Volle Opazität
            bar_colors.append(hex_to_rgba(base_color, 0.95))
            line_colors.append("rgba(0,0,0,0)")
            line_widths.append(0.0)

    # Plotly bar chart
    fig = go.Figure(
        go.Bar(
            x=df["co2_dichte"],
            y=df["label"],
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color=line_colors, width=line_widths)
            ),
            text=[f"{v:.1f} kg/m²" for v in df["co2_dichte"]],
            textposition="outside",
            textfont=dict(size=12, color="#2D2D2D"),
            hovertemplate="<b>%{y}</b><br>Dichte: %{x:.1f} kg/m²<br>Fläche: %{customdata[0]:.1f} m²<br>CO₂ total: %{customdata[1]:,.0f} kg<extra></extra>",
            customdata=list(zip(df["area_m2"], df["co2_load"])),
            cliponaxis=False,
        )
    )

    max_val = df["co2_dichte"].max() or 1.0
    apply_default_layout(fig, "CO₂-Intensität pro Raum (kg CO₂eq / m²)")
    fig.update_layout(
        title=dict(
            text="CO₂-Intensität pro Raum (kg CO₂eq / m²)<br>"
                 "<span style='font-size:12px;color:#888'>Zeigt welche Räume überproportional viel CO₂ pro Fläche verbrauchen</span>",
            font=dict(size=14, color=COLORS["text"], family="Inter, sans-serif"),
            x=0, xanchor="left",
        ),
        xaxis=dict(
            title="kg CO₂eq / m²",
            range=[0, max_val * 1.25],
            showgrid=True,
            gridcolor="#EAEAEA",
            zeroline=False,
            tickfont=dict(size=12, color=COLORS["text_light"]),
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=12, color=COLORS["text"]),
        ),
        paper_bgcolor="white",
        plot_bgcolor="#F5F5F5",
        margin=dict(l=10, r=60, t=80, b=40),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
    )
    return fig

def create_co2_pareto(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO₂-Daten verfügbar")
    
    df_m = element_df.dropna(subset=["co2e_total", "material"]).copy()
    if df_m.empty:
        return _empty_fig("Keine Materialien mit CO₂")
        
    df_m["co2_num"] = pd.to_numeric(df_m["co2e_total"], errors="coerce").fillna(0)
    agg = df_m.groupby("material")["co2_num"].sum().sort_values(ascending=False).reset_index()
    agg = agg[agg["co2_num"] > 0]
    if agg.empty:
        return _empty_fig("CO₂-Wert ist 0")
        
    total_co2 = agg["co2_num"].sum()
    agg["cum_pct"] = agg["co2_num"].cumsum() / total_co2 * 100
    
    fig = go.Figure()
    
    colors = [_MATERIAL_GROUP_COLORS.get(m, "#C9CDD3") for m in agg["material"]]
    
    # Bar for absolute CO2
    fig.add_trace(
        go.Bar(
            x=agg["material"],
            y=agg["co2_num"],
            marker_color=colors,
            name="CO₂-Last",
            hovertemplate="Material: %{x}<br>CO₂: %{y:,.0f} kg<extra></extra>"
        )
    )
    
    # Line for cumulative %
    fig.add_trace(
        go.Scatter(
            x=agg["material"],
            y=agg["cum_pct"],
            mode="lines+markers",
            name="Kumuliert %",
            yaxis="y2",
            line=dict(color=COLORS["text"], width=2),
            marker=dict(size=6, color=COLORS["text"]),
            hovertemplate="Material: %{x}<br>Kumuliert: %{y:.1f}%<extra></extra>"
        )
    )
    
    fig = apply_default_layout(fig, "")
    
    # Add 80% line
    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=80, y1=80, yref="y2",
        line=dict(color=COLORS["error_critical"], width=1, dash="dash"),
    )
    
    fig.update_layout(
        yaxis2=dict(
            title="Kumuliert %",
            overlaying="y",
            side="right",
            range=[0, 105],
            gridcolor="rgba(0,0,0,0)",
            tickfont=dict(size=11, color=COLORS["text_light"])
        ),
        showlegend=False,
        margin=dict(r=50) # make room for right yaxis
    )
    
    return fig

def create_sia_gauge(co2_per_m2: float, limit: float = 11.0) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=co2_per_m2,
        number={"valueformat": ".1f", "suffix": " kg"},
        delta={"reference": limit, "increasing": {"color": COLORS["error_critical"]}, "decreasing": {"color": COLORS["error_ok"]}},
        title={"text": "CO₂e pro m²·a", "font": {"size": 14, "color": COLORS["text_light"]}},
        gauge={
            "axis": {"range": [None, max(limit * 1.5, co2_per_m2 * 1.2)], "tickwidth": 1, "tickcolor": COLORS["text_light"]},
            "bar": {"color": COLORS["text"]},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "gray",
            "steps": [
                {"range": [0, limit * 0.8], "color": CO2_SCALE[0]},
                {"range": [limit * 0.8, limit], "color": CO2_SCALE[1]},
                {"range": [limit, max(limit * 1.5, co2_per_m2 * 1.2)], "color": CO2_SCALE[2]}
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": limit
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=20))
    return fig

def create_storey_material_heatmap(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "storey" not in element_df.columns or "co2e_total" not in element_df.columns:
        return _empty_fig("Daten für Heatmap fehlen")
        
    df_m = element_df.dropna(subset=["storey", "grouped_material", "co2e_total"]).copy()
    df_m["co2_num"] = pd.to_numeric(df_m["co2e_total"], errors="coerce").fillna(0)
    
    pivot = df_m.pivot_table(index="storey", columns="grouped_material", values="co2_num", aggfunc="sum").fillna(0)
    if pivot.empty:
        return _empty_fig("Keine Daten nach Filterung")
        
    # Sort storeys nicely if they have numbers
    storeys_sorted = sorted(pivot.index.tolist())
    pivot = pivot.reindex(storeys_sorted)
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#FFFFFF"], [1, COLORS["error_critical"]]],
        hovertemplate="Geschoss: %{y}<br>Material: %{x}<br>CO₂: %{z:,.0f} kg<extra></extra>",
        showscale=True
    ))
    
    fig = apply_default_layout(fig, "")
    return fig

def create_renovation_waterfall(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "status" not in element_df.columns or "co2e_total" not in element_df.columns:
        return _empty_fig("Status oder CO₂-Daten fehlen")
        
    df_m = element_df.dropna(subset=["status", "co2e_total"]).copy()
    df_m["co2_num"] = pd.to_numeric(df_m["co2e_total"], errors="coerce").fillna(0)
    
    agg = df_m.groupby("status")["co2_num"].sum()
    
    bestand = agg.get("Bestand", 0)
    abbruch = agg.get("Abbruch", 0)
    neubau = agg.get("Neubau", 0)
    
    fig = go.Figure(go.Waterfall(
        name="Umbau Waterfall", orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Bestand (Erhalten)", "Abbruch (Verloren)", "Neubau (Hinzugefügt)", "Netto-Bilanz"],
        textposition="outside",
        text=[f"{bestand:,.0f}", f"-{abbruch:,.0f}", f"+{neubau:,.0f}", f"{bestand-abbruch+neubau:,.0f}"],
        y=[bestand, -abbruch, neubau, bestand-abbruch+neubau],
        connector={"line":{"color":COLORS["text_light"]}},
        decreasing={"marker":{"color":COLORS["abbruch"]}},
        increasing={"marker":{"color":COLORS["neubau"]}},
        totals={"marker":{"color":COLORS["text"]}}
    ))
    
    fig = apply_default_layout(fig, "")
    fig.update_layout(showlegend=False)
    return fig

def create_cost_co2_scatter(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "cost_chf" not in element_df.columns or "co2e_total" not in element_df.columns:
        return _empty_fig("Kosten oder CO₂-Daten fehlen")
        
    df_m = element_df.dropna(subset=["grouped_material", "cost_chf", "co2e_total", "volume_m3"]).copy()
    if df_m.empty:
        return _empty_fig("Daten unvollständig")
        
    df_m["cost_num"] = pd.to_numeric(df_m["cost_chf"], errors="coerce").fillna(0)
    df_m["co2_num"] = pd.to_numeric(df_m["co2e_total"], errors="coerce").fillna(0)
    df_m["vol_num"] = pd.to_numeric(df_m["volume_m3"], errors="coerce").fillna(0)
    
    # Aggregate by material group
    agg = df_m.groupby("grouped_material").agg({"cost_num": "sum", "co2_num": "sum", "vol_num": "sum"}).reset_index()
    agg = agg[(agg["cost_num"]>0) | (agg["co2_num"]>0)]
    
    colors = [_MATERIAL_GROUP_COLORS.get(m, "#C9CDD3") for m in agg["grouped_material"]]
    
    fig = go.Figure(data=go.Scatter(
        x=agg["cost_num"],
        y=agg["co2_num"],
        mode="markers+text",
        text=agg["grouped_material"],
        textposition="top center",
        marker=dict(
            size=agg["vol_num"],
            sizemode="area",
            sizeref=2.*max(agg["vol_num"])/(40.**2) if max(agg["vol_num"])>0 else 1,
            sizemin=4,
            color=colors,
            line=dict(width=1, color=COLORS["text"])
        ),
        hovertemplate="<b>%{text}</b><br>Kosten: CHF %{x:,.0f}<br>CO₂: %{y:,.0f} kg<br>Volumen: %{marker.size:,.1f} m³<extra></extra>"
    ))
    
    fig = apply_default_layout(fig, "")
    fig.update_xaxes(title="Kosten (CHF)")
    fig.update_yaxes(title="CO₂e (kg)")
    return fig

def create_cost_breakdown_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "cost_chf" not in element_df.columns:
        return _empty_fig("Keine Kostendaten")
        
    df_m = element_df.dropna(subset=["grouped_material", "cost_chf"]).copy()
    df_m["cost_num"] = pd.to_numeric(df_m["cost_chf"], errors="coerce").fillna(0)
    
    agg = df_m.groupby("grouped_material")["cost_num"].sum().sort_values(ascending=True)
    agg = agg[agg>0]
    
    if agg.empty:
        return _empty_fig("Kosten sind 0")
        
    colors = [_MATERIAL_GROUP_COLORS.get(m, "#C9CDD3") for m in agg.index]
    
    fig = go.Figure(go.Bar(
        x=agg.values,
        y=agg.index,
        orientation="h",
        marker_color=colors,
        text=[f"CHF {v:,.0f}" for v in agg.values],
        textposition="auto",
        hovertemplate="%{y}: CHF %{x:,.0f}<extra></extra>"
    ))
    
    fig = apply_default_layout(fig, "")
    fig.update_layout(xaxis_title="Kosten (CHF)")
    return fig

def create_circularity_donut(element_df: pd.DataFrame) -> go.Figure:
    if element_df is None or element_df.empty or "status" not in element_df.columns or "volume_m3" not in element_df.columns:
        return _empty_fig("Status oder Volumen fehlen")
        
    df_m = element_df.dropna(subset=["status", "volume_m3"]).copy()
    df_m["vol_num"] = pd.to_numeric(df_m["volume_m3"], errors="coerce").fillna(0)
    
    agg = df_m.groupby("status")["vol_num"].sum()
    if agg.sum() == 0:
        return _empty_fig("Volumen ist 0")
        
    fig = go.Figure(go.Pie(
        labels=agg.index.tolist(),
        values=agg.values.tolist(),
        hole=0.6,
        marker=dict(colors=[STATUS_COLORS.get(s, "#C9CDD3") for s in agg.index]),
        textinfo="label+percent",
        hovertemplate="%{label}<br>Volumen: %{value:,.1f} m³<br>Anteil: %{percent}<extra></extra>"
    ))
    
    bestand_pct = (agg.get("Bestand", 0) / agg.sum()) * 100
    fig.add_annotation(
        text=f"<b>{bestand_pct:.0f}%</b><br>Erhalt",
        x=0.5, y=0.5, font=dict(size=20), showarrow=False
    )
    
    fig.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False)
    return fig
