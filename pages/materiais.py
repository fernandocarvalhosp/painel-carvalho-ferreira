# pages/materiais.py
# -*- coding: utf-8 -*-

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

st.set_page_config(
    page_title="Materiais | Carvalho Ferreira",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CONFIGURAÇÕES
# =============================================================================

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"

# Nomes das pastas que vamos procurar dentro da pasta do imóvel
PASTAS_MATERIAIS = [
    "POSTS",
    "FOTOS SELECIONADAS",
    "FOTOS TRATADAS",
    "PDF",
    "STATUS",
    "VIDEOS",
]


# =============================================================================
# CONEXÕES
# =============================================================================

@st.cache_resource
def conectar_drive():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_DRIVE,
    )
    return build("drive", "v3", credentials=creds)


@st.cache_resource
def conectar_sheets():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=SCOPES_SHEETS,
    )
    return build("sheets", "v4", credentials=creds)


# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================

def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


def buscar_legenda(codigo):
    """Busca Legenda 1 e Legenda 2 na planilha"""
    try:
        service = conectar_sheets()
        result = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=SPREADSHEET_ID,
                range=f"'{NOME_ABA}'!A:AZ",
            )
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


def encontrar_pasta_imovel(service, codigo):
    """Procura a pasta do imóvel pelo nome (código)"""
    try:
        query = (
            f"name = '{codigo}' "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        resultados = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=10,
            )
            .execute()
        )
        pastas = resultados.get("files", [])
        if pastas:
            return pastas[0]["id"]
        return None
    except Exception as e:
        st.error(f"Erro ao procurar pasta do imóvel: {e}")
        return None


def listar_subpastas(service, pasta_pai_id):
    """Lista as subpastas de materiais dentro da pasta do imóvel"""
    try:
        query = (
            f"'{pasta_pai_id}' in parents "
            f"and mimeType = 'application/vnd.google-apps.folder' "
            f"and trashed = false"
        )
        resultados = (
            service.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=50,
            )
            .execute()
        )
        return resultados.get("files", [])
    except Exception as e:
        st.error(f"Erro ao listar subpastas: {e}")
        return []


def listar_arquivos(service, pasta_id):
    """Lista os arquivos de uma pasta"""
    try:
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
                fields="files(id, name, mimeType, webViewLink, webContentLink)",
                pageSize=100,
                orderBy="name",
            )
            .execute()
        )
        return resultados.get("files", [])
    except Exception as e:
        st.error(f"Erro ao listar arquivos: {e}")
        return []


def baixar_arquivo(service, file_id):
    """Baixa o arquivo do Drive e retorna os bytes"""
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
        st.error(f"Erro ao baixar arquivo: {e}")
        return None


# =============================================================================
# INTERFACE
# =============================================================================

st.title("📂 Materiais do Imóvel")

# Código do imóvel (vindo da página principal)
codigo = st.session_state.get("codigo_materiais") or st.session_state.get("codigo_busca", "")

if not codigo:
    st.warning("Nenhum imóvel selecionado. Volte para a página principal e busque um imóvel.")
    if st.button("← Voltar"):
        st.switch_page("app.py")
    st.stop()

st.markdown(f"### Imóvel: **{codigo}**")

# Botão voltar
if st.button("← Voltar para o painel"):
    st.switch_page("app.py")

st.markdown("---")

# -----------------------------------------------------------------------------
# LEGENDAS
# -----------------------------------------------------------------------------

st.subheader("📝 Legendas")

legenda1, legenda2 = buscar_legenda(codigo)

col_leg1, col_leg2 = st.columns(2)

with col_leg1:
    st.markdown("**Legenda 1**")
    if legenda1:
        st.text_area("Legenda 1", value=legenda1, height=150, key="txt_leg1", label_visibility="collapsed")
        st.code(legenda1, language=None)
    else:
        st.info("Legenda 1 não cadastrada.")

with col_leg2:
    st.markdown("**Legenda 2**")
    if legenda2:
        st.text_area("Legenda 2", value=legenda2, height=150, key="txt_leg2", label_visibility="collapsed")
        st.code(legenda2, language=None)
    else:
        st.info("Legenda 2 não cadastrada.")

st.markdown("---")

# -----------------------------------------------------------------------------
# ARQUIVOS DO DRIVE
# -----------------------------------------------------------------------------

st.subheader("📁 Arquivos")

service = conectar_drive()

with st.spinner("Buscando pasta do imóvel no Drive..."):
    pasta_imovel_id = encontrar_pasta_imovel(service, codigo)

if not pasta_imovel_id:
    st.error(f"Não encontrei a pasta do imóvel **{codigo}** no Google Drive.")
    st.stop()

subpastas = listar_subpastas(service, pasta_imovel_id)

# Organiza as pastas na ordem desejada
pastas_ordenadas = []
for nome_desejado in PASTAS_MATERIAIS:
    for pasta in subpastas:
        if normalizar(pasta["name"]) == normalizar(nome_desejado):
            pastas_ordenadas.append(pasta)
            break

# Mostra também pastas extras que existirem
for pasta in subpastas:
    if pasta not in pastas_ordenadas:
        pastas_ordenadas.append(pasta)

if not pastas_ordenadas:
    st.warning("Nenhuma subpasta de materiais encontrada dentro da pasta do imóvel.")
else:
    # Cria abas para cada pasta
    nomes_abas = [p["name"] for p in pastas_ordenadas]
    abas = st.tabs(nomes_abas)

    for i, pasta in enumerate(pastas_ordenadas):
        with abas[i]:
            arquivos = listar_arquivos(service, pasta["id"])

            if not arquivos:
                st.info("Nenhum arquivo nesta pasta.")
            else:
                for arquivo in arquivos:
                    col1, col2, col3 = st.columns([6, 2, 2])

                    with col1:
                        st.markdown(f"**{arquivo['name']}**")

                    with col2:
                        # Botão de download
                        bytes_arquivo = baixar_arquivo(service, arquivo["id"])
                        if bytes_arquivo:
                            st.download_button(
                                label="Baixar",
                                data=bytes_arquivo,
                                file_name=arquivo["name"],
                                key=f"dl_{arquivo['id']}",
                                use_container_width=True,
                            )

                    with col3:
                        # Link para abrir no Drive
                        if arquivo.get("webViewLink"):
                            st.link_button(
                                "Abrir no Drive",
                                url=arquivo["webViewLink"],
                                use_container_width=True,
                            )

                    st.markdown("---")