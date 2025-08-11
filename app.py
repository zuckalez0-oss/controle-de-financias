import streamlit as st
import pandas as pd
from datetime import datetime
import groq

# --- 1. Configuração da Página (Mobile-First) ---
st.set_page_config(
    page_title="Finanças com IA",
    page_icon="🤖💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS Customizado para Melhorar a Aparência Mobile ---
# (Pequenos ajustes para melhor espaçamento e legibilidade)
st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .st-emotion-cache-16txtl3 { /* Classe específica para o container do form */
        padding: 20px;
        background-color: #1a1a1a;
        border-radius: 10px;
    }
    [data-testid="metric-container"] {
        background-color: #222;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    /* Melhora a visibilidade dos títulos dentro das abas */
    h2 {
        font-size: 1.5rem;
        color: #FAFAFA;
        border-bottom: 2px solid #333;
        padding-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)


# --- 2. Funções de Dados e IA ---

def carregar_dados():
    try:
        df = pd.read_csv('transacoes.csv')
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=['Data', 'Descrição', 'Valor', 'Tipo', 'Categoria'])

def salvar_dados(df):
    df.to_csv('transacoes.csv', index=False)

def categorizar_com_ia(descricao):
    if not descricao: return None
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Você é um assistente financeiro. Categorize a despesa em UMA das categorias: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Salário, Investimentos, Outros. Responda APENAS com a categoria."},
                {"role": "user", "content": f"Categorize: '{descricao}'"}
            ],
            model="llama3-8b-8192", temperature=0.0
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Erro na API Groq: {e}") # Loga o erro no terminal para debug
        return None

# --- 3. Inicialização e Carregamento de Dados ---
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_dados()
if 'categoria_sugerida' not in st.session_state:
    st.session_state.categoria_sugerida = ""

# --- 4. Interface Principal ---

st.title("🤖 Finanças com IA")

# --- CRIAÇÃO DAS ABAS (A "SEGUNDA BARRA") ---
tab_lancamento, tab_analise = st.tabs(["✍️ Lançar", "📊 Histórico & Análise"])

# --- ABA 1: FORMULÁRIO DE LANÇAMENTO ---
with tab_lancamento:
    st.header("Adicionar Nova Transação")
    with st.form("nova_transacao_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input("Descrição", placeholder="Ex: Almoço")
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"], label_visibility="collapsed")
        with col2:
            valor = st.number_input("Valor", min_value=0.01, format="%.2f")
            data = st.date_input("Data", datetime.now(), label_visibility="collapsed")

        if st.form_submit_button("Sugerir Categoria com IA ✨"):
            with st.spinner("A IA está pensando... 🤔"):
                sugestao = categorizar_com_ia(descricao)
                if sugestao:
                    st.session_state.categoria_sugerida = sugestao

        categorias = ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Salário", "Investimentos", "Outros"]
        try:
            indice_sugerido = categorias.index(st.session_state.categoria_sugerida)
        except ValueError:
            indice_sugerido = 0

        categoria_selecionada = st.selectbox("Categoria", categorias, index=indice_sugerido)

        if st.form_submit_button("✅ Adicionar Transação"):
            if not descricao or valor <= 0:
                st.warning("Por favor, preencha a descrição e o valor.")
            else:
                nova_transacao = pd.DataFrame([[data, descricao, valor, tipo, categoria_selecionada]], columns=['Data', 'Descrição', 'Valor', 'Tipo', 'Categoria'])
                st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
                salvar_dados(st.session_state.transacoes)
                st.success("Transação adicionada!")
                st.session_state.categoria_sugerida = ""
                st.rerun() # Recarrega a página para atualizar a outra aba

# --- ABA 2: HISTÓRICO E ANÁLISES ---
with tab_analise:
    st.header("Resumo Financeiro")
    total_receitas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Receita']['Valor'].sum()
    total_despesas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']['Valor'].sum()
    saldo = total_receitas - total_despesas

    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R${total_receitas:,.2f}")
    col2.metric("Despesas", f"R${total_despesas:,.2f}")
    col3.metric("Saldo", f"R${saldo:,.2f}")
    
    st.divider() # Adiciona uma linha divisória

    # Gráfico de Despesas
    despesas_df = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']
    if not despesas_df.empty:
        st.header("Despesas por Categoria")
        despesas_por_categoria = despesas_df.groupby('Categoria')['Valor'].sum()
        st.bar_chart(despesas_por_categoria, use_container_width=True)
        st.divider()

    # Histórico de Transações
    st.header("Todas as Transações")
    st.dataframe(st.session_state.transacoes.sort_values(by="Data", ascending=False), use_container_width=True)
