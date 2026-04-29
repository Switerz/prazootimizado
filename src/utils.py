"""Funções utilitárias de formatação e exportação."""

import io
import pandas as pd


# ── formatação ──────────────────────────────────────────────────────────────

def fmt_dias(v, decimals: int = 2) -> str:
    if pd.isna(v):
        return "—"
    return f"{v:.{decimals}f} d"


def fmt_pct(v, decimals: int = 1) -> str:
    """Formata uma fração (0‑1) como percentual."""
    if pd.isna(v):
        return "—"
    return f"{v * 100:.{decimals}f}%"


def fmt_pct_direct(v, decimals: int = 1) -> str:
    """Formata um valor já em percentual (0‑100)."""
    if pd.isna(v):
        return "—"
    return f"{v:.{decimals}f}%"


def fmt_num(v, decimals: int = 0) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(round(v, decimals)):,}".replace(",", ".")


def fmt_share(v, decimals: int = 2) -> str:
    """Formata share_base_pct (0‑100 range) como percentual."""
    if pd.isna(v):
        return "—"
    return f"{v:.{decimals}f}%"


# ── exportação ───────────────────────────────────────────────────────────────

def to_excel_download(dfs: dict[str, pd.DataFrame]) -> bytes:
    """Converte dicionário de DataFrames em bytes Excel com múltiplas abas."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    return buffer.getvalue()


def to_csv_download(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


# ── cores semânticas ─────────────────────────────────────────────────────────

VERDE = "#2ECC71"
VERMELHO = "#E74C3C"
LARANJA = "#F39C12"
AZUL = "#3498DB"
CINZA = "#95A5A6"

COLOR_MAP = {
    "Redução de prazo": VERDE,
    "Aumento de prazo": LARANJA,
    "Sem alteração": CINZA,
}

# Constantes executivas (referência do produto)
PMP_ATUAL_TOTAL: float = 3.84
PMP_RECOMENDADO_TOTAL: float = 3.33
SLA_BASELINE_TOTAL: float = 0.958
SLA_RECOMENDADO_TOTAL: float = 0.964
