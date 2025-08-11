import streamlit as st
import pandas as pd
from datetime import datetime
import groq # Importa a biblioteca da Groq

# --- 1. Configuração da Página (Mobile-First) ---
st.set_page_config(
    page_title="Finanças com IA",
    page_icon="🤖💰",
    layout="centered", # 'centered' é melhor para visualização em mobile
    initial_sidebar_state="collapsed"
)

# --- CSS Customizado para Melhorar a Aparência Mobile ---
st.markdown("""
<style>
    /* Reduz o padding no topo da página */
    .block-container {
        padding-top: 2rem;
    }
    /* Estiliza os cards de métricas para ficarem mais compactos */
    [data-testid="metric-container"] {
        background-color: #222;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    [data-testid="stForm"] {
        background-color: #1a1a1a;
        padding: 20px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Funções de Dados e IA ---

# Carrega os dados de um CSV. Se não existir, cria um DataFrame vazio.
def carregar_dados():
    try:
        df = pd.read_csv('transacoes.csv')
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Data', 'Descrição', 'Valor', 'Tipo', 'Categoria'])

# Salva o DataFrame no arquivo CSV.
def salvar_dados(df):
    df.to_csv('transacoes.csv', index=False)

# Função para chamar a API da Groq e categorizar a despesa
def categorizar_com_ia(descricao):
    """
    Usa a IA da Groq para sugerir uma categoria para a despesa.
    """
    if not descricao:
        return None

    try:
        # A chave de API é lida dos "Secrets" do Streamlit
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente financeiro especialista em categorizar despesas. "
                        "Responda APENAS com UMA das seguintes categorias: "
                        "Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Salário, Investimentos, Outros. "
                        "Se não tiver certeza, responda com 'Outros'."
                    )
                },
                {
                    "role": "user",
                    "content": f"Categorize a seguinte despesa: '{descricao}'"
                }
            ],
            model="llama3-8b-8192",
            temperature=0.0,
        )
        categoria_sugerida = chat_completion.choices[0].message.content.strip()
        return categoria_sugerida
    except Exception as e:
        st.error(f"Erro ao conectar com a IA: {e}")
        return None

# --- 3. Inicialização e Carregamento de Dados ---
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_dados()

if 'categoria_sugerida' not in st.session_state:
    st.session_state.categoria_sugerida = ""

# --- 4. Interface do Usuário (UI) ---

st.title("🤖 Finanças com IA")
st.markdown("Adicione suas transações e deixe a IA ajudar a organizar.")

# --- Formulário de Entrada ---
with st.form("nova_transacao_form"):
    st.header("Adicionar Nova Transação")

    # Layout em 2 colunas para melhor encaixe no mobile
    col1, col2 = st.columns(2)
    with col1:
        descricao = st.text_input("Descrição", placeholder="Ex: Almoço no shopping")
        tipo = st.selectbox("Tipo", ["Despesa", "Receita"])
    with col2:
        valor = st.number_input("Valor", min_value=0.01, format="%.2f")
        data = st.date_input("Data", datetime.now())

    # Lógica do Botão de Sugestão com IA
    if st.form_submit_button("Sugerir Categoria com IA ✨"):
        with st.spinner("A IA está pensando... 🤔"):
            sugestao = categorizar_com_ia(descricao)
            if sugestao:
                st.session_state.categoria_sugerida = sugestao

    # Dropdown de Categorias
    categorias_disponiveis = ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Salário", "Investimentos", "Outros"]
    
    # Define o índice padrão baseado na sugestão da IA
    try:
        indice_sugerido = categorias_disponiveis.index(st.session_state.categoria_sugerida)
    except ValueError:
        indice_sugerido = 0 # Padrão para o primeiro item se a sugestão não for encontrada

    categoria_selecionada = st.selectbox("Categoria", categorias_disponiveis, index=indice_sugerido)

    # Botão principal para adicionar
    if st.form_submit_button("✅ Adicionar Transação"):
        if not descricao or valor <= 0:
            st.warning("Por favor, preencha a descrição e o valor.")
        else:
            nova_transacao = pd.DataFrame([[data, descricao, valor, tipo, categoria_selecionada]], columns=['Data', 'Descrição', 'Valor', 'Tipo', 'Categoria'])
            st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
            salvar_dados(st.session_state.transacoes)
            st.success("Transação adicionada com sucesso!")
            st.session_state.categoria_sugerida = "" # Limpa a sugestão após adicionar


# --- 5. Visualização dos Dados ---

st.header("Resumo Financeiro")
total_receitas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Receita']['Valor'].sum()
total_despesas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']['Valor'].sum()
saldo = total_receitas - total_despesas

# Colunas para as métricas, elas se empilham verticalmente em telas pequenas
col1, col2, col3 = st.columns(3)
col1.metric("Receitas", f"R${total_receitas:,.2f}", delta_color="normal")
col2.metric("Despesas", f"R${total_despesas:,.2f}", delta_color="inverse")
col3.metric("Saldo", f"R${saldo:,.2f}", delta=f"{saldo - total_receitas:,.2f}")


# --- Gráfico de Despesas ---
despesas_df = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']
if not despesas_df.empty:
    st.header("Análise de Despesas")
    despesas_por_categoria = despesas_df.groupby('Categoria')['Valor'].sum()
    st.bar_chart(despesas_por_categoria)

# --- Histórico de Transações ---
st.header("Histórico de Transações")
st.dataframe(st.session_state.transacoes.sort_values(by="Data", ascending=False), use_container_width=True)

# Aviso sobre a persistência de dados
st.info("ℹ️ Os dados são salvos no servidor da aplicação. Se a aplicação for reiniciada por inatividade, os dados podem ser perdidos. Para uso contínuo, considere uma solução com banco de dados.", icon="ℹ️")
