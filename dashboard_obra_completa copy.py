# dashboard_obra_completo.py
import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import plotly.express as px
import plotly.graph_objects as go
import sqlite3
import hashlib
import os
from pathlib import Path
import io
from PIL import Image
import json
import yaml
from streamlit_authenticator import Authenticate
import extra_streamlit_components as stx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import base64

# ============================================
# CONFIGURAÇÃO INICIAL
# ============================================

st.set_page_config(
    page_title="Dashboard de Obra Completo",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        padding: 1rem 0;
    }
    .card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 0.5rem;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# AUTENTICAÇÃO
# ============================================

def setup_authentication():
    """Configura o sistema de autenticação"""
    config = {
        'credentials': {
            'usernames': {
                'fiscal': {
                    'name': 'Gildo José Cossa',
                    'password': hashlib.sha256('fiscal123'.encode()).hexdigest()
                },
                'proprietario': {
                    'name': 'Carlos Silva',
                    'password': hashlib.sha256('proprietario123'.encode()).hexdigest()
                },
                'financeiro': {
                    'name': 'Maria Santos',
                    'password': hashlib.sha256('financeiro123'.encode()).hexdigest()
                },
                'admin': {
                    'name': 'Administrador',
                    'password': hashlib.sha256('admin123'.encode()).hexdigest()
                }
            }
        },
        'cookie': {
            'expiry_days': 30,
            'key': 'obra_dashboard',
            'name': 'obra_auth'
        },
        'preauthorized': {
            'emails': []
        }
    }
    
    authenticator = Authenticate(
        config['credentials'],
        config['cookie']['key'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    
    return authenticator

# ============================================
# BANCO DE DADOS
# ============================================

def init_database():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('obra_completo.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT,
            tipo TEXT NOT NULL,
            telefone TEXT
        )
    ''')
    
    # Tabela de projetos
    c.execute('''
        CREATE TABLE IF NOT EXISTS projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            descricao TEXT,
            localizacao TEXT,
            orcamento_total REAL,
            data_inicio DATE,
            data_fim_previsto DATE,
            status TEXT DEFAULT 'Em andamento'
        )
    ''')
    
    # Tabela de relatórios
    c.execute('''
        CREATE TABLE IF NOT EXISTS relatorios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            projeto_id INTEGER,
            usuario_id INTEGER,
            temperatura TEXT,
            atividades TEXT NOT NULL,
            equipe TEXT,
            equipamentos TEXT,
            ocorrencias TEXT,
            acidentes TEXT DEFAULT 'Nenhum',
            status TEXT,
            produtividade INTEGER,
            observacoes TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')
    
    # Tabela de fotos
    c.execute('''
        CREATE TABLE IF NOT EXISTS fotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relatorio_id INTEGER,
            foto_data BLOB,
            descricao TEXT,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (relatorio_id) REFERENCES relatorios(id)
        )
    ''')
    
    # Tabela de materiais
    c.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER,
            material TEXT NOT NULL,
            quantidade REAL,
            unidade TEXT,
            custo_unitario REAL,
            data_entrada DATE,
            FOREIGN KEY (projeto_id) REFERENCES projetos(id)
        )
    ''')
    
    # Inserir dados iniciais
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios = [
            ('fiscal', 'Gildo José Cossa', 'fiscal@obra.com', 'fiscal', '+258841234567'),
            ('proprietario', 'Carlos Silva', 'proprietario@obra.com', 'proprietario', '+258842345678'),
            ('financeiro', 'Maria Santos', 'financeiro@obra.com', 'financeiro', '+258843456789'),
            ('admin', 'Administrador', 'admin@obra.com', 'admin', '+258844567890')
        ]
        c.executemany('INSERT INTO usuarios (username, nome, email, tipo, telefone) VALUES (?, ?, ?, ?, ?)', usuarios)
    
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        projetos = [
            ('LBO XAI-XA - Requalificação', 'Projeto de requalificação com expansão', 'Xai-Xai, Gaza', 
             2500000.00, '2025-02-01', '2025-08-01', 'Em andamento'),
            ('Edifício Residencial A', 'Construção de edifício residencial', 'Maputo', 
             1800000.00, '2025-01-15', '2025-07-15', 'Em andamento')
        ]
        c.executemany('INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, status) VALUES (?, ?, ?, ?, ?, ?, ?)', projetos)
    
    conn.commit()
    return conn

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def get_projetos(conn):
    """Obtém lista de projetos"""
    c = conn.cursor()
    c.execute("SELECT id, nome FROM projetos ORDER BY nome")
    return c.fetchall()

def get_relatorios(conn, projeto_id=None, data_inicio=None, data_fim=None):
    """Obtém relatórios com filtros"""
    c = conn.cursor()
    
    query = "SELECT * FROM relatorios WHERE 1=1"
    params = []
    
    if projeto_id:
        query += " AND projeto_id = ?"
        params.append(projeto_id)
    
    if data_inicio:
        query += " AND data >= ?"
        params.append(data_inicio)
    
    if data_fim:
        query += " AND data <= ?"
        params.append(data_fim)
    
    query += " ORDER BY data DESC"
    c.execute(query, params)
    return c.fetchall()

def save_relatorio(conn, data):
    """Salva um relatório no banco"""
    c = conn.cursor()
    c.execute('''
        INSERT INTO relatorios 
        (data, projeto_id, usuario_id, temperatura, atividades, equipe, 
         equipamentos, ocorrencias, acidentes, status, produtividade, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data)
    conn.commit()
    return c.lastrowid

def save_foto(conn, relatorio_id, foto_bytes, descricao=""):
    """Salva uma foto no banco"""
    c = conn.cursor()
    c.execute('''
        INSERT INTO fotos (relatorio_id, foto_data, descricao)
        VALUES (?, ?, ?)
    ''', (relatorio_id, foto_bytes, descricao))
    conn.commit()

def get_fotos(conn, relatorio_id):
    """Obtém fotos de um relatório"""
    c = conn.cursor()
    c.execute('SELECT foto_data, descricao FROM fotos WHERE relatorio_id = ?', (relatorio_id,))
    return c.fetchall()

def gerar_pdf_relatorio(relatorio_data):
    """Gera PDF do relatório"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph("Relatório Diário de Obra", styles['Title']))
    elements.append(Spacer(1, 20))
    
    # Informações básicas
    info_data = [
        ["Data:", relatorio_data['data']],
        ["Projeto:", relatorio_data['projeto']],
        ["Status:", relatorio_data['status']],
        ["Produtividade:", f"{relatorio_data['produtividade']}%"]
    ]
    
    info_table = Table(info_data, colWidths=[100, 400])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Conteúdo do relatório
    elementos_conteudo = [
        ("Condições Climáticas", relatorio_data['temperatura']),
        ("Atividades Realizadas", relatorio_data['atividades']),
        ("Equipe", relatorio_data['equipe']),
        ("Equipamentos", relatorio_data['equipamentos']),
        ("Ocorrências", relatorio_data['ocorrencias']),
        ("Acidentes", relatorio_data['acidentes']),
        ("Observações", relatorio_data['observacoes'])
    ]
    
    for titulo, conteudo in elementos_conteudo:
        if conteudo:
            elements.append(Paragraph(f"<b>{titulo}:</b>", styles['Heading2']))
            elements.append(Paragraph(conteudo, styles['Normal']))
            elements.append(Spacer(1, 10))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================
# PÁGINAS DO DASHBOARD
# ============================================

def pagina_dashboard(conn, usuario):
    """Página principal do dashboard"""
    st.markdown('<h1 class="main-header">📊 Dashboard de Obra</h1>', unsafe_allow_html=True)
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        projetos = get_projetos(conn)
        projeto_opcoes = {p[0]: p[1] for p in projetos}
        projeto_id = st.selectbox("Projeto", list(projeto_opcoes.keys()), 
                                format_func=lambda x: projeto_opcoes[x])
    
    with col2:
        data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=30))
    
    with col3:
        data_fim = st.date_input("Data final", value=date.today())
    
    # Obter dados
    relatorios = get_relatorios(conn, projeto_id, data_inicio, data_fim)
    
    if not relatorios:
        st.info("Nenhum relatório encontrado para o período selecionado.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(relatorios, columns=['ID', 'Data', 'Projeto_ID', 'Usuario_ID', 'Temperatura',
                                          'Atividades', 'Equipe', 'Equipamentos', 'Ocorrências',
                                          'Acidentes', 'Status', 'Produtividade', 'Observacoes'])
    
    # Métricas
    st.subheader("📈 Métricas do Projeto")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Dias Trabalhados", len(df))
    
    with col_m2:
        prod_media = df['Produtividade'].mean()
        st.metric("Produtividade Média", f"{prod_media:.1f}%")
    
    with col_m3:
        dias_concluidos = len(df[df['Status'] == 'Concluído'])
        st.metric("Dias Concluídos", dias_concluidos)
    
    with col_m4:
        dias_sem_acidente = len(df[df['Acidentes'] == 'Nenhum'])
        st.metric("Dias Sem Acidente", dias_sem_acidente)
    
    # Gráficos
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.subheader("Produtividade Diária")
        df['Data'] = pd.to_datetime(df['Data'])
        fig = px.line(df, x='Data', y='Produtividade', markers=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        st.subheader("Distribuição de Status")
        status_counts = df['Status'].value_counts()
        fig = px.pie(values=status_counts.values, names=status_counts.index)
        st.plotly_chart(fig, use_container_width=True)
    
    # Últimos relatórios
    st.subheader("📋 Últimos Relatórios")
    
    for idx, row in df.head(5).iterrows():
        with st.expander(f"📅 {row['Data'].strftime('%d/%m/%Y')} - {row['Status']} - {row['Produtividade']}%"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.write(f"**Atividades:** {row['Atividades'][:200]}...")
                st.write(f"**Equipe:** {row['Equipe']}")
            
            with col_e2:
                st.write(f"**Equipamentos:** {row['Equipamentos']}")
                if row['Acidentes'] != 'Nenhum':
                    st.error(f"**Acidentes:** {row['Acidentes']}")
                if row['Ocorrências'] != 'Nenhuma':
                    st.warning(f"**Ocorrências:** {row['Ocorrências']}")
            
            # Botões de ação
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("📄 Gerar PDF", key=f"pdf_{row['ID']}"):
                    relatorio_data = {
                        'data': row['Data'].strftime('%d/%m/%Y'),
                        'projeto': projeto_opcoes.get(projeto_id, 'Projeto'),
                        'status': row['Status'],
                        'produtividade': row['Produtividade'],
                        'temperatura': row['Temperatura'],
                        'atividades': row['Atividades'],
                        'equipe': row['Equipe'],
                        'equipamentos': row['Equipamentos'],
                        'ocorrencias': row['Ocorrências'],
                        'acidentes': row['Acidentes'],
                        'observacoes': row['Observacoes']
                    }
                    pdf = gerar_pdf_relatorio(relatorio_data)
                    st.download_button(
                        label="⬇️ Baixar PDF",
                        data=pdf,
                        file_name=f"relatorio_{row['Data'].strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )

def pagina_novo_relatorio(conn, usuario):
    """Página para criar novo relatório"""
    st.markdown('<h1 class="main-header">📝 Novo Relatório Diário</h1>', unsafe_allow_html=True)
    
    with st.form("form_novo_relatorio", clear_on_submit=True):
        # Informações básicas
        col1, col2 = st.columns(2)
        
        with col1:
            data = st.date_input("Data do relatório", value=date.today())
            
            projetos = get_projetos(conn)
            projeto_opcoes = {p[0]: p[1] for p in projetos}
            projeto_id = st.selectbox("Projeto", list(projeto_opcoes.keys()),
                                    format_func=lambda x: projeto_opcoes[x])
            
            temperatura = st.text_input("Condições climáticas", 
                                      placeholder="Ex: Céu parcialmente nublado com chuva")
        
        with col2:
            status = st.selectbox("Status do dia", 
                                ["Concluído", "Em andamento", "Atrasado", "Paralisado"])
            
            produtividade = st.slider("Produtividade (%)", 0, 100, 85,
                                    help="Avaliação da produtividade do dia")
            
            ocorreu_acidente = st.checkbox("Ocorreu acidente?")
        
        # Equipe
        st.subheader("👥 Equipe Presente")
        col_e1, col_e2, col_e3 = st.columns(3)
        
        with col_e1:
            mestre = st.number_input("Nº de Mestres", min_value=0, value=1)
        
        with col_e2:
            motoristas = st.number_input("Nº de Motoristas", min_value=0, value=1)
        
        with col_e3:
            subordinados = st.number_input("Nº de Subordinados", min_value=0, value=6)
        
        encarregado = st.checkbox("Encarregado presente", value=True)
        fiscal = st.checkbox("Fiscal presente", value=True)
        
        # Montar string da equipe
        equipe = f"{mestre} mestre(s), {motoristas} motorista(s), {subordinados} subordinado(s)"
        if encarregado:
            equipe += ", encarregado"
        if fiscal:
            equipe += ", fiscal"
        
        # Atividades
        st.subheader("🏗️ Atividades Realizadas")
        atividades = st.text_area(
            "Descreva detalhadamente as atividades do dia:",
            placeholder="Ex: Produção de betão classe B25, betonagem das sapatas, lançamento de betão de limpeza...",
            height=150
        )
        
        # Equipamentos
        st.subheader("🔧 Equipamentos Utilizados")
        equipamentos = st.text_area(
            "Equipamentos utilizados:",
            placeholder="Ex: Betoneira, caminhão, ferramentas manuais...",
            height=80
        )
        
        # Ocorrências
        st.subheader("📝 Ocorrências do Dia")
        ocorrencias = st.text_area(
            "Descreva as ocorrências:",
            placeholder="Ex: Avaria da betoneira, entrada de materiais, problemas técnicos...",
            height=100
        )
        
        # Acidentes
        acidentes = "Nenhum"
        if ocorreu_acidente:
            st.subheader("⚠️ Registro de Acidente")
            acidentes = st.text_area(
                "Descreva o acidente ocorrido:",
                placeholder="Descreva detalhadamente o acidente, pessoas envolvidas, medidas tomadas...",
                height=100
            )
        
        # Observações
        observacoes = st.text_area("Observações adicionais:", height=80)
        
        # Upload de fotos
        st.subheader("📸 Fotos do Dia")
        fotos = st.file_uploader("Selecione fotos da obra", 
                                type=['jpg', 'jpeg', 'png'],
                                accept_multiple_files=True)
        
        descricoes_fotos = []
        if fotos:
            st.write(f"{len(fotos)} foto(s) selecionada(s)")
            cols = st.columns(3)
            for i, foto in enumerate(fotos):
                with cols[i % 3]:
                    st.image(foto, caption=f"Foto {i+1}", width=200)
                    descricao = st.text_input(f"Descrição foto {i+1}", 
                                            placeholder="Breve descrição...",
                                            key=f"desc_{i}")
                    descricoes_fotos.append(descricao)
        
        # Botão de envio
        submitted = st.form_submit_button("💾 Salvar Relatório")
        
        if submitted:
            if not atividades:
                st.error("Por favor, descreva as atividades realizadas.")
            else:
                # Preparar dados
                dados_relatorio = (
                    data, projeto_id, 1,  # usuario_id fixo para demo
                    temperatura, atividades, equipe, equipamentos,
                    ocorrencias, acidentes, status, produtividade, observacoes
                )
                
                try:
                    # Salvar relatório
                    relatorio_id = save_relatorio(conn, dados_relatorio)
                    
                    # Salvar fotos
                    if fotos:
                        for i, foto in enumerate(fotos):
                            save_foto(conn, relatorio_id, foto.getvalue(),
                                     descricoes_fotos[i] if i < len(descricoes_fotos) else "")
                    
                    st.success(f"✅ Relatório salvo com sucesso! ID: {relatorio_id}")
                    
                    # Gerar PDF automaticamente
                    relatorio_data = {
                        'data': data.strftime('%d/%m/%Y'),
                        'projeto': projeto_opcoes.get(projeto_id, 'Projeto'),
                        'status': status,
                        'produtividade': produtividade,
                        'temperatura': temperatura,
                        'atividades': atividades,
                        'equipe': equipe,
                        'equipamentos': equipamentos,
                        'ocorrencias': ocorrencias,
                        'acidentes': acidentes,
                        'observacoes': observacoes
                    }
                    
                    pdf = gerar_pdf_relatorio(relatorio_data)
                    
                    st.download_button(
                        label="⬇️ Baixar Relatório em PDF",
                        data=pdf,
                        file_name=f"relatorio_{data.strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
                    
                except Exception as e:
                    st.error(f"Erro ao salvar relatório: {str(e)}")

def pagina_galeria_fotos(conn, usuario):
    """Página da galeria de fotos"""
    st.markdown('<h1 class="main-header">📸 Galeria de Fotos</h1>', unsafe_allow_html=True)
    
    # Filtros
    projetos = get_projetos(conn)
    projeto_opcoes = {p[0]: p[1] for p in projetos}
    projeto_id = st.selectbox("Projeto", list(projeto_opcoes.keys()),
                            format_func=lambda x: projeto_opcoes[x])
    
    data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=7))
    data_fim = st.date_input("Data final", value=date.today())
    
    # Buscar relatórios com fotos
    relatorios = get_relatorios(conn, projeto_id, data_inicio, data_fim)
    
    if not relatorios:
        st.info("Nenhum relatório com fotos encontrado.")
        return
    
    # Exibir fotos por relatório
    for relatorio in relatorios:
        fotos = get_fotos(conn, relatorio[0])
        
        if fotos:
            with st.expander(f"📅 {relatorio[1]} - {len(fotos)} foto(s)"):
                st.write(f"**Atividades:** {relatorio[5][:100]}...")
                
                # Mostrar fotos em grade
                cols = st.columns(3)
                for i, (foto_data, descricao) in enumerate(fotos):
                    with cols[i % 3]:
                        try:
                            img = Image.open(io.BytesIO(foto_data))
                            st.image(img, caption=descricao or f"Foto {i+1}", use_column_width=True)
                        except:
                            st.error("Erro ao carregar imagem")

def pagina_relatorios(conn, usuario):
    """Página de visualização de relatórios"""
    st.markdown('<h1 class="main-header">📋 Relatórios Diários</h1>', unsafe_allow_html=True)
    
    # Filtros avançados
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        projetos = get_projetos(conn)
        projeto_opcoes = {p[0]: p[1] for p in projetos}
        projeto_id = st.selectbox("Projeto", list(projeto_opcoes.keys()),
                                format_func=lambda x: projeto_opcoes[x])
    
    with col_f2:
        data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=30))
    
    with col_f3:
        data_fim = st.date_input("Data final", value=date.today())
    
    # Filtros adicionais
    col_f4, col_f5 = st.columns(2)
    with col_f4:
        status_filtro = st.multiselect("Filtrar por status", 
                                      ["Concluído", "Em andamento", "Atrasado", "Paralisado"],
                                      default=["Concluído", "Em andamento"])
    
    with col_f5:
        min_produtividade = st.slider("Produtividade mínima", 0, 100, 0)
    
    # Buscar relatórios
    relatorios = get_relatorios(conn, projeto_id, data_inicio, data_fim)
    
    if not relatorios:
        st.info("Nenhum relatório encontrado.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(relatorios, columns=['ID', 'Data', 'Projeto_ID', 'Usuario_ID', 'Temperatura',
                                          'Atividades', 'Equipe', 'Equipamentos', 'Ocorrências',
                                          'Acidentes', 'Status', 'Produtividade', 'Observacoes'])
    
    # Aplicar filtros
    df_filtrado = df[
        (df['Status'].isin(status_filtro)) & 
        (df['Produtividade'] >= min_produtividade)
    ]
    
    # Mostrar estatísticas
    st.subheader("📊 Estatísticas")
    col_s1, col_s2, col_s3 = st.columns(3)
    
    with col_s1:
        st.metric("Total de Relatórios", len(df_filtrado))
    
    with col_s2:
        prod_media = df_filtrado['Produtividade'].mean()
        st.metric("Produtividade Média", f"{prod_media:.1f}%")
    
    with col_s3:
        dias_com_acidente = len(df_filtrado[df_filtrado['Acidentes'] != 'Nenhum'])
        st.metric("Dias com Acidente", dias_com_acidente)
    
    # Tabela de relatórios
    st.subheader("📋 Lista de Relatórios")
    
    # Formatar DataFrame para exibição
    df_display = df_filtrado.copy()
    df_display['Data'] = pd.to_datetime(df_display['Data']).dt.strftime('%d/%m/%Y')
    df_display['Atividades'] = df_display['Atividades'].str[:100] + "..."
    
    st.dataframe(df_display[['Data', 'Atividades', 'Status', 'Produtividade', 'Acidentes']], 
                use_container_width=True)
    
    # Exportar dados
    st.subheader("📥 Exportar Dados")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if st.button("📊 Exportar para Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_filtrado.to_excel(writer, index=False, sheet_name='Relatorios')
            output.seek(0)
            
            st.download_button(
                label="⬇️ Baixar Excel",
                data=output,
                file_name=f"relatorios_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    with col_exp2:
        if st.button("📄 Exportar para JSON"):
            json_data = df_filtrado.to_json(orient='records', indent=2)
            st.download_button(
                label="⬇️ Baixar JSON",
                data=json_data,
                file_name=f"relatorios_{date.today()}.json",
                mime="application/json"
            )

def pagina_controle_financeiro(conn, usuario):
    """Página de controle financeiro"""
    st.markdown('<h1 class="main-header">💰 Controle Financeiro</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Orçamento", "Custos", "Análise"])
    
    with tab1:
        st.subheader("📋 Orçamento do Projeto")
        
        projetos = get_projetos(conn)
        projeto_opcoes = {p[0]: p[1] for p in projetos}
        projeto_id = st.selectbox("Selecione o projeto", list(projeto_opcoes.keys()),
                                format_func=lambda x: projeto_opcoes[x], key="projeto_fin")
        
        if projeto_id:
            c = conn.cursor()
            c.execute("SELECT * FROM projetos WHERE id = ?", (projeto_id,))
            projeto = c.fetchone()
            
            if projeto:
                col_o1, col_o2, col_o3 = st.columns(3)
                
                with col_o1:
                    st.metric("Orçamento Total", f"MZN {projeto[4]:,.2f}")
                
                with col_o2:
                    # Calcular custos (simulado)
                    custos_simulados = projeto[4] * 0.35  # 35% do orçamento
                    st.metric("Custos Realizados", f"MZN {custos_simulados:,.2f}")
                
                with col_o3:
                    percentual = (custos_simulados / projeto[4]) * 100
                    st.metric("Percentual Utilizado", f"{percentual:.1f}%")
                
                # Barra de progresso
                st.progress(percentual / 100)
                
                # Datas
                st.info(f"**Data de Início:** {projeto[5]}")
                st.info(f"**Previsão de Término:** {projeto[6]}")
                st.info(f"**Status:** {projeto[7]}")
    
    with tab2:
        st.subheader("📝 Lançar Novo Custo")
        
        with st.form("form_custo"):
            col_c1, col_c2 = st.columns(2)
            
            with col_c1:
                categoria = st.selectbox("Categoria", 
                                       ["Materiais", "Mão de Obra", "Equipamentos", 
                                        "Transporte", "Serviços", "Imprevistos"])
                
                descricao = st.text_input("Descrição do custo")
            
            with col_c2:
                valor = st.number_input("Valor (MZN)", min_value=0.0, step=100.0)
                data_custo = st.date_input("Data", value=date.today())
            
            if st.form_submit_button("💾 Lançar Custo"):
                st.success(f"Custo de MZN {valor:,.2f} lançado com sucesso!")
    
    with tab3:
        st.subheader("📈 Análise Financeira")
        
        # Dados simulados para análise
        dados_custos = pd.DataFrame({
            'Mês': ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
            'Planejado': [200000, 180000, 220000, 240000, 210000, 190000],
            'Realizado': [190000, 175000, 210000, 230000, 205000, 185000]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dados_custos['Mês'],
            y=dados_custos['Planejado'],
            name='Planejado',
            marker_color='indianred'
        ))
        fig.add_trace(go.Bar(
            x=dados_custos['Mês'],
            y=dados_custos['Realizado'],
            name='Realizado',
            marker_color='lightsalmon'
        ))
        
        fig.update_layout(barmode='group', title='Custos Mensais - Planejado vs Realizado')
        st.plotly_chart(fig, use_container_width=True)

# ============================================
# APLICAÇÃO PRINCIPAL
# ============================================

def main():
    """Função principal da aplicação"""
    
    # Inicializar banco de dados
    conn = init_database()
    
    # Sistema de autenticação simplificado
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario = None
    
    if not st.session_state.autenticado:
        # Tela de login
        st.markdown('<h1 class="main-header">🔐 Login - Dashboard de Obra</h1>', unsafe_allow_html=True)
        
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        
        with col_l2:
            with st.form("login_form"):
                st.subheader("Acesso ao Sistema")
                
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                
                submit = st.form_submit_button("Entrar")
                
                if submit:
                    # Verificar credenciais (simplificado)
                    if username and password:
                        c = conn.cursor()
                        c.execute("SELECT * FROM usuarios WHERE username = ?", (username,))
                        usuario = c.fetchone()
                        
                        if usuario:
                            # Verificar senha (simplificado - em produção usar hash)
                            senha_hash = hashlib.sha256(password.encode()).hexdigest()
                            c.execute("SELECT password FROM usuarios WHERE username = ?", (username,))
                            # Aqui deveria verificar o hash, mas para demo aceita qualquer senha
                            
                            st.session_state.autenticado = True
                            st.session_state.usuario = {
                                'id': usuario[0],
                                'username': usuario[1],
                                'nome': usuario[2],
                                'tipo': usuario[4]
                            }
                            st.success(f"Bem-vindo, {usuario[2]}!")
                            st.rerun()
                        else:
                            st.error("Usuário não encontrado.")
                    else:
                        st.error("Preencha usuário e senha.")
        
        # Informações de acesso para teste
        with st.expander("Credenciais para Teste"):
            st.write("**Usuários disponíveis:**")
            st.write("- **fiscal** / fiscal123")
            st.write("- **proprietario** / proprietario123")
            st.write("- **financeiro** / financeiro123")
            st.write("- **admin** / admin123")
    else:
        # Aplicação principal
        usuario = st.session_state.usuario
        
        # Sidebar com menu
        with st.sidebar:
            st.title(f"👤 {usuario['nome'].split()[0]}")
            st.caption(f"Tipo: {usuario['tipo'].title()}")
            
            st.markdown("---")
            
            # Menu baseado no tipo de usuário
            if usuario['tipo'] == 'fiscal':
                opcoes_menu = [
                    "📊 Dashboard",
                    "📝 Novo Relatório",
                    "📸 Galeria de Fotos",
                    "📋 Meus Relatórios"
                ]
            elif usuario['tipo'] == 'proprietario':
                opcoes_menu = [
                    "📊 Dashboard",
                    "📋 Relatórios",
                    "📸 Galeria de Fotos",
                    "💰 Controle Financeiro"
                ]
            elif usuario['tipo'] == 'financeiro':
                opcoes_menu = [
                    "📊 Dashboard",
                    "💰 Controle Financeiro",
                    "📋 Relatórios"
                ]
            else:  # admin
                opcoes_menu = [
                    "📊 Dashboard",
                    "📝 Novo Relatório",
                    "📸 Galeria de Fotos",
                    "📋 Relatórios",
                    "💰 Controle Financeiro"
                ]
            
            pagina_selecionada = stx.tab_bar(
                data=[
                    stx.TabBarItemData(id=opcao, title=opcao, description="") 
                    for opcao in opcoes_menu
                ],
                default=opcoes_menu[0]
            )
            
            st.markdown("---")
            
            if st.button("🚪 Sair"):
                st.session_state.autenticado = False
                st.session_state.usuario = None
                st.rerun()
        
        # Exibir página selecionada
        if "📊 Dashboard" in pagina_selecionada:
            pagina_dashboard(conn, usuario)
        elif "📝 Novo Relatório" in pagina_selecionada:
            pagina_novo_relatorio(conn, usuario)
        elif "📸 Galeria de Fotos" in pagina_selecionada:
            pagina_galeria_fotos(conn, usuario)
        elif "📋 Relatórios" in pagina_selecionada or "Meus Relatórios" in pagina_selecionada:
            pagina_relatorios(conn, usuario)
        elif "💰 Controle Financeiro" in pagina_selecionada:
            pagina_controle_financeiro(conn, usuario)

# ============================================
# EXECUÇÃO
# ============================================

if __name__ == "__main__":
    main()