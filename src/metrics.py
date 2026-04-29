"""Sprint 2 — KPIs executivos e agregações por UF, transportadora e matriz."""

import numpy as np
import pandas as pd

from .utils import PMP_ATUAL_TOTAL, PMP_RECOMENDADO_TOTAL, SLA_BASELINE_TOTAL, SLA_RECOMENDADO_TOTAL

UFS_BRASIL = [
    "AC","AL","AP","AM","BA","CE","DF","ES","GO",
    "MA","MT","MS","MG","PA","PB","PR","PE","PI",
    "RJ","RN","RS","RO","RR","SC","SP","SE","TO",
]


# ── KPIs globais ──────────────────────────────────────────────────────────────

def calculate_global_kpis(df: pd.DataFrame) -> dict:
    """Calcula KPIs executivos usando os valores de referência do produto."""
    n_total = len(df)
    n_reducoes = (df["tipo_recomendacao"] == "Redução de prazo").sum()
    n_aumentos = (df["tipo_recomendacao"] == "Aumento de prazo").sum()
    n_sem_alt = (df["tipo_recomendacao"] == "Sem alteração").sum()

    share_col = "share_base_decimal" if "share_base_decimal" in df.columns else None
    share_impactado = df[share_col].sum() if share_col else np.nan

    ufs = df["uf_primaria"].nunique() if "uf_primaria" in df.columns else df["uf"].nunique()
    transportadoras = df["transportadora"].nunique() if "transportadora" in df.columns else 0
    cceps = df["ccep"].nunique() if "ccep" in df.columns else 0

    ganho_pmp = PMP_RECOMENDADO_TOTAL - PMP_ATUAL_TOTAL           # ≈ -0.51
    reducao_pct = (PMP_RECOMENDADO_TOTAL / PMP_ATUAL_TOTAL) - 1   # ≈ -13.3%
    delta_sla = SLA_RECOMENDADO_TOTAL - SLA_BASELINE_TOTAL         # ≈ +0.006

    return {
        "pmp_atual":           PMP_ATUAL_TOTAL,
        "pmp_recomendado":     PMP_RECOMENDADO_TOTAL,
        "ganho_pmp":           ganho_pmp,
        "reducao_pct":         reducao_pct,
        "sla_baseline":        SLA_BASELINE_TOTAL,
        "sla_recomendado":     SLA_RECOMENDADO_TOTAL,
        "delta_sla":           delta_sla,
        "share_impactado":     share_impactado,
        "n_total":             n_total,
        "n_reducoes":          n_reducoes,
        "n_aumentos":          n_aumentos,
        "n_sem_alteracao":     n_sem_alt,
        "n_ufs":               ufs,
        "n_transportadoras":   transportadoras,
        "n_cceps":             cceps,
    }


# ── Agregação por UF ──────────────────────────────────────────────────────────

def _explode_uf(df: pd.DataFrame) -> pd.DataFrame:
    """Expande linhas com múltiplas UFs (ex: 'MG | SP') em uma linha por UF."""
    df2 = df.copy()
    df2["uf_lista"] = df2["uf"].str.split(r"\s*\|\s*")
    df2 = df2.explode("uf_lista").copy()
    df2["uf_lista"] = df2["uf_lista"].str.strip()
    return df2


def calculate_uf_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega métricas por UF (com explosão de multi-UF)."""
    df2 = _explode_uf(df)
    peso = df2["share_base_decimal"].fillna(0)

    agg = df2.groupby("uf_lista").agg(
        qtd_recomendacoes=("diff_prazo", "count"),
        qtd_reducoes=("tipo_recomendacao", lambda s: (s == "Redução de prazo").sum()),
        qtd_aumentos=("tipo_recomendacao", lambda s: (s == "Aumento de prazo").sum()),
    ).reset_index().rename(columns={"uf_lista": "uf"})

    # métricas ponderadas pelo share
    def wavg(group_col, val_col, weight_col):
        tmp = df2.copy()
        tmp["_w"] = tmp[weight_col].fillna(0)
        g = tmp.groupby(group_col).apply(
            lambda g: np.average(g[val_col], weights=g["_w"]) if g["_w"].sum() > 0
            else g[val_col].mean()
        ).reset_index()
        g.columns = [group_col, f"{val_col}_pond"]
        return g

    share_sum = df2.groupby("uf_lista")["share_base_decimal"].sum().reset_index()
    share_sum.columns = ["uf", "share_impactado"]

    impacto_sum = df2.groupby("uf_lista")["impacto_pond"].sum().reset_index()
    impacto_sum.columns = ["uf", "impacto_pond_total"]

    ganho_medio = df2.groupby("uf_lista")["ganho_prazo"].mean().reset_index()
    ganho_medio.columns = ["uf", "ganho_medio"]

    # PMP ponderado por share — usando numpy groupby manual para evitar FutureWarning
    tmp = df2.copy()
    tmp["_w"] = tmp["share_base_decimal"].fillna(0)

    def _wavg_by_group(group_col: str, val_col: str, weight_col: str) -> pd.DataFrame:
        rows = []
        for grp, sub in tmp.groupby(group_col):
            w = sub[weight_col].values
            v = sub[val_col].values
            result = np.average(v, weights=w) if w.sum() > 0 else v.mean()
            rows.append({group_col: grp, val_col: result})
        return pd.DataFrame(rows)

    pmp_atual_df = _wavg_by_group("uf_lista", "prazo_atual", "_w")
    pmp_atual = pmp_atual_df.rename(columns={"uf_lista": "uf", "prazo_atual": "pmp_atual_pond"})

    pmp_rec_df = _wavg_by_group("uf_lista", "prazo_recomendado", "_w")
    pmp_rec = pmp_rec_df.rename(columns={"uf_lista": "uf", "prazo_recomendado": "pmp_recomendado_pond"})

    result = (
        agg
        .merge(share_sum, on="uf", how="left")
        .merge(impacto_sum, on="uf", how="left")
        .merge(ganho_medio, on="uf", how="left")
        .merge(pmp_atual, on="uf", how="left")
        .merge(pmp_rec, on="uf", how="left")
    )

    result["ganho_ponderado"] = result["pmp_atual_pond"] - result["pmp_recomendado_pond"]
    return result.sort_values("impacto_pond_total", ascending=False)


# ── Agregação por transportadora ──────────────────────────────────────────────

def calculate_carrier_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega métricas por transportadora."""
    tmp = df.copy()
    tmp["_w"] = tmp["share_base_decimal"].fillna(0)

    agg = tmp.groupby("transportadora").agg(
        qtd_recomendacoes=("diff_prazo", "count"),
        qtd_reducoes=("tipo_recomendacao", lambda s: (s == "Redução de prazo").sum()),
        qtd_aumentos=("tipo_recomendacao", lambda s: (s == "Aumento de prazo").sum()),
        share_impactado=("share_base_decimal", "sum"),
        impacto_pond_total=("impacto_pond", "sum"),
    ).reset_index()

    extra_rows = []
    for carrier, g in tmp.groupby("transportadora"):
        w = g["_w"].values
        row = {"transportadora": carrier}
        row["pmp_atual_pond"] = np.average(g["prazo_atual"].values, weights=w) if w.sum() > 0 else g["prazo_atual"].mean()
        row["pmp_recomendado_pond"] = np.average(g["prazo_recomendado"].values, weights=w) if w.sum() > 0 else g["prazo_recomendado"].mean()
        row["media_fhat"] = g["fhat_at_k"].mean() if "fhat_at_k" in g.columns else np.nan
        row["media_lb"] = g["lb_at_k"].mean() if "lb_at_k" in g.columns else np.nan
        row["media_neff"] = g["n_eff_at_k"].mean() if "n_eff_at_k" in g.columns else np.nan
        extra_rows.append(row)
    extra = pd.DataFrame(extra_rows)

    result = agg.merge(extra, on="transportadora", how="left")
    result["ganho_ponderado"] = result["pmp_atual_pond"] - result["pmp_recomendado_pond"]
    return result.sort_values("impacto_pond_total", ascending=False)


# ── Matriz UF × transportadora ────────────────────────────────────────────────

def calculate_uf_carrier_matrix(df: pd.DataFrame, metric: str = "impacto_pond_total") -> pd.DataFrame:
    """Retorna DataFrame pivotado UF × transportadora para a métrica selecionada."""
    df2 = _explode_uf(df)
    tmp = df2.copy()
    tmp["_w"] = tmp["share_base_decimal"].fillna(0)

    if metric in ("impacto_pond_total", "share_impactado", "qtd_recomendacoes",
                  "qtd_reducoes", "qtd_aumentos"):
        agg_fn_map = {
            "impacto_pond_total": ("impacto_pond", "sum"),
            "share_impactado":    ("share_base_decimal", "sum"),
            "qtd_recomendacoes":  ("diff_prazo", "count"),
            "qtd_reducoes":       ("tipo_recomendacao", lambda s: (s == "Redução de prazo").sum()),
            "qtd_aumentos":       ("tipo_recomendacao", lambda s: (s == "Aumento de prazo").sum()),
        }
        col, fn = agg_fn_map[metric]
        if callable(fn):
            agg = tmp.groupby(["uf_lista", "transportadora"])[col].agg(fn).reset_index()
        else:
            agg = tmp.groupby(["uf_lista", "transportadora"])[col].agg(fn).reset_index()
        agg.columns = ["uf", "transportadora", "valor"]
    else:
        # métricas de média ponderada
        col_map = {
            "ganho_medio":        "ganho_prazo",
            "pmp_atual_pond":     "prazo_atual",
            "pmp_recomendado_pond": "prazo_recomendado",
        }
        col = col_map.get(metric, "ganho_prazo")
        rows = []
        for (uf_, carr_), g in tmp.groupby(["uf_lista", "transportadora"]):
            w = g["_w"].values
            v = np.average(g[col].values, weights=w) if w.sum() > 0 else g[col].mean()
            rows.append({"uf": uf_, "transportadora": carr_, "valor": v})
        agg = pd.DataFrame(rows)

    pivot = agg.pivot(index="uf", columns="transportadora", values="valor")
    return pivot


METRIC_LABELS = {
    "impacto_pond_total":     "Impacto Ponderado",
    "ganho_medio":            "Ganho Médio de Prazo (dias)",
    "share_impactado":        "Share Impactado",
    "pmp_atual_pond":         "PMP Atual Ponderado",
    "pmp_recomendado_pond":   "PMP Recomendado Ponderado",
    "qtd_recomendacoes":      "Qtd. Recomendações",
    "qtd_reducoes":           "Qtd. Reduções",
    "qtd_aumentos":           "Qtd. Aumentos",
}
