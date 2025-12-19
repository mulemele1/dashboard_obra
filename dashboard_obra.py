import streamlit as st
import pandas as pd
import numpy as np
import datetime
from datetime import date, timedelta
import sqlite3
import hashlib
import io
import os
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
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÕES AUXILIARES
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
    
    # Tabela de projetos
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
        FOREIGN KEY (responsavel_id) REFERENCES usuarios (id))""")
    
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

    # Inserir usuários padrão se não existirem
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ('fiscal', 'Fiscal da Obra', 'fiscal@obra.com', hashlib.sha256('fiscal123'.encode()).hexdigest(), 'fiscal', '+258840000000'),
            ('proprietario', 'Proprietário', 'prop@obra.com', hashlib.sha256('prop123'.encode()).hexdigest(), 'proprietario', '+258850000000'),
            ('admin', 'Administrador', 'admin@obra.com', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin', '+258860000000')
        ]
        c.executemany("INSERT INTO usuarios (username,nome,email,senha_hash,tipo,telefone) VALUES (?,?,?,?,?,?)", usuarios_padrao)

    # Inserir projeto padrão se não existir
    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id)
                  VALUES (?,?,?,?,?,?,?)""",
                  ('Obra Xai-Xai', 'Requalificação com expansão', 'Xai-Xai, Gaza', 2500000.0, '2025-02-01', '2025-08-01', 1))
    
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
    c.execute("SELECT p.*, u.nome as responsavel_nome FROM projetos p LEFT JOIN usuarios u ON p.responsavel_id = u.id ORDER BY p.data_inicio DESC")
    return c.fetchall()

def obter_projetos_por_usuario(usuario_id):
    """Obtém projetos que um usuário tem acesso"""
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT p.*, u.nome as responsavel_nome 
        FROM projetos p 
        LEFT JOIN usuarios u ON p.responsavel_id = u.id
        LEFT JOIN usuarios_projetos up ON p.id = up.projeto_id
        WHERE up.usuario_id = ? OR p.responsavel_id = ?
        ORDER BY p.data_inicio DESC
    """, (usuario_id, usuario_id))
    return c.fetchall()

def obter_usuarios():
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios ORDER BY nome")
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

def adicionar_projeto(nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id):
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id))
        conn.commit()
        return c.lastrowid
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

def atualizar_projeto(projeto_id, nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, status, responsavel_id):
    c = conn.cursor()
    try:
        c.execute("""
            UPDATE projetos 
            SET nome=?, descricao=?, localizacao=?, orcamento_total=?, data_inicio=?, data_fim_previsto=?, status=?, responsavel_id=?
            WHERE id=?
        """, (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, status, responsavel_id, projeto_id))
        conn.commit()
        return True
    except Exception as e:
        raise Exception(f"Erro: {str(e)}")

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
            SELECT id FROM projetos WHERE responsavel_id = ?
        )
        ORDER BY p.nome
    """, (usuario_id, usuario_id))
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
                   JOIN usuarios_projetos up ON p.id = up.projeto_id
                   WHERE up.usuario_id = ?"""
        params = [usuario_id]
    
    if projeto_id and projeto_id != 0:
        where_clause = " AND" if params else " WHERE"
        query += f" {where_clause} r.projeto_id = ?"
        params.append(projeto_id)
    
    query += " ORDER BY r.data DESC"
    c.execute(query, params)
    return c.fetchall()

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

def salvar_foto(relatorio_id, foto_bytes, descricao=""):
    os.makedirs("fotos_obra", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"foto_{relatorio_id}_{timestamp}.jpg"
    caminho = os.path.join("fotos_obra", nome)
    
    with open(caminho, "wb") as f:
        f.write(foto_bytes)
    
    c = conn.cursor()
    c.execute("INSERT INTO fotos_obra (relatorio_id, foto_path, descricao) VALUES (?,?,?)", (relatorio_id, caminho, descricao))
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

# ============================================
# LOGIN
# ============================================
if 'usuario' not in st.session_state:
    st.markdown("<h1 class='main-header'>Painel de Controle de Obra</h1>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        st.subheader("Login")
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        
        if st.form_submit_button("Entrar"):
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

    # Para usuários que não são admin, mostrar apenas projetos que têm acesso
    if usuario["tipo"] == "admin":
        projetos = obter_projetos()
    else:
        projetos = obter_projetos_por_usuario(usuario["id"])
    
    projeto_dict = {p["id"]: p["nome"] for p in projetos}
    
    # Verificar se há projetos disponíveis
    if projeto_dict:
        projeto_id = st.selectbox("Projeto", options=[0] + list(projeto_dict.keys()),
                                  format_func=lambda x: "Todos os Projetos" if x == 0 else projeto_dict.get(x, "Sem projeto"))
    else:
        st.info("Nenhum projeto disponível")
        projeto_id = 0

    if st.button("Sair"):
        del st.session_state.usuario
        st.rerun()

st.session_state.filtros = {"projeto_id": projeto_id if projeto_id != 0 else None}

# ============================================
# DASHBOARD
# ============================================
def exibir_dashboard(projeto_id):
    st.markdown("<h2 class='sub-header'>Dashboard</h2>", unsafe_allow_html=True)
    
    if usuario["tipo"] == "admin":
        projetos_lista = obter_projetos()
    else:
        projetos_lista = obter_projetos_por_usuario(usuario["id"])
    
    relatorios = obter_relatorios_usuario(
        usuario["id"], 
        admin=(usuario["tipo"] == "admin"), 
        projeto_id=projeto_id
    )
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Projetos", len(projetos_lista))
    col2.metric("Relatórios", len(relatorios))
    col3.metric("Dias Registrados", len(set(r["data"] for r in relatorios)) if relatorios else 0)
    prod_media = np.mean([r["produtividade"] for r in relatorios]) if relatorios else 0
    col4.metric("Produtividade Média", f"{prod_media:.1f}%")

    if relatorios:
        df_data = {
            "ID": [r["id"] for r in relatorios],
            "Data": [r["data"] for r in relatorios],
            "Projeto": [r["projeto_nome"] for r in relatorios],
            "Usuário": [r["usuario_nome"] for r in relatorios],
            "Status": [r["status"] or "Não informado" for r in relatorios],
            "Produtividade": [f"{r['produtividade'] or 0}%" for r in relatorios],
        }
        df = pd.DataFrame(df_data)
        df["Data"] = pd.to_datetime(df["Data"]).dt.strftime('%d/%m/%Y')

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Produtividade por Dia")
            chart_data = pd.Series(
                [r["produtividade"] for r in relatorios], 
                index=pd.to_datetime([r["data"] for r in relatorios])
            )
            st.line_chart(chart_data)
        
        with col2:
            st.subheader("Status dos Dias")
            status_counts = pd.Series([r["status"] or "Não informado" for r in relatorios]).value_counts()
            st.bar_chart(status_counts)
    else:
        st.info("Nenhum relatório registrado ainda.")

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
                        if st.button("✏️ Editar", key=f"edit_user_{user['id']}"):
                            st.session_state.editando_usuario_id = user['id']
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("🔗 Projetos", key=f"proj_user_{user['id']}"):
                            st.session_state.gerenciar_projetos_usuario_id = user['id']
                            st.rerun()
                    
                    with col_btn3:
                        if user['id'] != usuario["id"]:  # Não permitir desativar a si mesmo
                            if user['ativo']:
                                if st.button("❌", key=f"deact_{user['id']}"):
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
                                if st.button("✅", key=f"act_{user['id']}"):
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
                    if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
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
# GERENCIAR PROJETOS
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
                col1, col2, col3 = st.columns([3, 2, 3])
                
                with col1:
                    st.write(f"**🏗️ {proj['nome']}**")
                    st.write(f"**📍 {proj['localizacao']}**")
                    st.write(f"**📝 {proj['descricao'][:100]}...**" if proj['descricao'] and len(proj['descricao']) > 100 else f"**📝 {proj['descricao'] or 'Sem descrição'}**")
                
                with col2:
                    st.write(f"**💰 {proj['orcamento_total']:,.2f} MT**")
                    st.write(f"**📅 Início:** {proj['data_inicio']}")
                    st.write(f"**📅 Término:** {proj['data_fim_previsto']}")
                    st.write(f"**📊 Status:** {proj['status']}")
                    st.write(f"**👤 Responsável:** {proj['responsavel_nome'] or 'Não definido'}")
                
                with col3:
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button("✏️ Editar", key=f"edit_proj_{proj['id']}"):
                            st.session_state.editando_projeto_id = proj['id']
                            st.rerun()
                    
                    with col_btn2:
                        if st.button("👥 Acessos", key=f"access_proj_{proj['id']}"):
                            st.session_state.gerenciar_acessos_projeto_id = proj['id']
                            st.rerun()
                    
                    with col_btn3:
                        if st.button("🗑️", key=f"del_proj_{proj['id']}"):
                            st.warning("Funcionalidade de exclusão em desenvolvimento")
    
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
    # Obter lista de usuários para selecionar responsável
    usuarios = obter_usuarios()
    usuarios_opcoes = {u['id']: f"{u['nome']} ({u['tipo']})" for u in usuarios if u['ativo']}
    
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
            responsaveis_disponiveis = [u for u in usuarios if u['ativo'] and u['tipo'] in ['admin', 'fiscal']]
            responsavel_opcoes = {r['id']: f"{r['nome']} ({r['tipo']})" for r in responsaveis_disponiveis}
            
            if responsavel_opcoes:
                responsavel_id = st.selectbox(
                    "Responsável",
                    options=list(responsavel_opcoes.keys()),
                    format_func=lambda x: responsavel_opcoes[x],
                    index=list(responsavel_opcoes.keys()).index(projeto['responsavel_id']) if projeto and projeto['responsavel_id'] in responsavel_opcoes else 0
                )
            else:
                st.warning("Nenhum responsável disponível (admin ou fiscal ativo)")
                responsavel_id = None
        
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
                                responsavel_id
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
                                responsavel_id
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
                        if st.button("❌ Remover", key=f"rem_proj_{proj['id']}_{usuario_id}"):
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
# REGISTRO DE RELATÓRIOS - VERSÃO SIMPLIFICADA
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
# GALERIA DE FOTOS COM ZOOM - CORRIGIDA
# ============================================
def exibir_galeria(projeto_id):
    st.markdown("<h2 class='sub-header'>📸 Galeria de Fotos da Obra</h2>", unsafe_allow_html=True)

    c = conn.cursor()
    query = """
    SELECT f.id, f.foto_path, f.descricao, f.data_upload, r.data, p.nome
    FROM fotos_obra f
    JOIN relatorios_diarios r ON f.relatorio_id = r.id
    JOIN projetos p ON r.projeto_id = p.id
    """
    params = []
    
    if projeto_id and projeto_id != 0:
        query += " WHERE r.projeto_id = ?"
        params.append(projeto_id)
    elif usuario["tipo"] != "admin":
        # Para não-admins, filtrar apenas projetos que têm acesso
        query += " WHERE r.projeto_id IN (SELECT projeto_id FROM usuarios_projetos WHERE usuario_id = ?)"
        params.append(usuario["id"])
    
    query += " ORDER BY f.data_upload DESC"
    c.execute(query, params)
    fotos = c.fetchall()

    if not fotos:
        st.info("Nenhuma foto encontrada para o projeto selecionado.")
        return

    st.success(f"🖼️ {len(fotos)} foto(s) encontrada(s)")

    # Criar colunas dinamicamente
    num_colunas = 4
    cols = st.columns(num_colunas)
    
    for idx, foto in enumerate(fotos):
        with cols[idx % num_colunas]:
            with st.container(border=True):
                try:
                    img = Image.open(foto["foto_path"])
                    # CORREÇÃO: Removido o parâmetro 'key' que causa o erro
                    image_zoom(
                        image=img, 
                        mode="dragmove", 
                        size=(280, 280), 
                        zoom_factor=5.0, 
                        keep_aspect_ratio=True
                    )
                except Exception as e:
                    st.error(f"Erro ao carregar imagem: {e}")
                    continue

                st.caption(f"🏗️ **{foto['nome']}**")
                st.caption(f"📅 **{foto['data']}**")
                
                if foto["descricao"] and str(foto["descricao"]).strip():
                    st.caption(f"📝 **{foto['descricao'][:50]}...**")
                
                st.caption(f"⏰ **{str(foto['data_upload'])[:16].replace('T', ' ')}**")

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
# RELATÓRIOS (versão simplificada)
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
elif pagina == "Relatórios":
    exibir_relatorios(st.session_state.filtros["projeto_id"])
elif pagina == "Galeria":
    exibir_galeria(st.session_state.filtros["projeto_id"])
else:
    st.markdown(f"<h2 class='sub-header'>{pagina}</h2>", unsafe_allow_html=True)
    st.info(f"Seção {pagina} em desenvolvimento...")