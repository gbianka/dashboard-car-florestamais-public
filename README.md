# 🌿 Dashboard Interativo — Projeto CAR / PRA

Dashboard analítico para o Relatório Final do Projeto de Cadastro Ambiental Rural (CAR), cobrindo os três escopos: Análise de CAR, Retificação de CAR e Elegibilidade para PRA.

## Instalação

```bash
# Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

O dashboard abrirá automaticamente em `http://localhost:8501`.

## Uso

1. **Upload**: Faça upload do arquivo `.xlsx` com as abas "Cadastros CAR", "Retificação CAR" e "Elegibilidade CAR"
2. **Filtros**: Use a barra lateral para filtrar por município, status, ciclo, elegibilidade, UF e período
3. **Modo**: Alterne entre Estratégico (visão executiva) e Tático (detalhamento operacional)
4. **Exportar**: Baixe relatórios Excel/CSV refletindo os filtros ativos

Sem upload, o dashboard carrega dados sintéticos de demonstração.

## Estrutura do Código

```
dashboard_car/
├── app.py                 # Aplicação principal (módulos §1–§8)
├── requirements.txt       # Dependências Python
├── README.md              # Este arquivo
└── .streamlit/
    └── config.toml        # Tema e configurações do Streamlit
```

### Módulos dentro de `app.py`

| Seção | Descrição |
|-------|-----------|
| §1 | Imports, configuração, paleta de cores, coordenadas |
| §2 | Gerador de dataset sintético (fallback sem upload) |
| §3 | Carregamento e limpeza de dados (normalização) |
| §4 | Filtros globais (município, status, ciclo, elegibilidade, UF, período) |
| §5 | KPIs e métricas derivadas |
| §6 | Modo Estratégico: funil, Sankey, mapas, evolução temporal |
| §7 | Modo Tático: detalhamento por escopo, gargalos |
| §8 | Exportação de relatórios (.xlsx, .csv) |

## Funcionalidades

### Modo Estratégico
- 8 KPIs consolidados com métricas de variação
- Funil de CARs por escopo
- Diagrama Sankey (fluxo entre escopos)
- Condição final e elegibilidade (donuts)
- Mapas interativos (Plotly Mapbox): análises por município + elegibilidade por UF
- Evolução temporal (linha + barras)

### Modo Tático
- Análise de CAR: ciclos, complexidade, tipo de imóvel, RL, desmatamento, produtividade, condição por município
- Retificação: status, tipo de atendimento, fase SISNAMA, tabela detalhada
- Elegibilidade PRA: 11 critérios (stacked), por UF, fitofisionomia
- Gargalos: taxa de pendências por ciclo, concentração de pendências por município, municípios críticos

### Exportação
- Excel (.xlsx) com 5 abas: KPIs, Filtros, Análise, Retificação, Elegibilidade, Resumo Municípios
- CSV de KPIs

## Colunas esperadas

### Aba "Cadastros CAR"
`Nº DO CAR`, `Município`, `Técnico`, `LOTE`, `Ciclo de análise`, `Condição final do cadastro`, `Situação da Análise Externa`, `Status final`, `Grau de Complexidade`, `Tipo de imóvel`, `Área`, `Data início`, `Data fim`, `Tem Ativo ou Passivo de RL?`, `Desmatamento entre 2008 e 2018`, `Desmatamento após 2018`

### Aba "Retificação CAR"
`Código do CAR`, `Município`, `Status de Retificação`, `Tipo de Atendimento`, `Lote`, `Fase do Processo (SISNAMA)`, `Condição WFS`

### Aba "Elegibilidade CAR"
`Nº DO CAR`, `Município`, `UF`, `Elegibilidade`, `em_priorit`, `rvn_minima`, `prodes_1ha`, `sobrep_car`, `cnfp`, `uc`, `MF imóvel`, `Soma - MF dos Imóveis`, `prodes_6ha`, `embargo_ib`, `quilombola`, `fitofision`
