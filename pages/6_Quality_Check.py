import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.state_manager import (
    init_session_state,
    get_element_df,
    get_space_df,
    get_quality_data,
)
from src.filters import render_sidebar, render_cross_filter_reset
from src.chart_factory import create_pset_lollipop_chart, create_quality_radar
from src.quality_checker import build_pset_matrix
from src.constants import COLORS, STATUS_SHAPES

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

element_df = get_element_df(filtered=True)
space_df = get_space_df(filtered=True)

from src.quality_checker import check_quality, calculate_quality_score
error_df, quality_summary = check_quality(element_df, space_df, mode)
quality_summary["score"] = calculate_quality_score(quality_summary)

if not quality_summary:
    st.title("Quality Check")
    st.warning("No quality data available.")
    st.stop()

# Resolve metrics
score = quality_summary.get("score", 0)
error_counts = quality_summary.get("error_counts", {})
total_elements = quality_summary.get("total_elements", 0)
total_errors = sum(error_counts.values())

st.title("✅ Model Quality")

with st.expander("ℹ️ What does this page check?", expanded=False):
    st.markdown("""
    The quality check evaluates how complete and correct the IFC model is.
    Certain attributes are required for calculations (CO₂, costs, quantities):
    - **Storey**: Every component must be assigned to a floor.
    - **Material**: Without material assignment, KBOB calculation (CO₂, costs) is not possible.
    - **Quantities**: Volume or area required for all quantity take-offs.
    - **Psets** (Property Sets): Structured IFC attributes exchanged between discipline models.
    - **Zero Volume**: Elements with volume ≤ 0 indicate modelling errors.
    - **Duplicate GUIDs**: Duplicate element identifiers corrupt downstream analysis.
    - **Orphaned Elements**: Elements without storey assignment cannot be placed in context.

    **Quality Score** = proportion of elements without critical errors (0–100 %).
    """)

_MSG_MAP = {
    "missing_storey": "Elements without storey assignment",
    "missing_material": "Elements without material",
    "missing_quantity": "Elements without quantity data",
    "missing_usage": "Rooms without usage type",
    "missing_status": "Elements without status",
    "zero_volume": "Elements with zero/negative volume",
    "duplicate_guid": "Elements with duplicate GUID",
    "orphaned_element": "Elements without storey (orphaned)",
}
if total_errors > 0 and error_counts:
    worst_key = max(error_counts, key=error_counts.get)
    st.caption(f"{error_counts[worst_key]:,} {_MSG_MAP.get(worst_key, 'errors')} — quantities uncertain".replace(",", "'"))
else:
    st.caption("Model is error-free and consistent.")

CF_KEYS = ["cf_page6_error_cat"]
render_cross_filter_reset("page6", CF_KEYS)

def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", "'")

if "selected_fehler" not in st.session_state:
    st.session_state["selected_fehler"] = None

INDICATOR_CONFIG = [
    ("missing_storey", "No Storey", "critical"),
    ("missing_material", "No Material", "critical"),
    ("missing_quantity", "No Quantities", "warning"),
    ("missing_usage", "No Usage (Rooms)", "warning"),
    ("zero_volume", "Zero Volume", "critical"),
    ("duplicate_guid", "Duplicate GUID", "critical"),
    ("orphaned_element", "Orphaned Element", "warning"),
]
if mode == "umbau":
    INDICATOR_CONFIG.append(("missing_status", "No Status", "warning"))

SEVERITY_COLORS = {"critical": COLORS["error_critical"], "warning": COLORS["error_warning"], "ok": COLORS["error_ok"]}
SEVERITY_LABELS = {"critical": f"{STATUS_SHAPES['critical']} Critical", "warning": f"{STATUS_SHAPES['warning']} Warning", "ok": f"{STATUS_SHAPES['ok']} OK"}

indicator_lookup = {}
for key, lbl, sev in INDICATOR_CONFIG:
    val = error_counts.get(key, 0)
    effective_sev = sev if val > 0 else "ok"
    indicator_lookup[lbl] = {
        "key": key, "value": val, "severity": sev,
        "effective_severity": effective_sev,
        "color": SEVERITY_COLORS[sev] if val > 0 else "#CCCCCC",
    }

rows_sorted = sorted(indicator_lookup.items(), key=lambda r: r[1]["value"], reverse=True)
labels = [r[0] for r in rows_sorted]
values = [r[1]["value"] for r in rows_sorted]
selected_fehler = st.session_state.get("selected_fehler")

bar_colors = []
for lbl in labels:
    info = indicator_lookup[lbl]
    if selected_fehler is None or lbl == selected_fehler:
        bar_colors.append(info["color"])
    else:
        bar_colors.append("#CCCCCC")

# ── Tabs ──
tab_overview, tab_pset, tab_struktur = st.tabs(["📊 Overview", "📋 Pset Coverage", "🔧 Structure"])

# ── Tab: Overview ──
with tab_overview:
    col_kpi, col_radar = st.columns([1, 1])
    with col_kpi:
        selected = st.session_state.get("selected_fehler")
        if selected and selected in indicator_lookup:
            fe_info = indicator_lookup[selected]
            fe_count = fe_info["value"]
            kpi_title = f"QUALITY WITHOUT<br>{selected.upper()}"
            kpi_value = round((total_elements - fe_count) / total_elements * 100, 1) if total_elements > 0 else 0
            kpi_subtitle = f"(Total: {score:.1f}%)"
        else:
            kpi_title = "MODEL QUALITY"
            kpi_value = score
            kpi_subtitle = ""

        kpi_bar_width = max(0.0, min(float(kpi_value), 100.0))
        kpi_bar_color = "#2E86AB" if kpi_value >= 80 else "#E07B39"
        subtitle_html = f'<div style="color:#999;font-size:12px;margin-top:12px;">{kpi_subtitle}</div>' if kpi_subtitle else ""
        st.markdown(
            f"""<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;
            padding:28px 24px 22px 24px;box-shadow:0 2px 8px rgba(0,0,0,0.06);
            text-align:center;height:380px;display:flex;flex-direction:column;justify-content:center;">
                <div style="color:#888;font-size:13px;font-weight:600;letter-spacing:0.05em;margin-bottom:8px;">{kpi_title}</div>
                <div style="font-size:72px;font-weight:800;color:#1A1A2E;line-height:1.0;margin-bottom:24px;">
                    {kpi_value:.1f}<span style="font-size:34px;font-weight:600;color:#888;">%</span></div>
                <div style="background:#F0F0F0;border-radius:999px;height:14px;width:100%;overflow:hidden;">
                    <div style="background:{kpi_bar_color};width:{kpi_bar_width}%;height:100%;border-radius:999px;"></div>
                </div>
                <div style="display:flex;justify-content:space-between;margin-top:6px;">
                    <span style="font-size:11px;color:#AAA;">0%</span>
                    <span style="font-size:11px;color:#AAA;">100%</span>
                </div>{subtitle_html}
            </div>""",
            unsafe_allow_html=True,
        )

    with col_radar:
        st.subheader("Quality Profile")
        st.caption("5-dimensional quality radar: coverage across key attributes.")
        st.plotly_chart(create_quality_radar(error_counts, total_elements), use_container_width=True, config={"displayModeBar": False})

    st.markdown("<br>", unsafe_allow_html=True)

    col_bar_full = st.columns(1)[0]
    with col_bar_full:
        st.subheader("Quality Indicators")
        with st.expander("ℹ️ What do the indicators mean?", expanded=False):
            st.markdown("""
            | Indicator | Meaning | Impact |
            |---|---|---|
            | **No Storey** | Component not assigned to a floor | CO₂ distribution per storey impossible |
            | **No Material** | No material name present | No KBOB calculation (CO₂, costs) |
            | **No Quantities** | No volume/area specified | Quantity take-off incomplete |
            | **No Usage (Rooms)** | IfcSpace without usage type | NFA distribution distorted |
            | **No Status** | No existing/new/demolition classification | Renovation balance uncalculable |
            | **Zero Volume** | Volume ≤ 0 | Modelling error — invalid geometry |
            | **Duplicate GUID** | Duplicate element identifier | Corrupt downstream analysis |
            | **Orphaned Element** | Element without storey | Cannot be placed in context |
            """)
        hover_texts = []
        for lbl in labels:
            info = indicator_lookup[lbl]
            val = info["value"]
            pct = round(val / total_elements * 100, 1) if total_elements > 0 else 0
            sev_label = SEVERITY_LABELS.get(info["effective_severity"], "OK")
            hover_texts.append(f"<b>{lbl}</b><br>Count: {val}<br>Share: {pct}%<br>Severity: {sev_label}")

        fig_hbar = go.Figure(go.Bar(
            x=values, y=labels, orientation="h",
            marker=dict(color=bar_colors, line=dict(color="rgba(0,0,0,0)", width=0)),
            text=[str(v) if v > 0 else "" for v in values],
            textposition="outside", textfont=dict(size=13, color="#1A1A2E"),
            hovertext=hover_texts, hoverinfo="text", cliponaxis=False,
        ))
        max_val = max(values) if values else 1
        fig_hbar.update_layout(
            margin=dict(t=10, b=10, l=10, r=60), height=360,
            xaxis=dict(title="Number of Errors", showgrid=True, gridcolor="#F0F0F0", zeroline=False, range=[0, max_val * 1.35]),
            yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, bargap=0.35,
            hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter, sans-serif"),
        )
        event_bar = st.plotly_chart(fig_hbar, use_container_width=True, on_select="rerun", key="quality_bar_chart")
        if event_bar and hasattr(event_bar, "selection") and event_bar.selection:
            points = event_bar.selection.get("points", [])
            if points:
                clicked_label = points[0].get("y")
                if clicked_label and clicked_label in indicator_lookup:
                    if selected_fehler == clicked_label:
                        st.session_state["selected_fehler"] = None
                        st.rerun()
                    else:
                        st.session_state["selected_fehler"] = clicked_label
                        st.rerun()

        if total_errors == 0:
            st.success(f"Model complete – all {_fmt(total_elements)} elements have mandatory fields filled.")
        else:
            st.warning(f"{_fmt(total_errors)} issues found across {_fmt(total_elements)} elements.")

    # Detail table on click
    if selected_fehler and selected_fehler in indicator_lookup:
        fe_info = indicator_lookup[selected_fehler]
        fe_key = fe_info["key"]
        fe_count = fe_info["value"]
        st.divider()
        if fe_count == 0:
            st.success(f"✓ No affected elements for «{selected_fehler}».")
        else:
            st.markdown(f"#### 🔍 Affected Elements – {selected_fehler}")
            if error_df is not None and not error_df.empty:
                filtered_errors = error_df[error_df["error_type"] == fe_key].copy()
                display_cols = {}
                for c in ["element_id", "ifc_class", "storey", "description"]:
                    if c in filtered_errors.columns:
                        display_cols[c] = {"element_id": "Element ID", "ifc_class": "IFC Class", "storey": "Storey", "description": "Error Description"}.get(c, c)
                display_df = filtered_errors.rename(columns=display_cols)
                show_cols = [v for v in display_cols.values() if v in display_df.columns]
                st.dataframe(display_df[show_cols], use_container_width=True, hide_index=True)
        if st.button("✕ Clear Selection", key="reset_fehler", use_container_width=True):
            st.session_state["selected_fehler"] = None
            st.rerun()

    # Errors per storey stacked bar
    if error_df is not None and not error_df.empty and "storey" in error_df.columns:
        st.divider()
        st.subheader("Errors per Storey")
        st.caption("Distribution of errors by storey and error type — identifies problem floors.")
        storey_err = error_df.groupby(["storey", "error_type"]).size().reset_index(name="count")
        err_types = sorted(storey_err["error_type"].unique())
        storeys = sorted(storey_err["storey"].dropna().unique())

        ERR_COLORS = {
            "missing_storey": COLORS["error_warning"],   # orange
            "missing_material": "#7B5EA7",               # purple — CB-safe, distinct from orange/red/blue
            "missing_quantity": COLORS["error_critical"],
            "missing_usage": COLORS["primary"],
            "missing_status": COLORS["primary"],
            "zero_volume": COLORS["error_critical"],
            "duplicate_guid": COLORS["error_critical"],
            "orphaned_element": COLORS["error_warning"],
        }

        fig_storey_err = go.Figure()
        for et in err_types:
            sub = storey_err[storey_err["error_type"] == et]
            storey_counts = {row["storey"]: row["count"] for _, row in sub.iterrows()}
            fig_storey_err.add_trace(go.Bar(
                name=et.replace("_", " ").title(),
                x=storeys,
                y=[storey_counts.get(s, 0) for s in storeys],
                marker_color=ERR_COLORS.get(et, "#CCCCCC"),
                hovertemplate=f"<b>{et}</b><br>Storey: %{{x}}<br>Count: %{{y}}<extra></extra>",
            ))
        fig_storey_err.update_layout(
            template="plotly_white",
            barmode="stack",
            xaxis_title="Storey",
            yaxis_title="Number of Errors",
            margin=dict(l=40, r=20, t=30, b=40),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=-0.3, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig_storey_err, use_container_width=True, config={"displayModeBar": False})

# ── Tab: Pset Coverage ──
with tab_pset:
    with st.expander("ℹ️ What are Psets?", expanded=False):
        st.markdown("""
        **Property Sets (Psets)** are structured attribute groups in IFC, e.g. `Pset_WallCommon`
        for walls with attributes like fire resistance, thermal transmittance etc.
        Complete Psets are a prerequisite for data exchange between discipline models (structural, MEP).
        """)
    if element_df is not None and not element_df.empty:
        pset_matrix = build_pset_matrix(element_df)
        if pset_matrix is not None and not pset_matrix.empty:
            total_psets = len(pset_matrix.columns)
            class_completeness = {}
            class_missing = {}
            for cls in pset_matrix.index:
                present = int((pset_matrix.loc[cls] > 0).sum())
                pct = present / total_psets * 100 if total_psets > 0 else 0
                class_completeness[cls] = round(pct, 1)
                class_missing[cls] = total_psets - present

            if "selected_klasse" not in st.session_state:
                st.session_state["selected_klasse"] = None

            col_lkpi, col_lchrt = st.columns([1, 2])
            with col_lkpi:
                sel_cls = st.session_state.get("selected_klasse")
                if sel_cls and sel_cls in class_completeness:
                    lkpi_title = f"PSET: {sel_cls}"
                    lkpi_val = class_completeness[sel_cls]
                    lkpi_sub = f"{class_missing[sel_cls]} of {total_psets} Psets missing"
                else:
                    lkpi_title = "PSET QUALITY (Avg)"
                    overall = sum(class_completeness.values()) / len(class_completeness) if class_completeness else 0
                    lkpi_val = round(overall, 1)
                    lkpi_sub = f"Avg over {len(class_completeness)} IFC classes"

                lkpi_bw = max(0.0, min(float(lkpi_val), 100.0))
                lkpi_bc = "#2E86AB" if lkpi_val >= 50 else "#E07B39"
                st.markdown(
                    f"""<div style="background:#FFFFFF;border:1px solid #E8E8E8;border-radius:12px;
                    padding:24px;box-shadow:0 2px 8px rgba(0,0,0,0.06);text-align:center;min-height:260px;
                    display:flex;flex-direction:column;justify-content:center;">
                        <div style="color:#888;font-size:12px;font-weight:600;margin-bottom:8px;word-break:break-word;">{lkpi_title}</div>
                        <div style="font-size:56px;font-weight:800;color:#1A1A2E;line-height:1.0;margin-bottom:16px;">
                            {lkpi_val:.1f}<span style="font-size:26px;color:#888;">%</span></div>
                        <div style="background:#F0F0F0;border-radius:999px;height:12px;width:100%;overflow:hidden;">
                            <div style="background:{lkpi_bc};width:{lkpi_bw}%;height:100%;border-radius:999px;"></div>
                        </div>
                        <div style="color:#999;font-size:12px;margin-top:10px;">{lkpi_sub}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                if sel_cls:
                    if st.button("↩ Full View", key="reset_klasse", use_container_width=True):
                        st.session_state["selected_klasse"] = None
                        st.rerun()

            with col_lchrt:
                fig_lollipop = create_pset_lollipop_chart(pset_matrix)
                event_lollipop = st.plotly_chart(fig_lollipop, use_container_width=True, on_select="rerun", key="lollipop_chart")
                if event_lollipop and hasattr(event_lollipop, "selection") and event_lollipop.selection:
                    pts = event_lollipop.selection.get("points", [])
                    if pts:
                        clicked_cls = pts[0].get("y")
                        if clicked_cls and clicked_cls in class_completeness:
                            if st.session_state.get("selected_klasse") != clicked_cls:
                                st.session_state["selected_klasse"] = clicked_cls
                                st.rerun()

            # Completeness matrix heatmap: IFC class × attribute
            st.divider()
            st.subheader("Attribute Completeness Matrix")
            st.caption("Heatmap: presence of key attributes per IFC class — blue = present, white = missing.")
            if "ifc_class" in element_df.columns:
                key_attrs = ["material", "volume_m3", "storey", "usage"]
                avail_attrs = [a for a in key_attrs if a in element_df.columns]
                if avail_attrs:
                    classes = sorted(element_df["ifc_class"].dropna().unique())
                    z_data = []
                    hover_data = []
                    for cls in classes:
                        sub = element_df[element_df["ifc_class"] == cls]
                        row_z = []
                        row_h = []
                        for attr in avail_attrs:
                            if attr == "material":
                                present = (~sub[attr].isin(["", "nan", "Unbekannt", "Unknown", None]) & sub[attr].notna()).sum()
                            else:
                                present = sub[attr].notna().sum()
                            pct = present / len(sub) * 100 if len(sub) > 0 else 0
                            row_z.append(round(pct, 1))
                            row_h.append(f"{pct:.0f}% ({present}/{len(sub)})")
                        z_data.append(row_z)
                        hover_data.append(row_h)

                    fig_attr_heatmap = go.Figure(go.Heatmap(
                        z=z_data,
                        x=avail_attrs,
                        y=classes,
                        colorscale=[[0, "#FFFFFF"], [0.5, "#A8D4E6"], [1, "#2E86AB"]],
                        zmin=0, zmax=100,
                        showscale=True,
                        colorbar=dict(title="% Present", ticksuffix="%"),
                        hovertemplate="Class: %{y}<br>Attribute: %{x}<br>%{text}<extra></extra>",
                        text=hover_data,
                    ))
                    fig_attr_heatmap.update_layout(
                        template="plotly_white",
                        xaxis=dict(title="Attribute", tickangle=0),
                        yaxis=dict(title="IFC Class", autorange="reversed"),
                        margin=dict(l=20, r=20, t=30, b=50),
                        height=max(300, len(classes) * 28),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_attr_heatmap, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("No Pset data available.")
    else:
        st.info("No element data available.")

# ── Tab: Structure ──
with tab_struktur:
    st.subheader("Structural Completeness")
    with st.expander("ℹ️ What is checked here?", expanded=False):
        st.markdown("""
        Additional checks that go beyond the basic errors:
        - **No Storey Assignment**: Elements where `storey` is missing or not recognised.
        - **No Component Type**: Elements without `type_name` — hinders filtering and analysis.
        - **No Material**: Share of elements without material assignment (separately by IFC class).
        """)

    if element_df is not None and not element_df.empty:
        col_s1, col_s2, col_s3 = st.columns(3)

        # Check 1: no storey
        with col_s1:
            if "storey" in element_df.columns:
                no_storey = element_df[element_df["storey"].isin(["", "nan", "Nicht zugeordnet", None]) | element_df["storey"].isna()]
                n_no_storey = len(no_storey)
                pct_ns = n_no_storey / len(element_df) * 100 if len(element_df) > 0 else 0
                color_ns = COLORS["error_critical"] if pct_ns > 10 else (COLORS["error_warning"] if pct_ns > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_ns};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">NO STOREY</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_storey)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_ns:.1f}% of elements</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">Component not assigned to a floor — CO₂ distribution per storey impossible.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Column `storey` not available.")

        # Check 2: no type_name
        with col_s2:
            if "type_name" in element_df.columns:
                no_type = element_df[element_df["type_name"].isin(["", "nan", None]) | element_df["type_name"].isna()]
                n_no_type = len(no_type)
                pct_nt = n_no_type / len(element_df) * 100 if len(element_df) > 0 else 0
                color_nt = COLORS["error_critical"] if pct_nt > 20 else (COLORS["error_warning"] if pct_nt > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_nt};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">NO COMPONENT TYPE</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_type)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_nt:.1f}% of elements</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">No `type_name` — hinders filtering and component classification.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Column `type_name` not available.")

        # Check 3: no material
        with col_s3:
            if "material" in element_df.columns:
                no_mat = element_df[element_df["material"].isin(["", "nan", "Unbekannt", None]) | element_df["material"].isna()]
                n_no_mat = len(no_mat)
                pct_nm = n_no_mat / len(element_df) * 100 if len(element_df) > 0 else 0
                color_nm = COLORS["error_critical"] if pct_nm > 15 else (COLORS["error_warning"] if pct_nm > 0 else COLORS["error_ok"])
                st.markdown(
                    f"""<div style="background:#FFF;border-left:4px solid {color_nm};padding:16px 20px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);">
                        <div style="font-size:13px;color:#6B7280;font-weight:600;">NO MATERIAL</div>
                        <div style="font-size:40px;font-weight:800;color:#1A1A2E;">{_fmt(n_no_mat)}</div>
                        <div style="font-size:13px;color:#6B7280;">{pct_nm:.1f}% of elements</div>
                        <div style="font-size:12px;color:#9CA3AF;margin-top:6px;">No KBOB calculation (CO₂, costs) without material assignment.</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.info("Column `material` not available.")

        # Material coverage per IFC class
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("Material Coverage per IFC Class")
        st.caption("Share of elements with material assignment per IFC type — shows which classes are most sparsely modelled.")
        if "ifc_class" in element_df.columns and "material" in element_df.columns:
            _df_mc = element_df.copy()
            _df_mc["has_material"] = ~(_df_mc["material"].isin(["", "nan", "Unbekannt", None]) | _df_mc["material"].isna())
            _mc_agg = _df_mc.groupby("ifc_class")["has_material"].agg(["sum", "count"]).reset_index()
            _mc_agg.columns = ["ifc_class", "with_mat", "total"]
            _mc_agg["pct"] = (_mc_agg["with_mat"] / _mc_agg["total"] * 100).round(1)
            _mc_agg = _mc_agg.sort_values("pct", ascending=True)
            fig_mc = go.Figure()
            fig_mc.add_trace(go.Bar(
                y=_mc_agg["ifc_class"], x=_mc_agg["pct"], orientation="h",
                name="With Material", marker_color="#2E86AB",
                text=[f"{p:.0f}%" for p in _mc_agg["pct"]], textposition="inside",
                insidetextanchor="middle",
                hovertemplate="<b>%{y}</b><br>%{x:.1f}% with material (%{customdata[0]} of %{customdata[1]})<extra></extra>",
                customdata=list(zip(_mc_agg["with_mat"], _mc_agg["total"])),
            ))
            fig_mc.add_trace(go.Bar(
                y=_mc_agg["ifc_class"], x=(100 - _mc_agg["pct"]), orientation="h",
                name="Missing", marker_color="#E8EBEF",
                hovertemplate="<b>%{y}</b><br>%{x:.1f}% missing material<extra></extra>",
            ))
            fig_mc.update_layout(
                barmode="stack",
                template="plotly_white",
                font=dict(family="Inter, sans-serif", size=12, color=COLORS["text"]),
                xaxis=dict(title="% Coverage", range=[0, 100], ticksuffix="%", gridcolor=COLORS["grid"], showgrid=True, zeroline=False),
                yaxis=dict(title=""), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
                margin=dict(l=10, r=30, t=20, b=50),
                height=max(300, len(_mc_agg) * 30),
            )
            st.plotly_chart(fig_mc, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No element data available.")
