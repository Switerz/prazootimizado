"""Sprint 1 — Leitura, normalização e preparação do Excel."""

import pathlib
import numpy as np
import pandas as pd
import streamlit as st

# Mapeamento: nome canônico → lista de aliases possíveis no arquivo
COLUMN_ALIASES: dict[str, list[str]] = {
    "base":           ["base"],
    "cenario":        ["cenario", "strategy"],
    "transportadora": ["transportadora", "delivery_service", "carrier", "servico"],
    "ccep":           ["CCEP", "ccep", "cep"],
    "prazo_recomendado": ["prazo rec", "prazo_rec", "prazo_recomendado", "k_star", "prazo_recomendado_dias_uteis"],
    "sla_esperado":   ["SLA esperado", "sla_esperado", "sla esperado", "sla_recomendado_grupo"],
    "sla_baseline":   ["sla_baseline_grupo"],
    "sla_portfolio":  ["sla_portfolio_cenario"],
    "pmp_portfolio":  ["pmp_portfolio_cenario"],
    "prazo_atual":    ["prazo atual", "prazo_atual", "baseline_delivery_days_mean", "prazo_atual_dias_uteis"],
    "_ganho_raw":     ["diff_prazo", "delta_prazo_dias_uteis"],          # arquivo: prazo_atual - prazo_rec
    "cepi":           ["CEPI", "cepi"],
    "cepf":           ["CEPF", "cepf"],
    "share_base_decimal": ["share%", "share_%_base_total", "share", "share_base_total_pct", "share_base_pct"],
    "uf":             ["UF", "uf"],
    "cidade":         ["cidade", "Cidade"],
    "qtd_pedidos":    ["qtd_pedidos", "volume", "pedidos", "n_obs"],
    "fhat_at_k":      ["Fhat_at_k", "fhat_at_k", "fhat_modelo"],
    "lb_at_k":        ["LB_at_k", "lb_at_k", "lb_modelo"],
    "n_eff_at_k":     ["N_eff_at_k", "n_eff_at_k", "n_eff_modelo"],
    "decision_mode":  ["decision_mode"],
    "guardrail_status": ["guardrail_status"],
    "guardrail_reason": ["guardrail_reason"],
}

DEFAULT_FILENAME = "prazo_otimizado_brasil_fhat96_20260428_1716.xlsx"
EXPORT_PATTERNS = {
    "gocase": "prazo_otimizado_brasil_gocase_*.xlsx",
    "gobeaute": "prazo_otimizado_brasil_gobeaute_*.xlsx",
}


@st.cache_data(show_spinner=False)
def load_excel(source) -> dict[str, pd.DataFrame]:
    """Carrega todas as abas do Excel e retorna um dict {nome_aba: DataFrame}."""
    try:
        xl = pd.ExcelFile(source)
        return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}
    except Exception as exc:
        st.error(f"Erro ao abrir o arquivo: {exc}")
        return {}


def detect_default_file(base: str | None = None) -> pathlib.Path | None:
    """Procura o arquivo Excel padrão em pastas conhecidas."""
    here = pathlib.Path(__file__).parent.parent
    project = here.parent
    if base in EXPORT_PATTERNS:
        for folder in [here / "data", here / "exports", project / "exports"]:
            files = [
                p for p in folder.glob(EXPORT_PATTERNS[base])
                if p.is_file() and not p.name.startswith("~$")
            ]
            if files:
                return max(files, key=lambda p: p.stat().st_mtime)
    candidates = [
        here / "data" / DEFAULT_FILENAME,
        project / "exports" / DEFAULT_FILENAME,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def get_main_sheet(sheets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, list[str]]:
    """Detecta e retorna a aba principal de recomendações."""
    warnings: list[str] = []
    preferred = ["streamlit_input", "df_gold", "df_estrategias", "gold", "recomendacoes", "recommendations"]
    for name in preferred:
        if name in sheets:
            return sheets[name].copy(), warnings
    # fallback: maior aba
    if sheets:
        name = max(sheets, key=lambda k: len(sheets[k]))
        warnings.append(f"Aba '{name}' selecionada automaticamente (nenhuma aba padrão encontrada).")
        return sheets[name].copy(), warnings
    return pd.DataFrame(), warnings


def _find_column(df: pd.DataFrame, canonical: str) -> str | None:
    """Retorna o nome real da coluna no df que corresponde ao nome canônico."""
    aliases = COLUMN_ALIASES.get(canonical, [canonical])
    for alias in aliases:
        if alias in df.columns:
            return alias
    return None


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Renomeia colunas do arquivo para nomes canônicos."""
    rename_map: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in df.columns and alias != canonical:
                rename_map[alias] = canonical
                break
    df = df.rename(columns=rename_map)
    # Remove espaços extras em nomes de coluna
    df.columns = [c.strip() for c in df.columns]
    return df


def _detect_share_scale(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza share_base_decimal para verdadeira fração 0-1.

    Casos possíveis no arquivo:
    - max > 1.5 → coluna já está em escala 0-100, divide por 100
    - sum > 1.05 com max <= 1 → valores são percentuais pequenos (ex: 0.66 = 0.66%),
      não frações; divide por 100
    - caso contrário → já é fração 0-1, mantém
    """
    if "share_base_decimal" not in df.columns:
        return df
    max_val = df["share_base_decimal"].max()
    sum_val = df["share_base_decimal"].sum()
    if max_val > 1.5 or sum_val > 1.05:
        df["share_base_decimal"] = df["share_base_decimal"] / 100.0
    return df


def prepare_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """Cria todas as colunas derivadas necessárias."""
    df = normalize_columns(df)
    df = _detect_share_scale(df)

    # share_base_pct (0-100 para exibição)
    if "share_base_decimal" in df.columns:
        df["share_base_pct"] = df["share_base_decimal"] * 100.0
    elif "share_base_pct" in df.columns:
        df["share_base_decimal"] = df["share_base_pct"] / 100.0
    else:
        df["share_base_decimal"] = np.nan
        df["share_base_pct"] = np.nan

    # garantir prazo_atual e prazo_recomendado
    if "prazo_atual" not in df.columns:
        df["prazo_atual"] = np.nan
    if "prazo_recomendado" not in df.columns:
        df["prazo_recomendado"] = np.nan

    df["prazo_atual"] = pd.to_numeric(df["prazo_atual"], errors="coerce")
    df["prazo_recomendado"] = pd.to_numeric(df["prazo_recomendado"], errors="coerce")

    # diff_prazo (spec): prazo_rec - prazo_atual  (negativo = redução)
    if "_ganho_raw" in df.columns:
        # arquivo: _ganho_raw = prazo_atual - prazo_rec → inverter sinal
        df["diff_prazo"] = -pd.to_numeric(df["_ganho_raw"], errors="coerce")
        df["ganho_prazo"] = pd.to_numeric(df["_ganho_raw"], errors="coerce")
        df = df.drop(columns=["_ganho_raw"], errors="ignore")
    else:
        df["diff_prazo"] = df["prazo_recomendado"] - df["prazo_atual"]
        df["ganho_prazo"] = df["prazo_atual"] - df["prazo_recomendado"]

    # tipo de recomendação
    def _tipo(d: float) -> str:
        if pd.isna(d):
            return "Sem alteração"
        if d < -0.001:
            return "Redução de prazo"
        if d > 0.001:
            return "Aumento de prazo"
        return "Sem alteração"

    df["tipo_recomendacao"] = df["diff_prazo"].apply(_tipo)
    df["tipo_recomendacao"] = df["tipo_recomendacao"].replace({
        "reducao_pmp": "Redução de prazo",
        "recuperacao_sla": "Aumento de prazo",
        "Reducao PMP": "Redução de prazo",
        "Recuperacao SLA": "Aumento de prazo",
    })

    # impactos ponderados
    peso = df["share_base_decimal"].fillna(0)
    df["impacto_pond"] = df["ganho_prazo"] * peso
    df["impacto_abs"] = df["diff_prazo"].abs() * peso

    # UF: normalizar colunas multi-estado para exibição simples (usar primeira UF)
    if "uf" in df.columns:
        df["uf"] = df["uf"].astype(str).str.strip()
        df["uf_primaria"] = df["uf"].str.split(r"\s*\|\s*").str[0].str.strip()
    else:
        df["uf"] = "N/A"
        df["uf_primaria"] = "N/A"

    # transportadora
    if "transportadora" not in df.columns:
        df["transportadora"] = "N/A"

    # CCEP como string com zero-fill
    if "ccep" in df.columns:
        df["ccep_str"] = (
            df["ccep"].astype(str)
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(3)
        )
    else:
        df["ccep"] = np.nan
        df["ccep_str"] = "N/A"

    if "cenario" not in df.columns:
        df["cenario"] = "default"
    if "base" not in df.columns:
        df["base"] = "desconhecida"

    return df


def validate_dataframe(df: pd.DataFrame) -> list[str]:
    """Retorna lista de alertas de qualidade."""
    alerts: list[str] = []
    critical_cols = ["prazo_atual", "prazo_recomendado", "uf", "transportadora"]
    for col in critical_cols:
        if col not in df.columns:
            alerts.append(f"Coluna crítica ausente: **{col}**")
    if "share_base_decimal" in df.columns:
        nulls = df["share_base_decimal"].isna().sum()
        if nulls > 0:
            alerts.append(f"{nulls} linhas sem share% (serão ignoradas em cálculos ponderados).")
    return alerts


def check_metadata_consistency(sheets: dict, df_main: pd.DataFrame) -> str | None:
    """Retorna alerta se metadata indica número de linhas diferente do df principal."""
    for name in ["metadata", "Metadata"]:
        if name not in sheets:
            continue
        meta = sheets[name]
        if "campo" in meta.columns and "valor" in meta.columns:
            row = meta[meta["campo"] == "linhas_df_gold"]
            if not row.empty:
                try:
                    meta_lines = int(row["valor"].iloc[0])
                    actual = len(df_main)
                    if meta_lines != actual:
                        return (
                            f"A aba *metadata* registrou {meta_lines} linhas, "
                            f"mas o df principal tem {actual}. "
                            "Isso pode indicar que a metadata veio de uma etapa anterior do pipeline."
                        )
                except (ValueError, TypeError):
                    pass
    return None
