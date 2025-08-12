import streamlit as st
import pandas as pd
from datetime import datetime
import groq
import plotly.express as px
import json
import numpy as np

# --- 1. CONFIGURAÇÃO DA PÁGINA E ESTILOS ---
st.set_page_config(page_title="Finanças com IA", page_icon="🤖💰", layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .st-emotion-cache-16txtl3 { padding: 20px; background-color: #1a1a1a; border-radius: 10px; }
    [data-testid="metric-container"] { background-color: #222; border: 1px solid #333; padding: 15px; border-radius: 10px; color: white; }
    h2 { font-size: 1.5rem; color: #FAFAFA; border-bottom: 2px solid #333; padding-bottom: 5px; }
    [data-testid="stChatMessage"] { background-color: #333; border-radius: 10px; padding: 1rem; color: #FFFFFF !important; }
    [data-testid="stChatMessage"] p { color: #FFFFFF !important; }
</style>
""", unsafe_allow_html=True)


# --- 2. FUNÇÕES DE DADOS E IA (sem alterações) ---
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
    # ... (código existente)
    if not descricao: return "Outros", "N/A"
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": 'Você é um assistente financeiro especialista. Responda APENAS com um objeto JSON no formato: {"categoria": "...", "subcategoria": "..."}. Categorias permitidas: Alimentação, Moradia, Transporte, Lazer, Saúde, Educação, Compras, Salário, Investimentos, Outros. Exemplos: "Óculos de sol" -> {"categoria": "Compras", "subcategoria": "Acessórios"}; "Consulta médica" -> {"categoria": "Saúde", "subcategoria": "Médico"}.'}, {"role": "user", "content": f"Classifique a despesa: '{descricao}'"}], model="llama3-70b-8192", temperature=0.0, response_format={"type": "json_object"})
        response_json = json.loads(chat_completion.choices[0].message.content)
        return response_json.get("categoria", "Outros"), response_json.get("subcategoria", "N/A")
    except Exception as e: return "Outros", "N/A"

def chamar_chatbot_ia(historico_conversa, resumo_financeiro):
    # ... (código existente)
    try:
        client = groq.Client(api_key=st.secrets["GROQ_API_KEY"])
        mensagens_para_api = [{"role": "system", "content": f"Você é FinBot, um assistente financeiro educativo. Use o resumo financeiro ({resumo_financeiro}) para dar noções gerais sobre investimentos. Sempre inclua um aviso para procurar um profissional e NUNCA se apresente como um conselheiro licenciado."}]
        mensagens_para_api.extend(historico_conversa)
        chat_completion = client.chat.completions.create(messages=mensagens_para_api, model="llama3-70b-8192", temperature=0.7)
        return chat_completion.choices[0].message.content
    except Exception as e: return "Desculpe, estou com um problema para me conectar. Tente novamente."


# --- 3. INICIALIZAÇÃO DE ESTADO ---
if 'transacoes' not in st.session_state: st.session_state.transacoes = carregar_dados_csv('transacoes.csv', ['Data/Hora', 'Descrição', 'Valor', 'Tipo', 'Categoria', 'Subcategoria', 'Descrição da IA'])
if 'freelas' not in st.session_state: st.session_state.freelas = carregar_dados_csv('freelancer_jobs.csv', ['Descrição', 'Status', 'Modo de Cobrança', 'Valor da Hora', 'Valor Fixo', 'Início', 'Término', 'Valor a Receber'])
if 'reserva_movimentacoes' not in st.session_state: st.session_state.reserva_movimentacoes = carregar_dados_csv('reserva_movimentacoes.csv', ['Data', 'Tipo', 'Valor'])
if 'reserva_meta' not in st.session_state: st.session_state.reserva_meta = carregar_dados_json('reserva_meta.json', 'meta', 1000.0)
if 'sugestoes' not in st.session_state: st.session_state.sugestoes = {"categoria": "", "subcategoria": ""}
if "messages" not in st.session_state: st.session_state.messages = [{"role": "assistant", "content": "Olá! Sou o FinBot. Como posso ajudar?"}]

# --- 4. INTERFACE PRINCIPAL ---
st.title("🤖 Finanças & Freelas com IA")

# MUDANÇA: Seletor Global de Mês e Ano
st.markdown("### Selecione o Período de Análise")
agora = datetime.now()
meses_nomes = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
# Lógica para pegar todos os anos disponíveis nos dados
anos_disponiveis = set([agora.year])
for df_info in [('transacoes', 'Data/Hora'), ('freelas', 'Início'), ('reserva_movimentacoes', 'Data')]:
    df_name, col_name = df_info
    if not st.session_state[df_name].empty:
        datas_validas = pd.to_datetime(st.session_state[df_name][col_name], errors='coerce').dropna()
        anos_disponiveis.update(datas_validas.dt.year.unique())

col1, col2 = st.columns(2)
ano_selecionado = col1.selectbox("Ano", sorted(list(anos_disponiveis), reverse=True), index=0)
mes_selecionado = col2.selectbox("Mês", meses_nomes, index=agora.month - 1)
mes_selecionado_num = meses_nomes.index(mes_selecionado) + 1

st.info(f"Exibindo dados de: **{mes_selecionado} de {ano_selecionado}**")
st.divider()

# MUDANÇA: Lógica de filtragem dos DataFrames
df_transacoes = st.session_state.transacoes.copy()
df_transacoes['Data/Hora'] = pd.to_datetime(df_transacoes['Data/Hora'], errors='coerce')
transacoes_filtradas = df_transacoes[
    (df_transacoes['Data/Hora'].dt.month == mes_selecionado_num) &
    (df_transacoes['Data/Hora'].dt.year == ano_selecionado)
]

df_freelas = st.session_state.freelas.copy()
df_freelas['Término'] = pd.to_datetime(df_freelas['Término'], errors='coerce')
freelas_concluidos_filtrados = df_freelas[
    (df_freelas['Status'] == 'Concluído') &
    (df_freelas['Término'].dt.month == mes_selecionado_num) &
    (df_freelas['Término'].dt.year == ano_selecionado)
]

df_movimentacoes = st.session_state.reserva_movimentacoes.copy()
df_movimentacoes['Data'] = pd.to_datetime(df_movimentacoes['Data'], errors='coerce')
movimentacoes_filtradas = df_movimentacoes[
    (df_movimentacoes['Data'].dt.month == mes_selecionado_num) &
    (df_movimentacoes['Data'].dt.year == ano_selecionado)
]

# Início das abas
tab_lancamento, tab_historico, tab_freelancer, tab_reserva, tab_ia = st.tabs(["✍️ Lançar", "📊 Histórico", "💻 Freelancer", "🛡️ Reserva", "🤖 Análise IA"])

with tab_lancamento: # Esta aba é para entrada, então não é filtrada
    st.header("Adicionar Nova Transação")
    # ... (código existente da aba de lançamento)
    with st.form("nova_transacao_form"):
        # ... (todo o formulário permanece igual)
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

with tab_historico:
    st.header("Resumo Financeiro do Mês")
    # MUDANÇA: Cálculos usam o DataFrame filtrado
    total_receitas = transacoes_filtradas[transacoes_filtradas['Tipo'] == 'Receita']['Valor'].sum()
    total_despesas = transacoes_filtradas[transacoes_filtradas['Tipo'] == 'Despesa']['Valor'].sum()
    saldo = total_receitas - total_despesas
    col1, col2, col3 = st.columns(3)
    col1.metric("Receitas do Mês", f"R${total_receitas:,.2f}")
    col2.metric("Despesas do Mês", f"R${total_despesas:,.2f}")
    col3.metric("Saldo do Mês", f"R${saldo:,.2f}")
    st.divider()
    st.header("Transações do Mês")
    # MUDANÇA: Tabela usa o DataFrame filtrado
    st.data_editor(transacoes_filtradas.sort_values(by="Data/Hora", ascending=False), column_order=["Data/Hora", "Descrição", "Valor", "Categoria", "Subcategoria", "Descrição da IA", "Tipo"], use_container_width=True, hide_index=True, disabled=True, column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f"), "Descrição da IA": st.column_config.Column("O que a IA sugeriu", width="medium")})
    st.divider()
    st.header("Apagar Lançamento (Geral)")
    # MUDANÇA: A exclusão opera no DataFrame principal (não filtrado)
    if not st.session_state.transacoes.empty:
        # ... (código de apagar permanece o mesmo, operando em st.session_state.transacoes)
        indices_disponiveis = st.session_state.transacoes.index.tolist()
        indice_para_apagar = st.selectbox("Selecione o ID do lançamento a ser apagado (da lista geral):", indices_disponiveis)
        if st.button("🗑️ Apagar Lançamento Selecionado"):
             st.session_state.transacoes.drop(indice_para_apagar, inplace=True)
             st.session_state.transacoes.reset_index(drop=True, inplace=True)
             salvar_dados_csv(st.session_state.transacoes, 'transacoes.csv')
             st.success(f"Lançamento ID {indice_para_apagar} apagado!"); st.rerun()

with tab_freelancer:
    st.header("Gestor de Trabalhos Freelancer")
    # ... (código de registrar e de trabalhos em andamento permanece o mesmo)
    with st.expander("➕ Registrar Novo Trabalho"):
        # ... (código existente)
        with st.form("novo_freela_form", clear_on_submit=True):
            freela_descricao = st.text_input("Descrição do Trabalho", placeholder="Ex: Site para Padaria do Bairro")
            modo_cobranca = st.selectbox("Modo de Cobrança", ["Valor por Hora", "Valor Fixo"])
            valor_hora = 0.0
            valor_fixo = 0.0
            if modo_cobranca == "Valor por Hora": valor_hora = st.number_input("Seu valor por hora (R$)", min_value=1.0, format="%.2f")
            else: valor_fixo = st.number_input("Valor fixo do projeto (R$)", min_value=1.0, format="%.2f")
            if st.form_submit_button("🚀 Iniciar Trabalho"):
                novo_freela = {'Descrição': freela_descricao, 'Status': 'Em Andamento', 'Modo de Cobrança': modo_cobranca, 'Valor da Hora': valor_hora, 'Valor Fixo': valor_fixo, 'Início': datetime.now(), 'Término': pd.NaT, 'Valor a Receber': 0.0}
                st.session_state.freelas = pd.concat([st.session_state.freelas, pd.DataFrame([novo_freela])], ignore_index=True)
                salvar_dados_csv(st.session_state.freelas, 'freelancer_jobs.csv')
                st.success(f"Trabalho '{freela_descricao}' iniciado!"); st.rerun()
    st.divider()
    st.subheader("Em Andamento")
    # ... (código existente)
    trabalhos_andamento = st.session_state.freelas[st.session_state.freelas['Status'] == 'Em Andamento'].copy()
    if trabalhos_andamento.empty: st.info("Nenhum trabalho em andamento. Inicie um novo acima!")
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
                        st.success("Trabalho finalizado e movido para o histórico!"); st.rerun()
    st.divider()
    st.header("Histórico de Trabalhos Concluídos no Mês")
    # MUDANÇA: Tabela usa o DataFrame filtrado de freelas
    st.data_editor(freelas_concluidos_filtrados, use_container_width=True, hide_index=True, disabled=True, column_config={"Valor a Receber": st.column_config.NumberColumn(format="R$ %.2f")})

with tab_reserva:
    st.header("🛡️ Reserva de Emergência")
    # MUDANÇA: Exibe totais E métricas do mês
    movimentacoes_total = st.session_state.reserva_movimentacoes.copy()
    movimentacoes_total['Valor'] = pd.to_numeric(movimentacoes_total['Valor'], errors='coerce').fillna(0)
    aportes_total = movimentacoes_total[movimentacoes_total['Tipo'] == 'Aporte']['Valor'].sum()
    retiradas_total = movimentacoes_total[movimentacoes_total['Tipo'] == 'Retirada']['Valor'].sum()
    valor_atual = aportes_total - retiradas_total
    meta_reserva = st.session_state.reserva_meta
    percentual_completo = (valor_atual / meta_reserva) if meta_reserva > 0 else 0.0
    st.progress(percentual_completo, text=f"{percentual_completo:.1%} Completo")

    col1, col2, col3 = st.columns(3)
    col1.metric("Meta Total", f"R$ {meta_reserva:,.2f}")
    col2.metric("Valor Atual", f"R$ {valor_atual:,.2f}")
    col3.metric("Faltam", f"R$ {max(0, meta_reserva - valor_atual):,.2f}")
    
    # Novas métricas do mês
    aportes_mes = movimentacoes_filtradas[movimentacoes_filtradas['Tipo'] == 'Aporte']['Valor'].sum()
    retiradas_mes = movimentacoes_filtradas[movimentacoes_filtradas['Tipo'] == 'Retirada']['Valor'].sum()
    col1_mes, col2_mes = st.columns(2)
    col1_mes.metric(f"Aportes em {mes_selecionado}", f"R$ {aportes_mes:,.2f}", delta_color="normal")
    col2_mes.metric(f"Retiradas em {mes_selecionado}", f"R$ {retiradas_mes:,.2f}", delta_color="inverse")
    
    st.divider()
    # ... (código de registrar movimentação e configurar meta permanece o mesmo)
    with st.expander("💸 Registrar Movimentação na Reserva"):
        with st.form("movimentacao_reserva_form", clear_on_submit=True):
            valor_movimentacao = st.number_input("Valor da movimentação", min_value=0.01, format="%.2f")
            col_btn1, col_btn2 = st.columns(2)
            if col_btn1.form_submit_button("Adicionar Aporte 💵"):
                nova_mov = {'Data': datetime.now(), 'Tipo': 'Aporte', 'Valor': valor_movimentacao}
                st.session_state.reserva_movimentacoes = pd.concat([st.session_state.reserva_movimentacoes, pd.DataFrame([nova_mov])], ignore_index=True)
                salvar_dados_csv(st.session_state.reserva_movimentacoes, 'reserva_movimentacoes.csv')
                st.success("Aporte registrado!"); st.rerun()
            if col_btn2.form_submit_button("Realizar Retirada 🆘"):
                if valor_movimentacao > valor_atual: st.error("Valor da retirada maior que o saldo atual!")
                else:
                    nova_mov = {'Data': datetime.now(), 'Tipo': 'Retirada', 'Valor': valor_movimentacao}
                    st.session_state.reserva_movimentacoes = pd.concat([st.session_state.reserva_movimentacoes, pd.DataFrame([nova_mov])], ignore_index=True)
                    salvar_dados_csv(st.session_state.reserva_movimentacoes, 'reserva_movimentacoes.csv')
                    st.warning("Retirada registrada!"); st.rerun()
    with st.expander("⚙️ Configurar Meta da Reserva"):
        nova_meta = st.number_input("Defina o valor total da sua reserva de emergência", min_value=1.0, value=meta_reserva, format="%.2f")
        if st.button("Salvar Nova Meta"):
            st.session_state.reserva_meta = nova_meta
            salvar_dados_json({'meta': nova_meta}, 'reserva_meta.json')
            st.success("Nova meta salva com sucesso!"); st.rerun()
    st.divider()
    st.subheader("Histórico Geral de Movimentações da Reserva")
    # A tabela de histórico da reserva mostra TUDO, não é filtrada.
    st.data_editor(st.session_state.reserva_movimentacoes.sort_values(by="Data", ascending=False), use_container_width=True, hide_index=True, disabled=True, column_config={"Valor": st.column_config.NumberColumn(format="R$ %.2f")})

with tab_ia:
    st.header("Análise de Gastos do Mês")
    # MUDANÇA: Gráfico e Chatbot usam o DataFrame filtrado
    despesas_filtradas = transacoes_filtradas[transacoes_filtradas['Tipo'] == 'Despesa']
    if not despesas_filtradas.empty:
        df_para_grafico = despesas_filtradas.copy()
        df_para_grafico['Subcategoria'].replace(['', 'N/A'], np.nan, inplace=True)
        df_para_grafico.dropna(subset=['Categoria', 'Subcategoria'], inplace=True)
        if not df_para_grafico.empty:
            fig = px.sunburst(df_para_grafico, path=['Categoria', 'Subcategoria'], values='Valor', title='Distribuição de Gastos por Categoria e Subcategoria', color_discrete_sequence=px.colors.qualitative.Pastel)
            fi
