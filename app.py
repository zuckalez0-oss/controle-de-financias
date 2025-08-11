import streamlit as st
import pandas as pd
from datetime import datetime
import groq

# --- 1. Configuração da Página ---
st.set_page_config(
    page_title="Finanças com IA",
    page_icon="🤖💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS Customizado ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .st-emotion-cache-16txtl3 { padding: 20px; background-color: #1a1a1a; border-radius: 10px; }
    [data-testid="metric-container"] { background-color: #222; border: 1px solid #333; padding: 15px; border-radius: 10px; color: white; }
    h2 { font-size: 1.5rem; color: #FAFAFA; border-bottom: 2px solid #333; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)


# --- 2. Funções de Dados e IA ---

# AQUI ESTÁ A CORREÇÃO!
def carregar_dados():
    try:
        df = pd.read_csv('transacoes.csv')
        
        # --- LÓGICA DE MIGRAÇÃO ---
        # Verifica se o arquivo é da versão antiga (com a coluna 'Data')
        if 'Data' in df.columns and 'Data/Hora' not in df.columns:
            # Renomeia a coluna 'Data' para 'Data/Hora'
            df.rename(columns={'Data': 'Data/Hora'}, inplace=True)
            # Converte a coluna para datetime, tratando possíveis erros de formato
            df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
            # Salva o arquivo já no formato novo para não precisar fazer isso de novo
            salvar_dados(df)

        # Garante que a coluna 'Data/Hora' sempre seja do tipo datetime
        df['Data/Hora'] = pd.to_datetime(df['Data/Hora'])
        return df
        
    except FileNotFoundError:
        # Se o arquivo não existe, cria um novo já com a coluna correta
        return pd.DataFrame(columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria'])

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
        print(f"Erro na API Groq: {e}")
        return None

# --- 3. Inicialização ---
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_dados()
if 'categoria_sugerida' not in st.session_state:
    st.session_state.categoria_sugerida = ""

# --- 4. Interface Principal ---
st.title("🤖 Finanças com IA")
tab_lancamento, tab_analise = st.tabs(["✍️ Lançar", "📊 Histórico & Análise"])

with tab_lancamento:
    st.header("Adicionar Nova Transação")
    with st.form("nova_transacao_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            descricao = st.text_input("Descrição", placeholder="Ex: Almoço")
            tipo = st.selectbox("Tipo", ["Despesa", "Receita"], label_visibility="collapsed")
        with col2:
            valor = st.number_input("Valor", min_value=0.01, format="%.2f")
            
        if st.form_submit_button("Sugerir Categoria com IA ✨"):
            with st.spinner("A IA está pensando... 🤔"):
                sugestao = categorizar_com_ia(descricao)
                if sugestao: st.session_state.categoria_sugerida = sugestao

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
                data_hora_atual = datetime.now()
                nova_transacao = pd.DataFrame([[data_hora_atual, descricao, valor, tipo, categoria_selecionada]], columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria'])
                st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
                salvar_dados(st.session_state.transacoes)
                st.success("Transação adicionada!")
                st.session_state.categoria_sugerida = ""
                st.rerun()

with tab_analise:
    st.header("Resumo Financeiro")
    total_receitas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Receita']['Valor'].sum()
    total_despesas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']['Valor'].sum()
    saldo = total_receitas - total_despesas

    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R${total_receitas:,.2f}")
    col2.metric("Despesas", f"R${total_despesas:,.2f}")
    col3.metric("Saldo", f"R${saldo:,.2f}")
    st.divider()

    despesas_df = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']
    if not despesas_df.empty:
        st.header("Despesas por Categoria")
        despesas_por_categoria = despesas_df.groupby('Categoria')['Valor'].sum()
        st.bar_chart(despesas_por_categoria, use_container_width=True)
        st.divider()

    st.header("Todas as Transações")
    df_para_mostrar = st.session_state.transacoes.sort_values(by="Data/Hora", ascending=False)
    
    st.data_editor(
        df_para_mostrar.reset_index(drop=True), # Usar reset_index para mostrar índices limpos
        use_container_width=True,
        column_config={
            "Data/Hora": st.column_config.DatetimeColumn("Data e Hora", format="DD/MM/YYYY - HH:mm"),
            "Valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
        },
        disabled=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria']
    )
    st.divider()

    st.header("Apagar Lançamento")
    if not st.session_state.transacoes.empty:
        indices_disponiveis = st.session_state.transacoes.index.tolist()
        indice_para_apagar = st.selectbox("Selecione o ID do lançamento a ser apagado:", indices_disponiveis)

        if st.button("🗑️ Apagar Lançamento Selecionado"):
            if indice_para_apagar in indices_disponiveis:
                st.session_state.transacoes.drop(indice_para_apagar, inplace=True)
                st.session_state.transacoes.reset_index(drop=True, inplace=True)
                salvar_dados(st.session_state.transacoes)
                st.success(f"Lançamento com ID {indice_para_apagar} apagado!")
                st.rerun()
            else:
                st.error("ID inválido ou já apagado.")
    else:
        st.info("Nenhum lançamento para apagar.")
