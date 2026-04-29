"""Sprint 4 — Mapa choropleth do Brasil por UF."""

import json
import pathlib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

from .metrics import METRIC_LABELS
from .utils import AZUL

GEOJSON_PATH = pathlib.Path(__file__).parent.parent / "assets" / "brasil_ufs.geojson"

# GeoJSON com 27 estados e properties.sigla já preenchido corretamente
_GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforamerica/click_that_hood"
    "/master/public/data/brazil-states.geojson"
)


@st.cache_data(show_spinner=False)
def load_geojson() -> dict | None:
    """Carrega GeoJSON do Brasil: arquivo local → download → None."""
    # Arquivo local
    if GEOJSON_PATH.exists():
        with open(GEOJSON_PATH, encoding="utf-8") as f:
            geojson = json.load(f)
        # Valida: precisa ter 27 features com sigla
        features = geojson.get("features", [])
        if len(features) >= 27 and _has_sigla(features[0]):
            return geojson
        # arquivo inválido (ex: salvou o Brasil todo) — apaga e re-baixa
        GEOJSON_PATH.unlink(missing_ok=True)

    # Download
    try:
        resp = requests.get(_GEOJSON_URL, timeout=20)
        resp.raise_for_status()
        geojson = resp.json()
        if len(geojson.get("features", [])) >= 27:
            GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
                json.dump(geojson, f)
            return geojson
    except Exception:
        pass

    return None


def _has_sigla(feature: dict) -> bool:
    props = feature.get("properties", {})
    val = props.get("sigla", "")
    return isinstance(val, str) and len(val) == 2


def build_brazil_map(
    df_uf: pd.DataFrame,
    metric: str = "impacto_pond_total",
    geojson: dict | None = None,
) -> go.Figure | None:
    """Constrói choropleth do Brasil por UF. Retorna None se GeoJSON indisponível."""
    if geojson is None or df_uf.empty:
        return None

    # Garante que temos apenas UFs simples (sem 'MG | SP')
    df_plot = df_uf[df_uf["uf"].str.len() <= 2].copy()
    if df_plot.empty:
        return None

    label = METRIC_LABELS.get(metric, metric)

    hover_cols = {
        c: True
        for c in [
            "qtd_recomendacoes", "share_impactado", "pmp_atual_pond",
            "pmp_recomendado_pond", "ganho_ponderado", "qtd_reducoes", "qtd_aumentos",
        ]
        if c in df_plot.columns
    }

    fig = px.choropleth(
        df_plot,
        geojson=geojson,
        locations="uf",
        featureidkey="properties.sigla",
        color=metric,
        color_continuous_scale="YlOrRd",
        hover_name="uf",
        hover_data=hover_cols,
        labels={metric: label},
        title=f"Brasil por UF — {label}",
    )

    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showland=True,
        landcolor="#F0F3F4",
        showocean=True,
        oceancolor="#D6EAF8",
        showframe=False,
        projection_type="mercator",
    )

    fig.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Inter, sans-serif",
        coloraxis_colorbar=dict(title=label, thickness=14),
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def build_uf_bar_fallback(df_uf: pd.DataFrame, metric: str = "impacto_pond_total") -> go.Figure:
    """Fallback: barras horizontais por UF quando GeoJSON não está disponível."""
    if df_uf.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sem dados", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False)
        return fig

    label = METRIC_LABELS.get(metric, metric)
    df_sorted = df_uf[df_uf["uf"].str.len() <= 2].sort_values(metric, ascending=True).tail(27)

    fig = go.Figure(go.Bar(
        x=df_sorted[metric],
        y=df_sorted["uf"],
        orientation="h",
        marker_color=AZUL,
        text=df_sorted[metric].round(4),
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Ranking UF — {label}",
        xaxis_title=label,
        height=650,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=60, t=40, b=10),
    )
    return fig
