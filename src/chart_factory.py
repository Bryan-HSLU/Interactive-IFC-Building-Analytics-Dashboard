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
            font=dict(size=15, weight="bold", color=COLORS["text"]),
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


def _group_small_categories_df(df: pd.DataFrame, label_col: str, val_col: str, max_cats: int = 7) -> pd.DataFrame:
    """Groups tail categories into 'Sonstige' for a dataframe with label+value columns."""
    if len(df) <= max_cats:
        return df
    top = df.nlargest(max_cats, val_col)
    rest_val = df.iloc[max_cats:][val_col].sum()
    rest_row = pd.DataFrame([{label_col: "Sonstige", val_col: rest_val}])
    return pd.concat([top, rest_row], ignore_index=True)


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
            y=subset, name=cat, marker_color=color, boxmean=True,
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
            x=pivot.index, y=pivot[col], name=col, marker_color=color,
            hovertemplate=f"<b>%{{x}}</b><br>{col}: %{{y:.1f}} m²<extra></extra>",
        ))
    fig.update_layout(barmode="stack")
    apply_default_layout(fig, "Raumfläche nach Geschoss und Nutzung")
    fig.update_layout(yaxis_title="Fläche (m²)", xaxis_title="Geschoss")
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

    col = "volume_m3" if unit in ("m³", "m\u00b3") else "area_m2"
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


# ── Page 5: Impact & Costs ─────────────────────────────────────────────────────

def create_co2_treemap(element_df: pd.DataFrame) -> go.Figure:
    """Treemap of Embodied CO2 with color scale mapping to total value (higher CO2 = deeper color)."""
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO₂-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]
    if df.empty:
        return _empty_fig("Keine CO₂-Faktoren konnten zugeordnet werden")

    agg = df.groupby(["material", "ifc_class"])["co2e_total"].sum().reset_index()
    mat_totals = agg.groupby("material")["co2e_total"].sum().reset_index()

    labels, parents, values, ids = ["Gesamt"], [""], [0.0], ["root"]

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
        hovertemplate="<b>%{label}</b><br>CO₂e: %{value:,.0f} kg<br>Anteil: %{percentRoot:.1%}<extra></extra>",
        marker=dict(
            colorscale=[[0, "#EAEAEA"], [0.5, "#E28B65"], [1, "#A04C22"]],
            showscale=True,
            colorbar_title="CO₂e (kg)",
        ),
    ))
    apply_default_layout(fig, "CO₂e nach Material und IFC-Klasse")
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10))
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


# ── Page 2: Overview Charts ────────────────────────────────────────────────────

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


# ── Page 5: Expander Charts (Advanced Analytics) ───────────────────────────────

def create_waterfall_co2(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine CO₂-Daten verfügbar")

    df = element_df.dropna(subset=["co2e_total"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]
    if df.empty:
        return _empty_fig("Keine CO₂-Faktoren zugeordnet")

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
        hovertemplate="<b>%{x}</b><br>CO₂e: %{y:,.0f} kg<extra></extra>",
    ))
    apply_default_layout(fig, "CO₂e-Beitrag nach Material (Waterfall)")
    fig.update_layout(xaxis_title="Material", yaxis_title="CO₂e (kg)")
    return fig


def create_sankey_material(element_df: pd.DataFrame) -> go.Figure:
    if element_df.empty or "co2e_total" not in element_df.columns:
        return _empty_fig("Keine Daten für Sankey verfügbar")

    df = element_df.dropna(subset=["co2e_total", "material", "ifc_class"]).copy()
    df["co2e_total"] = pd.to_numeric(df["co2e_total"], errors="coerce")
    df = df[df["co2e_total"] > 0]
    if df.empty:
        return _empty_fig("Keine CO₂-Daten für Sankey")

    df["ifc_class"] = _group_small_categories(df["ifc_class"], 6)
    df["material"] = _group_small_categories(df["material"], 6)

    vol_series = pd.to_numeric(df.get("volume_m3", pd.Series(dtype=float)), errors="coerce").fillna(1)
    intensity = df["co2e_total"] / vol_series.replace(0, np.nan)
    df["bucket"] = pd.cut(
        intensity.fillna(0),
        bins=[-1, 100, 500, float("inf")],
        labels=["CO₂: Niedrig", "CO₂: Mittel", "CO₂: Hoch"],
    ).astype(str)

    materials = df["material"].unique().tolist()
    classes = df["ifc_class"].unique().tolist()
    buckets = ["CO₂: Niedrig", "CO₂: Mittel", "CO₂: Hoch"]
    nodes = materials + classes + buckets
    idx = {n: i for i, n in enumerate(nodes)}

    agg1 = df.groupby(["material", "ifc_class"])["co2e_total"].sum().reset_index()
    agg2 = df.groupby(["ifc_class", "bucket"])["co2e_total"].sum().reset_index()

    src, tgt, val, clr = [], [], [], []
    for _, r in agg1.iterrows():
        if r["material"] in idx and r["ifc_class"] in idx:
            src.append(idx[r["material"]]); tgt.append(idx[r["ifc_class"]])
            val.append(r["co2e_total"]); clr.append("rgba(46,125,107,0.3)")
    for _, r in agg2.iterrows():
        if r["ifc_class"] in idx and r["bucket"] in idx:
            src.append(idx[r["ifc_class"]]); tgt.append(idx[r["bucket"]])
            val.append(r["co2e_total"]); clr.append("rgba(217,123,79,0.25)")

    if not val:
        return _empty_fig("Keine Verbindungen für Sankey")

    node_colors = (
        [COLORS["primary"]] * len(materials) +
        [CATEGORICAL_COLORS[1]] * len(classes) +
        [COLORS["error_ok"], COLORS["error_warning"], COLORS["error_critical"]]
    )

    fig = go.Figure(go.Sankey(
        node=dict(label=nodes, color=node_colors, pad=15, thickness=15,
                  line=dict(color="white", width=0.5)),
        link=dict(source=src, target=tgt, value=val, color=clr,
                  hovertemplate="<b>%{source.label}</b> → <b>%{target.label}</b><br>CO₂e: %{value:,.0f} kg<extra></extra>"),
    ))
    apply_default_layout(fig, "Sankey: Material → IFC-Klasse → CO₂-Intensität")
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
            x=["Bestand", "Neubau"], y=[row["Bestand"], row["Neubau"]],
            mode="lines+markers+text", name=row["material"],
            line=dict(color=color, width=2), marker=dict(color=color, size=10),
            text=[f"{row['Bestand']:,.0f}", f"{row['Neubau']:,.0f}"],
            textposition=["middle left", "middle right"],
            textfont=dict(size=9, color=color),
            hovertemplate=f"<b>{row['material']}</b><br>%{{x}}: %{{y:,.0f}} kg CO₂e<extra></extra>",
        ))
    apply_default_layout(fig, "Slope Chart: CO₂e Bestand vs. Neubau")
    fig.update_layout(
        xaxis=dict(tickmode="array", tickvals=["Bestand", "Neubau"], title="Status"),
        yaxis_title="CO₂e (kg)",
    )
    return fig


# ── Internal Helper ────────────────────────────────────────────────────────────

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
