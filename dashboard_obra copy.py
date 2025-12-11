import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import io
import base64
import json
import os
from pathlib import Path
import tempfile

# Tentar importar plotly com fallback
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    st.warning("âš ï¸ Plotly nÃ£o estÃ¡ disponÃ­vel. Instale com: pip install plotly")

# PIL removido - incompatível com Python 3.13.9

try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# ============================================
# CONFIGURAÃ‡ÃƒO INICIAL
# ============================================

# ConfiguraÃ§Ã£o da pÃ¡gina
st.set_page_config(
    page_title="Dashboard de Obra AvanÃ§ado",
    page_icon="ðŸ—ï¸",
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
        padding-top: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #3B82F6;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
    .card {
        background-color: #F8FAFC;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
        border: 1px solid #E5E7EB;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        text-align: center;
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
    .uploaded-image {
        max-width: 100%;
        border-radius: 8px;
        margin: 10px 0;
        border: 2px solid #E5E7EB;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    .alert-warning {
        background-color: #FEF3C7;
        border-left-color: #F59E0B;
    }
    .alert-success {
        background-color: #D1FAE5;
        border-left-color: #10B981;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# INICIALIZAÃ‡ÃƒO DO BANCO DE DADOS
# ============================================

def init_database():
    """Inicializa o banco de dados SQLite com todas as tabelas necessÃ¡rias"""
    conn = sqlite3.connect('controle_obra.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tabela de usuÃ¡rios
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            tipo TEXT NOT NULL,
            telefone TEXT,
            ativo INTEGER DEFAULT 1
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
            status TEXT DEFAULT 'Em andamento',
            responsavel_id INTEGER,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabela de relatÃ³rios diÃ¡rios
    c.execute('''
        CREATE TABLE IF NOT EXISTS relatorios_diarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data DATE NOT NULL,
            projeto_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            temperatura TEXT,
            atividades TEXT NOT NULL,
            equipe TEXT,
            equipamentos TEXT,
            ocorrencias TEXT,
            acidentes TEXT DEFAULT 'Nenhum',
            plano_amanha TEXT,
            status TEXT,
            produtividade INTEGER,
            observacoes TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos (id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
    ''')
    
    # Tabela de fotos
    c.execute('''
        CREATE TABLE IF NOT EXISTS fotos_obra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relatorio_id INTEGER NOT NULL,
            foto_path TEXT NOT NULL,
            descricao TEXT,
            data_upload DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (relatorio_id) REFERENCES relatorios_diarios (id)
        )
    ''')
    
    # Tabela de materiais
    c.execute('''
        CREATE TABLE IF NOT EXISTS materiais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            material TEXT NOT NULL,
            quantidade REAL,
            unidade TEXT,
            custo_unitario REAL,
            data_entrada DATE,
            fornecedor TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos (id)
        )
    ''')
    
    # Tabela de custos
    c.execute('''
        CREATE TABLE IF NOT EXISTS custos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT,
            valor REAL NOT NULL,
            data DATE,
            comprovante_path TEXT,
            FOREIGN KEY (projeto_id) REFERENCES projetos (id)
        )
    ''')
    
    # Tabela de alertas
    c.execute('''
        CREATE TABLE IF NOT EXISTS alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            lido INTEGER DEFAULT 0,
            FOREIGN KEY (projeto_id) REFERENCES projetos (id)
        )
    ''')
    
    # Inserir usuÃ¡rios padrÃ£o se a tabela estiver vazia
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ('fiscal', 'Gildo JosÃ© Cossa', 'fiscal@obra.com', 
             hashlib.sha256('fiscal123'.encode()).hexdigest(), 'fiscal', '+258841234567'),
            ('proprietario', 'Carlos Silva', 'proprietario@obra.com',
             hashlib.sha256('proprietario123'.encode()).hexdigest(), 'proprietario', '+258842345678'),
            ('financeiro', 'Maria Santos', 'financeiro@obra.com',
             hashlib.sha256('financeiro123'.encode()).hexdigest(), 'financeiro', '+258843456789'),
            ('admin', 'Administrador', 'admin@obra.com',
             hashlib.sha256('admin123'.encode()).hexdigest(), 'admin', '+258844567890')
        ]
        c.executemany('''
            INSERT INTO usuarios (username, nome, email, senha_hash, tipo, telefone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', usuarios_padrao)
    
    # Inserir projeto padrÃ£o
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, 
                                 data_inicio, data_fim_previsto, responsavel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('LBO XAI-XA - RequalificaÃ§Ã£o com ExpansÃ£o',
              'Projeto de requalificaÃ§Ã£o com expansÃ£o da estrutura existente',
              'Xai-Xai, Gaza', 2500000.00,
              '2025-02-01', '2025-08-01', 1))
    
    conn.commit()
    return conn

# Inicializar banco de dados
conn = init_database()

# ============================================
# SISTEMA DE AUTENTICAÃ‡ÃƒO
# ============================================

def verificar_login(username, password):
    """Verifica as credenciais do usuÃ¡rio"""
    c = conn.cursor()
    senha_hash = hashlib.sha256(password.encode()).hexdigest()
    
    c.execute('''
        SELECT id, username, nome, tipo FROM usuarios 
        WHERE username = ? AND senha_hash = ? AND ativo = 1
    ''', (username, senha_hash))
    
    return c.fetchone()

def criar_usuario(username, nome, email, password, tipo, telefone=""):
    """Cria um novo usuÃ¡rio"""
    try:
        c = conn.cursor()
        senha_hash = hashlib.sha256(password.encode()).hexdigest()
        
        c.execute('''
            INSERT INTO usuarios (username, nome, email, senha_hash, tipo, telefone)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, nome, email, senha_hash, tipo, telefone))
        
        conn.commit()
        return True
    except:
        return False

# ============================================
# FUNÃ‡Ã•ES DE GERENCIAMENTO DE PROJETOS
# ============================================

def obter_projetos():
    """ObtÃ©m todos os projetos"""
    c = conn.cursor()
    c.execute('''
        SELECT p.*, u.nome as responsavel_nome 
        FROM projetos p 
        LEFT JOIN usuarios u ON p.responsavel_id = u.id
        ORDER BY p.data_inicio DESC
    ''')
    return c.fetchall()

def obter_projeto_por_id(projeto_id):
    """ObtÃ©m um projeto especÃ­fico"""
    c = conn.cursor()
    c.execute('''
        SELECT p.*, u.nome as responsavel_nome 
        FROM projetos p 
        LEFT JOIN usuarios u ON p.responsavel_id = u.id
        WHERE p.id = ?
    ''', (projeto_id,))
    return c.fetchone()

def criar_projeto(nome, descricao, localizacao, orcamento, data_inicio, data_fim, responsavel_id):
    """Cria um novo projeto"""
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, 
                                 data_inicio, data_fim_previsto, responsavel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, descricao, localizacao, orcamento, data_inicio, data_fim, responsavel_id))
        
        projeto_id = c.lastrowid
        conn.commit()
        
        # Criar alerta de novo projeto
        criar_alerta(projeto_id, 'info', f'Novo projeto criado: {nome}')
        
        return projeto_id
    except:
        return None

# ============================================
# FUNÃ‡Ã•ES DE RELATÃ“RIOS DIÃRIOS
# ============================================

def salvar_relatorio(data, projeto_id, usuario_id, **dados):
    """Salva um relatÃ³rio diÃ¡rio"""
    try:
        c = conn.cursor()
        
        # Verificar se jÃ¡ existe relatÃ³rio para esta data e projeto
        c.execute('''
            SELECT id FROM relatorios_diarios 
            WHERE data = ? AND projeto_id = ?
        ''', (data, projeto_id))
        
        relatorio_existente = c.fetchone()
        
        if relatorio_existente:
            # Atualizar relatÃ³rio existente
            c.execute('''
                UPDATE relatorios_diarios 
                SET temperatura = ?, atividades = ?, equipe = ?, equipamentos = ?,
                    ocorrencias = ?, acidentes = ?, plano_amanha = ?, status = ?,
                    produtividade = ?, observacoes = ?
                WHERE id = ?
            ''', (dados.get('temperatura'), dados.get('atividades'), dados.get('equipe'),
                  dados.get('equipamentos'), dados.get('ocorrencias'), dados.get('acidentes'),
                  dados.get('plano_amanha'), dados.get('status'), dados.get('produtividade'),
                  dados.get('observacoes'), relatorio_existente[0]))
            
            relatorio_id = relatorio_existente[0]
        else:
            # Inserir novo relatÃ³rio
            c.execute('''
                INSERT INTO relatorios_diarios 
                (data, projeto_id, usuario_id, temperatura, atividades, equipe, 
                 equipamentos, ocorrencias, acidentes, plano_amanha, status, 
                 produtividade, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (data, projeto_id, usuario_id, dados.get('temperatura'), 
                  dados.get('atividades'), dados.get('equipe'), dados.get('equipamentos'),
                  dados.get('ocorrencias'), dados.get('acidentes'), dados.get('plano_amanha'),
                  dados.get('status'), dados.get('produtividade'), dados.get('observacoes')))
            
            relatorio_id = c.lastrowid
        
        conn.commit()
        
        # Verificar se precisa criar alertas
        if dados.get('acidentes') != 'Nenhum' and dados.get('acidentes'):
            criar_alerta(projeto_id, 'emergencia', 
                        f'Acidente reportado no dia {data}. Verificar relatÃ³rio.')
        
        if dados.get('produtividade', 100) < 60:
            criar_alerta(projeto_id, 'aviso', 
                        f'Baixa produtividade ({dados.get("produtividade")}%) no dia {data}')
        
        return relatorio_id
    except Exception as e:
        st.error(f"Erro ao salvar relatÃ³rio: {str(e)}")
        return None

def obter_relatorios(projeto_id=None, data_inicio=None, data_fim=None):
    """ObtÃ©m relatÃ³rios com filtros"""
    c = conn.cursor()
    
    query = '''
        SELECT r.*, p.nome as projeto_nome, u.nome as usuario_nome 
        FROM relatorios_diarios r
        JOIN projetos p ON r.projeto_id = p.id
        JOIN usuarios u ON r.usuario_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if projeto_id:
        query += " AND r.projeto_id = ?"
        params.append(projeto_id)
    
    if data_inicio:
        query += " AND r.data >= ?"
        params.append(data_inicio)
    
    if data_fim:
        query += " AND r.data <= ?"
        params.append(data_fim)
    
    query += " ORDER BY r.data DESC"
    
    c.execute(query, params)
    return c.fetchall()

# ============================================
# GERENCIAMENTO DE FOTOS
# ============================================

def salvar_foto(relatorio_id, foto_bytes, descricao=""):
    """Salva uma foto no sistema de arquivos e registra no banco"""
    try:
        # Criar diretÃ³rio para fotos se nÃ£o existir
        os.makedirs('fotos_obra', exist_ok=True)
        
        # Gerar nome Ãºnico para o arquivo
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"foto_{relatorio_id}_{timestamp}.jpg"
        filepath = os.path.join('fotos_obra', filename)
        
        # Salvar arquivo
        with open(filepath, 'wb') as f:
            f.write(foto_bytes)
        
        # Registrar no banco
        c = conn.cursor()
        c.execute('''
            INSERT INTO fotos_obra (relatorio_id, foto_path, descricao)
            VALUES (?, ?, ?)
        ''', (relatorio_id, filepath, descricao))
        
        conn.commit()
        return True
    except:
        return False

def obter_fotos(relatorio_id):
    """ObtÃ©m todas as fotos de um relatÃ³rio"""
    c = conn.cursor()
    c.execute('''
        SELECT * FROM fotos_obra 
        WHERE relatorio_id = ? 
        ORDER BY data_upload DESC
    ''', (relatorio_id,))
    return c.fetchall()

# ============================================
# SISTEMA DE ALERTAS
# ============================================

def criar_alerta(projeto_id, tipo, mensagem):
    """Cria um novo alerta"""
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO alertas (projeto_id, tipo, mensagem)
            VALUES (?, ?, ?)
        ''', (projeto_id, tipo, mensagem))
        
        conn.commit()
        
        # Enviar notificaÃ§Ã£o por email (se configurado)
        enviar_email_alerta(projeto_id, tipo, mensagem)
        
        # Enviar notificaÃ§Ã£o por WhatsApp (se configurado)
        enviar_whatsapp_alerta(projeto_id, tipo, mensagem)
        
        return True
    except:
        return False

def obter_alertas(projeto_id=None, nao_lidos=False):
    """ObtÃ©m alertas com filtros"""
    c = conn.cursor()
    
    query = '''
        SELECT a.*, p.nome as projeto_nome 
        FROM alertas a
        JOIN projetos p ON a.projeto_id = p.id
        WHERE 1=1
    '''
    params = []
    
    if projeto_id:
        query += " AND a.projeto_id = ?"
        params.append(projeto_id)
    
    if nao_lidos:
        query += " AND a.lido = 0"
    
    query += " ORDER BY a.data_criacao DESC"
    
    c.execute(query, params)
    return c.fetchall()

def marcar_alerta_como_lido(alerta_id):
    """Marca um alerta como lido"""
    c = conn.cursor()
    c.execute('UPDATE alertas SET lido = 1 WHERE id = ?', (alerta_id,))
    conn.commit()

# ============================================
# INTEGRAÃ‡ÃƒO COM EMAIL
# ============================================

def enviar_email_alerta(projeto_id, tipo, mensagem):
    """Envia alerta por email"""
    # ConfiguraÃ§Ãµes de email (substituir com suas configuraÃ§Ãµes)
    config_email = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'email_from': 'seu_email@gmail.com',
        'senha': 'sua_senha',
        'emails_to': ['proprietario@obra.com', 'gerente@obra.com']
    }
    
    try:
        # Verificar se as configuraÃ§Ãµes estÃ£o definidas
        if config_email['email_from'] == 'seu_email@gmail.com':
            return False  # ConfiguraÃ§Ã£o nÃ£o definida
        
        projeto = obter_projeto_por_id(projeto_id)
        
        msg = MIMEMultipart()
        msg['From'] = config_email['email_from']
        msg['To'] = ', '.join(config_email['emails_to'])
        msg['Subject'] = f'ALERTA [{tipo.upper()}] - Projeto: {projeto[1]}'
        
        corpo = f'''
        <h2>Alerta do Sistema de Controle de Obra</h2>
        <p><strong>Projeto:</strong> {projeto[1]}</p>
        <p><strong>Tipo:</strong> {tipo}</p>
        <p><strong>Mensagem:</strong> {mensagem}</p>
        <p><strong>Data:</strong> {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}</p>
        <br>
        <p>Acesse o dashboard: http://localhost:8501</p>
        '''
        
        msg.attach(MIMEText(corpo, 'html'))
        
        server = smtplib.SMTP(config_email['smtp_server'], config_email['smtp_port'])
        server.starttls()
        server.login(config_email['email_from'], config_email['senha'])
        server.send_message(msg)
        server.quit()
        
        return True
    except:
        return False

# ============================================
# INTEGRAÃ‡ÃƒO COM WHATSAPP (TWILIO)
# ============================================

def enviar_whatsapp_alerta(projeto_id, tipo, mensagem):
    """Envia alerta por WhatsApp usando Twilio"""
    # ConfiguraÃ§Ãµes Twilio (substituir com suas credenciais)
    config_whatsapp = {
        'account_sid': 'sua_account_sid',
        'auth_token': 'seu_auth_token',
        'from_number': 'whatsapp:+14155238886',
        'to_numbers': ['whatsapp:+258841234567', 'whatsapp:+258842345678']
    }
    
    try:
        if config_whatsapp['account_sid'] == 'sua_account_sid':
            return False  # ConfiguraÃ§Ã£o nÃ£o definida
        
        projeto = obter_projeto_por_id(projeto_id)
        
        client = Client(config_whatsapp['account_sid'], config_whatsapp['auth_token'])
        
        for to_number in config_whatsapp['to_numbers']:
            message = client.messages.create(
                body=f'ðŸš¨ ALERTA [{tipo}] - {projeto[1]}\n{mensagem}',
                from_=config_whatsapp['from_number'],
                to=to_number
            )
        
        return True
    except:
        return False

# ============================================
# GERADOR DE RELATÃ“RIOS PDF
# ============================================

def gerar_relatorio_pdf(relatorio_id):
    """Gera um relatÃ³rio em PDF"""
    try:
        # Obter dados do relatÃ³rio
        c = conn.cursor()
        c.execute('''
            SELECT r.*, p.nome as projeto_nome, u.nome as usuario_nome 
            FROM relatorios_diarios r
            JOIN projetos p ON r.projeto_id = p.id
            JOIN usuarios u ON r.usuario_id = u.id
            WHERE r.id = ?
        ''', (relatorio_id,))
        
        relatorio = c.fetchone()
        
        if not relatorio:
            return None
            
        # Criar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            textColor=colors.HexColor('#1E3A8A')
        )
        
        # TÃ­tulo
        elements.append(Paragraph(f"RelatÃ³rio DiÃ¡rio de Obra", title_style))
        
        # InformaÃ§Ãµes bÃ¡sicas - ÃNDICES CORRIGIDOS
        # Colunas: 0:id, 1:data, 2:projeto_id, 3:usuario_id, 4:temperatura, 5:atividades,
        # 6:equipe, 7:equipamentos, 8:ocorrencias, 9:acidentes, 10:plano_amanha,
        # 11:status, 12:produtividade, 13:observacoes, 14:projeto_nome, 15:usuario_nome
        info_data = [
            ["Data:", relatorio[1]],
            ["Projeto:", relatorio[14]],  # projeto_nome
            ["ResponsÃ¡vel:", relatorio[15]],  # usuario_nome
            ["Status:", relatorio[11]],
            ["Produtividade:", f"{relatorio[12]}%"]
        ]
        
        info_table = Table(info_data, colWidths=[100, 300])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F3F4F6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4B5563')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        # SeÃ§Ãµes do relatÃ³rio - ÃNDICES CORRIGIDOS
        secoes = [
            ("CondiÃ§Ãµes ClimÃ¡ticas", relatorio[4]),  # temperatura
            ("Atividades Realizadas", relatorio[5]),  # atividades
            ("Equipe Presente", relatorio[6]),  # equipe
            ("Equipamentos Utilizados", relatorio[7]),  # equipamentos
            ("OcorrÃªncias", relatorio[8]),  # ocorrencias
            ("Acidentes", relatorio[9]),  # acidentes
            ("Plano para AmanhÃ£", relatorio[10]),  # plano_amanha
            ("ObservaÃ§Ãµes", relatorio[13])  # observacoes
        ]
        
        for titulo, conteudo in secoes:
            if conteudo:
                elements.append(Paragraph(f"<b>{titulo}:</b>", styles['Heading2']))
                elements.append(Paragraph(conteudo, styles['Normal']))
                elements.append(Spacer(1, 10))
        
        # Construir PDF
        doc.build(elements)
        
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar PDF: {str(e)}")
        return None

def gerar_relatorio_mensal_pdf(projeto_id, mes, ano):
    """Gera relatÃ³rio mensal em PDF"""
    try:
        # Obter dados do mÃªs
        data_inicio = f"{ano}-{mes:02d}-01"
        if mes == 12:
            data_fim = f"{ano+1}-01-01"
        else:
            data_fim = f"{ano}-{mes+1:02d}-01"
        
        relatorios = obter_relatorios(projeto_id, data_inicio, data_fim)
        projeto = obter_projeto_por_id(projeto_id)
        
        if not projeto:
            return None
            
        # Criar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # TÃ­tulo
        elements.append(Paragraph(f"RelatÃ³rio Mensal de Obra", styles['Heading1']))
        elements.append(Paragraph(f"Projeto: {projeto[1]}", styles['Heading2']))
        elements.append(Paragraph(f"MÃªs: {mes:02d}/{ano}", styles['Heading2']))
        elements.append(Spacer(1, 30))
        
        # MÃ©tricas
        dias_trabalhados = len(relatorios)
        if relatorios:
            produtividade_media = np.mean([r[12] for r in relatorios])
        else:
            produtividade_media = 0
        dias_concluidos = len([r for r in relatorios if r[11] == 'ConcluÃ­do'])
        
        metricas_data = [
            ["Dias Trabalhados:", dias_trabalhados],
            ["Dias ConcluÃ­dos:", dias_concluidos],
            ["Produtividade MÃ©dia:", f"{produtividade_media:.1f}%"],
            ["Dias sem Acidente:", len([r for r in relatorios if r[9] == 'Nenhum'])]
        ]
        
        metricas_table = Table(metricas_data)
        metricas_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#EFF6FF')),
        ]))
        
        elements.append(metricas_table)
        elements.append(Spacer(1, 30))
        
        # Tabela de relatÃ³rios
        if relatorios:
            tabela_data = [["Data", "Atividades", "Status", "Produtividade", "Acidentes"]]
            
            for rel in relatorios:
                atividades = rel[5]
                if len(atividades) > 50:
                    atividades = atividades[:50] + "..."
                tabela_data.append([
                    rel[1],
                    atividades,
                    rel[11],
                    f"{rel[12]}%",
                    "Sim" if rel[9] != 'Nenhum' else "NÃ£o"
                ])
            
            tabela = Table(tabela_data, colWidths=[60, 200, 60, 70, 60])
            tabela.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F9FAFB')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            
            elements.append(tabela)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Erro ao gerar relatÃ³rio mensal: {str(e)}")
        return None

# ============================================
# INTERFACE DO USUÃRIO
# ============================================

# Tela de login
def tela_login():
    """Exibe a tela de login"""
    st.markdown('<h1 class="main-header">ðŸ—ï¸ Dashboard de Controle de Obra</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("UsuÃ¡rio")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                usuario = verificar_login(username, password)
                if usuario:
                    st.session_state.usuario = {
                        'id': usuario[0],
                        'username': usuario[1],
                        'nome': usuario[2],
                        'tipo': usuario[3]
                    }
                    st.success(f"Bem-vindo, {usuario[2]}!")
                    st.rerun()
                else:
                    st.error("UsuÃ¡rio ou senha incorretos")

# Menu principal
def exibir_menu_principal():
    """Exibe o menu principal baseado no tipo de usuÃ¡rio"""
    usuario = st.session_state.usuario
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
        st.title(f"OlÃ¡, {usuario['nome'].split()[0]}")
        st.caption(f"Tipo: {usuario['tipo'].title()}")
        
        # Menu baseado no tipo de usuÃ¡rio
        if usuario['tipo'] == 'admin':
            opcoes = ["ðŸ“Š Dashboard", "ðŸ“ Registrar RelatÃ³rio", "ðŸ‘¥ Gerenciar UsuÃ¡rios", 
                     "ðŸ—ï¸ Gerenciar Projetos", "ðŸ“¸ Galeria de Fotos", "ðŸš¨ Alertas", 
                     "ðŸ“ˆ RelatÃ³rios", "âš™ï¸ ConfiguraÃ§Ãµes"]
        elif usuario['tipo'] == 'fiscal':
            opcoes = ["ðŸ“Š Dashboard", "ðŸ“ Registrar RelatÃ³rio", "ðŸ“¸ Enviar Fotos", 
                     "ðŸš¨ Alertas", "ðŸ“ˆ Meus RelatÃ³rios"]
        elif usuario['tipo'] == 'proprietario':
            opcoes = ["ðŸ“Š Dashboard", "ðŸ‘ï¸ Visualizar RelatÃ³rios", "ðŸ“¸ Galeria de Fotos", 
                     "ðŸš¨ Alertas", "ðŸ“ˆ RelatÃ³rios Financeiros"]
        else:  # financeiro
            opcoes = ["ðŸ“Š Dashboard", "ðŸ’° Controle Financeiro", "ðŸ“ˆ RelatÃ³rios", 
                     "ðŸš¨ Alertas Financeiros"]
        
        pagina = st.radio("NavegaÃ§Ã£o", opcoes)
        
        st.markdown("---")
        
        # Filtros comuns
        st.subheader("Filtros")
        projetos = obter_projetos()
        projeto_opcoes = {p[0]: p[1] for p in projetos}
        projeto_selecionado = st.selectbox(
            "Projeto",
            list(projeto_opcoes.keys()),
            format_func=lambda x: projeto_opcoes[x],
            index=0 if projetos else None
        )
        
        data_inicio = st.date_input("Data inicial", value=date.today() - timedelta(days=30))
        data_fim = st.date_input("Data final", value=date.today())
        
        st.markdown("---")
        
        if st.button("ðŸšª Sair"):
            del st.session_state.usuario
            st.rerun()
        
        st.caption(f"VersÃ£o 2.0 | {date.today().strftime('%d/%m/%Y')}")
    
    # Armazenar filtros na sessÃ£o
    st.session_state.filtros = {
        'projeto_id': projeto_selecionado,
        'data_inicio': data_inicio,
        'data_fim': data_fim
    }
    
    # Exibir pÃ¡gina selecionada
    if "Dashboard" in pagina:
        exibir_dashboard(usuario)
    elif "Registrar RelatÃ³rio" in pagina:
        exibir_formulario_relatorio(usuario)
    elif "Enviar Fotos" in pagina or "Galeria de Fotos" in pagina:
        exibir_galeria_fotos()
    elif "Alertas" in pagina:
        exibir_alertas()
    elif "Gerenciar UsuÃ¡rios" in pagina:
        exibir_gerenciamento_usuarios()
    elif "Gerenciar Projetos" in pagina:
        exibir_gerenciamento_projetos()
    elif "RelatÃ³rios" in pagina:
        exibir_relatorios_avancados()
    elif "Controle Financeiro" in pagina:
        exibir_controle_financeiro()
    elif "ConfiguraÃ§Ãµes" in pagina:
        exibir_configuracoes()
    elif "Visualizar RelatÃ³rios" in pagina or "Meus RelatÃ³rios" in pagina:
        exibir_relatorios_lista()
    elif "RelatÃ³rios Financeiros" in pagina:
        exibir_relatorios_financeiros()

# ============================================
# PÃGINAS DA APLICAÃ‡ÃƒO
# ============================================

def exibir_dashboard(usuario):
    """Exibe o dashboard principal"""
    st.markdown(f'<h2 class="sub-header">ðŸ“Š Dashboard - VisÃ£o Geral</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    
    # MÃ©tricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Obter dados do projeto
        projeto = obter_projeto_por_id(filtros['projeto_id'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        if projeto:
            st.metric("Projeto", projeto[1])
            st.caption(f"OrÃ§amento: MZN {projeto[4]:,.2f}")
        else:
            st.metric("Projeto", "NÃ£o encontrado")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        # Dias trabalhados no perÃ­odo
        relatorios = obter_relatorios(filtros['projeto_id'], filtros['data_inicio'], filtros['data_fim'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Dias Trabalhados", len(relatorios))
        dias_concluidos = len([r for r in relatorios if r[11] == 'ConcluÃ­do'])
        st.caption(f"ConcluÃ­dos: {dias_concluidos}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        # Produtividade mÃ©dia
        if relatorios:
            produtividade_media = np.mean([r[12] for r in relatorios])
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Produtividade MÃ©dia", f"{produtividade_media:.1f}%")
            status = "ðŸ‘ Boa" if produtividade_media >= 80 else "âš ï¸ MÃ©dia" if produtividade_media >= 60 else "ðŸ‘Ž Baixa"
            st.caption(status)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.metric("Produtividade MÃ©dia", "0%")
            st.caption("Sem dados")
            st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        # Alertas nÃ£o lidos
        alertas = obter_alertas(filtros['projeto_id'], nao_lidos=True)
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Alertas Ativos", len(alertas))
        if alertas:
            st.caption(f"âš ï¸ {len([a for a in alertas if a[2] == 'emergencia'])} urgentes")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # GrÃ¡ficos
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if relatorios and len(relatorios) > 0:
            # Criar DataFrame com Ã­ndices corrigidos
            data_list = []
            for rel in relatorios:
                data_list.append({
                    'id': rel[0],
                    'data': rel[1],
                    'projeto_id': rel[2],
                    'usuario_id': rel[3],
                    'temperatura': rel[4],
                    'atividades': rel[5],
                    'equipe': rel[6],
                    'equipamentos': rel[7],
                    'ocorrencias': rel[8],
                    'acidentes': rel[9],
                    'plano_amanha': rel[10],
                    'status': rel[11],
                    'produtividade': rel[12],
                    'observacoes': rel[13],
                    'projeto_nome': rel[14],
                    'usuario_nome': rel[15]
                })
            
            df = pd.DataFrame(data_list)
            df['data'] = pd.to_datetime(df['data'])
            df = df.sort_values('data')
            
            fig = px.line(df, x='data', y='produtividade', title='Produtividade DiÃ¡ria',
                         markers=True, line_shape='linear')
            fig.update_layout(xaxis_title="Data", yaxis_title="Produtividade (%)",
                            hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes para grÃ¡fico de produtividade")
    
    with col_chart2:
        if relatorios and len(relatorios) > 0:
            data_list = []
            for rel in relatorios:
                data_list.append({
                    'status': rel[11]
                })
            
            df = pd.DataFrame(data_list)
            status_counts = df['status'].value_counts()
            fig = px.pie(values=status_counts.values, names=status_counts.index,
                        title='DistribuiÃ§Ã£o de Status', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados suficientes para grÃ¡fico de status")
    
    # Ãšltimos relatÃ³rios
    st.markdown('<h3 class="sub-header">ðŸ“… Ãšltimos RelatÃ³rios</h3>', unsafe_allow_html=True)
    
    if relatorios:
        for rel in relatorios[:5]:  # Mostrar apenas os 5 mais recentes
            # ÃNDICES CORRIGIDOS:
            # 0:id, 1:data, 2:projeto_id, 3:usuario_id, 4:temperatura, 5:atividades,
            # 6:equipe, 7:equipamentos, 8:ocorrencias, 9:acidentes, 10:plano_amanha,
            # 11:status, 12:produtividade, 13:observacoes, 14:projeto_nome, 15:usuario_nome
            
            with st.expander(f"ðŸ“‹ {rel[1]} - {rel[14]} - {rel[11]}"):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**ResponsÃ¡vel:** {rel[15]}")  # usuario_nome
                    st.write(f"**Produtividade:** {rel[12]}%")
                    st.write(f"**Equipe:** {rel[6]}")
                with col_info2:
                    st.write(f"**Equipamentos:** {rel[7]}")
                    st.write(f"**Acidentes:** {rel[9]}")
                    st.write(f"**Clima:** {rel[4]}")
                
                st.write("**Atividades:**")
                st.info(rel[5])
                
                if rel[8] and rel[8] != 'Nenhuma':
                    st.write("**OcorrÃªncias:**")
                    st.warning(rel[8])
                
                # BotÃµes de aÃ§Ã£o
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    if st.button("ðŸ“„ Gerar PDF", key=f"pdf_{rel[0]}"):
                        pdf = gerar_relatorio_pdf(rel[0])
                        if pdf:
                            st.download_button(
                                label="â¬‡ï¸ Baixar PDF",
                                data=pdf,
                                file_name=f"relatorio_{rel[1]}_{rel[0]}.pdf",
                                mime="application/pdf",
                                key=f"download_pdf_{rel[0]}"
                            )
                
                with col_btn2:
                    if st.button("ðŸ“¸ Ver Fotos", key=f"fotos_{rel[0]}"):
                        st.session_state.ver_fotos_relatorio = rel[0]
                        st.rerun()
                
                with col_btn3:
                    if st.button("ðŸ“± Enviar WhatsApp", key=f"whatsapp_{rel[0]}"):
                        projeto_nome = rel[14]
                        mensagem = f"RelatÃ³rio {rel[1]} - {projeto_nome}\nStatus: {rel[11]}\nProdutividade: {rel[12]}%"
                        enviar_whatsapp_alerta(filtros['projeto_id'], 'info', mensagem)
                        st.success("Mensagem enviada para WhatsApp!")
    else:
        st.info("Nenhum relatÃ³rio encontrado para o perÃ­odo selecionado.")

def exibir_formulario_relatorio(usuario):
    """Exibe o formulÃ¡rio para registrar relatÃ³rio diÃ¡rio"""
    st.markdown('<h2 class="sub-header">ðŸ“ Registrar RelatÃ³rio DiÃ¡rio</h2>', unsafe_allow_html=True)
    
    with st.form("form_relatorio_detalhado", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            data_relatorio = st.date_input("Data do relatÃ³rio", value=date.today())
            projetos = obter_projetos()
            projeto_opcoes = {p[0]: p[1] for p in projetos}
            projeto_id = st.selectbox(
                "Projeto",
                list(projeto_opcoes.keys()),
                format_func=lambda x: projeto_opcoes[x]
            )
            temperatura = st.text_input("CondiÃ§Ãµes climÃ¡ticas", 
                                       placeholder="Ex: CÃ©u parcialmente nublado com perÃ­odos de chuva")
            status = st.selectbox("Status do dia", 
                                 ["ConcluÃ­do", "Em andamento", "Atrasado", "Paralisado"])
            produtividade = st.slider("Produtividade (%)", 0, 100, 85, 
                                     help="AvaliaÃ§Ã£o da produtividade do dia")
        
        with col2:
            mestre = st.number_input("NÂº de Mestres", min_value=0, value=1)
            motoristas = st.number_input("NÂº de Motoristas", min_value=0, value=1)
            subordinados = st.number_input("NÂº de Subordinados", min_value=0, value=6)
            encarregado = st.checkbox("Encarregado presente", value=True)
            fiscal = st.checkbox("Fiscal presente", value=True)
            
            # Montar string da equipe
            equipe = f"{mestre} mestre(s), {motoristas} motorista(s), {subordinados} subordinado(s)"
            if encarregado:
                equipe += ", encarregado"
            if fiscal:
                equipe += ", fiscal"
        
        # Atividades
        st.subheader("Atividades Realizadas")
        atividades = st.text_area(
            "Descreva detalhadamente as atividades realizadas:",
            placeholder="Ex: ProduÃ§Ã£o de betÃ£o classe B25 com traÃ§o (1;2;3), betonagem das sapatas...",
            height=120
        )
        
        # Equipamentos
        st.subheader("Equipamentos Utilizados")
        equipamentos = st.text_area(
            "Equipamentos utilizados:",
            placeholder="Ex: Betoneira, caminhÃ£o betoneira, vibrador de concreto...",
            height=80
        )
        
        # OcorrÃªncias
        st.subheader("OcorrÃªncias do Dia")
        ocorrencias = st.text_area(
            "Descreva as ocorrÃªncias (positivas ou negativas):",
            placeholder="Ex: Avaria da betoneira, entrada de areia grossa, descarregamento de materiais...",
            height=100
        )
        
        # Acidentes
        st.subheader("SeguranÃ§a do Trabalho")
        ocorreu_acidente = st.checkbox("Ocorreu acidente?")
        acidentes = "Nenhum"
        if ocorreu_acidente:
            acidentes = st.text_area(
                "Descreva o(s) acidente(s) ocorrido(s):",
                placeholder="Descreva detalhadamente: tipo de acidente, pessoas envolvidas, primeiros socorros...",
                height=100
            )
        
        # Plano para amanhÃ£
        st.subheader("Plano para o PrÃ³ximo Dia")
        plano_amanha = st.text_area(
            "Atividades planejadas para amanhÃ£:",
            placeholder="Ex: ProduÃ§Ã£o e lanÃ§amento de betÃ£o de limpeza, verificaÃ§Ã£o de nÃ­vel...",
            height=100
        )
        
        # ObservaÃ§Ãµes adicionais
        observacoes = st.text_area("ObservaÃ§Ãµes adicionais:", height=80)
        
        # Upload de fotos
        st.subheader("ðŸ“¸ Anexar Fotos do Dia")
        fotos = st.file_uploader("Selecione fotos da obra", 
                                type=['jpg', 'jpeg', 'png'],
                                accept_multiple_files=True)
        
        descricoes_fotos = []
        if fotos:
            st.write(f"{len(fotos)} foto(s) selecionada(s)")
            for i, foto in enumerate(fotos):
                col_foto1, col_foto2 = st.columns([2, 3])
                with col_foto1:
                    st.image(foto, caption=f"Foto {i+1}", width=150)
                with col_foto2:
                    descricao = st.text_input(f"DescriÃ§Ã£o da foto {i+1}", 
                                            key=f"desc_{i}")
                    descricoes_fotos.append(descricao)
        
        submitted = st.form_submit_button("ðŸ’¾ Salvar RelatÃ³rio")
        
        if submitted:
            if not atividades:
                st.error("Por favor, descreva as atividades realizadas.")
            else:
                # Salvar relatÃ³rio
                dados = {
                    'temperatura': temperatura,
                    'atividades': atividades,
                    'equipe': equipe,
                    'equipamentos': equipamentos,
                    'ocorrencias': ocorrencias,
                    'acidentes': acidentes,
                    'plano_amanha': plano_amanha,
                    'status': status,
                    'produtividade': produtividade,
                    'observacoes': observacoes
                }
                
                relatorio_id = salvar_relatorio(
                    data_relatorio, projeto_id, usuario['id'], **dados
                )
                
                if relatorio_id:
                    st.success(f"âœ… RelatÃ³rio salvo com sucesso! ID: {relatorio_id}")
                    
                    # Salvar fotos
                    if fotos:
                        for i, foto in enumerate(fotos):
                            salvar_foto(relatorio_id, foto.getvalue(), 
                                       descricoes_fotos[i] if i < len(descricoes_fotos) else "")
                        st.success(f"âœ… {len(fotos)} foto(s) salva(s)")
                    
                    # Gerar PDF automaticamente
                    with st.spinner("Gerando PDF..."):
                        pdf = gerar_relatorio_pdf(relatorio_id)
                        if pdf:
                            st.download_button(
                                label="â¬‡ï¸ Baixar RelatÃ³rio em PDF",
                                data=pdf,
                                file_name=f"relatorio_{data_relatorio}.pdf",
                                mime="application/pdf",
                                key="download_relatorio_pdf"
                            )
                    st.rerun()

def exibir_galeria_fotos():
    """Exibe a galeria de fotos da obra"""
    st.markdown('<h2 class="sub-header">ðŸ“¸ Galeria de Fotos da Obra</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    
    # Verificar se estamos visualizando fotos de um relatÃ³rio especÃ­fico
    if 'ver_fotos_relatorio' in st.session_state:
        relatorio_id = st.session_state.ver_fotos_relatorio
        fotos = obter_fotos(relatorio_id)
        
        st.subheader(f"Fotos do RelatÃ³rio {relatorio_id}")
        
        if fotos:
            cols = st.columns(3)
            for idx, foto in enumerate(fotos):
                with cols[idx % 3]:
                    try:
                        if os.path.exists(foto[2]):
                            with open(foto[2], 'rb') as f:
                                img_bytes = f.read()
                            st.image(img_bytes, caption=foto[3] or f"Foto {idx+1}")
                            st.caption(f"Upload: {foto[4]}")
                        else:
                            st.warning(f"Arquivo nÃ£o encontrado: {foto[2]}")
                    except Exception as e:
                        st.error(f"Erro ao carregar foto: {str(e)}")
        else:
            st.info("Nenhuma foto encontrada para este relatÃ³rio.")
        
        if st.button("â† Voltar para Galeria Geral"):
            del st.session_state.ver_fotos_relatorio
            st.rerun()
        
        return
    
    # Galeria geral
    # Obter relatÃ³rios com fotos
    relatorios = obter_relatorios(filtros['projeto_id'], 
                                 filtros['data_inicio'], 
                                 filtros['data_fim'])
    
    if not relatorios:
        st.info("Nenhum relatÃ³rio encontrado.")
        return
    
    # Organizar fotos por data
    fotos_por_data = {}
    
    for rel in relatorios:
        fotos_rel = obter_fotos(rel[0])
        if fotos_rel:
            fotos_por_data[rel[1]] = {
                'relatorio': rel,
                'fotos': fotos_rel
            }
    
    if not fotos_por_data:
        st.info("Nenhuma foto encontrada para o perÃ­odo selecionado.")
        return
    
    # Exibir fotos
    for data_str, dados in sorted(fotos_por_data.items(), reverse=True):
        with st.expander(f"ðŸ“… {data_str} - {len(dados['fotos'])} foto(s)"):
            st.write(f"**Atividades:** {dados['relatorio'][5][:100]}...")
            
            cols = st.columns(4)
            for idx, foto in enumerate(dados['fotos'][:8]):  # Limitar a 8 fotos por expansor
                with cols[idx % 4]:
                    try:
                        if os.path.exists(foto[2]):
                            with open(foto[2], 'rb') as f:
                                img_bytes = f.read()
                            st.image(img_bytes, use_column_width=True)
                        else:
                            st.warning("Arquivo nÃ£o encontrado")
                    except:
                        st.error("Erro ao carregar imagem")
            
            if len(dados['fotos']) > 8:
                st.info(f"... e mais {len(dados['fotos']) - 8} foto(s)")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("ðŸ‘ï¸ Ver Todas", key=f"ver_todas_{data_str}"):
                    st.session_state.ver_fotos_relatorio = dados['relatorio'][0]
                    st.rerun()
            with col2:
                # OpÃ§Ã£o para baixar fotos
                if st.button("ðŸ“¥ Baixar Fotos", key=f"baixar_{data_str}"):
                    st.info("Funcionalidade de download em desenvolvimento")

def exibir_alertas():
    """Exibe os alertas do sistema"""
    st.markdown('<h2 class="sub-header">ðŸš¨ Sistema de Alertas</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    
    # Criar novo alerta (apenas para admin/fiscal)
    usuario = st.session_state.usuario
    if usuario['tipo'] in ['admin', 'fiscal']:
        with st.expander("âž• Criar Novo Alerta"):
            col1, col2 = st.columns(2)
            with col1:
                tipo = st.selectbox("Tipo de Alerta", 
                                   ["info", "aviso", "emergencia", "financeiro"])
            with col2:
                prioridade = st.select_slider("Prioridade", ["Baixa", "MÃ©dia", "Alta", "CrÃ­tica"])
            
            mensagem = st.text_area("Mensagem do Alerta", height=100)
            
            if st.button("Enviar Alerta"):
                if mensagem:
                    criar_alerta(filtros['projeto_id'], tipo, f"[{prioridade}] {mensagem}")
                    st.success("Alerta criado com sucesso!")
                    # Enviar notificaÃ§Ãµes
                    enviar_email_alerta(filtros['projeto_id'], tipo, mensagem)
                    enviar_whatsapp_alerta(filtros['projeto_id'], tipo, mensagem)
                    st.rerun()
    
    # Listar alertas
    alertas = obter_alertas(filtros['projeto_id'])
    
    if not alertas:
        st.info("Nenhum alerta encontrado.")
        return
    
    # Separar alertas nÃ£o lidos
    alertas_nao_lidos = [a for a in alertas if a[5] == 0]
    alertas_lidos = [a for a in alertas if a[5] == 1]
    
    # Alertas nÃ£o lidos
    if alertas_nao_lidos:
        st.subheader("âš ï¸ Alertas NÃ£o Lidos")
        for alerta in alertas_nao_lidos:
            cor = {
                'emergencia': '#EF4444',
                'aviso': '#F59E0B',
                'info': '#3B82F6',
                'financeiro': '#8B5CF6'
            }.get(alerta[2], '#6B7280')
            
            st.markdown(f"""
            <div style="border-left: 4px solid {cor}; padding: 1rem; margin: 0.5rem 0; 
                        background-color: #F9FAFB; border-radius: 0 8px 8px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>{alerta[2].upper()}</strong>
                    <small>{alerta[4]}</small>
                </div>
                <p style="margin: 0.5rem 0;">{alerta[3]}</p>
                <small>Projeto: {alerta[6]}</small>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("âœ… Marcar como Lido", key=f"ler_{alerta[0]}"):
                    marcar_alerta_como_lido(alerta[0])
                    st.rerun()
            with col2:
                if st.button("ðŸ“± Enviar WhatsApp", key=f"whats_{alerta[0]}"):
                    enviar_whatsapp_alerta(filtros['projeto_id'], alerta[2], alerta[3])
                    st.success("NotificaÃ§Ã£o enviada!")
            with col3:
                st.write("")  # EspaÃ§o vazio
    
    # Alertas lidos
    if alertas_lidos:
        with st.expander("ðŸ“š Alertas Lidos"):
            for alerta in alertas_lidos:
                st.info(f"**{alerta[2].upper()}** - {alerta[4]}\n{alerta[3]}")

def exibir_gerenciamento_usuarios():
    """Exibe a interface de gerenciamento de usuÃ¡rios"""
    st.markdown('<h2 class="sub-header">ðŸ‘¥ Gerenciamento de UsuÃ¡rios</h2>', unsafe_allow_html=True)
    
    # Abas para diferentes funcionalidades
    tab1, tab2, tab3 = st.tabs(["Lista de UsuÃ¡rios", "Criar Novo UsuÃ¡rio", "EstatÃ­sticas"])
    
    with tab1:
        # Listar usuÃ¡rios
        c = conn.cursor()
        c.execute('SELECT id, username, nome, email, tipo, telefone, ativo FROM usuarios')
        usuarios = c.fetchall()
        
        if usuarios:
            df = pd.DataFrame(usuarios, 
                            columns=['ID', 'UsuÃ¡rio', 'Nome', 'Email', 'Tipo', 'Telefone', 'Ativo'])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum usuÃ¡rio cadastrado.")
    
    with tab2:
        # FormulÃ¡rio para criar novo usuÃ¡rio
        with st.form("form_novo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Nome de usuÃ¡rio*")
                nome = st.text_input("Nome completo*")
                email = st.text_input("Email*")
            
            with col2:
                tipo = st.selectbox("Tipo de usuÃ¡rio*", 
                                   ['fiscal', 'proprietario', 'financeiro', 'admin'])
                telefone = st.text_input("Telefone")
                senha = st.text_input("Senha*", type="password")
                confirmar_senha = st.text_input("Confirmar senha*", type="password")
            
            st.caption("* Campos obrigatÃ³rios")
            
            if st.form_submit_button("Criar UsuÃ¡rio"):
                if not all([username, nome, email, senha]):
                    st.error("Preencha todos os campos obrigatÃ³rios.")
                elif senha != confirmar_senha:
                    st.error("As senhas nÃ£o coincidem.")
                else:
                    sucesso = criar_usuario(username, nome, email, senha, tipo, telefone)
                    if sucesso:
                        st.success(f"UsuÃ¡rio {username} criado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao criar usuÃ¡rio. Verifique se o usuÃ¡rio jÃ¡ existe.")
    
    with tab3:
        # EstatÃ­sticas de uso
        st.subheader("EstatÃ­sticas de Uso")
        
        c = conn.cursor()
        
        # Total de usuÃ¡rios por tipo
        c.execute('SELECT tipo, COUNT(*) FROM usuarios GROUP BY tipo')
        tipos = c.fetchall()
        
        if tipos:
            df_tipos = pd.DataFrame(tipos, columns=['Tipo', 'Quantidade'])
            fig = px.pie(df_tipos, values='Quantidade', names='Tipo', 
                        title='DistribuiÃ§Ã£o de UsuÃ¡rios por Tipo')
            st.plotly_chart(fig, use_container_width=True)
        
        # Atividade recente
        st.subheader("Atividade Recente")
        c.execute('''
            SELECT u.nome, COUNT(r.id) as total_relatorios 
            FROM usuarios u 
            LEFT JOIN relatorios_diarios r ON u.id = r.usuario_id 
            GROUP BY u.id 
            ORDER BY total_relatorios DESC
        ''')
        atividade = c.fetchall()
        
        if atividade:
            df_atividade = pd.DataFrame(atividade, columns=['UsuÃ¡rio', 'RelatÃ³rios'])
            st.dataframe(df_atividade, use_container_width=True)

def exibir_gerenciamento_projetos():
    """Exibe a interface de gerenciamento de projetos"""
    st.markdown('<h2 class="sub-header">ðŸ—ï¸ Gerenciamento de Projetos</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Lista de Projetos", "Criar Novo Projeto", "Detalhes"])
    
    with tab1:
        projetos = obter_projetos()
        
        if projetos:
            df = pd.DataFrame(projetos, 
                            columns=['ID', 'Nome', 'DescriÃ§Ã£o', 'LocalizaÃ§Ã£o', 'OrÃ§amento', 
                                    'InÃ­cio', 'Fim Previsto', 'Status', 'ResponsÃ¡vel ID', 
                                    'ResponsÃ¡vel Nome'])
            
            # Formatar colunas
            df['OrÃ§amento'] = df['OrÃ§amento'].apply(lambda x: f"MZN {x:,.2f}")
            df['InÃ­cio'] = pd.to_datetime(df['InÃ­cio']).dt.strftime('%d/%m/%Y')
            df['Fim Previsto'] = pd.to_datetime(df['Fim Previsto']).dt.strftime('%d/%m/%Y')
            
            st.dataframe(df[['ID', 'Nome', 'LocalizaÃ§Ã£o', 'OrÃ§amento', 'InÃ­cio', 'Status', 'ResponsÃ¡vel Nome']], 
                        use_container_width=True)
        else:
            st.info("Nenhum projeto cadastrado.")
    
    with tab2:
        with st.form("form_novo_projeto"):
            nome = st.text_input("Nome do Projeto*")
            descricao = st.text_area("DescriÃ§Ã£o")
            localizacao = st.text_input("LocalizaÃ§Ã£o*")
            orcamento = st.number_input("OrÃ§amento Total (MZN)*", min_value=0.0, step=1000.0)
            
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input("Data de InÃ­cio*", value=date.today())
            with col2:
                data_fim = st.date_input("Data Prevista de TÃ©rmino*", 
                                        value=date.today() + timedelta(days=180))
            
            # Selecionar responsÃ¡vel
            c = conn.cursor()
            c.execute("SELECT id, nome FROM usuarios WHERE tipo IN ('admin', 'fiscal')")
            responsaveis = c.fetchall()
            responsavel_opcoes = {r[0]: r[1] for r in responsaveis}
            
            responsavel_id = st.selectbox("ResponsÃ¡vel*", 
                                         list(responsavel_opcoes.keys()),
                                         format_func=lambda x: responsavel_opcoes[x])
            
            if st.form_submit_button("Criar Projeto"):
                if not all([nome, localizacao, orcamento]):
                    st.error("Preencha todos os campos obrigatÃ³rios.")
                else:
                    projeto_id = criar_projeto(nome, descricao, localizacao, orcamento,
                                              data_inicio, data_fim, responsavel_id)
                    if projeto_id:
                        st.success(f"Projeto '{nome}' criado com sucesso! ID: {projeto_id}")
                        st.rerun()
                    else:
                        st.error("Erro ao criar projeto.")
    
    with tab3:
        # Detalhes do projeto selecionado
        filtros = st.session_state.filtros
        projeto = obter_projeto_por_id(filtros['projeto_id'])
        
        if projeto:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Nome do Projeto", projeto[1])
                st.write(f"**DescriÃ§Ã£o:** {projeto[2]}")
                st.write(f"**LocalizaÃ§Ã£o:** {projeto[3]}")
                st.write(f"**ResponsÃ¡vel:** {projeto[9]}")
            
            with col2:
                st.metric("OrÃ§amento", f"MZN {projeto[4]:,.2f}")
                st.write(f"**InÃ­cio:** {projeto[5]}")
                st.write(f"**TÃ©rmino Previsto:** {projeto[6]}")
                st.write(f"**Status:** {projeto[7]}")
            
            # Progresso do projeto
            st.subheader("Progresso do Projeto")
            
            # Calcular dias passados e restantes
            try:
                data_inicio = datetime.datetime.strptime(projeto[5], '%Y-%m-%d').date()
                data_fim = datetime.datetime.strptime(projeto[6], '%Y-%m-%d').date()
                hoje = date.today()
                
                dias_totais = (data_fim - data_inicio).days
                dias_passados = (hoje - data_inicio).days
                dias_restantes = (data_fim - hoje).days
                
                if dias_totais > 0:
                    progresso = min(100, (dias_passados / dias_totais) * 100)
                    
                    col_prog1, col_prog2, col_prog3 = st.columns(3)
                    with col_prog1:
                        st.metric("Dias Passados", dias_passados)
                    with col_prog2:
                        st.metric("Dias Restantes", max(0, dias_restantes))
                    with col_prog3:
                        st.metric("Progresso", f"{progresso:.1f}%")
                    
                    st.progress(progresso / 100)
            except:
                st.warning("NÃ£o foi possÃ­vel calcular o progresso do projeto")

def exibir_relatorios_avancados():
    """Exibe relatÃ³rios avanÃ§ados e anÃ¡lises"""
    st.markdown('<h2 class="sub-header">ðŸ“ˆ RelatÃ³rios AvanÃ§ados</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    
    tab1, tab2, tab3, tab4 = st.tabs(["RelatÃ³rio Mensal", "AnÃ¡lise de Produtividade", 
                                      "RelatÃ³rio de SeguranÃ§a", "Exportar Dados"])
    
    with tab1:
        # RelatÃ³rio mensal
        st.subheader("RelatÃ³rio Mensal")
        
        col1, col2 = st.columns(2)
        with col1:
            ano = st.number_input("Ano", min_value=2020, max_value=2030, value=date.today().year)
        with col2:
            mes = st.number_input("MÃªs", min_value=1, max_value=12, value=date.today().month)
        
        if st.button("Gerar RelatÃ³rio Mensal"):
            with st.spinner("Gerando relatÃ³rio..."):
                pdf = gerar_relatorio_mensal_pdf(filtros['projeto_id'], mes, ano)
                if pdf:
                    st.download_button(
                        label="â¬‡ï¸ Baixar RelatÃ³rio Mensal PDF",
                        data=pdf,
                        file_name=f"relatorio_mensal_{mes:02d}_{ano}.pdf",
                        mime="application/pdf",
                        key="download_relatorio_mensal"
                    )
                else:
                    st.error("Erro ao gerar relatÃ³rio.")
    
    with tab2:
        # AnÃ¡lise de produtividade
        st.subheader("AnÃ¡lise de Produtividade")
        
        relatorios = obter_relatorios(filtros['projeto_id'], 
                                     filtros['data_inicio'], 
                                     filtros['data_fim'])
        
        if relatorios:
            # Criar DataFrame com Ã­ndices corrigidos
            data_list = []
            for rel in relatorios:
                data_list.append({
                    'id': rel[0],
                    'data': rel[1],
                    'projeto_id': rel[2],
                    'usuario_id': rel[3],
                    'temperatura': rel[4],
                    'atividades': rel[5],
                    'equipe': rel[6],
                    'equipamentos': rel[7],
                    'ocorrencias': rel[8],
                    'acidentes': rel[9],
                    'plano_amanha': rel[10],
                    'status': rel[11],
                    'produtividade': rel[12],
                    'observacoes': rel[13],
                    'projeto_nome': rel[14],
                    'usuario_nome': rel[15]
                })
            
            df = pd.DataFrame(data_list)
            
            # AnÃ¡lise por dia da semana
            df['data'] = pd.to_datetime(df['data'])
            df['dia_semana'] = df['data'].dt.day_name()
            df['mes'] = df['data'].dt.month
            
            # Ordenar dias da semana
            dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            df['dia_semana'] = pd.Categorical(df['dia_semana'], categories=dias_ordem, ordered=True)
            
            fig = px.box(df, x='dia_semana', y='produtividade', 
                        title='Produtividade por Dia da Semana')
            st.plotly_chart(fig, use_container_width=True)
            
            # CorrelaÃ§Ã£o com condiÃ§Ãµes climÃ¡ticas
            st.subheader("Produtividade vs CondiÃ§Ãµes ClimÃ¡ticas")
            
            # Agrupar por temperatura (simplificado)
            if len(df['temperatura'].unique()) < 10:  # Evitar muitos grupos
                df_clima = df.groupby('temperatura')['produtividade'].mean().reset_index()
                fig2 = px.bar(df_clima, x='temperatura', y='produtividade',
                             title='Produtividade MÃ©dia por CondiÃ§Ã£o ClimÃ¡tica')
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum relatÃ³rio encontrado para anÃ¡lise.")
    
    with tab3:
        # RelatÃ³rio de seguranÃ§a
        st.subheader("RelatÃ³rio de SeguranÃ§a do Trabalho")
        
        relatorios = obter_relatorios(filtros['projeto_id'], 
                                     filtros['data_inicio'], 
                                     filtros['data_fim'])
        
        if relatorios:
            dias_com_acidente = sum(1 for r in relatorios if r[9] != 'Nenhum')
            dias_totais = len(relatorios)
            taxa_acidente = (dias_com_acidente / dias_totais * 100) if dias_totais > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Dias com Acidente", dias_com_acidente)
            with col2:
                st.metric("Dias sem Acidente", dias_totais - dias_com_acidente)
            with col3:
                st.metric("Taxa de Acidente", f"{taxa_acidente:.1f}%")
            
            # Listar acidentes
            if dias_com_acidente > 0:
                st.subheader("Registro de Acidentes")
                for rel in relatorios:
                    if rel[9] != 'Nenhum':
                        with st.expander(f"Acidente em {rel[1]}"):
                            st.write(f"**DescriÃ§Ã£o:** {rel[9]}")
                            st.write(f"**ResponsÃ¡vel:** {rel[15]}")  # usuario_nome
                            st.write(f"**Atividades do dia:** {rel[5]}")
        else:
            st.info("Nenhum relatÃ³rio encontrado.")
    
    with tab4:
        # Exportar dados
        st.subheader("Exportar Dados")
        
        formato = st.selectbox("Formato de exportaÃ§Ã£o", 
                              ["CSV", "Excel", "JSON"])
        
        # Selecionar dados para exportar
        opcoes_dados = st.multiselect(
            "Selecione os dados para exportar",
            ["RelatÃ³rios DiÃ¡rios", "Projetos", "UsuÃ¡rios", "Fotos (metadados)", "Alertas"],
            default=["RelatÃ³rios DiÃ¡rios"]
        )
        
        if st.button("Exportar Dados"):
            with st.spinner("Preparando exportaÃ§Ã£o..."):
                dados_exportar = {}
                
                if "RelatÃ³rios DiÃ¡rios" in opcoes_dados:
                    relatorios = obter_relatorios(filtros['projeto_id'], 
                                                 filtros['data_inicio'], 
                                                 filtros['data_fim'])
                    if relatorios:
                        # Criar DataFrame com nomes de colunas
                        colunas = ['id', 'data', 'projeto_id', 'usuario_id', 'temperatura', 
                                  'atividades', 'equipe', 'equipamentos', 'ocorrencias', 
                                  'acidentes', 'plano_amanha', 'status', 'produtividade', 
                                  'observacoes', 'projeto_nome', 'usuario_nome']
                        df_relatorios = pd.DataFrame(relatorios, columns=colunas)
                        dados_exportar['relatorios'] = df_relatorios
                
                if "Projetos" in opcoes_dados:
                    projetos = obter_projetos()
                    if projetos:
                        colunas = ['id', 'nome', 'descricao', 'localizacao', 'orcamento_total',
                                  'data_inicio', 'data_fim_previsto', 'status', 'responsavel_id',
                                  'responsavel_nome']
                        df_projetos = pd.DataFrame(projetos, columns=colunas)
                        dados_exportar['projetos'] = df_projetos
                
                if "UsuÃ¡rios" in opcoes_dados:
                    c = conn.cursor()
                    c.execute('SELECT * FROM usuarios')
                    usuarios = c.fetchall()
                    if usuarios:
                        colunas = ['id', 'username', 'nome', 'email', 'senha_hash', 
                                  'tipo', 'telefone', 'ativo']
                        df_usuarios = pd.DataFrame(usuarios, columns=colunas)
                        dados_exportar['usuarios'] = df_usuarios
                
                # Criar arquivo Ãºnico com mÃºltiplas abas (para Excel)
                if formato == "Excel" and dados_exportar:
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        for nome, df in dados_exportar.items():
                            df.to_excel(writer, sheet_name=nome[:31], index=False)
                    buffer.seek(0)
                    
                    st.download_button(
                        label="â¬‡ï¸ Baixar Excel",
                        data=buffer,
                        file_name=f"export_obra_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel"
                    )
                
                elif formato == "CSV" and dados_exportar:
                    # Para mÃºltiplos CSVs, criar um ZIP
                    import zipfile
                    
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, 'w') as zip_file:
                        for nome, df in dados_exportar.items():
                            csv_buffer = io.StringIO()
                            df.to_csv(csv_buffer, index=False)
                            zip_file.writestr(f"{nome}.csv", csv_buffer.getvalue())
                    buffer.seek(0)
                    
                    st.download_button(
                        label="â¬‡ï¸ Baixar ZIP com CSVs",
                        data=buffer,
                        file_name=f"export_obra_{date.today()}.zip",
                        mime="application/zip",
                        key="download_csv_zip"
                    )
                
                elif formato == "JSON" and dados_exportar:
                    dados_json = {}
                    for nome, df in dados_exportar.items():
                        dados_json[nome] = df.to_dict(orient='records')
                    
                    json_str = json.dumps(dados_json, indent=2, default=str)
                    
                    st.download_button(
                        label="â¬‡ï¸ Baixar JSON",
                        data=json_str,
                        file_name=f"export_obra_{date.today()}.json",
                        mime="application/json",
                        key="download_json"
                    )
                else:
                    st.warning("Nenhum dado selecionado para exportar.")

def exibir_controle_financeiro():
    """Exibe o controle financeiro"""
    st.markdown('<h2 class="sub-header">ðŸ’° Controle Financeiro</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    
    tab1, tab2, tab3 = st.tabs(["LanÃ§ar Custos", "AnÃ¡lise Financeira", "OrÃ§amento vs Realizado"])
    
    with tab1:
        # FormulÃ¡rio para lanÃ§ar custos
        with st.form("form_custo"):
            categoria = st.selectbox("Categoria", 
                                    ["Materiais", "MÃ£o de Obra", "Equipamentos", 
                                     "Transporte", "ServiÃ§os", "Imprevistos"])
            descricao = st.text_input("DescriÃ§Ã£o do custo*")
            valor = st.number_input("Valor (MZN)*", min_value=0.0, step=100.0)
            data_custo = st.date_input("Data", value=date.today())
            
            comprovante = st.file_uploader("Comprovante (opcional)", 
                                          type=['pdf', 'jpg', 'png'])
            
            if st.form_submit_button("LanÃ§ar Custo"):
                if not descricao or valor <= 0:
                    st.error("Preencha a descriÃ§Ã£o e valor corretamente.")
                else:
                    try:
                        c = conn.cursor()
                        comprovante_path = None
                        
                        if comprovante:
                            # Salvar comprovante
                            os.makedirs('comprovantes', exist_ok=True)
                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                            ext = comprovante.type.split('/')[-1]
                            comprovante_path = f"comprovantes/{timestamp}_{descricao[:20].replace(' ', '_')}.{ext}"
                            with open(comprovante_path, 'wb') as f:
                                f.write(comprovante.getvalue())
                        
                        c.execute('''
                            INSERT INTO custos (projeto_id, categoria, descricao, valor, data, comprovante_path)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (filtros['projeto_id'], categoria, descricao, valor, data_custo, comprovante_path))
                        
                        conn.commit()
                        st.success(f"Custo de MZN {valor:,.2f} lanÃ§ado com sucesso!")
                        
                        # Criar alerta para custos altos
                        if valor > 10000:
                            criar_alerta(filtros['projeto_id'], 'financeiro',
                                        f"Custo alto lanÃ§ado: {descricao} - MZN {valor:,.2f}")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"Erro ao lanÃ§ar custo: {str(e)}")
    
    with tab2:
        # AnÃ¡lise financeira
        c = conn.cursor()
        c.execute('''
            SELECT categoria, SUM(valor) as total 
            FROM custos 
            WHERE projeto_id = ? AND data BETWEEN ? AND ?
            GROUP BY categoria
        ''', (filtros['projeto_id'], filtros['data_inicio'], filtros['data_fim']))
        
        custos = c.fetchall()
        
        if custos:
            df_custos = pd.DataFrame(custos, columns=['Categoria', 'Total'])
            
            # GrÃ¡fico de pizza
            fig = px.pie(df_custos, values='Total', names='Categoria',
                        title='DistribuiÃ§Ã£o de Custos por Categoria')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("Detalhamento de Custos")
            st.dataframe(df_custos, use_container_width=True)
            
            # Total geral
            total_geral = df_custos['Total'].sum()
            st.metric("Total de Custos no PerÃ­odo", f"MZN {total_geral:,.2f}")
        else:
            st.info("Nenhum custo registrado no perÃ­odo selecionado.")
    
    with tab3:
        # OrÃ§amento vs Realizado
        projeto = obter_projeto_por_id(filtros['projeto_id'])
        
        if projeto:
            orcamento_total = projeto[4]
            
            # Calcular custos totais
            c = conn.cursor()
            c.execute('SELECT SUM(valor) FROM custos WHERE projeto_id = ?', 
                     (filtros['projeto_id'],))
            resultado = c.fetchone()
            custos_totais = resultado[0] if resultado and resultado[0] else 0
            
            # Calcular percentual utilizado
            percentual_utilizado = (custos_totais / orcamento_total * 100) if orcamento_total > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("OrÃ§amento Total", f"MZN {orcamento_total:,.2f}")
            with col2:
                st.metric("Custos Realizados", f"MZN {custos_totais:,.2f}")
            with col3:
                st.metric("Percentual Utilizado", f"{percentual_utilizado:.1f}%")
            
            # Barra de progresso
            st.progress(min(1.0, percentual_utilizado / 100))
            
            # Alerta se ultrapassar 80% do orÃ§amento
            if percentual_utilizado > 80:
                st.error(f"âš ï¸ AtenÃ§Ã£o! {percentual_utilizado:.1f}% do orÃ§amento jÃ¡ foi utilizado.")
                criar_alerta(filtros['projeto_id'], 'financeiro',
                           f"OrÃ§amento utilizado em {percentual_utilizado:.1f}%")
        else:
            st.info("Projeto nÃ£o encontrado.")

def exibir_configuracoes():
    """Exibe as configuraÃ§Ãµes do sistema"""
    st.markdown('<h2 class="sub-header">âš™ï¸ ConfiguraÃ§Ãµes do Sistema</h2>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Email", "WhatsApp", "Sistema"])
    
    with tab1:
        st.subheader("ConfiguraÃ§Ãµes de Email")
        
        # Em produÃ§Ã£o, estas configuraÃ§Ãµes viriam de um arquivo de configuraÃ§Ã£o ou banco de dados
        smtp_server = st.text_input("Servidor SMTP", value="smtp.gmail.com")
        smtp_port = st.number_input("Porta SMTP", value=587)
        email_from = st.text_input("Email de origem", value="seu_email@gmail.com")
        email_password = st.text_input("Senha do email", type="password")
        
        emails_notificacao = st.text_area(
            "Emails para notificaÃ§Ãµes (um por linha)",
            value="proprietario@obra.com\ngerente@obra.com\nfiscal@obra.com"
        )
        
        if st.button("Salvar ConfiguraÃ§Ãµes de Email"):
            st.success("ConfiguraÃ§Ãµes de email salvas! (Em produÃ§Ã£o, seriam persistidas)")
    
    with tab2:
        st.subheader("ConfiguraÃ§Ãµes do WhatsApp (Twilio)")
        
        account_sid = st.text_input("Account SID", value="sua_account_sid")
        auth_token = st.text_input("Auth Token", type="password", value="seu_auth_token")
        from_number = st.text_input("NÃºmero Twilio", value="whatsapp:+14155238886")
        
        numeros_whatsapp = st.text_area(
            "NÃºmeros para notificaÃ§Ãµes WhatsApp (um por linha)",
            value="whatsapp:+258841234567\nwhatsapp:+258842345678"
        )
        
        if st.button("Salvar ConfiguraÃ§Ãµes WhatsApp"):
            st.success("ConfiguraÃ§Ãµes do WhatsApp salvas! (Em produÃ§Ã£o, seriam persistidas)")
    
    with tab3:
        st.subheader("ConfiguraÃ§Ãµes do Sistema")
        
        # Backup do banco de dados
        if st.button("ðŸ”„ Criar Backup do Banco de Dados"):
            try:
                if os.path.exists('controle_obra.db'):
                    backup_data = open('controle_obra.db', 'rb').read()
                    st.download_button(
                        label="â¬‡ï¸ Baixar Backup",
                        data=backup_data,
                        file_name=f"backup_obra_{date.today()}.db",
                        mime="application/x-sqlite3",
                        key="download_backup"
                    )
                else:
                    st.error("Banco de dados nÃ£o encontrado.")
            except Exception as e:
                st.error(f"Erro ao criar backup: {str(e)}")
        
        # Limpar cache de fotos
        if st.button("ðŸ§¹ Limpar Cache de Fotos"):
            st.warning("Esta aÃ§Ã£o removerÃ¡ fotos nÃ£o associadas a relatÃ³rios. Tem certeza?")
            if st.button("Confirmar Limpeza", key="confirmar_limpeza"):
                st.info("Funcionalidade em desenvolvimento")
        
        # EstatÃ­sticas do sistema
        st.subheader("EstatÃ­sticas do Sistema")
        
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM usuarios")
        total_usuarios = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM projetos")
        total_projetos = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM relatorios_diarios")
        total_relatorios = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM fotos_obra")
        total_fotos = c.fetchone()[0]
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("UsuÃ¡rios", total_usuarios)
        with col2:
            st.metric("Projetos", total_projetos)
        with col3:
            st.metric("RelatÃ³rios", total_relatorios)
        with col4:
            st.metric("Fotos", total_fotos)

def exibir_relatorios_lista():
    """Exibe lista de relatÃ³rios para visualizaÃ§Ã£o"""
    st.markdown('<h2 class="sub-header">ðŸ“‹ RelatÃ³rios DiÃ¡rios</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    relatorios = obter_relatorios(filtros['projeto_id'], 
                                 filtros['data_inicio'], 
                                 filtros['data_fim'])
    
    if not relatorios:
        st.info("Nenhum relatÃ³rio encontrado para o perÃ­odo selecionado.")
        return
    
    # Filtros adicionais
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    with col_filtro1:
        filtrar_status = st.multiselect("Filtrar por status", 
                                       ["ConcluÃ­do", "Em andamento", "Atrasado", "Paralisado"],
                                       default=["ConcluÃ­do", "Em andamento"])
    with col_filtro2:
        filtrar_acidente = st.selectbox("Filtrar por acidente", 
                                       ["Todos", "Com acidente", "Sem acidente"])
    with col_filtro3:
        min_produtividade = st.slider("Produtividade mÃ­nima", 0, 100, 0)
    
    # Aplicar filtros
    relatorios_filtrados = []
    for rel in relatorios:
        if filtrar_status and rel[11] not in filtrar_status:
            continue
        if filtrar_acidente == "Com acidente" and rel[9] == "Nenhum":
            continue
        if filtrar_acidente == "Sem acidente" and rel[9] != "Nenhum":
            continue
        if rel[12] < min_produtividade:
            continue
        
        relatorios_filtrados.append(rel)
    
    # Exibir relatÃ³rios
    for rel in relatorios_filtrados:
        # ÃNDICES CORRIGIDOS:
        # 0:id, 1:data, 2:projeto_id, 3:usuario_id, 4:temperatura, 5:atividades,
        # 6:equipe, 7:equipamentos, 8:ocorrencias, 9:acidentes, 10:plano_amanha,
        # 11:status, 12:produtividade, 13:observacoes, 14:projeto_nome, 15:usuario_nome
        
        with st.expander(f"{rel[1]} - {rel[14]} - {rel[11]} - {rel[12]}%"):
            # Layout do relatÃ³rio
            tab_det, tab_fotos, tab_acoes = st.tabs(["Detalhes", "Fotos", "AÃ§Ãµes"])
            
            with tab_det:
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Data:** {rel[1]}")
                    st.write(f"**Projeto:** {rel[14]}")
                    st.write(f"**ResponsÃ¡vel:** {rel[15]}")
                    st.write(f"**Status:** {rel[11]}")
                    st.write(f"**Produtividade:** {rel[12]}%")
                with col2:
                    st.write(f"**CondiÃ§Ãµes ClimÃ¡ticas:** {rel[4]}")
                    st.write(f"**Equipe:** {rel[6]}")
                    st.write(f"**Equipamentos:** {rel[7]}")
                    st.write(f"**Acidentes:** {rel[9]}")
                
                st.write("**Atividades Realizadas:**")
                st.info(rel[5])
                
                if rel[8] and rel[8] != 'Nenhuma':
                    st.write("**OcorrÃªncias:**")
                    st.warning(rel[8])
                
                if rel[10]:
                    st.write("**Plano para o PrÃ³ximo Dia:**")
                    st.success(rel[10])
            
            with tab_fotos:
                fotos = obter_fotos(rel[0])
                if fotos:
                    cols = st.columns(3)
                    for idx, foto in enumerate(fotos):
                        with cols[idx % 3]:
                            try:
                                if os.path.exists(foto[2]):
                                    with open(foto[2], 'rb') as f:
                                        img_bytes = f.read()
                                    st.image(img_bytes, caption=foto[3] or f"Foto {idx+1}", 
                                            use_column_width=True)
                                else:
                                    st.warning("Arquivo nÃ£o encontrado")
                            except:
                                st.error("Erro ao carregar foto")
                else:
                    st.info("Nenhuma foto para este relatÃ³rio")
            
            with tab_acoes:
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    if st.button("ðŸ“„ Gerar PDF", key=f"gen_pdf_{rel[0]}"):
                        pdf = gerar_relatorio_pdf(rel[0])
                        if pdf:
                            st.download_button(
                                label="â¬‡ï¸ Baixar PDF",
                                data=pdf,
                                file_name=f"relatorio_{rel[1]}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_{rel[0]}"
                            )
                with col_btn2:
                    if st.button("ðŸ“§ Enviar por Email", key=f"email_{rel[0]}"):
                        st.info("Funcionalidade em desenvolvimento")
                with col_btn3:
                    if st.button("ðŸ“± Compartilhar WhatsApp", key=f"share_{rel[0]}"):
                        mensagem = f"RelatÃ³rio {rel[1]} - {rel[14]}\nStatus: {rel[11]}\nProdutividade: {rel[12]}%"
                        enviar_whatsapp_alerta(filtros['projeto_id'], 'info', mensagem)
                        st.success("Mensagem enviada para WhatsApp!")

def exibir_relatorios_financeiros():
    """Exibe relatÃ³rios financeiros especÃ­ficos"""
    st.markdown('<h2 class="sub-header">ðŸ’° RelatÃ³rios Financeiros</h2>', unsafe_allow_html=True)
    
    filtros = st.session_state.filtros
    projeto = obter_projeto_por_id(filtros['projeto_id'])
    
    if not projeto:
        st.error("Projeto nÃ£o encontrado.")
        return
    
    # Obter custos
    c = conn.cursor()
    c.execute('''
        SELECT categoria, descricao, valor, data 
        FROM custos 
        WHERE projeto_id = ? AND data BETWEEN ? AND ?
        ORDER BY data DESC
    ''', (filtros['projeto_id'], filtros['data_inicio'], filtros['data_fim']))
    
    custos = c.fetchall()
    
    tab1, tab2, tab3 = st.tabs(["Fluxo de Caixa", "Custos Detalhados", "PrevisÃµes"])
    
    with tab1:
        # Fluxo de caixa
        if custos:
            df = pd.DataFrame(custos, columns=['Categoria', 'DescriÃ§Ã£o', 'Valor', 'Data'])
            df['Data'] = pd.to_datetime(df['Data'])
            
            # Agrupar por data
            df_fluxo = df.groupby('Data')['Valor'].sum().reset_index()
            df_fluxo['Acumulado'] = df_fluxo['Valor'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_fluxo['Data'], y=df_fluxo['Valor'],
                                name='Custo DiÃ¡rio', marker_color='indianred'))
            fig.add_trace(go.Scatter(x=df_fluxo['Data'], y=df_fluxo['Acumulado'],
                                    name='Custo Acumulado', line=dict(color='royalblue', width=3)))
            
            fig.update_layout(title='Fluxo de Caixa DiÃ¡rio',
                            xaxis_title='Data',
                            yaxis_title='Valor (MZN)',
                            hovermode='x unified')
            
            st.plotly_chart(fig, use_container_width=True)
            
            # MÃ©tricas
            total_periodo = df['Valor'].sum()
            media_diaria = total_periodo / len(df_fluxo) if len(df_fluxo) > 0 else 0
            maior_custo = df['Valor'].max()
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total no PerÃ­odo", f"MZN {total_periodo:,.2f}")
            with col2:
                st.metric("MÃ©dia DiÃ¡ria", f"MZN {media_diaria:,.2f}")
            with col3:
                st.metric("Maior Custo", f"MZN {maior_custo:,.2f}")
        else:
            st.info("Nenhum custo registrado no perÃ­odo.")
    
    with tab2:
        # Custos detalhados
        if custos:
            df = pd.DataFrame(custos, columns=['Categoria', 'DescriÃ§Ã£o', 'Valor', 'Data'])
            
            # Agrupar por categoria
            df_cat = df.groupby('Categoria').agg({
                'Valor': ['sum', 'count', 'mean', 'max']
            }).round(2)
            
            df_cat.columns = ['Total', 'Quantidade', 'MÃ©dia', 'MÃ¡ximo']
            df_cat = df_cat.sort_values('Total', ascending=False)
            
            st.subheader("Resumo por Categoria")
            st.dataframe(df_cat, use_container_width=True)
            
            # Tabela detalhada
            st.subheader("Detalhamento de Custos")
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Nenhum custo registrado no perÃ­odo.")
    
    with tab3:
        # PrevisÃµes
        st.subheader("PrevisÃ£o de Custos")
        
        if custos:
            df = pd.DataFrame(custos, columns=['Categoria', 'DescriÃ§Ã£o', 'Valor', 'Data'])
            df['Data'] = pd.to_datetime(df['Data'])
            
            # Calcular custo mÃ©dio diÃ¡rio
            dias_periodo = (filtros['data_fim'] - filtros['data_inicio']).days + 1
            custo_total = df['Valor'].sum()
            custo_medio_diario = custo_total / dias_periodo if dias_periodo > 0 else 0
            
            # Calcular dias restantes do projeto
            try:
                data_fim_projeto = datetime.datetime.strptime(projeto[6], '%Y-%m-%d').date()
            except:
                data_fim_projeto = date.today() + timedelta(days=180)
            
            dias_restantes = max(0, (data_fim_projeto - date.today()).days)
            
            # PrevisÃ£o
            previsao_restante = custo_medio_diario * dias_restantes
            previsao_total = custo_total + previsao_restante
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Custo MÃ©dio DiÃ¡rio", f"MZN {custo_medio_diario:,.2f}")
            with col2:
                st.metric("Dias Restantes", dias_restantes)
            with col3:
                st.metric("PrevisÃ£o Custo Restante", f"MZN {previsao_restante:,.2f}")
            
            # ComparaÃ§Ã£o com orÃ§amento
            orcamento = projeto[4]
            percentual_previsto = (previsao_total / orcamento * 100) if orcamento > 0 else 0
            
            st.subheader("ComparaÃ§Ã£o com OrÃ§amento")
            
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode = "gauge+number",
                value = percentual_previsto,
                title = {'text': "OrÃ§amento Previsto (%)"},
                domain = {'x': [0, 1], 'y': [0, 1]},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 70], 'color': "green"},
                        {'range': [70, 90], 'color': "yellow"},
                        {'range': [90, 100], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            if percentual_previsto > 100:
                st.error(f"âš ï¸ ATENÃ‡ÃƒO: PrevisÃ£o ultrapassa o orÃ§amento em {percentual_previsto-100:.1f}%!")
            elif percentual_previsto > 90:
                st.warning(f"âš ï¸ CUIDADO: PrevisÃ£o prÃ³xima do orÃ§amento ({percentual_previsto:.1f}%)")
        else:
            st.info("Insira custos para gerar previsÃµes.")

# ============================================
# MAIN APP
# ============================================

def main():
    """FunÃ§Ã£o principal da aplicaÃ§Ã£o"""
    
    # Verificar se o usuÃ¡rio estÃ¡ logado
    if 'usuario' not in st.session_state:
        tela_login()
    else:
        exibir_menu_principal()

if __name__ == "__main__":
    main()

