# portal_B.py
# -*- coding: utf-8 -*-
"""
Carvalho Ferreira | Portal Público — VERSÃO B
Backup da estável: portal_A.py

- Colunas completas da planilha
- Página do imóvel com mais dados
- Fotos a partir da pasta da miniatura (opção B)
- CTA para contato (mais fotos / vídeo / material)
"""

import io
import urllib.parse
from pathlib import Path
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import base64
import math
import unicodedata

# =============================================================================
# CONFIGURAÇÃO
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

TELEFONE_FERNANDO = "5512988162626"
TELEFONE_VALDIR = "5512992157474"

ITENS_POR_PAGINA = 6
MAX_DESTAQUES = 6
MAX_FOTOS_DETALHE = 6  # limite para não deixar a página pesada

# =============================================================================
# ESTILO
# =============================================================================

st.markdown(
    """
    <style>
    [data-testid="stSidebarNav"] { display: none !important; }
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    .stApp {
        background-color: #0B0F14;
        color: #F7F5F0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.1rem;
        padding-bottom: 4rem;
        max-width: 1100px;
        padding-left: 1.4rem;
        padding-right: 1.4rem;
    }

    div[data-testid="stVerticalBlock"] > div { gap: 0.35rem !important; }
    .element-container { margin-bottom: 0 !important; }

    .brand-header { text-align: center; padding: 0.15rem 0 0.4rem 0; }
    .brand-title {
        font-size: 1.3rem !important;
        font-weight: 600 !important;
        letter-spacing: 4px;
        color: #F7F5F0 !important;
        margin: 0;
        text-transform: uppercase;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 0.7rem;
        font-weight: 500;
        letter-spacing: 3px;
        color: #6B7280;
        margin-top: 4px;
        text-transform: uppercase;
    }
    .brand-line {
        width: 42px;
        height: 1px;
        background: #D4AF37;
        margin: 10px auto 0 auto;
        opacity: 0.9;
    }

    div[data-testid="stHorizontalBlock"] button {
        background: transparent !important;
        border: none !important;
        color: #6B7280 !important;
        font-size: 0.76rem !important;
        font-weight: 500 !important;
        letter-spacing: 1.6px !important;
        text-transform: uppercase !important;
        padding: 4px 2px 7px 2px !important;
        border-radius: 0 !important;
        border-bottom: 1.5px solid transparent !important;
        box-shadow: none !important;
        min-height: unset !important;
    }
    div[data-testid="stHorizontalBlock"] button:hover {
        color: #F7F5F0 !important;
        border-bottom: 1.5px solid rgba(212, 175, 55, 0.5) !important;
        background: transparent !important;
    }

    .thin-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #1F2937 15%, #1F2937 85%, transparent);
        margin: 0.25rem 0 1.2rem 0;
    }

    .stTextInput > div > div > input {
        background-color: #111827 !important;
        border: 1px solid #1F2937 !important;
        border-radius: 6px !important;
        color: #F7F5F0 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 0.9rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #D4AF37 !important;
        box-shadow: 0 0 0 1px rgba(212, 175, 55, 0.25) !important;
    }

    .section-title {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #F7F5F0 !important;
        letter-spacing: 1px;
        margin: 0.2rem 0 0.9rem 0;
        text-transform: uppercase;
    }
    .section-count {
        font-size: 0.82rem;
        color: #6B7280;
        font-weight: 400;
    }

    .imovel-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 13px;
        margin-bottom: 6px;
        transition: border-color 0.2s ease;
        height: 100%;
    }
    .imovel-card:hover { border-color: #D4AF37; }

    .foto-container-relativo {
        position: relative;
        width: 100%;
        margin-bottom: 10px;
        overflow: hidden;
        border-radius: 7px;
    }
    .foto-container-relativo img {
        border-radius: 7px;
        width: 100% !important;
        object-fit: cover !important;
        height: 195px !important;
        display: block;
        transition: transform 0.3s ease;
    }
    .imovel-card:hover .foto-container-relativo img { transform: scale(1.03); }

    .status-badge {
        position: absolute;
        top: 9px;
        right: 9px;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.6px;
        z-index: 10;
        backdrop-filter: blur(4px);
    }
    .status-disponivel {
        background-color: rgba(35, 134, 54, 0.92);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .status-negociacao {
        background-color: rgba(158, 106, 3, 0.92);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.15);
    }
    .status-vendido {
        background-color: rgba(218, 54, 51, 0.92);
        color: #fff;
        border: 1px solid rgba(255,255,255,0.15);
    }

    .preco-imovel {
        font-size: 1.18rem;
        font-weight: 700;
        color: #D4AF37;
        margin-bottom: 4px;
    }
    .codigo-tag {
        font-size: 0.7rem;
        font-weight: 600;
        color: #6B7280;
        background: #0B0F14;
        padding: 2px 6px;
        border-radius: 4px;
        border: 1px solid #1F2937;
        display: inline-block;
        margin-bottom: 6px;
    }
    .info-sub {
        font-size: 0.8rem;
        color: #6B7280;
        margin-bottom: 2px;
    }
    .tipo-detalhe {
        font-size: 0.86rem;
        font-weight: 560;
        color: #F7F5F0;
        margin-top: 4px;
        margin-bottom: 10px;
    }

    .stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        background-color: #0B0F14 !important;
        color: #F7F5F0 !important;
        border: 1px solid #1F2937 !important;
        width: 100% !important;
        font-size: 0.8rem !important;
        padding: 0.45rem 0.5rem !important;
        letter-spacing: 0.4px;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #111827 !important;
        border-color: #D4AF37 !important;
        color: #fff !important;
    }

    .stLinkButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        background-color: #0B0F14 !important;
        color: #F7F5F0 !important;
        border: 1px solid #1F2937 !important;
        width: 100% !important;
        font-size: 0.8rem !important;
        padding: 0.5rem 0.5rem !important;
    }
    .stLinkButton > button:hover {
        background-color: #111827 !important;
        border-color: #D4AF37 !important;
        color: #fff !important;
    }

    .destaque-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        transition: border-color 0.2s ease;
    }
    .destaque-card:hover { border-color: #D4AF37; }
    .destaque-preco {
        font-size: 1.35rem;
        font-weight: 700;
        color: #D4AF37;
        margin: 10px 0 4px 0;
    }
    .destaque-titulo {
        font-size: 1rem;
        font-weight: 600;
        color: #F7F5F0;
        margin-bottom: 4px;
    }
    .destaque-info {
        font-size: 0.85rem;
        color: #6B7280;
        margin-bottom: 12px;
    }

    .paginacao-info {
        text-align: center;
        font-size: 0.8rem;
        color: #6B7280;
        margin: 1rem 0 0.5rem 0;
    }

    .footer-cf {
        text-align: center;
        margin-top: 2.5rem;
        padding-top: 1.2rem;
        border-top: 1px solid #1F2937;
    }
    .footer-text {
        font-size: 0.7rem;
        color: #6B7280;
        letter-spacing: 1.4px;
        text-transform: uppercase;
    }
    .footer-line {
        width: 34px;
        height: 1px;
        background: #D4AF37;
        margin: 9px auto 11px auto;
        opacity: 0.75;
    }

    /* Página do imóvel */
    .detalhe-codigo {
        font-size: 0.75rem;
        font-weight: 600;
        color: #6B7280;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .detalhe-titulo {
        font-size: 1.35rem;
        font-weight: 600;
        color: #F7F5F0;
        margin-bottom: 4px;
        line-height: 1.3;
    }
    .detalhe-subtitulo {
        font-size: 1rem;
        color: #D4AF37;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .detalhe-local {
        font-size: 0.9rem;
        color: #6B7280;
        margin-bottom: 1.2rem;
    }
    .detalhe-preco {
        font-size: 1.6rem;
        font-weight: 700;
        color: #D4AF37;
        margin: 1rem 0 0.5rem 0;
    }
    .detalhe-specs {
        font-size: 0.92rem;
        color: #F7F5F0;
        margin-bottom: 0.4rem;
        line-height: 1.5;
    }
    .detalhe-secao {
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 1.5px;
        color: #6B7280;
        text-transform: uppercase;
        margin: 1.5rem 0 0.6rem 0;
    }
    .detalhe-texto {
        font-size: 0.92rem;
        color: #D1D5DB;
        line-height: 1.55;
        margin-bottom: 0.8rem;
    }
    .detalhe-cta-texto {
        color: #9CA3AF;
        font-size: 0.9rem;
        line-height: 1.5;
        margin-bottom: 1rem;
    }
    .detalhe-foto {
        width: 100%;
        border-radius: 10px;
        object-fit: cover;
        max-height: 400px;
        margin-bottom: 10px;
    }
    .galeria-item {
        margin-bottom: 8px;
    }
    .galeria-item img {
        width: 100%;
        border-radius: 8px;
        object-fit: cover;
        height: 200px;
        display: block;
    }
    .detalhe-titulo-1 {
        font-size: 0.82rem;
        font-weight: 500;
        color: #9CA3AF;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .detalhe-titulo-2 {
        font-size: 1.45rem;
        font-weight: 700;
        color: #F7F5F0;
        margin-bottom: 4px;
        line-height: 1.25;
    }
    .detalhe-titulo-3 {
        font-size: 1rem;
        font-weight: 500;
        color: #D4AF37;
        margin-bottom: 8px;
        line-height: 1.3;
    }
    .detalhe-obs {
        font-size: 0.88rem;
        font-weight: 600;
        color: #D1D5DB;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
        line-height: 1.45;
    }

    @media (max-width: 768px) {
        .brand-title { font-size: 1.15rem !important; letter-spacing: 3px; }
        div[data-testid="stHorizontalBlock"] button {
            font-size: 0.66rem !important;
            letter-spacing: 1px !important;
        }
        .foto-container-relativo img { height: 175px !important; }
        .detalhe-foto { max-height: 280px; }
        .galeria-item img { height: 180px; }
        .detalhe-titulo-2 { font-size: 1.25rem; }
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# GOOGLE
# =============================================================================

@st.cache_resource
def conectar_google():
    creds_dict = dict(st.secrets["google_credentials"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES_DRIVE
    )
    drive = build("drive", "v3", credentials=creds)
    sheets = build("sheets", "v4", credentials=creds)
    return drive, sheets


def normalizar(texto):
    if not texto:
        return ""
    texto = str(texto).strip().upper()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(texto.split())


def eh_sim(valor):
    v = normalizar(valor)
    return v in ("SIM", "S", "YES", "Y", "1", "TRUE", "X", "VERDADEIRO")


def pegar(dados, *chaves, default=""):
    for c in chaves:
        if c in dados and str(dados[c]).strip():
            return str(dados[c]).strip()
    return default


@st.cache_data(ttl=300)
def carregar_imoveis_sheets():
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

            codigo = pegar(dados, "CODIGO", "CÓDIGO") or row[0]
            publicar = pegar(dados, "PUBLICAR NO PORTAL", "PUBLICAR", "PUBLICAR PORTAL")
            destaque = pegar(dados, "DESTAQUE", "DESTAQUES")
            ordem_raw = pegar(dados, "ORDEM DE DESTAQUE", "ORDEM DESTAQUE", "ORDEM", default="999")
            try:
                ordem = int("".join(filter(str.isdigit, str(ordem_raw))) or "999")
            except Exception:
                ordem = 999

            imoveis.append({
                "codigo": codigo,
                "publicar": eh_sim(publicar),
                "destaque": eh_sim(destaque),
                "ordem": ordem,
                "tipo": pegar(dados, "TIPO", "CATEGORIA", default="Imóvel"),
                "cidade": pegar(dados, "CIDADE"),
                "bairro": pegar(dados, "BAIRRO"),
                "endereco": pegar(dados, "ENDERECO", "ENDEREÇO"),
                "valor": pegar(dados, "VALOR", default="Sob consulta"),
                "status": pegar(dados, "STATUS", default="Disponível"),
                "miniatura_id": pegar(dados, "MINIATURA", "FOTO"),
                "dormitorios": pegar(dados, "DORMITORIOS", "DORMITÓRIOS", "QUARTOS", "DORMS"),
                "banheiros": pegar(dados, "BANHEIROS"),
                "suites": pegar(dados, "SUITES", "SUÍTES"),
                "vagas": pegar(dados, "VAGAS", "GARAGEM"),
                "area_util": pegar(dados, "AREA UTIL", "ÁREA ÚTIL"),
                "area_total": pegar(dados, "AREA TOTAL", "ÁREA TOTAL", "AREA DO TERRENO"),
                "andar": pegar(dados, "ANDAR"),
                "iptu": pegar(dados, "IPTU"),
                "condominio": pegar(dados, "CONDOMINIO", "CONDOMÍNIO"),
                "titulo_01": pegar(dados, "TITULO 01", "TÍTULO 01", "TITULO01"),
                "titulo_02": pegar(dados, "TITULO 02", "TÍTULO 02", "TITULO02"),
                "titulo_03": pegar(dados, "TITULO 03", "TÍTULO 03", "TITULO03"),
                "descricao": pegar(dados, "DESCRICAO", "DESCRIÇÃO"),
                "obs_extras": pegar(dados, "OBS EXTRAS", "OBSERVACOES EXTRAS", "OBS", "OBSERVACOES"),
                "legenda_01": pegar(dados, "LEGENDA 01", "LEGENDA01"),
                "legenda_02": pegar(dados, "LEGENDA 02", "LEGENDA02"),
            })


        return imoveis
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return []


@st.cache_data(ttl=600)
def obter_foto_miniatura_por_id(file_id):
    if not file_id or len(str(file_id).strip()) < 10:
        return None
    try:
        drive, _ = conectar_google()
        request = drive.files().get_media(fileId=file_id.strip())
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    except Exception:
        return None


def _eh_arquivo_imagem(nome, mime=""):
    mime = (mime or "").lower()
    if "image/" in mime:
        return True
    nome = (nome or "").lower()
    return any(nome.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))


@st.cache_data(ttl=300)
def listar_fotos_pasta_miniatura(file_id, limite=MAX_FOTOS_DETALHE):
    """
    Usa APENAS imagens da pasta de miniaturas.
    Aceita mime image/* e também por extensão (.jpg, .png...).
    """
    if not file_id or len(str(file_id).strip()) < 10:
        return []
    try:
        drive, _ = conectar_google()
        meta = drive.files().get(
            fileId=file_id.strip(),
            fields="id, name, parents, mimeType",
            supportsAllDrives=True,
        ).execute()

        mime = meta.get("mimeType", "")
        folder_id = None

        if "folder" in mime:
            nome_pasta = normalizar(meta.get("name", ""))
            if "MINIATURA" in nome_pasta:
                folder_id = file_id.strip()
        else:
            parents = meta.get("parents") or []
            if parents:
                parent = drive.files().get(
                    fileId=parents[0],
                    fields="id, name",
                    supportsAllDrives=True,
                ).execute()
                nome_pasta = normalizar(parent.get("name", ""))
                if "MINIATURA" in nome_pasta:
                    folder_id = parents[0]

        if not folder_id:
            data = obter_foto_miniatura_por_id(file_id)
            return [data] if data else []

        result = drive.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType)",
            orderBy="name",
            pageSize=50,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = [
            f for f in result.get("files", [])
            if _eh_arquivo_imagem(f.get("name"), f.get("mimeType"))
        ][:limite]

        fotos = []
        for f in files:
            data = obter_foto_miniatura_por_id(f["id"])
            if data:
                fotos.append(data)

        if fotos:
            return fotos

        data = obter_foto_miniatura_por_id(file_id)
        return [data] if data else []
    except Exception:
        data = obter_foto_miniatura_por_id(file_id)
        return [data] if data else []


# =============================================================================
# ESTADO
# =============================================================================

if "cat" not in st.session_state:
    st.session_state["cat"] = "DESTAQUES"
if "pagina" not in st.session_state:
    st.session_state["pagina"] = 1
if "idx_destaque" not in st.session_state:
    st.session_state["idx_destaque"] = 0
if "imovel_selecionado" not in st.session_state:
    st.session_state["imovel_selecionado"] = None
if "idx_foto" not in st.session_state:
    st.session_state["idx_foto"] = 0

# =============================================================================
# LOGO
# =============================================================================

def encontrar_logo():
    candidatos = [
        Path("marca/logo/logo.png"),
        Path("marca/Logo/logo.png"),
        Path("marca/logo.png"),
        Path("marca/Logo.png"),
    ]
    for pasta in [Path("marca/logo"), Path("marca/Logo")]:
        if pasta.exists() and pasta.is_dir():
            for arq in list(pasta.glob("*.png")) + list(pasta.glob("*.PNG")):
                candidatos.append(arq)
    for caminho in candidatos:
        if caminho.exists() and caminho.is_file():
            return caminho
    return None


logo_encontrado = encontrar_logo()

if logo_encontrado:
    col_l, col_c, col_r = st.columns([1.5, 1, 1.5])
    with col_c:
        st.image(str(logo_encontrado), width=30)
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-title">Carvalho Ferreira</div>
            <div class="brand-subtitle">Consultoria Imobiliária</div>
            <div class="brand-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="brand-header">
            <div class="brand-title">Carvalho Ferreira</div>
            <div class="brand-subtitle">Consultoria Imobiliária</div>
            <div class="brand-line"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =============================================================================
# MENU
# =============================================================================

categorias = ["DESTAQUES", "CASAS", "APARTAMENTOS", "TERRENOS", "COMERCIAIS"]
cols_nav = st.columns(len(categorias))

for i, cat_nome in enumerate(categorias):
    with cols_nav[i]:
        if st.button(cat_nome, key=f"nav_{cat_nome}", use_container_width=True):
            st.session_state["cat"] = cat_nome
            st.session_state["pagina"] = 1
            st.session_state["idx_destaque"] = 0
            st.session_state["busca_portal"] = ""
            st.session_state["imovel_selecionado"] = None
            st.session_state["idx_foto"] = 0
            st.rerun()

st.markdown('<hr class="thin-divider">', unsafe_allow_html=True)

# =============================================================================
# BUSCA
# =============================================================================

if "busca_portal" not in st.session_state:
    st.session_state["busca_portal"] = ""

busca = st.text_input(
    "Buscar",
    placeholder="Procure por bairro, código ou tipo...",
    label_visibility="collapsed",
    key="busca_portal",
)

# =============================================================================
# DADOS
# =============================================================================

lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado no momento.")
    st.stop()

imoveis_publicos = [i for i in lista_imoveis if i["publicar"]]

# =============================================================================
# PÁGINA DO IMÓVEL
# =============================================================================

codigo_sel = st.session_state.get("imovel_selecionado")

if codigo_sel:
    imovel = next(
        (i for i in imoveis_publicos if normalizar(i["codigo"]) == normalizar(str(codigo_sel))),
        None,
    )

    if not imovel:
        st.warning("Imóvel não encontrado ou não disponível no portal.")
        if st.button("← Voltar"):
            st.session_state["imovel_selecionado"] = None
            st.rerun()
        st.stop()

    if st.button("← Voltar", key="btn_voltar_detalhe"):
        st.session_state["imovel_selecionado"] = None
        st.rerun()

    st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    # Código
    st.markdown(
        f'<div class="detalhe-codigo">Cód. {imovel["codigo"]}</div>',
        unsafe_allow_html=True,
    )

    # Hierarquia de títulos (como no PDF)
    # Título 1 = linha menor | Título 2 = manchete principal | Título 3 = subtítulo
    if imovel["titulo_01"]:
        st.markdown(
            f'<div class="detalhe-titulo-1">{imovel["titulo_01"]}</div>',
            unsafe_allow_html=True,
        )
    titulo_principal = imovel["titulo_02"] or imovel["tipo"]
    st.markdown(
        f'<div class="detalhe-titulo-2">{titulo_principal}</div>',
        unsafe_allow_html=True,
    )
    if imovel["titulo_03"]:
        st.markdown(
            f'<div class="detalhe-titulo-3">{imovel["titulo_03"]}</div>',
            unsafe_allow_html=True,
        )

    # Local
    local_parts = [p for p in [imovel["bairro"], imovel["cidade"]] if p]
    if imovel["endereco"]:
        local_parts.insert(0, imovel["endereco"])
    if local_parts:
        st.markdown(
            f'<div class="detalhe-local">{" · ".join(local_parts)}</div>',
            unsafe_allow_html=True,
        )

    # Fotos — carrossel (somente pasta MINIATURA)
    with st.spinner("Carregando fotos..."):
        fotos = listar_fotos_pasta_miniatura(imovel["miniatura_id"], limite=MAX_FOTOS_DETALHE)

    if fotos:
        idx_f = st.session_state.get("idx_foto", 0)
        if idx_f >= len(fotos):
            idx_f = 0
            st.session_state["idx_foto"] = 0

        encoded = base64.b64encode(fotos[idx_f]).decode("utf-8")
        st.markdown(
            f'<img class="detalhe-foto" src="data:image/jpeg;base64,{encoded}" />',
            unsafe_allow_html=True,
        )

        if len(fotos) > 1:
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("←", use_container_width=True, key="foto_prev"):
                    st.session_state["idx_foto"] = (idx_f - 1) % len(fotos)
                    st.rerun()
            with c2:
                st.markdown(
                    f'<div style="text-align:center;color:#6B7280;font-size:0.85rem;padding-top:0.45rem;">'
                    f"{idx_f + 1} / {len(fotos)}</div>",
                    unsafe_allow_html=True,
                )
            with c3:
                if st.button("→", use_container_width=True, key="foto_next"):
                    st.session_state["idx_foto"] = (idx_f + 1) % len(fotos)
                    st.rerun()

            indicadores = "  ".join(
                ["●" if i == idx_f else "○" for i in range(len(fotos))]
            )
            st.markdown(
                f'<div style="text-align:center;color:#6B7280;font-size:0.85rem;margin-top:0.2rem;margin-bottom:0.6rem;">{indicadores}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="background:#111827;height:280px;display:flex;align-items:center;justify-content:center;color:#6B7280;border-radius:10px;border:1px solid #1F2937;">Foto em breve</div>',
            unsafe_allow_html=True,
        )

    # Preço
    st.markdown(
        f'<div class="detalhe-preco">{imovel["valor"]}</div>',
        unsafe_allow_html=True,
    )

    # Características
    specs = []
    if imovel["area_util"]:
        specs.append(f"{imovel['area_util']} úteis")
    if imovel["area_total"]:
        specs.append(f"{imovel['area_total']} totais")
    if imovel["dormitorios"]:
        specs.append(f"{imovel['dormitorios']} dormitórios")
    if imovel["suites"]:
        specs.append(f"{imovel['suites']} suíte(s)")
    if imovel["banheiros"]:
        specs.append(f"{imovel['banheiros']} banheiros")
    if imovel["vagas"]:
        specs.append(f"{imovel['vagas']} vaga(s)")
    if imovel["andar"]:
        specs.append(f"Andar {imovel['andar']}")

    if specs:
        st.markdown(
            f'<div class="detalhe-specs">{" · ".join(specs)}</div>',
            unsafe_allow_html=True,
        )

    custos = []
    if imovel["iptu"]:
        custos.append(f"IPTU {imovel['iptu']}")
    if imovel["condominio"]:
        custos.append(f"Cond. {imovel['condominio']}")
    if custos:
        st.markdown(
            f'<div class="detalhe-specs" style="color:#9CA3AF;font-size:0.88rem;">{" · ".join(custos)}</div>',
            unsafe_allow_html=True,
        )

    # Textos do anúncio (ordem do PDF: OBS EXTRAS → DESCRIÇÃO)
    if imovel.get("obs_extras") or imovel["descricao"] or imovel["legenda_01"] or imovel["legenda_02"]:
        st.markdown('<div class="detalhe-secao">Sobre o imóvel</div>', unsafe_allow_html=True)

    if imovel.get("obs_extras"):
        st.markdown(
            f'<div class="detalhe-obs">{imovel["obs_extras"]}</div>',
            unsafe_allow_html=True,
        )

    if imovel["descricao"]:
        st.markdown(
            f'<div class="detalhe-texto">{imovel["descricao"]}</div>',
            unsafe_allow_html=True,
        )

    if imovel["legenda_01"]:
        st.markdown(
            f'<div class="detalhe-texto">{imovel["legenda_01"]}</div>',
            unsafe_allow_html=True,
        )
    if imovel["legenda_02"]:
        st.markdown(
            f'<div class="detalhe-texto">{imovel["legenda_02"]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="thin-divider">', unsafe_allow_html=True)

    # CTA — funil de contato
    st.markdown('<div class="detalhe-secao">Gostou deste imóvel?</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="detalhe-cta-texto">
            Quer mais fotos, vídeo ou o material completo?<br>
            Fale com um de nossos consultores. Vamos entender o que você busca
            e enviar o que faz sentido para você.
        </div>
        """,
        unsafe_allow_html=True,
    )

    msg_whats = (
        f"Olá, tenho interesse no imóvel {imovel['codigo']} "
        f"({imovel['tipo']} em {imovel['bairro']}). "
        f"Gostaria de mais informações, fotos e material completo."
    )
    link_wf = f"https://wa.me/{TELEFONE_FERNANDO}?text={urllib.parse.quote(msg_whats)}"
    link_wv = f"https://wa.me/{TELEFONE_VALDIR}?text={urllib.parse.quote(msg_whats)}"

    c1, c2 = st.columns(2)
    with c1:
        st.link_button("Fernando Carvalho", link_wf, use_container_width=True)
    with c2:
        st.link_button("Valdir Ferreira", link_wv, use_container_width=True)

    st.markdown(
        """
        <div class="footer-cf">
            <div class="footer-line"></div>
            <div class="footer-text">Carvalho Ferreira · Consultoria Imobiliária</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# =============================================================================
# FILTRAGEM (listagem)
# =============================================================================

cat_ativa = st.session_state["cat"]
imoveis_exibidos = []

if busca and busca.strip():
    termo = normalizar(busca)
    imoveis_exibidos = [
        i for i in imoveis_publicos
        if termo in normalizar(
            f"{i['codigo']} {i['tipo']} {i['bairro']} {i['cidade']} {i['titulo_01']}"
        )
    ]
    titulo_secao = "Resultado da busca"
    st.session_state["pagina"] = 1
else:
    if cat_ativa == "DESTAQUES":
        imoveis_exibidos = sorted(
            [i for i in imoveis_publicos if i["destaque"]],
            key=lambda x: x["ordem"],
        )[:MAX_DESTAQUES]
        titulo_secao = "Destaques"
    elif cat_ativa == "CASAS":
        imoveis_exibidos = [i for i in imoveis_publicos if "CASA" in normalizar(i["tipo"])]
        titulo_secao = "Casas"
    elif cat_ativa == "APARTAMENTOS":
        imoveis_exibidos = [
            i for i in imoveis_publicos
            if "APARTAMENTO" in normalizar(i["tipo"]) or "APTO" in normalizar(i["tipo"])
        ]
        titulo_secao = "Apartamentos"
    elif cat_ativa == "TERRENOS":
        imoveis_exibidos = [
            i for i in imoveis_publicos
            if "TERRENO" in normalizar(i["tipo"]) or "LOTE" in normalizar(i["tipo"])
        ]
        titulo_secao = "Terrenos e Lotes"
    elif cat_ativa == "COMERCIAIS":
        imoveis_exibidos = [
            i for i in imoveis_publicos
            if any(x in normalizar(i["tipo"]) for x in ["COMERCIAL", "SALA", "GALPAO", "GALPÃO"])
        ]
        titulo_secao = "Comerciais"

total = len(imoveis_exibidos)

st.markdown(
    f"""
    <div class="section-title">
        {titulo_secao}
        <span class="section-count"> · {total} imóveis</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# RENDER LISTAGEM
# =============================================================================

def render_card(imovel, key_suffix=""):
    st.markdown('<div class="imovel-card">', unsafe_allow_html=True)

    st_normal = normalizar(imovel["status"])
    if "NEGOCIACAO" in st_normal or "NEGOCIAÇÃO" in st_normal:
        badge_classe, badge_texto = "status-negociacao", "EM NEGOCIAÇÃO"
    elif any(x in st_normal for x in ["VENDIDO", "LOCADO", "INDISPONIVEL", "INDISPONÍVEL"]):
        badge_classe, badge_texto = "status-vendido", imovel["status"].upper()
    else:
        badge_classe, badge_texto = "status-disponivel", "DISPONÍVEL"

    foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])
    if foto_bytes:
        encoded = base64.b64encode(foto_bytes).decode("utf-8")
        st.markdown(
            f"""
            <div class="foto-container-relativo">
                <span class="status-badge {badge_classe}">{badge_texto}</span>
                <img src="data:image/jpeg;base64,{encoded}" />
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="foto-container-relativo" style="background:#0B0F14;height:195px;display:flex;align-items:center;justify-content:center;color:#6B7280;border-radius:7px;">
                <span class="status-badge {badge_classe}">{badge_texto}</span>
                <span style="font-size:0.8rem;">Foto em breve</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(f'<div class="preco-imovel">{imovel["valor"]}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="codigo-tag">Cód: {imovel["codigo"]}</div>', unsafe_allow_html=True)

    local = imovel["bairro"]
    if imovel["cidade"]:
        local += f" · {imovel['cidade']}"
    st.markdown(f'<div class="info-sub">{local}</div>', unsafe_allow_html=True)

    partes = [imovel["tipo"]]
    if imovel["dormitorios"]:
        partes.append(f"{imovel['dormitorios']} Dorm.")
    if imovel["vagas"]:
        partes.append(f"{imovel['vagas']} Vaga(s)")
    if imovel["area_util"]:
        partes.append(f"{imovel['area_util']} úteis")
    st.markdown(f'<div class="tipo-detalhe">{" · ".join(partes)}</div>', unsafe_allow_html=True)

    if st.button("Ver imóvel", key=f"ver_{imovel['codigo']}_{key_suffix}", use_container_width=True):
        st.session_state["imovel_selecionado"] = imovel["codigo"]
        st.session_state["idx_foto"] = 0
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)



if not imoveis_exibidos:
    st.info("Nenhum imóvel encontrado nesta categoria ou busca.")
else:
    if cat_ativa == "DESTAQUES" and not (busca and busca.strip()):
        idx = st.session_state["idx_destaque"]
        if idx >= len(imoveis_exibidos):
            idx = 0
            st.session_state["idx_destaque"] = 0

        imovel = imoveis_exibidos[idx]

        col_esq, col_centro, col_dir = st.columns([0.8, 2.4, 0.8])
        with col_centro:
            st.markdown('<div class="destaque-card">', unsafe_allow_html=True)

            foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])
            if foto_bytes:
                encoded = base64.b64encode(foto_bytes).decode("utf-8")
                st.markdown(
                    f'<img src="data:image/jpeg;base64,{encoded}" style="width:100%;border-radius:8px;height:280px;object-fit:cover;" />',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="background:#0B0F14;height:280px;display:flex;align-items:center;justify-content:center;color:#6B7280;border-radius:8px;">Foto em breve</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(f'<div class="destaque-preco">{imovel["valor"]}</div>', unsafe_allow_html=True)
            titulo_card = imovel["titulo_01"] or f"{imovel['tipo']} · {imovel['bairro']}"
            st.markdown(f'<div class="destaque-titulo">{titulo_card}</div>', unsafe_allow_html=True)

            partes = []
            if imovel["area_util"]:
                partes.append(f"{imovel['area_util']} úteis")
            if imovel["dormitorios"]:
                partes.append(f"{imovel['dormitorios']} dorm.")
            if imovel["vagas"]:
                partes.append(f"{imovel['vagas']} vaga(s)")
            st.markdown(
                f'<div class="destaque-info">{" · ".join(partes) if partes else imovel["codigo"]}</div>',
                unsafe_allow_html=True,
            )

            if st.button("Ver imóvel", key=f"destaque_ver_{imovel['codigo']}", use_container_width=True):
                st.session_state["imovel_selecionado"] = imovel["codigo"]
                st.session_state["idx_foto"] = 0
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("← Anterior", use_container_width=True, key="car_prev"):
                st.session_state["idx_destaque"] = (idx - 1) % len(imoveis_exibidos)
                st.rerun()
        with c3:
            if st.button("Próximo →", use_container_width=True, key="car_next"):
                st.session_state["idx_destaque"] = (idx + 1) % len(imoveis_exibidos)
                st.rerun()

        indicadores = "  ".join(
            ["●" if i == idx else "○" for i in range(len(imoveis_exibidos))]
        )
        st.markdown(
            f'<div style="text-align:center;color:#6B7280;font-size:0.85rem;margin-top:0.4rem;">{indicadores}</div>',
            unsafe_allow_html=True,
        )

    else:
        total_paginas = max(1, math.ceil(total / ITENS_POR_PAGINA))
        pagina_atual = st.session_state["pagina"]
        if pagina_atual > total_paginas:
            pagina_atual = 1
            st.session_state["pagina"] = 1

        inicio = (pagina_atual - 1) * ITENS_POR_PAGINA
        pagina_imoveis = imoveis_exibidos[inicio : inicio + ITENS_POR_PAGINA]

        for i in range(0, len(pagina_imoveis), 3):
            grupo = pagina_imoveis[i : i + 3]
            cols = st.columns(3, gap="medium")
            for pos, imovel in enumerate(grupo):
                with cols[pos]:
                    render_card(imovel, key_suffix=f"{pagina_atual}_{i}_{pos}")

        if total_paginas > 1:
            st.markdown(
                f'<div class="paginacao-info">Página {pagina_atual} de {total_paginas}</div>',
                unsafe_allow_html=True,
            )
            c_prev, _, c_next = st.columns([1, 2, 1])
            with c_prev:
                if pagina_atual > 1:
                    if st.button("← Anterior", use_container_width=True, key="pg_prev"):
                        st.session_state["pagina"] = pagina_atual - 1
                        st.rerun()
            with c_next:
                if pagina_atual < total_paginas:
                    if st.button("Próxima →", use_container_width=True, key="pg_next"):
                        st.session_state["pagina"] = pagina_atual + 1
                        st.rerun()

st.markdown(
    """
    <div class="footer-cf">
        <div class="footer-line"></div>
        <div class="footer-text">Carvalho Ferreira · Consultoria Imobiliária</div>
    </div>
    """,
    unsafe_allow_html=True,
)
