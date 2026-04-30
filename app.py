"""
Prazo Otimizado — Painel Executivo Brasil
Recomendações de ajuste de PMP por transportadora, UF e CCEP com proteção de SLA.
"""

import pathlib
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_loader import (
    load_excel, detect_default_file, get_main_sheet,
    prepare_recommendations, validate_dataframe, check_metadata_consistency,
)
from src.metrics import (
    calculate_global_kpis, calculate_uf_metrics,
    calculate_carrier_metrics, calculate_uf_carrier_matrix, METRIC_LABELS,
)
from src.filters import build_sidebar_filters, apply_filters
from src.charts import (
    build_waterfall_kpi, build_type_distribution, build_sla_comparison,
    build_ranking_chart, build_scatter_opportunity, build_stacked_carrier,
    build_boxplot_carrier, build_heatmap_uf_carrier, build_simulator_comparison,
)
from src.maps import load_geojson, build_brazil_map, build_uf_bar_fallback
from src.simulator import simulate_rollout, build_rollout_table
from src.utils import (
    fmt_dias, fmt_pct, fmt_num, fmt_share,
    to_excel_download, to_csv_download,
    PMP_ATUAL_TOTAL, PMP_RECOMENDADO_TOTAL,
    SLA_BASELINE_TOTAL, SLA_RECOMENDADO_TOTAL,
    VERDE, LARANJA, AZUL, VERMELHO, COLOR_MAP,
)

# ── Configuração da página ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Prazo Otimizado — Brasil",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

_CSS = """
<style>
/* ── Base ── */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0B0E17 0%, #131929 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] .stMarkdown p { color: #8E9BAE !important; }
[data-testid="stFileUploader"] { border-radius: 10px !important; }

/* ── Header ── */
.dash-header {
    background: linear-gradient(135deg,#0F1923 0%,#142032 55%,#0D2B45 100%);
    border-radius: 14px;
    padding: 26px 30px 20px;
    margin-bottom: 20px;
    border: 1px solid rgba(52,152,219,0.2);
    box-shadow: 0 4px 28px rgba(0,0,0,0.45);
}
.dash-header-title {
    font-size: 1.55rem;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: -0.3px;
    margin-bottom: 4px;
}
.dash-header-sub { color: #6B7D90; font-size: 0.87rem; }
.dash-header-badge {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(46,204,113,0.12);
    border: 1px solid rgba(46,204,113,0.25);
    border-radius: 20px; padding: 4px 12px;
    font-size: 0.73rem; font-weight: 600; color: #2ECC71; margin-top: 12px;
}

/* ── KPI cards ── */
.kpi-card {
    border-radius: 12px;
    padding: 16px 16px 12px;
    border-left: 4px solid #3498DB;
    box-shadow: 0 2px 14px rgba(0,0,0,0.3);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    background: rgba(255,255,255,0.04);
    margin-bottom: 2px;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 5px 22px rgba(0,0,0,0.4); }
.kpi-label {
    font-size: 0.63rem; font-weight: 700; letter-spacing: 1.6px;
    text-transform: uppercase; color: #6B7D90; margin-bottom: 6px;
}
.kpi-val-lg { font-size: 2.1rem; font-weight: 700; color: #FFF; letter-spacing: -0.5px; line-height: 1; }
.kpi-val-md { font-size: 1.65rem; font-weight: 700; color: #FFF; line-height: 1; }
.kpi-val-sm { font-size: 1.35rem; font-weight: 700; color: #FFF; line-height: 1; }
.kpi-badge {
    display: inline-flex; align-items: center; gap: 3px;
    margin-top: 7px; padding: 2px 9px; border-radius: 20px;
    font-size: 0.71rem; font-weight: 600;
}
.b-green  { background: rgba(46,204,113,0.14);  color: #2ECC71; }
.b-red    { background: rgba(231,76,60,0.14);   color: #E74C3C; }
.b-blue   { background: rgba(52,152,219,0.14);  color: #5DADE2; }
.b-orange { background: rgba(243,156,18,0.14);  color: #F39C12; }
.b-purple { background: rgba(155,89,182,0.14);  color: #A569BD; }
.b-teal   { background: rgba(26,188,156,0.14);  color: #1ABC9C; }
.b-gray   { background: rgba(127,140,141,0.12); color: #95A5A6; }

/* ── Section label ── */
.sec-lbl {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #3E5060;
    margin: 18px 0 10px; padding-bottom: 5px;
    border-bottom: 1px solid rgba(52,152,219,0.12);
}

/* ── Insight box ── */
.insight-box {
    background: rgba(52,152,219,0.07);
    border-left: 3px solid #2980B9; border-radius: 8px;
    padding: 13px 18px; margin-bottom: 16px;
    font-size: 0.85rem; color: #A0ADB8; line-height: 1.55;
}

/* ── Tabs ── */
button[data-baseweb="tab"] { font-size: 0.82rem !important; font-weight: 500 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: #5DADE2 !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 8px !important; }
</style>
"""
st.markdown(_CSS, unsafe_allow_html=True)


# ── UI helpers ────────────────────────────────────────────────────────────────

def _as_num(series_or_value):
    return pd.to_numeric(series_or_value, errors="coerce")


def _sheet(name: str) -> pd.DataFrame:
    """Return a workbook sheet or an empty DataFrame."""
    return sheets.get(name, pd.DataFrame()).copy()


def _format_strategy_name(value) -> str:
    return str(value).replace("_", " ").title()


def _active_strategy() -> str | None:
    """Infer the active strategy from the sidebar filter / current dataset."""
    selected = filters.get("cenario") if "filters" in globals() else None
    if selected:
        return selected[0]
    if "cenario" in df_filtered.columns and df_filtered["cenario"].notna().any():
        return str(df_filtered["cenario"].dropna().iloc[0])
    return None


def _active_strategy_review() -> pd.Series | None:
    """Find the review_estrategias row for the currently selected strategy."""
    review = _sheet("review_estrategias")
    strategy = _active_strategy()
    if review.empty or "strategy" not in review.columns or strategy is None:
        return None
    match = review[review["strategy"].astype(str) == str(strategy)]
    if match.empty:
        return None
    return match.iloc[0]

def insight(text: str) -> None:
    st.markdown(f'<div class="insight-box">💡 {text}</div>', unsafe_allow_html=True)


def sec(label: str) -> None:
    st.markdown(f'<div class="sec-lbl">{label}</div>', unsafe_allow_html=True)


def kpi(
    label: str,
    value: str,
    badge: str = "",
    badge_cls: str = "b-gray",
    accent: str = "#3498DB",
    size: str = "lg",
) -> str:
    """Return HTML for a single KPI card (to be used inside a column)."""
    val_cls = {"lg": "kpi-val-lg", "md": "kpi-val-md", "sm": "kpi-val-sm"}.get(size, "kpi-val-md")
    badge_html = f'<div class="kpi-badge {badge_cls}">{badge}</div>' if badge else ""
    return (
        f'<div class="kpi-card" style="border-left-color:{accent};">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="{val_cls}">{value}</div>'
        f'{badge_html}</div>'
    )


def kpi_row(items: list[str], widths: list[float] | None = None) -> None:
    """Render a list of kpi() HTML strings in columns."""
    w = widths or [1] * len(items)
    for col, html in zip(st.columns(w), items):
        col.markdown(html, unsafe_allow_html=True)


def render_header(n_filtered: int, n_total: int, source: str) -> None:
    pct = n_filtered / n_total * 100 if n_total else 0
    st.markdown(
        f"""<div class="dash-header">
        <div class="dash-header-title">📦 Prazo Otimizado — Painel Executivo Brasil</div>
        <div class="dash-header-sub">
            Recomendações de ajuste de PMP por transportadora, UF e CCEP com proteção de SLA
        </div>
        <div>
            <span class="dash-header-badge">
                ✦ {n_filtered} de {n_total} recomendações &nbsp;·&nbsp;
                {pct:.0f}% do escopo &nbsp;·&nbsp; {source}
            </span>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )


# ── Carregamento de dados ─────────────────────────────────────────────────────

st.sidebar.markdown(
    '<div style="padding:6px 0 4px;font-size:1.05rem;font-weight:700;color:#fff;">📦 Prazo Otimizado</div>'
    '<div style="font-size:0.72rem;color:#6B7D90;margin-bottom:8px;">Painel Executivo Brasil</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

base_options = {
    "gocase": "Gocase",
    "gobeaute": "GoBeaute",
}
base_key = st.radio(
    "Dashboard",
    options=list(base_options.keys()),
    format_func=lambda k: base_options[k],
    horizontal=True,
    label_visibility="collapsed",
)

uploaded = st.sidebar.file_uploader(
    f"Carregar arquivo Excel ({base_options[base_key]})",
    type=["xlsx"],
    help="Se vazio, será usado o export mais recente da base selecionada.",
)

@st.cache_data(show_spinner="Carregando dados…")
def _load(source):
    return load_excel(source)

if uploaded is not None:
    sheets = _load(uploaded)
    source_label = uploaded.name
else:
    default_path = detect_default_file(base_key)
    if default_path:
        sheets = _load(str(default_path))
        source_label = default_path.name
    else:
        st.error("Nenhum arquivo encontrado. Faça upload de um arquivo .xlsx ou coloque-o em data/.")
        st.stop()

if not sheets:
    st.error("Não foi possível ler o arquivo. Verifique o formato e tente novamente.")
    st.stop()

df_raw, load_warnings = get_main_sheet(sheets)
for w in load_warnings:
    st.sidebar.warning(w)

df = prepare_recommendations(df_raw)
df["base_dashboard"] = base_key

# Alerta de consistência com metadata
meta_alert = check_metadata_consistency(sheets, df)
if meta_alert:
    st.sidebar.info(f"ℹ️ {meta_alert}")

# Validação de colunas
data_alerts = validate_dataframe(df)

# ── Filtros globais ───────────────────────────────────────────────────────────
st.sidebar.markdown("---")
filters = build_sidebar_filters(df)
df_filtered = apply_filters(df, filters)

st.sidebar.markdown("---")
st.sidebar.caption(f"Base: **{base_options[base_key]}**")
st.sidebar.caption(f"Fonte: `{source_label}`")
st.sidebar.caption(f"**{len(df_filtered)}** de **{len(df)}** recomendações exibidas")

# ── Pré-cálculos globais ──────────────────────────────────────────────────────
kpis = calculate_global_kpis(df_filtered)
kpis_all = calculate_global_kpis(df)
df_uf = calculate_uf_metrics(df_filtered)
df_carrier = calculate_carrier_metrics(df_filtered)

active_review_row = _active_strategy_review()
if active_review_row is not None:
    PMP_ATUAL_DASH = pd.to_numeric(active_review_row.get("PMP_baseline_total"), errors="coerce")
    PMP_RECOMENDADO_DASH = pd.to_numeric(active_review_row.get("PMP_reco_total"), errors="coerce")
    SLA_BASELINE_DASH = pd.to_numeric(active_review_row.get("SLA_baseline_total"), errors="coerce")
    SLA_RECOMENDADO_DASH = pd.to_numeric(active_review_row.get("SLA_reco_total"), errors="coerce")
else:
    PMP_ATUAL_DASH = PMP_ATUAL_TOTAL
    PMP_RECOMENDADO_DASH = PMP_RECOMENDADO_TOTAL
    SLA_BASELINE_DASH = SLA_BASELINE_TOTAL
    SLA_RECOMENDADO_DASH = SLA_RECOMENDADO_TOTAL

# ── Header ────────────────────────────────────────────────────────────────────
render_header(len(df_filtered), len(df), f"{base_options[base_key]} · {source_label}")

if data_alerts:
    with st.expander("⚠️ Alertas de qualidade dos dados", expanded=False):
        for a in data_alerts:
            st.warning(a)

if df_filtered.empty:
    st.warning("Nenhuma recomendação encontrada com os filtros selecionados. Ajuste os filtros no sidebar.")
    st.stop()

# ── Abas ─────────────────────────────────────────────────────────────────────
tab_labels = [
    "1 · Visão Executiva",
    "2 · Mapa Brasil",
    "3 · Ranking de Oportunidades",
    "4 · Transportadoras",
    "5 · UF × Transportadora",
    "6 · Simulador de Rollout",
    "7 · Governança & Exportação",
    "8 · Dados Brutos",
    "9 · Estratégias",
]
if base_key == "gobeaute":
    tab_labels.append("10 · GoBeaute Marcas")
tabs = st.tabs(tab_labels)


# ════════════════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO EXECUTIVA
# ════════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    insight(
        "O modelo recomenda ajustes de prazo com foco em reduzir PMP sem romper a governança de SLA. "
        "Reduções indicam oportunidades de promessa mais competitiva; aumentos indicam proteção "
        "em regiões ou transportadoras onde o prazo atual pode estar agressivo demais."
    )

    # ── KPIs primários ────────────────────────────────────────────────────────
    sec("Métricas executivas — PMP & SLA")
    _ganho_abs = PMP_ATUAL_DASH - PMP_RECOMENDADO_DASH
    _red_pct   = (PMP_RECOMENDADO_DASH / PMP_ATUAL_DASH - 1) * 100 if PMP_ATUAL_DASH else np.nan
    _delta_sla = (SLA_RECOMENDADO_DASH - SLA_BASELINE_DASH) * 100

    kpi_row([
        kpi("PMP Atual",        fmt_dias(PMP_ATUAL_DASH),
            badge="referência", badge_cls="b-blue", accent="#3498DB"),
        kpi("PMP Recomendado",  fmt_dias(PMP_RECOMENDADO_DASH),
            badge=f"▼ {PMP_RECOMENDADO_DASH - PMP_ATUAL_DASH:+.2f} d",
            badge_cls="b-green", accent="#2ECC71"),
        kpi("Ganho de PMP",     fmt_dias(_ganho_abs),
            badge="redução no prazo médio", badge_cls="b-teal", accent="#1ABC9C"),
        kpi("Redução %",        f"{_red_pct:.1f}%",
            badge="vs. PMP atual", badge_cls="b-orange", accent="#E67E22"),
        kpi("SLA Recomendado",  f"{SLA_RECOMENDADO_DASH*100:.1f}%",
            badge=f"▲ +{_delta_sla:.1f} p.p.", badge_cls="b-purple", accent="#9B59B6"),
    ])

    # ── KPIs secundários ──────────────────────────────────────────────────────
    sec("Volume & cobertura")
    _share_pct = kpis["share_impactado"] * 100 if not np.isnan(kpis["share_impactado"]) else 0.0
    _red_share = kpis["n_reducoes"] / kpis["n_total"] * 100 if kpis["n_total"] else 0
    _aum_share = kpis["n_aumentos"] / kpis["n_total"] * 100 if kpis["n_total"] else 0

    kpi_row([
        kpi("SLA Baseline",     f"{SLA_BASELINE_DASH*100:.1f}%",
            badge="pré-recomendação", badge_cls="b-gray", accent="#5D6D7E", size="md"),
        kpi("Share Impactado",  fmt_share(_share_pct),
            badge="da base de pedidos", badge_cls="b-blue", accent="#2980B9", size="md"),
        kpi("Recomendações",    fmt_num(kpis["n_total"]),
            badge="grupos CCEP × transportadora", badge_cls="b-gray", accent="#E67E22", size="md"),
        kpi("↓ Reduções",       fmt_num(kpis["n_reducoes"]),
            badge=f"{_red_share:.0f}% do total", badge_cls="b-green", accent="#27AE60", size="md"),
        kpi("↑ Proteções SLA",  fmt_num(kpis["n_aumentos"]),
            badge=f"{_aum_share:.0f}% do total", badge_cls="b-orange", accent="#F39C12", size="md"),
    ])

    # ── KPIs de escopo ────────────────────────────────────────────────────────
    sec("Escopo geográfico & operacional")
    kpi_row([
        kpi("UFs Impactadas",       fmt_num(kpis["n_ufs"]),
            badge="de 27 estados", badge_cls="b-purple", accent="#8E44AD", size="sm"),
        kpi("Transportadoras",      fmt_num(kpis["n_transportadoras"]),
            badge="carriers ativos", badge_cls="b-blue", accent="#2C3E50", size="sm"),
        kpi("CCEPs Distintos",      fmt_num(kpis["n_cceps"]),
            badge="faixas de CEP", badge_cls="b-teal", accent="#16A085", size="sm"),
    ], widths=[1, 1, 1])

    st.markdown("")

    col_wf, col_dist = st.columns([3, 2])
    with col_wf:
        st.plotly_chart(build_waterfall_kpi(), use_container_width=True)
    with col_dist:
        st.plotly_chart(build_type_distribution(df_filtered), use_container_width=True)

    col_sla, col_uf = st.columns([2, 3])
    with col_sla:
        st.plotly_chart(build_sla_comparison(), use_container_width=True)
    with col_uf:
        st.plotly_chart(
            build_ranking_chart(df_filtered, "uf_primaria", "impacto_pond",
                                "Top UFs por Impacto Ponderado", top_n=10, color=AZUL),
            use_container_width=True,
        )

    st.plotly_chart(
        build_ranking_chart(df_filtered, "transportadora", "impacto_pond",
                            "Top Transportadoras por Impacto Ponderado", top_n=10, color="#8E44AD"),
        use_container_width=True,
    )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 2 — MAPA BRASIL
# ════════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    insight(
        "O mapa mostra a distribuição geográfica do impacto das recomendações. "
        "Estados com maior impacto ponderado devem ser priorizados no rollout, "
        "pois combinam ganho de prazo e relevância na base."
    )

    metric_options = list(METRIC_LABELS.keys())
    metric_sel = st.selectbox(
        "Métrica do mapa",
        metric_options,
        format_func=lambda k: METRIC_LABELS[k],
        index=0,
    )

    geojson = load_geojson()

    if df_uf.empty:
        st.warning("Sem dados agregados por UF para o filtro atual.")
    else:
        col_map, col_rank = st.columns([3, 1])
        with col_map:
            if geojson is not None:
                fig_map = build_brazil_map(df_uf, metric_sel, geojson)
                if fig_map:
                    st.plotly_chart(fig_map, use_container_width=True)
                else:
                    st.info("GeoJSON carregado, mas sem dados mapeáveis.")
                    st.plotly_chart(build_uf_bar_fallback(df_uf, metric_sel), use_container_width=True)
            else:
                st.info("ℹ️ GeoJSON não disponível — exibindo ranking por UF.")
                st.plotly_chart(build_uf_bar_fallback(df_uf, metric_sel), use_container_width=True)

        with col_rank:
            st.markdown("**Ranking UFs**")
            label_col = METRIC_LABELS.get(metric_sel, metric_sel)
            if metric_sel in df_uf.columns:
                rank_df = (
                    df_uf[["uf", metric_sel]]
                    .sort_values(metric_sel, ascending=False)
                    .reset_index(drop=True)
                )
                rank_df.index += 1
                rank_df.columns = ["UF", label_col]
                st.dataframe(rank_df, use_container_width=True, height=500)

        st.markdown("---")
        st.markdown("**Tabela agregada por UF**")
        st.dataframe(df_uf, use_container_width=True)
        st.download_button(
            "⬇️ Baixar agregado UF (.csv)",
            to_csv_download(df_uf),
            "uf_agregado.csv",
            "text/csv",
        )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 3 — RANKING DE OPORTUNIDADES
# ════════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    insight(
        "Priorize as recomendações com maior impacto ponderado "
        "(ganho_prazo × share_base). Reduções trazem competitividade; "
        "aumentos protegem o SLA em rotas desafiadoras."
    )

    df_red = df_filtered[df_filtered["tipo_recomendacao"] == "Redução de prazo"].sort_values(
        "impacto_pond", ascending=False
    )
    df_aum = df_filtered[df_filtered["tipo_recomendacao"] == "Aumento de prazo"].sort_values(
        "impacto_abs", ascending=False
    )

    cols_tabela = [
        c for c in [
            "transportadora", "uf", "cidade", "ccep_str", "qtd_pedidos",
            "share_base_pct", "prazo_atual", "prazo_recomendado",
            "diff_prazo", "ganho_prazo", "impacto_pond", "tipo_recomendacao",
            "sla_esperado", "fhat_at_k", "lb_at_k", "n_eff_at_k", "decision_mode",
        ]
        if c in df_filtered.columns
    ]

    tab_red, tab_aum, tab_ccep = st.tabs(["↓ Top Reduções", "↑ Top Proteções SLA", "📍 Por CCEP"])

    with tab_red:
        st.markdown(f"**Top 20 maiores oportunidades de redução** ({len(df_red)} totais)")
        st.dataframe(df_red[cols_tabela].head(20), use_container_width=True)
        st.plotly_chart(
            build_ranking_chart(df_red, "uf_primaria", "impacto_pond",
                                "UFs com Maior Redução Potencial", top_n=15, color=VERDE),
            use_container_width=True,
        )

    with tab_aum:
        st.markdown(f"**Top 20 maiores aumentos de proteção SLA** ({len(df_aum)} totais)")
        st.dataframe(df_aum[cols_tabela].head(20), use_container_width=True)
        st.plotly_chart(
            build_ranking_chart(df_aum, "uf_primaria", "impacto_abs",
                                "UFs com Maior Necessidade de Proteção", top_n=15, color=LARANJA),
            use_container_width=True,
        )

    with tab_ccep:
        st.markdown("**Top CCEPs por impacto ponderado**")
        if "ccep_str" in df_filtered.columns:
            top_ccep = (
                df_filtered.groupby("ccep_str")["impacto_pond"]
                .sum()
                .reset_index()
                .sort_values("impacto_pond", ascending=False)
                .head(20)
            )
            st.dataframe(top_ccep, use_container_width=True)
            st.plotly_chart(
                build_ranking_chart(df_filtered, "ccep_str", "impacto_pond",
                                    "Top 20 CCEPs por Impacto Ponderado", top_n=20, color=AZUL),
                use_container_width=True,
            )

    st.markdown("---")
    st.markdown("**Scatter: Share × Ganho de Prazo**")
    st.plotly_chart(build_scatter_opportunity(df_filtered), use_container_width=True)

    st.markdown("---")
    st.markdown("**Tabela detalhada (filtrada)**")
    st.dataframe(df_filtered[cols_tabela], use_container_width=True)

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        "⬇️ Baixar Top Reduções (.csv)",
        to_csv_download(df_red[cols_tabela]),
        "top_reducoes.csv", "text/csv",
    )
    col_dl2.download_button(
        "⬇️ Baixar Base Filtrada (.csv)",
        to_csv_download(df_filtered[cols_tabela]),
        "base_filtrada.csv", "text/csv",
    )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 4 — TRANSPORTADORAS
# ════════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    insight(
        "Identifique transportadoras com maior ganho potencial, maior necessidade "
        "de ajuste de prazo e maior volume afetado para priorizar o rollout operacional."
    )

    if df_carrier.empty:
        st.warning("Sem dados de transportadoras para o filtro atual.")
    else:
        # KPI cards por transportadora (top 4)
        sec("Top transportadoras por ganho ponderado")
        top4 = df_carrier.head(4)
        _carr_accents = ["#8E44AD", "#2ECC71", "#3498DB", "#E67E22"]
        kpi_row([
            kpi(
                row["transportadora"].replace("_", " ").title(),
                fmt_dias(row.get("ganho_ponderado", 0)),
                badge=f"{int(row.get('qtd_recomendacoes', 0))} recomendações",
                badge_cls="b-gray",
                accent=_carr_accents[i % len(_carr_accents)],
                size="md",
            )
            for i, (_, row) in enumerate(top4.iterrows())
        ])

        st.markdown("---")
        col_imp, col_share = st.columns(2)
        with col_imp:
            st.plotly_chart(
                build_ranking_chart(df_carrier, "transportadora", "impacto_pond_total",
                                    "Impacto Ponderado por Transportadora", top_n=10, color="#8E44AD"),
                use_container_width=True,
            )
        with col_share:
            st.plotly_chart(
                build_ranking_chart(df_carrier, "transportadora", "share_impactado",
                                    "Share Impactado por Transportadora", top_n=10, color=AZUL),
                use_container_width=True,
            )

        st.plotly_chart(build_stacked_carrier(df_carrier), use_container_width=True)
        st.plotly_chart(build_boxplot_carrier(df_filtered), use_container_width=True)

        st.markdown("---")
        st.markdown("**Tabela consolidada por transportadora**")
        st.dataframe(df_carrier, use_container_width=True)

        st.markdown("**Tabela granular filtrada por transportadora**")
        carr_sel = st.selectbox(
            "Selecionar transportadora",
            ["(todas)"] + sorted(df_filtered["transportadora"].dropna().unique().tolist()),
        )
        df_carr_detail = df_filtered if carr_sel == "(todas)" else df_filtered[df_filtered["transportadora"] == carr_sel]
        cols_tabela_c = [
            c for c in [
                "transportadora", "uf", "cidade", "ccep_str", "share_base_pct",
                "prazo_atual", "prazo_recomendado", "diff_prazo", "ganho_prazo",
                "impacto_pond", "tipo_recomendacao",
            ] if c in df_carr_detail.columns
        ]
        st.dataframe(df_carr_detail[cols_tabela_c], use_container_width=True)
        st.download_button(
            "⬇️ Baixar tabela transportadora (.csv)",
            to_csv_download(df_carrier),
            "transportadoras.csv", "text/csv",
        )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 5 — UF × TRANSPORTADORA
# ════════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    insight(
        "O heatmap cruza UF e transportadora para localizar combinações críticas "
        "que concentram maior oportunidade ou risco de SLA."
    )

    metric_hm = st.selectbox(
        "Métrica do heatmap",
        list(METRIC_LABELS.keys()),
        format_func=lambda k: METRIC_LABELS[k],
        key="heatmap_metric",
    )

    try:
        pivot = calculate_uf_carrier_matrix(df_filtered, metric_hm)
        if pivot is not None and not pivot.empty:
            st.plotly_chart(
                build_heatmap_uf_carrier(
                    pivot,
                    title=f"Heatmap UF × Transportadora — {METRIC_LABELS[metric_hm]}",
                    colorscale="YlOrRd" if "impacto" in metric_hm or "qtd" in metric_hm else "RdYlGn",
                ),
                use_container_width=True,
            )
            st.markdown("**Tabela cruzada**")
            st.dataframe(pivot.round(3), use_container_width=True)
            st.download_button(
                "⬇️ Baixar matriz UF × Transportadora (.csv)",
                to_csv_download(pivot.reset_index()),
                "uf_transportadora.csv", "text/csv",
            )
        else:
            st.info("Sem dados suficientes para gerar o heatmap.")
    except Exception as e:
        st.error(f"Erro ao gerar heatmap: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# ABA 6 — SIMULADOR DE ROLLOUT
# ════════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    insight(
        "O simulador estima o efeito executivo de aplicar apenas parte das recomendações. "
        "Ele não substitui uma nova execução do modelo, mas ajuda a comparar cenários de rollout."
    )

    st.markdown("### ⚙️ Configurações do Cenário")

    with st.expander("Filtros do simulador", expanded=True):
        sim_col1, sim_col2 = st.columns(2)

        with sim_col1:
            apply_all = st.checkbox("Aplicar todas as recomendações", value=True)
            only_red = st.checkbox("Apenas reduções de prazo", value=False)
            only_aum = st.checkbox("Apenas aumentos de prazo", value=False)

        with sim_col2:
            share_min_sim = st.number_input(
                "Share mínimo (%)", min_value=0.0, max_value=100.0,
                value=0.0, step=0.01, format="%.2f",
            )
            ganho_min_sim = st.number_input(
                "Ganho mínimo (dias)", min_value=0.0, max_value=30.0,
                value=0.0, step=0.1, format="%.1f",
            )
            top_n_sim = st.number_input(
                "Top N recomendações por impacto (0 = todas)",
                min_value=0, max_value=500, value=0, step=10,
            )

        ufs_disponiveis = sorted(df["uf_primaria"].dropna().unique().tolist()) if "uf_primaria" in df.columns else []
        ufs_sim = st.multiselect("UFs incluídas no cenário", ufs_disponiveis, default=[])

        carriers_disponiveis = sorted(df["transportadora"].dropna().unique().tolist())
        carriers_sim = st.multiselect("Transportadoras incluídas", carriers_disponiveis, default=[])

    # Construir df do cenário
    df_sim = df.copy()

    if not apply_all:
        if only_red:
            df_sim = df_sim[df_sim["tipo_recomendacao"] == "Redução de prazo"]
        if only_aum:
            df_sim = df_sim[df_sim["tipo_recomendacao"] == "Aumento de prazo"]

    if share_min_sim > 0 and "share_base_pct" in df_sim.columns:
        df_sim = df_sim[df_sim["share_base_pct"] >= share_min_sim]

    if ganho_min_sim > 0 and "ganho_prazo" in df_sim.columns:
        df_sim = df_sim[df_sim["ganho_prazo"] >= ganho_min_sim]

    if ufs_sim and "uf_primaria" in df_sim.columns:
        df_sim = df_sim[df_sim["uf_primaria"].isin(ufs_sim)]

    if carriers_sim:
        df_sim = df_sim[df_sim["transportadora"].isin(carriers_sim)]

    if top_n_sim > 0 and "impacto_pond" in df_sim.columns:
        df_sim = df_sim.sort_values("impacto_pond", ascending=False).head(top_n_sim)

    kpis_sim = simulate_rollout(df_sim, df)

    st.markdown("")
    sec("Resultados do Cenário")

    kpi_row([
        kpi("Recomendações Aplicadas", fmt_num(kpis_sim["n_aplicadas"]),
            badge="do total de 374", badge_cls="b-orange", accent="#E67E22", size="md"),
        kpi("Share Afetado", fmt_share(kpis_sim["share_afetado"] * 100),
            badge="da base de pedidos", badge_cls="b-blue", accent="#2980B9", size="md"),
        kpi("↓ Reduções", fmt_num(kpis_sim["n_reducoes"]),
            badge="no cenário", badge_cls="b-green", accent="#27AE60", size="md"),
        kpi("↑ Proteções", fmt_num(kpis_sim["n_aumentos"]),
            badge="no cenário", badge_cls="b-orange", accent="#F39C12", size="md"),
    ])

    _sim_delta = kpis_sim["pmp_simulado"] - kpis_sim["pmp_atual"]
    _sim_sla_d = (kpis_sim["sla_simulado"] - kpis_sim["sla_baseline"]) * 100

    kpi_row([
        kpi("PMP Atual",     fmt_dias(kpis_sim["pmp_atual"]),
            badge="referência", badge_cls="b-blue", accent="#3498DB"),
        kpi("PMP Simulado",  fmt_dias(kpis_sim["pmp_simulado"]),
            badge=f"{_sim_delta:+.2f} d vs atual",
            badge_cls="b-green" if _sim_delta < 0 else "b-red", accent="#2ECC71"),
        kpi("Redução Simulada", f"{kpis_sim['reducao_pct']*100:.1f}%",
            badge=f"de {fmt_dias(PMP_ATUAL_TOTAL)}", badge_cls="b-teal", accent="#1ABC9C"),
        kpi("SLA Simulado",  f"{kpis_sim['sla_simulado']*100:.1f}%",
            badge=f"+{_sim_sla_d:.2f} p.p. vs baseline",
            badge_cls="b-purple", accent="#9B59B6"),
    ])

    proporcao_pct = kpis_sim["proporcao"] * 100
    st.progress(min(kpis_sim["proporcao"], 1.0), text=f"Cobertura do impacto total: {proporcao_pct:.1f}%")

    st.caption(
        "⚠️ Nota: O simulador usa aproximação proporcional ao impacto ponderado "
        "e não substitui uma nova execução do modelo estatístico."
    )

    st.plotly_chart(
        build_simulator_comparison(kpis_all, kpis_sim),
        use_container_width=True,
    )

    if not df_sim.empty:
        st.markdown("**Recomendações aplicadas no cenário**")
        cols_sim = [
            c for c in [
                "transportadora", "uf", "ccep_str", "prazo_atual", "prazo_recomendado",
                "diff_prazo", "ganho_prazo", "impacto_pond", "tipo_recomendacao",
            ] if c in df_sim.columns
        ]
        st.dataframe(df_sim[cols_sim].sort_values("impacto_pond", ascending=False), use_container_width=True)
        st.download_button(
            "⬇️ Baixar cenário simulado (.csv)",
            to_csv_download(df_sim[cols_sim]),
            "cenario_simulado.csv", "text/csv",
        )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 7 — GOVERNANÇA & EXPORTAÇÃO
# ════════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    insight(
        "Controle o status de cada recomendação e exporte a base completa para "
        "uso operacional. O arquivo Excel final contém múltiplas abas prontas para rollout."
    )

    df_rollout = build_rollout_table(df_filtered)

    STATUS_OPTS = ["Pendente", "Aprovado", "Aplicado", "Recusado", "Revisar"]

    st.markdown("### 📋 Tabela de Controle de Rollout")
    st.caption("Edite o status de cada recomendação antes de exportar.")

    df_edited = st.data_editor(
        df_rollout,
        column_config={
            "status_rollout": st.column_config.SelectboxColumn(
                "Status Rollout",
                options=STATUS_OPTS,
                required=True,
            ),
            "prioridade": st.column_config.SelectboxColumn(
                "Prioridade",
                options=["Alta", "Média", "Baixa"],
                required=True,
            ),
        },
        use_container_width=True,
        num_rows="fixed",
        height=500,
    )

    st.markdown("---")
    st.markdown("### ⬇️ Exportações")

    # Agregações para exportação
    df_uf_exp = calculate_uf_metrics(df_filtered)
    df_carr_exp = calculate_carrier_metrics(df_filtered)
    try:
        df_uf_carr_exp = calculate_uf_carrier_matrix(df_filtered, "impacto_pond_total")
        df_uf_carr_reset = df_uf_carr_exp.reset_index() if df_uf_carr_exp is not None else pd.DataFrame()
    except Exception:
        df_uf_carr_reset = pd.DataFrame()

    meta_sheet = sheets.get("metadata", pd.DataFrame())
    kpis_sheet = sheets.get("kpis_total", pd.DataFrame())

    excel_bytes = to_excel_download({
        "recomendacoes_filtradas": df_filtered,
        "rollout": df_edited,
        "uf": df_uf_exp,
        "transportadora": df_carr_exp,
        "uf_transportadora": df_uf_carr_reset,
        "kpis_executivos": pd.DataFrame([kpis_all]),
        "metadata": meta_sheet,
    })

    col_xlsx, col_csv1, col_csv2 = st.columns(3)
    col_xlsx.download_button(
        "📥 Exportar Excel completo (.xlsx)",
        data=excel_bytes,
        file_name="prazo_otimizado_rollout.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    col_csv1.download_button(
        "⬇️ Base filtrada (.csv)",
        to_csv_download(df_filtered),
        "recomendacoes_filtradas.csv", "text/csv",
        use_container_width=True,
    )
    col_csv2.download_button(
        "⬇️ Rollout (.csv)",
        to_csv_download(df_edited),
        "rollout.csv", "text/csv",
        use_container_width=True,
    )

    col_uf_dl, col_carr_dl = st.columns(2)
    col_uf_dl.download_button(
        "⬇️ Agregado UF (.csv)",
        to_csv_download(df_uf_exp),
        "uf.csv", "text/csv",
        use_container_width=True,
    )
    col_carr_dl.download_button(
        "⬇️ Agregado Transportadora (.csv)",
        to_csv_download(df_carr_exp),
        "transportadora.csv", "text/csv",
        use_container_width=True,
    )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 8 — DADOS BRUTOS
# ════════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown("### 🗃️ Preview do DataFrame Principal")
    st.dataframe(df.head(50), use_container_width=True)

    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("**Colunas detectadas**")
        col_df = pd.DataFrame({
            "Coluna": df.columns.tolist(),
            "Tipo": [str(df[c].dtype) for c in df.columns],
            "Nulos": [df[c].isna().sum() for c in df.columns],
        })
        st.dataframe(col_df, use_container_width=True, height=400)

    with col_info2:
        meta = sheets.get("metadata", pd.DataFrame())
        kpis_t = sheets.get("kpis_total", sheets.get("kpis", pd.DataFrame()))
        if not meta.empty:
            st.markdown("**Metadata do arquivo**")
            st.dataframe(meta.astype(str), use_container_width=True)
        if not kpis_t.empty:
            st.markdown("**KPIs do arquivo (kpis_total)**")
            st.dataframe(kpis_t.astype(str), use_container_width=True)

    st.markdown("---")
    st.markdown("**Alertas de qualidade**")
    if data_alerts:
        for a in data_alerts:
            st.warning(a)
    else:
        st.success("Nenhum alerta de qualidade detectado.")

    st.markdown("**Nulos por coluna**")
    nulls = df.isna().sum().reset_index()
    nulls.columns = ["Coluna", "Nulos"]
    nulls = nulls[nulls["Nulos"] > 0]
    if nulls.empty:
        st.success("Nenhum valor nulo encontrado.")
    else:
        st.dataframe(nulls, use_container_width=True)

    st.markdown("---")
    st.download_button(
        "⬇️ Baixar base tratada (.csv)",
        to_csv_download(df),
        "base_tratada.csv", "text/csv",
    )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 9 — ESTRATÉGIAS
# ════════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown("### Estratégias de SLA e PMP")
    insight(
        "Esta aba lê diretamente as abas geradas pelos notebooks "
        "(review_estrategias, df_estrategias, kpis e streamlit_input). "
        "Use-a para comparar os cenários combinados, inclusive as variantes com e sem UF SP."
    )

    review = _sheet("review_estrategias")
    df_estrategias = _sheet("df_estrategias")
    kpis_file = _sheet("kpis")
    streamlit_input = _sheet("streamlit_input")

    if review.empty:
        st.warning("Aba `review_estrategias` não encontrada no arquivo carregado.")
    else:
        numeric_cols = [
            "selected_groups", "selected_orders",
            "SLA_baseline_total", "SLA_reco_total", "Delta_SLA_total",
            "PMP_baseline_total", "PMP_reco_total", "Delta_PMP_total",
            "portfolio_sla_est", "portfolio_pmp_est",
        ]
        for col in numeric_cols:
            if col in review.columns:
                review[col] = pd.to_numeric(review[col], errors="coerce")

        active = _active_strategy_review()
        if active is not None:
            st.caption(f"Estratégia ativa no dashboard: `{active.get('strategy')}`")
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(
                kpi("SLA cenário", fmt_pct(active.get("SLA_reco_total")),
                    badge=f"Δ {active.get('Delta_SLA_total', np.nan) * 100:+.2f} p.p."
                    if pd.notna(active.get("Delta_SLA_total", np.nan)) else "",
                    badge_cls="b-purple", accent="#9B59B6", size="md"),
                unsafe_allow_html=True,
            )
            c2.markdown(
                kpi("PMP cenário", fmt_dias(active.get("PMP_reco_total")),
                    badge=f"Δ {active.get('Delta_PMP_total', np.nan):+.2f} d"
                    if pd.notna(active.get("Delta_PMP_total", np.nan)) else "",
                    badge_cls="b-teal", accent="#1ABC9C", size="md"),
                unsafe_allow_html=True,
            )
            c3.markdown(
                kpi("Grupos selecionados", fmt_num(active.get("selected_groups")),
                    badge="estratégia", badge_cls="b-blue", accent="#2980B9", size="md"),
                unsafe_allow_html=True,
            )
            c4.markdown(
                kpi("Pedidos cobertos", fmt_num(active.get("selected_orders")),
                    badge="base histórica", badge_cls="b-orange", accent="#E67E22", size="md"),
                unsafe_allow_html=True,
            )

        st.markdown("#### Review das estratégias")
        display_cols = [
            c for c in [
                "strategy", "excluded_ufs", "reached_target",
                "selected_groups", "selected_orders",
                "SLA_baseline_total", "SLA_reco_total", "Delta_SLA_total",
                "PMP_baseline_total", "PMP_reco_total", "Delta_PMP_total",
                "portfolio_sla_est", "portfolio_pmp_est",
            ] if c in review.columns
        ]
        sort_cols = [c for c in ["reached_target", "Delta_PMP_total", "SLA_reco_total"] if c in review.columns]
        if sort_cols:
            review_show = review.sort_values(sort_cols, ascending=[False] * len(sort_cols))
        else:
            review_show = review
        st.dataframe(review_show[display_cols], use_container_width=True)

        if {"PMP_reco_total", "SLA_reco_total", "strategy"}.issubset(review.columns):
            plot_df = review.dropna(subset=["PMP_reco_total", "SLA_reco_total"]).copy()
            if not plot_df.empty:
                size_col = "selected_orders" if "selected_orders" in plot_df.columns else None
                fig = px.scatter(
                    plot_df,
                    x="PMP_reco_total",
                    y="SLA_reco_total",
                    color="strategy",
                    size=size_col,
                    hover_data=[c for c in ["excluded_ufs", "selected_groups", "Delta_PMP_total"] if c in plot_df.columns],
                    labels={
                        "PMP_reco_total": "PMP recomendado",
                        "SLA_reco_total": "SLA recomendado",
                        "strategy": "Estratégia",
                    },
                    title="Fronteira prática: SLA x PMP por estratégia",
                )
                fig.add_hline(y=0.96, line_dash="dash", line_color="#F39C12", annotation_text="Target 96%")
                fig.update_layout(height=460, margin=dict(l=10, r=10, t=55, b=10))
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### KPIs por estratégia")
        if kpis_file.empty:
            st.info("Aba `kpis` não encontrada.")
        else:
            st.dataframe(kpis_file.astype(str), use_container_width=True, height=360)
    with col_s2:
        st.markdown("#### Base de estratégias")
        if df_estrategias.empty:
            st.info("Aba `df_estrategias` não encontrada.")
        else:
            st.dataframe(df_estrategias.head(300), use_container_width=True, height=360)

    st.markdown("---")
    export_tabs = {
        "review_estrategias": review,
        "kpis": kpis_file,
        "df_estrategias": df_estrategias,
        "streamlit_input": streamlit_input,
    }
    export_tabs = {k: v for k, v in export_tabs.items() if isinstance(v, pd.DataFrame) and not v.empty}
    if export_tabs:
        st.download_button(
            "⬇️ Baixar pacote de estratégias (.xlsx)",
            data=to_excel_download(export_tabs),
            file_name=f"estrategias_{base_key}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


# ════════════════════════════════════════════════════════════════════════════════
# ABA 10 — GOBEAUTE MARCAS
# ════════════════════════════════════════════════════════════════════════════════
if base_key == "gobeaute":
    with tabs[9]:
        st.markdown("### 🧴 GoBeaute — Marcas e Canais")
        insight(
            "Esta visão usa a base bruta da GoBeaute para abrir a leitura por Canal de Vendas/marca, "
            "algo que não existe na Gocase. O carregamento é opcional porque a base bruta é grande."
        )

        load_brand = st.checkbox("Carregar base bruta para análise de marcas", value=False)
        raw_dir = pathlib.Path(__file__).parent.parent / "base_gobeaute"
        raw_files = []
        if raw_dir.exists():
            raw_files = [
                p for p in raw_dir.glob("*.xlsx")
                if not p.name.startswith("~$") and not p.name.lower().startswith("depara")
            ]
        raw_file = max(raw_files, key=lambda p: p.stat().st_mtime) if raw_files else None

        if raw_file is None:
            st.warning("Nenhuma base bruta GoBeaute encontrada em `base_gobeaute/`.")
        elif not load_brand:
            st.info(f"Base detectada: `{raw_file.name}`. Marque a opção acima para carregar a análise.")
        else:
            brand_cols = [
                "Canal de Vendas", "Praça", "Transportadora", "UF", "Cidade do Destinatário",
                "Status Transportador", "Performance", "Performance Transp.",
                "Custo Frete", "Preço Frete", "Valor da Nota",
                "Prazo transportadora dias úteis",
            ]

            @st.cache_data(show_spinner="Carregando base bruta GoBeaute…")
            def _load_brand_base(path: str) -> pd.DataFrame:
                raw = pd.read_excel(path, usecols=lambda c: c in brand_cols, engine="openpyxl")
                raw.columns = raw.columns.map(lambda c: str(c).strip())
                raw["marca"] = (
                    raw.get("Canal de Vendas", pd.Series(index=raw.index, dtype=object))
                    .astype(str).str.strip().str.split("-").str[0].str.upper()
                )
                for col in ["Custo Frete", "Preço Frete", "Valor da Nota", "Prazo transportadora dias úteis"]:
                    if col in raw.columns:
                        raw[col] = pd.to_numeric(raw[col], errors="coerce")
                return raw

            raw_brand = _load_brand_base(str(raw_file))
            st.caption(f"Base bruta: `{raw_file.name}` · {len(raw_brand):,} linhas")

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(kpi("Pedidos brutos", fmt_num(len(raw_brand)), size="md"), unsafe_allow_html=True)
            c2.markdown(kpi("Marcas/canais", fmt_num(raw_brand["marca"].nunique()), size="md", accent="#9B59B6"), unsafe_allow_html=True)
            c3.markdown(kpi("UFs", fmt_num(raw_brand["UF"].nunique()) if "UF" in raw_brand.columns else "-", size="md", accent="#2ECC71"), unsafe_allow_html=True)
            c4.markdown(kpi("Transportadoras", fmt_num(raw_brand["Transportadora"].nunique()) if "Transportadora" in raw_brand.columns else "-", size="md", accent="#F39C12"), unsafe_allow_html=True)

            brand = raw_brand.groupby("marca", dropna=False).agg(
                pedidos=("marca", "count"),
                prazo_medio=("Prazo transportadora dias úteis", "mean"),
                custo_frete=("Custo Frete", "mean"),
                preco_frete=("Preço Frete", "mean"),
                ticket_medio=("Valor da Nota", "mean"),
            ).reset_index().sort_values("pedidos", ascending=False)
            brand["share"] = brand["pedidos"] / len(raw_brand)

            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(
                    build_ranking_chart(brand, "marca", "pedidos", "Top marcas/canais por volume", top_n=15, color=AZUL),
                    use_container_width=True,
                )
            with col_b:
                st.plotly_chart(
                    build_ranking_chart(brand, "marca", "prazo_medio", "Prazo médio por marca", top_n=15, color=LARANJA),
                    use_container_width=True,
                )

            if {"marca", "UF"}.issubset(raw_brand.columns):
                top_brands = brand.head(10)["marca"].tolist()
                brand_uf = (
                    raw_brand[raw_brand["marca"].isin(top_brands)]
                    .groupby(["marca", "UF"]).size().reset_index(name="pedidos")
                )
                st.markdown("**Marca × UF**")
                st.dataframe(
                    brand_uf.sort_values("pedidos", ascending=False).head(100),
                    use_container_width=True,
                )

            if {"marca", "Transportadora"}.issubset(raw_brand.columns):
                brand_carrier = (
                    raw_brand[raw_brand["marca"].isin(brand.head(10)["marca"])]
                    .groupby(["marca", "Transportadora"]).size().reset_index(name="pedidos")
                    .sort_values("pedidos", ascending=False)
                )
                st.markdown("**Mix de transportadoras por marca**")
                st.dataframe(brand_carrier, use_container_width=True)

            st.markdown("**Resumo por marca/canal**")
            st.dataframe(brand, use_container_width=True)
