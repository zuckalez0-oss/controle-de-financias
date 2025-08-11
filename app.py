import streamlit as st
import pandas as pd
from datetime import datetime
import groq
import plotly.express as px
import json

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
    [data-testid="stChatMessage"] { background-color: #333; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


# --- 2. Funções de Dados e IA ---

# AQUI ESTÁ A VERSÃO CORRIGIDA E ROBUSTA DA FUNÇÃO
def carregar_dados():
    try:
        # Passo 1: Ler o CSV da forma mais simples possível, sem parse_dates.
        df = pd.read_csv('transacoes.csv')
        
        # Passo 2: Lógica de migração para 'Data/Hora'
        if 'Data' in df.columns and 'Data/Hora' not in df.columns:
            df.rename(columns={'Data': 'Data/Hora'}, inplace=True)
        
        # Passo 3: Lógica de migração para 'Subcategoria'
        if 'Subcategoria' not in df.columns:
            df['Subcategoria'] = 'N/A'
        
        # Passo 4: Agora que garantimos que a coluna existe, convertemos para datetime.
        # 'errors='coerce'' transforma qualquer data inválida em 'NaT' (Not a Time)
        df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        
        # Salva o dataframe já corrigido para não precisar migrar novamente.
        salvar_dados(df)
        return df

    except FileNotFoundError:
        # Se o arquivo não existe, cria um novo com a estrutura correta.
        return pd.DataFrame(columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria'])
    except pd.errors.EmptyDataError:
        # Se o arquivo existe mas está vazio, também retorna um dataframe vazio.
        return pd.DataFrame(columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria'])

def salvar_dados(df):
    df.to_csv('transacoes.csv', index=False)

def categorizar_com_ia(descricao):
    if not descricao: return None, None
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """Você é um assistente financeiro especialista. Sua tarefa é analisar a descrição de uma despesa e classificá-la.
                    Responda APENAS com um objeto JSON válido no seguinte formato: {"categoria": "...", "subcategoria": "..."}.
                    Categorias principais permitidas: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Compras, Salário, Investimentos, Outros.
                    A subcategoria deve ser um detalhe específico da despesa. Ex: para 'Almoço com amigos', use {"categoria": "Alimentação", "subcategoria": "Restaurante"}."""
                },
                {"role": "user", "content": f"Classifique a seguinte despesa: '{descricao}'"}
            ],
            model="llama3-70b-8192",
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        response_json = json.loads(chat_completion.choices[0].message.content)
        return response_json.get("categoria", "Outros"), response_json.get("subcategoria", "N/A")
    except Exception as e:
        print(f"Erro na API Groq (categorização): {e}")
        return "Outros", "N/A"

def chamar_chatbot_ia(historico_conversa, resumo_financeiro):
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        mensagens_para_api = [
            {
                "role": "system",
                "content": f"""Você é um assistente financeiro prestativo e educativo. Seu nome é FinBot.
                Seu objetivo é dar ao usuário noções gerais sobre investimentos, com base na sua receita.
                NUNCA se apresente como um conselheiro financeiro licenciado. Sempre inclua um aviso de que suas sugestões são educacionais e que o usuário deve procurar um profissional.
                Use o seguinte resumo financeiro do usuário para personalizar suas respostas: {resumo_financeiro}.
                Seja amigável, didático e seguro. Baseie as sugestões na receita mensal informada."""
            }
        ]
        mensagens_para_api.extend(historico_conversa)

        chat_completion = client.chat.completions.create(messages=mensagens_para_api, model="llama3-70b-8192", temperature=0.7)
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Erro na API Groq (chatbot): {e}")
        return "Desculpe, estou com um problema para me conectar. Tente novamente mais tarde."

# --- O resto do código continua exatamente o mesmo ---
# --- (Copiando abaixo para garantir que você tenha tudo) ---

# --- 3. Inicialização ---
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_dados()
if 'sugestoes' not in st.session_state:
    st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o FinBot. Com base na sua receita, posso te dar algumas ideias educacionais de investimento. Como posso ajudar?"}]

# --- 4. Interface Principal ---
st.title("🤖 Finanças com IA")
tab_lancamento, tab_historico, tab_ia = st.tabs(["✍️ Lançar", "📊 Histórico", "🤖 Análise com IA"])

with tab_lancamento:
    st.header("Adicionar Nova Transação")
    with st.form("nova_transacao_form"):
        descricao = st.text_input("Descrição", placeholder="Ex: Almoço com amigos no shopping")
        col1, col2 = st.columns(2)
        with col1: valor = st.number_input("Valor", min_value=0.01, format="%.2f")
        with col2: tipo = st.selectbox("Tipo", ["Despesa", "Receita"])

        if st.form_submit_button("Sugerir Classificação com IA ✨"):
            with st.spinner("A IA está analisando e classificando... 🤔"):
                cat, subcat = categorizar_com_ia(descricao)
                st.session_state.sugestoes = {"categoria": cat, "subcategoria": subcat}

        st.write(f"Sugestão da IA: **{st.session_state.sugestoes.get('categoria', '')}** -> **{st.session_state.sugestoes.get('subcategoria', '')}**")
        
        if st.form_submit_button("✅ Adicionar Transação"):
            if not descricao or valor <= 0: st.warning("Por favor, preencha a descrição e o valor.")
            else:
                data_hora_atual = datetime.now()
                categoria_final = st.session_state.sugestoes.get('categoria', 'Outros')
                subcategoria_final = st.session_state.sugestoes.get('subcategoria', 'N/A')
                
                nova_transacao = pd.DataFrame([[data_hora_atual, descricao, valor, tipo, categoria_final, subcategoria_final]], columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria'])
                st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
                salvar_dados(st.session_state.transacoes)
                st.success("Transação adicionada!")
                st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
                st.rerun()

with tab_historico:
    st.header("Resumo Financeiro")
    total_receitas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Receita']['Valor'].sum()
    total_despesas = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']['Valor'].sum()
    saldo = total_receitas - total_despesas
    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R${total_receitas:,.2f}")
    col2.metric("Despesas", f"R${total_despesas:,.2f}")
    col3.metric("Saldo", f"R${saldo:,.2f}")
    st.divider()

    st.header("Todas as Transações")
    st.data_editor(st.session_state.transacoes.sort_values(by="Data/Hora", ascending=False), use_container_width=True, hide_index=True, disabled=True,
                   column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})
    st.divider()

    st.header("Apagar Lançamento")
    if not st.session_state.transacoes.empty:
        indices_disponiveis = st.session_state.transacoes.index.tolist()
        indice_para_apagar = st.selectbox("Selecione o ID do lançamento a ser apagado:", indices_disponiveis)
        if st.button("🗑️ Apagar Lançamento Selecionado"):
             st.session_state.transacoes.drop(indice_para_apagar, inplace=True)
             st.session_state.transacoes.reset_index(drop=True, inplace=True)
             salvar_dados(st.session_state.transacoes)
             st.success(f"Lançamento ID {indice_para_apagar} apagado!")
             st.rerun()

with tab_ia:
    st.header("Análise de Gastos com IA")
    despesas_df = st.session_state.transacoes[st.session_state.transacoes['Tipo'] == 'Despesa']
    if not despesas_df.empty and 'Subcategoria' in despesas_df.columns:
        fig = px.sunburst(
            despesas_df.dropna(subset=['Subcategoria']), 
            path=['Categoria', 'Subcategoria'], 
            values='Valor',
            title='Distribuição de Gastos por Categoria e Subcategoria',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(margin=dict(t=50, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Adicione algumas despesas para ver a análise de gastos.")
    st.divider()

    st.header("FinBot: Seu Assistente de Investimentos")
    st.warning("⚠️ **Atenção:** Eu sou um chatbot educacional. As sugestões aqui NÃO são aconselhamento financeiro. Consulte sempre um profissional qualificado.", icon="🤖")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pergunte sobre investimentos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("FinBot está pensando..."):
                resumo_financeiro_atual = f"Receita mensal total do usuário: R${total_receitas:,.2f}"
                resposta = chamar_chatbot_ia(st.session_state.messages, resumo_financeiro_atual)
                st.markdown(resposta)
        st.session_state.messages.append({"role": "assistant", "content": resposta})
