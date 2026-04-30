"""Sprint 3 — Filtros globais do sidebar."""

import pandas as pd
import streamlit as st


def build_sidebar_filters(df: pd.DataFrame) -> dict:
    """Renderiza filtros no sidebar e retorna dict de valores selecionados."""
    st.sidebar.title("🔍 Filtros")

    filters: dict = {}

    # Estratégia / cenário
    if "cenario" in df.columns:
        cenarios = sorted(df["cenario"].dropna().unique().tolist())
        default = [c for c in cenarios if c == "max_pmp"] or []
        cenarios_sel = st.sidebar.multiselect("Estratégia", cenarios, default=default)
        filters["cenario"] = cenarios_sel

    # UF
    if "uf_primaria" in df.columns or "uf" in df.columns:
        uf_col = "uf_primaria" if "uf_primaria" in df.columns else "uf"
        ufs_disponiveis = sorted(df[uf_col].dropna().unique().tolist())
        ufs_sel = st.sidebar.multiselect("UF", ufs_disponiveis, default=[])
        filters["uf"] = ufs_sel

    # Transportadora
    if "transportadora" in df.columns:
        carriers = sorted(df["transportadora"].dropna().unique().tolist())
        carriers_sel = st.sidebar.multiselect("Transportadora", carriers, default=[])
        filters["transportadora"] = carriers_sel

    # Tipo de recomendação
    if "tipo_recomendacao" in df.columns:
        tipos = sorted(df["tipo_recomendacao"].dropna().unique().tolist())
        tipos_sel = st.sidebar.multiselect("Tipo de recomendação", tipos, default=[])
        filters["tipo_recomendacao"] = tipos_sel

    # Cidade
    if "cidade" in df.columns:
        cidades = sorted(df["cidade"].dropna().unique().tolist())
        if len(cidades) <= 500:
            cidades_sel = st.sidebar.multiselect("Cidade", cidades, default=[])
            filters["cidade"] = cidades_sel

    # Share mínimo
    if "share_base_pct" in df.columns:
        share_min = float(df["share_base_pct"].dropna().min())
        share_max = float(df["share_base_pct"].dropna().max())
        if share_min < share_max:
            share_sel = st.sidebar.slider(
                "Share mínimo (%)",
                min_value=round(share_min, 2),
                max_value=round(share_max, 2),
                value=round(share_min, 2),
                step=0.01,
            )
            filters["share_min"] = share_sel

    # Ganho mínimo de prazo
    if "ganho_prazo" in df.columns:
        ganho_min_val = float(df["ganho_prazo"].dropna().min())
        ganho_max_val = float(df["ganho_prazo"].dropna().max())
        if ganho_min_val < ganho_max_val:
            ganho_sel = st.sidebar.slider(
                "Ganho mínimo de prazo (dias)",
                min_value=round(ganho_min_val, 1),
                max_value=round(ganho_max_val, 1),
                value=round(ganho_min_val, 1),
                step=0.1,
            )
            filters["ganho_min"] = ganho_sel

    # Faixa de prazo atual
    if "prazo_atual" in df.columns:
        pa_min = float(df["prazo_atual"].dropna().min())
        pa_max = float(df["prazo_atual"].dropna().max())
        if pa_min < pa_max:
            pa_sel = st.sidebar.slider(
                "Prazo atual (dias)",
                min_value=int(pa_min),
                max_value=int(pa_max) + 1,
                value=(int(pa_min), int(pa_max) + 1),
            )
            filters["prazo_atual_range"] = pa_sel

    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Limpar todos os filtros", use_container_width=True):
        st.rerun()

    return filters


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    """Aplica os filtros ao dataframe e retorna o subconjunto filtrado."""
    result = df.copy()

    if filters.get("uf"):
        uf_col = "uf_primaria" if "uf_primaria" in result.columns else "uf"
        result = result[result[uf_col].isin(filters["uf"])]

    if filters.get("cenario") and "cenario" in result.columns:
        result = result[result["cenario"].isin(filters["cenario"])]

    if filters.get("transportadora"):
        result = result[result["transportadora"].isin(filters["transportadora"])]

    if filters.get("tipo_recomendacao"):
        result = result[result["tipo_recomendacao"].isin(filters["tipo_recomendacao"])]

    if filters.get("cidade") and "cidade" in result.columns:
        result = result[result["cidade"].isin(filters["cidade"])]

    if "share_min" in filters and "share_base_pct" in result.columns:
        result = result[result["share_base_pct"] >= filters["share_min"]]

    if "ganho_min" in filters and "ganho_prazo" in result.columns:
        result = result[result["ganho_prazo"] >= filters["ganho_min"]]

    if "prazo_atual_range" in filters and "prazo_atual" in result.columns:
        lo, hi = filters["prazo_atual_range"]
        result = result[(result["prazo_atual"] >= lo) & (result["prazo_atual"] <= hi)]

    return result
