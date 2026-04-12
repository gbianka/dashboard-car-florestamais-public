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
<style>
html, body, .stApp, .stApp * {
    font-family: 'Manrope', sans-serif;
}
[class*="material-symbols"],
[class*="material-icons"] {
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


# ════════════════════════════════════════════════════════════════
# §3  CARREGAMENTO E LIMPEZA DE DADOS
# ════════════════════════════════════════════════════════════════

def normalizar_texto(s):
    if pd.isna(s): return s
    s = str(s).strip()
    return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")


def col_existe(df, nome):
    """Verifica se coluna existe (case-insensitive fuzzy)."""
    for c in df.columns:
        if nome.lower() in c.lower():
            return c
    return None


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
    col_car_r = col_existe(df_r, "código do car") or col_existe(df_r, "Código do CAR")
    if col_car_r and col_car_r != "Código do CAR":
        df_r = df_r.rename(columns={col_car_r: "Código do CAR"})

    # ── Limpeza Elegibilidade ──
    col_car_e = col_existe(df_e, "nº do car") or col_existe(df_e, "Nº DO CAR")
    if col_car_e and col_car_e != "Nº DO CAR":
        df_e = df_e.rename(columns={col_car_e: "Nº DO CAR"})

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
    kpis["municipios_analise"] = df_a["Município"].nunique() if "Município" in df_a.columns else 0
    kpis["tecnicos"] = df_a["Técnico"].nunique() if "Técnico" in df_a.columns else 0

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
    st.markdown("### 📊 Indicadores-Chave do Projeto")
    # ── Linha 1: Análise ──
    st.caption("Análise")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Atuação do Projeto", fmt_int(kpis['registros_analise']))
    a2.metric("CARs Únicos", fmt_int(kpis['cars_analise']))
    a3.metric("Municípios", fmt_int(kpis['municipios_analise']))
    a4.metric("CARs com Pendência", fmt_pct(kpis['pct_pendencia']),
              delta=f"-{fmt_pct(kpis['pct_sem_pendencia'])} sem", delta_color="inverse")

    # ── Linha 2 ──
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CARs Analisados", fmt_int(kpis['cars_analise']),
              f"{fmt_int(kpis['registros_analise'])} registros")
    c2.metric("CARs Retificados", fmt_int(kpis['cars_retif']),
              f"{fmt_int(kpis['registros_retif'])} registros")
    c3.metric("Elegibilidade PRA", fmt_pct(kpis['pct_elegivel']),
              f"{fmt_int(kpis['n_fase1'] + kpis['n_fase2'])} elegíveis")
    c4.metric("CARs com Pendência", fmt_pct(kpis['pct_pendencia']),
              delta=f"-{fmt_pct(kpis['pct_sem_pendencia'])} sem", delta_color="inverse")

    # ── Linha 3 ──
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Municípios", fmt_int(kpis['municipios_analise']))
    c6.metric("Técnicos", fmt_int(kpis['tecnicos']))
    c7.metric("Média de Ciclos", fmt_dec(kpis['media_ciclos'], 2))
    c8.metric("1º Ciclo", fmt_pct(kpis['pct_1ciclo']))

    st.divider()

    # ── Funil + Sankey ──
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown("#### Funil do Projeto")
        fig_funil = go.Figure(go.Funnel(
            y=["Análise de CAR", "Retificação de CAR", "Elegibilidade PRA"],
            x=[kpis["cars_analise"], kpis["cars_retif"], kpis["cars_eleg"]],
            textposition="inside", textinfo="value+percent initial",
            marker=dict(color=[COR["azul"], COR["laranja"], COR["verde_claro"]]),
        ))
        fig_funil.update_layout(height=350, margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig_funil, width="stretch")

    with col_right:
        st.markdown("#### Fluxo entre Escopos (Sankey)")
        node_labels = ["Análise", "Só Análise", "Retificação", "Elegibilidade",
                       "Análise+Retif", "Análise+Eleg", "Todos 3"]
        node_values = [
            kpis["cars_analise"],
            kpis["so_analise"],
            kpis["cars_retif"],
            kpis["cars_eleg"],
            kpis["a_r"],
            kpis["a_e"],
            kpis["todos_3"],
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
                value=[kpis["so_analise"], kpis["a_r"], kpis["a_e"], kpis["todos_3"]],
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
        st.markdown("#### Condição Final do Cadastro")
        if "Condição_norm" in df_a.columns:
            cond = df_a["Condição_norm"].value_counts()
            cores_cond = {
                "Com pendências": COR["vermelho"], "Em conformidade": COR["verde_claro"],
                "Aguard. regularização": COR["amarelo"], "Conformidade (CRA)": COR["verde_escuro"],
                "Conformidade (ativos)": COR["verde"], "Aprovado": COR["azul"], "Outros": COR["cinza"],
            }
            fig_cond = px.pie(
                values=cond.values, names=cond.index, hole=0.45,
                color=cond.index, color_discrete_map=cores_cond,
            )
            fig_cond.update_traces(textinfo="percent+value", textposition="auto")
            fig_cond.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10),
                                   legend=dict(font=dict(size=10)))
            st.plotly_chart(fig_cond, width="stretch")

    with col_b:
        st.markdown("#### Elegibilidade para PRA")
        if "Elegibilidade" in df_e.columns:
            eleg = df_e["Elegibilidade"].value_counts()
            cores_eleg = {"Inelegível": COR["vermelho"], "Fase 1": COR["verde_claro"], "Fase 2": COR["verde_escuro"]}
            fig_eleg = px.pie(
                values=eleg.values, names=eleg.index, hole=0.45,
                color=eleg.index, color_discrete_map=cores_eleg,
            )
            fig_eleg.update_traces(textinfo="percent+value", textposition="auto")
            fig_eleg.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_eleg, width="stretch")

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
    st.markdown("#### 📈 Evolução Temporal")
    if "Data fim" in df_a.columns:
        df_tempo = df_a.dropna(subset=["Data fim"]).copy()
        if not df_tempo.empty:
            df_tempo["Mês"] = df_tempo["Data fim"].dt.to_period("M").astype(str)
            mensal = df_tempo.groupby("Mês").agg(
                total=("Nº DO CAR", "count"),
                cars_unicos=("Nº DO CAR", "nunique"),
            ).reset_index()
            fig_tempo = go.Figure()
            fig_tempo.add_trace(go.Scatter(
                x=mensal["Mês"], y=mensal["total"], mode="lines+markers",
                name="Total análises", line=dict(color=COR["azul"], width=3),
                fill="tozeroy", fillcolor="rgba(21,101,192,0.08)",
            ))
            fig_tempo.add_trace(go.Bar(
                x=mensal["Mês"], y=mensal["cars_unicos"], name="CARs únicos",
                marker_color=COR["verde_claro"], opacity=0.6,
            ))
            fig_tempo.update_layout(
                height=380, xaxis_tickangle=-45,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(l=40, r=20, t=40, b=80),
            )
            st.plotly_chart(fig_tempo, width="stretch")


# ════════════════════════════════════════════════════════════════
# §7  MODO TÁTICO
# ════════════════════════════════════════════════════════════════

def _titulo_grafico(titulo, total_grafico, total_df):
    """Exibe título do gráfico com ícone de alerta inline se houver divergência."""
    diff = total_df - total_grafico
    if diff != 0:
        tooltip = (f"{fmt_int(total_grafico)} de {fmt_int(total_df)} registros "
                   f"({fmt_int(diff)} sem dados nesta coluna)")
        st.markdown(
            f'##### {titulo} <span title="{tooltip}" style="cursor:help; font-size:0.85em;">⚠️</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f"##### {titulo}")


def render_tatico(df_a, df_r, df_e, kpis):
    """Renderiza o painel tático (visão operacional detalhada)."""

    tab_analise, tab_retif, tab_eleg, tab_gargalos = st.tabs([
        "🔍 Análise de CAR", "🔧 Retificação", "✅ Elegibilidade PRA", "⚠️ Gargalos"
    ])

    # ────────────────────────────────────────────────────────
    # TAB: ANÁLISE DE CAR
    # ────────────────────────────────────────────────────────
    with tab_analise:
        st.markdown("### Detalhamento — Análise de CAR")

        total_a = len(df_a)

        a1, a2, a3, a4 = st.columns(4)
        a1.metric("Atuação do Projeto", fmt_int(kpis['registros_analise']))
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
        if "Município" in df_a.columns and "Condição_norm" in df_a.columns:
            top10 = df_a["Município"].value_counts().head(10).index
            df_t10 = df_a[df_a["Município"].isin(top10)]
            cross = pd.crosstab(df_t10["Município"], df_t10["Condição_norm"])
            cross = cross.reindex(top10)
            cores_cn = {
                "Com pendências": COR["vermelho"], "Em conformidade": COR["verde_claro"],
                "Aguard. regularização": COR["amarelo"], "Conformidade (CRA)": COR["verde_escuro"],
                "Conformidade (ativos)": COR["verde"], "Aprovado": COR["azul"], "Outros": COR["cinza"],
            }
            fig_mc = px.bar(cross, barmode="stack", color_discrete_map=cores_cn)
            fig_mc.update_layout(height=400, xaxis_tickangle=-45, legend=dict(font=dict(size=9)),
                                 margin=dict(l=40, r=20, t=20, b=80))
            st.plotly_chart(fig_mc, width="stretch")

    # ────────────────────────────────────────────────────────
    # TAB: RETIFICAÇÃO
    # ────────────────────────────────────────────────────────
    with tab_retif:
        st.markdown("### Detalhamento — Retificação de CAR")
        total_r = len(df_r)

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
        st.markdown("### Detalhamento — Elegibilidade para PRA")
        total_e = len(df_e)

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
# MAIN — ORQUESTRAÇÃO
# ════════════════════════════════════════════════════════════════

def main():
    # ── Cabeçalho ──
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #1565C0 100%);
                padding: 1.2rem 2rem; border-radius: 12px; margin-bottom: 1rem; font-family: Manrope, sans-serif;">
        <h1 style="color: white; margin: 0; font-size: 1.8rem; font-family: Manrope, sans-serif;">🌿 Dashboard — Projeto CAR / PRA</h1>
        <p style="color: rgba(255,255,255,0.85); margin: 0.3rem 0 0 0; font-size: 0.95rem; font-family: Manrope, sans-serif;">
            Análise de CAR · Retificação · Elegibilidade PRA — Amazônia Legal
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sidebar: Upload + Filtros ──
    with st.sidebar:
        
        # ── Modo ──
        st.markdown("### 🔀 Menu")
        modo = st.radio("Menu", ["📊 Painel Estratégico", "🔧 Painel Tático", "📋 Dados / Tabelas"], index=0,
                        label_visibility="collapsed",
                        help="Estratégico: visão executiva. Tático: detalhamento operacional. Dados: tabelas brutas para normalização.")

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
            filtros["elegibilidade"] = st.multiselect("Elegibilidade PRA", eleg_disp, placeholder="Selecione...")

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
        "Dashboard CAR/PRA · Amazônia Legal · Gerado com Streamlit + Plotly"
        "</p>", unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
