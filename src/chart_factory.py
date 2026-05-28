import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from src.constants import COLORS, STATUS_COLORS, CATEGORICAL_COLORS


def apply_default_layout(fig: go.Figure, title: str = None) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        title=dict(
            text=title,
            font=dict(size=16, color=COLORS["text"]),
            x=0,
            xanchor="left",
        ) if title else None,
        margin=dict(l=60, r=20, t=50 if title else 20, b=50),
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


def _assign_categorical_colors(categories: list) -> list:
    colors = []
    color_idx = 0
    for cat in categories:
        if cat in ("Unbekannt", "Sonstige"):
            colors.append(COLORS["unknown"])
        else:
            colors.append(CATEGORICAL_COLORS[color_idx % (len(CATEGORICAL_COLORS) - 1)])
            color_idx += 1
    return colors


def _group_small_categories(series: pd.Series, max_cats: int = 7) -> pd.Series:
    counts = series.value_counts()
    if len(counts) <= max_cats:
        return series
    top = counts.index[:max_cats].tolist()
    return series.apply(lambda x: x if x in top else "Sonstige")


# ── Page 3: Räume & Flächen ───────────────────────────────────────────────────

def create_room_boxplot(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten verfügbar")

    df = space_df.dropna(subset=["area_m2"]).copy()
    df["usage"] = df["usage"].fillna("Unbekannt")
    mean_val = df["area_m2"].mean()

    categories = sorted(df["usage"].unique(), key=lambda x: (x == "Unbekannt", x))
    fig = go.Figure()
    for i, cat in enumerate(categories):
        subset = df[df["usage"] == cat]["area_m2"]
        color = COLORS["unknown"] if cat == "Unbekannt" else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        fig.add_trace(go.Box(
            y=subset,
            name=cat,
            marker_color=color,
            boxmean=True,
            hovertemplate=f"<b>{cat}</b><br>Fläche: %{{y:.1f}} m²<extra></extra>",
        ))

    fig.add_hline(
        y=mean_val, line_dash="dash", line_color=COLORS["text_light"], line_width=1.5,
        annotation_text=f"Ø {mean_val:.1f} m²",
        annotation_position="top right",
        annotation_font=dict(size=11, color=COLORS["text_light"]),
    )
    apply_default_layout(fig, "Raumgrösse nach Nutzungstyp")
    fig.update_layout(yaxis_title="Fläche (m²)", showlegend=False)
    return fig


def create_room_stacked_bar(space_df: pd.DataFrame, storey_order: list = None) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten verfügbar")

    df = space_df.dropna(subset=["area_m2"]).copy()
    df["usage"] = _group_small_categories(df["usage"].fillna("Unbekannt"), 6)

    pivot = df.pivot_table(index="storey", columns="usage", values="area_m2", aggfunc="sum", fill_value=0)

    if storey_order:
        pivot = pivot.reindex([s for s in storey_order if s in pivot.index])

    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        color = COLORS["unknown"] if col in ("Unbekannt", "Sonstige") else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        fig.add_trace(go.Bar(
            x=pivot.index,
            y=pivot[col],
            name=col,
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:.1f}} m²<extra></extra>",
        ))

    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Raumfläche nach Geschoss und Nutzung")
    fig.update_layout(yaxis_title="Fläche (m²)", xaxis_title="Geschoss")
    return fig


def create_room_histogram(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten verfügbar")

    df = space_df.dropna(subset=["area_m2"])
    mean_val = df["area_m2"].mean()

    fig = go.Figure(go.Histogram(
        x=df["area_m2"],
        nbinsx=20,
        marker_color=COLORS["primary"],
        opacity=0.8,
        hovertemplate="Fläche: %{x:.0f}–%{x:.0f} m²<br>Anzahl: %{y}<extra></extra>",
    ))
    fig.add_vline(
        x=mean_val, line_dash="dash", line_color=COLORS["text_light"], line_width=1.5,
        annotation_text=f"Ø {mean_val:.1f} m²",
        annotation_position="top right",
        annotation_font=dict(size=11, color=COLORS["text_light"]),
    )
    apply_default_layout(fig, "Raumgrössenverteilung")
    fig.update_layout(xaxis_title="Fläche (m²)", yaxis_title="Anzahl Räume")
    return fig


# ── Page 4: Bauteile & Mengen ───────────────────────────────────────────────

def create_class_bar_horizontal(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty:
        return _empty_fig("Keine Elementdaten verfügbar")

    counts = element_df["ifc_class"].value_counts().reset_index()
    counts.columns = ["ifc_class", "count"]
    counts = counts.sort_values("count", ascending=True)

    colors = [COLORS["primary"]] * len(counts)

    fig = go.Figure(go.Bar(
        x=counts["count"],
        y=counts["ifc_class"],
        orientation="h",
        marker_color=colors,
        text=counts["count"],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Anzahl: %{x}<extra></extra>",
    ))
    apply_default_layout(fig, "Elemente pro IFC-Klasse")
    fig.update_layout(xaxis_title="Anzahl", yaxis_title="")
    return fig


def create_class_storey_stacked(element_df: pd.DataFrame, storey_order: list = None) -> go.Figure:
    if element_df.empty:
        return _empty_fig("Keine Elementdaten verfügbar")

    df = element_df.copy()
    df["ifc_class"] = _group_small_categories(df["ifc_class"], 7)

    pivot = df.pivot_table(index="storey", columns="ifc_class", aggfunc="size", fill_value=0)
    if storey_order:
        pivot = pivot.reindex([s for s in storey_order if s in pivot.index])

    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        color = COLORS["unknown"] if col == "Sonstige" else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        fig.add_trace(go.Bar(
            x=pivot.index,
            y=pivot[col],
            name=col,
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y}}<extra></extra>",
        ))

    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Elemente nach Geschoss und Klasse")
    fig.update_layout(xaxis_title="Geschoss", yaxis_title="Anzahl")
    return fig


def create_material_quantity_bar(element_df: pd.DataFrame, unit: str = "m³") -> go.Figure:
    if element_df.empty:
        return _empty_fig("Keine Elementdaten verfügbar")

    col = "volume_m3" if unit == "m³" else "area_m2"
    df = element_df.dropna(subset=[col]).copy()
    if df.empty:
        return _empty_fig("Keine Mengendaten verfügbar")

    agg = df.groupby("material")[col].sum().reset_index()
    agg.columns = ["material", "quantity"]
    agg = agg.sort_values("quantity", ascending=True)

    colors = [COLORS["unknown"] if m == "Unbekannt" else COLORS["primary"] for m in agg["material"]]

    fig = go.Figure(go.Bar(
        x=agg["quantity"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        hovertemplate=f"<b>%{{y}}</b><br>Menge: %{{x:.1f}} {unit}<extra></extra>",
    ))
    apply_default_layout(fig, f"Materialmenge ({unit})")
    fig.update_layout(xaxis_title=unit, yaxis_title="")
    return fig


def create_diverging_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "status" not in element_df.columns:
        return _empty_fig("Keine Statusdaten verfügbar")

    df = element_df.dropna(subset=["volume_m3"]).copy()
    neubau = df[df["status"] == "Neubau"].groupby("material")["volume_m3"].sum()
    abbruch = df[df["status"] == "Abbruch"].groupby("material")["volume_m3"].sum()

    materials = sorted(set(neubau.index) | set(abbruch.index))

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[neubau.get(m, 0) for m in materials],
        y=materials,
        name="Neubau",
        orientation="h",
        marker_color=COLORS["neubau"],
        hovertemplate="<b>%{y}</b><br>Neubau: %{x:.1f} m³<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=[-abbruch.get(m, 0) for m in materials],
        y=materials,
        name="Abbruch",
        orientation="h",
        marker_color=COLORS["abbruch"],
        hovertemplate="<b>%{y}</b><br>Abbruch: %{customdata:.1f} m³<extra></extra>",
        customdata=[abbruch.get(m, 0) for m in materials],
    ))
    fig.update_layout(barmode="relative")
    apply_default_layout(fig, "Neubau vs. Abbruch (m³)")
    fig.update_layout(xaxis_title="Volumen (m³)", yaxis_title="")
    return fig


# ── Page 5: Impact & Costs ─────────────────────────────────────────────────────

def create_co2_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO2-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    if df.empty:
        return _empty_fig("Keine CO2-Faktoren konnten zugeordnet werden")

    agg = df.groupby("material")["co2e_total"].sum().reset_index()
    agg.columns = ["material", "co2e"]
    agg = agg.sort_values("co2e", ascending=True)
    total_co2 = agg["co2e"].sum()
    agg["pct"] = (agg["co2e"] / total_co2 * 100).round(1) if total_co2 > 0 else 0.0

    fig = go.Figure(go.Bar(
        x=agg["co2e"],
        y=agg["material"],
        orientation="h",
        marker_color=COLORS["primary"],
        customdata=agg["pct"],
        hovertemplate="<b>%{y}</b><br>CO2e: %{x:,.0f} kg<br>Anteil: %{customdata:.1f}%<extra></extra>",
    ))
    apply_default_layout(fig, "CO2e nach Materialgruppe")
    fig.update_layout(xaxis_title="CO2e (kg)", yaxis_title="")
    return fig


def create_co2_treemap(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO2-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    if df.empty:
        return _empty_fig("Keine CO2-Faktoren konnten zugeordnet werden")

    agg = df.groupby(["material", "ifc_class"])["co2e_total"].sum().reset_index()
    agg = agg[agg["co2e_total"] > 0]

    mat_totals = agg.groupby("material")["co2e_total"].sum().reset_index()

    # fix #4: doppelte Initialisierung entfernt – direkt mit den korrekten Variablen starten
    labels, parents, values, ids = ["Gesamt"], [""], [0], ["root"]

    for _, row in mat_totals.iterrows():
        labels.append(row["material"])
        parents.append("Gesamt")
        values.append(row["co2e_total"])
        ids.append(row["material"])

    for _, row in agg.iterrows():
        labels.append(row["ifc_class"])
        parents.append(row["material"])
        values.append(row["co2e_total"])
        ids.append(f"{row['material']}__{row['ifc_class']}")

    fig = go.Figure(go.Treemap(
        ids=ids,
        labels=labels,
        parents=parents,
        values=values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>CO2e: %{value:,.0f} kg<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(
            colorscale=[[0, "#D5EEF0"], [0.5, "#1A7F8E"], [1, "#0D4A52"]],
            showscale=True,
            colorbar_title="CO2e (kg)",
        ),
    ))
    apply_default_layout(fig, "CO2e nach Material und IFC-Klasse")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def create_cost_heatmap(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "cost_chf" not in element_df.columns:
        return _empty_fig("Keine Kostendaten verfügbar")

    df = element_df.dropna(subset=["cost_chf"]).copy()
    if df.empty:
        return _empty_fig("Keine Kostenfaktoren konnten zugeordnet werden")

    df["ifc_class"] = _group_small_categories(df["ifc_class"], 8)
    pivot = df.pivot_table(index="storey", columns="ifc_class", values="cost_chf", aggfunc="sum", fill_value=0)

    z_text = [[f"{v:,.0f}" for v in row] for row in pivot.values] if pivot.size < 30 else None

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[[0, "#F5EFE6"], [1, "#A0522D"]],
        text=z_text,
        texttemplate="%{text}" if z_text else "",
        hovertemplate="Geschoss: %{y}<br>Klasse: %{x}<br>Kosten: CHF %{z:,.0f}<extra></extra>",
        colorbar_title="CHF",
    ))
    apply_default_layout(fig, "Kosten nach Geschoss × IFC-Klasse (CHF)")
    fig.update_layout(xaxis_title="IFC-Klasse", yaxis_title="Geschoss")
    return fig


def create_cost_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "cost_chf" not in element_df.columns:
        return _empty_fig("Keine Kostendaten verfügbar")

    df = element_df.dropna(subset=["cost_chf"]).copy()
    df["cost_chf"] = pd.to_numeric(df["cost_chf"], errors="coerce")
    df = df[df["cost_chf"] > 0]
    if df.empty:
        return _empty_fig("Keine Kostenfaktoren zugeordnet")

    agg = df.groupby("material")["cost_chf"].sum().reset_index()
    agg.columns = ["material", "cost"]
    agg = agg.sort_values("cost", ascending=True)
    total = agg["cost"].sum()
    agg["pct"] = (agg["cost"] / total * 100).round(1) if total > 0 else 0.0

    colors = [COLORS["unknown"] if m == "Unbekannt" else CATEGORICAL_COLORS[0] for m in agg["material"]]

    fig = go.Figure(go.Bar(
        x=agg["cost"],
        y=agg["material"],
        orientation="h",
        marker_color=colors,
        customdata=agg["pct"],
        hovertemplate="<b>%{y}</b><br>Kosten: CHF %{x:,.0f}<br>Anteil: %{customdata:.1f}%<extra></extra>",
    ))
    apply_default_layout(fig, "Kostentreiber nach Material")
    fig.update_layout(xaxis_title="CHF", yaxis_title="")
    return fig


# ── Page 6: Quality Check ────────────────────────────────────────────────────

def create_quality_gauge(score: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": COLORS["primary"]},
            "steps": [
                {"range": [0, 50], "color": "#F0DDD0"},
                {"range": [50, 80], "color": "#FDF3DC"},
                {"range": [80, 100], "color": "#D5EEF0"},
            ],
            "threshold": {
                "line": {"color": COLORS["error_warning"], "width": 4},
                "thickness": 0.75,
                "value": score,
            },
        },
        title={"text": "Modellqualität", "font": {"size": 16}},
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


def create_status_distribution(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "status" not in element_df.columns:
        return _empty_fig("Keine Statusdaten verfügbar")

    df = element_df.copy()
    df["ifc_class"] = _group_small_categories(df["ifc_class"], 8)
    pivot = df.pivot_table(index="ifc_class", columns="status", aggfunc="size", fill_value=0)
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig = go.Figure()
    for status in pivot_pct.columns:
        color = STATUS_COLORS.get(status, COLORS["neutral"])
        fig.add_trace(go.Bar(
            x=pivot_pct.index,
            y=pivot_pct[status],
            name=status,
            marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{status}: %{{y:.1f}}%<extra></extra>",
        ))

    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Statusverteilung pro IFC-Klasse")
    fig.update_layout(xaxis_title="IFC-Klasse", yaxis_title="Anteil (%)")
    return fig


def create_pset_matrix_heatmap(pset_matrix: pd.DataFrame) -> go.Figure:
    if pset_matrix is None or pset_matrix.empty:
        return _empty_fig("Keine Pset-Daten verfügbar")

    z = (pset_matrix > 0).astype(int).values

    fig = go.Figure(go.Heatmap(
        z=z,
        x=pset_matrix.columns.tolist(),
        y=pset_matrix.index.tolist(),
        colorscale=[[0, "#ECF0F1"], [1, "#1A7F8E"]],
        showscale=False,
        hovertemplate="Klasse: %{y}<br>Pset: %{x}<br>%{text}<extra></extra>",
        text=[["Vorhanden" if v else "Fehlt" for v in row] for row in z],
    ))
    apply_default_layout(fig, "Pset-Verfügbarkeit nach IFC-Klasse")
    fig.update_layout(xaxis_title="Property Set", yaxis_title="IFC-Klasse")
    fig.update_xaxes(tickangle=45)
    return fig


# ── Page 3: Additional Charts ──────────────────────────────────────────────────

def create_room_sunburst(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty:
        return _empty_fig("Keine Raumdaten verfügbar")

    df = space_df.copy()
    df["storey"] = df.get("storey", pd.Series(dtype=str)).fillna("Unbekannt")
    df["usage"] = df.get("usage", pd.Series(dtype=str)).fillna("Unbekannt")

    if "area_m2" in df.columns:
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce").fillna(0)
        storey_totals = df.groupby("storey")["area_m2"].sum().reset_index()
        usage_totals = df.groupby(["storey", "usage"])["area_m2"].sum().reset_index()
        val_label = "m²"
    else:
        storey_totals = df.groupby("storey").size().reset_index(name="area_m2")
        usage_totals = df.groupby(["storey", "usage"]).size().reset_index(name="area_m2")
        val_label = "Räume"

    labels = ["Alle Räume"] + storey_totals["storey"].tolist() + usage_totals["usage"].tolist()
    ids = ["root"] + storey_totals["storey"].tolist() + [
        f"{r['storey']}__{r['usage']}" for _, r in usage_totals.iterrows()
    ]
    parents = [""] + ["Alle Räume"] * len(storey_totals) + usage_totals["storey"].tolist()
    values = [0.0] + storey_totals["area_m2"].tolist() + usage_totals["area_m2"].tolist()

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        insidetextorientation="radial",
        hovertemplate=f"<b>%{{label}}</b><br>{val_label}: %{{value:.1f}}<br>Anteil: %{{percentRoot:.1%}}<extra></extra>",
    ))
    apply_default_layout(fig, "Raumhierarchie: Geschoss → Nutzung")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def create_room_scatter(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten verfügbar")

    df = space_df.dropna(subset=["area_m2"]).copy()
    y_col = next(
        (c for c in ["height_m", "volume_m3"] if c in df.columns and df[c].notna().any()), None
    )
    if y_col is None:
        return _empty_fig("Keine Höhen- oder Volumendaten verfügbar")

    df = df.dropna(subset=[y_col])
    df["usage"] = df["usage"].fillna("Unbekannt")

    usages = sorted(df["usage"].unique(), key=lambda x: (x == "Unbekannt", x))
    fig = go.Figure()
    for i, usage in enumerate(usages):
        sub = df[df["usage"] == usage]
        color = COLORS["unknown"] if usage == "Unbekannt" else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        names = sub["name"].astype(str).tolist() if "name" in sub.columns else ["Raum"] * len(sub)
        y_unit = "m" if y_col == "height_m" else "m³"
        y_label_hover = "Höhe" if y_col == "height_m" else "Volumen"
        fig.add_trace(go.Scatter(
            x=sub["area_m2"], y=sub[y_col],
            mode="markers", name=usage,
            marker=dict(color=color, size=7, opacity=0.7, line=dict(width=0.5, color="white")),
            text=names,
            hovertemplate=f"<b>%{{text}}</b><br>Fläche: %{{x:.1f}} m²<br>{y_label_hover}: %{{y:.2f}} {y_unit}<extra></extra>",
        ))

    y_axis_label = "Raumhöhe (m)" if y_col == "height_m" else "Volumen (m³)"
    apply_default_layout(fig, "Scatter: Raumfläche vs. Raumhöhe")
    fig.update_layout(xaxis_title="Fläche (m²)", yaxis_title=y_axis_label)
    return fig


def create_room_bubble(space_df: pd.DataFrame) -> go.Figure:
    if space_df.empty or "area_m2" not in space_df.columns:
        return _empty_fig("Keine Raumdaten verfügbar")

    y_col = next(
        (c for c in ["height_m", "volume_m3"] if c in space_df.columns and space_df[c].notna().any()), None
    )
    if y_col is None:
        return _empty_fig("Keine Höhendaten für Bubble Chart")

    size_col = None
    if y_col != "volume_m3" and "volume_m3" in space_df.columns and space_df["volume_m3"].notna().any():
        size_col = "volume_m3"

    df = space_df.dropna(subset=["area_m2", y_col]).copy()
    df["usage"] = df["usage"].fillna("Unbekannt")
    if df.empty:
        return _empty_fig("Keine ausreichenden Daten")

    if size_col:
        df[size_col] = pd.to_numeric(df[size_col], errors="coerce").fillna(0)
        max_sz = df[size_col].max() or 1
        df["bubble_size"] = (df[size_col] / max_sz * 35 + 6).clip(6, 45)
    else:
        df["bubble_size"] = 12

    usages = sorted(df["usage"].unique(), key=lambda x: (x == "Unbekannt", x))
    fig = go.Figure()
    for i, usage in enumerate(usages):
        sub = df[df["usage"] == usage]
        color = COLORS["unknown"] if usage == "Unbekannt" else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        names = sub["name"].astype(str).tolist() if "name" in sub.columns else ["Raum"] * len(sub)
        size_tip = "<br>Volumen: %{marker.size:.1f} m³" if size_col else ""
        fig.add_trace(go.Scatter(
            x=sub["area_m2"], y=sub[y_col],
            mode="markers", name=usage,
            marker=dict(color=color, size=sub["bubble_size"], opacity=0.55,
                        line=dict(width=0.5, color="white"), sizemode="diameter"),
            text=names,
            hovertemplate=f"<b>%{{text}}</b><br>Fläche: %{{x:.1f}} m²<br>Höhe: %{{y:.2f}} m{size_tip}<extra></extra>",
        ))

    y_label = "Raumhöhe (m)" if y_col == "height_m" else "Volumen (m³)"
    apply_default_layout(fig, "Bubble Chart: Fläche × Höhe × Volumen")
    fig.update_layout(xaxis_title="Fläche (m²)", yaxis_title=y_label)
    return fig


# ── Page 4: Additional Charts ──────────────────────────────────────────────────

def create_grouped_bar(element_df: pd.DataFrame, mode: str = "neubau") -> go.Figure:
    if element_df.empty or "volume_m3" not in element_df.columns:
        return _empty_fig("Keine Volumendaten verfügbar")

    df = element_df.dropna(subset=["volume_m3"]).copy()
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")
    df = df.dropna(subset=["volume_m3"])
    if df.empty:
        return _empty_fig("Keine Daten verfügbar")

    if mode == "umbau" and "status" in df.columns:
        top_mats = df.groupby("material")["volume_m3"].sum().nlargest(8).index
        df = df[df["material"].isin(top_mats)]
        pivot = df.pivot_table(index="material", columns="status", values="volume_m3", aggfunc="sum", fill_value=0)
        title = "Volumen nach Material und Status (Umbau)"
        get_color = lambda col, _: STATUS_COLORS.get(col, COLORS["neutral"])
    else:
        df["ifc_class"] = _group_small_categories(df["ifc_class"], 6)
        top_mats = df.groupby("material")["volume_m3"].sum().nlargest(5).index
        df["material_grp"] = df["material"].apply(lambda x: x if x in top_mats else "Sonstige")
        pivot = df.pivot_table(index="ifc_class", columns="material_grp", values="volume_m3", aggfunc="sum", fill_value=0)
        title = "Volumen nach IFC-Klasse und Material"
        cols_list = list(pivot.columns)
        get_color = lambda col, i: (COLORS["unknown"] if col in ("Unbekannt", "Sonstige")
                                    else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)])

    if pivot.empty:
        return _empty_fig("Keine Daten für Grouped Bar")

    fig = go.Figure()
    for i, col in enumerate(pivot.columns):
        color = get_color(col, i)
        fig.add_trace(go.Bar(
            x=pivot.index, y=pivot[col], name=col, marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:.1f}} m³<extra></extra>",
        ))
    fig.update_layout(barmode="group")
    apply_default_layout(fig, title)
    fig.update_layout(xaxis_title="", yaxis_title="Volumen (m³)")
    return fig


def create_element_treemap(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "volume_m3" not in element_df.columns:
        return _empty_fig("Keine Volumendaten verfügbar")

    df = element_df.dropna(subset=["volume_m3"]).copy()
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")
    df = df[df["volume_m3"] > 0]
    if df.empty:
        return _empty_fig("Keine positiven Volumenwerte")

    df["ifc_class"] = _group_small_categories(df["ifc_class"], 8)
    agg = df.groupby(["material", "ifc_class"])["volume_m3"].sum().reset_index()
    agg = agg[agg["volume_m3"] > 0]
    if agg.empty:
        return _empty_fig("Keine Daten für Treemap")

    mat_totals = agg.groupby("material")["volume_m3"].sum().reset_index()
    labels, parents, values, ids = ["Gesamt"], [""], [0.0], ["root"]

    for _, r in mat_totals.iterrows():
        labels.append(r["material"]); parents.append("Gesamt")
        values.append(r["volume_m3"]); ids.append(r["material"])

    for _, r in agg.iterrows():
        labels.append(r["ifc_class"]); parents.append(r["material"])
        values.append(r["volume_m3"]); ids.append(f"{r['material']}__{r['ifc_class']}")

    fig = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>Volumen: %{value:.1f} m³<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(colorscale=[[0, "#D6DCE8"], [1, "#34495E"]]),
    ))
    apply_default_layout(fig, "Treemap: Volumen nach Material und IFC-Klasse")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    return fig


def create_volume_violin(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "volume_m3" not in element_df.columns:
        return _empty_fig("Keine Volumendaten verfügbar")

    df = element_df.dropna(subset=["volume_m3"]).copy()
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")
    df = df[df["volume_m3"] > 0]
    if df.empty:
        return _empty_fig("Keine positiven Volumenwerte")

    df["ifc_class"] = _group_small_categories(df["ifc_class"], 7)
    fig = go.Figure()
    for i, cls in enumerate(sorted(df["ifc_class"].unique())):
        sub = df[df["ifc_class"] == cls]["volume_m3"]
        if len(sub) < 2:
            continue
        color = CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        fig.add_trace(go.Violin(
            y=sub, x0=cls, name=cls,
            fillcolor=color, line_color=color, opacity=0.7,
            meanline_visible=True, box_visible=True, points="outliers",
            hovertemplate=f"<b>{cls}</b><br>Volumen: %{{y:.3f}} m³<extra></extra>",
        ))

    apply_default_layout(fig, "Volumenverteilung nach IFC-Klasse (Violin)")
    fig.update_layout(yaxis_title="Volumen (m³)", showlegend=False, yaxis_type="log")
    return fig


def create_volume_histogram(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "volume_m3" not in element_df.columns:
        return _empty_fig("Keine Volumendaten verfügbar")

    df = element_df.dropna(subset=["volume_m3"]).copy()
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")
    df = df[df["volume_m3"] > 0]
    if df.empty:
        return _empty_fig("Keine positiven Volumenwerte")

    median_val = df["volume_m3"].median()
    mean_val = df["volume_m3"].mean()

    fig = go.Figure(go.Histogram(
        x=df["volume_m3"], nbinsx=25,
        marker_color=CATEGORICAL_COLORS[4], opacity=0.8,
        hovertemplate="Volumen: %{x:.2f} m³<br>Anzahl: %{y}<extra></extra>",
    ))
    fig.add_vline(x=median_val, line_dash="solid", line_color=COLORS["primary"], line_width=2,
                  annotation_text=f"Median: {median_val:.2f}",
                  annotation_position="top right",
                  annotation_font=dict(size=11, color=COLORS["primary"]))
    fig.add_vline(x=mean_val, line_dash="dash", line_color=COLORS["text_light"], line_width=1.5,
                  annotation_text=f"Ø {mean_val:.2f}",
                  annotation_position="top left",
                  annotation_font=dict(size=11, color=COLORS["text_light"]))
    apply_default_layout(fig, "Volumenverteilung (Histogramm)")
    fig.update_layout(xaxis_title="Volumen (m³)", yaxis_title="Anzahl Elemente")
    return fig


def create_raincloud_plot(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "volume_m3" not in element_df.columns:
        return _empty_fig("Keine Volumendaten verfügbar")

    df = element_df.dropna(subset=["volume_m3", "material"]).copy()
    df["volume_m3"] = pd.to_numeric(df["volume_m3"], errors="coerce")
    df = df[df["volume_m3"] > 0]
    if df.empty:
        return _empty_fig("Keine Daten verfügbar")

    top_mats = df.groupby("material")["volume_m3"].sum().nlargest(6).index.tolist()
    df = df[df["material"].isin(top_mats)]

    fig = go.Figure()
    for i, mat in enumerate(top_mats):
        sub = df[df["material"] == mat]["volume_m3"]
        if len(sub) < 3:
            continue
        color = COLORS["unknown"] if mat == "Unbekannt" else CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        sample = sub.sample(min(len(sub), 200), random_state=42)
        fig.add_trace(go.Violin(
            y=sample, x0=mat, name=mat,
            side="positive", fillcolor=color, line_color=color,
            opacity=0.6, meanline_visible=True, box_visible=True,
            points="all", jitter=0.35, pointpos=-1.1,
            marker=dict(color=color, size=4, opacity=0.35),
            hovertemplate=f"<b>{mat}</b><br>Volumen: %{{y:.3f}} m³<extra></extra>",
        ))

    apply_default_layout(fig, "Raincloud: Volumenverteilung Top-Materialien")
    fig.update_layout(yaxis_title="Volumen (m³)", showlegend=False)
    return fig


# ── Page 5: Additional Charts ──────────────────────────────────────────────────

def create_waterfall_co2(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO2-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]
    if df.empty:
        return _empty_fig("Keine CO2-Faktoren zugeordnet")

    agg = df.groupby("material")["co2e_total"].sum().reset_index()
    agg.columns = ["material", "co2e"]
    agg = agg.sort_values("co2e", ascending=False)

    if len(agg) > 8:
        top = agg.head(8)
        rest_val = agg.iloc[8:]["co2e"].sum()
        agg = pd.concat([top, pd.DataFrame([{"material": "Sonstige", "co2e": rest_val}])], ignore_index=True)

    x = agg["material"].tolist() + ["Gesamt"]
    y = agg["co2e"].tolist() + [agg["co2e"].sum()]
    measures = ["relative"] * len(agg) + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=x, y=y,
        text=[f"{v:,.0f}" for v in y], textposition="outside",
        connector=dict(line=dict(color=COLORS["grid"], width=1, dash="dot")),
        increasing=dict(marker=dict(color=COLORS["abbruch"])),
        decreasing=dict(marker=dict(color=COLORS["neubau"])),
        totals=dict(marker=dict(color=COLORS["primary"])),
        hovertemplate="<b>%{x}</b><br>CO2e: %{y:,.0f} kg<extra></extra>",
    ))
    apply_default_layout(fig, "CO2e-Beitrag nach Material (Waterfall)")
    fig.update_layout(xaxis_title="", yaxis_title="CO2e (kg)")
    return fig


def create_sankey_material(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine Daten für Sankey verfügbar")

    df = element_df.dropna(subset=["co2e_total", "material", "ifc_class"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]
    if df.empty:
        return _empty_fig("Keine CO2-Daten für Sankey")

    df["ifc_class"] = _group_small_categories(df["ifc_class"], 6)
    df["material"] = _group_small_categories(df["material"], 6)

    vol_series = pd.to_numeric(df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").fillna(1)
    intensity = df["co2e_total"] / vol_series.replace(0, np.nan)
    df["bucket"] = pd.cut(
        intensity.fillna(0),
        bins=[-1, 100, 500, float("inf")],
        labels=["CO2: Niedrig", "CO2: Mittel", "CO2: Hoch"],
    ).astype(str)

    materials = df["material"].unique().tolist()
    classes = df["ifc_class"].unique().tolist()
    buckets = ["CO2: Niedrig", "CO2: Mittel", "CO2: Hoch"]
    nodes = materials + classes + buckets
    idx = {n: i for i, n in enumerate(nodes)}

    agg1 = df.groupby(["material", "ifc_class"])["co2e_total"].sum().reset_index()
    agg2 = df.groupby(["ifc_class", "bucket"])["co2e_total"].sum().reset_index()

    src, tgt, val, clr = [], [], [], []
    for _, r in agg1.iterrows():
        if r["material"] in idx and r["ifc_class"] in idx:
            src.append(idx[r["material"]]); tgt.append(idx[r["ifc_class"]])
            val.append(r["co2e_total"]); clr.append("rgba(26,127,142,0.3)")
    for _, r in agg2.iterrows():
        if r["ifc_class"] in idx and r["bucket"] in idx:
            src.append(idx[r["ifc_class"]]); tgt.append(idx[r["bucket"]])
            val.append(r["co2e_total"]); clr.append("rgba(160,82,45,0.25)")

    if not val:
        return _empty_fig("Keine Verbindungen für Sankey")

    node_colors = (
        [COLORS["primary"]] * len(materials) +
        [CATEGORICAL_COLORS[2]] * len(classes) +
        [COLORS["error_ok"], COLORS["error_warning"], COLORS["error_critical"]]
    )

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, color=node_colors, pad=15, thickness=15,
                  line=dict(color="white", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color=clr,
                  hovertemplate="<b>%{source.label}</b> → <b>%{target.label}</b><br>CO2e: %{value:,.0f} kg<extra></extra>"),
    ))
    apply_default_layout(fig, "Sankey: Material → IFC-Klasse → CO2-Intensität")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=440)
    return fig


def create_slope_co2(element_df: pd.DataFrame) -> go.Figure:
    if (element_df.empty or "co2e_total" not in element_df.columns
            or "status" not in element_df.columns):
        return _empty_fig("Nur im Umbau-Modus verfügbar")

    df = element_df.dropna(subset=["co2e_total", "status"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["status"].isin(["Bestand", "Neubau"])]
    if df.empty:
        return _empty_fig("Keine Bestand/Neubau-Daten verfügbar")

    agg = df.groupby(["material", "status"])["co2e_total"].sum().unstack(fill_value=0).reset_index()
    for col in ["Bestand", "Neubau"]:
        if col not in agg.columns:
            agg[col] = 0.0

    total_ser = agg["Bestand"] + agg["Neubau"]
    agg = agg.iloc[total_ser.nlargest(8).index].reset_index(drop=True)

    fig = go.Figure()
    for i, row in agg.iterrows():
        color = CATEGORICAL_COLORS[i % (len(CATEGORICAL_COLORS) - 1)]
        fig.add_trace(go.Scatter(
            x=["Bestand", "Neubau"],
            y=[row["Bestand"], row["Neubau"]],
            mode="lines+markers+text", name=row["material"],
            line=dict(color=color, width=2), marker=dict(color=color, size=10),
            text=[f"{row['Bestand']:,.0f}", f"{row['Neubau']:,.0f}"],
            textposition=["middle left", "middle right"],
            textfont=dict(size=9, color=color),
            hovertemplate=f"<b>{row['material']}</b><br>%{{x}}: %{{y:,.0f}} kg CO2e<extra></extra>",
        ))

    apply_default_layout(fig, "Slope Chart: CO2e Bestand vs. Neubau")
    fig.update_layout(
        xaxis=dict(tickmode="array", tickvals=["Bestand", "Neubau"], title=""),
        yaxis_title="CO2e (kg)",
    )
    return fig


# ── Page 6: Additional Charts ──────────────────────────────────────────────────

def create_upset_plot(error_df: pd.DataFrame) -> go.Figure:
    from plotly.subplots import make_subplots

    if error_df is None or error_df.empty:
        return _empty_fig("Keine Fehlerdaten verfügbar")
    if "element_id" not in error_df.columns or "error_type" not in error_df.columns:
        return _empty_fig("Fehlerdaten unvollständig")

    pivot = error_df.pivot_table(
        index="element_id", columns="error_type", aggfunc="size", fill_value=0
    ).clip(0, 1)
    if pivot.empty:
        return _empty_fig("Keine Daten")

    error_types = pivot.columns.tolist()
    n_errors = len(error_types)
    error_labels = [e.replace("missing_", "Kein ").replace("_", " ").title() for e in error_types]

    pivot["combo"] = pivot[error_types].apply(lambda r: tuple(r.tolist()), axis=1)
    counts = (pivot.groupby("combo").size().reset_index(name="n")
              .sort_values("n", ascending=False).head(8))
    n_combos = len(counts)

    set_sizes = pivot[error_types].sum().reset_index()
    set_sizes.columns = ["error_type", "count"]

    fig = make_subplots(
        rows=2, cols=2,
        row_heights=[0.55, 0.45], column_widths=[0.65, 0.35],
        vertical_spacing=0.04, horizontal_spacing=0.06,
        subplot_titles=["Schnittmenge-Grösse", "Set-Grössen (gesamt)", "Schnittmengen-Matrix", ""],
    )

    bar_colors = [
        COLORS["error_critical"] if r["n"] > 10 else
        COLORS["error_warning"] if r["n"] > 3 else COLORS["primary"]
        for _, r in counts.iterrows()
    ]
    fig.add_trace(go.Bar(
        x=list(range(n_combos)), y=counts["n"].tolist(),
        marker_color=bar_colors, text=counts["n"].tolist(), textposition="outside",
        showlegend=False, hovertemplate="Kombination %{x}<br>Anzahl: %{y}<extra></extra>",
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=set_sizes["count"].tolist(), y=error_labels,
        orientation="h", marker_color=COLORS["error_warning"],
        showlegend=False, hovertemplate="%{y}: %{x} Elemente<extra></extra>",
    ), row=1, col=2)

    bg_x = [i for i in range(n_combos) for _ in range(n_errors)]
    bg_y = [j for _ in range(n_combos) for j in range(n_errors)]
    fig.add_trace(go.Scatter(
        x=bg_x, y=bg_y, mode="markers",
        marker=dict(color="#DCDCDC", size=10, line=dict(color="#bbb", width=1)),
        showlegend=False, hoverinfo="skip",
    ), row=2, col=1)

    for i, (_, row_data) in enumerate(counts.iterrows()):
        combo = row_data["combo"]
        active_j = [j for j, v in enumerate(combo) if v == 1]
        if len(active_j) > 1:
            fig.add_trace(go.Scatter(
                x=[i] * len(active_j), y=active_j, mode="lines",
                line=dict(color=COLORS["error_critical"], width=4),
                showlegend=False, hoverinfo="skip",
            ), row=2, col=1)
        if active_j:
            fig.add_trace(go.Scatter(
                x=[i] * len(active_j), y=active_j, mode="markers",
                marker=dict(color=COLORS["error_critical"], size=12),
                showlegend=False, hoverinfo="skip",
            ), row=2, col=1)

    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_yaxes(
        tickmode="array", tickvals=list(range(n_errors)), ticktext=error_labels,
        row=2, col=1,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
        title=dict(text="UpSet Plot: Fehler-Kombinationen", font=dict(size=16), x=0, xanchor="left"),
        height=520, showlegend=False,
        margin=dict(l=60, r=20, t=80, b=20),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
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
