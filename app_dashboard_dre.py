import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Dashboard Interativo DRE", layout="wide")

ARQUIVO_PADRAO = "DRE 2019.xlsx"

# --- Sistema de Login ---
USUARIOS = {
    "ViniciusAdmin": "vini123",
    "user": "user123",
}

def check_credentials(username, password):
    return USUARIOS.get(username) == password

# Inicializar o estado de login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):
        if check_credentials(username, password):
            st.session_state.logged_in = True
            st.sidebar.success("Login realizado com sucesso!")
            st.rerun() # Recarregar a página para mostrar o dashboard
        else:
            st.sidebar.error("Usuário ou senha incorretos.")
    st.stop() # Parar a execução se não estiver logado
# --- Fim do Sistema de Login ---


@st.cache_data
def carregar_dados(arquivo):
    # ... (sua função carregar_dados existente) ...
    plano = pd.read_excel(arquivo, sheet_name="Plano de Contas")
    realizado = pd.read_excel(arquivo, sheet_name="Realizado")
    orcado = pd.read_excel(arquivo, sheet_name="Orçado")

    realizado["Conta"] = realizado["Conta"].astype(str)
    orcado["Conta"] = orcado["Conta"].astype(str)
    plano["Conta"] = plano["Conta"].astype(str)

    realizado["Mês/Ano"] = pd.to_datetime(realizado["Mês/Ano"])
    orcado["Mês/Ano"] = pd.to_datetime(orcado["Mês/Ano"])

    df_real = realizado.merge(plano, on="Conta", how="left")
    df_orc = orcado.merge(plano, on="Conta", how="left")

    df_real["Tipo"] = "Realizado"
    df_orc["Tipo"] = "Orçado"

    df_real = df_real.rename(columns={"Valor Realizado": "Valor"})
    df_orc = df_orc.rename(columns={"Valor Orçado": "Valor"})

    df = pd.concat([df_real, df_orc], ignore_index=True)
    df["Ano"] = df["Mês/Ano"].dt.year
    df["Mes"] = df["Mês/Ano"].dt.month
    df["Mes_Nome"] = df["Mês/Ano"].dt.strftime("%b/%Y")

    return df

st.title("Dashboard Interativo de Análise de Dados")
st.caption("O usuário escolhe dimensões, métricas e tipo de gráfico a partir das tabelas do Excel.")

with st.sidebar:
    # Adicionar um botão de logout se o usuário estiver logado
    if st.session_state.logged_in:
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    st.header("Configurações")
    arquivo = st.file_uploader(
        "Envie um arquivo Excel",
        type=["xlsx"],
        help="Se nada for enviado, o app tenta abrir o arquivo DRE 2019.xlsx na mesma pasta."
    )

if arquivo is not None:
    df = carregar_dados(arquivo)
else:
    df = carregar_dados(ARQUIVO_PADRAO)

st.subheader("Pré-visualização dos dados")
st.dataframe(df.head(20), use_container_width=True)

st.sidebar.header("Filtros")
tipos = st.sidebar.multiselect("Tipo", sorted(df["Tipo"].dropna().unique()), default=sorted(df["Tipo"].dropna().unique()))
n1 = st.sidebar.multiselect("Nível 1", sorted(df["Nível 1"].dropna().unique()), default=sorted(df["Nível 1"].dropna().unique()))
n2 = st.sidebar.multiselect("Nível 2", sorted(df["Nível 2"].dropna().unique()), default=sorted(df["Nível 2"].dropna().unique()))
contas = st.sidebar.multiselect("Conta / Descrição", sorted(df["Descrição da Conta"].dropna().unique()))

anos = sorted(df["Ano"].dropna().unique())
anos_sel = st.sidebar.multiselect("Ano", anos, default=anos)

df_f = df.copy()
df_f = df_f[df_f["Tipo"].isin(tipos)]
df_f = df_f[df_f["Nível 1"].isin(n1)]
df_f = df_f[df_f["Nível 2"].isin(n2)]
df_f = df_f[df_f["Ano"].isin(anos_sel)]
if contas:
    df_f = df_f[df_f["Descrição da Conta"].isin(contas)]

st.sidebar.header("Montagem do gráfico")
dimensoes = {
    "Mês/Ano": "Mes_Nome",
    "Conta": "Conta",
    "Descrição da Conta": "Descrição da Conta",
    "Nível 1": "Nível 1",
    "Nível 2": "Nível 2",
    "Tipo": "Tipo",
    "Ano": "Ano",
    "Mês": "Mes",
}
x_label = st.sidebar.selectbox("Eixo X", list(dimensoes.keys()), index=0)
cor_label = st.sidebar.selectbox("Cor / Série", ["Nenhuma"] + list(dimensoes.keys()), index=5)
grafico = st.sidebar.selectbox("Tipo de gráfico", ["Barra", "Linha", "Pizza", "Área"])
agregacao = st.sidebar.selectbox("Agregação", ["Soma", "Média", "Contagem"])

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Registros filtrados", f"{len(df_f):,}".replace(",", "."))
with col2:
    st.metric("Valor total", f"R$ {df_f['Valor'].sum():,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col3:
    st.metric("Média", f"R$ {df_f['Valor'].mean():,.0f}".replace(",", "X").replace(".", ",").replace("X", "."))
with col4:
    st.metric("Qtd. contas", int(df_f["Conta"].nunique()))

if df_f.empty:
    st.warning("Nenhum dado encontrado com os filtros escolhidos.")
    st.stop()

x = dimensoes[x_label]
cor = None if cor_label == "Nenhuma" else dimensoes[cor_label]

if agregacao == "Soma":
    df_plot = df_f.groupby([x] + ([cor] if cor else []), dropna=False, as_index=False)["Valor"].sum()
    titulo_y = "Soma do Valor"
elif agregacao == "Média":
    df_plot = df_f.groupby([x] + ([cor] if cor else []), dropna=False, as_index=False)["Valor"].mean()
    titulo_y = "Média do Valor"
else:
    df_plot = df_f.groupby([x] + ([cor] if cor else []), dropna=False, as_index=False)["Valor"].count()
    titulo_y = "Contagem"
    df_plot = df_plot.rename(columns={"Valor": "Contagem"})

st.subheader("Comparativo Realizado vs. Orçado")

df_comparativo = df_f[df_f["Tipo"].isin(["Realizado", "Orçado"])]

df_comparativo_agrupado = df_comparativo.groupby(["Mes_Nome", "Nível 1", "Tipo"], as_index=False)["Valor"].sum()

df_pivot = df_comparativo_agrupado.pivot_table(index=["Mes_Nome", "Nível 1"], columns="Tipo", values="Valor").reset_index()
df_pivot = df_pivot.fillna(0) 

df_pivot["Diferenca"] = df_pivot["Orçado"] - df_pivot["Realizado"]
df_pivot["Perda"] = df_pivot["Diferenca"].apply(lambda x: x if x > 0 else 0) # Apenas valores positivos para perdas

fig_comp = px.bar(
    df_pivot,
    x="Mes_Nome",
    y=["Realizado", "Orçado"],
    barmode="group",
    title="Comparativo Realizado vs. Orçado",
    labels={"value": "Valor", "variable": "Tipo"},
    color_discrete_map={"Realizado": "blue", "Orçado": "orange"}
)

for index, row in df_pivot[df_pivot["Perda"] > 0].iterrows():
    fig_comp.add_annotation(
        x=row["Mes_Nome"],
        y=row["Orçado"],
        text=f"Perda: R$ {row['Perda']:,.0f}".replace(",", "X").replace(".", ",").replace("X", "."),
        showarrow=True,
        arrowhead=2,
        yshift=10,
        font=dict(color="red", size=10)
    )

fig_comp.update_layout(template="plotly_white")
st.plotly_chart(fig_comp, use_container_width=True)

st.subheader("Gráfico dinâmico")

if grafico == "Barra":
    if agregacao == "Contagem":
        fig = px.bar(df_plot, x=x, y="Contagem", color=cor, barmode="group", title="Gráfico de barras")
    else:
        fig = px.bar(df_plot, x=x, y="Valor", color=cor, barmode="group", title="Gráfico de barras")
elif grafico == "Linha":
    if agregacao == "Contagem":
        fig = px.line(df_plot, x=x, y="Contagem", color=cor, markers=True, title="Gráfico de linhas")
    else:
        fig = px.line(df_plot, x=x, y="Valor", color=cor, markers=True, title="Gráfico de linhas")
elif grafico == "Pizza":
    base_pizza = df_plot.groupby(x, as_index=False)[df_plot.columns[-1]].sum()
    fig = px.pie(base_pizza, names=x, values=base_pizza.columns[-1], title="Gráfico de pizza")
else:
    if agregacao == "Contagem":
        fig = px.area(df_plot, x=x, y="Contagem", color=cor, title="Gráfico de área")
    else:
        fig = px.area(df_plot, x=x, y="Valor", color=cor, title="Gráfico de área")

fig.update_layout(template="plotly_white")
fig.update_layout(xaxis_title=x_label, yaxis_title=titulo_y)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Tabela resumida")
st.dataframe(df_plot, use_container_width=True)

csv = df_plot.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Baixar tabela resumida em CSV",
    data=csv,
    file_name="resumo_dashboard.csv",
    mime="text/csv",
)

pdf = fig.to_image(format="pdf")
st.download_button(
    "Baixar tabela resumida em PDF",
    data=pdf,
    file_name="dre_painel_plotly.pdf",
    mime="application/pdf"
)

with st.expander("Como este dashboard funciona"):
    st.markdown(
        """
        - Lê as abas **Plano de Contas**, **Realizado** e **Orçado**
        - Junta as tabelas pela coluna **Conta**
        - Permite filtrar por tipo, nível, conta e ano
        - O usuário escolhe:
          - eixo X
          - série/cor
          - tipo de gráfico
          - agregação
        - Gera tabela resumida e gráfico automaticamente
        """
    )