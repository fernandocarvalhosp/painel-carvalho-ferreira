# portal.py
# -*- coding: utf-8 -*-
"""
Carvalho Ferreira | Portal Público
Versão focada em experiência premium e conversão de leads.
"""

import io
import urllib.parse
from pathlib import Path
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import base64

# =============================================================================
# CONFIGURAÇÃO DA PÁGINA
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

# =============================================================================
# ESTILO VISUAL – IDENTIDADE CARVALHO FERREIRA
# =============================================================================

st.markdown(
    """
    <style>
    /* ===== RESET E BASE ===== */
    [data-testid="stSidebarNav"] { display: none !important; }
    header { visibility: hidden !important; }
    #MainMenu { visibility: hidden !important; }
    footer { visibility: hidden !important; }

    .stApp {
        background-color: #0e1117;
        color: #f0f2f6;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 5rem;
        max-width: 1180px;
        padding-left: 1.5rem;
        padding-right: 1.5rem;
    }

    /* ===== CABEÇALHO DE MARCA ===== */
    .brand-header {
        text-align: center;
        padding: 0.5rem 0 0.8rem 0;
    }

    .brand-title {
        font-size: 1.85rem !important;
        font-weight: 600 !important;
        letter-spacing: 5px;
        color: #f7f5ef !important;
        margin: 0;
        text-transform: uppercase;
        line-height: 1.2;
    }

    .brand-subtitle {
        font-size: 0.72rem;
        font-weight: 500;
        letter-spacing: 3.5px;
        color: #8b949e;
        margin-top: 6px;
        text-transform: uppercase;
    }

    .brand-line {
        width: 48px;
        height: 1px;
        background: #d4af37;
        margin: 14px auto 0 auto;
        opacity: 0.85;
    }

    /* ===== MENU DE NAVEGAÇÃO FINO ===== */
    .nav-container {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 2.8rem;
        padding: 0.6rem 0 0.9rem 0;
        flex-wrap: wrap;
    }

    .nav-item {
        font-size: 0.78rem;
        font-weight: 500;
        letter-spacing: 1.8px;
        color: #8b949e;
        text-transform: uppercase;
        text-decoration: none !important;
        padding-bottom: 6px;
        border-bottom: 1.5px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
        background: none;
        border-top: none;
        border-left: none;
        border-right: none;
    }

    .nav-item:hover {
        color: #f7f5ef;
        border-bottom-color: rgba(212, 175, 55, 0.45);
    }

    .nav-item.active {
        color: #f7f5ef;
        border-bottom-color: #d4af37;
        font-weight: 600;
    }

    /* Esconde botões nativos do Streamlit usados como navegação */
    div[data-testid="stHorizontalBlock"] button {
        background: transparent !important;
        border: none !important;
        color: #8b949e !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
        letter-spacing: 1.8px !important;
        text-transform: uppercase !important;
        padding: 4px 2px 8px 2px !important;
        border-radius: 0 !important;
        border-bottom: 1.5px solid transparent !important;
        box-shadow: none !important;
        min-height: unset !important;
    }

    div[data-testid="stHorizontalBlock"] button:hover {
        color: #f7f5ef !important;
        border-bottom: 1.5px solid rgba(212, 175, 55, 0.45) !important;
        background: transparent !important;
    }

    /* ===== DIVISÓRIA FINA ===== */
    .thin-divider {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #30363d 20%, #30363d 80%, transparent);
        margin: 0.4rem 0 1.6rem 0;
    }

    /* ===== BUSCA ===== */
    .stTextInput > div > div > input {
        background-color: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        color: #f7f5ef !important;
        font-size: 0.9rem !important;
        padding: 0.6rem 0.9rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #d4af37 !important;
        box-shadow: 0 0 0 1px rgba(212, 175, 55, 0.25) !important;
    }

    .stTextInput label {
        color: #8b949e !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.5px;
    }

    /* ===== TÍTULOS DE SEÇÃO ===== */
    .section-title {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        color: #f7f5ef !important;
        letter-spacing: 1px;
        margin: 0.5rem 0 1.2rem 0;
        text-transform: uppercase;
    }

    .section-count {
        font-size: 0.85rem;
        color: #8b949e;
        font-weight: 400;
        letter-spacing: 0.5px;
    }

    /* ===== CARDS DE IMÓVEIS ===== */
    .imovel-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 18px;
        transition: border-color 0.22s ease, transform 0.22s ease;
        height: 100%;
    }

    .imovel-card:hover {
        border-color: #d4af37;
    }

    .foto-container-relativo {
        position: relative;
        width: 100%;
        margin-bottom: 12px;
        overflow: hidden;
        border-radius: 7px;
    }

    .foto-container-relativo img {
        border-radius: 7px;
        width: 100% !important;
        object-fit: cover !important;
        height: 210px !important;
        display: block;
        transition: transform 0.35s ease;
    }

    .imovel-card:hover .foto-container-relativo img {
        transform: scale(1.03);
    }

    .status-badge {
        position: absolute;
        top: 10px;
        right: 10px;
        padding: 4px 9px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.7px;
        z-index: 10;
        backdrop-filter: blur(4px);
    }

    .status-disponivel {
        background-color: rgba(35, 134, 54, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .status-negociacao {
        background-color: rgba(158, 106, 3, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .status-vendido {
        background-color: rgba(218, 54, 51, 0.92);
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .preco-imovel {
        font-size: 1.25rem;
        font-weight: 700;
        color: #d4af37;
        margin-bottom: 6px;
        letter-spacing: 0.3px;
    }

    .codigo-tag {
        font-size: 0.72rem;
        font-weight: 600;
        color: #8b949e;
        background: #1a1f2c;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid #30363d;
        display: inline-block;
        margin-bottom: 8px;
        letter-spacing: 0.4px;
    }

    .info-sub {
        font-size: 0.82rem;
        color: #8b949e;
        margin-bottom: 3px;
        line-height: 1.35;
    }

    .tipo-detalhe {
        font-size: 0.88rem;
        font-weight: 560;
        color: #f7f5ef;
        margin-top: 6px;
        margin-bottom: 12px;
        line-height: 1.4;
    }

    /* ===== BOTÕES WHATSAPP ===== */
    .stLinkButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        background-color: #1f2937 !important;
        color: #f7f5ef !important;
        border: 1px solid #374151 !important;
        width: 100% !important;
        font-size: 0.78rem !important;
        padding: 0.45rem 0.4rem !important;
        letter-spacing: 0.3px;
        transition: all 0.2s ease !important;
    }

    .stLinkButton > button:hover {
        background-color: #374151 !important;
        border-color: #d4af37 !important;
        color: #ffffff !important;
    }

    /* ===== RODAPÉ ===== */
    .footer-cf {
        text-align: center;
        margin-top: 3.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #21262d;
    }

    .footer-text {
        font-size: 0.72rem;
        color: #6e7681;
        letter-spacing: 1.5px;
        text-transform: uppercase;
    }

    .footer-line {
        width: 36px;
        height: 1px;
        background: #d4af37;
        margin: 10px auto 12px auto;
        opacity: 0.7;
    }

    /* ===== RESPONSIVO ===== */
    @media (max-width: 768px) {
        .brand-title {
            font-size: 1.45rem !important;
            letter-spacing: 3px;
        }
        .nav-container {
            gap: 1.4rem;
        }
        div[data-testid="stHorizontalBlock"] button {
            font-size: 0.68rem !important;
            letter-spacing: 1.2px !important;
        }
        .imovel-card {
            padding: 12px;
        }
        .foto-container-relativo img {
            height: 190px !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# CONEXÕES GOOGLE
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
    return " ".join(str(texto).strip().upper().split())


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

            codigo = dados.get("CODIGO") or dados.get("CÓDIGO") or row[0]
            tipo = dados.get("TIPO") or dados.get("CATEGORIA") or "Imóvel"
            bairro = dados.get("BAIRRO") or ""
            cidade = dados.get("CIDADE") or ""
            valor = dados.get("VALOR") or "Sob consulta"
            quartos = dados.get("QUARTOS") or dados.get("DORMS") or dados.get("DORMITORIOS") or ""
            vagas = dados.get("VAGAS") or dados.get("GARAGEM") or ""
            area_util = dados.get("AREA UTIL") or dados.get("ÁREA ÚTIL") or ""
            status = dados.get("STATUS") or "Disponível"
            miniatura_id = dados.get("MINIATURA") or dados.get("FOTO") or ""

            imoveis.append({
                "codigo": codigo,
                "tipo": tipo,
                "bairro": bairro,
                "cidade": cidade,
                "valor": valor,
                "quartos": quartos,
                "vagas": vagas,
                "area_util": area_util,
                "status": status,
                "miniatura_id": miniatura_id.strip(),
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


# =============================================================================
# ESTADO DA NAVEGAÇÃO
# =============================================================================

if "cat" not in st.session_state:
    st.session_state["cat"] = "DESTAQUES"

# =============================================================================
# CABEÇALHO DE MARCA
# =============================================================================

col_l, col_c, col_r = st.columns([1, 2.2, 1])
with col_c:
    logo_path = Path("marca/logo.png")
    if logo_path.exists():
        st.image(str(logo_path), use_container_width=True)
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
# MENU DE NAVEGAÇÃO FINO (texto + underline)
# =============================================================================

categorias = ["DESTAQUES", "CASAS", "APARTAMENTOS", "TERRENOS", "COMERCIAIS"]
cols_nav = st.columns(len(categorias))

for i, cat_nome in enumerate(categorias):
    with cols_nav[i]:
        # O CSS acima transforma esses botões em links finos com underline
        if st.button(cat_nome, key=f"nav_{cat_nome}", use_container_width=True):
            st.session_state["cat"] = cat_nome
            st.rerun()

# Linha divisória fina
st.markdown('<hr class="thin-divider">', unsafe_allow_html=True)

# =============================================================================
# BUSCA RÁPIDA
# =============================================================================

busca_codigo = st.text_input(
    "Busca rápida por código",
    placeholder="Ex: CF024",
    label_visibility="collapsed",
)

st.markdown("<div style='height: 0.6rem'></div>", unsafe_allow_html=True)

# =============================================================================
# CARREGAMENTO E FILTRAGEM
# =============================================================================

lista_imoveis = carregar_imoveis_sheets()

if not lista_imoveis:
    st.warning("Nenhum imóvel encontrado no momento.")
    st.stop()

imoveis_exibidos = []
cat_ativa = st.session_state["cat"]

if busca_codigo and busca_codigo.strip():
    termo = normalizar(busca_codigo)
    imoveis_exibidos = [i for i in lista_imoveis if termo in normalizar(i["codigo"])]
    titulo_secao = f"Resultado da busca"
else:
    if cat_ativa == "DESTAQUES":
        # Mostra apenas disponíveis (pode ser ajustado para um campo "Destaque" na planilha)
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "DISPONÍVEL" in normalizar(i["status"]) or "DISPONIVEL" in normalizar(i["status"])
        ][:12]  # limita para não sobrecarregar a home
        titulo_secao = "Destaques"
    elif cat_ativa == "CASAS":
        imoveis_exibidos = [i for i in lista_imoveis if "CASA" in normalizar(i["tipo"])]
        titulo_secao = "Casas"
    elif cat_ativa == "APARTAMENTOS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "APARTAMENTO" in normalizar(i["tipo"]) or "APTO" in normalizar(i["tipo"])
        ]
        titulo_secao = "Apartamentos"
    elif cat_ativa == "TERRENOS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "TERRENO" in normalizar(i["tipo"]) or "LOTE" in normalizar(i["tipo"])
        ]
        titulo_secao = "Terrenos e Lotes"
    elif cat_ativa == "COMERCIAIS":
        imoveis_exibidos = [
            i for i in lista_imoveis
            if "COMERCIAL" in normalizar(i["tipo"])
            or "SALA" in normalizar(i["tipo"])
            or "GALPÃO" in normalizar(i["tipo"])
            or "GALPAO" in normalizar(i["tipo"])
        ]
        titulo_secao = "Comerciais"

# Título da seção
st.markdown(
    f"""
    <div class="section-title">
        {titulo_secao}
        <span class="section-count"> · {len(imoveis_exibidos)} imóveis</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# GRID DE CARDS
# =============================================================================

if not imoveis_exibidos:
    st.info("Nenhum imóvel encontrado nesta categoria ou busca.")
else:
    for inicio in range(0, len(imoveis_exibidos), 3):
        grupo = imoveis_exibidos[inicio : inicio + 3]
        colunas = st.columns(3)

        for posicao, imovel in enumerate(grupo):
            with colunas[posicao]:
                st.markdown('<div class="imovel-card">', unsafe_allow_html=True)

                # Status badge
                st_normal = normalizar(imovel["status"])
                if "NEGOCIAÇÃO" in st_normal or "NEGOCIACAO" in st_normal:
                    badge_classe = "status-negociacao"
                    badge_texto = "EM NEGOCIAÇÃO"
                elif any(x in st_normal for x in ["VENDIDO", "LOCADO", "INDISPONÍVEL", "INDISPONIVEL"]):
                    badge_classe = "status-vendido"
                    badge_texto = imovel["status"].upper()
                else:
                    badge_classe = "status-disponivel"
                    badge_texto = "DISPONÍVEL"

                # Foto
                foto_bytes = obter_foto_miniatura_por_id(imovel["miniatura_id"])

                if foto_bytes:
                    encoded_img = base64.b64encode(foto_bytes).decode("utf-8")
                    st.markdown(
                        f"""
                        <div class="foto-container-relativo">
                            <span class="status-badge {badge_classe}">{badge_texto}</span>
                            <img src="data:image/jpeg;base64,{encoded_img}" />
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="foto-container-relativo" style="background:#21262d;height:210px;display:flex;align-items:center;justify-content:center;color:#8b949e;border-radius:7px;">
                            <span class="status-badge {badge_classe}">{badge_texto}</span>
                            <span style="font-size:0.8rem;">Foto em breve</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # Preço
                st.markdown(
                    f'<div class="preco-imovel">{imovel["valor"]}</div>',
                    unsafe_allow_html=True,
                )

                # Código
                st.markdown(
                    f'<div class="codigo-tag">Cód: {imovel["codigo"]}</div>',
                    unsafe_allow_html=True,
                )

                # Localização
                local = f"{imovel['bairro']}"
                if imovel["cidade"]:
                    local += f" · {imovel['cidade']}"
                st.markdown(
                    f'<div class="info-sub">{local}</div>',
                    unsafe_allow_html=True,
                )

                # Tipo + detalhes
                partes = [imovel["tipo"]]
                if imovel["quartos"]:
                    partes.append(f"{imovel['quartos']} Dorm.")
                if imovel["vagas"]:
                    partes.append(f"{imovel['vagas']} Vaga(s)")
                if imovel["area_util"]:
                    partes.append(f"{imovel['area_util']} úteis")

                st.markdown(
                    f'<div class="tipo-detalhe">{" · ".join(partes)}</div>',
                    unsafe_allow_html=True,
                )

                # WhatsApp – conversão
                msg_whats = (
                    f"Olá, tenho interesse no imóvel {imovel['codigo']} "
                    f"({imovel['tipo']} em {imovel['bairro']}). "
                    f"Gostaria de mais informações."
                )
                link_wf = f"https://wa.me/{TELEFONE_FERNANDO}?text={urllib.parse.quote(msg_whats)}"
                link_wv = f"https://wa.me/{TELEFONE_VALDIR}?text={urllib.parse.quote(msg_whats)}"

                col_w1, col_w2 = st.columns(2)
                with col_w1:
                    st.link_button("Fernando", link_wf, use_container_width=True)
                with col_w2:
                    st.link_button("Valdir", link_wv, use_container_width=True)

                st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# RODAPÉ
# =============================================================================

st.markdown(
    """
    <div class="footer-cf">
        <div class="footer-line"></div>
        <div class="footer-text">Carvalho Ferreira · Consultoria Imobiliária</div>
    </div>
    """,
    unsafe_allow_html=True,
)
