import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import groq
import plotly.express as px
import json
import numpy as np

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS ---
st.set_page_config(page_title="Finanças com IA", page_icon="🤖💰", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    h2 { font-size: 1.5rem; color: #FAFAFA; border-bottom: 2px solid #333; padding-bottom: 5px; }
    [data-testid="stChatMessage"] p { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)

# --- 2. FUNÇÕES DE DADOS E IA ---
def carregar_dados_csv(caminho_arquivo, colunas):
    try: return pd.read_csv(caminho_arquivo)
    except (FileNotFoundError, pd.errors.EmptyDataError): return pd.DataFrame(columns=colunas)
def salvar_dados_csv(df, caminho_arquivo): df.to_csv(caminho_arquivo, index=False)
def carregar_dados_json(caminho_arquivo, chave_padrão, valor_padrão):
    try: return json.load(open(caminho_arquivo, 'r')).get(chave_padrão, valor_padrão)
    except (FileNotFoundError, json.JSONDecodeError): return valor_padrão
def salvar_dados_json(dados, caminho_arquivo):
    with open(caminho_arquivo, 'w') as f: json.dump(dados, f)

def categorizar_com_ia(descricao):
    if not descricao: return "Outros", "N/A"
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": 'Você é um assistente financeiro especialista. Responda APENAS com um objeto JSON no formato: {"categoria": "...", "subcategoria": "..."}. Categorias permitidas: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Compras, Salário, Investimentos, Outros. Exemplos: "Óculos de sol" -> {"categoria": "Compras", "subcategoria": "Acessórios"}; "Consulta médica" -> {"categoria": "Saúde", "subcategoria": "Médico"}.'}, {"role": "user", "content": f"Classifique a despesa: '{descricao}'"}], model="llama3-70b-8192", temperature=0.0, response_format={"type": "json_object"})
        response_json = json.loads(chat_completion.choices[0].message.content)
        return response_json.get("categoria", "Outros"), response_json.get("subcategoria", "N/A")
    except Exception as e:
        st.error(f"Erro ao categorizar: {e}")
        return "Outros", "N/A"

def chamar_chatbot_ia(historico_conversa, resumo_financeiro):
    # AQUI ESTAVA O ERRO DE SINTAXE. CORRIGIDO PARA SER MAIS SEGURO.
    prompt_sistema = (
        "Você é FinBot, um assistente financeiro educativo. Use o seguinte resumo financeiro do usuário para personalizar suas respostas: "
        f"{resumo_financeiro}. "
        "Dê noções gerais sobre investimentos. Sempre inclua um aviso para procurar um profissional e NUNCA se apresente como um conselheiro licenciado."
    )
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        mensagens_para_api = [{"role": "system", "content": prompt_sistema}]
        mensagens_para_api.extend(historico_conversa)
        chat_completion = client.chat.completions.create(messages=mensagens_para_api, model="llama3-70b-8192", temperature=0.7)
        return chat_completion.choices[0].message.content
    except Exception as e:
        st.error(f"Erro no chatbot: {e}")
        return "Desculpe, estou com um problema para me conectar. Tente novamente."

# --- 3. INICIALIZAÇÃO E LÓGICA DE PERÍODO ---
if 'periodo_selecionado' not in st.session_state: st.session_state.periodo_selecionado = datetime.now()
if 'transacoes' not in st.session_state: st.session_state.transacoes = carregar_dados_csv('transacoes.csv', ['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria', 'Descrição da IA'])
if 'freelas' not in st.session_state: st.session_state.freelas = carregar_dados_csv('freelancer_jobs.csv', ['Descrição', 'Status', 'Modo de Cobrança', 'Valor da Hora', 'Valor Fixo', 'Início', 'Término', 'Valor a Receber'])
if 'reserva_movimentacoes' not in st.session_state: st.session_state.reserva_movimentacoes = carregar_dados_csv('reserva_movimentacoes.csv', ['Data', 'Tipo', 'Valor'])
if 'reserva_meta' not in st.session_state: st.session_state.reserva_meta = carregar_dados_json('reserva_meta.json', 'meta', 1000.0)
if 'sugestoes' not in st.session_state: st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o FinBot. Como posso ajudar?"}]

def exibir_navegador_mes():
    col1, col2, col3 = st.columns([1, 4, 1])
    if col1.button("⬅️", use_container_width=True, help="Mês Anterior"):
        st.session_state.periodo_selecionado -= relativedelta(months=1)
        st.rerun()
    mes_ano_str = st.session_state.periodo_selecionado.strftime("%B de %Y").capitalize()
    col2.subheader(mes_ano_str)
    if col3.button("➡️", use_container_width=True, help="Próximo Mês"):
        st.session_state.periodo_selecionado += relativedelta(months=1)
        st.rerun()

# --- 4. INTERFACE PRINCIPAL ---
st.title("🤖 Finanças & Freelas com IA")
tab_lancamento, tab_historico, tab_freelancer, tab_reserva, tab_ia = st.tabs(["✍️ Lançar", "📊 Histórico", "💻 Freelancer", "🛡️ Reserva", "🤖 Análise IA"])

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
                salvar_dados_csv(st.session_state.transacoes, 'transacoes.csv')
                st.success("Transação salva com sucesso!"); st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}; st.rerun()

# --- Lógica de Filtragem ---
periodo = st.session_state.periodo_selecionado
df_transacoes = st.session_state.transacoes.copy()
df_transacoes['Data/Hora'] = pd.to_datetime(df_transacoes['Data/Hora'], errors='coerce')
df_transacoes['Valor'] = pd.to_numeric(df_transacoes['Valor'], errors='coerce').fillna(0)
transacoes_filtradas = df_transacoes[(df_transacoes['Data/Hora'].dt.year == periodo.year) & (df_transacoes['Data/Hora'].dt.month == periodo.month)]

with tab_historico:
    exibir_navegador_mes()
    st.header("Resumo Financeiro do Mês")
    total_receitas = transacoes_filtradas[transacoes_filtradas['Tipo'] == 'Receita']['Valor'].sum()
    total_despesas = transacoes_filtradas[transacoes_filtradas['Tipo'] == 'Despesa']['Valor'].sum()
    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas", f"R${total_receitas:,.2f}"); col2.metric("Despesas", f"R${total_despesas:,.2f}"); col3.metric("Saldo", f"R${total_receitas - total_despesas:,.2f}")
    st.header("Transações do Mês")
    st.data_editor(transacoes_filtradas.sort_values(by="Data/Hora", ascending=False), hide_index=True, use_container_width=True)

with tab_freelancer:
    exibir_navegador_mes()
    st.header("Gestor de Trabalhos Freelancer")
    df_freelas = st.session_state.freelas.copy()
    df_freelas['Término'] = pd.to_datetime(df_freelas['Término'], errors='coerce')
    freelas_concluidos_filtrados = df_freelas[(df_freelas['Status'] == 'Concluído') & (df_freelas['Término'].dt.year == periodo.year) & (df_freelas['Término'].dt.month == periodo.month)]
    with st.expander("➕ Registrar Novo Trabalho"):
        with st.form("novo_freela_form", clear_on_submit=True):
            freela_descricao = st.text_input("Descrição do Trabalho", placeholder="Ex: Site para Padaria do Bairro")
            modo_cobranca = st.selectbox("Modo de Cobrança", ["Valor por Hora", "Valor Fixo"])
            valor_hora = 0.0; valor_fixo = 0.0
            if modo_cobranca == "Valor por Hora": valor_hora = st.number_input("Seu valor por hora (R$)", min_value=1.0, format="%.2f")
            else: valor_fixo = st.number_input("Valor fixo do projeto (R$)", min_value=1.0, format="%.2f")
            if st.form_submit_button("🚀 Iniciar Trabalho"):
                novo_freela = {'Descrição': freela_descricao, 'Status': 'Em Andamento', 'Modo de Cobrança': modo_cobranca, 'Valor da Hora': valor_hora, 'Valor Fixo': valor_fixo, 'Início': datetime.now(), 'Término': pd.NaT, 'Valor a Receber': 0.0}
                st.session_state.freelas = pd.concat([st.session_state.freelas, pd.DataFrame([novo_freela])], ignore_index=True)
                salvar_dados_csv(st.session_state.freelas, 'freelancer_jobs.csv')
                st.success(f"Trabalho '{freela_descricao}' iniciado!"); st.rerun()
    st.divider()
    st.subheader("Em Andamento")
    trabalhos_andamento = st.session_state.freelas[st.session_state.freelas['Status'] == 'Em Andamento'].copy()
    if trabalhos_andamento.empty: st.info("Nenhum trabalho em andamento.")
    else:
        trabalhos_andamento['Início'] = pd.to_datetime(trabalhos_andamento['Início'], errors='coerce')
        for idx, job in trabalhos_andamento.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{job['Descrição']}**")
                    if pd.notna(job['Início']): st.write(f"Iniciado em: {job['Início'].strftime('%d/%m/%Y às %H:%M')}")
                    if job['Modo de Cobrança'] == 'Valor por Hora': st.write(f"Cobrança: R$ {job['Valor da Hora']:.2f}/hora")
                    else: st.write(f"Cobrança: R$ {job['Valor Fixo']:.2f} (valor fixo)")
                with col2:
                    if st.button("🏁 Finalizar", key=f"finalizar_{idx}"):
                        termino = datetime.now(); valor_final = 0.0
                        if job['Modo de Cobrança'] == 'Valor por Hora':
                            duracao = termino - pd.to_datetime(job['Início']); horas = duracao.total_seconds() / 3600
                            valor_final = horas * job['Valor da Hora']
                        else: valor_final = job['Valor Fixo']
                        st.session_state.freelas.at[idx, 'Status'] = 'Concluído'; st.session_state.freelas.at[idx, 'Término'] = termino
                        st.session_state.freelas.at[idx, 'Valor a Receber'] = valor_final
                        salvar_dados_csv(st.session_state.freelas, 'freelancer_jobs.csv')
                        st.success("Trabalho finalizado!"); st.rerun()
    st.divider()
    st.subheader("Histórico de Trabalhos Concluídos no Mês")
    st.data_editor(freelas_concluidos_filtrados, use_container_width=True, hide_index=True)

with tab_reserva:
    st.header("🛡️ Reserva de Emergência")
    movimentacoes = st.session_state.reserva_movimentacoes.copy()
    movimentacoes['Valor'] = pd.to_numeric(movimentacoes['Valor'], errors='coerce').fillna(0)
    valor_atual = movimentacoes[movimentacoes['Tipo'] == 'Aporte']['Valor'].sum() - movimentacoes[movimentacoes['Tipo'] == 'Retirada']['Valor'].sum()
    meta_reserva = st.session_state.reserva_meta
    percentual_completo = (valor_atual / meta_reserva) if meta_reserva > 0 else 0.0
    st.progress(percentual_completo, text=f"{percentual_completo:.1%} Completo")
    col1, col2, col3 = st.columns(3)
    col1.metric("Meta", f"R$ {meta_reserva:,.2f}"); col2.metric("Valor Atual", f"R$ {valor_atual:,.2f}"); col3.metric("Faltam", f"R$ {max(0, meta_reserva - valor_atual):,.2f}")
    with 
