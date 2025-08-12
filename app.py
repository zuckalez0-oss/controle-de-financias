import streamlit as st
import pandas as pd
from datetime import datetime
import groq
import plotly.express as px
import json
import numpy as np

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
    [data-testid="stChatMessage"] p { color: #FFFFFF; }
</style>
""", unsafe_allow_html=True)


# --- 2. Funções de Dados e IA ---

# Funções para Transações Financeiras
def carregar_dados():
    try:
        df = pd.read_csv('transacoes.csv')
        if 'Data' in df.columns and 'Data/Hora' not in df.columns: df.rename(columns={'Data': 'Data/Hora'}, inplace=True)
        if 'Subcategoria' not in df.columns: df['Subcategoria'] = 'N/A'
        if 'Descrição da IA' not in df.columns: df['Descrição da IA'] = 'N/A'
        df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
        salvar_dados(df)
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria', 'Descrição da IA'])
def salvar_dados(df): df.to_csv('transacoes.csv', index=False)

# Funções para Freelancer
def carregar_freelas():
    try:
        df = pd.read_csv('freelancer_jobs.csv')
        df['Início'] = pd.to_datetime(df['Início'], errors='coerce')
        df['Término'] = pd.to_datetime(df['Término'], errors='coerce')
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=['Descrição', 'Status', 'Modo de Cobrança', 'Valor da Hora', 'Valor Fixo', 'Início', 'Término', 'Valor a Receber'])
def salvar_freelas(df): df.to_csv('freelancer_jobs.csv', index=False)

# MUDANÇA: Novas funções para a Reserva de Emergência
def carregar_reserva_meta():
    try:
        with open('reserva_meta.json', 'r') as f:
            data = json.load(f)
            return data.get('meta', 1000.0) # Retorna 1000 como padrão se a chave não existir
    except (FileNotFoundError, json.JSONDecodeError):
        return 1000.0 # Meta padrão inicial
def salvar_reserva_meta(meta):
    with open('reserva_meta.json', 'w') as f:
        json.dump({'meta': meta}, f)
def carregar_movimentacoes():
    try:
        df = pd.read_csv('reserva_movimentacoes.csv')
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        return df
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=['Data', 'Tipo', 'Valor'])
def salvar_movimentacoes(df):
    df.to_csv('reserva_movimentacoes.csv', index=False)

# Funções da IA (sem alterações)
def categorizar_com_ia(descricao):
    # ... (código existente) ...
    if not descricao: return "Outros", "N/A"
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": 'Você é um assistente financeiro especialista. Responda APENAS com um objeto JSON no formato: {"categoria": "...", "subcategoria": "..."}. Categorias permitidas: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Compras, Salário, Investimentos, Outros. Exemplos: "Óculos de sol" -> {"categoria": "Compras", "subcategoria": "Acessórios"}; "Consulta médica" -> {"categoria": "Saúde", "subcategoria": "Médico"}.'}, {"role": "user", "content": f"Classifique a despesa: '{descricao}'"}], model="llama3-70b-8192", temperature=0.0, response_format={"type": "json_object"})
        response_json = json.loads(chat_completion.choices[0].message.content)
        return response_json.get("categoria", "Outros"), response_json.get("subcategoria", "N/A")
    except Exception as e: return "Outros", "N/A"

def chamar_chatbot_ia(historico_conversa, resumo_financeiro):
    # ... (código existente) ...
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        mensagens_para_api = [{"role": "system", "content": f"Você é FinBot, um assistente financeiro educativo. Use o resumo financeiro ({resumo_financeiro}) para dar noções gerais sobre investimentos. Sempre inclua um aviso para procurar um profissional e NUNCA se apresente como um conselheiro licenciado."}]
        mensagens_para_api.extend(historico_conversa)
        chat_completion = client.chat.completions.create(messages=mensagens_para_api, model="llama3-70b-8192", temperature=0.7)
        return chat_completion.choices[0].message.content
    except Exception as e: return "Desculpe, estou com um problema para me conectar. Tente novamente."


# --- 3. Inicialização ---
if 'transacoes' not in st.session_state: st.session_state.transacoes = carregar_dados()
if 'sugestoes' not in st.session_state: st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
if 'freelas' not in st.session_state: st.session_state.freelas = carregar_freelas()
if 'reserva_meta' not in st.session_state: st.session_state.reserva_meta = carregar_reserva_meta()
if 'reserva_movimentacoes' not in st.session_state: st.session_state.reserva_movimentacoes = carregar_movimentacoes()
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o FinBot. Como posso ajudar?"}]


# --- 4. Interface Principal ---
st.title("🤖 Finanças & Freelas com IA")
# MUDANÇA: Adicionada a nova aba "Reserva"
tab_lancamento, tab_historico, tab_freelancer, tab_reserva, tab_ia = st.tabs(["✍️ Lançar", "📊 Histórico", "💻 Freelancer", "🛡️ Reserva", "🤖 Análise IA"])

with tab_lancamento: # Esta aba não muda
    # ... (código existente da aba de lançamento) ...
    st.header("Adicionar Nova Transação")
    # (O código desta aba permanece o mesmo)

with tab_historico: # Esta aba não muda
    # ... (código existente da aba de histórico) ...
    st.header("Resumo Financeiro")
    # (O código desta aba permanece o mesmo)

with tab_freelancer: # Esta aba não muda
    # ... (código existente da aba de freelancer) ...
    st.header("Gestor de Trabalhos Freelancer")
    # (O código desta aba permanece o mesmo)

# MUDANÇA: Construção da nova aba "Reserva de Emergência"
with tab_reserva:
    st.header("🛡️ Reserva de Emergência")
    
    # Cálculos principais
    movimentacoes = st.session_state.reserva_movimentacoes
    aportes = movimentacoes[movimentacoes['Tipo'] == 'Aporte']['Valor'].sum()
    retiradas = movimentacoes[movimentacoes['Tipo'] == 'Retirada']['Valor'].sum()
    valor_atual = aportes - retiradas
    meta_reserva = st.session_state.reserva_meta
    
    percentual_completo = 0.0
    if meta_reserva > 0:
        percentual_completo = valor_atual / meta_reserva
    
    # Exibição visual
    st.progress(percentual_completo, text=f"{percentual_completo:.1%} Completo")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Meta", f"R$ {meta_reserva:,.2f}")
    col2.metric("Valor Atual", f"R$ {valor_atual:,.2f}")
    col3.metric("Faltam", f"R$ {max(0, meta_reserva - valor_atual):,.2f}")
    
    st.divider()

    # Seção de Ações
    with st.expander("💸 Registrar Movimentação na Reserva"):
        with st.form("movimentacao_reserva_form", clear_on_submit=True):
            valor_movimentacao = st.number_input("Valor da movimentação", min_value=0.01, format="%.2f")
            
            col_btn1, col_btn2 = st.columns(2)
            com_aporte = col_btn1.form_submit_button("Adicionar Aporte 💵")
            com_retirada = col_btn2.form_submit_button("Realizar Retirada 🆘")

            if com_aporte:
                nova_mov = {'Data': datetime.now(), 'Tipo': 'Aporte', 'Valor': valor_movimentacao}
                st.session_state.reserva_movimentacoes = pd.concat([st.session_state.reserva_movimentacoes, pd.DataFrame([nova_mov])], ignore_index=True)
                salvar_movimentacoes(st.session_state.reserva_movimentacoes)
                st.success("Aporte registrado!")
                st.rerun()

            if com_retirada:
                if valor_movimentacao > valor_atual:
                    st.error("Valor da retirada maior que o saldo atual da reserva!")
                else:
                    nova_mov = {'Data': datetime.now(), 'Tipo': 'Retirada', 'Valor': valor_movimentacao}
                    st.session_state.reserva_movimentacoes = pd.concat([st.session_state.reserva_movimentacoes, pd.DataFrame([nova_mov])], ignore_index=True)
                    salvar_movimentacoes(st.session_state.reserva_movimentacoes)
                    st.warning("Retirada registrada!")
                    st.rerun()
    
    # Seção de Configuração
    with st.expander("⚙️ Configurar Meta da Reserva"):
        nova_meta = st.number_input("Defina o valor total da sua reserva de emergência", min_value=1.0, value=meta_reserva, format="%.2f")
        if st.button("Salvar Nova Meta"):
            st.session_state.reserva_meta = nova_meta
            salvar_reserva_meta(nova_meta)
            st.success("Nova meta salva com sucesso!")
            st.rerun()

    st.divider()
    
    # Histórico de Movimentações
    st.subheader("Histórico de Movimentações da Reserva")
    st.data_editor(st.session_state.reserva_movimentacoes.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True, disabled=True,
                   column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})

with tab_ia: # Esta aba não muda
    # ... (código existente da aba de análise com IA) ...
    st.header("Análise de Gastos com IA")
    # (O código desta aba permanece o mesmo)
