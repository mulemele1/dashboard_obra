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

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(page_title="Dashboard de Obra", page_icon="ESCALENO", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-header {font-size: 2.8rem; color: #1E40AF; text-align: center; margin: 1rem 0;}
    .sub-header  {font-size: 1.8rem; color: #2563EB; margin-top: 2rem; border-bottom: 2px solid #E5E7EB; padding-bottom: 0.5rem;}
    .metric-card {background: linear-gradient(135deg, #6366f1, #8b5cf6); color:white; padding:1.5rem; border-radius:12px; text-align:center;}
</style>
""", unsafe_allow_html=True)

# ============================================
# BANCO DE DADOS
# ============================================
def init_database():
    conn = sqlite3.connect('controle_obra.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, email TEXT UNIQUE NOT NULL, senha_hash TEXT NOT NULL, tipo TEXT NOT NULL, telefone TEXT, ativo INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS projetos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, descricao TEXT, localizacao TEXT, orcamento_total REAL, data_inicio DATE, data_fim_previsto DATE, status TEXT DEFAULT 'Em andamento', responsavel_id INTEGER, FOREIGN KEY (responsavel_id) REFERENCES usuarios (id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS relatorios_diarios (id INTEGER PRIMARY KEY AUTOINCREMENT, data DATE NOT NULL, projeto_id INTEGER NOT NULL, usuario_id INTEGER NOT NULL, temperatura TEXT, atividades TEXT NOT NULL, equipe TEXT, equipamentos TEXT, ocorrencias TEXT, acidentes TEXT DEFAULT 'Nenhum', plano_amanha TEXT, status TEXT, produtividade INTEGER, observacoes TEXT, FOREIGN KEY (projeto_id) REFERENCES projetos (id), FOREIGN KEY (usuario_id) REFERENCES usuarios (id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS fotos_obra (id INTEGER PRIMARY KEY AUTOINCREMENT, relatorio_id INTEGER NOT NULL, foto_path TEXT NOT NULL, descricao TEXT, data_upload DATETIME DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (relatorio_id) REFERENCES relatorios_diarios (id))""")

    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        usuarios_padrao = [
            ('fiscal', 'Fiscal da Obra', 'fiscal@obra.com', hashlib.sha256('fiscal123'.encode()).hexdigest(), 'fiscal', '+258840000000'),
            ('proprietario', 'Proprietário', 'prop@obra.com', hashlib.sha256('prop123'.encode()).hexdigest(), 'proprietario', '+258850000000'),
            ('admin', 'Administrador', 'admin@obra.com', hashlib.sha256('admin123'.encode()).hexdigest(), 'admin', '+258860000000')
        ]
        c.executemany("INSERT INTO usuarios (username,nome,email,senha_hash,tipo,telefone) VALUES (?,?,?,?,?,?)", usuarios_padrao)

    c.execute("SELECT COUNT(*) FROM projetos")
    if c.fetchone()[0] == 0:
        c.execute("""INSERT INTO projetos (nome, descricao, localizacao, orcamento_total, data_inicio, data_fim_previsto, responsavel_id) VALUES (?,?,?,?,?,?,?)""",
                  ('Obra Xai-Xai', 'Requalificação com expansão', 'Xai-Xai, Gaza', 2500000.0, '2025-02-01', '2025-08-01', 1))

    conn.commit()
    return conn

conn = init_database()

# ============================================
# FUNÇÕES AUXILIARES
# ============================================
def verificar_login(username, password):
    c = conn.cursor()
    hash_senha = hashlib.sha256(password.encode()).hexdigest()
    c.execute("SELECT id,username,nome,tipo FROM usuarios WHERE username=? AND senha_hash=? AND ativo=1", (username, hash_senha))
    return c.fetchone()

def obter_projetos():
    c = conn.cursor()
    c.execute("SELECT p.*, u.nome FROM projetos p LEFT JOIN usuarios u ON p.responsavel_id = u.id ORDER BY p.data_inicio DESC")
    return c.fetchall()

def obter_relatorios(projeto_id=None):
    c = conn.cursor()
    query = """SELECT r.id, r.data, p.nome, u.nome, r.status, r.produtividade 
               FROM relatorios_diarios r 
               JOIN projetos p ON r.projeto_id=p.id 
               JOIN usuarios u ON r.usuario_id=u.id"""
    params = []
    if projeto_id:
        query += " WHERE r.projeto_id=?"
        params.append(projeto_id)
    query += " ORDER BY r.data DESC"
    c.execute(query, params)
    return c.fetchall()

def salvar_relatorio(data, projeto_id, usuario_id, **dados):
    c = conn.cursor()
    c.execute("SELECT id FROM relatorios_diarios WHERE data=? AND projeto_id=?", (data, projeto_id))
    existente = c.fetchone()
    produtividade = int(dados.get('produtividade', 0))

    if existente:
        c.execute("""UPDATE relatorios_diarios SET temperatura=?, atividades=?, equipe=?, equipamentos=?, ocorrencias=?, acidentes=?, plano_amanha=?, status=?, produtividade=?, observacoes=? WHERE id=?""",
                  (dados.get('temperatura'), dados.get('atividades'), dados.get('equipe'), dados.get('equipamentos'), dados.get('ocorrencias'), dados.get('acidentes'), dados.get('plano_amanha'), dados.get('status'), produtividade, dados.get('observacoes'), existente[0]))
        rel_id = existente[0]
    else:
        c.execute("""INSERT INTO relatorios_diarios (data,projeto_id,usuario_id,temperatura,atividades,equipe,equipamentos,ocorrencias,acidentes,plano_amanha,status,produtividade,observacoes) 
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (data, projeto_id, usuario_id, dados.get('temperatura'), dados.get('atividades'), dados.get('equipe'), dados.get('equipamentos'), dados.get('ocorrencias'), dados.get('acidentes'), dados.get('plano_amanha'), dados.get('status'), produtividade, dados.get('observacoes')))
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
    c.execute("""SELECT r.*, p.nome, u.nome FROM relatorios_diarios r 
                 JOIN projetos p ON r.projeto_id=p.id 
                 JOIN usuarios u ON r.usuario_id=u.id WHERE r.id=?""", (rel_id,))
    rel = c.fetchone()
    if not rel: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = [Paragraph("Relatório Diário de Obra", styles['Title']), Spacer(1, 20)]
    data = [["Data", str(rel[1])], ["Projeto", rel[14]], ["Responsável", rel[15]], ["Status", rel[11]], ["Produtividade", f"{rel[12]}%"]]
    t = Table(data, colWidths=[100, 400])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f0f0')), ('GRID',(0,0),(-1,-1),1,colors.black)]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    secoes = [("Clima", rel[4]), ("Atividades", rel[5]), ("Equipe", rel[6]), ("Equipamentos", rel[7]), ("Ocorrências", rel[8]), ("Acidentes", rel[9]), ("Plano Amanhã", rel[10]), ("Observações", rel[13])]
    for titulo, texto in secoes:
        if texto and texto.strip():
            elements.append(Paragraph(f"<b>{titulo}:</b> {texto}", styles['Normal']))
            elements.append(Spacer(1, 10))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================
# LOGIN
# ============================================
if 'usuario' not in st.session_state:
    st.markdown("<h1 class='main-header'>Painel de Controle de Obra de Construção</h1>", unsafe_allow_html=True)
    with st.form("login_form"):
        st.subheader("Login")
        user = st.text_input("Usuário")
        pwd = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            logado = verificar_login(user, pwd)
            if logado:
                st.session_state.usuario = {"id": logado[0], "username": logado[1], "nome": logado[2], "tipo": logado[3]}
                st.success(f"Bem-vindo, {logado[2]}!")
                st.rerun()
            else:
                st.error("Credenciais inválidas")
    st.stop()

usuario = st.session_state.usuario

# ============================================
# MENU LATERAL PERSONALIZADO POR TIPO DE USUÁRIO
# ============================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=80)
    st.title(f"Olá, {usuario['nome'].split()[0]}")
    st.caption(f"Função: {usuario['tipo'].title()}")

    # Opções por tipo de usuário
    opcoes = {
        "admin": [
            ("📊 Dashboard", "Dashboard"),
            ("📝 Registrar Relatório", "Registrar Relatório"),
            ("👥 Gerenciar Usuários", "Gerenciar Usuários"),
            ("🏗️ Gerenciar Projetos", "Gerenciar Projetos"),
            ("📸 Galeria de Fotos", "Galeria"),
            ("🚨 Alertas", "Alertas"),
            ("📈 Relatórios", "Relatórios"),
            ("⚙️ Configurações", "Configurações"),
        ],
        "proprietario": [
            ("📊 Dashboard", "Dashboard"),
            ("📸 Galeria de Fotos", "Galeria"),
            ("🚨 Alertas", "Alertas"),
            ("📈 Relatórios", "Relatórios"),
        ],
        "fiscal": [
            ("📊 Dashboard", "Dashboard"),
            ("📝 Registrar Relatório", "Registrar Relatório"),
            ("🏗️ Gerenciar Projetos", "Gerenciar Projetos"),
            ("📸 Galeria de Fotos", "Galeria"),
            ("🚨 Alertas", "Alertas"),
        ]
    }

    opcoes_usuario = opcoes.get(usuario["tipo"], opcoes["fiscal"])
    pagina = st.radio(
        "Navegação",
        [item[1] for item in opcoes_usuario],
        format_func=lambda x: [i[0] for i in opcoes_usuario if i[1]==x][0]
    )

    projetos = obter_projetos()
    projeto_dict = {p[0]: p[1] for p in projetos}
    projeto_id = st.selectbox(
        "Projeto",
        options=[0] + list(projeto_dict.keys()),
        format_func=lambda x: "Todos os Projetos" if x == 0 else projeto_dict.get(x, "Sem projeto")
    )

    if st.button("Sair"):
        del st.session_state.usuario
        st.rerun()

st.session_state.filtros = {"projeto_id": projeto_id if projeto_id != 0 else None}

# ============================================
# DASHBOARD
# ============================================
def exibir_dashboard(projeto_id):
    st.markdown("<h2 class='sub-header'>Dashboard</h2>", unsafe_allow_html=True)
    projetos = obter_projetos()
    relatorios = obter_relatorios(projeto_id)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Projetos", len(projetos))
    col2.metric("Relatórios", len(relatorios))
    col3.metric("Dias Registrados", len(set(r[1] for r in relatorios)) if relatorios else 0)
    prod_media = np.mean([r[5] for r in relatorios]) if relatorios else 0
    col4.metric("Produtividade Média", f"{prod_media:.1f}%")

    if relatorios:
        df = pd.DataFrame(relatorios, columns=["ID", "Data", "Projeto", "Usuário", "Status", "Produtividade"])
        df["Data"] = pd.to_datetime(df["Data"])

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Produtividade por Dia")
            chart_data = df.set_index("Data")["Produtividade"]
            st.line_chart(chart_data)

        with col2:
            st.subheader("Status dos Dias")
            status_count = df["Status"].value_counts()
            st.bar_chart(status_count)

# ============================================
# FORMULÁRIO DE RELATÓRIO COM VALIDAÇÃO
# ============================================
def exibir_formulario_relatorio(usuario):
    st.markdown("<h2 class='sub-header'>Registrar Relatório Diário</h2>", unsafe_allow_html=True)

    # Estados dinâmicos
    if "efet_adic" not in st.session_state: st.session_state.efet_adic = []
    if "atividades" not in st.session_state: st.session_state.atividades = []

    # --- EFETIVIDADES ---
    st.markdown("---")
    st.subheader("Efetividades do Dia")
    col1, col2 = st.columns(2)
    with col1:
        mestres = st.number_input("Mestres", min_value=0, value=1)
        motoristas = st.number_input("Motoristas", min_value=0, value=1)
        subordinados = st.number_input("Subordinados", min_value=0, value=6)
        encarregado = st.checkbox("Encarregado presente", value=True)
        fiscal = st.checkbox("Fiscal presente", value=True)

    with col2:
        st.markdown("**Adicionar efetividade extra:**")
        col_cargo, col_qtd = st.columns([3, 2])
        with col_cargo:
            cargo_temp = st.text_input("Cargo/Função", placeholder="Ex: Carpinteiro...", key="cargo_temp")
        with col_qtd:
            qtd_temp = st.number_input("Quantidade", min_value=1, value=1, key="qtd_temp")
        if st.button("Adicionar efetividade extra"):
            if cargo_temp.strip():
                st.session_state.efet_adic.append({"nome": cargo_temp.strip(), "qtd": qtd_temp})
                st.rerun()

    if st.session_state.efet_adic:
        st.markdown("**Efetividades extras:**")
        for i, e in enumerate(st.session_state.efet_adic):
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.info(e["nome"])
            c2.info(f"{e['qtd']} pessoa(s)")
            if c3.button("Remover", key=f"rem_e{i}"):
                del st.session_state.efet_adic[i]
                st.rerun()

    # --- ADICIONAR ATIVIDADE PRINCIPAL ---
    st.markdown("---")
    st.subheader("Atividades Realizadas")
    if st.button("Adicionar Atividade Principal"):
        st.session_state.atividades.append({"titulo": "", "subs": []})
        st.rerun()

    # --- GERENCIAR ATIVIDADES E SUBATIVIDADES ---
    total_subs = 0
    feitas = 0
    atividades_texto = []

    for i, ativ in enumerate(st.session_state.atividades):
        with st.expander(f"Atividade {i+1} – {ativ.get('titulo','Nova atividade')}"):
            titulo = st.text_input("Título da atividade principal", value=ativ.get("titulo",""), key=f"titulo_{i}")
            st.session_state.atividades[i]["titulo"] = titulo

            col_add, col_rem = st.columns(2)
            with col_add:
                if st.button(f"Adicionar subatividade", key=f"add_sub_{i}"):
                    st.session_state.atividades[i]["subs"].append({"nome": "", "feito": False})
                    st.rerun()
            with col_rem:
                if st.button(f"Remover esta atividade", key=f"rem_ativ_{i}"):
                    del st.session_state.atividades[i]
                    st.rerun()

            for j, sub in enumerate(ativ["subs"]):
                c1, c2, c3 = st.columns([5, 2, 1])
                with c1:
                    nome_sub = st.text_input("Nome da subatividade", value=sub.get("nome",""), key=f"sub_nome_{i}_{j}")
                    st.session_state.atividades[i]["subs"][j]["nome"] = nome_sub
                with c2:
                    feito = st.checkbox("Feito", value=sub.get("feito",False), key=f"sub_feito_{i}_{j}")
                    st.session_state.atividades[i]["subs"][j]["feito"] = feito
                    if feito:
                        feitas += 1
                    total_subs += 1
                with c3:
                    if st.button("X", key=f"rem_sub_{i}_{j}"):
                        del st.session_state.atividades[i]["subs"][j]
                        st.rerun()

            if titulo:
                subs_txt = [f"{s['nome']} ({'Feito' if s['feito'] else 'Não Feito'})" for s in ativ["subs"] if s["nome"]]
                linha = titulo + (": " + ", ".join(subs_txt) if subs_txt else "")
                atividades_texto.append(linha)

    produtividade = round((feitas / total_subs * 100), 1) if total_subs > 0 else 0
    st.metric("Produtividade Calculada", f"{produtividade}%", help=f"{feitas} de {total_subs} subatividades concluídas")

    # --- FORMULÁRIO PRINCIPAL ---
    with st.form("form_relatorio", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            data_rel = st.date_input("Data do relatório", value=date.today())
            temperatura = st.text_input("Condições climáticas")
            status = st.selectbox("Status do dia", ["Concluído", "Em andamento", "Atrasado", "Paralisado"])
        with col2:
            projetos = obter_projetos()
            projeto_opcoes = {p[0]: p[1] for p in projetos}
            projeto_id_form = st.selectbox("Projeto", options=list(projeto_opcoes.keys()), format_func=lambda x: projeto_opcoes[x])

        equipamentos = st.text_area("Equipamentos utilizados", height=80)

        ocorrencia_check = st.checkbox("Ocorreu ocorrência?")
        ocorrencias = ""
        if ocorrencia_check:
            ocorrencias = st.text_area("Descreva a ocorrência", height=100)

        acidente_check = st.checkbox("Ocorreu acidente?")
        acidentes = "Nenhum"
        if acidente_check:
            acidentes = st.text_area("Descreva o acidente (detalhes, gravidade, ações tomadas)", height=120)

        data_plano = st.date_input("Data do plano", value=date.today() + timedelta(days=1))
        plano_amanha = st.text_area("Plano para amanhã", height=100)
        plano_amanha = f"{data_plano}: {plano_amanha}" if plano_amanha.strip() else ""

        observacoes = st.text_area("Observações adicionais", height=80)
        fotos = st.file_uploader("Fotos do dia", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        enviado = st.form_submit_button("SALVAR RELATÓRIO")

    # --- VALIDAÇÃO E SALVAR ---
    if enviado:
        erros = []
        if not data_rel:
            erros.append("Data do relatório é obrigatória")
        if not projeto_id_form:
            erros.append("Projeto é obrigatório")
        if not temperatura.strip():
            erros.append("Condições climáticas são obrigatórias")
        if not status:
            erros.append("Status do dia é obrigatório")
        if not atividades_texto:
            erros.append("Adicione pelo menos uma atividade principal com título")
        if ocorrencia_check and not ocorrencias.strip():
            erros.append("Descreva a ocorrência se selecionada")
        if acidente_check and not acidentes.strip():
            erros.append("Descreva o acidente se selecionado")

        if erros:
            for erro in erros:
                st.error(erro)
        else:
            equipe = [f"{mestres} mestre(s)" if mestres > 0 else "", 
                      f"{motoristas} motorista(s)" if motoristas > 0 else "", 
                      f"{subordinados} subordinado(s)" if subordinados > 0 else ""]
            if encarregado: equipe.append("encarregado")
            if fiscal: equipe.append("fiscal")
            for e in st.session_state.efet_adic:
                if e["nome"] and e["qtd"] > 0:
                    equipe.append(f"{e['qtd']} {e['nome']}(s)")
            equipe = [e for e in equipe if e]
            equipe_str = ", ".join(equipe) if equipe else "Nenhuma equipe registrada"

            dados = {
                "temperatura": temperatura or "Não informado",
                "atividades": "\n".join(atividades_texto),
                "equipe": equipe_str,
                "equipamentos": equipamentos or "Nenhum",
                "ocorrencias": ocorrencias or "Nenhuma ocorrência registrada",
                "acidentes": acidentes,
                "plano_amanha": plano_amanha,
                "status": status,
                "produtividade": produtividade,
                "observacoes": observacoes
            }

            rel_id = salvar_relatorio(data_rel, projeto_id_form, usuario["id"], **dados)
            if fotos:
                for f in fotos:
                    salvar_foto(rel_id, f.getvalue(), "")

            pdf = gerar_pdf(rel_id)
            if pdf:
                st.session_state.pdf_gerado = pdf
                st.session_state.pdf_nome = f"relatorio_{data_rel}.pdf"

            st.success(f"Relatório #{rel_id} salvo com sucesso!")
            st.session_state.efet_adic = []
            st.session_state.atividades = []
            st.rerun()

    if "pdf_gerado" in st.session_state:
        st.download_button("Baixar Relatório em PDF", data=st.session_state.pdf_gerado,
                           file_name=st.session_state.pdf_nome, mime="application/pdf")
        if st.button("Criar Novo Relatório"):
            st.session_state.pop("pdf_gerado", None)
            st.rerun()

# ============================================
# NAVEGAÇÃO FINAL
# ============================================
if pagina == "Dashboard":
    exibir_dashboard(st.session_state.filtros["projeto_id"])

elif pagina == "Registrar Relatório":
    exibir_formulario_relatorio(usuario)

elif pagina == "Relatórios":
    st.markdown("<h2 class='sub-header'>Relatórios Diários</h2>", unsafe_allow_html=True)
    rels = obter_relatorios(st.session_state.filtros["projeto_id"])
    if rels:
        df = pd.DataFrame(rels, columns=["ID", "Data", "Projeto", "Responsável", "Status", "Produtividade"])
        st.dataframe(df, use_container_width=True)
        for r in rels:
            with st.expander(f"Relatório #{r[0]} - {r[1]}"):
                pdf = gerar_pdf(r[0])
                if pdf:
                    st.download_button("Baixar PDF", pdf, f"relatorio_{r[1]}.pdf", "application/pdf")
    else:
        st.info("Nenhum relatório encontrado.")

elif pagina in ["Galeria", "Alertas", "Gerenciar Usuários", "Gerenciar Projetos", "Configurações"]:
    st.markdown(f"<h2 class='sub-header'>{pagina}</h2>", unsafe_allow_html=True)
    st.info(f"Seção {pagina} em desenvolvimento...")

elif pagina == "Sair":
    del st.session_state.usuario
    st.rerun()