"""
╔══════════════════════════════════════════════════════════════════╗
║  DASHBOARD INTERATIVO — PROJETO CAR / PRA                       ║
║  Análise de CAR · Retificação · Elegibilidade PRA               ║
║  Projeto Floresta+ - Amazônia Legal                                                  ║
╚══════════════════════════════════════════════════════════════════╝

Estrutura modular:
  §1  Imports e configuração
  §2  Dataset sintético (fallback)
  §3  Carregamento e limpeza de dados
  §4  Filtros globais
  §5  KPIs e métricas derivadas
  §6  Modo Estratégico
  §7  Modo Tático
  §8  Exportação de relatórios
"""

# ════════════════════════════════════════════════════════════════
# §1  IMPORTS E CONFIGURAÇÃO
# ════════════════════════════════════════════════════════════════

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
import json
from datetime import datetime
import unicodedata
import warnings
warnings.filterwarnings("ignore")

# ── Bibliotecas geoespaciais (opcionais) ──
try:
    import geopandas as gpd
    import folium
    from streamlit_folium import st_folium
    HAS_GEO = True
except ImportError:
    HAS_GEO = False

st.set_page_config(
    page_title="Dashboard CAR/PRA",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Fonte Manrope ──
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded" rel="stylesheet">
<style>
html, body, .stApp {
    font-family: 'Manrope', sans-serif;
}
/* Esconder setinhas dos deltas nos st.metric */
[data-testid="stMetricDelta"] svg {
    display: none;
}
/* Estilizar popover de ajuda como ícone nativo */
[data-testid="stPopover"] > button {
    background: none !important;
    border: 1.5px solid #9E9E9E !important;
    border-radius: 50% !important;
    width: 24px !important;
    height: 24px !important;
    min-width: 24px !important;
    padding: 0 !important;
    font-size: 14px !important;
    color: #9E9E9E !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin-top: 8px !important;
}
[class*="material-symbols"],
[class*="material-icons"],
[class*="icon"] span,
button[kind] span {
    font-family: 'Material Symbols Rounded' !important;
    -webkit-font-feature-settings: 'liga';
    font-feature-settings: 'liga';
}
</style>
""", unsafe_allow_html=True)

FONT_FAMILY = "Manrope, sans-serif"

# ── Template Plotly com fonte Manrope ──
import plotly.io as pio
_font = dict(family=FONT_FAMILY)
_plotly_template = pio.templates["plotly"]
_plotly_template.layout.font = _font
pio.templates.default = "plotly"

# ── Paleta de cores ──
COR = {
    "verde_escuro": "#1B5E20", "verde": "#2E7D32", "verde_claro": "#66BB6A",
    "amarelo": "#FFC107", "laranja": "#FF9800", "vermelho": "#E53935",
    "azul": "#1565C0", "azul_claro": "#42A5F5", "cinza": "#9E9E9E",
    "roxo": "#7B1FA2", "bg": "#FAFAFA", "texto": "#212121",
}
PALETA = [COR["verde_escuro"], COR["verde_claro"], COR["amarelo"],
          COR["laranja"], COR["vermelho"], COR["azul"], COR["roxo"], COR["azul_claro"]]

# ── Coordenadas aproximadas de municípios do AM ──
COORDS_MUNICIPIOS = {
    "Manaus": (-3.12, -60.02), "Rio Preto da Eva": (-2.70, -59.70),
    "Itacoatiara": (-3.14, -58.44), "Careiro": (-3.77, -60.37),
    "Presidente Figueiredo": (-2.03, -60.02), "Parintins": (-2.63, -56.74),
    "Autazes": (-3.58, -59.13), "Manacapuru": (-3.29, -60.62),
    "Iranduba": (-3.28, -60.19), "Borba": (-4.39, -59.59),
    "Maués": (-3.38, -57.72), "Codajás": (-3.84, -62.06),
    "Lábrea": (-7.26, -64.80), "Tefé": (-3.35, -64.71),
    "Humaitá": (-7.51, -63.02), "Novo Airão": (-2.62, -60.94),
    "Caapiranga": (-2.63, -61.21), "Coari": (-4.08, -63.14),
    "Manicoré": (-5.81, -61.30), "Apuí": (-7.20, -59.89),
    "São Gabriel da Cachoeira": (0.13, -67.09), "Barcelos": (-0.97, -62.93),
    "Tabatinga": (-4.25, -69.94), "Benjamin Constant": (-4.38, -70.03),
    "Eirunepé": (-6.66, -69.87), "Envira": (-7.44, -70.02),
    "Jutaí": (-2.75, -66.76), "Fonte Boa": (-2.51, -66.10),
}

COORDS_UF = {
    "AM": (-3.12, -60.02), "PA": (-1.46, -48.50), "AP": (0.03, -51.07),
    "RR": (2.82, -60.67), "MT": (-15.60, -56.10), "RO": (-8.76, -63.90),
    "MA": (-2.53, -44.28), "AC": (-9.97, -67.81), "TO": (-10.18, -48.33),
}


# ── Formatação pt-BR ──
def fmt_int(v):
    """Formata inteiro com separador de milhar pt-BR (ponto)."""
    return f"{int(v):,}".replace(",", ".")

def fmt_dec(v, casas=1):
    """Formata decimal com vírgula e milhar com ponto (pt-BR)."""
    s = f"{v:,.{casas}f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s

def fmt_pct(v, casas=1):
    """Formata percentual pt-BR (vírgula decimal)."""
    return f"{fmt_dec(v, casas)}%"


_ORDEM_GRUPO_MF = ["0 a 1 MF", "1 a 2 MF", "2 a 3 MF", "3 MF ou mais", "Não informado"]
_CORES_GRUPO_MF = {
    "0 a 1 MF":    "#1B5E20",  # verde escuro
    "1 a 2 MF":    "#66BB6A",  # verde claro
    "2 a 3 MF":    "#FFC107",  # amarelo
    "3 MF ou mais": "#FF9800", # laranja
    "Não informado": "#9E9E9E", # cinza
}


def classificar_grupo_mf(valor):
    """Classifica valor numérico de módulo fiscal em grupo para o sumário executivo."""
    if pd.isna(valor):
        return "Não informado"
    try:
        v = float(valor)
    except (ValueError, TypeError):
        return "Não informado"
    if v <= 1:
        return "0 a 1 MF"
    elif v <= 2:
        return "1 a 2 MF"
    elif v <= 3:
        return "2 a 3 MF"
    else:
        return "3 MF ou mais"


# ════════════════════════════════════════════════════════════════
# §3  CARREGAMENTO E LIMPEZA DE DADOS
# ════════════════════════════════════════════════════════════════

def normalizar_texto(s):
    if pd.isna(s): return s
    s = str(s).strip()
    return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")



def normalizar_condicao(val):
    if pd.isna(val): return "Outros"
    v = str(val).lower().strip()
    if "pendência" in v or "pendencia" in v: return "Com pendências"
    if "conformidade" in v and "cota" in v: return "Conformidade (CRA)"
    if "conformidade" in v and "ativo" in v: return "Conformidade (ativos)"
    if "conformidade" in v: return "Em conformidade"
    if "regularização" in v: return "Aguard. regularização"
    if "aprovado" in v: return "Aprovado"
    return "Outros"


@st.cache_data
def carregar_e_limpar(file_bytes, nome_arquivo):
    """Carrega xlsx e normaliza as 3 abas."""
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    abas = xls.sheet_names

    # Detectar abas
    aba_a = next((a for a in abas if "cadastro" in a.lower() or "anális" in a.lower()), abas[0])
    aba_r = next((a for a in abas if "retif" in a.lower()), abas[1] if len(abas) > 1 else abas[0])
    aba_e = next((a for a in abas if "elegib" in a.lower()), abas[2] if len(abas) > 2 else abas[0])

    df_a = pd.read_excel(io.BytesIO(file_bytes), sheet_name=aba_a)
    df_r = pd.read_excel(io.BytesIO(file_bytes), sheet_name=aba_r)
    df_e = pd.read_excel(io.BytesIO(file_bytes), sheet_name=aba_e)

    # ── Strip em todas as colunas de texto ──
    for df in [df_a, df_r, df_e]:
        df.columns = df.columns.str.strip()
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    # ── Limpeza Análise ──
    if "Ciclo de análise" in df_a.columns:
        df_a["Ciclo de análise"] = pd.to_numeric(df_a["Ciclo de análise"], errors="coerce")
    for col_data in ["Data início", "Data fim"]:
        if col_data in df_a.columns:
            df_a[col_data] = pd.to_datetime(df_a[col_data], errors="coerce")
    if "Área" in df_a.columns:
        df_a["Área"] = pd.to_numeric(df_a["Área"], errors="coerce")
    if "Grau de Complexidade" in df_a.columns:
        df_a["Grau de Complexidade"] = df_a["Grau de Complexidade"].astype(str).str.strip().str.capitalize()
        df_a.loc[~df_a["Grau de Complexidade"].isin(["Verde", "Amarelo", "Vermelho"]), "Grau de Complexidade"] = np.nan
    if "Condição final do cadastro" in df_a.columns:
        df_a["Condição_norm"] = df_a["Condição final do cadastro"].apply(normalizar_condicao)

    # ── Limpeza Retificação ──
    # Coluna do CAR: padronizar para "Código do CAR"
    if "Código do CAR" not in df_r.columns:
        for c in df_r.columns:
            if c.strip().lower() == "código do car":
                df_r = df_r.rename(columns={c: "Código do CAR"})
                break

    # ── Limpeza Elegibilidade ──
    # Coluna do CAR: padronizar para "Nº DO CAR"
    if "Nº DO CAR" not in df_e.columns:
        for c in df_e.columns:
            if c.strip().lower() == "nº do car":
                df_e = df_e.rename(columns={c: "Nº DO CAR"})
                break

    return df_a, df_r, df_e


# ════════════════════════════════════════════════════════════════
# §4  FILTROS GLOBAIS
# ════════════════════════════════════════════════════════════════

def aplicar_filtros(df_a, df_r, df_e, filtros):
    """Aplica filtros globais aos 3 DataFrames."""
    fa, fr, fe = df_a.copy(), df_r.copy(), df_e.copy()

    # Código do CAR (busca parcial, case-insensitive)
    if filtros.get("car"):
        busca_car = filtros["car"].strip()
        if "Nº DO CAR" in fa.columns:
            fa = fa[fa["Nº DO CAR"].astype(str).str.contains(busca_car, case=False, na=False)]
        if "Código do CAR" in fr.columns:
            fr = fr[fr["Código do CAR"].astype(str).str.contains(busca_car, case=False, na=False)]
        if "Nº DO CAR" in fe.columns:
            fe = fe[fe["Nº DO CAR"].astype(str).str.contains(busca_car, case=False, na=False)]

    # Município
    if filtros.get("municipios"):
        muns = filtros["municipios"]
        if "Município" in fa.columns: fa = fa[fa["Município"].isin(muns)]
        if "Município" in fr.columns: fr = fr[fr["Município"].isin(muns)]
        if "Município" in fe.columns: fe = fe[fe["Município"].isin(muns)]

    # Lote
    if filtros.get("lotes"):
        lotes = filtros["lotes"]
        if "LOTE" in fa.columns: fa = fa[fa["LOTE"].isin(lotes)]
        if "Lote" in fr.columns: fr = fr[fr["Lote"].isin(lotes)]
        if "LOTE" in fe.columns: fe = fe[fe["LOTE"].isin(lotes)]

    # Status (condição normalizada)
    if filtros.get("status") and "Condição_norm" in fa.columns:
        fa = fa[fa["Condição_norm"].isin(filtros["status"])]

    # Ciclos
    if filtros.get("ciclos") and "Ciclo de análise" in fa.columns:
        fa = fa[fa["Ciclo de análise"].isin(filtros["ciclos"])]

    # Elegibilidade
    if filtros.get("elegibilidade") and "Elegibilidade" in fe.columns:
        fe = fe[fe["Elegibilidade"].isin(filtros["elegibilidade"])]

    # UF
    if filtros.get("ufs") and "UF" in fe.columns:
        fe = fe[fe["UF"].isin(filtros["ufs"])]

    # Período (mantém registros sem data)
    if filtros.get("data_inicio") and filtros.get("data_fim") and "Data fim" in fa.columns:
        sem_data = fa["Data fim"].isna()
        dentro_periodo = (fa["Data fim"] >= pd.Timestamp(filtros["data_inicio"])) & \
                         (fa["Data fim"] <= pd.Timestamp(filtros["data_fim"]))
        fa = fa[sem_data | dentro_periodo]

    # Propagar filtro de CARs
    if filtros.get("municipios") or filtros.get("status"):
        cars_filtrados_a = set(fa["Nº DO CAR"].dropna().unique()) if "Nº DO CAR" in fa.columns else set()
        if cars_filtrados_a and "Código do CAR" in fr.columns:
            fr = fr[fr["Código do CAR"].isin(cars_filtrados_a) | fr["Município"].isin(filtros.get("municipios", []))]

    return fa, fr, fe


# ════════════════════════════════════════════════════════════════
# §5  KPIs E MÉTRICAS DERIVADAS
# ════════════════════════════════════════════════════════════════

def calcular_kpis(df_a, df_r, df_e):
    """Calcula todos os KPIs do projeto."""
    kpis = {}

    # Volume
    kpis["cars_analise"] = df_a["Nº DO CAR"].nunique() if "Nº DO CAR" in df_a.columns else len(df_a)
    kpis["registros_analise"] = len(df_a)
    kpis["cars_retif"] = df_r["Código do CAR"].nunique() if "Código do CAR" in df_r.columns else len(df_r)
    kpis["registros_retif"] = len(df_r)
    kpis["cars_eleg"] = df_e["Nº DO CAR"].nunique() if "Nº DO CAR" in df_e.columns else len(df_e)
    kpis["registros_eleg"] = len(df_e)
    kpis["municipios_analise"] = df_a["Município"].nunique() if "Município" in df_a.columns else 0
    kpis["municipios_retif"] = df_r["Município"].nunique() if "Município" in df_r.columns else 0
    kpis["municipios_eleg"] = df_e["Município"].nunique() if "Município" in df_e.columns else 0
    kpis["tecnicos"] = df_a["Técnico Vinculado"].nunique() if "Técnico Vinculado" in df_a.columns else 0
    kpis["ufs_eleg"] = df_e["UF"].nunique() if "UF" in df_e.columns else 0

    # Retificação
    if "Status de Retificação" in df_r.columns:
        sr = df_r["Status de Retificação"].value_counts()
        kpis["retif_retificados"] = int(sr.get("Retificado", 0))
        kpis["retif_finalizados"] = int(sr.get("Finalizado", 0))
        kpis["retif_outros_menos_inscritos"] = int(sr.sum() - sr.get("Inscrito", 0) - kpis["retif_retificados"] - kpis["retif_finalizados"])
        kpis["pct_retificado"] = kpis["retif_retificados"] / max(len(df_r), 1) * 100
        # CARs distintos com status (exclui vazios) — Painel Estratégico
        if "Código do CAR" in df_r.columns:
            _mask_todos = (
                df_r["Status de Retificação"].notna()
                & (df_r["Status de Retificação"].astype(str).str.strip() != "")
            )
            kpis["cars_retif_todos"] = df_r[_mask_todos]["Código do CAR"].nunique()
        else:
            kpis["cars_retif_todos"] = 0
        # CARs distintos trabalhados (exclui "Inscrito") — Sankey
        if "Código do CAR" in df_r.columns:
            _mask_retif = _mask_todos & (df_r["Status de Retificação"] != "Inscrito")
            kpis["cars_retif_retificados"] = df_r[_mask_retif]["Código do CAR"].nunique()
        else:
            kpis["cars_retif_retificados"] = 0
    else:
        kpis["retif_retificados"] = kpis["retif_finalizados"] = 0
        kpis["pct_retificado"] = 0
        kpis["cars_retif_retificados"] = 0
        kpis["cars_retif_todos"] = 0

    # Ciclos
    if "Ciclo de análise" in df_a.columns and "Nº DO CAR" in df_a.columns:
        ciclos = df_a.groupby("Nº DO CAR")["Ciclo de análise"].max()
        kpis["media_ciclos"] = ciclos.mean()
        kpis["pct_1ciclo"] = (ciclos == 1).mean() * 100
    else:
        kpis["media_ciclos"] = 0
        kpis["pct_1ciclo"] = 0

    # Pendências
    if "Situação da Análise Externa" in df_a.columns:
        sit = df_a["Situação da Análise Externa"].value_counts()
        total_sit = sit.sum()
        kpis["pct_pendencia"] = sit.get("CAR com pendência(s)", 0) / max(total_sit, 1) * 100
        kpis["pct_sem_pendencia"] = sit.get("CAR sem pendência(s)", 0) / max(total_sit, 1) * 100
    else:
        kpis["pct_pendencia"] = 0
        kpis["pct_sem_pendencia"] = 0

    # Elegibilidade
    if "Elegibilidade" in df_e.columns:
        eleg = df_e["Elegibilidade"].value_counts()
        total_e = len(df_e)
        kpis["n_inelegivel"] = eleg.get("Inelegível", 0)
        kpis["n_fase1"] = eleg.get("Fase 1", 0)
        kpis["n_fase2"] = eleg.get("Fase 2", 0)
        kpis["pct_elegivel"] = (kpis["n_fase1"] + kpis["n_fase2"]) / max(total_e, 1) * 100
    else:
        kpis["n_inelegivel"] = kpis["n_fase1"] = kpis["n_fase2"] = 0
        kpis["pct_elegivel"] = 0

    # Cruzamento
    cars_A = set(df_a["Nº DO CAR"].dropna().unique()) if "Nº DO CAR" in df_a.columns else set()
    cars_R = set(df_r["Código do CAR"].dropna().unique()) if "Código do CAR" in df_r.columns else set()
    cars_E = set(df_e["Nº DO CAR"].dropna().unique()) if "Nº DO CAR" in df_e.columns else set()
    kpis["so_analise"] = len(cars_A - cars_R - cars_E)
    kpis["a_r"] = len(cars_A & cars_R - cars_E)
    kpis["a_e"] = len(cars_A & cars_E - cars_R)
    kpis["todos_3"] = len(cars_A & cars_R & cars_E)
    kpis["so_retif"] = len(cars_R - cars_A - cars_E)
    kpis["so_eleg"] = len(cars_E - cars_A - cars_R)
    kpis["total_distintos"] = len(cars_A | cars_R | cars_E)

    return kpis


# ════════════════════════════════════════════════════════════════
# §6  MODO ESTRATÉGICO
# ════════════════════════════════════════════════════════════════

def render_estrategico(df_a, df_r, df_e, kpis):
    """Renderiza o painel estratégico (visão executiva)."""

    # ── Métricas de destaque ──
    _t1, _t2 = st.columns([20, 1])
    _t1.markdown("### 📊 Indicadores-Chave do Projeto")
    with _t2.popover("❓"):
        st.markdown(
            "Os **CARs distintos por escopo** não somam ao total "
            "porque muitos CARs aparecem em mais de um escopo "
            "(ex: Análise + Retificação).\n\n"
            "O **total de CARs distintos** é a **união** dos 3 conjuntos, "
            "contando cada CAR apenas uma vez."
        )
    # ── Linha 1: Visão Geral ──
    a1, a2, a3, a4, a5 = st.columns(5)
    a1.metric("Atuação do Projeto", fmt_int(kpis['registros_analise'] + kpis['registros_retif'] + kpis['registros_eleg']),
              f"{fmt_int(kpis['total_distintos'])} CARs distintos")
    a2.metric("Análise", fmt_int(kpis['registros_analise']),
              f"{fmt_int(kpis['cars_analise'])} CARs distintos")
    a3.metric("Retificação", fmt_int(kpis['registros_retif']),
              f"{fmt_int(kpis['cars_retif'])} CARs distintos")
    a4.metric("Elegibilidade", fmt_int(kpis['registros_eleg']),
              f"{fmt_int(kpis['ufs_eleg'])} UFs")
    a5.metric("Municípios", fmt_int(kpis['municipios_analise']))


    st.divider()

    # ── Funil + Sankey ──
    _E = "Painel Estratégico"
    col_left, col_right = st.columns([1, 1])

    with col_left:
        if _pode_ver(_E, "funil"):
            st.markdown("#### Distribuição por Escopo")
            _tree_df = pd.DataFrame({
                "Escopo": ["Análise", "Retificação", "Elegibilidade"],
                "CARs": [kpis["cars_analise"], kpis["cars_retif"], kpis["cars_eleg"]],
            })
            fig_tree = px.treemap(
                _tree_df, path=["Escopo"], values="CARs",
                color="Escopo",
                color_discrete_map={"Análise": COR["verde_escuro"], "Retificação": COR["azul"], "Elegibilidade": COR["laranja"]},
            )
            fig_tree.update_traces(textinfo="label+value+percent root", textfont=dict(size=15))
            fig_tree.update_layout(height=380, margin=dict(l=5, r=5, t=5, b=5), showlegend=False)
            st.plotly_chart(fig_tree, use_container_width=True)

    with col_right:
        if _pode_ver(_E, "sankey"):
            st.markdown("#### Fluxo entre Escopos")
            # Cruzamento local: apenas CARs efetivamente retificados
            _sA = set(df_a["Nº DO CAR"].dropna().unique()) if "Nº DO CAR" in df_a.columns else set()
            if "Status de Retificação" in df_r.columns and "Código do CAR" in df_r.columns:
                _sR = set(df_r[df_r["Status de Retificação"] != "Inscrito"]["Código do CAR"].dropna().unique())
            else:
                _sR = set(df_r["Código do CAR"].dropna().unique()) if "Código do CAR" in df_r.columns else set()
            _sE = set(df_e["Nº DO CAR"].dropna().unique()) if "Nº DO CAR" in df_e.columns else set()
            _so_a = len(_sA - _sR - _sE)
            _a_r  = len(_sA & _sR - _sE)
            _a_e  = len(_sA & _sE - _sR)
            _t3   = len(_sA & _sR & _sE)

            node_labels = ["Análise", "Só Análise", "Retificados", "Elegibilidade",
                           "Análise+Retif", "Análise+Eleg", "Todos 3"]
            node_values = [
                kpis["cars_analise"], _so_a, kpis["cars_retif_retificados"],
                kpis["cars_eleg"], _a_r, _a_e, _t3,
            ]
            node_labels_fmt = [f"{l} ({fmt_int(v)})" for l, v in zip(node_labels, node_values)]
            fig_sankey = go.Figure(go.Sankey(
                node=dict(
                    pad=18, thickness=22,
                    label=node_labels_fmt,
                    color=[COR["azul"], COR["cinza"], COR["laranja"],
                           COR["verde_claro"], COR["amarelo"], COR["verde"], COR["verde_escuro"]],
                ),
                link=dict(
                    source=[0, 0, 0, 0],
                    target=[1, 4, 5, 6],
                    value=[_so_a, _a_r, _a_e, _t3],
                    color=["rgba(158,158,158,0.25)", "rgba(255,193,7,0.3)",
                           "rgba(102,187,106,0.3)", "rgba(27,94,32,0.35)"],
                ),
                textfont=dict(color="black", size=12),
            ))
            fig_sankey.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_sankey, width="stretch")

    st.divider()

    # ── Condição Final + Elegibilidade ──
    col_a, col_b = st.columns([1, 1])

    with col_a:
        _visao_cond = st.radio(
            "Visão:", ["Normalizada", "Original"], horizontal=True,
            key="cond_estrategico", label_visibility="collapsed",
        )
        _col_cond = "Condição_norm" if _visao_cond == "Normalizada" else "Condição final do cadastro"
        if _col_cond in df_a.columns:
            # Apenas último ciclo por CAR (condição final real)
            if "Ciclo de análise" in df_a.columns and "Nº DO CAR" in df_a.columns:
                _df_uc = df_a.sort_values(["Nº DO CAR", "Ciclo de análise"]).drop_duplicates(subset="Nº DO CAR", keep="last")
            else:
                _df_uc = df_a.drop_duplicates(subset="Nº DO CAR", keep="last") if "Nº DO CAR" in df_a.columns else df_a
            cond = _df_uc[_col_cond].value_counts()
            _titulo_grafico("Condição Final (CARs únicos)", int(cond.sum()), kpis["cars_analise"], "####")
            cores_cond = {
                "Com pendências": COR["vermelho"], "Em conformidade": COR["verde_claro"],
                "Aguard. regularização": COR["amarelo"], "Conformidade (CRA)": COR["verde_escuro"],
                "Conformidade (ativos)": COR["verde"], "Aprovado": COR["azul"], "Outros": COR["cinza"],
            }
            fig_cond = px.pie(
                values=cond.values, names=cond.index, hole=0.45,
                color=cond.index,
                color_discrete_map=cores_cond if _visao_cond == "Normalizada" else {},
            )
            fig_cond.update_traces(textinfo="percent+value", textposition="auto")
            fig_cond.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                                   legend=dict(font=dict(size=10)))
            st.plotly_chart(fig_cond, width="stretch")

    with col_b:
        if "Elegibilidade" in df_e.columns:
            eleg = df_e["Elegibilidade"].value_counts()
            _titulo_grafico("Elegibilidade para PSA", int(eleg.sum()), len(df_e), "####")
            cores_eleg = {"Inelegível": COR["vermelho"], "Fase 1": COR["verde_claro"], "Fase 2": COR["verde_escuro"]}
            fig_eleg = px.pie(
                values=eleg.values, names=eleg.index, hole=0.45,
                color=eleg.index, color_discrete_map=cores_eleg,
            )
            fig_eleg.update_traces(textinfo="percent+value", textposition="auto")
            fig_eleg.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_eleg, width="stretch")

    st.divider()

    # ── Grupo de Módulo Fiscal ──
    st.markdown("#### 🏡 Grupo de Módulo Fiscal")

    _MF_FONTES = [
        ("Análise",      df_a, "MF"),
        ("Retificação",  df_r, "Módulos Fiscais"),
        ("Elegibilidade", df_e, "MF imóvel"),
    ]
    _CORES_ESCOPO_MF = {
        "Análise":       COR["verde_escuro"],
        "Retificação":   COR["azul"],
        "Elegibilidade": COR["laranja"],
    }

    _mf_series = {}
    for _esc, _df_src, _col_mf in _MF_FONTES:
        if _col_mf in _df_src.columns:
            _s = pd.to_numeric(_df_src[_col_mf], errors="coerce").apply(classificar_grupo_mf)
            _mf_series[_esc] = (_s, _col_mf, len(_df_src))

    if _mf_series:
        _grupos_validos = [g for g in _ORDEM_GRUPO_MF
                           if any(g in sd[0].values for sd in _mf_series.values())]
        _col_mf1, _col_mf2 = st.columns([3, 2])

        with _col_mf1:
            st.markdown("##### Imóveis por Grupo de MF — por Escopo")
            fig_mf_grp = go.Figure()
            for _esc, (_s, _col_usada, _total) in _mf_series.items():
                _ct = _s.value_counts().reindex(_grupos_validos, fill_value=0)
                fig_mf_grp.add_trace(go.Bar(
                    name=f"{_esc} ('{_col_usada}')",
                    x=_ct.index, y=_ct.values,
                    marker_color=_CORES_ESCOPO_MF[_esc],
                    text=[fmt_int(v) if v else "" for v in _ct.values],
                    textposition="auto",
                ))
            fig_mf_grp.update_layout(
                barmode="group", height=400,
                margin=dict(l=20, r=10, t=10, b=60),
                yaxis_title="Imóveis", xaxis_title="Grupo de Módulo Fiscal",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=10)),
            )
            st.plotly_chart(fig_mf_grp, width="stretch")

        with _col_mf2:
            _esc_pie = "Análise" if "Análise" in _mf_series else list(_mf_series.keys())[0]
            _s_pie, _col_pie, _tot_pie = _mf_series[_esc_pie]
            _ct_pie = _s_pie.value_counts().reindex(
                [g for g in _grupos_validos if g in _s_pie.values], fill_value=0
            )
            _titulo_grafico(f"Distribuição (%) — {_esc_pie}", int(_ct_pie.sum()), _tot_pie, "#####")
            fig_mf_pie = px.pie(
                values=_ct_pie.values, names=_ct_pie.index, hole=0.45,
                color=_ct_pie.index, color_discrete_map=_CORES_GRUPO_MF,
            )
            fig_mf_pie.update_traces(textinfo="percent+value", textposition="auto")
            fig_mf_pie.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10),
                                     legend=dict(font=dict(size=11)))
            st.plotly_chart(fig_mf_pie, width="stretch")
            st.caption(f"Fonte: coluna '{_col_pie}' da aba {_esc_pie}")
    else:
        st.info("Colunas de MF não encontradas. Esperadas: 'MF' (Análise), 'Módulos Fiscais' (Retificação), 'MF imóvel' (Elegibilidade).")

    st.divider()

    # ── Mapa territorial ──
    st.markdown("#### 🗺️ Distribuição Territorial")
    tab_mapa1, tab_mapa2 = st.tabs(["📍 Análises por Município", "📍 Elegibilidade por UF"])

    with tab_mapa1:
        if "Município" in df_a.columns:
            mun_counts = df_a["Município"].value_counts().reset_index()
            mun_counts.columns = ["Município", "Quantidade"]
            mun_geo = []
            for _, row in mun_counts.iterrows():
                nome = row["Município"].strip()
                for k, (lat, lon) in COORDS_MUNICIPIOS.items():
                    if k.upper() == nome.upper() or k.upper() in nome.upper() or nome.upper() in k.upper():
                        mun_geo.append({"Município": nome, "Quantidade": row["Quantidade"], "lat": lat, "lon": lon})
                        break
            if mun_geo:
                df_geo = pd.DataFrame(mun_geo)
                _titulo_grafico("Municípios mapeados", int(df_geo["Quantidade"].sum()), len(df_a), "#####")
                fig_map = px.scatter_mapbox(
                    df_geo, lat="lat", lon="lon", size="Quantidade",
                    color="Quantidade", color_continuous_scale="YlGn",
                    hover_name="Município", hover_data={"Quantidade": True, "lat": False, "lon": False},
                    size_max=40, zoom=4, mapbox_style="carto-positron",
                )
                fig_map.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_map, width="stretch")
            else:
                st.info("Coordenadas de municípios não encontradas para mapeamento.")

    with tab_mapa2:
        if "UF" in df_e.columns:
            eleg_uf = df_e.groupby("UF")["Elegibilidade"].value_counts().unstack(fill_value=0)
            map_data = []
            for uf, row in eleg_uf.iterrows():
                if uf in COORDS_UF:
                    lat, lon = COORDS_UF[uf]
                    total = row.sum()
                    elegivel = row.get("Fase 1", 0) + row.get("Fase 2", 0)
                    map_data.append({"UF": uf, "Total": total, "Elegível": elegivel,
                                     "Inelegível": row.get("Inelegível", 0),
                                     "Taxa Elegib.": fmt_pct(elegivel/max(total,1)*100),
                                     "lat": lat, "lon": lon})
            if map_data:
                df_map_uf = pd.DataFrame(map_data)
                fig_uf = px.scatter_mapbox(
                    df_map_uf, lat="lat", lon="lon", size="Total",
                    color="Elegível", color_continuous_scale="RdYlGn",
                    hover_name="UF", hover_data={"Total": True, "Elegível": True,
                                                  "Inelegível": True, "Taxa Elegib.": True,
                                                  "lat": False, "lon": False},
                    size_max=35, zoom=3, mapbox_style="carto-positron",
                )
                fig_uf.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig_uf, width="stretch")

    st.divider()

    # ── Evolução temporal ──

    def _agrupar_mensal(df, col_data, col_car):
        tmp = df.dropna(subset=[col_data]).copy()
        tmp[col_data] = pd.to_datetime(tmp[col_data], errors="coerce")
        tmp = tmp.dropna(subset=[col_data])
        if tmp.empty:
            return None
        tmp["Mês"] = tmp[col_data].dt.to_period("M").astype(str)
        return tmp.groupby("Mês").agg(
            total=(col_car, "count"),
            cars_unicos=(col_car, "nunique"),
        ).reset_index()

    fig_tempo = go.Figure()
    _tem_dados = False
    _fontes = []
    _total_com_data = 0
    _total_registros = len(df_a) + len(df_r) + len(df_e)

    # Análise — coluna fixa: "Data fim"
    if "Data fim" in df_a.columns:
        m_a = _agrupar_mensal(df_a, "Data fim", "Nº DO CAR")
        if m_a is not None and not m_a.empty:
            _tem_dados = True
            _total_com_data += int(m_a["total"].sum())
            _fontes.append("Análise: Data fim")
            fig_tempo.add_trace(go.Scatter(
                x=m_a["Mês"], y=m_a["total"], mode="lines+markers",
                name="Análise (mensal)", line=dict(color=COR["verde_escuro"], width=3),
            ))
            m_a["acumulado"] = m_a["cars_unicos"].cumsum()
            fig_tempo.add_trace(go.Bar(
                x=m_a["Mês"], y=m_a["cars_unicos"], name="CARs únicos (mensal)",
                marker_color=COR["verde_claro"], opacity=0.4,
            ))
            fig_tempo.add_trace(go.Scatter(
                x=m_a["Mês"], y=m_a["acumulado"], mode="lines",
                name="CARs únicos (acumulado)",
                line=dict(color=COR["verde_claro"], width=2, dash="dot"),
                yaxis="y2",
            ))

    # Retificação — coluna fixa: "Data da Última Retificação"
    _COL_DATA_RETIF = "Data da Última Retificação"
    _COL_CAR_RETIF = "Código do CAR"
    if _COL_DATA_RETIF in df_r.columns and _COL_CAR_RETIF in df_r.columns:
        m_r = _agrupar_mensal(df_r, _COL_DATA_RETIF, _COL_CAR_RETIF)
        if m_r is not None and not m_r.empty:
            _tem_dados = True
            _total_com_data += int(m_r["total"].sum())
            _fontes.append(f"Retificação: {_COL_DATA_RETIF}")
            fig_tempo.add_trace(go.Scatter(
                x=m_r["Mês"], y=m_r["total"], mode="lines+markers",
                name="Retificação", line=dict(color=COR["azul"], width=3),
            ))

    # Elegibilidade — sem coluna de data disponível na planilha

    if _tem_dados:
        _titulo_grafico("📈 Evolução Temporal", _total_com_data, _total_registros, "####")
        fig_tempo.update_layout(
            height=400, xaxis_tickangle=-45,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=40, r=40, t=40, b=80),
            yaxis_title="Registros / mês",
            yaxis2=dict(title="Acumulado", overlaying="y", side="right"),
        )
        st.plotly_chart(fig_tempo, width="stretch")
        st.caption("Colunas de data utilizadas: " + " | ".join(_fontes))
    else:
        st.info("Sem dados de datas para gerar evolução temporal.")

# ════════════════════════════════════════════════════════════════
# §7  MODO TÁTICO
# ════════════════════════════════════════════════════════════════

def _titulo_grafico(titulo, total_grafico, total_df, nivel="#####"):
    """Exibe título do gráfico com ícone de alerta inline se houver divergência."""
    diff = total_df - total_grafico
    if diff != 0:
        tooltip = (f"{fmt_int(total_grafico)} de {fmt_int(total_df)} registros "
                   f"({fmt_int(diff)} sem dados nesta coluna)")
        st.markdown(
            f'{nivel} {titulo} <span title="{tooltip}" style="cursor:help; font-size:0.85em;">⚠️</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"{nivel} {titulo}")


def render_tatico(df_a, df_r, df_e, kpis):
    """Renderiza o painel tático (visão operacional detalhada)."""

    tab_analise, tab_retif, tab_eleg, tab_gargalos = st.tabs([
        "🔍 Análise de CAR", "🔧 Retificação", "✅ Elegibilidade PSA", "⚠️ Gargalos"
    ])

    # ────────────────────────────────────────────────────────
    # TAB: ANÁLISE DE CAR
    # ────────────────────────────────────────────────────────
    with tab_analise:
        st.markdown("### Análise de CAR")

        total_a = len(df_a)

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Total de Análises", fmt_int(kpis['registros_analise']))
        a2.metric("CARs Únicos", fmt_int(kpis['cars_analise']))
        a3.metric("Municípios", fmt_int(kpis['municipios_analise']))
        a4.metric("CARs com Pendência", fmt_pct(kpis['pct_pendencia']),
                  delta=f"-{fmt_pct(kpis['pct_sem_pendencia'])} sem", delta_color="inverse")

        st.divider()

        col1, col2, col3 = st.columns(3)

        # Ciclos
        with col1:
            if "Ciclo de análise" in df_a.columns:
                cd = df_a["Ciclo de análise"].dropna()
                cd = cd[cd.isin([1, 2, 3, 4])]
                cd_counts = cd.value_counts().sort_index()
                _titulo_grafico("Ciclos de Análise", int(cd_counts.sum()), total_a)
                cores_c = [COR["verde_claro"], COR["amarelo"], COR["laranja"], COR["vermelho"]]
                fig_c = go.Figure(go.Bar(
                    x=[f"{int(c)}º" for c in cd_counts.index], y=cd_counts.values,
                    marker_color=cores_c[:len(cd_counts)],
                    text=[fmt_int(v) for v in cd_counts.values], textposition="auto",
                ))
                fig_c.update_layout(height=300, margin=dict(l=20, r=10, t=10, b=30),
                                    yaxis_title="Registros")
                st.plotly_chart(fig_c, width="stretch")

        # Complexidade
        with col2:
            if "Grau de Complexidade" in df_a.columns:
                comp = df_a["Grau de Complexidade"].dropna().value_counts()
                _titulo_grafico("Grau de Complexidade", int(comp.sum()), total_a)
                cores_comp = {"Verde": "#4CAF50", "Vermelho": "#F44336", "Amarelo": "#FFC107"}
                fig_comp = go.Figure(go.Bar(
                    x=comp.index, y=comp.values,
                    marker_color=[cores_comp.get(c, "#999") for c in comp.index],
                    text=[fmt_int(v) for v in comp.values], textposition="auto",
                ))
                fig_comp.update_layout(height=300, margin=dict(l=20, r=10, t=10, b=30))
                st.plotly_chart(fig_comp, width="stretch")

        # Tipo de imóvel
        with col3:
            if "Tipo de imóvel" in df_a.columns:
                tipo = df_a["Tipo de imóvel"].value_counts()
                _titulo_grafico("Tipo de Imóvel", int(tipo.sum()), total_a)
                tipo = tipo[tipo.index.isin(["IRU", "AST"])]
                fig_tipo = go.Figure(go.Bar(
                    x=["IRU", "AST"], y=tipo.values,
                    marker_color=[COR["azul"], COR["verde"]],
                    text=[fmt_int(v) for v in tipo.values], textposition="auto",
                ))
                fig_tipo.update_layout(height=300, margin=dict(l=20, r=10, t=10, b=30))
                st.plotly_chart(fig_tipo, width="stretch")

        # Grupo de Módulo Fiscal (Tático)
        st.markdown("##### Grupo de Módulo Fiscal")
        _MF_FONTES_T = [
            ("Análise",       df_a, "MF"),
            ("Retificação",   df_r, "Módulos Fiscais"),
            ("Elegibilidade", df_e, "MF imóvel"),
        ]
        _mf_series_t = {}
        for _esc_t, _df_t, _col_t in _MF_FONTES_T:
            if _col_t in _df_t.columns:
                _s_t = pd.to_numeric(_df_t[_col_t], errors="coerce").apply(classificar_grupo_mf)
                _mf_series_t[_esc_t] = (_s_t, _col_t, len(_df_t))

        if _mf_series_t:
            _grupos_t = [g for g in _ORDEM_GRUPO_MF
                         if any(g in sd[0].values for sd in _mf_series_t.values())]
            _cores_esc_t = {"Análise": COR["verde_escuro"], "Retificação": COR["azul"], "Elegibilidade": COR["laranja"]}
            _radio_esc = st.radio(
                "Escopo:", list(_mf_series_t.keys()), horizontal=True, key="mf_tatico_escopo"
            )
            _s_sel, _col_sel, _tot_sel = _mf_series_t[_radio_esc]
            _mf_ct = _s_sel.value_counts().reindex(
                [g for g in _grupos_t if g in _s_sel.values], fill_value=0
            )
            _ct1, _ct2, _ct3 = st.columns([2, 1, 1])
            with _ct1:
                _titulo_grafico(f"Grupo de MF — {_radio_esc}", int(_mf_ct.sum()), _tot_sel)
                fig_mf_t = go.Figure(go.Bar(
                    x=_mf_ct.index, y=_mf_ct.values,
                    marker_color=_cores_esc_t.get(_radio_esc, COR["cinza"]),
                    text=[fmt_int(v) for v in _mf_ct.values], textposition="auto",
                ))
                fig_mf_t.update_layout(height=300, margin=dict(l=20, r=10, t=10, b=30),
                                       yaxis_title="Imóveis")
                st.plotly_chart(fig_mf_t, width="stretch")
            with _ct2:
                for _g in _mf_ct.index:
                    _pct = _mf_ct[_g] / max(_mf_ct.sum(), 1) * 100
                    st.metric(_g, fmt_int(_mf_ct[_g]), fmt_pct(_pct))
            with _ct3:
                _sem_info = int((_s_sel == "Não informado").sum())
                st.metric(f"Total {_radio_esc}", fmt_int(_tot_sel))
                st.metric("Sem MF informado", fmt_int(_sem_info))
                if _sem_info:
                    st.caption(f"{fmt_pct(_sem_info / max(_tot_sel, 1) * 100)} sem dado")
            st.caption(f"📊 Coluna: '{_col_sel}' | Escopo: {_radio_esc}")
        else:
            st.info("ℹ️ Colunas de MF não encontradas nos escopos.")

        # Reserva Legal + Desmatamento
        col_rl, col_desm = st.columns(2)
        with col_rl:
            rl_col = "Tem Ativo ou Passivo de RL? (baseado no uso do solo)"
            if rl_col in df_a.columns:
                rl = df_a[rl_col].value_counts()
                _titulo_grafico("Reserva Legal (Ativo / Passivo)", int(rl.sum()), total_a)
                rl = rl[rl.index.isin(["Ativo", "Passivo", "OK", "Não vetorizada"])]
                cores_rl = {"Ativo": COR["verde_claro"], "Passivo": COR["vermelho"],
                            "OK": COR["azul"], "Não vetorizada": COR["cinza"]}
                fig_rl = px.pie(values=rl.values, names=rl.index, hole=0.45,
                               color=rl.index, color_discrete_map=cores_rl)
                fig_rl.update_traces(textinfo="percent+value")
                fig_rl.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_rl, width="stretch")

        with col_desm:
            desm_cols = ["Desmatamento entre 2008 e 2018", "Desmatamento após 2018"]
            if all(c in df_a.columns for c in desm_cols):
                d1 = df_a[desm_cols[0]].value_counts()
                d2 = df_a[desm_cols[1]].value_counts()
                menor = min(int(d1.sum()), int(d2.sum()))
                _titulo_grafico("Desmatamento Detectado", menor, total_a)
                d1 = d1[d1.index.isin(["Sim", "Não"])]
                d2 = d2[d2.index.isin(["Sim", "Não"])]
                fig_d = make_subplots(1, 2, specs=[[{"type": "domain"}, {"type": "domain"}]],
                                     subplot_titles=("2008–2018", "Após 2018"))
                fig_d.add_trace(go.Pie(
                    labels=d1.index, values=d1.values, hole=0.45,
                    marker_colors=[COR["verde_claro"] if i == "Não" else COR["vermelho"] for i in d1.index],
                    textinfo="percent+value",
                ), 1, 1)
                fig_d.add_trace(go.Pie(
                    labels=d2.index, values=d2.values, hole=0.45,
                    marker_colors=[COR["verde_claro"] if i == "Não" else COR["vermelho"] for i in d2.index],
                    textinfo="percent+value",
                ), 1, 2)
                fig_d.update_layout(height=320, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_d, width="stretch")

        # Produtividade por técnico
        st.markdown("##### Produtividade por Técnico")
        visao_tecnico = st.radio(
            "Visualização", ["Técnico Vinculado", "Análise Externa / Interna"],
            horizontal=True, key="radio_tecnico",
        )

        if visao_tecnico == "Técnico Vinculado" and "Técnico Vinculado" in df_a.columns:
            prod_all = df_a["Técnico Vinculado"].dropna()
            _titulo_grafico("Técnico Vinculado", len(prod_all), total_a)
            prod = prod_all.value_counts()
            df_prod = pd.DataFrame({"Técnico": prod.index, "Análises": prod.values})
            df_prod["label"] = df_prod["Análises"].apply(fmt_int)
            fig_prod = px.bar(df_prod, x="Técnico", y="Análises",
                              color_discrete_sequence=[COR["azul"]],
                              text="label")
            fig_prod.update_traces(textposition="auto")
            fig_prod.update_layout(height=350, xaxis_tickangle=-45, showlegend=False,
                                   margin=dict(l=40, r=20, t=20, b=80))
            st.plotly_chart(fig_prod, width="stretch")

        elif visao_tecnico == "Análise Externa / Interna":
            col_ext = "Técnico Análise Externa"
            col_int = "Técnico Análise Interna"
            if col_ext in df_a.columns and col_int in df_a.columns:
                ext = df_a[col_ext].dropna().value_counts()
                inter = df_a[col_int].dropna().value_counts()
                tecnicos_todos = sorted(set(ext.index) | set(inter.index))
                df_stack = pd.DataFrame({
                    "Técnico": tecnicos_todos,
                    "Análise Externa": [ext.get(t, 0) for t in tecnicos_todos],
                    "Análise Interna": [inter.get(t, 0) for t in tecnicos_todos],
                })
                df_stack["Total"] = df_stack["Análise Externa"] + df_stack["Análise Interna"]
                df_stack = df_stack.sort_values("Total", ascending=False)
                fig_stack = go.Figure()
                fig_stack.add_trace(go.Bar(
                    x=df_stack["Técnico"], y=df_stack["Análise Externa"],
                    name="Análise Externa", marker_color=COR["verde"],
                    text=[fmt_int(v) for v in df_stack["Análise Externa"]], textposition="auto",
                ))
                fig_stack.add_trace(go.Bar(
                    x=df_stack["Técnico"], y=df_stack["Análise Interna"],
                    name="Análise Interna", marker_color=COR["laranja"],
                    text=[fmt_int(v) for v in df_stack["Análise Interna"]], textposition="auto",
                ))
                fig_stack.update_layout(barmode="stack", height=350, xaxis_tickangle=-45,
                                        margin=dict(l=40, r=20, t=20, b=80),
                                        legend=dict(orientation="h", yanchor="bottom", y=1.02))
                st.plotly_chart(fig_stack, width="stretch")

        # Top municípios
        st.markdown("##### Condição por Município (Top 10)")
        _visao_cond_t = st.radio(
            "Visão:", ["Normalizada", "Original"], horizontal=True,
            key="cond_tatico", label_visibility="collapsed",
        )
        _col_cond_t = "Condição_norm" if _visao_cond_t == "Normalizada" else "Condição final do cadastro"
        if "Município" in df_a.columns and _col_cond_t in df_a.columns:
            top10 = df_a["Município"].value_counts().head(10).index
            df_t10 = df_a[df_a["Município"].isin(top10)]
            cross = pd.crosstab(df_t10["Município"], df_t10[_col_cond_t])
            cross = cross.reindex(top10)
            cores_cn = {
                "Com pendências": COR["vermelho"], "Em conformidade": COR["verde_claro"],
                "Aguard. regularização": COR["amarelo"], "Conformidade (CRA)": COR["verde_escuro"],
                "Conformidade (ativos)": COR["verde"], "Aprovado": COR["azul"], "Outros": COR["cinza"],
            }
            fig_mc = px.bar(cross, barmode="stack",
                           color_discrete_map=cores_cn if _visao_cond_t == "Normalizada" else {})
            fig_mc.update_layout(height=400, xaxis_tickangle=-45, legend=dict(font=dict(size=9)),
                                 margin=dict(l=40, r=20, t=20, b=80))
            st.plotly_chart(fig_mc, width="stretch")

    # ────────────────────────────────────────────────────────
    # TAB: RETIFICAÇÃO
    # ────────────────────────────────────────────────────────
    with tab_retif:
        st.markdown("### Retificação de CAR")
        total_r = len(df_r)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total de Retificações", fmt_int(kpis['registros_retif']))
        r2.metric("CARs Únicos", fmt_int(kpis['cars_retif']))
        r3.metric("Municípios", fmt_int(kpis['municipios_retif']))
        r4.metric("Retificados", fmt_int(kpis['cars_retif_retificados']),
                  f"{fmt_pct(kpis['pct_retificado'])} do escopo")

        st.divider()

        cr1, cr2 = st.columns(2)
        with cr1:
            if "Status de Retificação" in df_r.columns:
                sr = df_r["Status de Retificação"].value_counts()
                _titulo_grafico("Status da Retificação", int(sr.sum()), total_r)
                cores_sr = {"Retificado": COR["verde_claro"], "Finalizado": COR["verde_escuro"],
                            "Inscrito": COR["amarelo"]}
                fig_sr = go.Figure(go.Bar(
                    x=sr.index, y=sr.values,
                    marker_color=[cores_sr.get(s, COR["cinza"]) for s in sr.index],
                    text=[fmt_int(v) for v in sr.values], textposition="auto",
                ))
                fig_sr.update_layout(height=320, margin=dict(l=20, r=10, t=10, b=30))
                st.plotly_chart(fig_sr, width="stretch")

        with cr2:
            if "Tipo de Atendimento" in df_r.columns:
                atend = df_r["Tipo de Atendimento"].dropna().value_counts()
                _titulo_grafico("Tipo de Atendimento", int(atend.sum()), total_r)
                fig_at = px.bar(x=atend.values, y=atend.index, orientation="h",
                                color_discrete_sequence=[COR["laranja"]], text=atend.values)
                fig_at.update_traces(textposition="auto")
                fig_at.update_layout(height=320, yaxis=dict(autorange="reversed"),
                                     margin=dict(l=10, r=10, t=10, b=30))
                st.plotly_chart(fig_at, width="stretch")

        # Fase do processo
        if "Fase do Processo (SISNAMA)" in df_r.columns:
            fase = df_r["Fase do Processo (SISNAMA)"].value_counts()
            _titulo_grafico("Fase do Processo (SISNAMA)", int(fase.sum()), total_r)
            fig_fase = px.bar(x=fase.values, y=fase.index, orientation="h",
                              color_discrete_sequence=[COR["azul"]], text=fase.values)
            fig_fase.update_traces(textposition="auto")
            fig_fase.update_layout(height=350, yaxis=dict(autorange="reversed"),
                                   margin=dict(l=10, r=10, t=10, b=30))
            st.plotly_chart(fig_fase, width="stretch")

        # Tabela detalhada
        st.markdown("##### Dados Detalhados")
        cols_show_r = [c for c in ["Código do CAR", "Município", "Status de Retificação",
                                    "Tipo de Atendimento", "Lote", "Fase do Processo (SISNAMA)"] if c in df_r.columns]
        if cols_show_r:
            st.dataframe(df_r[cols_show_r].head(200), width="stretch", height=300)

    # ────────────────────────────────────────────────────────
    # TAB: ELEGIBILIDADE PRA
    # ────────────────────────────────────────────────────────
    with tab_eleg:
        st.markdown("### Elegibilidade para PSA")
        total_e = len(df_e)

        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Total de Elegibilidades", fmt_int(kpis['registros_eleg']))
        e2.metric("CARs Únicos", fmt_int(kpis['cars_eleg']))
        e3.metric("UFs", fmt_int(kpis['ufs_eleg']))
        e4.metric("Elegibilidade PSA", fmt_pct(kpis['pct_elegivel']),
                  f"{fmt_int(kpis['n_fase1'] + kpis['n_fase2'])} elegíveis")

        st.divider()

        # Critérios
        st.markdown("##### Critérios de Elegibilidade")
        criterios = {
            "MF imóvel": "Módulo Fiscal", "Soma - MF dos Imóveis": "Soma MF",
            "cnfp": "CNFP", "uc": "Unid. Conservação", "quilombola": "Quilombola",
            "embargo_ib": "Embargo IBAMA", "sobrep_car": "Sobreposição CAR",
            "prodes_1ha": "PRODES > 1ha", "prodes_6ha": "PRODES > 6.25ha",
            "rvn_minima": "RVN Mínima", "em_priorit": "Munic. Prioritário",
        }
        crit_data = []
        for col, label in criterios.items():
            if col in df_e.columns:
                ne = (df_e[col] == "Não Elegível").sum()
                el = (df_e[col] == "Elegível").sum()
                crit_data.append({"Critério": label, "Elegível": el, "Não Elegível": ne,
                                  "Total": el + ne, "pct": ne / max(len(df_e), 1) * 100})
        if crit_data:
            total_crit_min = min(d["Total"] for d in crit_data)
            _titulo_grafico("Análise por Critério", total_crit_min, total_e)
            df_crit = pd.DataFrame(crit_data).sort_values("pct")
            fig_crit = go.Figure()
            fig_crit.add_trace(go.Bar(y=df_crit["Critério"], x=df_crit["Elegível"],
                                      name="Elegível", orientation="h", marker_color=COR["verde_claro"]))
            fig_crit.add_trace(go.Bar(y=df_crit["Critério"], x=df_crit["Não Elegível"],
                                      name="Não Elegível", orientation="h", marker_color=COR["vermelho"]))
            fig_crit.update_layout(barmode="stack", height=420,
                                   margin=dict(l=10, r=10, t=10, b=30),
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_crit, width="stretch")

        # Por UF
        ce1, ce2 = st.columns(2)
        with ce1:
            st.markdown("##### Elegibilidade por UF")
            if "UF" in df_e.columns and "Elegibilidade" in df_e.columns:
                cross_uf = pd.crosstab(df_e["UF"], df_e["Elegibilidade"])
                cross_uf = cross_uf.sort_values(cross_uf.columns.tolist(), ascending=False)
                cores_e = {"Inelegível": COR["vermelho"], "Fase 1": COR["verde_claro"], "Fase 2": COR["verde_escuro"]}
                fig_uf = px.bar(cross_uf, barmode="stack", color_discrete_map=cores_e)
                fig_uf.update_layout(height=350, margin=dict(l=20, r=10, t=10, b=30))
                st.plotly_chart(fig_uf, width="stretch")

        with ce2:
            if "fitofision" in df_e.columns:
                fito = df_e["fitofision"].dropna().value_counts()
                _titulo_grafico("Fitofisionomia", int(fito.sum()), total_e)
                fig_fito = px.pie(values=fito.values, names=fito.index, hole=0.45,
                                  color_discrete_sequence=PALETA)
                fig_fito.update_traces(textinfo="percent+value")
                fig_fito.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_fito, width="stretch")

    # ────────────────────────────────────────────────────────
    # TAB: GARGALOS
    # ────────────────────────────────────────────────────────
    with tab_gargalos:
        st.markdown("### Identificação de Gargalos")

        # Atendimento de pendências por ciclo
        st.markdown("##### Taxa de Atendimento de Pendências por Ciclo")
        if "Ciclo de análise" in df_a.columns and "Situação da Análise Externa" in df_a.columns:
            ciclo_sit = df_a[df_a["Ciclo de análise"].isin([1, 2, 3])].groupby(
                "Ciclo de análise")["Situação da Análise Externa"].value_counts().unstack(fill_value=0)
            if "CAR sem pendência(s)" in ciclo_sit.columns and "CAR com pendência(s)" in ciclo_sit.columns:
                ciclo_sit["total"] = ciclo_sit.sum(axis=1)
                ciclo_sit["pct_sem"] = ciclo_sit["CAR sem pendência(s)"] / ciclo_sit["total"] * 100
                ciclo_sit["pct_com"] = ciclo_sit["CAR com pendência(s)"] / ciclo_sit["total"] * 100
                fig_garg = go.Figure()
                fig_garg.add_trace(go.Bar(
                    x=[f"{int(c)}º ciclo" for c in ciclo_sit.index],
                    y=ciclo_sit["pct_sem"].values, name="Sem pendência",
                    marker_color=COR["verde_claro"],
                    text=[fmt_pct(v) for v in ciclo_sit["pct_sem"].values], textposition="auto",
                ))
                fig_garg.add_trace(go.Bar(
                    x=[f"{int(c)}º ciclo" for c in ciclo_sit.index],
                    y=ciclo_sit["pct_com"].values, name="Com pendência",
                    marker_color=COR["vermelho"],
                    text=[fmt_pct(v) for v in ciclo_sit["pct_com"].values], textposition="auto",
                ))
                fig_garg.update_layout(barmode="stack", height=350, yaxis_title="%",
                                       margin=dict(l=40, r=20, t=20, b=40))
                st.plotly_chart(fig_garg, width="stretch")

        # Mapa de calor de pendências por município
        st.markdown("##### Concentração de Pendências por Município")
        if "Município" in df_a.columns and "Situação da Análise Externa" in df_a.columns:
            pend_mun = df_a.groupby("Município").apply(
                lambda x: (x["Situação da Análise Externa"] == "CAR com pendência(s)").mean() * 100
            ).sort_values(ascending=False).head(20)
            fig_hm = px.bar(x=pend_mun.values, y=pend_mun.index, orientation="h",
                            color=pend_mun.values, color_continuous_scale="RdYlGn_r",
                            labels={"x": "% com Pendência", "y": "Município"},
                            text=[fmt_pct(v) for v in pend_mun.values])
            fig_hm.update_traces(textposition="auto")
            fig_hm.update_layout(height=500, yaxis=dict(autorange="reversed"),
                                 coloraxis_showscale=False,
                                 margin=dict(l=10, r=10, t=10, b=30))
            st.plotly_chart(fig_hm, width="stretch")

        # Municípios com maior gargalo
        st.markdown("##### Municípios Críticos")
        if "Município" in df_a.columns:
            garg = df_a.groupby("Município").agg(
                total=("Nº DO CAR", "count"),
                unicos=("Nº DO CAR", "nunique"),
            ).reset_index()
            garg["ratio_ciclos"] = (garg["total"] / garg["unicos"]).round(2)
            if "Situação da Análise Externa" in df_a.columns:
                pend_pct = df_a.groupby("Município")["Situação da Análise Externa"].apply(
                    lambda x: round((x == "CAR com pendência(s)").mean() * 100, 1)
                ).reset_index(name="% Pendência")
                garg = garg.merge(pend_pct, on="Município")
            garg = garg.sort_values("total", ascending=False).head(20)
            garg.columns = [c.replace("_", " ").title() if c != "% Pendência" else c for c in garg.columns]
            st.dataframe(garg, width="stretch", height=400)


# ════════════════════════════════════════════════════════════════
# §8  DADOS EM TABELA (NORMALIZAÇÃO)
# ════════════════════════════════════════════════════════════════

def _resumo_completude(df):
    """Exibe resumo de completude das colunas de um DataFrame."""
    total = len(df)
    if total == 0:
        st.warning("Nenhum registro encontrado.")
        return

    vazios = df.isnull().sum() + (df == "").sum()
    pct_preenchido = ((total - vazios) / total * 100).round(1)
    resumo = pd.DataFrame({
        "Coluna": df.columns,
        "Preenchidos": total - vazios.values,
        "Vazios": vazios.values,
        "% Preenchido": pct_preenchido.values,
    })
    resumo = resumo.sort_values("% Preenchido", ascending=True).reset_index(drop=True)

    # Métricas rápidas
    cols_completas = int((resumo["% Preenchido"] == 100).sum())
    cols_com_vazios = int((resumo["% Preenchido"] < 100).sum())
    cols_criticas = int((resumo["% Preenchido"] < 50).sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Registros", fmt_int(total))
    c2.metric("Colunas 100% preenchidas", cols_completas)
    c3.metric("Colunas com vazios", cols_com_vazios)
    c4.metric("Colunas críticas (<50%)", cols_criticas, delta=f"-{cols_criticas}" if cols_criticas else "0",
              delta_color="inverse")

    # Tabela de completude (só colunas com vazios)
    com_vazios = resumo[resumo["Vazios"] > 0]
    if not com_vazios.empty:
        with st.expander(f"📋 Completude das colunas ({len(com_vazios)} com campos vazios)", expanded=False):
            st.dataframe(
                com_vazios,
                width="stretch",
                hide_index=True,
                height=min(400, 35 * len(com_vazios) + 40),
                column_config={
                    "% Preenchido": st.column_config.ProgressColumn(
                        "% Preenchido", min_value=0, max_value=100, format="%.1f %%",
                    ),
                },
            )


def _render_tabela_aba(df, label_car_col, colunas_chave=None):
    """Renderiza uma aba de dados com filtro de busca e destaque de vazios."""
    if df.empty:
        st.warning("Sem dados para exibir.")
        return

    # Filtro de busca rápida
    col_busca, col_filtro_vazio = st.columns([2, 1])
    with col_busca:
        busca = st.text_input("🔍 Buscar (qualquer coluna)", key=f"busca_{label_car_col}",
                              placeholder="Digite para filtrar registros...")
    with col_filtro_vazio:
        mostrar_incompletos = st.checkbox("Mostrar apenas registros com campos vazios",
                                          key=f"incomp_{label_car_col}")

    df_view = df.copy()

    # Aplicar busca
    if busca:
        mask = df_view.astype(str).apply(lambda col: col.str.contains(busca, case=False, na=False)).any(axis=1)
        df_view = df_view[mask]

    # Filtrar incompletos
    if mostrar_incompletos:
        if colunas_chave:
            cols_check = [c for c in colunas_chave if c in df_view.columns]
        else:
            cols_check = list(df_view.columns)
        mask_vazio = df_view[cols_check].isnull().any(axis=1) | (df_view[cols_check] == "").any(axis=1)
        df_view = df_view[mask_vazio]

    st.caption(f"Exibindo {fmt_int(len(df_view))} de {fmt_int(len(df))} registros")

    # Exibir tabela
    st.dataframe(
        df_view,
        width="stretch",
        hide_index=True,
        height=600,
    )


def _alerta_car_fora_padrao(df, col_car):
    """Exibe alerta se existem códigos de CAR fora do padrão (não começam com AM-)."""
    if col_car not in df.columns:
        return
    cars = df[col_car].dropna().astype(str)
    fora_padrao = cars[~cars.str.startswith("AM-")]
    if fora_padrao.empty:
        return
    unicos = fora_padrao.unique()
    st.warning(f"**{len(unicos)} código(s) de CAR fora do padrão** (não começam com `AM-`):")
    with st.expander(f"Ver todos ({len(unicos)})", expanded=False):
        st.dataframe(
            pd.DataFrame({"Código do CAR fora do padrão": unicos}),
            width="stretch",
            hide_index=True,
        )


def render_dados_tabela(df_a, df_r, df_e):
    """Renderiza a página de visualização dos dados em tabela para normalização."""
    st.markdown("### 📋 Dados em Tabela — Normalização e Conferência")
    st.caption("Visualize os dados brutos de cada aba, identifique campos vazios e inconsistências.")

    tab_analise, tab_retif, tab_eleg = st.tabs([
        "📊 Análise CAR",
        "🔄 Retificação / Inscrição CAR",
        "✅ Elegibilidade CAR",
    ])

    # ── Aba Análise ──
    with tab_analise:
        st.markdown("#### Análise CAR")
        _alerta_car_fora_padrao(df_a, "Nº DO CAR")
        colunas_chave_a = [
            "Nº DO CAR", "Técnico", "Município", "LOTE", "Grau de Complexidade",
            "Área", "Tipo de imóvel", "Condição final do cadastro",
            "Situação da Análise Externa", "Status final", "Ciclo de análise",
            "Data início", "Data fim", "Recomendação", "Parecer Técnico",
        ]
        _resumo_completude(df_a)
        st.divider()
        _render_tabela_aba(df_a, "analise", colunas_chave_a)

    # ── Aba Retificação ──
    with tab_retif:
        st.markdown("#### Retificação / Inscrição CAR")
        _alerta_car_fora_padrao(df_r, "Código do CAR")
        colunas_chave_r = [
            "Código do CAR", "Município", "Lote", "Técnico(a) Responsável",
            "Status de Retificação", "Tipo de Atendimento",
            "Fase do Processo (SISNAMA)", "Condição WFS",
            "Nome do(a) Proprietário(a) ou Possuidor(a)", "CPF/CNPJ - PROPRIETÁRIO",
            "Telefone (principal)", "Documentação Fundiária",
            "Área (líquida)", "Reserva Legal Proposta",
        ]
        _resumo_completude(df_r)
        st.divider()
        _render_tabela_aba(df_r, "retificacao", colunas_chave_r)

    # ── Aba Elegibilidade ──
    with tab_eleg:
        st.markdown("#### Elegibilidade CAR")
        _alerta_car_fora_padrao(df_e, "Nº DO CAR")
        colunas_chave_e = [
            "Nº DO CAR", "Município", "UF", "Elegibilidade",
            "Status do CAR", "Área do Imóvel", "MF",
            "em_priorit", "rvn_minima", "cnfp", "sobrep_car",
            "prodes_1ha", "Elegivel Fase 1", "Elegivel Fase 2", "Parecer",
        ]
        _resumo_completude(df_e)
        st.divider()
        _render_tabela_aba(df_e, "elegibilidade", colunas_chave_e)


# ════════════════════════════════════════════════════════════════
# §9  EXPORTAÇÃO DE RELATÓRIOS
# ════════════════════════════════════════════════════════════════

def exportar_xlsx(df_a, df_r, df_e, kpis, filtros_ativos):
    """Gera relatório Excel com dados filtrados e KPIs."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        # KPIs
        kpi_df = pd.DataFrame([
            {"Indicador": k.replace("_", " ").title(), "Valor": str(v)}
            for k, v in kpis.items()
        ])
        kpi_df.to_excel(writer, sheet_name="KPIs", index=False)

        # Filtros aplicados
        filtros_df = pd.DataFrame([
            {"Filtro": k, "Valor": str(v)} for k, v in filtros_ativos.items() if v
        ])
        filtros_df.to_excel(writer, sheet_name="Filtros Aplicados", index=False)

        # Dados
        cols_a = [c for c in ["Nº DO CAR", "Município", "Técnico", "LOTE", "Ciclo de análise",
                               "Condição_norm", "Situação da Análise Externa", "Status final",
                               "Grau de Complexidade", "Tipo de imóvel", "Área",
                               "Data início", "Data fim"] if c in df_a.columns]
        df_a[cols_a].to_excel(writer, sheet_name="Análise CAR", index=False)

        cols_r = [c for c in df_r.columns if not c.startswith("Unnamed")][:15]
        df_r[cols_r].to_excel(writer, sheet_name="Retificação", index=False)

        cols_e = [c for c in df_e.columns if not c.startswith("Unnamed")][:20]
        df_e[cols_e].to_excel(writer, sheet_name="Elegibilidade", index=False)

        # Resumo por município
        if "Município" in df_a.columns:
            mun_resumo = df_a.groupby("Município").agg(
                total=("Nº DO CAR", "count"), unicos=("Nº DO CAR", "nunique"),
            ).reset_index()
            mun_resumo.to_excel(writer, sheet_name="Resumo Municípios", index=False)

    return buf.getvalue()


# ════════════════════════════════════════════════════════════════
# §M  MÓDULO MAPA — SHAPEFILES SICAR
# ════════════════════════════════════════════════════════════════

CORES_ESCOPO = {
    "Apenas Análise":                           COR["verde_escuro"],
    "Apenas Retificação":                       COR["azul"],
    "Apenas Elegibilidade":                     COR["laranja"],
    "Análise + Retificação":                     "#00897B",
    "Análise + Elegibilidade":                   COR["roxo"],
    "Retificação + Elegibilidade":               COR["vermelho"],
    "Análise + Retificação + Elegibilidade":      "#37474F",
    "Fora do Escopo":                           COR["cinza"],
}


def _carregar_shapefile(file_bytes):
    """Carrega shapefile a partir de bytes de um arquivo ZIP."""
    import zipfile, tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(file_bytes)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)
        shp_paths = []
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith(".shp"):
                    shp_paths.append(os.path.join(root, f))
        if not shp_paths:
            return None, "Nenhum arquivo .shp encontrado no ZIP."
        gdf = gpd.read_file(shp_paths[0])
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        elif gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)
        return gdf, None


def _detectar_coluna_car(gdf):
    """Tenta detectar automaticamente a coluna do código do CAR."""
    candidatas = [
        "cod_imovel", "COD_IMOVEL", "Cod_Imovel",
        "num_car", "NUM_CAR", "Num_Car",
        "cod_car", "COD_CAR", "CODIGO", "codigo",
    ]
    for c in candidatas:
        if c in gdf.columns:
            return c
    for c in gdf.columns:
        if c == "geometry":
            continue
        if gdf[c].dtype == "object":
            amostra = gdf[c].dropna().head(10)
            if amostra.str.match(r"^[A-Z]{2}-\d{7}-").any():
                return c
    return None


def _classificar_imovel(codigo, cars_a, cars_r, cars_e):
    """Classifica um imóvel pelo seu escopo no projeto."""
    partes = []
    if codigo in cars_a:
        partes.append("Análise")
    if codigo in cars_r:
        partes.append("Retificação")
    if codigo in cars_e:
        partes.append("Elegibilidade")
    if not partes:
        return "Fora do Escopo"
    if len(partes) == 1:
        return f"Apenas {partes[0]}"
    return " + ".join(partes)


def render_mapa(df_a, df_r, df_e):
    """§M — Módulo de Mapa: visualização geoespacial dos imóveis do Projeto."""

    st.markdown("### 🗺️ Mapa de Imóveis — Shapefiles SICAR")
    st.caption(
        "Faça upload dos shapefiles (.zip) exportados do SICAR para visualizar "
        "os imóveis rurais que foram escopo do Projeto CAR/PRA."
    )

    if not HAS_GEO:
        st.error(
            "⚠️ Bibliotecas de geoprocessamento não instaladas. "
            "Execute: `pip install geopandas folium streamlit-folium`"
        )
        return

    shp_zips = st.file_uploader(
        "📁 Shapefiles SICAR (.zip)",
        type=["zip"],
        accept_multiple_files=True,
        help="Um ou mais arquivos .zip com shapefiles do SICAR (um por estado, por exemplo)",
        key="shp_upload_mapa",
    )

    if not shp_zips:
        st.info("☝️ Faça upload de um ou mais arquivos .zip com os shapefiles do SICAR.")
        m = folium.Map(location=[-3.4, -65.0], zoom_start=5, tiles="CartoDB positron",
                      max_bounds=True, min_zoom=4,
                      min_lat=-34.0, max_lat=6.0, min_lon=-74.0, max_lon=-33.0)
        st_folium(m, width=None, height=500, returned_objects=[])
        return

    # ── Carregar e concatenar shapefiles ──
    gdfs = []
    with st.spinner(f"Carregando {len(shp_zips)} shapefile(s)..."):
        for shp_zip in shp_zips:
            gdf_i, erro = _carregar_shapefile(shp_zip.getvalue())
            if erro:
                st.warning(f"⚠️ {shp_zip.name}: {erro}")
            else:
                gdf_i["_arquivo"] = shp_zip.name
                gdfs.append(gdf_i)

    if not gdfs:
        st.error("❌ Nenhum shapefile válido encontrado nos arquivos enviados.")
        return

    import pandas as _pd
    gdf = gpd.GeoDataFrame(_pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)
    st.success(f"✅ {len(gdf)} feições carregadas de {len(gdfs)} arquivo(s)")

    # ── Detectar coluna do CAR ──
    col_car_shp = _detectar_coluna_car(gdf)
    if col_car_shp:
        st.caption(f"Coluna do CAR detectada: **{col_car_shp}**")
    else:
        cols_texto = [c for c in gdf.columns if c != "geometry"]
        col_car_shp = st.selectbox(
            "Selecione a coluna do CAR no shapefile:",
            cols_texto,
            help="Coluna que contém o código do imóvel rural no SICAR",
        )

    # ── Classificar por escopo do projeto ──
    col_car_proj = "Nº DO CAR"
    cars_a = set(df_a[col_car_proj].dropna().unique()) if col_car_proj in df_a.columns else set()
    cars_r = set(df_r[col_car_proj].dropna().unique()) if col_car_proj in df_r.columns else set()
    cars_e = set(df_e[col_car_proj].dropna().unique()) if col_car_proj in df_e.columns else set()

    gdf["_escopo"] = gdf[col_car_shp].apply(
        lambda x: _classificar_imovel(str(x), cars_a, cars_r, cars_e)
    )

    # ── Construir mapa Folium com camadas por escopo ──
    centroid = gdf.geometry.centroid
    m = folium.Map(
        location=[centroid.y.mean(), centroid.x.mean()],
        zoom_start=8,
        tiles="CartoDB positron",
        max_bounds=True,
        min_zoom=4,
        min_lat=-34.0,
        max_lat=6.0,
        min_lon=-74.0,
        max_lon=-33.0,
    )

    cols_popup = [col_car_shp, "_escopo", "_arquivo"]
    for c in ["municipio", "nom_munic", "MUNICIPIO", "area_imovel", "AREA", "des_condic"]:
        if c in gdf.columns:
            cols_popup.append(c)
    cols_keep = [c for c in cols_popup + ["geometry"] if c in gdf.columns]

    # Uma camada (FeatureGroup) para cada escopo — ordem fixa
    _ORDEM_ESCOPO = [
        "Apenas Análise", "Apenas Retificação", "Apenas Elegibilidade",
        "Análise + Retificação", "Análise + Elegibilidade",
        "Retificação + Elegibilidade", "Análise + Retificação + Elegibilidade",
        "Fora do Escopo",
    ]
    escopos_presentes = [e for e in _ORDEM_ESCOPO if e in gdf["_escopo"].values]
    for escopo in escopos_presentes:
        gdf_escopo = gdf[gdf["_escopo"] == escopo][cols_keep].copy()
        if gdf_escopo.empty:
            continue

        cor = CORES_ESCOPO.get(escopo, COR["cinza"])

        fg = folium.FeatureGroup(name=f"● {escopo} ({len(gdf_escopo)})", show=True)

        folium.GeoJson(
            gdf_escopo.to_json(),
            style_function=lambda feature, c=cor: {
                "fillColor": c,
                "color": "#333333",
                "weight": 1,
                "fillOpacity": 0.6,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[col_car_shp, "_escopo"],
                aliases=["CAR:", "Escopo:"],
                sticky=True,
            ),
            popup=folium.GeoJsonPopup(
                fields=cols_popup,
                aliases=[c.replace("_", " ").title() for c in cols_popup],
            ),
        ).add_to(fg)

        fg.add_to(m)

    bounds = gdf.total_bounds
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width=None, height=600, returned_objects=[])

    # ── Resumo ──
    st.markdown("---")
    st.markdown("#### 📊 Resumo dos Imóveis Carregados")

    resumo = gdf["_escopo"].value_counts().reset_index()
    resumo.columns = ["Escopo", "Quantidade"]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        st.metric("Total de feições", fmt_int(len(gdf)))
        no_projeto = len(gdf[gdf["_escopo"] != "Fora do Escopo"])
        st.metric("No escopo do Projeto", fmt_int(no_projeto))

    with col2:
        fig = px.pie(
            resumo, names="Escopo", values="Quantidade",
            title="Distribuição por Escopo do Projeto",
            color="Escopo",
            color_discrete_map=CORES_ESCOPO,
        )
        fig.update_layout(height=350, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# §C  MÓDULO CARs — VISÃO CONSOLIDADA DE CARs ÚNICOS
# ════════════════════════════════════════════════════════════════

def construir_df_cars_unicos(df_consol):
    """Deriva DataFrame de CARs únicos a partir do DataFrame consolidado.

    - Análise: prevalece o registro do maior ‘Ciclo de análise’.
    - Retificação / Elegibilidade: último registro por CAR.
    - Colunas comuns vêm da Análise; colunas exclusivas de cada escopo são adicionadas.
    """
    col_unif = "Nº DO CAR"
    meta_cols = ["Origem", "Escopo", "Último Ciclo"]

    # ── Separar por Origem e deduplicar ──
    df_a = df_consol[df_consol["Origem"] == "Análise"].copy()
    if "Ciclo de análise" in df_a.columns:
        df_a["Ciclo de análise"] = pd.to_numeric(df_a["Ciclo de análise"], errors="coerce")
        df_a = df_a.sort_values([col_unif, "Ciclo de análise"]).drop_duplicates(subset=col_unif, keep="last")
    else:
        df_a = df_a.drop_duplicates(subset=col_unif, keep="last")

    df_r = df_consol[df_consol["Origem"] == "Retificação"].drop_duplicates(subset=col_unif, keep="last")
    df_e = df_consol[df_consol["Origem"] == "Elegibilidade"].drop_duplicates(subset=col_unif, keep="last")

    # Remover colunas meta antes do merge
    df_a_m = df_a.drop(columns=[c for c in meta_cols if c in df_a.columns])
    df_r_m = df_r.drop(columns=[c for c in meta_cols if c in df_r.columns])
    df_e_m = df_e.drop(columns=[c for c in meta_cols if c in df_e.columns])

    # ── Base: todos os CARs únicos ──
    all_cars = sorted(df_consol[col_unif].unique())
    df_cars = pd.DataFrame({col_unif: all_cars})

    # Merge Análise (todas as colunas)
    df_cars = df_cars.merge(df_a_m, on=col_unif, how="left")

    # Merge Retificação (colunas exclusivas)
    cols_r_new = [c for c in df_r_m.columns if c not in df_cars.columns]
    if cols_r_new:
        df_cars = df_cars.merge(df_r_m[[col_unif] + cols_r_new], on=col_unif, how="left")

    # Merge Elegibilidade (colunas exclusivas)
    cols_e_new = [c for c in df_e_m.columns if c not in df_cars.columns]
    if cols_e_new:
        df_cars = df_cars.merge(df_e_m[[col_unif] + cols_e_new], on=col_unif, how="left")

    # ── Escopo e Último Ciclo (do consolidado) ──
    esc_map = df_consol.drop_duplicates(subset=col_unif).set_index(col_unif)["Escopo"].to_dict()
    df_cars.insert(1, "Escopo", df_cars[col_unif].map(esc_map))

    if "Último Ciclo" in df_consol.columns:
        ciclo_map = df_consol.drop_duplicates(subset=col_unif).set_index(col_unif)["Último Ciclo"].to_dict()
        df_cars.insert(2, "Último Ciclo", df_cars[col_unif].map(ciclo_map))

    # Remover colunas 100% vazias
    df_cars = df_cars.dropna(axis=1, how="all")

    return df_cars

def construir_df_consolidado(df_a, df_r, df_e):
    """Constrói DataFrame consolidado com TODOS os registros das 3 abas.

    Empilha todas as linhas dos 3 escopos via pd.concat.
    Adiciona colunas: Origem (aba), Escopo (classificação do CAR) e Último Ciclo.
    """
    col_a = "Nº DO CAR"
    col_r = "Código do CAR"
    col_e = "Nº DO CAR"
    col_unif = "Nº DO CAR"

    def _cars_validos(series):
        return set(x for x in series.dropna().unique() if str(x).strip())

    # Cópias limpas (sem CARs vazios, sem colunas Unnamed)
    dfa = df_a[df_a[col_a].notna() & (df_a[col_a].astype(str).str.strip() != "")].copy() if col_a in df_a.columns else df_a.copy()
    dfr = df_r[df_r[col_r].notna() & (df_r[col_r].astype(str).str.strip() != "")].copy() if col_r in df_r.columns else df_r.copy()
    dfe = df_e[df_e[col_e].notna() & (df_e[col_e].astype(str).str.strip() != "")].copy() if col_e in df_e.columns else df_e.copy()

    dfa = dfa.loc[:, ~dfa.columns.str.startswith("Unnamed")]
    dfr = dfr.loc[:, ~dfr.columns.str.startswith("Unnamed")]
    dfe = dfe.loc[:, ~dfe.columns.str.startswith("Unnamed")]

    # Padronizar coluna do CAR na Retificação
    if col_r in dfr.columns and col_r != col_unif:
        dfr = dfr.rename(columns={col_r: col_unif})

    # Coluna de Origem
    dfa.insert(1, "Origem", "Análise")
    dfr.insert(1, "Origem", "Retificação")
    dfe.insert(1, "Origem", "Elegibilidade")

    # Empilhar tudo
    df_consol = pd.concat([dfa, dfr, dfe], ignore_index=True)

    # Sets para classificação de Escopo
    cars_a = _cars_validos(df_a[col_a]) if col_a in df_a.columns else set()
    cars_r = _cars_validos(df_r[col_r]) if col_r in df_r.columns else set()
    cars_e = _cars_validos(df_e[col_e]) if col_e in df_e.columns else set()

    # Inserir Escopo e Último Ciclo
    df_consol.insert(2, "Escopo", df_consol[col_unif].apply(
        lambda x: _classificar_imovel(str(x), cars_a, cars_r, cars_e)
    ))
    if "Ciclo de análise" in df_a.columns:
        _ciclo = pd.to_numeric(df_a["Ciclo de análise"], errors="coerce")
        _max = df_a.assign(_c=_ciclo).groupby(col_a)["_c"].max().to_dict()
        df_consol.insert(3, "Último Ciclo", df_consol[col_unif].map(_max))

    # Remover colunas 100% vazias
    df_consol = df_consol.dropna(axis=1, how="all")

    return df_consol

def render_cars(df_a, df_r, df_e):
    """§C — Visão consolidada de CARs únicos com escopo e condição final."""

    st.markdown("### 🏷️ CARs Únicos — Visão Consolidada")
    st.caption(
        "Cada linha é um CAR único. Prevalece o registro do maior ciclo de análise. "
        "Colunas exclusivas de Retificação e Elegibilidade aparecem apenas para "
        "CARs que passaram por esses escopos."
    )

    df_consol = construir_df_consolidado(df_a, df_r, df_e)
    df_cars = construir_df_cars_unicos(df_consol)

    # ── Filtros (ACIMA dos KPIs) ──
    _ORDEM_ESCOPO = [
        "Apenas Análise", "Apenas Retificação", "Apenas Elegibilidade",
        "Análise + Retificação", "Análise + Elegibilidade",
        "Retificação + Elegibilidade", "Análise + Retificação + Elegibilidade",
        "Fora do Escopo",
    ]
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        escopo_sel = st.multiselect(
            "Filtrar por Escopo:",
            [e for e in _ORDEM_ESCOPO if e in df_cars["Escopo"].values],
            help="Selecione um ou mais escopos",
            key="cars_escopo_filter",
        )
    with col_f2:
        busca_car = st.text_input(
            "Buscar CAR:", placeholder="Ex: AM-1300060-...",
            help="Filtre por código completo ou parcial",
            key="cars_busca_car",
        )

    df_view = df_cars.copy()
    if escopo_sel:
        df_view = df_view[df_view["Escopo"].isin(escopo_sel)]
    if busca_car:
        df_view = df_view[df_view["Nº DO CAR"].astype(str).str.contains(busca_car, case=False, na=False)]

    # Remover colunas que ficaram 100% vazias após filtragem
    df_view = df_view.dropna(axis=1, how="all")

    # ── KPIs (refletem filtros) ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CARs Únicos", fmt_int(len(df_view)))
    c2.metric("Análise", fmt_int(len(df_view[df_view["Escopo"].str.contains("Análise")])))
    c3.metric("Retificação", fmt_int(len(df_view[df_view["Escopo"].str.contains("Retificação")])))
    c4.metric("Elegibilidade", fmt_int(len(df_view[df_view["Escopo"].str.contains("Elegibilidade")])))

    if escopo_sel or busca_car:
        st.caption(f"🔍 Exibindo {fmt_int(len(df_view))} de {fmt_int(len(df_cars))} CARs")

    # ── Seletor de colunas ──
    all_cols = df_view.columns.tolist()
    default_cols = [c for c in [
        "Nº DO CAR", "Escopo", "Último Ciclo", "Município", "LOTE",
        "Condição_norm", "Condição final do cadastro", "Tipo de imóvel", "Área",
        "Grau de Complexidade", "Status final",
    ] if c in all_cols]

    with st.expander("⚙️ Selecionar colunas visíveis", expanded=False):
        cols_sel = st.multiselect("Colunas:", all_cols, default=default_cols or all_cols[:10],
                                  key="cars_cols_select")

    cols_final = cols_sel if cols_sel else (default_cols if default_cols else all_cols[:10])

    st.dataframe(
        df_view[cols_final],
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    # ── Distribuição por Escopo ──
    st.markdown("---")
    resumo = df_view["Escopo"].value_counts().reindex(
        [e for e in _ORDEM_ESCOPO if e in df_view["Escopo"].values]
    ).reset_index()
    resumo.columns = ["Escopo", "Quantidade"]

    fig = px.bar(
        resumo, x="Escopo", y="Quantidade",
        title="Distribuição de CARs Únicos por Escopo",
        color="Escopo",
        color_discrete_map=CORES_ESCOPO,
        text="Quantidade",
    )
    fig.update_layout(
        height=400, xaxis_tickangle=-30, showlegend=False,
        margin=dict(l=20, r=20, t=40, b=100),
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # ── Exportar Dados ──
    st.markdown("---")
    st.markdown("#### 📦 Exportar Dados")

    dl1, dl2 = st.columns(2)

    # Download CARs Únicos
    with dl1:
        st.caption(f"CARs Únicos — {fmt_int(len(df_cars))} linhas × {fmt_int(len(df_cars.columns))} colunas")
        buf_unicos = io.BytesIO()
        with pd.ExcelWriter(buf_unicos, engine="xlsxwriter") as writer:
            df_cars.to_excel(writer, sheet_name="CARs Únicos", index=False)
        st.download_button(
            label="⬇️ Baixar CARs Únicos (.xlsx)",
            data=buf_unicos.getvalue(),
            file_name=f"cars_unicos_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
            key="dl_cars_unicos",
        )

    # Download Consolidado
    with dl2:
        st.caption(f"Consolidado — {fmt_int(len(df_consol))} linhas × {fmt_int(len(df_consol.columns))} colunas")
        buf_consol = io.BytesIO()
        with pd.ExcelWriter(buf_consol, engine="xlsxwriter") as writer:
            df_consol.to_excel(writer, sheet_name="CARs Consolidado", index=False)
        st.download_button(
            label="⬇️ Baixar Consolidado (.xlsx)",
            data=buf_consol.getvalue(),
            file_name=f"cars_consolidado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
            key="dl_consolidado",
        )


# ════════════════════════════════════════════════════════════════
# §D  DETALHE DO CAR — FICHA COMPLETA
# ════════════════════════════════════════════════════════════════

def _render_ficha_registro(row, meta_cols):
    """Renderiza um registro como ficha com campos em 3 colunas."""
    dados = {k: v for k, v in row.items()
             if k not in meta_cols and pd.notna(v) and str(v).strip()}
    if not dados:
        st.caption("Sem dados adicionais.")
        return
    campos = list(dados.items())
    for i in range(0, len(campos), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(campos):
                campo, valor = campos[i + j]
                col.markdown(f"<small style='color:#888'>{campo}</small><br>"
                             f"<strong>{valor}</strong>", unsafe_allow_html=True)


def render_detalhe_car(df_a, df_r, df_e):
    """§D — Ficha detalhada de um CAR com todos os dados do consolidado."""

    st.markdown("### 🔍 Detalhe do CAR")
    st.caption("Selecione um CAR para visualizar todos os dados do projeto.")

    df_consol = construir_df_consolidado(df_a, df_r, df_e)

    # ── Busca ──
    busca = st.text_input(
        "Buscar CAR:", placeholder="Digite o código (ex: AM-1300060-...)",
        key="detalhe_busca",
    )

    if not busca:
        st.info("☝️ Digite o código de um CAR para ver a ficha completa.")
        return

    matches = df_consol[df_consol["Nº DO CAR"].astype(str).str.contains(busca, case=False, na=False)]
    cars_encontrados = sorted(matches["Nº DO CAR"].unique())

    if not len(cars_encontrados):
        st.warning("Nenhum CAR encontrado com esse código.")
        return

    car_sel = st.selectbox(
        f"{len(cars_encontrados)} CAR(s) encontrado(s):", cars_encontrados,
        key="detalhe_car_sel",
    )

    registros = df_consol[df_consol["Nº DO CAR"] == car_sel]
    if registros.empty:
        return

    # ── Cabeçalho ──
    _esc = registros["Escopo"].iloc[0]
    _uc = registros["Último Ciclo"].iloc[0] if "Último Ciclo" in registros.columns else None
    _n = len(registros)

    st.markdown("---")
    st.markdown(f"#### `{car_sel}`")
    h1, h2, h3 = st.columns(3)
    h1.metric("Escopo", _esc)
    h2.metric("Último Ciclo", str(int(_uc)) if pd.notna(_uc) else "—")
    h3.metric("Total de Registros", fmt_int(_n))

    _meta = ["Nº DO CAR", "Origem", "Escopo", "Último Ciclo"]

    # ── Abas por Escopo ──
    origens_presentes = [o for o in ["Análise", "Retificação", "Elegibilidade"]
                         if o in registros["Origem"].values]

    if not origens_presentes:
        st.warning("Nenhum registro com Origem identificada.")
        return

    tabs = st.tabs([
        f"{o} ({len(registros[registros['Origem'] == o])})" for o in origens_presentes
    ])

    for tab, origem in zip(tabs, origens_presentes):
        with tab:
            df_orig = registros[registros["Origem"] == origem]

            if origem == "Análise" and "Ciclo de análise" in df_orig.columns and len(df_orig) > 1:
                # Seletor de ciclo para navegar sem rolagem
                ciclos = sorted(df_orig["Ciclo de análise"].dropna().unique())
                ciclo_sel = st.selectbox(
                    "Ciclo de análise:", ciclos,
                    index=len(ciclos) - 1,  # último ciclo por padrão
                    format_func=lambda x: f"Ciclo {int(x)}",
                    key=f"detalhe_ciclo_{car_sel}",
                )
                row = df_orig[df_orig["Ciclo de análise"] == ciclo_sel].iloc[0]
                _render_ficha_registro(row, _meta)
            else:
                # Registro único ou sem ciclo
                for idx, (_, row) in enumerate(df_orig.iterrows()):
                    if idx > 0:
                        st.divider()
                    _render_ficha_registro(row, _meta)


# ════════════════════════════════════════════════════════════════
# LOGIN
# ════════════════════════════════════════════════════════════════

# Credenciais e perfis (podem ser sobrescritos via .streamlit/secrets.toml)
_CREDENCIAIS_PADRAO = {
    "admin":    {"senha": "florestamais2024", "perfil": "Admin",    "nome": "Administrador"},
    "analista": {"senha": "car2024",          "perfil": "Analista", "nome": "Analista CAR"},
    "gestor":   {"senha": "pra2024",          "perfil": "Gestor",   "nome": "Gestor do Projeto"},
    "ipaam":    {"senha": "ipaam2024",         "perfil": "IPAAM",    "nome": "IPAAM"},
    "giz":      {"senha": "giz2024",           "perfil": "GIZ",     "nome": "GIZ"},
}


TODOS_OS_MENUS = ["Painel Estratégico", "Painel Tático", "CARs", "Detalhe CAR", "Mapa", "Dados / Tabelas"]

TODAS_AS_SECOES = {
    "Painel Estratégico": ["kpis", "funil", "sankey", "condicao", "elegibilidade", "mapa_territorial", "evolucao_temporal"],
    "Painel Tático":     ["analise", "retificacao", "elegibilidade", "gargalos"],
    "CARs":              ["kpis", "filtros", "tabela", "grafico_escopo", "exportar"],
    "Detalhe CAR":       ["busca", "ficha"],
    "Mapa":              ["upload", "mapa", "resumo"],
    "Dados / Tabelas":   ["analise", "retificacao", "elegibilidade"],
}

# Menus acessíveis por perfil
_MENUS_POR_PERFIL = {
    "Admin":    ["Painel Estratégico", "Painel Tático", "CARs", "Detalhe CAR", "Mapa", "Dados / Tabelas"],
    "Gestor":   ["Painel Estratégico", "Painel Tático", "CARs", "Mapa"],
    "Analista": ["Painel Estratégico", "Painel Tático", "CARs", "Mapa"],
    "IPAAM":    ["Painel Estratégico", "Painel Tático", "CARs", "Mapa"],
    "GIZ":      ["Painel Estratégico", "CARs", "Mapa"],
}

# Seções visíveis dentro de cada página, por perfil
_SECOES_POR_PERFIL = {
    "Admin": {
        "Painel Estratégico": ["kpis", "funil", "sankey", "condicao", "elegibilidade", "mapa_territorial", "evolucao_temporal"],
        "Painel Tático":     ["analise", "retificacao", "elegibilidade", "gargalos"],
        "CARs":              ["kpis", "filtros", "tabela", "grafico_escopo", "exportar"],
        "Detalhe CAR":       ["busca", "ficha"],
        "Mapa":              ["upload", "mapa", "resumo"],
        "Dados / Tabelas":   ["analise", "retificacao", "elegibilidade"],
    },
    "Gestor": {
        "Painel Estratégico": ["kpis", "funil", "sankey", "condicao", "elegibilidade", "mapa_territorial", "evolucao_temporal"],
        "Painel Tático":     ["analise", "retificacao", "elegibilidade", "gargalos"],
        "CARs":              ["kpis", "filtros", "tabela", "grafico_escopo", "exportar"],
        "Detalhe CAR":       ["busca", "ficha"],
        "Mapa":              ["upload", "mapa", "resumo"],
        "Dados / Tabelas":   ["analise", "retificacao", "elegibilidade"],
    },
    "Analista": {
        "Painel Estratégico": ["kpis", "funil", "sankey", "condicao", "elegibilidade", "mapa_territorial", "evolucao_temporal"],
        "Painel Tático":     ["analise", "retificacao", "elegibilidade", "gargalos"],
        "CARs":              ["kpis", "filtros", "tabela", "grafico_escopo", "exportar"],
        "Detalhe CAR":       ["busca", "ficha"],
        "Mapa":              ["upload", "mapa", "resumo"],
        "Dados / Tabelas":   ["analise", "retificacao", "elegibilidade"],
    },
    "IPAAM": {
        "Painel Estratégico": ["kpis", "funil", "condicao", "elegibilidade", "mapa_territorial"],
        "Painel Tático":     ["analise", "retificacao", "elegibilidade"],
        "CARs":              ["kpis", "filtros", "tabela", "grafico_escopo"],
        "Detalhe CAR":       ["busca", "ficha"],
        "Mapa":              ["upload", "mapa", "resumo"],
    },
    "GIZ": {
        "Painel Estratégico": ["kpis", "funil", "condicao", "elegibilidade", "mapa_territorial"],
        "CARs":              ["kpis", "tabela", "grafico_escopo"],
        "Mapa":              ["upload", "mapa", "resumo"],
    },
}


def _pode_ver(pagina, secao):
    """Verifica se o perfil logado pode ver a seção indicada."""
    perfil = st.session_state.get("perfil", "GIZ")
    secoes = _SECOES_POR_PERFIL.get(perfil, {}).get(pagina, [])
    return secao in secoes

# Ícones dos menus
_ICONES_MENU = {
    "Painel Estratégico": "📊",
    "Painel Tático": "🔧",
    "CARs": "🏷️",
    "Detalhe CAR": "🔍",
    "Mapa": "🗺️",
    "Dados / Tabelas": "📋",
}


def _obter_credenciais():
    """Obtém credenciais do secrets.toml ou usa padrão."""
    return _CREDENCIAIS_PADRAO


def _render_login():
    """Renderiza a tela de login. Retorna True se autenticado."""
    if st.session_state.get("autenticado"):
        return True

    import base64, pathlib
    _logo_login = pathlib.Path(__file__).parent / "assets" / "img" / "Floresta-Logo" / "Floresta-Logo COR 2.png"
    if _logo_login.exists():
        _logo_b64 = base64.b64encode(_logo_login.read_bytes()).decode()
        _logo_src = f"data:image/png;base64,{_logo_b64}"
    else:
        _logo_src = "https://www.florestamaisamazonia.org.br/wp-content/themes/tupi-florestamais/assets/img/logo_floresta_mono.png"

    # Fundo escuro na página inteira
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(160deg, #061F11 0%, #0D3B1E 40%, #1B5E20 70%, #0D3B1E 100%);
        }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stSidebar"] { display: none; }
        .stForm { background: rgba(255,255,255,0.07); border-radius: 12px; padding: 1.5rem; }
        .stForm label, .stForm .stMarkdown p { color: rgba(255,255,255,0.85) !important; }
        .stForm input { background: rgba(255,255,255,0.12) !important; color: #1B5E20 !important;
                        border: 1px solid rgba(255,255,255,0.2) !important; }
        .stForm input::placeholder { color: rgba(255,255,255,0.4) !important; }
        .stForm input:focus { color: #111 !important; background: rgba(255,255,255,0.85) !important; }
        .stForm button[kind="formSubmit"] { background: #2E7D32 !important; color: white !important;
                                            border: none !important; font-weight: 600 !important; }
        .stForm button[kind="formSubmit"]:hover { background: #388E3C !important; }
    </style>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown(f"""
        <div style="text-align: center; margin: 1rem 0 2rem 0;">
            <img src="{_logo_src}" alt="Floresta+ Amazônia" style="height: 160px; margin-bottom: 1.5rem;">
            <h2 style="font-family: Manrope, sans-serif; color: white; margin: 0;">Dashboard CAR / PRA</h2>
            <p style="color: rgba(255,255,255,0.6); font-family: Manrope, sans-serif;">Projeto Floresta+ — Amazônia Legal</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            usuario = st.text_input("Usuário", placeholder="Digite seu usuário")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submit = st.form_submit_button("🔓 Entrar", use_container_width=True)

        if submit:
            creds = _obter_credenciais()
            _usr = usuario.strip().lower()
            if _usr in creds and creds[_usr]["senha"] == senha:
                st.session_state["autenticado"] = True
                st.session_state["usuario"] = _usr
                st.session_state["perfil"] = creds[_usr]["perfil"]
                st.session_state["nome_usuario"] = creds[_usr]["nome"]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    return False


# ════════════════════════════════════════════════════════════════
# MAIN — ORQUESTRAÇÃO
# ════════════════════════════════════════════════════════════════

def main():
    # ── Login ──
    if not _render_login():
        return

    # ── Cabeçalho ──
    import base64, pathlib
    _logo_path = pathlib.Path(__file__).parent / "assets" / "img" / "LOGO_FLORESTAMAIS_TRANSPARENTE_V1.svg"
    if _logo_path.exists():
        _logo_b64 = base64.b64encode(_logo_path.read_bytes()).decode()
        _logo_src = f"data:image/svg+xml;base64,{_logo_b64}"
    else:
        _logo_src = "https://www.florestamaisamazonia.org.br/wp-content/themes/tupi-florestamais/assets/img/logo_floresta_mono.png"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #1565C0 100%);
                padding: 1.2rem 2rem; border-radius: 12px; margin-bottom: 1rem; font-family: Manrope, sans-serif;
                display: flex; align-items: center; gap: 1.2rem;">
        <img src="{_logo_src}"
             alt="Floresta+ Amazônia" style="height: 100px; flex-shrink: 0;">
        <div>
            <h1 style="color: white; margin: 0; font-size: 1.8rem; font-family: Manrope, sans-serif;">Dashboard — Projeto CAR / PRA</h1>
            <p style="color: rgba(255,255,255,0.85); margin: 0.3rem 0 0 0; font-size: 0.95rem; font-family: Manrope, sans-serif;">
                Análise de CAR · Retificação · Elegibilidade PRA — Amazônia Legal
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar: Upload + Filtros ──
    with st.sidebar:

        # ── Usuário logado + Sair ──
        _perfil = st.session_state.get("perfil", "")
        _nome = st.session_state.get("nome_usuario", "")
        _usr_col, _sair_col = st.columns([3, 1])
        _usr_col.caption(f"👤 {_nome} ({_perfil})")
        if _sair_col.button("❌", help="Sair", key="btn_logout"):
            for k in ["autenticado", "usuario", "perfil", "nome_usuario"]:
                st.session_state.pop(k, None)
            st.rerun()
        
        # ── Modo (filtrado por perfil) ──
        _menus_permitidos = _MENUS_POR_PERFIL.get(_perfil, _MENUS_POR_PERFIL["GIZ"])
        _opcoes_menu = [f"{_ICONES_MENU[m]} {m}" for m in _menus_permitidos]
        st.markdown("### 🔀 Menu")
        modo = st.radio("Menu", _opcoes_menu, index=0,
                        label_visibility="collapsed")

        st.divider()
        
        st.markdown("### 📂 Dados")
        arquivo = st.file_uploader(
            "Faça upload do arquivo .xlsx",
            type=["xlsx", "xls"],
            help="Planilha com abas: Cadastros CAR, Retificação CAR, Elegibilidade CAR",
        )

        if arquivo:
            file_bytes = arquivo.read()
            df_a_raw, df_r_raw, df_e_raw = carregar_e_limpar(file_bytes, arquivo.name)
            st.success(f"Carregado: {arquivo.name}")
        else:
            st.warning("Faça upload do arquivo .xlsx para começar.")
            st.stop()

        st.divider()

        # ── Filtros globais ──
        st.markdown("### 🎯 Filtros")

        filtros = {}

        # Código do CAR
        filtros["car"] = st.text_input("Código do CAR",
                                       placeholder="Ex: AM-1300060-...",
                                       help="Filtre por código completo ou parcial do CAR")

        # Município
        if "Município" in df_a_raw.columns:
            municipios_disp = sorted(df_a_raw["Município"].dropna().unique())
            filtros["municipios"] = st.multiselect("Município", municipios_disp,
                                                    placeholder="Selecione...",
                                                    help="Filtre por um ou mais municípios")

        # Lote
        if "LOTE" in df_a_raw.columns:
            lotes_disp = sorted(df_a_raw["LOTE"].dropna().unique())
            filtros["lotes"] = st.multiselect("Lote", lotes_disp,
                                               placeholder="Selecione...",
                                               help="Filtre por um ou mais lotes")

        # Status
        if "Condição_norm" in df_a_raw.columns:
            status_disp = sorted(df_a_raw["Condição_norm"].dropna().unique())
            filtros["status"] = st.multiselect("Status de Análise", status_disp, placeholder="Selecione...")

        # Ciclos
        if "Ciclo de análise" in df_a_raw.columns:
            ciclos_disp = sorted(df_a_raw["Ciclo de análise"].dropna().unique())
            ciclos_disp = [int(c) for c in ciclos_disp if c in [1, 2, 3, 4]]
            filtros["ciclos"] = st.multiselect("Ciclo de Análise", ciclos_disp, placeholder="Selecione...")

        # Elegibilidade
        if "Elegibilidade" in df_e_raw.columns:
            eleg_disp = sorted(df_e_raw["Elegibilidade"].dropna().unique())
            filtros["elegibilidade"] = st.multiselect("Elegibilidade PSA", eleg_disp, placeholder="Selecione...")

        # UF
        if "UF" in df_e_raw.columns:
            uf_disp = sorted(df_e_raw["UF"].dropna().unique())
            filtros["ufs"] = st.multiselect("UF (Elegibilidade)", uf_disp, placeholder="Selecione...")

        # Período
        if "Data fim" in df_a_raw.columns:
            datas_validas = df_a_raw["Data fim"].dropna()
            if not datas_validas.empty:
                st.markdown("**Período (Data fim)**")
                d_min = datas_validas.min().date()
                d_max = datas_validas.max().date()
                datas_sel = st.date_input(
                    "Intervalo", value=(d_min, d_max), min_value=d_min, max_value=d_max,
                    label_visibility="collapsed",
                )
                # Só marca como filtro ativo se o usuário alterou o intervalo
                if isinstance(datas_sel, tuple) and len(datas_sel) == 2:
                    sel_ini, sel_fim = datas_sel
                    if sel_ini != d_min or sel_fim != d_max:
                        filtros["data_inicio"] = sel_ini
                        filtros["data_fim"] = sel_fim

        st.divider()

    # ── Aplicar filtros ──
    df_a, df_r, df_e = aplicar_filtros(df_a_raw, df_r_raw, df_e_raw, filtros)

    # ── Indicador de filtros ativos ──
    filtros_ativos = {k: v for k, v in filtros.items() if v and v != []}
    if filtros_ativos:
        tags = " · ".join([f"**{k}**: {len(v) if isinstance(v, list) else v}" for k, v in filtros_ativos.items()])
        st.markdown(f"🔍 Filtros ativos: {tags}")
        st.caption(f"Registros: Análise={fmt_int(len(df_a))} | Retificação={fmt_int(len(df_r))} | Elegibilidade={fmt_int(len(df_e))}")

    # ── KPIs ──
    kpis = calcular_kpis(df_a, df_r, df_e)

    # ── Renderização ──
    if "Painel Estratégico" in modo:
        render_estrategico(df_a, df_r, df_e, kpis)
    elif "Painel Tático" in modo:
        render_tatico(df_a, df_r, df_e, kpis)
    elif "CARs" in modo:
        render_cars(df_a, df_r, df_e)
    elif "Detalhe CAR" in modo:
        render_detalhe_car(df_a, df_r, df_e)
    elif "Mapa" in modo:
        render_mapa(df_a, df_r, df_e)
    else:
        render_dados_tabela(df_a, df_r, df_e)

    # ── Exportação ──
    st.divider()
    st.markdown("### 📥 Exportar Relatório")
    col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])

    with col_exp1:
        xlsx_data = exportar_xlsx(df_a, df_r, df_e, kpis, filtros_ativos)
        st.download_button(
            label="⬇️ Baixar Excel (.xlsx)",
            data=xlsx_data,
            file_name=f"relatorio_car_filtrado_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
        )

    with col_exp2:
        # CSV dos KPIs
        kpi_csv = pd.DataFrame([
            {"Indicador": k.replace("_", " ").title(), "Valor": str(v)}
            for k, v in kpis.items()
        ]).to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ KPIs (.csv)",
            data=kpi_csv,
            file_name=f"kpis_car_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    # ── Footer ──
    st.markdown("---")
    st.markdown(
        "<p style='text-align:center; color:#9E9E9E; font-size:0.8rem;'>"
        "Dashboard Projeto Floresta+ · CAR/PRA - Amazônia Legal ·  Amazônia "
        "</p>", unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
