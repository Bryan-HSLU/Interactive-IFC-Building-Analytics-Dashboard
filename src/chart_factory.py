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


# ── Page 3: Räume & Flächen ────────────────────────────────────────────────

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


# ── Page 4: Bauteile & Mengen ──────────────────────────────────────────────

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


# ── Page 5: Impact & Costs ─────────────────────────────────────────────────

def create_co2_bar(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO2-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    if df.empty:
        return _empty_fig("Keine CO2-Faktoren konnten zugeordnet werden")

    agg = df.groupby("material")["co2e_total"].sum().reset_index()
    agg.columns = ["material", "co2e"]
    agg = agg.sort_values("co2e", ascending=True)

    fig = go.Figure(go.Bar(
        x=agg["co2e"],
        y=agg["material"],
        orientation="h",
        marker_color=COLORS["primary"],
        hovertemplate="<b>%{y}</b><br>CO2e: %{x:,.0f} kg<extra></extra>",
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

    labels = ["Gesamt"] + agg["material"].unique().tolist() + agg["material"].tolist()
    parents = [""] + ["Gesamt"] * len(agg["material"].unique()) + agg["material"].tolist()
    values = [0] + [agg[agg["material"] == m]["co2e_total"].sum() for m in agg["material"].unique()] + agg["co2e_total"].tolist()
    ids = ["Gesamt"] + agg["material"].unique().tolist() + [f"{r['material']}_{r['ifc_class']}" for _, r in agg.iterrows()]

    # Rebuild properly
    mat_totals = agg.groupby("material")["co2e_total"].sum().reset_index()
    all_labels, all_parents, all_values, all_ids = ["Gesamt"], [""], [0], ["root"]

    for _, row in mat_totals.iterrows():
        all_labels.append(row["material"])
        all_parents.append("Gesamt")
        all_values.append(row["co2e_total"])
        all_ids.append(row["material"])

    for _, row in agg.iterrows():
        all_labels.append(row["ifc_class"])
        all_parents.append(row["material"])
        all_values.append(row["co2e_total"])
        all_ids.append(f"{row['material']}__{row['ifc_class']}")

    fig = go.Figure(go.Treemap(
        ids=all_ids,
        labels=all_labels,
        parents=all_parents,
        values=all_values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>CO2e: %{value:,.0f} kg<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(
            colorscale=[[0, "#27AE60"], [0.5, "#F1C40F"], [1, "#E74C3C"]],
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
        colorscale=[[0, "#FFFFFF"], [1, "#2980B9"]],
        text=z_text,
        texttemplate="%{text}" if z_text else "",
        hovertemplate="Geschoss: %{y}<br>Klasse: %{x}<br>Kosten: CHF %{z:,.0f}<extra></extra>",
        colorbar_title="CHF",
    ))
    apply_default_layout(fig, "Kosten nach Geschoss × IFC-Klasse (CHF)")
    fig.update_layout(xaxis_title="IFC-Klasse", yaxis_title="Geschoss")
    return fig


# ── Page 6: Quality Check ──────────────────────────────────────────────────

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
                {"range": [50, 80], "color": "#FCF3CF"},
                {"range": [80, 100], "color": "#D5F5E3"},
            ],
            "threshold": {
                "line": {"color": COLORS["error_critical"], "width": 4},
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

    # Convert to percentages
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

    # Normalize: 0 = missing, 1 = present
    z = (pset_matrix > 0).astype(int).values

    fig = go.Figure(go.Heatmap(
        z=z,
        x=pset_matrix.columns.tolist(),
        y=pset_matrix.index.tolist(),
        colorscale=[[0, "#E74C3C"], [1, "#27AE60"]],
        showscale=False,
        hovertemplate="Klasse: %{y}<br>Pset: %{x}<br>%{text}<extra></extra>",
        text=[["Vorhanden" if v else "Fehlt" for v in row] for row in z],
    ))
    apply_default_layout(fig, "Pset-Verfügbarkeit nach IFC-Klasse")
    fig.update_layout(xaxis_title="Property Set", yaxis_title="IFC-Klasse")
    fig.update_xaxes(tickangle=45)
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
