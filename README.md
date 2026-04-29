# Prazo Otimizado — Dashboard Executivo

## Objetivo

Painel Streamlit para visualizar recomendações de ajuste de PMP por UF, transportadora e CCEP,
com proteção de SLA. Baseado no output final do modelo de Prazo Otimizado Brasil.

## Como rodar

```bash
cd prazo_otimizado_dashboard
pip install -r requirements.txt
streamlit run app.py
```

## Dados esperados

Coloque o arquivo Excel com a aba `df_gold` dentro da pasta `data/`:

```
data/prazo_otimizado_brasil_fhat96_20260428_1716.xlsx
```

O app também aceita upload manual via interface.

## Principais métricas (referência executiva)

| Métrica | Valor |
|---|---|
| PMP Atual | 3,84 dias |
| PMP Recomendado | 3,33 dias |
| Ganho de PMP | −0,51 dia |
| Redução % | −13,3% |
| SLA Baseline | 95,8% |
| SLA Recomendado | 96,4% |
| Delta SLA | +0,6 p.p. |

## Abas do painel

1. **Visão Executiva** — KPIs, waterfall e rankings gerais
2. **Mapa Brasil** — Choropleth por UF com métrica selecionável
3. **Ranking de Oportunidades** — Top reduções, proteções e CCEPs
4. **Transportadoras** — Análise por transportadora
5. **UF × Transportadora** — Heatmap cruzado
6. **Simulador de Rollout** — Cenários de aplicação parcial
7. **Governança & Exportação** — Controle de status e downloads
8. **Dados Brutos** — Preview, qualidade e download da base tratada

## Mapa do Brasil (GeoJSON)

O app tenta carregar o GeoJSON de estados em `assets/brasil_ufs.geojson`.
Se não encontrar, faz download automático da API do IBGE e salva o arquivo.
Se o download falhar, exibe ranking de barras como fallback.

## Observação

O simulador usa aproximação proporcional ao impacto ponderado e não substitui
uma nova execução do modelo estatístico.
