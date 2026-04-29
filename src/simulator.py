"""Sprint 8 — Simulador de cenários de rollout."""

import numpy as np
import pandas as pd

from .utils import PMP_ATUAL_TOTAL, PMP_RECOMENDADO_TOTAL, SLA_BASELINE_TOTAL, SLA_RECOMENDADO_TOTAL


def simulate_rollout(df_filtered: pd.DataFrame, df_all: pd.DataFrame) -> dict:
    """
    Estima o efeito de aplicar apenas as recomendações de df_filtered.

    O ganho executivo total (PMP_ATUAL - PMP_RECOMENDADO) é distribuído
    proporcionalmente ao impacto ponderado das recomendações selecionadas.
    """
    if df_all.empty or "impacto_pond" not in df_all.columns:
        return _empty_sim()

    impacto_total = df_all["impacto_pond"].clip(lower=0).sum()
    impacto_cenario = df_filtered["impacto_pond"].clip(lower=0).sum() if not df_filtered.empty else 0.0

    ganho_total_oficial = PMP_ATUAL_TOTAL - PMP_RECOMENDADO_TOTAL  # positivo ≈ 0.51

    if impacto_total > 0:
        proporcao = impacto_cenario / impacto_total
    else:
        proporcao = 0.0

    ganho_cenario = ganho_total_oficial * proporcao
    pmp_simulado = PMP_ATUAL_TOTAL - ganho_cenario
    reducao_pct = (pmp_simulado / PMP_ATUAL_TOTAL) - 1 if PMP_ATUAL_TOTAL > 0 else 0.0

    # SLA simulado: interpolação linear entre baseline e recomendado
    delta_sla_total = SLA_RECOMENDADO_TOTAL - SLA_BASELINE_TOTAL
    sla_simulado = SLA_BASELINE_TOTAL + delta_sla_total * proporcao

    n_aplicadas = len(df_filtered)
    n_reducoes = (df_filtered["tipo_recomendacao"] == "Redução de prazo").sum() if not df_filtered.empty else 0
    n_aumentos = (df_filtered["tipo_recomendacao"] == "Aumento de prazo").sum() if not df_filtered.empty else 0
    share_afetado = df_filtered["share_base_decimal"].sum() if "share_base_decimal" in df_filtered.columns else 0.0

    return {
        "n_aplicadas":   n_aplicadas,
        "n_reducoes":    n_reducoes,
        "n_aumentos":    n_aumentos,
        "share_afetado": share_afetado,
        "pmp_atual":     PMP_ATUAL_TOTAL,
        "pmp_simulado":  pmp_simulado,
        "pmp_total":     PMP_RECOMENDADO_TOTAL,
        "ganho_simulado": ganho_cenario,
        "reducao_pct":   reducao_pct,
        "proporcao":     proporcao,
        "sla_baseline":  SLA_BASELINE_TOTAL,
        "sla_simulado":  sla_simulado,
        "sla_total":     SLA_RECOMENDADO_TOTAL,
    }


def build_rollout_table(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara tabela de governança com colunas de controle de rollout."""
    cols_desejadas = [
        "transportadora", "uf", "cidade", "ccep", "qtd_pedidos",
        "share_base_pct", "prazo_atual", "prazo_recomendado",
        "diff_prazo", "ganho_prazo", "impacto_pond",
        "tipo_recomendacao", "sla_esperado", "fhat_at_k", "lb_at_k",
        "n_eff_at_k", "decision_mode",
    ]
    cols_presentes = [c for c in cols_desejadas if c in df.columns]
    result = df[cols_presentes].copy()

    result.insert(0, "status_rollout", "Pendente")
    result.insert(1, "prioridade", _calc_prioridade(result))

    import datetime
    result["data_recomendacao"] = datetime.date.today().isoformat()
    result["justificativa_modelo"] = result.apply(_justificativa, axis=1)

    return result.reset_index(drop=True)


def _calc_prioridade(df: pd.DataFrame) -> pd.Series:
    if "impacto_pond" not in df.columns:
        return pd.Series(["—"] * len(df))
    rank = df["impacto_pond"].rank(pct=True, ascending=False)
    return rank.apply(lambda r: "Alta" if r <= 0.33 else ("Média" if r <= 0.66 else "Baixa"))


def _justificativa(row) -> str:
    tipo = row.get("tipo_recomendacao", "")
    if tipo == "Redução de prazo":
        return "Prazo atual acima do ótimo estimado; redução melhora competitividade sem risco de SLA."
    elif tipo == "Aumento de prazo":
        return "Prazo atual abaixo do observado; aumento protege SLA e reduz atrasos percebidos."
    return "Prazo já ajustado ao ótimo estimado."


def _empty_sim() -> dict:
    return {
        "n_aplicadas": 0, "n_reducoes": 0, "n_aumentos": 0,
        "share_afetado": 0.0, "pmp_atual": PMP_ATUAL_TOTAL,
        "pmp_simulado": PMP_ATUAL_TOTAL, "pmp_total": PMP_RECOMENDADO_TOTAL,
        "ganho_simulado": 0.0, "reducao_pct": 0.0, "proporcao": 0.0,
        "sla_baseline": SLA_BASELINE_TOTAL, "sla_simulado": SLA_BASELINE_TOTAL,
        "sla_total": SLA_RECOMENDADO_TOTAL,
    }
