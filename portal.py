# portal.py
# -*- coding: utf-8 -*-

import io
import urllib.parse
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# =============================================================================
# CONFIGURAÇÕES DA PÁGINA (Portal Público | Carvalho Ferreira)
# =============================================================================

st.set_page_config(
    page_title="Carvalho Ferreira | Consultoria Imobiliária",
    page_icon="CF",
    layout="wide",
    initial_sidebar_state="collapsed",
)

SCOPES_DRIVE = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

SPREADSHEET_ID = "1nVEpOZFYFKcq0MXtOwxn22nqxafmJBHnf6zhHQlyT8w"
NOME_ABA = "Imoveis"


# =============================================================================
# ESTILO VISUAL: ELEGANTE, SILENCIOSO E COM IDENTIDADE DE ALTO PADRÃO
# =============================================================================

st.markdown(
    """
    <style>
    /* Oculta navegação padrão e elementos de sistema */
    [data-testid="stSidebarNav"] { display: none; }
    header { visibility: hidden; }
    
    /* Fundo geral e tipografia base */
    .stApp {
        background-color: #0b0e14;
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 4rem;
        max-width: 1100px;
    }

    /* Cabeçalho da Marca */
    .brand-container {
        text-align: center;
        padding: 20px 0 10px 0;
        border-bottom: 1px solid #21262d;
        margin-bottom: 30px;
    }
    .brand-title {
        font-size: 1.8rem;
        font-weight: 300;
        letter-spacing: 4px;
        color: #f0f6fc;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 0.8rem;
        font-weight: 600;
        letter-spacing: 3px;
        color: #8b949e;
        margin-top: 6px;
        text-transform: uppercase;
    }

    /* Navegação Minimalista por Linhas */
    .nav-container {
        text-align: center;
        margin-bottom: 35px;
        font-size: 0.95rem;
        letter-spacing: 1px;
    }
    .nav-container a {
        color: #8b949e;
        text-decoration: none;
        margin: 0 15px;
        transition: color 0.2s ease;
    }
    .nav-container a:hover {
        color: #f0f6fc;
    }

    /* Cards de Imóveis (Estilo Editorial Limpo) */
    .imovel-card {
        background-color: #11161d;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 24px;
        transition: border-color 0.2s ease;
    }
    .imovel-card:hover {
        border-color: #30363d;
    }

    .imovel-preco {
        font-size: 1.15rem;
        font-weight: 600;
        color: #f0f6fc;
        margin-top: 10px;
        margin-bottom: 4px;
    }

    .imovel-detalhes {
        font-size: 0.85rem;
        color: #8b949e;
        margin-bottom: 12px;
    }

    /* Botões personalizados */
    .stButton > button, .stLinkButton > button {
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
        background-color: #161b22;
        color: #c9d1d9;
        border: 1px solid #30363d;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton > button:hover, .stLinkButton > button:hover {
        background-color: #21262d;
        border-color: #8b949e;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# CONEXÃO GOOGLE (SECRETS)
# =============================================================================

@st.cache_resource
def conectar_google():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            creds_dict = dict(st.secrets["google_credentials"])
        
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES_DRIVE
        )
        drive = build("drive", "v3", credentials=creds)
        sheets = build("sheets", "v4", credentials=creds)
        return drive, sheets
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        st.stop()


def normalizar(texto):
    if not texto:
        return ""
    return " ".join(str(texto).strip().upper().split())


# =============================================================================
# CARREGAR DADOS DA PLANILHA (FILTRANDO APENAS PUBLICADOS)
# =============================================================================

@st.cache_data(ttl=120)
def carregar_portal_imoveis():
    try:
        _, sheets = conectar_google()
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=f"'{NOME_ABA}'!A:AZ")
            .execute()
        )
        rows = result.get("values", [])
        if not rows or len(rows) < 2:
            return []

        cabecalho = [normalizar(h) for h in rows[0]]
        imoveis = []

        for row in rows[1:]:
            if not row or not row[0]:
                continue
            while len(row) < len(cabecalho):
                row.append("")
            
            dados = {cabecalho[i]: row[i] for i in range(len(cabecalho))}
            
            # Regra de Ouro: Só exibe se PUBLICAR NO PORTAL for SIM
            publicar = normalizar(dados.get("PUBLICAR NO PORTAL", ""))
            if publicar != "SIM":
                continue

            destaque_val = normalizar(dados.get("DESTAQUE", ""))
            is_destaque = (destaque_val == "SIM")

            codigo = dados.get("CODIGO") or dados.get("CÓDIGO") or row[0]
            titulo = dados.get("TITULO 1") or dados.get("TITULO") or ""
            tipo = dados.get("TIPO") or ""
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or ""
            vagas = dados.get("VAGAS") or ""
            area = dados.get("AREA UTIL") or dados.get("ÁREA ÚTIL") or dados.get("METRAGEM") or ""
            
            imoveis.append({
                "codigo": codigo,
                "titulo": titulo,
                "tipo": tipo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
                "vagas": vagas,
                "area": area,
                "destaque": is_destaque,
            })
            
        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar o portal: {e}")
        return []


# =============================================================================
# BUSCA LEVE DA FOTO DA MINIATURA NO DRIVE
# =============================================================================

@st.cache_data(ttl=600)
def obter_miniatura_drive(codigo):
    try:
        drive, _ = conectar_google()
        query_pasta = f"name contains '{codigo}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res_pasta = drive.files().list(q=query_pasta, pageSize=5, fields="files(id, name)").execute()
        pastas = res_pasta.get("files", [])
        
        id_imovel = None
        for p in pastas:
            nome_p = p["name"].strip().upper()
            if nome_p == codigo.upper() or nome_p.startswith(codigo.upper() + " ") or nome_p.startswith(codigo.upper() + "-"):
                id_imovel = p["id"]
                break
        if not id_imovel and pastas:
            id_imovel = pastas[0]["id"]
            
        if not id_imovel:
            return None

        res_sub = drive.files().list(q=f"'{id_imovel}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false", fields="files(id, name)").execute()
        subpastas = res_sub.get("files", [])
        
        id_fotos = id_imovel
        for sub in subpastas:
            if "MINIATURA" in sub["name"].upper():
                id_fotos = sub["id"]
                break

        res_arq = drive.files().list(q=f"'{id_fotos}' in parents and mimeType contains 'image/' and trashed = false", orderBy="name", pageSize=1, fields="files(id)").execute()
        arquivos = res_arq.get("files", [])
        
        if arquivos:
            file_id = arquivos[0]["id"]
            request = drive.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            fh.seek(0)
            return fh.read()
        return None
    except Exception:
        return None


# =============================================================================
# INTERFACE DO PORTAL PÚBLICO
# =============================================================================

# Cabeçalho Oficial Carvalho Ferreira
st.markdown(
    """
    <div class="brand-container">
        <h1 class="brand-title">CARVALHO FERREIRA</h1>
        <div class="brand-subtitle">Consultoria Imobiliária</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Navegação Minimalista
st.markdown(
    """
    <div class="nav-container">
        <span>DESTAQUES</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
        <span>CASAS</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
        <span>APARTAMENTOS</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
        <span>TERRENOS</span> &nbsp;&nbsp;|&nbsp;&nbsp; 
        <span>COMERCIAIS</span>
    </div>
    """,
    unsafe_allow_html=True,
)

lista_imoveis = carregar_portal_imoveis()

if not lista_imoveis:
    st.info("Nenhum imóvel disponível no momento.")
    st.stop()

# Filtro rápido por código na barra lateral discreta
pesquisa = st.sidebar.text_input("🔍 Buscar por Código", placeholder="Ex: CF001")

imoveis_exibidos = lista_imoveis
if pesquisa:
    termo = normalizar(pesquisa)
    imoveis_exibidos = [i for i in lista_imoveis if termo in normalizar(i["codigo"])]

# Exibição em Grade Limpa
st.markdown("### Oportunidades Selecionadas")
st.markdown("---")

colunas = st.columns(3)

for indice, imovel in enumerate(imoveis_exibidos):
    col = colunas[indice % 3]
    with col:
        st.markdown('<div class="imovel-card">', unsafe_allow_html=True)
        
        foto = obter_miniatura_drive(imovel["codigo"])
        if foto:
            st.image(foto, use_container_width=True)
        else:
            st.markdown("🖼️ *Em breve*")
            
        st.markdown(f"**{imovel['tipo']}** • {imovel['bairro']}")
        st.markdown(f'<div class="imovel-preco">{imovel["valor"]}</div>', unsafe_allow_html=True)
        
        detalhes_parts = []
        if imovel["area"]:
            detalhes_parts.append(f"{imovel['area']} m²")
        if imovel["quartos"]:
            detalhes_parts.append(f"{imovel['quartos']} dorm.")
        if imovel["vagas"]:
            detalhes_parts.append(f"{imovel['vagas']} vaga(s)")
            
        st.markdown(f'<div class="imovel-detalhes">{" · ".join(detalhes_parts)}</div>', unsafe_allow_html=True)
        
        msg = f"Olá! Gostaria de mais informações sobre o imóvel {imovel['codigo']} visto no portal."
        link_zap = f"https://wa.me/5512997777777?text={urllib.parse.quote(msg)}"
        st.link_button("Falar com Consultor", link_zap, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
