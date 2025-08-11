import streamlit as st
import pandas as pd
from datetime import datetime
import groq
import plotly.express as px
import json

# --- 1. Configuração da Página ---
st.set_page_config(page_title="Finanças com IA", page_icon="🤖💰", layout="centered", initial_sidebar_state="collapsed")

# --- CSS Customizado ---
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .st-emotion-cache-16txtl3 { padding: 20px; background-color: #1a1a1a; border-radius: 10px; }
    [data-testid="metric-container"] { background-color: #222; border: 1px solid #333; padding: 15px; border-radius: 10px; color: white; }
    h2 { font-size: 1.5rem; color: #FAFAFA; border-bottom: 2px solid #333; padding-bottom: 5px; }
    [data-testid="stChatMessage"] { background-color: #333; border-radius: 10px; padding: 1rem; }
</style>
""", unsafe_allow_html=True)


# --- 2. Funções de Dados e IA ---

def carregar_dados():
    try:
        df = pd.read_csv('transacoes.csv')
        if 'Data' in df.columns and 'Data/Hora' not in df.columns:
            df.rename(columns={'Data': 'Data/Hora'}, inplace=True)
        if 'Subcategoria' not in df.columns:
            df['Subcategoria'] = 'N/A'
        if 'Descrição da IA' not in df.columns:
            df['Descrição da IA'] = 'N/A'
        df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        salvar_dados(df)
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria', 'Descrição da IA'])

def salvar_dados(df):
    df.to_csv('transacoes.csv', index=False)

def categorizar_com_ia(descricao):
    if not descricao: return "Outros", "N/A"
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": """Você é um assistente financeiro especialista. Responda APENAS com um objeto JSON no formato: {"categoria": "...", "subcategoria": "..."}. Categorias permitidas: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Compras, Salário, Investimentos, Outros. Exemplos: "Óculos de sol" -> {"categoria": "Compras", "subcategoria": "Acessórios"}; "Consulta médica" -> {"categoria": "Saúde", "subcategoria": "Médico"}."""},
                {"role": "user", "content": f"Classifique a despesa: '{descricao}'"}
            ], model="llama3-70b-8192", temperature=0.0, response_format={"type": "json_object"}
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
            {"role": "system", "content": f"Você é FinBot, um assistente financeiro educativo. Use o resumo financeiro ({resumo_financeiro}) para dar noções gerais sobre investimentos. Sempre inclua um aviso para procurar um profissional e NUNCA se apresente como um conselheiro licenciado."}
        ]
        mensagens_para_api.extend(historico_conversa)
        chat_completion = client.chat.completions.create(
            messages=mensagens_para_api, model="llama3-70b-8192", temperature=0.7
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"Erro na API Groq (chatbot): {e}")
        return "Desculpe, estou com um problema para me conectar. Tente novamente."

# --- 3. Inicialização ---
if 'transacoes' not in st.session_state: st.session_state.transacoes = carregar_dados()
if 'sugestoes' not in st.session_state: st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o FinBot. Como posso ajudar com suas dúvidas sobre investimentos?"}]

# --- 4. Interface Principal ---
st.title("🤖 Finanças com IA")
tab_lancamento, tab_historico, tab_ia = st.tabs(["✍️ Lançar", "📊 Histórico", "🤖 Análise com IA"])

with tab_lancamento:
    st.header("Adicionar Nova Transação")
    with st.form("nova_transacao_form"):
        descricao = st.text_input("Descrição", placeholder="Ex: Óculos de sol novos")
        col1, col2 = st.columns(2)
        with col1: valor = st.number_input("Valor", min_value=0.01, format="%.2f")
        with col2: tipo = st.selectbox("Tipo", ["Despesa", "Receita"])

        if st.form_submit_button("Sugerir Classificação com IA ✨"):
            with st.spinner("A IA está analisando... 🤔"):
                cat, subcat = categorizar_com_ia(descricao)
                st.session_state.sugestoes = {"categoria": cat, "subcategoria": subcat}
        
        st.info(f"Sugestão da IA: Categoria '{st.session_state.sugestoes.get('categoria', 'N/A')}', Subcategoria '{st.session_state.sugestoes.get('subcategoria', 'N/A')}'")

        categorias_disponiveis = ["Alimentação", "Moradia", "Transporte", "Lazer", "Saúde", "Educação", "Compras", "Salário", "Investimentos", "Outros"]
        try: index_cat = categorias_disponiveis.index(st.session_state.sugestoes['categoria'])
        except (ValueError, KeyError): index_cat = 0
        
        col_cat, col_sub = st.columns(2)
        with col_cat: categoria_final = st.selectbox("Sua Categoria:", categorias_disponiveis, index=index_cat)
        with col_sub: subcategoria_final = st.text_input("Sua Subcategoria:", value=st.session_state.sugestoes.get('subcategoria', ''))

        if st.form_submit_button("✅ Salvar Transação"):
            if not descricao or valor <= 0: st.warning("Por favor, preencha a descrição e o valor.")
            else:
                data_hora_atual = datetime.now()
                sugestao_ia_texto = f"{st.session_state.sugestoes.get('categoria', 'N/A')} -> {st.session_state.sugestoes.get('subcategoria', 'N/A')}"
                nova_transacao = pd.DataFrame([[data_hora_atual, descricao, valor, tipo, categoria_final, subcategoria_final, sugestao_ia_texto]], columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria', 'Descrição da IA'])
                st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_transacao], ignore_index=True)
                salvar_dados(st.session_state.transacoes)
                st.success("Transação salva com sucesso!")
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
    st.data_editor(st.session_state.transacoes.sort_values(by="Data/Hora", ascending=False), column_order=["Data/Hora", "Descrição", "Valor", "Categoria", "Subcategoria", "Descrição da IA", "Tipo"], use_container_width=True, hide_index=True, disabled=True, column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f"), "Descrição da IA": st.column_config.Column("O que a IA sugeriu", width="medium")})
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
        fig = px.sunburst(despesas_df.dropna(subset=['Subcategoria']), path=['Categoria', 'Subcategoria'], values='Valor', title='Distribuição de Gastos', color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(margin=dict(t=50, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else: st.info("Adicione algumas despesas para ver a análise de gastos.")
    st.divider()

    st.header("FinBot: Seu Assistente de Investimentos")
    
    with st.container(border=True):
        for message in st.session_state.messages:
            # AQUI ESTÁ A CORREÇÃO: Removi o argumento 'avatar' que estava causando o erro de sintaxe.
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
