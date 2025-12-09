import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Obra - Controle de Atividades",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 5px;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .status-completed {
        background-color: #D1FAE5;
        color: #065F46;
    }
    .status-progress {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .status-delayed {
        background-color: #FEE2E2;
        color: #991B1B;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown('<h1 class="main-header">🏗️ Dashboard de Controle de Obra</h1>', unsafe_allow_html=True)

# Inicialização dos dados na sessão
if 'relatorios' not in st.session_state:
    st.session_state.relatorios = []
if 'projeto_atual' not in st.session_state:
    st.session_state.projeto_atual = "LBO XAI-XA - Requalificação com Expansão"

# Sidebar para navegação
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
    st.title("Menu de Navegação")
    
    modo = st.radio(
        "Modo de Acesso:",
        ["👷 Fiscal (Registrar)", "👨‍💼 Proprietário (Visualizar)", "📊 Financeiro (Análise)"]
    )
    
    st.markdown("---")
    st.subheader("Filtros de Visualização")
    
    # Filtro de datas
    data_inicio = st.date_input(
        "Data inicial",
        value=date.today() - timedelta(days=30)
    )
    data_fim = st.date_input(
        "Data final",
        value=date.today()
    )
    
    # Filtro por projeto
    projetos = ["LBO XAI-XA", "Projeto A", "Projeto B", "Projeto C"]
    projeto_selecionado = st.selectbox(
        "Selecione o projeto:",
        projetos,
        index=0
    )
    
    st.markdown("---")
    st.info("**Sistema de Controle de Obra**\n\nRegistro e monitoramento diário de atividades para transparência total do projeto.")

# Dados de exemplo para demonstração
def carregar_dados_exemplo():
    hoje = date.today()
    dados_exemplo = [
        {
            "data": hoje - timedelta(days=2),
            "projeto": "LBO XAI-XA",
            "temperatura": "Céu parcialmente nublado com períodos de Chuva",
            "atividades": "Produção de betão, betonagem das sapatas e lançamento de betão de limpeza",
            "equipe": "1 mestre, 1 motorista, 6 subordinados, 1 encarregado, 1 fiscal",
            "equipamentos": "Betoneira",
            "ocorrencias": "Avaria da betoneira, entrada de areia grossa, descarregamento de materiais",
            "acidentes": "Nenhum",
            "status": "Concluído",
            "produtividade": 85
        },
        {
            "data": hoje - timedelta(days=1),
            "projeto": "LBO XAI-XA",
            "temperatura": "Céu limpo",
            "atividades": "Produção e lançamento de betão de limpeza, verificação de nível",
            "equipe": "1 mestre, 1 motorista, 6 subordinados, 1 encarregado",
            "equipamentos": "Betoneira (reparada)",
            "ocorrencias": "Nenhuma",
            "acidentes": "Nenhum",
            "status": "Concluído",
            "produtividade": 95
        },
        {
            "data": hoje,
            "projeto": "LBO XAI-XA",
            "temperatura": "Parcialmente nublado",
            "atividades": "Início do processo de levantamento das alvenarias de fundação",
            "equipe": "1 mestre, 7 subordinados, 1 encarregado, 1 fiscal",
            "equipamentos": "Ferramentas manuais",
            "ocorrencias": "Nenhuma",
            "acidentes": "Nenhum",
            "status": "Em andamento",
            "produtividade": 70
        }
    ]
    
    # Adicionar mais dados de exemplo
    for i in range(3, 15):
        status_opcoes = ["Concluído", "Em andamento", "Atrasado"]
        dados_exemplo.append({
            "data": hoje - timedelta(days=i),
            "projeto": "LBO XAI-XA",
            "temperatura": ["Ensolarado", "Nublado", "Chuvoso"][i % 3],
            "atividades": f"Atividade exemplo {i}",
            "equipe": "Equipe padrão",
            "equipamentos": "Equipamentos diversos",
            "ocorrencias": ["Nenhuma", "Chuva forte", "Atraso material"][i % 3],
            "acidentes": "Nenhum",
            "status": status_opcoes[i % 3],
            "produtividade": [80, 90, 75, 85, 95][i % 5]
        })
    
    return pd.DataFrame(dados_exemplo)

# MODO FISCAL - Registrar atividades
if modo == "👷 Fiscal (Registrar)":
    st.markdown('<h2 class="sub-header">📝 Registrar Relatório Diário</h2>', unsafe_allow_html=True)
    
    with st.form("form_relatorio"):
        col1, col2 = st.columns(2)
        
        with col1:
            data_relatorio = st.date_input("Data do relatório", value=date.today())
            projeto = st.text_input("Nome do projeto", value=st.session_state.projeto_atual)
            temperatura = st.text_input("Condições climáticas", placeholder="Ex: Céu parcialmente nublado com chuva")
            
        with col2:
            status = st.selectbox("Status do dia", ["Concluído", "Em andamento", "Atrasado", "Paralisado"])
            produtividade = st.slider("Produtividade (%)", 0, 100, 85)
            ocorreu_acidente = st.checkbox("Ocorreu acidente?")
        
        st.markdown("---")
        
        # Atividades planejadas
        st.subheader("Atividades Realizadas")
        atividades = st.text_area(
            "Descreva as atividades realizadas:",
            placeholder="Ex: Produção de betão, betonagem das sapatas, lançamento de betão de limpeza...",
            height=100
        )
        
        # Equipe presente
        st.subheader("Recursos Humanos")
        col3, col4 = st.columns(2)
        
        with col3:
            mestre = st.number_input("Nº de Mestres", min_value=0, value=1)
            motoristas = st.number_input("Nº de Motoristas", min_value=0, value=1)
            subordinados = st.number_input("Nº de Subordinados", min_value=0, value=6)
        
        with col4:
            encarregado = st.checkbox("Encarregado presente", value=True)
            fiscal = st.checkbox("Fiscal presente", value=True)
        
        # Equipamentos
        st.subheader("Equipamentos Utilizados")
        equipamentos = st.text_area(
            "Equipamentos utilizados:",
            placeholder="Ex: Betoneira, caminhão, ferramentas manuais...",
            height=80
        )
        
        # Ocorrências
        st.subheader("Ocorrências do Dia")
        ocorrencias = st.text_area(
            "Descreva as ocorrências (boas ou ruins):",
            placeholder="Ex: Avaria da betoneira, entrada de materiais, problemas técnicos...",
            height=100
        )
        
        # Acidentes (se houver)
        acidentes = ""
        if ocorreu_acidente:
            acidentes = st.text_area(
                "Descreva o(s) acidente(s) ocorrido(s):",
                placeholder="Descreva detalhadamente o acidente, feridos, medidas tomadas...",
                height=100
            )
        else:
            acidentes = "Nenhum acidente de trabalho"
        
        # Plano para o próximo dia
        st.subheader("Plano para o Próximo Dia")
        plano_amanha = st.text_area(
            "Atividades planejadas para amanhã:",
            placeholder="Ex: Produção e lançamento de betão, verificação de nível, início de alvenaria...",
            height=100
        )
        
        submitted = st.form_submit_button("Salvar Relatório")
        
        if submitted:
            # Criar objeto do relatório
            relatorio = {
                "data": data_relatorio,
                "projeto": projeto,
                "temperatura": temperatura,
                "atividades": atividades,
                "equipe": f"{mestre} mestre(s), {motoristas} motorista(s), {subordinados} subordinado(s)" + 
                         (", encarregado" if encarregado else "") + 
                         (", fiscal" if fiscal else ""),
                "equipamentos": equipamentos,
                "ocorrencias": ocorrencias,
                "acidentes": acidentes,
                "plano_amanha": plano_amanha,
                "status": status,
                "produtividade": produtividade
            }
            
            # Adicionar à lista de relatórios
            st.session_state.relatorios.append(relatorio)
            
            st.success(f"✅ Relatório de {data_relatorio.strftime('%d/%m/%Y')} salvo com sucesso!")
            
            # Mostrar preview
            with st.expander("Visualizar Relatório Salvo"):
                st.write(f"**Data:** {data_relatorio.strftime('%d/%m/%Y')}")
                st.write(f"**Projeto:** {projeto}")
                st.write(f"**Condições Climáticas:** {temperatura}")
                st.write(f"**Atividades:** {atividades}")
                st.write(f"**Equipe:** {relatorio['equipe']}")
                st.write(f"**Equipamentos:** {equipamentos}")
                st.write(f"**Ocorrências:** {ocorrencias}")
                st.write(f"**Acidentes:** {acidentes}")
                st.write(f"**Status:** {status}")
                st.write(f"**Produtividade:** {produtividade}%")
                st.write(f"**Plano para Amanhã:** {plano_amanha}")

# MODO PROPRIETÁRIO - Visualizar relatórios
elif modo == "👨‍💼 Proprietário (Visualizar)":
    # Carregar dados de exemplo
    df = carregar_dados_exemplo()
    
    # Filtrar dados
    df_filtrado = df[
        (df['data'] >= pd.Timestamp(data_inicio)) & 
        (df['data'] <= pd.Timestamp(data_fim)) &
        (df['projeto'] == projeto_selecionado)
    ]
    
    # Métricas principais
    st.markdown('<h2 class="sub-header">📊 Métricas Gerais do Projeto</h2>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Dias de Trabalho", len(df_filtrado))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        dias_concluidos = len(df_filtrado[df_filtrado['status'] == 'Concluído'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Dias Concluídos", dias_concluidos)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        produtividade_media = df_filtrado['produtividade'].mean() if len(df_filtrado) > 0 else 0
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Produtividade Média", f"{produtividade_media:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        dias_sem_acidente = len(df_filtrado[df_filtrado['acidentes'] == 'Nenhum'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Dias Sem Acidente", dias_sem_acidente)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráficos
    st.markdown('<h2 class="sub-header">📈 Análise de Produtividade</h2>', unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if len(df_filtrado) > 0:
            fig_prod = px.line(
                df_filtrado.sort_values('data'),
                x='data',
                y='produtividade',
                title='Produtividade por Dia',
                markers=True
            )
            fig_prod.update_layout(
                xaxis_title="Data",
                yaxis_title="Produtividade (%)",
                hovermode="x unified"
            )
            st.plotly_chart(fig_prod, use_container_width=True)
    
    with col_chart2:
        if len(df_filtrado) > 0:
            status_counts = df_filtrado['status'].value_counts()
            fig_status = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title='Distribuição de Status',
                color=status_counts.index,
                color_discrete_map={
                    'Concluído': '#10B981',
                    'Em andamento': '#F59E0B',
                    'Atrasado': '#EF4444'
                }
            )
            st.plotly_chart(fig_status, use_container_width=True)
    
    # Tabela de relatórios
    st.markdown('<h2 class="sub-header">📋 Relatórios Diários</h2>', unsafe_allow_html=True)
    
    if len(df_filtrado) > 0:
        # Formatar dataframe para exibição
        df_display = df_filtrado.copy()
        df_display['data'] = df_display['data'].dt.strftime('%d/%m/%Y')
        
        # Função para colorir status
        def color_status(status):
            if status == 'Concluído':
                return '<span class="status-badge status-completed">Concluído</span>'
            elif status == 'Em andamento':
                return '<span class="status-badge status-progress">Em andamento</span>'
            else:
                return '<span class="status-badge status-delayed">Atrasado</span>'
        
        df_display['status'] = df_display['status'].apply(color_status)
        
        # Mostrar tabela
        st.markdown(df_display[['data', 'atividades', 'status', 'produtividade', 'ocorrencias']].to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # Expansor para detalhes
        for idx, row in df_filtrado.iterrows():
            with st.expander(f"📅 Relatório Detalhado - {row['data'].strftime('%d/%m/%Y')}"):
                col_det1, col_det2 = st.columns(2)
                
                with col_det1:
                    st.write(f"**Projeto:** {row['projeto']}")
                    st.write(f"**Condições Climáticas:** {row['temperatura']}")
                    st.write(f"**Equipe:** {row['equipe']}")
                    st.write(f"**Equipamentos:** {row['equipamentos']}")
                
                with col_det2:
                    st.write(f"**Status:** {row['status']}")
                    st.write(f"**Produtividade:** {row['produtividade']}%")
                    st.write(f"**Acidentes:** {row['acidentes']}")
                
                st.write("**Atividades Realizadas:**")
                st.info(row['atividades'])
                
                if row['ocorrencias'] != 'Nenhuma':
                    st.write("**Ocorrências:**")
                    st.warning(row['ocorrencias'])
    else:
        st.warning("Nenhum relatório encontrado para os filtros selecionados.")

# MODO FINANCEIRO - Análise detalhada
else:
    st.markdown('<h2 class="sub-header">💰 Análise Financeira e de Progresso</h2>', unsafe_allow_html=True)
    
    # Carregar dados
    df = carregar_dados_exemplo()
    
    # Métricas financeiras
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Custos Diários")
        st.metric("Custo Médio/Dia", "MZN 25.000", "+2%")
        st.progress(0.75)
        st.caption("75% do orçamento diário utilizado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Materiais Consumidos")
        st.metric("Betão Produzido", "45 m³")
        st.metric("Areia", "12 ton")
        st.metric("Cimento", "150 sacos")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Custos com Equipe")
        st.metric("Custo Total", "MZN 180.000")
        st.metric("Dias Homem", "156")
        st.metric("Custo Médio/Homem-Dia", "MZN 1.154")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráfico de progresso
    st.markdown('<h3 class="sub-header">📅 Progresso ao Longo do Tempo</h3>', unsafe_allow_html=True)
    
    # Dados simulados de progresso
    progresso_data = pd.DataFrame({
        'Semana': [1, 2, 3, 4, 5, 6, 7, 8],
        'Planejado (%)': [10, 20, 30, 40, 50, 60, 70, 80],
        'Realizado (%)': [8, 18, 28, 38, 48, 58, 65, 72],
        'Custo (MZN mil)': [50, 105, 165, 230, 300, 375, 455, 540]
    })
    
    fig_progress = go.Figure()
    fig_progress.add_trace(go.Scatter(
        x=progresso_data['Semana'],
        y=progresso_data['Planejado (%)'],
        mode='lines+markers',
        name='Planejado',
        line=dict(color='blue', dash='dash')
    ))
    fig_progress.add_trace(go.Scatter(
        x=progresso_data['Semana'],
        y=progresso_data['Realizado (%)'],
        mode='lines+markers',
        name='Realizado',
        line=dict(color='green')
    ))
    
    fig_progress.update_layout(
        title='Progresso do Projeto vs Planejado',
        xaxis_title='Semana',
        yaxis_title='Completude (%)',
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_progress, use_container_width=True)
    
    # Tabela de custos
    st.markdown('<h3 class="sub-header">📋 Detalhamento de Custos</h3>', unsafe_allow_html=True)
    
    custos_categorias = pd.DataFrame({
        'Categoria': ['Materiais', 'Mão de Obra', 'Equipamentos', 'Transporte', 'Serviços', 'Imprevistos'],
        'Orçamento (MZN)': [500000, 300000, 150000, 80000, 50000, 20000],
        'Gasto (MZN)': [420000, 280000, 130000, 75000, 45000, 18000],
        'Variação (%)': [-16, -6.7, -13.3, -6.25, -10, -10]
    })
    
    custos_categorias['Utilização (%)'] = (custos_categorias['Gasto (MZN)'] / custos_categorias['Orçamento (MZN)'] * 100).round(1)
    
    st.dataframe(custos_categorias, use_container_width=True)

# Rodapé
st.markdown("---")
col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.caption("**Dashboard de Controle de Obra**")
    st.caption("Sistema desenvolvido para transparência e monitoramento")

with col_footer2:
    st.caption(f"Última atualização: {date.today().strftime('%d/%m/%Y')}")
    st.caption("Dados atualizados diariamente")

with col_footer3:
    st.caption("👷 Fiscal: Gildo José Cossa")
    st.caption("📞 Contato: fiscal.obra@exemplo.com")

# Instruções para executar
st.sidebar.markdown("---")
st.sidebar.info(
    "**Para executar esta aplicação:**\n\n"
    "1. Instale as dependências:\n"
    "```bash\npip install streamlit pandas plotly\n```\n"
    "2. Execute o app:\n"
    "```bash\nstreamlit run dashboard_obra.py\n```"
)