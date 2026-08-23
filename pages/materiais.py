# pages/materiais.py
# -*- coding: utf-8 -*-

import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

st.set_page_config(
    page_title="Materiais | Carvalho Ferreira",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"


# =============================================================================
# ESTILO SOFISTICADO (DARK & PREMIUM)
# =============================================================================

st.markdown(
    """
    <style>
    /* Fundo geral escuro / sofisticado */
    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
    }

    /* Container principal */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 900px;
    }

    /* Títulos visíveis e elegantes */
    h1, h2, h3 {
        color: #f7f5ef !important;
    }

    /* Código do imóvel em destaque limpo */
    .codigo-imovel {
        font-size: 1.1rem;
        font-weight: 700;
        color: #d4af37;
        background: #1a1f2c;
        padding: 6px 14px;
        border-radius: 8px;
        display: inline-block;
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }

    /* Botões de navegação e ações principais */
    .stButton > button,
    .stDownloadButton > button,
    .stLinkButton > button {
        border-radius: 10px;
        font-weight: 600;
        background-color: #1f2937;
        color: #f7f5ef;
        border: 1px solid #374151;
        transition: all 0.2s ease-in-out;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover,
    .stLinkButton > button:hover {
        background-color: #374151;
        border-color: #d4af37;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# CONEXÕES
# =============================================================================

@st.cache_resource
def conectar_drive():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES_DRIVE
    )
    return build("drive", "v3", credentials=creds)


@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES_SHEETS
    )
    return build("sheets", "v4", credentials=creds)


# =============================================================================
# AUXILIARES
# =============================================================================

def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


@st.cache_data(ttl=300)
def buscar_legendas(codigo):
    try:
        service = conectar_sheets()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=f"'{NOME_ABA}'!A:AZ")
            .execute()
        )
        rows = result.get("values", [])
        if not rows:
            return "", ""

        cabecalho = [normalizar(h) for h in rows[0]]
        codigo_busca = normalizar(codigo)

        for row in rows[1:]:
            if not row:
                continue
            while len(row) < len(cabecalho):
                row.append("")

            if normalizar(row[0]) == codigo_busca:
                dados = {cabecalho[i]: row[i] for i in range(len(cabecalho))}
                legenda1 = dados.get("LEGENDA 1", "") or dados.get("LEGENDA1", "")
                legenda2 = dados.get("LEGENDA 2", "") or dados.get("LEGENDA2", "")
                return legenda1, legenda2

        return "", ""
    except Exception as e:
        st.error(f"Erro ao buscar legendas: {e}")
        return "", ""


@st.cache_data(ttl=300)
def encontrar_pasta_imovel(codigo):
    service = conectar_drive()
    query = (
        f"name contains '{codigo}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resultados = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id,name,webViewLink)", pageSize=10)
        .execute()
    )
    pastas = resultados.get("files", [])
    if pastas:
        return pastas[0]
    return None


@st.cache_data(ttl=300)
def listar_subpastas(pasta_pai_id):
    service = conectar_drive()
    query = (
        f"'{pasta_pai_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resultados = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id,name,webViewLink)", pageSize=50)
        .execute()
    )
    return resultados.get("files", [])


@st.cache_data(ttl=300)
def listar_arquivos(pasta_id):
    service = conectar_drive()
    query = (
        f"'{pasta_id}' in parents "
        f"and mimeType != 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    resultados = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id,name,mimeType,webViewLink)",
            pageSize=100,
            orderBy="name",
        )
        .execute()
    )
    return resultados.get("files", [])


def baixar_arquivo(file_id):
    service = conectar_drive()
    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None


def encontrar_pasta(subpastas, nome):
    nome_normalizado = normalizar(nome)
    for pasta in subpastas:
        if normalizar(pasta["name"]) == nome_normalizado:
            return pasta
    return None


def arquivos_da_pasta(subpastas, nome):
    pasta = encontrar_pasta(subpastas, nome)
    if not pasta:
        return []
    return listar_arquivos(pasta["id"])


# =============================================================================
# VALIDAÇÃO DA SESSÃO
# =============================================================================

codigo = st.session_state.get("codigo_materiais") or st.session_state.get("codigo_busca", "")

if not codigo:
    st.warning("Nenhum imóvel selecionado. Volte para o painel e escolha um imóvel.")
    if st.button("← Voltar para o painel"):
        st.switch_page("app.py")
    st.stop()


# =============================================================================
# CABEÇALHO LIMPO E VISÍVEL
# =============================================================================

col_voltar, col_vazio = st.columns([1, 5])
with col_voltar:
    if st.button("← Voltar"):
        st.switch_page("app.py")

# Exibição limpa do código com alta visibilidade
st.markdown(f'<div class="codigo-imovel">🏷️ IMÓVEL: {codigo}</div>', unsafe_allow_html=True)
st.title("Central de Materiais")


# =============================================================================
# CARREGAMENTO DO DRIVE
# =============================================================================

with st.spinner("Carregando pastas..."):
    pasta_imovel = encontrar_pasta_imovel(codigo)

if not pasta_imovel:
    st.error(f"Não encontrei a pasta do imóvel {codigo} no Google Drive.")
    st.stop()

pasta_imovel_id = pasta_imovel["id"]
subpastas = listar_subpastas(pasta_imovel_id)
legenda1, legenda2 = buscar_legendas(codigo)


# =============================================================================
# MENU PRINCIPAL DE BOTÕES
# =============================================================================

st.markdown("---")

if "material_selecionado" not in st.session_state:
    st.session_state["material_selecionado"] = "LEGENDA_1"

col_b1, col_b2, col_b3, col_b4 = st.columns(4)
with col_b1:
    if st.button("📝 Legenda 1", use_container_width=True):
        st.session_state["material_selecionado"] = "LEGENDA_1"
with col_b2:
    if st.button("📝 Legenda 2", use_container_width=True):
        st.session_state["material_selecionado"] = "LEGENDA_2"
with col_b3:
    if st.button("📱 Status", use_container_width=True):
        st.session_state["material_selecionado"] = "STATUS"
with col_b4:
    if st.button("📲 Posts", use_container_width=True):
        st.session_state["material_selecionado"] = "POSTS"

col_b5, col_b6, col_b7, col_vazio_menu = st.columns(4)
with col_b5:
    if st.button("📸 Fotos", use_container_width=True):
        st.session_state["material_selecionado"] = "FOTOS"
with col_b6:
    if st.button("📄 PDF", use_container_width=True):
        st.session_state["material_selecionado"] = "PDF"
with col_b7:
    if st.button("🎥 Vídeos", use_container_width=True):
        st.session_state["material_selecionado"] = "VIDEOS"

st.markdown("---")

selecao = st.session_state["material_selecionado"]


# =============================================================================
# EXIBIÇÃO DO CONTEÚDO SELECIONADO
# =============================================================================

# --- LEGENDA 1 ---
if selecao == "LEGENDA_1":
    st.markdown("### 📝 Legenda 1")
    if legenda1:
        st.text_area("Texto da Legenda 1", value=legenda1, height=200, label_visibility="collapsed")
        st.code(legenda1, language=None)
        st.info("💡 Toque acima para copiar o texto com facilidade.")
    else:
        st.info("Nenhuma Legenda 1 cadastrada na planilha.")

# --- LEGENDA 2 ---
elif selecao == "LEGENDA_2":
    st.markdown("### 📝 Legenda 2")
    if legenda2:
        st.text_area("Texto da Legenda 2", value=legenda2, height=200, label_visibility="collapsed")
        st.code(legenda2, language=None)
        st.info("💡 Toque acima para copiar o texto com facilidade.")
    else:
        st.info("Nenhuma Legenda 2 cadastrada na planilha.")

# --- STATUS ---
elif selecao == "STATUS":
    st.markdown("### 📱 Materiais para Status")
    arquivos_status = arquivos_da_pasta(subpastas, "STATUS")
    if not arquivos_status:
        st.info("Nenhum material de Status encontrado.")
    else:
        colunas = st.columns(2)
        for indice, arquivo in enumerate(arquivos_status):
            with colunas[indice % 2]:
                st.markdown(f"**{arquivo['name']}**")
                dados = baixar_arquivo(arquivo["id"])
                if dados:
                    st.image(dados, use_container_width=True)
                    st.download_button(
                        "📥 Baixar / Compartilhar",
                        data=dados,
                        file_name=arquivo["name"],
                        key=f"dl_status_{arquivo['id']}",
                        use_container_width=True,
                    )

# --- POSTS ---
elif selecao == "POSTS":
    st.markdown("### 📲 Materiais para Posts")
    arquivos_posts = arquivos_da_pasta(subpastas, "POSTS")
    if not arquivos_posts:
        st.info("Nenhum post encontrado.")
    else:
        colunas = st.columns(2)
        for indice, arquivo in enumerate(arquivos_posts):
            with colunas[indice % 2]:
                st.markdown(f"**{arquivo['name']}**")
                dados = baixar_arquivo(arquivo["id"])
                if dados:
                    st.image(dados, use_container_width=True)
                    st.download_button(
                        "📥 Baixar / Compartilhar",
                        data=dados,
                        file_name=arquivo["name"],
                        key=f"dl_post_{arquivo['id']}",
                        use_container_width=True,
                    )

# --- FOTOS TRATADAS (Otimizado para abrir direto no Drive) ---
elif selecao == "FOTOS":
    st.markdown("### 📸 Fotos Tratadas")
    pasta_fotos = encontrar_pasta(subpastas, "FOTOS TRATADAS")
    
    st.info(
        "⚡ **Clique no Botão abaixo:** Para acessar as fotos do Imóvel. "
    )
    
    if pasta_fotos and pasta_fotos.get("webViewLink"):
        st.link_button(
            "↗ Abrir Pasta de Fotos no Google Drive",
            url=pasta_fotos["webViewLink"],
            use_container_width=True,
        )
    else:
        st.warning("Pasta de Fotos Tratadas não encontrada no Drive deste imóvel.")

# --- PDF ---
elif selecao == "PDF":
    st.markdown("### 📄 Apresentação em PDF")
    arquivos_pdf = arquivos_da_pasta(subpastas, "PDF")
    if not arquivos_pdf:
        st.info("Nenhum PDF encontrado.")
    else:
        for arquivo in arquivos_pdf:
            st.markdown(f"**{arquivo['name']}**")
            dados_pdf = baixar_arquivo(arquivo["id"])
            if dados_pdf:
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    st.download_button(
                        "📥 Baixar PDF",
                        data=dados_pdf,
                        file_name=arquivo["name"],
                        mime="application/pdf",
                        key=f"dl_pdf_{arquivo['id']}",
                        use_container_width=True,
                    )
                with col_p2:
                    if arquivo.get("webViewLink"):
                        st.link_button(
                            "↗ Abrir Apresentação",
                            url=arquivo["webViewLink"],
                            use_container_width=True,
                        )

# --- VÍDEOS ---
elif selecao == "VIDEOS":
    st.markdown("### 🎥 Vídeos do Imóvel")
    pasta_videos = encontrar_pasta(subpastas, "VIDEOS")
    arquivos_videos = arquivos_da_pasta(subpastas, "VIDEOS")
    
    if not arquivos_videos and pasta_videos and pasta_videos.get("webViewLink"):
        st.link_button(
            "↗ Abrir Pasta de Vídeos no Google Drive",
            url=pasta_videos["webViewLink"],
            use_container_width=True,
        )
    elif not arquivos_videos:
        st.info("Nenhum vídeo encontrado.")
    else:
        for arquivo in arquivos_videos:
            st.markdown(f"**{arquivo['name']}**")
            if arquivo.get("webViewLink"):
                st.link_button(
                    "↗ Assistir / Abrir Vídeo",
                    url=arquivo["webViewLink"],
                    use_container_width=True,
                )


# =============================================================================
# RODAPÉ
# =============================================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align:center; color:#8b949e; padding:8px; font-size: 0.75rem;">
        Carvalho Ferreira · Central de Materiais
    </div>
    """,
    unsafe_allow_html=True,
)
