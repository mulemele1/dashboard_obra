import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import sqlite3
import hashlib
import io
import os
import plotly.graph_objects as go
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from streamlit_image_zoom import image_zoom
from PIL import Image

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(page_title="Dashboard de Obra", page_icon="🏗️", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    .main-header {font-size: 2.8rem; color: #1E40AF; text-align: center; margin: 1rem 0;}
    .sub-header {font-size: 1.8rem; color: #2563EB; margin-top: 2rem; border-bottom: 2px solid #E5E7EB; padding-bottom: 0.5rem;}
    .stButton > button {
        width: 100%;
        margin-top: 5px;
        margin-bottom: 5px;
    }
    /* ESTILO PARA BOTÕES AZUIS */
    div.stButton > button.primary {
        background-color: #1E40AF !important;
        color: white !important;
        border-color: #1E40AF !important;
    }
    div.stButton > button.primary:hover {
        background-color: #1E3A8A !important;
        border-color: #1E3A8A !important;
    }
    
     /* Botão Novo Relatório específico */
    button[kind="primary"] {
        background-color: #1E40AF !important;
        color: white !important;
        border-color: #1E40AF !important;
    }
    
    /* OU por atributo data-testid */
    button[data-testid="baseButton-primary"] {
        background-color: #1E40AF !important;
        color: white !important;
        border-color: #1E40AF !important;
    }
    
    /* Estilos para cards do dashboard */
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 5px solid #1E40AF;
    }
    
    .card-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1E40AF;
        margin-bottom: 0.5rem;
    }
    
    .card-value {
        font-size: 2rem;
        font-weight: bold;
        color: #2D3748;
    }
    
    .card-subtitle {
        font-size: 0.9rem;
        color: #718096;
    }
    
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    .status-completed {
        background-color: #D1FAE5;
        color: #065F46;
        border: 1px solid #10B981;
    }
    
    .status-in-progress {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #F59E0B;
    }
    
    .status-pending {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #EF4444;
    }
    
    .status-delayed {
        background-color: #E5E7EB;
        color: #4B5563;
        border: 1px solid #9CA3AF;
    }
    
    .activity-card {
        background-color: #F8FAFC;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #3B82F6;
    }
    
    .subactivity-item {
        background-color: white;
        border-radius: 6px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        border-left: 3px solid #E5E7EB;
    }
    
    .subactivity-completed {
        border-left-color: #10B981;
        background-color: #F0FDF4;
    }
    
    .subactivity-pending {
        border-left-color: #F59E0B;
        background-color: #FFFBEB;
    }
    
    .progress-bar {
        height: 10px;
        background-color: #E5E7EB;
        border-radius: 5px;
        overflow: hidden;
        margin: 0.5rem 0;
    }
    
    .progress-fill {
        height: 100%;
        background-color: #10B981;
        border-radius: 5px;
    }
    
    .plan-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .occurrence-card {
        background-color: #FEF3C7;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #F59E0B;
    }
    
    .equipment-card {
        background-color: #E0F2FE;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #0EA5E9;
    }
    
    .workforce-card {
        background-color: #F0F9FF;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #0369A1;
    }
    
    .weather-card {
        background-color: #F0FDFA;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 5px solid #0D9488;
    }
    
    /* Estilo para gráficos */
    .plot-container {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÕES AUXILIARES - ATUALIZADA
# ============================================
def init_database():
    conn = sqlite3.connect('controle_obra.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE NOT NULL, 
        nome TEXT NOT NULL, 
        email TEXT UNIQUE NOT NULL,
        senha_hash TEXT NOT NULL, 
        tipo TEXT NOT NULL, 
        telefone TEXT, 
        ativo INTEGER DEFAULT 1)""")
    
    # Tabela de projetos - ADICIONADA coluna proprietario_id
    c.execute("""CREATE TABLE IF NOT EXISTS projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        nome TEXT NOT NULL, 
        descricao TEXT, 
        localizacao TEXT, 
        orcamento_total REAL,
        data_inicio DATE, 
        data_fim_previsto DATE, 
        status TEXT DEFAULT 'Em andamento', 
        responsavel_id INTEGER,
        proprietario_id INTEGER,
        FOREIGN KEY (responsavel_id) REFERENCES usuarios (id),
        FOREIGN KEY (proprietario_id) REFERENCES usuarios (id))""")
    
    # Tabela de relatórios diários
    c.execute("""CREATE TABLE IF NOT EXISTS relatorios_diarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        data DATE NOT NULL, 
        projeto_id INTEGER NOT NULL, 
        usuario_id INTEGER NOT NULL,
        temperatura TEXT, 
        atividades TEXT NOT NULL, 
        equipe TEXT, 
        equipamentos TEXT, 
        ocorrencias TEXT,
        plano_amanha TEXT, 
        status TEXT, 
        produtividade INTEGER, 
        observacoes TEXT,
        FOREIGN KEY (projeto_id) REFERENCES projetos (id), 
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id))""")
    
    # Tabela de fotos
    c.execute("""CREATE TABLE IF NOT EXISTS fotos_obra (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        relatorio_id INTEGER NOT NULL, 
        foto_path TEXT NOT NULL,
        descricao TEXT, 
        atividade_principal TEXT,
        data_upload DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (relatorio_id) REFERENCES relatorios_diarios (id))""")

    # Tabela de acesso de usuários a projetos
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios_projetos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        projeto_id INTEGER NOT NULL,
        data_associacao DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
        FOREIGN KEY (projeto_id) REFERENCES projetos (id),
        UNIQUE(usuario_id, projeto_id))""")

    # VERIFICAR E ADICIONAR COLUNAS SE NECESSÁRIO
    try:
        c.execute("SELECT proprietario_id FROM projetos LIMIT 1")
    except sqlite3.OperationalError:
        # A coluna não existe, vamos adicioná-la
        c.execute("ALTER TABLE projetos ADD COLUMN proprietario_id INTEGER")
        conn.commit()

    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ('fiscal', 'Fiscal da Obra', 'fiscal@obra.com', hashlib.sha256('fiscal123'.encode()).hexdigest(), 'fiscal', '+258840000000'),
            ('proprietario1', 'João Silva', 'joao@obra.com', hashlib.sha256('joao123'.encode()).hexdigest(), 'proprietario', '+258841111111'),
            ('proprietario2', 'Maria Santos', 'maria@obra.com', hashlib.sha256('maria123'.encode()).hexdigest(), 'proprietario', '+258842222222'),
            ('proprietario3', 'Antonio Pereira', 'antonio@obra.com', hashlib.sha256('antonio123'.encode()).hexdigest(), 'proprietario', '+258843333333'),
            ('admin', 'Administrador', 'admin@obra.com', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin', '+258860000000')
        ]
        c.executemany("INSERT INTO usuarios (username,nome,email,senha_hash,tipo,telefone) VALUES (?,?,?,?,?,?)", usuarios_padrao)

    # Inserir projeto padrão se não existir
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        projetos_padrao = [
            ('Obra Xai-Xai', 'Requalificação com expansão', 'Xai-Xai, Gaza', 2500000.0, '2025-02-01', '2025-08-01', 1, 2),
            ('Condomínio Maputo', 'Residencial de luxo', 'Maputo', 3500000.0, '2025-01-15', '2025-10-30', 1, 3),
            ('Escola Gaza', 'Escola secundária', 'Gaza', 1800000.0, '2025-03-01', '2025-11-15', 1, 4)
        ]
        for projeto in projetos_padrao:
            c.execute("""INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id, proprietario_id)
                      VALUES (?,?,?,?,?,?,?,?)""", projeto)
    
    conn.commit()
    return conn

conn = init_database()

def verificar_login(username, password):
    c = conn.cursor()
    hash_senha = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id,username,nome,tipo FROM usuarios WHERE username=? AND senha_hash=? AND ativo=1", (username, hash_senha))
    return c.fetchone()

def obter_projetos():
    c = conn.cursor()
    c.execute("""SELECT p.*, u.nome as responsavel_nome, up.nome as proprietario_nome 
                 FROM projetos p 
                 LEFT JOIN usuarios u ON p.responsavel_id = u.id
                 LEFT JOIN usuarios up ON p.proprietario_id = up.id
                 ORDER BY p.data_inicio DESC""")
    return c.fetchall()

def obter_projetos_por_usuario(usuario_id, usuario_tipo):
    """Obtém projetos que um usuário tem acesso"""
    c = conn.cursor()
    
    if usuario_tipo == 'admin':
        # Admin vê todos os projetos
        c.execute("""
            SELECT p.*, u.nome as responsavel_nome, up.nome as proprietario_nome 
            FROM projetos p 
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            LEFT JOIN usuarios up ON p.proprietario_id = up.id
            ORDER BY p.data_inicio DESC
        """)
    elif usuario_tipo == 'fiscal':
        # Fiscal vê todos os projetos
        c.execute("""
            SELECT p.*, u.nome as responsavel_nome, up.nome as proprietario_nome 
            FROM projetos p 
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            LEFT JOIN usuarios up ON p.proprietario_id = up.id
            ORDER BY p.data_inicio DESC
        """)
    else:
        # Proprietário vê apenas seus projetos
        c.execute("""
            SELECT DISTINCT p.*, u.nome as responsavel_nome, up.nome as proprietario_nome 
            FROM projetos p 
            LEFT JOIN usuarios u ON p.responsavel_id = u.id
            LEFT JOIN usuarios up ON p.proprietario_id = up.id
            LEFT JOIN usuarios_projetos upr ON p.id = upr.projeto_id
            WHERE p.proprietario_id = ? OR upr.usuario_id = ? OR p.responsavel_id = ?
            ORDER BY p.data_inicio DESC
        """, (usuario_id, usuario_id, usuario_id))
    
    return c.fetchall()

def obter_usuarios():
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios ORDER BY nome")
    return c.fetchall()

def obter_usuarios_por_tipo(tipo):
    """Obtém usuários por tipo específico"""
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE tipo = ? AND ativo = 1 ORDER BY nome", (tipo,))
    return c.fetchall()

def obter_usuarios_por_projeto(projeto_id):
    """Obtém usuários que têm acesso a um projeto específico"""
    c = conn.cursor()
    c.execute("""
        SELECT u.* FROM usuarios u
        JOIN usuarios_projetos up ON u.id = up.usuario_id
        WHERE up.projeto_id = ?
        ORDER BY u.nome
    """, (projeto_id,))
    return c.fetchall()

def adicionar_usuario(username, nome, email, senha, tipo, telefone):
    c = conn.cursor()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        c.execute("""
            INSERT INTO usuarios (username, nome, email, senha_hash, tipo, telefone)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, nome, email, senha_hash, tipo, telefone))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError as e:
        raise Exception(f"Erro: {str(e)}")

def atualizar_usuario(usuario_id, username, nome, email, tipo, telefone, ativo):
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE usuarios 
            SET username=?, nome=?, email=?, tipo=?, telefone=?, ativo=?
            WHERE id=?
        """, (username, nome, email, tipo, telefone, ativo, usuario_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        raise Exception(f"Erro: {str(e)}")

def adicionar_projeto(nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id, proprietario_id):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id, proprietario_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id, proprietario_id))
        projeto_id = c.lastrowid
        
        # Associar automaticamente o proprietário ao projeto
        if proprietario_id:
            associar_usuario_projeto(proprietario_id, projeto_id)
        
        conn.commit()
        return projeto_id
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

def atualizar_projeto(projeto_id, nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, status, responsavel_id, proprietario_id):
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE projetos 
            SET nome=?, descricao=?, localizacao=?, orcamento_total=?, data_inicio=?, data_fim_previsto=?, status=?, responsavel_id=?, proprietario_id=?
            WHERE id=?
        """, (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, status, responsavel_id, proprietario_id, projeto_id))
        conn.commit()
        return True
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

def excluir_projeto(projeto_id):
    """Exclui um projeto e todos os dados relacionados"""
    c = conn.cursor()
    try:
        # Obter todas as fotos do projeto para excluir arquivos
        c.execute("""
            SELECT f.foto_path FROM fotos_obra f
            JOIN relatorios_diarios r ON f.relatorio_id = r.id
            WHERE r.projeto_id = ?
        """, (projeto_id,))
        
        fotos = c.fetchall()
        for foto in fotos:
            caminho = foto["foto_path"]
            if os.path.exists(caminho):
                try:
                    os.remove(caminho)
                except:
                    pass
        
        # Excluir dados relacionados
        c.execute("DELETE FROM usuarios_projetos WHERE projeto_id = ?", (projeto_id,))
        c.execute("DELETE FROM fotos_obra WHERE relatorio_id IN (SELECT id FROM relatorios_diarios WHERE projeto_id = ?)", (projeto_id,))
        c.execute("DELETE FROM relatorios_diarios WHERE projeto_id = ?", (projeto_id,))
        c.execute("DELETE FROM projetos WHERE id = ?", (projeto_id,))
        
        conn.commit()
        return True
    except Exception as e:
        raise Exception(f"Erro ao excluir projeto: {str(e)}")

def associar_usuario_projeto(usuario_id, projeto_id):
    """Associa um usuário a um projeto"""
    c = conn.cursor()
    try:
        c.execute("""
            INSERT OR IGNORE INTO usuarios_projetos (usuario_id, projeto_id)
            VALUES (?, ?)
        """, (usuario_id, projeto_id))
        conn.commit()
        return True
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

def desassociar_usuario_projeto(usuario_id, projeto_id):
    """Remove a associação de um usuário com um projeto"""
    c = conn.cursor()
    try:
        c.execute("DELETE FROM usuarios_projetos WHERE usuario_id=? AND projeto_id=?", (usuario_id, projeto_id))
        conn.commit()
        return True
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

def obter_projetos_disponiveis_usuario(usuario_id):
    """Obtém projetos disponíveis para um usuário (que ainda não tem acesso)"""
    c = conn.cursor()
    c.execute("""
        SELECT p.* FROM projetos p
        WHERE p.id NOT IN (
            SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?
        )
        AND p.id NOT IN (
            SELECT id FROM projetos WHERE responsavel_id = ? OR proprietario_id = ?
        )
        ORDER BY p.nome
    """, (usuario_id, usuario_id, usuario_id))
    return c.fetchall()

def obter_relatorios_usuario(usuario_id, admin=False, projeto_id=None):
    c = conn.cursor()
    
    # Se for admin, mostra todos os relatórios
    if admin:
        query = """SELECT r.id, r.data, p.nome AS projeto_nome, u.nome AS usuario_nome, r.status, r.produtividade
                   FROM relatorios_diarios r
                   JOIN projetos p ON r.projeto_id = p.id
                   JOIN usuarios u ON r.usuario_id = u.id"""
        params = []
    else:
        # Para não-admins, mostra apenas relatórios de projetos que têm acesso
        query = """SELECT r.id, r.data, p.nome AS projeto_nome, u.nome AS usuario_nome, r.status, r.produtividade
                   FROM relatorios_diarios r
                   JOIN projetos p ON r.projeto_id = p.id
                   JOIN usuarios u ON r.usuario_id = u.id
                   WHERE p.id IN (
                       SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?
                       UNION
                       SELECT id FROM projetos WHERE responsavel_id = ? OR proprietario_id = ?
                   )"""
        params = [usuario_id, usuario_id, usuario_id]
    
    if projeto_id and projeto_id != 0:
        where_clause = " AND" if params else " WHERE"
        query += f" {where_clause} r.projeto_id = ?"
        params.append(projeto_id)
    
    query += " ORDER BY r.data DESC"
    c.execute(query, params)
    return c.fetchall()

def obter_fotos_por_relatorio(relatorio_id):
    """Obtém todas as fotos de um relatório específico"""
    c = conn.cursor()
    c.execute("""
        SELECT * FROM fotos_obra 
        WHERE relatorio_id = ?
        ORDER BY data_upload DESC
    """, (relatorio_id,))
    return c.fetchall()

def obter_fotos_por_atividade(projeto_id=None, usuario_id=None, usuario_tipo=None):
    """Obtém fotos agrupadas por atividade principal"""
    c = conn.cursor()
    
    query = """
        SELECT f.*, r.data, p.nome as projeto_nome, 
               COALESCE(f.atividade_principal, 'Sem atividade') as atividade_agrupada
        FROM fotos_obra f
        JOIN relatorios_diarios r ON f.relatorio_id = r.id
        JOIN projetos p ON r.projeto_id = p.id
    """
    
    params = []
    
    if projeto_id and projeto_id != 0:
        query += " WHERE r.projeto_id = ?"
        params.append(projeto_id)
    elif usuario_tipo != "admin":
        # Para não-admins, filtrar apenas projetos que têm acesso
        query += """ WHERE r.projeto_id IN (
            SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?
            UNION
            SELECT id FROM projetos WHERE responsavel_id = ? OR proprietario_id = ?
        )"""
        params.extend([usuario_id, usuario_id, usuario_id])
    
    query += " ORDER BY f.atividade_principal, r.data DESC, f.data_upload DESC"
    
    c.execute(query, params)
    return c.fetchall()

def contar_fotos_por_atividade(projeto_id=None, usuario_id=None, usuario_tipo=None):
    """Conta fotos por atividade principal"""
    c = conn.cursor()
    
    query = """
        SELECT 
            COALESCE(f.atividade_principal, 'Sem atividade') as atividade,
            COUNT(*) as total_fotos
        FROM fotos_obra f
        JOIN relatorios_diarios r ON f.relatorio_id = r.id
        JOIN projetos p ON r.projeto_id = p.id
    """
    
    params = []
    
    if projeto_id and projeto_id != 0:
        query += " WHERE r.projeto_id = ?"
        params.append(projeto_id)
    elif usuario_tipo != "admin":
        query += """ WHERE r.projeto_id IN (
            SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?
            UNION
            SELECT id FROM projetos WHERE responsavel_id = ? OR proprietario_id = ?
        )"""
        params.extend([usuario_id, usuario_id, usuario_id])
    
    query += " GROUP BY atividade ORDER BY total_fotos DESC"
    
    c.execute(query, params)
    return c.fetchall()

def obter_ultimo_relatorio(projeto_id=None, usuario_id=None, usuario_tipo=None):
    """Obtém o último relatório registrado"""
    c = conn.cursor()
    
    query = """
        SELECT r.*, p.nome as projeto_nome, u.nome as usuario_nome
        FROM relatorios_diarios r
        JOIN projetos p ON r.projeto_id = p.id
        JOIN usuarios u ON r.usuario_id = u.id
    """
    
    params = []
    
    if projeto_id and projeto_id != 0:
        query += " WHERE r.projeto_id = ?"
        params.append(projeto_id)
    elif usuario_tipo != "admin":
        query += """ WHERE r.projeto_id IN (
            SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?
            UNION
            SELECT id FROM projetos WHERE responsavel_id = ? OR proprietario_id = ?
        )"""
        params.extend([usuario_id, usuario_id, usuario_id])
    
    query += " ORDER BY r.data DESC LIMIT 1"
    
    c.execute(query, params)
    return c.fetchone()

def carregar_relatorio(rel_id):
    c = conn.cursor()
    c.execute("SELECT * FROM relatorios_diarios WHERE id = ?", (rel_id,))
    return c.fetchone()

def apagar_relatorio(rel_id):
    c = conn.cursor()
    c.execute("SELECT foto_path FROM fotos_obra WHERE relatorio_id = ?", (rel_id,))
    for row in c.fetchall():
        caminho = row["foto_path"]
        if os.path.exists(caminho):
            os.remove(caminho)
    
    c.execute("DELETE FROM fotos_obra WHERE relatorio_id = ?", (rel_id,))
    c.execute("DELETE FROM relatorios_diarios WHERE id = ?", (rel_id,))
    conn.commit()

def salvar_relatorio(data, projeto_id, usuario_id, **dados):
    c = conn.cursor()
    c.execute("SELECT id FROM relatorios_diarios WHERE data=? AND projeto_id=?", (data, projeto_id))
    existente = c.fetchone()
    produtividade = int(dados.get('produtividade', 0))
    
    if existente:
        c.execute("""UPDATE relatorios_diarios SET temperatura=?, atividades=?, equipe=?, equipamentos=?, ocorrencias=?,
                  plano_amanha=?, status=?, produtividade=?, observacoes=? WHERE id=?""",
                  (dados.get('temperatura'), dados.get('atividades'), dados.get('equipe'), dados.get('equipamentos'),
                   dados.get('ocorrencias'), dados.get('plano_amanha'), dados.get('status'),
                   produtividade, dados.get('observacoes'), existente['id']))
        rel_id = existente['id']
    else:
        c.execute("""INSERT INTO relatorios_diarios (data,projeto_id,usuario_id,temperatura,atividades,equipe,equipamentos,ocorrencias,
                  plano_amanha,status,produtividade,observacoes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data, projeto_id, usuario_id, dados.get('temperatura'), dados.get('atividades'), dados.get('equipe'),
                   dados.get('equipamentos'), dados.get('ocorrencias'), dados.get('plano_amanha'),
                   dados.get('status'), produtividade, dados.get('observacoes')))
        rel_id = c.lastrowid
    
    conn.commit()
    return rel_id

def salvar_foto(relatorio_id, foto_bytes, descricao="", atividade_principal=""):
    os.makedirs("fotos_obra", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"foto_{relatorio_id}_{timestamp}.jpg"
    caminho = os.path.join("fotos_obra", nome)
    
    with open(caminho, "wb") as f:
        f.write(foto_bytes)
    
    c = conn.cursor()
    c.execute("INSERT INTO fotos_obra (relatorio_id, foto_path, descricao, atividade_principal) VALUES (?,?,?,?)", 
              (relatorio_id, caminho, descricao, atividade_principal))
    conn.commit()

def gerar_pdf(rel_id):
    c = conn.cursor()
    c.execute("""SELECT r.*, p.nome AS nome_projeto, u.nome AS nome_usuario 
                 FROM relatorios_diarios r
                 JOIN projetos p ON r.projeto_id = p.id
                 JOIN usuarios u ON r.usuario_id = u.id 
                 WHERE r.id = ?""", (rel_id,))
    rel = c.fetchone()
    
    if not rel:
        return None

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Relatório Diário de Obra", styles['Title']), Spacer(1, 20)]

    data_tabela = [
        ["Data", str(rel["data"])],
        ["Projeto", rel["nome_projeto"]],
        ["Responsável", rel["nome_usuario"]],
        ["Status", rel["status"] or "Não informado"],
        ["Produtividade", f"{rel['produtividade'] or 0}%"],
    ]
    
    t = Table(data_tabela, colWidths=[100, 400])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f0f0')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 20))

    secoes = [
        ("Clima", rel["temperatura"]),
        ("Atividades", rel["atividades"]),
        ("Equipe", rel["equipe"]),
        ("Equipamentos", rel["equipamentos"]),
        ("Ocorrências", rel["ocorrencias"]),
        ("Plano Amanhã", rel["plano_amanha"]),
        ("Observações", rel["observacoes"]),
    ]

    for titulo, texto in secoes:
        if texto and str(texto).strip():
            elements.append(Paragraph(f"<b>{titulo}:</b> {texto}", styles['Normal']))
            elements.append(Spacer(1, 10))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def get_day_name(date_obj):
    """Retorna o nome do dia da semana em português"""
    days_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", 
               "Sexta-feira", "Sábado", "Domingo"]
    return days_pt[date_obj.weekday()]

def parse_atividades(atividades_texto):
    """Parseia o texto de atividades em estrutura hierárquica"""
    atividades = []
    linhas = atividades_texto.split('\n')
    
    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        if ':' in linha:
            partes = linha.split(':', 1)
            atividade_principal = partes[0].strip()
            subatividades_texto = partes[1].strip()
            
            # Parsear subatividades
            subatividades = []
            if subatividades_texto:
                # Separar por vírgulas ou outros delimitadores
                for sub in subatividades_texto.split(','):
                    sub = sub.strip()
                    if sub:
                        # Verificar se tem indicação de status
                        feito = '✅' in sub or 'Concluído' in sub or 'Feito' in sub
                        # Remover indicadores de status
                        nome_sub = sub.replace('✅', '').replace('❌', '').replace('Concluído', '').replace('Feito', '').replace('Pendente', '').strip()
                        subatividades.append({
                            'nome': nome_sub,
                            'feito': feito
                        })
            
            atividades.append({
                'titulo': atividade_principal,
                'subs': subatividades
            })
        else:
            # Se não tem subatividades, é uma atividade simples
            atividades.append({
                'titulo': linha,
                'subs': []
            })
    
    return atividades

# ============================================
# FUNÇÕES PARA GRÁFICOS
# ============================================
def criar_grafico_atividades_vs_subatividades(atividades_parsed):
    """Cria gráfico de barras de atividades vs subatividades"""
    if not atividades_parsed:
        return None
    
    atividades = []
    totais_subs = []
    concluidas_subs = []
    
    for atividade in atividades_parsed:
        atividades.append(atividade['titulo'])
        total = len(atividade['subs'])
        concluidas = sum(1 for sub in atividade['subs'] if sub['feito'])
        
        totais_subs.append(total)
        concluidas_subs.append(concluidas)
    
    fig = go.Figure(data=[
        go.Bar(name='Total Subatividades', x=atividades, y=totais_subs, marker_color='#3B82F6'),
        go.Bar(name='Subatividades Concluídas', x=atividades, y=concluidas_subs, marker_color='#10B981')
    ])
    
    fig.update_layout(
        title='Atividades vs Subatividades Concluídas',
        barmode='group',
        xaxis_title='Atividades',
        yaxis_title='Quantidade',
        template='plotly_white',
        height=400
    )
    
    return fig

def criar_grafico_pizza_produtividade(atividades_parsed):
    """Cria gráfico de pizza mostrando distribuição de produtividade"""
    if not atividades_parsed:
        return None
    
    total_subs = 0
    concluidas_subs = 0
    
    for atividade in atividades_parsed:
        total_subs += len(atividade['subs'])
        concluidas_subs += sum(1 for sub in atividade['subs'] if sub['feito'])
    
    pendentes_subs = total_subs - concluidas_subs
    
    fig = go.Figure(data=[go.Pie(
        labels=['Concluídas', 'Pendentes'],
        values=[concluidas_subs, pendentes_subs],
        hole=.3,
        marker_colors=['#10B981', '#EF4444']
    )])
    
    fig.update_layout(
        title='Distribuição de Subatividades',
        height=400
    )
    
    return fig

def criar_grafico_status_relatorios(relatorios):
    """Cria gráfico de status dos relatórios"""
    if not relatorios:
        return None
    
    status_counts = {}
    for rel in relatorios:
        status = rel["status"] or "Não informado"
        status_counts[status] = status_counts.get(status, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(status_counts.keys()),
        values=list(status_counts.values()),
        hole=.2,
        marker_colors=['#10B981', '#F59E0B', '#EF4444', '#6B7280']
    )])
    
    fig.update_layout(
        title='Distribuição de Status dos Relatórios',
        height=400
    )
    
    return fig

def criar_grafico_produtividade_temporal(relatorios):
    """Cria gráfico de linha da produtividade ao longo do tempo"""
    if not relatorios or len(relatorios) < 2:
        return None
    
    datas = [r["data"] for r in relatorios]
    produtividades = [r["produtividade"] for r in relatorios]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=datas,
        y=produtividades,
        mode='lines+markers',
        name='Produtividade',
        line=dict(color='#3B82F6', width=3),
        marker=dict(size=8)
    ))
    
    # Adicionar média móvel
    if len(produtividades) > 5:
        media_movel = pd.Series(produtividades).rolling(window=5, min_periods=1).mean()
        fig.add_trace(go.Scatter(
            x=datas,
            y=media_movel,
            mode='lines',
            name='Média Móvel (5 dias)',
            line=dict(color='#EF4444', width=2, dash='dash')
        ))
    
    fig.update_layout(
        title='Evolução da Produtividade',
        xaxis_title='Data',
        yaxis_title='Produtividade (%)',
        template='plotly_white',
        height=400
    )
    
    return fig

# ============================================
# LOGIN
# ============================================
if 'usuario' not in st.session_state:
    st.markdown("<h1 class='main-header'>Painel de Controle de Obra</h1>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("Login")
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar", type="primary"):
            logado = verificar_login(user, pwd)
            if logado:
                st.session_state.usuario = {
                    "id": logado[0], 
                    "username": logado[1], 
                    "nome": logado[2], 
                    "tipo": logado[3]
                }
                st.success(f"Bem-vindo, {logado[2]}!")
                st.rerun()
            else:
                st.error("Credenciais inválidas")
    
    st.stop()

usuario = st.session_state.usuario

# ============================================
# MENU LATERAL
# ============================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
    st.title(f"Olá, {usuario['nome'].split()[0]}")
    st.caption(f"Função: {usuario['tipo'].title()}")

    opcoes = {
        "admin": [
            ("📊 Dashboard", "Dashboard"), 
            ("📝 Registrar Relatório", "Registrar Relatório"),
            ("👥 Gerenciar Usuários", "Gerenciar Usuários"), 
            ("🏗️ Gerenciar Projetos", "Gerenciar Projetos"),
            ("📸 Galeria de Fotos", "Galeria"), 
            ("🚨 Alertas", "Alertas"), 
            ("📈 Relatórios", "Relatórios"),
            ("⚙️ Configurações", "Configurações")
        ],
        "proprietario": [
            ("📊 Dashboard", "Dashboard"), 
            ("📸 Galeria de Fotos", "Galeria"),
            ("🚨 Alertas", "Alertas"), 
            ("📈 Relatórios", "Relatórios")
        ],
        "fiscal": [
            ("📊 Dashboard", "Dashboard"), 
            ("📝 Registrar Relatório", "Registrar Relatório"),
            ("🏗️ Gerenciar Projetos", "Gerenciar Projetos"), 
            ("📸 Galeria de Fotos", "Galeria"),
            ("🚨 Alertas", "Alertas")
        ]
    }
    
    opcoes_usuario = opcoes.get(usuario["tipo"], opcoes["fiscal"])
    pagina = st.radio("Navegação", [item[1] for item in opcoes_usuario],
                      format_func=lambda x: next((i[0] for i in opcoes_usuario if i[1] == x), x))

    # Obter projetos baseado no tipo de usuário
    projetos = obter_projetos_por_usuario(usuario["id"], usuario["tipo"])
    projeto_dict = {p["id"]: p["nome"] for p in projetos}
    
    # Verificar se há projetos disponíveis
    if projeto_dict:
        projeto_id = st.selectbox("Projeto", options=[0] + list(projeto_dict.keys()),
                                  format_func=lambda x: "Todos os Projetos" if x == 0 else projeto_dict.get(x, "Sem projeto"))
    else:
        st.info("Nenhum projeto disponível")
        projeto_id = 0

    if st.button("Sair", type="primary"):
        del st.session_state.usuario
        st.rerun()

st.session_state.filtros = {"projeto_id": projeto_id if projeto_id != 0 else None}

# ============================================
# DASHBOARD - VERSÃO MELHORADA COM GRÁFICOS
# ============================================
def exibir_dashboard(projeto_id):
    st.markdown("<h2 class='sub-header'>📊 Dashboard de Monitoramento</h2>", unsafe_allow_html=True)
    
    projetos_lista = obter_projetos_por_usuario(usuario["id"], usuario["tipo"])
    
    relatorios = obter_relatorios_usuario(
        usuario["id"], 
        admin=(usuario["tipo"] == "admin"), 
        projeto_id=projeto_id
    )
    
    # Obter último relatório para análise detalhada
    ultimo_relatorio = obter_ultimo_relatorio(projeto_id, usuario["id"], usuario["tipo"])
    
    # ========== CARDS DE RESUMO ==========
    st.subheader("📈 Resumo Geral")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🏗️ Projetos Ativos</div>
            <div class="card-value">{len(projetos_lista)}</div>
            <div class="card-subtitle">Total de projetos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📋 Relatórios</div>
            <div class="card-value">{len(relatorios)}</div>
            <div class="card-subtitle">Dias registrados</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        prod_media = np.mean([r["produtividade"] for r in relatorios]) if relatorios else 0
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📊 Produtividade Média</div>
            <div class="card-value">{prod_media:.1f}%</div>
            <div class="card-subtitle">Média geral</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Contar fotos
        if projeto_id and projeto_id != 0:
            fotos_por_atividade = contar_fotos_por_atividade(projeto_id, usuario["id"], usuario["tipo"])
        else:
            fotos_por_atividade = contar_fotos_por_atividade(None, usuario["id"], usuario["tipo"])
        total_fotos = sum(item['total_fotos'] for item in fotos_por_atividade) if fotos_por_atividade else 0
        
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📸 Total de Fotos</div>
            <div class="card-value">{total_fotos}</div>
            <div class="card-subtitle">Imagens registradas</div>
        </div>
        """, unsafe_allow_html=True)
    
    # ========== SEÇÃO DE GRÁFICOS ==========
    if relatorios or ultimo_relatorio:
        st.markdown("---")
        st.subheader("📊 Análise Visual de Dados")
        
        # Layout de gráficos
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            if relatorios:
                # Gráfico de status dos relatórios
                fig_status = criar_grafico_status_relatorios(relatorios)
                if fig_status:
                    st.plotly_chart(fig_status, use_container_width=True)
        
        with col_chart2:
            if relatorios and len(relatorios) > 1:
                # Gráfico de produtividade temporal
                fig_prod_temporal = criar_grafico_produtividade_temporal(relatorios)
                if fig_prod_temporal:
                    st.plotly_chart(fig_prod_temporal, use_container_width=True)
    
    # ========== ANÁLISE DO ÚLTIMO RELATÓRIO ==========
    if ultimo_relatorio:
        st.markdown("---")
        st.subheader(f"📅 Último Relatório: {ultimo_relatorio['data']}")
        
        # Parsear atividades do último relatório
        atividades_parsed = parse_atividades(ultimo_relatorio['atividades'])
        
        # Card de Status e Produtividade
        col_status, col_prod, col_fotos = st.columns(3)
        
        with col_status:
            status_color = {
                'Concluído': 'status-completed',
                'Em andamento': 'status-in-progress',
                'Atrasado': 'status-delayed',
                'Paralisado': 'status-pending'
            }.get(ultimo_relatorio['status'], 'status-pending')
            
            st.markdown(f"""
            <div class="card">
                <div class="card-title">📊 Status do Dia</div>
                <div><span class="status-badge {status_color}">{ultimo_relatorio['status'] or 'Não informado'}</span></div>
                <div class="card-subtitle">Projeto: {ultimo_relatorio['projeto_nome']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_prod:
            prod = ultimo_relatorio['produtividade'] or 0
            st.markdown(f"""
            <div class="card">
                <div class="card-title">🎯 Produtividade do Dia</div>
                <div class="card-value">{prod}%</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {prod}%"></div>
                </div>
                <div class="card-subtitle">Meta alcançada</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col_fotos:
            # Contar fotos do último relatório
            fotos_relatorio = obter_fotos_por_relatorio(ultimo_relatorio['id'])
            st.markdown(f"""
            <div class="card">
                <div class="card-title">📸 Fotos do Dia</div>
                <div class="card-value">{len(fotos_relatorio)}</div>
                <div class="card-subtitle">Imagens registradas</div>
            </div>
            """, unsafe_allow_html=True)
        
        # ========== GRÁFICO DE ATIVIDADES VS SUBATIVIDADES ==========
        if atividades_parsed:
            st.markdown("---")
            st.subheader("📋 Análise de Atividades")
            
            col_grafico1, col_grafico2 = st.columns(2)
            
            with col_grafico1:
                # Gráfico de barras: atividades vs subatividades
                fig_atividades = criar_grafico_atividades_vs_subatividades(atividades_parsed)
                if fig_atividades:
                    st.plotly_chart(fig_atividades, use_container_width=True)
            
            with col_grafico2:
                # Gráfico de pizza: distribuição de produtividade
                fig_pizza = criar_grafico_pizza_produtividade(atividades_parsed)
                if fig_pizza:
                    st.plotly_chart(fig_pizza, use_container_width=True)
            
            # Detalhes das atividades
            total_subatividades = sum(len(atividade['subs']) for atividade in atividades_parsed)
            subatividades_concluidas = sum(sum(1 for sub in atividade['subs'] if sub['feito']) for atividade in atividades_parsed)
            
            if total_subatividades > 0:
                prod_percentual = (subatividades_concluidas / total_subatividades) * 100
                st.markdown(f"""
                <div class="card">
                    <div class="card-title">📊 Resumo de Produtividade</div>
                    <div style="display: flex; justify-content: space-between; margin: 1rem 0;">
                        <div>
                            <div style="font-size: 0.9rem; color: #718096;">Subatividades totais</div>
                            <div style="font-size: 1.5rem; font-weight: bold;">{total_subatividades}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #718096;">Concluídas</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #10B981;">{subatividades_concluidas}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.9rem; color: #718096;">Pendentes</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: #F59E0B;">{total_subatividades - subatividades_concluidas}</div>
                        </div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {prod_percentual}%"></div>
                    </div>
                    <div class="card-subtitle">Taxa de conclusão: {prod_percentual:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
        
        # ========== OUTRAS INFORMAÇÕES DO RELATÓRIO ==========
        if ultimo_relatorio['plano_amanha']:
            st.markdown("---")
            st.subheader("📅 Plano para Amanhã")
            
            try:
                if ':' in ultimo_relatorio['plano_amanha']:
                    data_plano, plano_texto = ultimo_relatorio['plano_amanha'].split(':', 1)
                    data_plano = data_plano.strip()
                    plano_texto = plano_texto.strip()
                else:
                    data_plano = "Data não especificada"
                    plano_texto = ultimo_relatorio['plano_amanha']
                
                st.markdown(f"""
                <div class="plan-card">
                    <div class="card-title" style="color: white;">📋 Plano do Dia</div>
                    <div style="font-size: 1.1rem; margin-bottom: 0.5rem; color: white;">
                        <strong>Data:</strong> {data_plano}
                    </div>
                    <div style="background-color: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 8px; color: white;">
                        {plano_texto}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            except:
                st.markdown(f"""
                <div class="plan-card">
                    <div class="card-title" style="color: white;">📋 Plano para Amanhã</div>
                    <div style="background-color: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 8px; color: white;">
                        {ultimo_relatorio['plano_amanha']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    else:
        st.info("Nenhum relatório encontrado para o projeto selecionado.")
    
    # ========== LISTA DE PROJETOS DO USUÁRIO ==========
    if projetos_lista:
        st.markdown("---")
        st.subheader("🏗️ Meus Projetos")
        
        col_proj1, col_proj2, col_proj3 = st.columns(3)
        
        projetos_cols = [col_proj1, col_proj2, col_proj3]
        
        for idx, proj in enumerate(projetos_lista[:6]):  # Mostrar até 6 projetos
            with projetos_cols[idx % 3]:
                status_color = {
                    'Concluído': '#10B981',
                    'Em andamento': '#3B82F6',
                    'Atrasado': '#EF4444',
                    'Cancelado': '#6B7280',
                    'Planejamento': '#F59E0B'
                }.get(proj['status'], '#6B7280')
                
                st.markdown(f"""
                <div class="card" style="border-left-color: {status_color};">
                    <div class="card-title">{proj['nome']}</div>
                    <div style="font-size: 0.9rem; color: #6B7280; margin-bottom: 0.5rem;">
                        📍 {proj['localizacao']}
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <div style="font-size: 0.8rem; color: #9CA3AF;">Status</div>
                            <div style="font-weight: bold; color: {status_color};">{proj['status']}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.8rem; color: #9CA3AF;">Orçamento</div>
                            <div style="font-weight: bold;">{proj['orcamento_total']:,.0f} MT</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ============================================
# GERENCIAR USUÁRIOS
# ============================================
def exibir_gerenciar_usuarios():
    st.markdown("<h2 class='sub-header'>👥 Gerenciar Usuários</h2>", unsafe_allow_html=True)
    
    # Verificar se é admin
    if usuario["tipo"] != "admin":
        st.error("Apenas administradores podem acessar esta seção.")
        return
    
    # Inicializar estado para edição
    if "editando_usuario_id" not in st.session_state:
        st.session_state.editando_usuario_id = None
    
    # Botão para adicionar novo usuário
    if st.button("➕ Adicionar Novo Usuário", type="primary", use_container_width=True):
        st.session_state.editando_usuario_id = None
        st.rerun()
    
    # Lista de usuários
    usuarios = obter_usuarios()
    
    if usuarios:
        st.subheader("📋 Lista de Usuários")
        
        for user in usuarios:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
                
                with col1:
                    st.write(f"**👤 {user['nome']}**")
                    st.write(f"**📧 {user['email']}**")
                    st.write(f"**📱 {user['telefone'] or 'Não informado'}**")
                
                with col2:
                    tipo_texto = {
                        'admin': '🛡️ Administrador',
                        'proprietario': '🏢 Proprietário',
                        'fiscal': '👷 Fiscal'
                    }.get(user['tipo'], user['tipo'])
                    st.write(f"**Tipo:** {tipo_texto}")
                
                with col3:
                    status = "✅ Ativo" if user['ativo'] else "❌ Inativo"
                    st.write(f"**Status:** {status}")
                    st.write(f"**Username:** {user['username']}")
                
                with col4:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button("✏️ Editar", key=f"edit_user_{user['id']}", use_container_width=True):
                            st.session_state.editando_usuario_id = user['id']
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("🔗 Projetos", key=f"proj_user_{user['id']}", use_container_width=True):
                            st.session_state.gerenciar_projetos_usuario_id = user['id']
                            st.rerun()
                    
                    with col_btn3:
                        if user['id'] != usuario["id"]:  # Não permitir desativar a si mesmo
                            if user['ativo']:
                                if st.button("❌ Desativar", key=f"deact_{user['id']}", use_container_width=True):
                                    atualizar_usuario(
                                        user['id'], 
                                        user['username'], 
                                        user['nome'], 
                                        user['email'], 
                                        user['tipo'], 
                                        user['telefone'], 
                                        0
                                    )
                                    st.success(f"Usuário {user['nome']} desativado!")
                                    st.rerun()
                            else:
                                if st.button("✅ Ativar", key=f"act_{user['id']}", use_container_width=True):
                                    atualizar_usuario(
                                        user['id'], 
                                        user['username'], 
                                        user['nome'], 
                                        user['email'], 
                                        user['tipo'], 
                                        user['telefone'], 
                                        1
                                    )
                                    st.success(f"Usuário {user['nome']} ativado!")
                                    st.rerun()
    
    # Formulário para adicionar/editar usuário
    st.markdown("---")
    
    if st.session_state.editando_usuario_id is not None:
        # Modo edição
        user_edit = None
        for u in usuarios:
            if u['id'] == st.session_state.editando_usuario_id:
                user_edit = u
                break
        
        if user_edit:
            st.subheader(f"✏️ Editando Usuário: {user_edit['nome']}")
            
            with st.form(f"form_edit_usuario_{user_edit['id']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    username = st.text_input("Username", value=user_edit['username'])
                    nome = st.text_input("Nome Completo", value=user_edit['nome'])
                    email = st.text_input("Email", value=user_edit['email'])
                
                with col2:
                    tipo = st.selectbox(
                        "Tipo de Usuário",
                        options=['admin', 'proprietario', 'fiscal'],
                        format_func=lambda x: {
                            'admin': 'Administrador',
                            'proprietario': 'Proprietário',
                            'fiscal': 'Fiscal'
                        }[x],
                        index=['admin', 'proprietario', 'fiscal'].index(user_edit['tipo']) if user_edit['tipo'] in ['admin', 'proprietario', 'fiscal'] else 0
                    )
                    telefone = st.text_input("Telefone", value=user_edit['telefone'] or "")
                    ativo = st.checkbox("Usuário Ativo", value=bool(user_edit['ativo']))
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True, type="primary"):
                        try:
                            atualizar_usuario(
                                user_edit['id'], 
                                username, 
                                nome, 
                                email, 
                                tipo, 
                                telefone, 
                                1 if ativo else 0
                            )
                            st.success("Usuário atualizado com sucesso!")
                            st.session_state.editando_usuario_id = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar usuário: {str(e)}")
                
                with col_btn2:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.editando_usuario_id = None
                        st.rerun()
        else:
            st.session_state.editando_usuario_id = None
    else:
        # Modo adição
        st.subheader("➕ Adicionar Novo Usuário")
        
        with st.form("form_novo_usuario"):
            col1, col2 = st.columns(2)
            
            with col1:
                username = st.text_input("Username*", placeholder="nome.usuario")
                nome = st.text_input("Nome Completo*", placeholder="Nome Sobrenome")
                email = st.text_input("Email*", placeholder="usuario@exemplo.com")
            
            with col2:
                tipo = st.selectbox(
                    "Tipo de Usuário*",
                    options=['admin', 'proprietario', 'fiscal'],
                    format_func=lambda x: {
                        'admin': 'Administrador (acesso completo)',
                        'proprietario': 'Proprietário (acesso limitado a projetos)',
                        'fiscal': 'Fiscal (acesso a todos os projetos)'
                    }[x]
                )
                telefone = st.text_input("Telefone", placeholder="+258XXXXXXXXX")
                senha = st.text_input("Senha*", type="password", placeholder="Mínimo 6 caracteres")
                senha_confirm = st.text_input("Confirmar Senha*", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("💾 Salvar Novo Usuário", use_container_width=True, type="primary"):
                    # Validações
                    erros = []
                    if not username.strip():
                        erros.append("Username é obrigatório")
                    if not nome.strip():
                        erros.append("Nome completo é obrigatório")
                    if not email.strip():
                        erros.append("Email é obrigatório")
                    if not senha.strip():
                        erros.append("Senha é obrigatória")
                    if senha != senha_confirm:
                        erros.append("As senhas não coincidem")
                    if len(senha) < 6:
                        erros.append("A senha deve ter pelo menos 6 caracteres")
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        try:
                            novo_id = adicionar_usuario(username, nome, email, senha, tipo, telefone)
                            st.success(f"Usuário {nome} criado com sucesso! ID: {novo_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao criar usuário: {str(e)}")
            
            with col_btn2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.rerun()

# ============================================
# GERENCIAR PROJETOS - COM EXCLUSÃO
# ============================================
def exibir_gerenciar_projetos():
    st.markdown("<h2 class='sub-header'>🏗️ Gerenciar Projetos</h2>", unsafe_allow_html=True)
    
    # Verificar se é admin
    if usuario["tipo"] != "admin":
        st.error("Apenas administradores podem acessar esta seção.")
        return
    
    # Inicializar estados
    if "editando_projeto_id" not in st.session_state:
        st.session_state.editando_projeto_id = None
    
    if "confirmar_exclusao" not in st.session_state:
        st.session_state.confirmar_exclusao = None
    
    if "gerenciar_projetos_usuario_id" in st.session_state:
        exibir_gerenciar_projetos_usuario(st.session_state.gerenciar_projetos_usuario_id)
        return
    
    # Botão para adicionar novo projeto
    if st.button("➕ Adicionar Novo Projeto", type="primary", use_container_width=True):
        st.session_state.editando_projeto_id = None
        st.rerun()
    
    # Lista de projetos
    projetos = obter_projetos()
    
    if projetos:
        st.subheader("📋 Lista de Projetos")
        
        for proj in projetos:
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    st.write(f"**🏗️ {proj['nome']}**")
                    st.write(f"**📍 {proj['localizacao']}**")
                    st.write(f"**📝 {proj['descricao'][:100]}...**" if proj['descricao'] and len(proj['descricao']) > 100 else f"**📝 {proj['descricao'] or 'Sem descrição'}**")
                
                with col2:
                    st.write(f"**💰 {proj['orcamento_total']:,.2f} MT**")
                    st.write(f"**📅 Início:** {proj['data_inicio']}")
                    st.write(f"**📅 Término:** {proj['data_fim_previsto']}")
                    st.write(f"**📊 Status:** {proj['status']}")
                
                with col3:
                    st.write(f"**👤 Responsável:** {proj['responsavel_nome'] or 'Não definido'}")
                    st.write(f"**🏢 Proprietário:** {proj['proprietario_nome'] or 'Não definido'}")
                
                with col4:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button("✏️", key=f"edit_proj_{proj['id']}", help="Editar projeto", use_container_width=True):
                            st.session_state.editando_projeto_id = proj['id']
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("👥", key=f"access_proj_{proj['id']}", help="Gerenciar acessos", use_container_width=True):
                            st.session_state.gerenciar_acessos_projeto_id = proj['id']
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("🗑️", key=f"del_proj_{proj['id']}", help="Excluir projeto", use_container_width=True):
                            st.session_state.confirmar_exclusao = proj['id']
                            st.rerun()
    
    # Modal de confirmação de exclusão
    if st.session_state.confirmar_exclusao is not None:
        projeto_excluir = None
        for p in projetos:
            if p['id'] == st.session_state.confirmar_exclusao:
                projeto_excluir = p
                break
        
        if projeto_excluir:
            st.warning(f"⚠️ **Atenção!** Você está prestes a excluir o projeto **{projeto_excluir['nome']}**.")
            st.error("**Esta ação é irreversível e excluirá:**")
            st.error("- Todos os relatórios diários relacionados")
            st.error("- Todas as fotos do projeto")
            st.error("- Todas as associações de usuários ao projeto")
            
            col_confirm1, col_confirm2, col_confirm3 = st.columns([1, 1, 2])
            
            with col_confirm1:
                if st.button("✅ Confirmar Exclusão", type="primary", use_container_width=True):
                    try:
                        excluir_projeto(projeto_excluir['id'])
                        st.success(f"Projeto {projeto_excluir['nome']} excluído com sucesso!")
                        st.session_state.confirmar_exclusao = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir projeto: {str(e)}")
            
            with col_confirm2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.confirmar_exclusao = None
                    st.rerun()
    
    # Formulário para adicionar/editar projeto
    st.markdown("---")
    
    if st.session_state.editando_projeto_id is not None:
        # Modo edição
        proj_edit = None
        for p in projetos:
            if p['id'] == st.session_state.editando_projeto_id:
                proj_edit = p
                break
        
        if proj_edit:
            st.subheader(f"✏️ Editando Projeto: {proj_edit['nome']}")
            exibir_formulario_projeto(proj_edit)
        else:
            st.session_state.editando_projeto_id = None
    else:
        # Modo adição
        st.subheader("➕ Adicionar Novo Projeto")
        exibir_formulario_projeto()

def exibir_formulario_projeto(projeto=None):
    """Exibe formulário para adicionar/editar projeto"""
    # Obter lista de usuários para selecionar responsável e proprietário
    usuarios = obter_usuarios()
    usuarios_ativos = [u for u in usuarios if u['ativo']]
    
    # Filtrar responsáveis (admin ou fiscal)
    responsaveis_disponiveis = [u for u in usuarios_ativos if u['tipo'] in ['admin', 'fiscal']]
    responsavel_opcoes = {r['id']: f"{r['nome']} ({r['tipo']})" for r in responsaveis_disponiveis}
    
    # Filtrar proprietários
    proprietarios_disponiveis = [u for u in usuarios_ativos if u['tipo'] in ['proprietario']]
    proprietario_opcoes = {p['id']: f"{p['nome']} ({p['tipo']})" for p in proprietarios_disponiveis}
    
    with st.form(f"form_projeto_{projeto['id'] if projeto else 'novo'}"):
        col1, col2 = st.columns(2)
        
        with col1:
            nome = st.text_input("Nome do Projeto*", 
                                value=projeto['nome'] if projeto else "",
                                placeholder="Ex: Obra Xai-Xai, Edifício Central...")
            
            descricao = st.text_area("Descrição", 
                                    value=projeto['descricao'] if projeto else "",
                                    placeholder="Descreva o projeto...",
                                    height=100)
            
            localizacao = st.text_input("Localização*", 
                                       value=projeto['localizacao'] if projeto else "",
                                       placeholder="Ex: Xai-Xai, Gaza, Maputo...")
        
        with col2:
            orcamento_total = st.number_input("Orçamento Total (MT)*", 
                                             min_value=0.0, 
                                             value=float(projeto['orcamento_total']) if projeto else 0.0,
                                             step=1000.0)
            
            data_inicio = st.date_input("Data de Início*", 
                                       value=datetime.datetime.strptime(projeto['data_inicio'], "%Y-%m-%d").date() if projeto else date.today())
            
            data_fim_previsto = st.date_input("Data de Término Prevista*", 
                                            value=datetime.datetime.strptime(projeto['data_fim_previsto'], "%Y-%m-%d").date() if projeto else date.today() + timedelta(days=180))
            
            status = st.selectbox("Status", 
                                 options=["Em andamento", "Concluído", "Atrasado", "Cancelado", "Planejamento"],
                                 index=["Em andamento", "Concluído", "Atrasado", "Cancelado", "Planejamento"].index(projeto['status']) if projeto and projeto['status'] in ["Em andamento", "Concluído", "Atrasado", "Cancelado", "Planejamento"] else 0)
            
            # Selecionar responsável
            if responsavel_opcoes:
                responsavel_id = st.selectbox(
                    "Responsável*",
                    options=list(responsavel_opcoes.keys()),
                    format_func=lambda x: responsavel_opcoes[x],
                    index=list(responsavel_opcoes.keys()).index(projeto['responsavel_id']) if projeto and projeto['responsavel_id'] in responsavel_opcoes else 0
                )
            else:
                st.warning("Nenhum responsável disponível (admin ou fiscal ativo)")
                responsavel_id = None
            
            # Selecionar proprietário - NOVO CAMPO
            if proprietario_opcoes:
                proprietario_id = st.selectbox(
                    "Proprietário*",
                    options=list(proprietario_opcoes.keys()),
                    format_func=lambda x: proprietario_opcoes[x],
                    index=list(proprietario_opcoes.keys()).index(projeto['proprietario_id']) if projeto and projeto['proprietario_id'] in proprietario_opcoes else 0
                )
            else:
                st.warning("Nenhum proprietário disponível")
                proprietario_id = None
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if projeto:
                if st.form_submit_button("💾 Atualizar Projeto", use_container_width=True, type="primary"):
                    # Validações
                    erros = []
                    if not nome.strip():
                        erros.append("Nome do projeto é obrigatório")
                    if not localizacao.strip():
                        erros.append("Localização é obrigatória")
                    if orcamento_total <= 0:
                        erros.append("Orçamento deve ser maior que zero")
                    if data_fim_previsto <= data_inicio:
                        erros.append("Data de término deve ser após a data de início")
                    if not responsavel_id:
                        erros.append("Selecione um responsável")
                    if not proprietario_id:
                        erros.append("Selecione um proprietário")
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        try:
                            atualizar_projeto(
                                projeto['id'],
                                nome,
                                descricao,
                                localizacao,
                                orcamento_total,
                                data_inicio.strftime("%Y-%m-%d"),
                                data_fim_previsto.strftime("%Y-%m-%d"),
                                status,
                                responsavel_id,
                                proprietario_id
                            )
                            st.success(f"Projeto {nome} atualizado com sucesso!")
                            st.session_state.editando_projeto_id = None
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar projeto: {str(e)}")
            else:
                if st.form_submit_button("💾 Criar Projeto", use_container_width=True, type="primary"):
                    # Validações
                    erros = []
                    if not nome.strip():
                        erros.append("Nome do projeto é obrigatório")
                    if not localizacao.strip():
                        erros.append("Localização é obrigatória")
                    if orcamento_total <= 0:
                        erros.append("Orçamento deve ser maior que zero")
                    if data_fim_previsto <= data_inicio:
                        erros.append("Data de término deve ser após a data de início")
                    if not responsavel_id:
                        erros.append("Selecione um responsável")
                    if not proprietario_id:
                        erros.append("Selecione um proprietário")
                    
                    if erros:
                        for erro in erros:
                            st.error(erro)
                    else:
                        try:
                            novo_id = adicionar_projeto(
                                nome,
                                descricao,
                                localizacao,
                                orcamento_total,
                                data_inicio.strftime("%Y-%m-%d"),
                                data_fim_previsto.strftime("%Y-%m-%d"),
                                responsavel_id,
                                proprietario_id
                            )
                            st.success(f"Projeto {nome} criado com sucesso! ID: {novo_id}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao criar projeto: {str(e)}")
        
        with col_btn2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state.editando_projeto_id = None
                st.rerun()

def exibir_gerenciar_projetos_usuario(usuario_id):
    """Gerencia projetos de um usuário específico"""
    # Obter informações do usuário
    usuarios = obter_usuarios()
    usuario_info = None
    for u in usuarios:
        if u['id'] == usuario_id:
            usuario_info = u
            break
    
    if not usuario_info:
        st.error("Usuário não encontrado")
        st.session_state.pop("gerenciar_projetos_usuario_id", None)
        st.rerun()
        return
    
    st.subheader(f"🔗 Gerenciar Projetos para: {usuario_info['nome']} ({usuario_info['tipo']})")
    
    # Botão para voltar
    if st.button("↩️ Voltar para Lista de Usuários", use_container_width=True):
        st.session_state.pop("gerenciar_projetos_usuario_id", None)
        st.rerun()
    
    # Regras de acesso baseadas no tipo de usuário
    st.info(f"""
    **Regras de acesso para {usuario_info['tipo']}:**
    - **Administrador:** Acesso a todos os projetos automaticamente
    - **Fiscal:** Acesso a todos os projetos automaticamente
    - **Proprietário:** Acesso apenas aos projetos atribuídos abaixo
    """)
    
    # Se for admin ou fiscal, mostrar mensagem
    if usuario_info['tipo'] in ['admin', 'fiscal']:
        st.success(f"✅ {usuario_info['nome']} tem acesso a TODOS os projetos automaticamente (tipo: {usuario_info['tipo']})")
        
        # Mostrar lista de projetos disponíveis
        projetos = obter_projetos()
        if projetos:
            st.subheader("📋 Todos os Projetos Disponíveis")
            for proj in projetos:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**🏗️ {proj['nome']}**")
                        st.write(f"**📍 {proj['localizacao']}**")
                        st.write(f"**📊 Status:** {proj['status']}")
                    with col2:
                        st.success("✅ Acesso total")
        return
    
    # Para proprietários, gerenciar projetos específicos
    st.subheader("📋 Projetos Atribuídos")
    
    # Projetos já atribuídos
    projetos_atribuidos = obter_usuarios_por_projeto(usuario_id)
    projetos_geral = obter_projetos()
    
    # Mapear quais projetos já estão atribuídos
    projetos_atribuidos_ids = [p['id'] for p in projetos_atribuidos if p['id'] == usuario_id]
    
    if projetos_atribuidos:
        for proj in projetos_geral:
            # Verificar se este projeto está atribuído ao usuário
            projetos_usuario = obter_usuarios_por_projeto(proj['id'])
            usuario_tem_acesso = any(u['id'] == usuario_id for u in projetos_usuario)
            
            if usuario_tem_acesso:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.write(f"**🏗️ {proj['nome']}**")
                        st.write(f"**📍 {proj['localizacao']}**")
                    
                    with col2:
                        st.write(f"**📅 Início:** {proj['data_inicio']}")
                        st.write(f"**📊 Status:** {proj['status']}")
                    
                    with col3:
                        if st.button("❌ Remover", key=f"rem_proj_{proj['id']}_{usuario_id}", use_container_width=True):
                            try:
                                desassociar_usuario_projeto(usuario_id, proj['id'])
                                st.success(f"Acesso removido do projeto {proj['nome']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao remover acesso: {str(e)}")
    
    # Adicionar novo projeto
    st.subheader("➕ Adicionar Acesso a Projeto")
    
    # Projetos disponíveis (não atribuídos)
    projetos_disponiveis = obter_projetos_disponiveis_usuario(usuario_id)
    
    if projetos_disponiveis:
        with st.form(f"form_add_projeto_{usuario_id}"):
            projeto_opcoes = {p['id']: f"{p['nome']} - {p['localizacao']}" for p in projetos_disponiveis}
            projeto_selecionado = st.selectbox(
                "Selecione um projeto para adicionar acesso",
                options=list(projeto_opcoes.keys()),
                format_func=lambda x: projeto_opcoes[x]
            )
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.form_submit_button("🔗 Adicionar Acesso", use_container_width=True):
                    try:
                        associar_usuario_projeto(usuario_id, projeto_selecionado)
                        st.success("Acesso ao projeto adicionado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao adicionar acesso: {str(e)}")
            
            with col_btn2:
                if st.form_submit_button("❌ Cancelar", use_container_width=True):
                    st.rerun()
    else:
        st.info("Todos os projetos já estão atribuídos a este usuário ou não há projetos disponíveis.")

# ============================================
# GALERIA DE FOTOS COM ZOOM - AGRUPADA POR ATIVIDADE
# ============================================
def exibir_galeria(projeto_id):
    st.markdown("<h2 class='sub-header'>📸 Galeria de Fotos da Obra</h2>", unsafe_allow_html=True)

    # Obter fotos agrupadas por atividade
    fotos = obter_fotos_por_atividade(projeto_id, usuario["id"], usuario["tipo"])
    
    if not fotos:
        st.info("Nenhuma foto encontrada para o projeto selecionado.")
        return
    
    # Estatísticas
    atividades_unicas = set(f['atividade_agrupada'] for f in fotos)
    st.success(f"🖼️ {len(fotos)} foto(s) encontrada(s) em {len(atividades_unicas)} atividade(s)")
    
    # Filtro por atividade
    atividades_opcoes = ["Todas as atividades"] + sorted(list(atividades_unicas))
    atividade_selecionada = st.selectbox("Filtrar por atividade:", atividades_opcoes)
    
    if atividade_selecionada != "Todas as atividades":
        fotos_filtradas = [f for f in fotos if f['atividade_agrupada'] == atividade_selecionada]
    else:
        fotos_filtradas = fotos
    
    # Agrupar fotos por atividade
    fotos_por_atividade = {}
    for foto in fotos_filtradas:
        atividade = foto['atividade_agrupada']
        if atividade not in fotos_por_atividade:
            fotos_por_atividade[atividade] = []
        fotos_por_atividade[atividade].append(foto)
    
    # Exibir por atividade
    for atividade, lista_fotos in fotos_por_atividade.items():
        with st.expander(f"📁 {atividade} ({len(lista_fotos)} foto(s))", expanded=True):
            # Dividir em colunas
            num_colunas = 4
            colunas = st.columns(num_colunas)
            
            for idx, foto in enumerate(lista_fotos):
                with colunas[idx % num_colunas]:
                    with st.container(border=True):
                        try:
                            img = Image.open(foto["foto_path"])
                            image_zoom(
                                image=img, 
                                mode="dragmove", 
                                size=(250, 250), 
                                zoom_factor=5.0, 
                                keep_aspect_ratio=True
                            )
                        except Exception as e:
                            st.error(f"Erro ao carregar imagem: {e}")
                            continue

                        st.caption(f"**🏗️ {foto['projeto_nome']}**")
                        st.caption(f"**📅 {foto['data']}**")
                        
                        if foto["descricao"] and str(foto["descricao"]).strip():
                            st.caption(f"**📝 {foto['descricao'][:40]}...**")
                        
                        st.caption(f"**⏰ {str(foto['data_upload'])[:16].replace('T', ' ')}**")

                        try:
                            with open(foto["foto_path"], "rb") as f:
                                img_bytes = f.read()
                            
                            st.download_button(
                                "💾 Baixar", 
                                data=img_bytes, 
                                file_name=os.path.basename(foto["foto_path"]), 
                                mime="image/jpeg", 
                                key=f"dl_{foto['id']}_{idx}"
                            )
                        except:
                            st.warning("Erro no download")

# ============================================
# FUNCIONALIDADES SIMPLIFICADAS
# ============================================
def exibir_alertas():
    st.markdown("<h2 class='sub-header'>🚨 Alertas e Notificações</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="card" style="border-left-color: #EF4444;">
            <div class="card-title">⚠️ Projetos Atrasados</div>
            <div class="card-value">2</div>
            <div class="card-subtitle">Necessitam de atenção</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="card" style="border-left-color: #F59E0B;">
            <div class="card-title">📅 Prazos Próximos</div>
            <div class="card-value">3</div>
            <div class="card-subtitle">Vencimento em 7 dias</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="card" style="border-left-color: #10B981;">
            <div class="card-title">✅ Relatórios Pendentes</div>
            <div class="card-value">5</div>
            <div class="card-subtitle">Para esta semana</div>
        </div>
        """, unsafe_allow_html=True)

def exibir_configuracoes():
    st.markdown("<h2 class='sub-header'>⚙️ Configurações do Sistema</h2>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔐 Segurança", "📧 Notificações", "🌐 Sistema"])
    
    with tab1:
        st.subheader("Configurações de Segurança")
        st.checkbox("Exigir autenticação de dois fatores")
        st.checkbox("Log de atividades do usuário")
        st.checkbox("Notificar sobre logins suspeitos")
        
    with tab2:
        st.subheader("Configurações de Notificação")
        st.checkbox("Alertas por email", value=True)
        st.checkbox("Notificações no sistema", value=True)
        st.checkbox("Relatórios semanais automáticos")
        
    with tab3:
        st.subheader("Configurações do Sistema")
        st.selectbox("Idioma", ["Português", "Inglês", "Espanhol"])
        st.selectbox("Fuso Horário", ["GMT+2 (Maputo)", "GMT-3 (Brasília)"])
        st.number_input("Dias para retenção de dados", min_value=30, max_value=365, value=90)

# ============================================
# REGISTRO DE RELATÓRIOS - DO CÓDIGO 2
# ============================================
def exibir_registro_relatorios(usuario):
    st.markdown("<h2 class='sub-header'>📝 Registrar Relatório Diário</h2>", unsafe_allow_html=True)

    # Inicializar estados
    if "efet_adic" not in st.session_state:
        st.session_state.efet_adic = []
    if "atividades" not in st.session_state:
        st.session_state.atividades = []
    if "mostrar_formulario" not in st.session_state:
        st.session_state.mostrar_formulario = True

    # Se estamos editando, carregar dados
    editando = st.session_state.get("editando_relatorio")
    
    # Botão para voltar à lista (se estiver em modo edição)
    if editando:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("↩️ Voltar para Lista", use_container_width=True):
                st.session_state.editando_relatorio = None
                st.session_state.mostrar_formulario = False
                st.rerun()

    # FORMULÁRIO PRINCIPAL
    if st.session_state.mostrar_formulario:
        # Determinar modo (edição ou novo)
        modo = "edit" if editando else "novo"
        
        if editando:
            st.subheader(f"✏️ Editando Relatório #{editando['id']}")
            rel_id = editando["id"]
        else:
            st.subheader("📝 Novo Relatório Diário")
            rel_id = None

        # 1. Data do relatório (com dia da semana)
        hoje = date.today()
        if editando:
            data_edit = datetime.datetime.strptime(editando["data"], "%Y-%m-%d").date()
            data_rel = st.date_input("**📅 Data do relatório**", 
                                    value=data_edit,
                                    key="data_rel_input")
        else:
            data_rel = st.date_input("**📅 Data do relatório**", 
                                    value=hoje, 
                                    key="data_rel_input")
        
        dia_semana = get_day_name(data_rel)
        st.info(f"{dia_semana}: {data_rel.strftime('%d/%m/%Y')}")

        # 2. Projeto - MODIFICADO: Mostrar apenas projetos que o usuário tem acesso
        if usuario["tipo"] == "admin":
            projetos = obter_projetos()
        else:
            projetos = obter_projetos_por_usuario(usuario["id"])
        
        if not projetos:
            st.error("Você não tem acesso a nenhum projeto. Contacte o administrador.")
            return
        
        projeto_opcoes = {p["id"]: p["nome"] for p in projetos}
        
        if editando:
            projeto_selecionado = editando["projeto_id"]
        else:
            projeto_selecionado = list(projeto_opcoes.keys())[0] if projeto_opcoes else None
            
        projeto_id_form = st.selectbox("**🏗️ Projeto**", 
                                     options=list(projeto_opcoes.keys()), 
                                     format_func=lambda x: projeto_opcoes[x],
                                     index=list(projeto_opcoes.keys()).index(projeto_selecionado) if projeto_selecionado in projeto_opcoes else 0,
                                     key="projeto_input")

        # 3. Condições climáticas (Temperatura)
        st.markdown("### 🌤️ Condições climáticas (Temperatura)")
        if editando:
            temp_default = editando["temperatura"] or ""
        else:
            temp_default = ""
            
        temperatura = st.text_input("Descreva as condições climáticas:", 
                                   value=temp_default,
                                   placeholder="Ex: 28°C, céu limpo, vento fraco...",
                                   key="temperatura_input")

        # 4. Efetividades do Dia
        st.markdown("### 👥 Efetividades do Dia")
        
        # Carregar efetividades se estiver editando
        if editando and "equipe" in editando and editando["equipe"]:
            # Extrair informações da string de equipe salva
            equipe_salva = editando["equipe"]
            # Esta é uma simplificação - na implementação real você precisaria parsear a string
            pass
        
        col_ef1, col_ef2 = st.columns(2)
        with col_ef1:
            mestres = st.number_input("Mestres", min_value=0, key="mestres_input")
            motoristas = st.number_input("Motoristas", min_value=0, key="motoristas_input")
        
        with col_ef2:
            encarregado = st.checkbox("Encarregado presente", value=True, key="encarregado_input")
            fiscal = st.checkbox("Fiscal presente", value=True, key="fiscal_input")
            
            # Efetividades adicionais (fora do formulário principal)
            st.markdown("**Adicionar efetividade extra:**")
            cargo_temp = st.text_input("Cargo/Função", placeholder="Ex: Carpinteiro, Pedreiro...", key="cargo_temp_add")
            qtd_temp = st.number_input("Quantidade", min_value=1, value=1, key="qtd_temp_add")
            
            if st.button("➕ Adicionar", key="add_efet_extra"):
                if cargo_temp.strip():
                    st.session_state.efet_adic.append({"nome": cargo_temp.strip(), "qtd": qtd_temp})
                    st.rerun()

        # Listar efetividades extras
        if st.session_state.efet_adic:
            st.markdown("**Efetividades extras registradas:**")
            for i, e in enumerate(st.session_state.efet_adic):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{e['nome']}**")
                c2.write(f"Quantidade: {e['qtd']}")
                if c3.button("❌", key=f"rem_e_{i}"):
                    del st.session_state.efet_adic[i]
                    st.rerun()

        # 5. Atividades Realizadas
        st.markdown("### 📋 Atividades Realizadas")
        
        # Carregar atividades se estiver editando
        if editando and "atividades" in editando and editando["atividades"]:
            # Parsear atividades salvas
            atividades_salvas = editando["atividades"].split('\n')
            # Esta é uma simplificação - na implementação real você precisaria parsear melhor
            if not st.session_state.atividades and atividades_salvas:
                st.session_state.atividades = [{"titulo": atividade, "subs": []} for atividade in atividades_salvas]
        
        # Botão para adicionar nova atividade (fora do formulário)
        if st.button("➕ Adicionar Nova Atividade", key="add_ativ_principal"):
            st.session_state.atividades.append({"titulo": "", "subs": []})
            st.rerun()

        total_subs = 0
        feitas = 0
        atividades_texto = []
        
        # Listar atividades existentes
        for i, ativ in enumerate(st.session_state.atividades):
            with st.expander(f"Atividade {i+1} – {ativ.get('titulo','Nova atividade') or 'Nova atividade'}"):
                # Título da atividade principal
                titulo = st.text_input("Título da atividade principal", 
                                      value=ativ.get("titulo",""), 
                                      key=f"titulo_{i}",
                                      placeholder="Ex: Fundações, Alvenaria, Instalações...")
                st.session_state.atividades[i]["titulo"] = titulo

                # Botões de controle da atividade (fora do formulário dentro do expander)
                col_add, col_rem = st.columns(2)
                with col_add:
                    if st.button("➕ Adicionar subatividade", key=f"add_sub_{i}"):
                        st.session_state.atividades[i]["subs"].append({"nome": "", "feito": False})
                        st.rerun()
                with col_rem:
                    if st.button("❌ Remover esta atividade", key=f"rem_ativ_{i}"):
                        del st.session_state.atividades[i]
                        st.rerun()

                # Listar subatividades
                for j, sub in enumerate(ativ["subs"]):
                    c1, c2, c3 = st.columns([5, 2, 1])
                    with c1:
                        nome_sub = st.text_input("Nome da subatividade", 
                                               value=sub.get("nome",""), 
                                               key=f"sub_nome_{i}_{j}",
                                               placeholder="Ex: Preparação do terreno, Concretagem...")
                        st.session_state.atividades[i]["subs"][j]["nome"] = nome_sub
                    with c2:
                        feito = st.checkbox("✅ Concluído", 
                                          value=sub.get("feito",False), 
                                          key=f"sub_feito_{i}_{j}")
                        st.session_state.atividades[i]["subs"][j]["feito"] = feito
                        if feito: 
                            feitas += 1
                        total_subs += 1
                    with c3:
                        if st.button("🗑️", key=f"rem_sub_{i}_{j}"):
                            del st.session_state.atividades[i]["subs"][j]
                            st.rerun()

                # Adicionar ao texto final se houver título
                if titulo:
                    subs_txt = [f"{s['nome']} ({'✅ Concluído' if s['feito'] else '❌ Pendente'})" 
                              for s in ativ["subs"] if s["nome"]]
                    linha = f"{titulo}" + (": " + ", ".join(subs_txt) if subs_txt else "")
                    atividades_texto.append(linha)

        # Mostrar produtividade calculada
        produtividade = round((feitas / total_subs * 100), 1) if total_subs > 0 else 0
        st.metric("📊 **Produtividade Calculada**", f"{produtividade}%", 
                 help=f"{feitas} de {total_subs} subatividades concluídas")

        # 6. Status do dia
        st.markdown("### 📊 Status do dia")
        if editando:
            status_default = editando["status"] or "Em andamento"
        else:
            status_default = "Em andamento"
            
        status = st.selectbox("Selecione o status do dia:", 
                             ["Concluído", "Em andamento", "Atrasado", "Paralisado"], 
                             index=["Concluído", "Em andamento", "Atrasado", "Paralisado"].index(status_default) 
                             if status_default in ["Concluído", "Em andamento", "Atrasado", "Paralisado"] else 1,
                             key="status_input")

        # 7. Equipamentos utilizados
        st.markdown("### 🔧 Equipamentos utilizados")
        if editando:
            equip_default = editando["equipamentos"] or ""
        else:
            equip_default = ""
            
        equipamentos = st.text_area("Descreva os equipamentos utilizados:", 
                                   value=equip_default,
                                   placeholder="Ex: Betoneira, Compactador, Andaime...",
                                   height=80, 
                                   key="equipamentos_input")

        # 8. Ocorrências
        st.markdown("### ⚠️ Ocorrências")
        if editando:
            ocorr_default = editando["ocorrencias"] or ""
        else:
            ocorr_default = ""
            
        ocorrencias = st.text_area("Descreva as ocorrências do dia (se não houver, deixe em branco):", 
                                  value=ocorr_default,
                                  placeholder="Ex: Falta de material, Problemas técnicos, Incidentes...",
                                  height=100, 
                                  key="ocorrencias_input")

        # 9. Data do plano de atividade para outro dia
        st.markdown("### 📅 Data do plano de atividade para outro dia")
        if editando and editando["plano_amanha"]:
            # Extrair data do plano salvo
            try:
                data_plano_str = editando["plano_amanha"].split(":")[0].strip()
                data_plano_default = datetime.datetime.strptime(data_plano_str, "%Y-%m-%d").date()
            except:
                data_plano_default = hoje + timedelta(days=1)
        else:
            data_plano_default = hoje + timedelta(days=1)
            
        data_plano = st.date_input("Selecione a data do plano:", 
                                  value=data_plano_default, 
                                  key="data_plano_input")

        # 10. Plano para amanhã
        st.markdown("### 📋 Plano para amanhã")
        if editando and editando["plano_amanha"]:
            # Extrair texto do plano salvo
            try:
                plano_texto = ":".join(editando["plano_amanha"].split(":")[1:]).strip()
                plano_default = plano_texto
            except:
                plano_default = ""
        else:
            plano_default = ""
            
        plano_amanha_input = st.text_area("Descreva o plano para o próximo dia:", 
                                         value=plano_default,
                                         placeholder="Ex: Continuar alvenaria, Iniciar instalações elétricas...",
                                         height=100, 
                                         key="plano_amanha_input")
        
        # Combinar data e plano
        plano_amanha = f"{data_plano.strftime('%Y-%m-%d')}: {plano_amanha_input}" if plano_amanha_input.strip() else ""

        # 11. Observações adicionais
        st.markdown("### 📝 Observações adicionais")
        if editando:
            obs_default = editando["observacoes"] or ""
        else:
            obs_default = ""
            
        observacoes = st.text_area("Adicione observações adicionais:", 
                                  value=obs_default,
                                  placeholder="Ex: Material necessário para amanhã, Pessoal em falta...",
                                  height=80, 
                                  key="observacoes_input")

        # 12. Fotos do Dia
        st.markdown("### 📸 Fotos do Dia")
        fotos_uploaded = st.file_uploader("Envie as fotos (máx. 10MB cada)", 
                                         type=["jpg", "jpeg", "png"], 
                                         accept_multiple_files=True, 
                                         key="fotos_uploader",
                                         help="Selecione as fotos do dia de trabalho")

        fotos_com_descricao = []
        if fotos_uploaded:
            st.write("**🖼️ Pré-visualização das fotos:**")
            for i, foto in enumerate(fotos_uploaded):
                col_img, col_desc = st.columns([1, 2])
                with col_img:
                    st.image(foto, width=200, caption=f"Foto {i+1}")
                with col_desc:
                    desc = st.text_input(f"Descrição da foto {i+1}", 
                                        placeholder="Ex: Fundações concluídas, Andar 1 completo...",
                                        key=f"desc_foto_{i}")
                    fotos_com_descricao.append({"file": foto, "descricao": desc})

        # Botões de ação
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.mostrar_formulario = False
                st.session_state.editando_relatorio = None
                st.session_state.efet_adic = []
                st.session_state.atividades = []
                st.rerun()
        
        with col_btn2:
            if modo == "edit":
                if st.button(f"💾 Atualizar Relatório #{rel_id}", use_container_width=True, type="primary"):
                    # Processar envio
                    processar_envio_relatorio(data_rel, projeto_id_form, usuario, temperatura, atividades_texto,
                                            mestres, motoristas, encarregado, fiscal,
                                            equipamentos, ocorrencias, plano_amanha, status, 
                                            produtividade, observacoes, fotos_com_descricao, modo, rel_id)
            else:
                if st.button("💾 Salvar Novo Relatório", use_container_width=True, type="primary"):
                    # Processar envio
                    processar_envio_relatorio(data_rel, projeto_id_form, usuario, temperatura, atividades_texto,
                                            mestres, motoristas, encarregado, fiscal,
                                            equipamentos, ocorrencias, plano_amanha, status, 
                                            produtividade, observacoes, fotos_com_descricao, modo, None)

    else:
        # MOSTRAR LISTA DE RELATÓRIOS (quando não está mostrando formulário)
        exibir_lista_relatorios(usuario)

def processar_envio_relatorio(data_rel, projeto_id_form, usuario, temperatura, atividades_texto,
                             mestres, motoristas, encarregado, fiscal,
                             equipamentos, ocorrencias, plano_amanha, status, 
                             produtividade, observacoes, fotos_com_descricao, modo, rel_id):
    """Processa o envio do relatório"""
    # Validações
    erros = []
    
    if not atividades_texto:
        erros.append("❌ Adicione pelo menos uma atividade principal com título")
    if not temperatura.strip():
        erros.append("❌ As condições climáticas são obrigatórias")
    if not projeto_id_form:
        erros.append("❌ Selecione um projeto")

    if erros:
        for erro in erros:
            st.error(erro)
    else:
        # Montar string da equipe
        equipe = []
        if mestres > 0: 
            equipe.append(f"{mestres} mestre(s)")
        if motoristas > 0: 
            equipe.append(f"{motoristas} motorista(s)")
        if encarregado: 
            equipe.append("encarregado")
        if fiscal: 
            equipe.append("fiscal")
        
        for e in st.session_state.efet_adic:
            if e["nome"]: 
                equipe.append(f"{e['qtd']} {e['nome']}(s)")
        
        equipe_str = ", ".join(equipe) if equipe else "Nenhuma equipe registrada"

        # Preparar dados para salvar
        dados = {
            "temperatura": temperatura or "Não informado",
            "atividades": "\n".join(atividades_texto),
            "equipe": equipe_str,
            "equipamentos": equipamentos or "Nenhum equipamento utilizado",
            "ocorrencias": ocorrencias or "Nenhuma ocorrência registrada",
            "plano_amanha": plano_amanha,
            "status": status,
            "produtividade": produtividade,
            "observacoes": observacoes or "Nenhuma observação adicional"
        }

        try:
            if modo == "edit":
                rel_id = salvar_relatorio(data_rel, projeto_id_form, usuario["id"], **dados)
                mensagem = f"Relatório #{rel_id} atualizado com sucesso!"
            else:
                rel_id = salvar_relatorio(data_rel, projeto_id_form, usuario["id"], **dados)
                mensagem = f"Novo relatório #{rel_id} criado com sucesso!"

            # Salvar fotos (apenas se for novo)
            if fotos_com_descricao and modo == "novo":
                for item in fotos_com_descricao:
                    salvar_foto(rel_id, item["file"].getvalue(), item["descricao"])

            st.success(mensagem)
            
            # Limpar estados
            st.session_state.mostrar_formulario = False
            st.session_state.editando_relatorio = None
            st.session_state.efet_adic = []
            st.session_state.atividades = []
            
            # Gerar e disponibilizar PDF
            pdf = gerar_pdf(rel_id)
            if pdf:
                st.session_state.pdf_gerado = pdf
                st.session_state.pdf_nome = f"relatorio_{data_rel}.pdf"
            
            st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao salvar relatório: {str(e)}")

def exibir_lista_relatorios(usuario):
    """Exibe a lista de relatórios com opção para criar novo"""
    st.markdown("### 📋 Relatórios Registrados")
    
    # Botão para criar novo relatório
    if st.button("➕ Novo Relatório", use_container_width=True, type="primary"):
        st.session_state.mostrar_formulario = True
        st.session_state.editando_relatorio = None
        st.session_state.efet_adic = []
        st.session_state.atividades = []
        st.rerun()
    
    # Exibir lista de relatórios
    admin = usuario["tipo"] == "admin"
    rels = obter_relatorios_usuario(
        usuario["id"], 
        admin=admin, 
        projeto_id=st.session_state.filtros["projeto_id"]
    )

    if rels:
        for r in rels:
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 2, 3])
                
                with col1:
                    st.write(f"**📅 {r['data']}**")
                    st.write(f"**🏗️ {r['projeto_nome']}**")
                    st.write(f"**👤 {r['usuario_nome']}**")
                
                with col2:
                    status_color = {
                        'Concluído': 'green',
                        'Em andamento': 'orange',
                        'Atrasado': 'red',
                        'Paralisado': 'gray'
                    }.get(r['status'], 'blue')
                    st.markdown(f"**Status:** <span style='color:{status_color};'>{r['status'] or 'Não informado'}</span>", unsafe_allow_html=True)
                    st.write(f"**Produtividade:** {r['produtividade'] or 0}%")
                
                with col3:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    with col_btn1:
                        if st.button("👁️ Ver", key=f"ver_{r['id']}"):
                            pdf = gerar_pdf(r['id'])
                            if pdf:
                                st.session_state.pdf_gerado = pdf
                                st.session_state.pdf_nome = f"relatorio_{r['data']}.pdf"
                                st.rerun()
                    with col_btn2:
                        if st.button("✏️ Editar", key=f"edit_{r['id']}"):
                            st.session_state.editando_relatorio = carregar_relatorio(r['id'])
                            st.session_state.mostrar_formulario = True
                            st.rerun()
                    with col_btn3:
                        if st.button("🗑️", key=f"del_{r['id']}"):
                            if st.checkbox("Confirmar exclusão?", key=f"conf_del_{r['id']}"):
                                apagar_relatorio(r['id'])
                                st.success("Relatório apagado!")
                                st.rerun()
    else:
        st.info("Nenhum relatório registrado ainda. Clique em 'Novo Relatório' para começar.")
    
    # Download do PDF se existir
    if "pdf_gerado" in st.session_state:
        st.markdown("---")
        st.markdown("### 📄 Relatório Gerado")
        st.download_button(
            label="📥 Baixar Relatório em PDF",
            data=st.session_state.pdf_gerado,
            file_name=st.session_state.pdf_nome,
            mime="application/pdf",
            use_container_width=True
        )
        
        if st.button("Fechar", use_container_width=True):
            st.session_state.pop("pdf_gerado", None)
            st.session_state.pop("pdf_nome", None)
            st.rerun()

# ============================================
# RELATÓRIOS (versão simplificada do Código 2)
# ============================================
def exibir_relatorios(projeto_id):
    st.markdown("<h2 class='sub-header'>📊 Relatórios Diários</h2>", unsafe_allow_html=True)
    
    admin = usuario["tipo"] == "admin"
    rels = obter_relatorios_usuario(usuario["id"], admin=admin, projeto_id=projeto_id)
    
    if not rels:
        st.info("Nenhum relatório encontrado.")
        return

    df = pd.DataFrame(rels, columns=["ID", "Data", "Projeto", "Usuário", "Status", "Produtividade"])
    df["Data"] = pd.to_datetime(df["Data"]).dt.strftime('%d/%m/%Y')
    df["Produtividade"] = df["Produtividade"].astype(str) + "%"
    
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### 📄 Baixar Relatórios")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Baixar Todos (ZIP)", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento...")
    
    with col2:
        if st.button("📊 Resumo Excel", use_container_width=True):
            st.info("Funcionalidade em desenvolvimento...")

    for r in rels[:5]:  # Mostrar apenas os 5 mais recentes
        with st.expander(f"Relatório #{r['id']} - {r['data']}"):
            pdf = gerar_pdf(r['id'])
            if pdf:
                st.download_button(
                    "📄 Baixar PDF", 
                    data=pdf, 
                    file_name=f"relatorio_{r['data']}.pdf",
                    mime="application/pdf", 
                    key=f"rel_pdf_{r['id']}"
                )
            st.write(f"**Projeto:** {r['projeto_nome']}")
            st.write(f"**Status:** {r['status'] or 'Não informado'}")
            st.write(f"**Produtividade:** {r['produtividade']}%")

# ============================================
# NAVEGAÇÃO FINAL
# ============================================
if pagina == "Dashboard":
    exibir_dashboard(st.session_state.filtros["projeto_id"])
elif pagina == "Registrar Relatório":
    exibir_registro_relatorios(usuario)
elif pagina == "Gerenciar Usuários":
    exibir_gerenciar_usuarios()
elif pagina == "Gerenciar Projetos":
    exibir_gerenciar_projetos()
elif pagina == "Galeria":
    exibir_galeria(st.session_state.filtros["projeto_id"])
elif pagina == "Alertas":
    exibir_alertas()
elif pagina == "Relatórios":
    exibir_relatorios(st.session_state.filtros["projeto_id"])
elif pagina == "Configurações":
    exibir_configuracoes()
else:
    st.markdown(f"<h2 class='sub-header'>{pagina}</h2>", unsafe_allow_html=True)
    st.info(f"Seção {pagina} em desenvolvimento...")