"""Sprints 2, 5, 6, 7 — Todos os gráficos Plotly."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from .utils import (
    COLOR_MAP, VERDE, VERMELHO, LARANJA, AZUL, CINZA,
    PMP_ATUAL_TOTAL, PMP_RECOMENDADO_TOTAL, SLA_BASELINE_TOTAL, SLA_RECOMENDADO_TOTAL,
)

_AXIS = dict(
    gridcolor="rgba(255,255,255,0.05)",
    zerolinecolor="rgba(255,255,255,0.08)",
    tickfont=dict(color="#7F8C8D", size=11),
    linecolor="rgba(255,255,255,0.06)",
)

_LAYOUT = dict(
    font_family="Inter, 'Segoe UI', sans-serif",
    font_color="#AEB6BF",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.02)",
    margin=dict(l=10, r=10, t=44, b=10),
    title_font=dict(size=13, color="#D5D8DC"),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8E9BAE", size=11)),
    xaxis=_AXIS,
    yaxis=_AXIS,
)


# ── Sprint 2 — KPIs Executivos ────────────────────────────────────────────────

def build_waterfall_kpi() -> go.Figure:
    """Waterfall: PMP Atual → Ganho estimado → PMP Recomendado."""
    ganho = PMP_RECOMENDADO_TOTAL - PMP_ATUAL_TOTAL  # negativo

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["absolute", "relative", "total"],
        x=["PMP Atual", "Ganho Estimado", "PMP Recomendado"],
        y=[PMP_ATUAL_TOTAL, ganho, PMP_RECOMENDADO_TOTAL],
        text=[f"<b>{PMP_ATUAL_TOTAL:.2f} d</b>", f"<b>{ganho:+.2f} d</b>", f"<b>{PMP_RECOMENDADO_TOTAL:.2f} d</b>"],
        textposition="outside",
        textfont=dict(size=13, color="#FFFFFF"),
        connector=dict(line=dict(color="rgba(255,255,255,0.12)", width=1, dash="dot")),
        decreasing=dict(marker=dict(color="#2ECC71", line=dict(color="#27AE60", width=1))),
        totals=dict(marker=dict(color="#3498DB", line=dict(color="#2980B9", width=1))),
        increasing=dict(marker=dict(color=LARANJA)),
    ))
    fig.update_layout(
        title="Evolução do PMP Médio (dias)",
        yaxis_title="Dias",
        showlegend=False,
        height=340,
        yaxis=dict(**_AXIS, range=[3.0, 4.1]),
        **{k: v for k, v in _LAYOUT.items() if k not in ("xaxis", "yaxis")},
    )
    return fig


def build_type_distribution(df: pd.DataFrame) -> go.Figure:
    """Bar chart: quantidade de reduções vs aumentos vs sem alteração."""
    counts = df["tipo_recomendacao"].value_counts().reset_index()
    counts.columns = ["tipo", "qtd"]
    counts["cor"] = counts["tipo"].map(COLOR_MAP).fillna(CINZA)

    fig = go.Figure(go.Bar(
        x=counts["tipo"],
        y=counts["qtd"],
        marker_color=counts["cor"].tolist(),
        text=counts["qtd"],
        textposition="outside",
    ))
    fig.update_layout(
        title="Distribuição das Recomendações",
        yaxis_title="Quantidade",
        xaxis_title="",
        showlegend=False,
        height=320,
        **_LAYOUT,
    )
    return fig


def build_sla_comparison() -> go.Figure:
    """Gráfico de barras comparando SLA baseline vs recomendado."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="SLA Baseline",
        x=["SLA"],
        y=[SLA_BASELINE_TOTAL * 100],
        marker_color=AZUL,
        text=[f"{SLA_BASELINE_TOTAL*100:.1f}%"],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="SLA Recomendado",
        x=["SLA"],
        y=[SLA_RECOMENDADO_TOTAL * 100],
        marker_color=VERDE,
        text=[f"{SLA_RECOMENDADO_TOTAL*100:.1f}%"],
        textposition="outside",
    ))
    fig.update_layout(
        title="SLA: Baseline vs Recomendado",
        yaxis_title="%",
        barmode="group",
        height=300,
        yaxis_range=[93, 98],
        **_LAYOUT,
    )
    return fig


# ── Sprint 5 — Rankings ───────────────────────────────────────────────────────

def build_ranking_chart(
    df: pd.DataFrame,
    group_col: str,
    metric_col: str,
    title: str = "",
    top_n: int = 15,
    color: str = AZUL,
) -> go.Figure:
    """Gráfico de barras horizontal para rankings."""
    if df.empty or group_col not in df.columns or metric_col not in df.columns:
        return _empty_figure(title)

    agg = (
        df.groupby(group_col)[metric_col]
        .sum()
        .reset_index()
        .sort_values(metric_col, ascending=False)
        .head(top_n)
        .sort_values(metric_col, ascending=True)
    )

    fig = go.Figure(go.Bar(
        x=agg[metric_col],
        y=agg[group_col].astype(str),
        orientation="h",
        marker_color=color,
        text=agg[metric_col].round(3),
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        xaxis_title=metric_col.replace("_", " ").title(),
        height=max(300, top_n * 28),
        **_LAYOUT,
    )
    return fig


def build_scatter_opportunity(df: pd.DataFrame) -> go.Figure:
    """Scatter: share (X) × ganho de prazo (Y), tamanho = share, cor = tipo."""
    if df.empty:
        return _empty_figure("Oportunidades: Share × Ganho de Prazo")

    needed = ["share_base_pct", "ganho_prazo", "tipo_recomendacao"]
    if not all(c in df.columns for c in needed):
        return _empty_figure("Oportunidades: Share × Ganho de Prazo")

    hover_cols = [c for c in ["uf_primaria", "ccep_str", "transportadora", "cidade"] if c in df.columns]
    fig = px.scatter(
        df,
        x="share_base_pct",
        y="ganho_prazo",
        color="tipo_recomendacao",
        color_discrete_map=COLOR_MAP,
        size="share_base_pct",
        size_max=30,
        hover_data=hover_cols,
        labels={
            "share_base_pct": "Share da Base (%)",
            "ganho_prazo": "Ganho de Prazo (dias)",
            "tipo_recomendacao": "Tipo",
        },
        title="Oportunidades: Share × Ganho de Prazo",
    )
    fig.update_layout(height=450, **_LAYOUT)
    return fig


def build_stacked_carrier(df_carrier: pd.DataFrame) -> go.Figure:
    """Barras empilhadas: reduções vs aumentos por transportadora."""
    if df_carrier.empty:
        return _empty_figure("Redução vs Aumento por Transportadora")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Reduções",
        x=df_carrier["transportadora"],
        y=df_carrier["qtd_reducoes"],
        marker_color=VERDE,
    ))
    fig.add_trace(go.Bar(
        name="Aumentos",
        x=df_carrier["transportadora"],
        y=df_carrier["qtd_aumentos"],
        marker_color=LARANJA,
    ))
    fig.update_layout(
        barmode="stack",
        title="Reduções vs Aumentos por Transportadora",
        yaxis_title="Qtd. Recomendações",
        height=380,
        **_LAYOUT,
    )
    return fig


def build_boxplot_carrier(df: pd.DataFrame) -> go.Figure:
    """Boxplot da distribuição de diff_prazo por transportadora."""
    if df.empty or "diff_prazo" not in df.columns or "transportadora" not in df.columns:
        return _empty_figure("Distribuição de Δ Prazo por Transportadora")

    carriers = df["transportadora"].dropna().unique().tolist()
    fig = go.Figure()
    for c in sorted(carriers):
        vals = df[df["transportadora"] == c]["diff_prazo"].dropna()
        fig.add_trace(go.Box(
            y=vals,
            name=c,
            boxpoints="outliers",
            marker_color=AZUL,
        ))
    fig.update_layout(
        title="Distribuição de Δ Prazo por Transportadora",
        yaxis_title="Δ Prazo (dias) — negativo = redução",
        height=420,
        showlegend=False,
        **_LAYOUT,
    )
    return fig


# ── Sprint 7 — Heatmap UF × Transportadora ───────────────────────────────────

def build_heatmap_uf_carrier(
    pivot: pd.DataFrame,
    title: str = "Heatmap UF × Transportadora",
    colorscale: str = "RdYlGn",
) -> go.Figure:
    """Heatmap a partir de pivot DataFrame (index=UF, columns=transportadora)."""
    if pivot is None or pivot.empty:
        return _empty_figure(title)

    z = pivot.values
    y_labels = [str(v) for v in pivot.index.tolist()]
    x_labels = [str(v) for v in pivot.columns.tolist()]

    text = [[f"{v:.3f}" if not np.isnan(v) else "" for v in row] for row in z]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        text=text,
        texttemplate="%{text}",
        colorscale=colorscale,
        colorbar=dict(title="Valor"),
        hovertemplate="UF: %{y}<br>Transportadora: %{x}<br>Valor: %{z:.3f}<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        height=max(400, len(y_labels) * 22),
        **_LAYOUT,
    )
    return fig


# ── Simulador ─────────────────────────────────────────────────────────────────

def build_simulator_comparison(kpis_all: dict, kpis_sim: dict) -> go.Figure:
    """Barras comparando PMP: cenário total vs cenário simulado."""
    categories = ["PMP Atual", "PMP Simulado", "PMP Recomendado (100%)"]
    values = [kpis_all["pmp_atual"], kpis_sim["pmp_simulado"], kpis_all["pmp_recomendado"]]
    colors = [AZUL, LARANJA, VERDE]

    fig = go.Figure(go.Bar(
        x=categories,
        y=values,
        marker_color=colors,
        text=[f"{v:.2f} d" for v in values],
        textposition="outside",
    ))
    fig.update_layout(
        title="PMP: Comparação de Cenários",
        yaxis_title="Dias",
        height=320,
        showlegend=False,
        **_LAYOUT,
    )
    return fig


# ── Helpers ───────────────────────────────────────────────────────────────────

def _empty_figure(title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Sem dados para exibir com os filtros selecionados.",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="#7F8C8D"),
    )
    fig.update_layout(title=title, height=300, **_LAYOUT)
    return fig
